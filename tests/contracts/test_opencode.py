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
            self.assertIn(".agents/skills/architecture-decision/SKILL.md", files)
            self.assertIn(".agents/skills/semantic-versioning/SKILL.md", files)

    @unittest.skipUnless(shutil.which("opencode"), "OpenCode CLI not installed")
    def test_opencode_diagnostics_load_generated_config_skill_and_agent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root, ["opencode"], agents=True)
            apply_plan(build_plan(root, render_project(req)), ["opencode"])
            env = {**os.environ, "XDG_CONFIG_HOME": str(root / "xdg")}
            outputs: dict[str, str] = {}
            commands = (
                ("config", ["opencode", "debug", "config"]),
                ("skill", ["opencode", "debug", "skill"]),
                ("agent", ["opencode", "debug", "agent", "architecture-reviewer"]),
            )
            for label, command in commands:
                result = subprocess.run(
                    command,
                    cwd=root,
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    timeout=30,
                    check=False,
                )
                self.assertEqual(0, result.returncode, f"{' '.join(command)}\n{result.stdout}")
                outputs[label] = result.stdout
            config = json.loads(outputs["config"])
            self.assertEqual("ask", config["permission"]["edit"])
            self.assertIn("adr-new", config["command"])
            skills = json.loads(outputs["skill"])
            self.assertEqual(
                {"architecture-decision", "docs-check", "semantic-versioning"},
                {item["name"] for item in skills},
            )
            agent = json.loads(outputs["agent"])
            self.assertEqual("architecture-reviewer", agent["name"])
            self.assertEqual("subagent", agent["mode"])


if __name__ == "__main__":
    unittest.main()
