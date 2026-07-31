from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import tomllib
import unittest
from pathlib import Path

from agentic_bootstrap.apply import apply_plan
from agentic_bootstrap.planner import build_plan
from agentic_bootstrap.renderer import render_project
from tests.helpers import request


class PlatformContractTests(unittest.TestCase):
    def test_claude_uses_official_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            files = render_project(request(Path(directory), ["claude"], mcp=True, agents=True))
            self.assertIn("CLAUDE.md", files)
            self.assertIn(".claude/skills/agentic-bootstrap/SKILL.md", files)
            self.assertIn(".claude/skills/docs-check/SKILL.md", files)
            self.assertIn(".claude/skills/semantic-versioning/SKILL.md", files)
            self.assertIn(".claude/agents/architecture-reviewer.md", files)
            self.assertIn(".mcp.json", files)
            self.assertNotIn(".claude/claude.json", files)

    def test_codex_uses_agents_and_toml(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            files = render_project(request(Path(directory), ["codex"], mcp=True, agents=True))
            self.assertIn("AGENTS.md", files)
            self.assertIn(".agents/skills/agentic-bootstrap/SKILL.md", files)
            self.assertIn(".agents/skills/docs-check/SKILL.md", files)
            self.assertIn(".agents/skills/semantic-versioning/SKILL.md", files)
            self.assertIn(".codex/config.toml", files)
            self.assertNotIn(".codex.md", files)
            tomllib.loads(files[".codex/config.toml"].content.decode())

    def test_pi_core_is_native_and_extension_capabilities_not_generated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            files = render_project(request(Path(directory), ["pi"], mcp=True, agents=True))
            self.assertIn("AGENTS.md", files)
            self.assertIn(".agents/skills/agentic-bootstrap/SKILL.md", files)
            self.assertIn(".agents/skills/docs-check/SKILL.md", files)
            self.assertIn(".agents/skills/semantic-versioning/SKILL.md", files)
            self.assertFalse(any(path.startswith(".pi/") for path in files))
            config = json.loads(files[".agentic/config.json"].content)
            self.assertTrue(config["features"]["requested"]["mcp"])
            self.assertTrue(config["features"]["requested"]["agents"])
            self.assertFalse(config["features"]["effective_by_platform"]["pi"]["mcp"])
            self.assertFalse(config["features"]["effective_by_platform"]["pi"]["agents"])
            support = files["docs/PLATFORM_SUPPORT.md"].content.decode()
            self.assertIn("MCP/subagents require extensions", support)

    @unittest.skipUnless(shutil.which("claude"), "Claude Code CLI not installed")
    def test_claude_parses_project_mcp(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root, ["claude"], mcp=True)
            apply_plan(build_plan(root, render_project(req)), ["claude"])
            result = subprocess.run(
                ["claude", "mcp", "get", "context7"], cwd=root,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=30, check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertIn("Scope: Project config", result.stdout)
            self.assertIn("Type: http", result.stdout)

    @unittest.skipUnless(shutil.which("codex"), "Codex CLI not installed")
    def test_codex_cli_parses_generated_toml_in_isolated_config_home(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root, ["codex"], mcp=True, agents=True)
            apply_plan(build_plan(root, render_project(req)), ["codex"])
            result = subprocess.run(
                ["codex", "mcp", "list", "--json"], cwd=root,
                env={**os.environ, "CODEX_HOME": str(root / ".codex")},
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=30, check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout)
            servers = json.loads(result.stdout)
            self.assertTrue(any(server["name"] == "context7" for server in servers))

    def test_shell_files_parse(self) -> None:
        bash = shutil.which("bash")
        if not bash:
            self.skipTest("bash not installed")
        root = Path(__file__).resolve().parents[2]
        scripts = list((root / "scripts").glob("*.sh"))
        with tempfile.TemporaryDirectory() as directory:
            req = request(Path(directory), hooks=True)
            req.facts.build_command = "printf '%s\\n' build"
            req.facts.test_command = "python -c \"print('test')\""
            generated = render_project(req)
            for relative in (".githooks/pre-commit", "setup-hooks.sh"):
                path = Path(directory) / relative.replace("/", "_")
                path.write_bytes(generated[relative].content)
                scripts.append(path)
            for script in scripts:
                result = subprocess.run([bash, "-n", str(script)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(0, result.returncode, result.stderr.decode())


if __name__ == "__main__":
    unittest.main()
