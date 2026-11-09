from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from agentic_bootstrap.apply import apply_plan
from agentic_bootstrap.planner import build_plan
from agentic_bootstrap.renderer import render_project
from tests.helpers import request


class OpenCodeContractTests(unittest.TestCase):
    def test_native_artifacts_and_safe_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root, ["opencode"], agents=True, mcp=True)
            files = render_project(req)
            config = json.loads(files["opencode.json"].content)
            self.assertEqual("ask", config["permission"]["edit"])
            self.assertEqual("ask", config["permission"]["bash"])
            self.assertNotIn("model", config)
            self.assertIn(".opencode/commands/adr-new.md", files)
            self.assertIn(".opencode/agents/architecture-reviewer.md", files)
            self.assertIn(".agents/skills/agentic-bootstrap/SKILL.md", files)
            self.assertIn(".agents/skills/architecture-decision/SKILL.md", files)
            self.assertIn(".agents/skills/semantic-versioning/SKILL.md", files)

    @unittest.skipUnless(shutil.which("opencode"), "OpenCode CLI not installed")
    def test_opencode_parses_generated_config_v2(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root, ["opencode"], agents=True)
            apply_plan(build_plan(root, render_project(req)), ["opencode"])
            env = {**os.environ, "XDG_CONFIG_HOME": str(root / "xdg")}
            result = subprocess.run(
                ["opencode", "debug", "config"],
                cwd=root,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                timeout=30,
                check=False,
            )
            self.assertEqual(0, result.returncode, result.stdout)
            sources = json.loads(result.stdout)
            generated = next(
                entry["info"]
                for entry in sources
                if entry.get("type") == "document"
                and entry.get("path", "").endswith("opencode.json")
            )
            effects = {
                item["action"]: item["effect"] for item in generated["permissions"]
            }
            self.assertEqual("ask", effects["edit"])
            self.assertEqual("ask", effects["shell"])
            # OpenCode v2 removed `debug skill` and `debug agent` and does not
            # list project agents; the agents/commands/skills surface is
            # verified on the filesystem instead.
            self.assertTrue((root / ".opencode/agents/architecture-reviewer.md").is_file())
            self.assertTrue((root / ".opencode/commands/adr-new.md").is_file())
            self.assertTrue((root / ".opencode/commands/docs-check.md").is_file())
            skills = {
                path.parent.name for path in (root / ".agents/skills").glob("*/SKILL.md")
            }
            self.assertEqual(
                {"agentic-bootstrap", "architecture-decision", "docs-check", "semantic-versioning"},
                skills,
            )


if __name__ == "__main__":
    unittest.main()
