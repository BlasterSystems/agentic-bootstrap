from __future__ import annotations

import json
import tempfile
import tomllib
import unittest
from pathlib import Path

from agentic_bootstrap.renderer import render_project
from agentic_bootstrap.validation import validate_rendered
from tests.helpers import request


ROOT = Path(__file__).resolve().parents[2]


class RendererTests(unittest.TestCase):
    def test_all_platform_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            files = render_project(request(Path(directory), mcp=True, agents=True, github=True, hooks=True))
            self.assertIn("AGENTS.md", files)
            self.assertIn("CLAUDE.md", files)
            self.assertIn("opencode.json", files)
            self.assertIn(".codex/config.toml", files)
            self.assertIn(".codex/agents/architecture-reviewer.toml", files)
            self.assertIn(".opencode/agents/architecture-reviewer.md", files)
            self.assertIn(".agents/skills/agentic-bootstrap/SKILL.md", files)
            self.assertIn(".agents/skills/architecture-decision/SKILL.md", files)
            self.assertNotIn(".codex.md", files)
            self.assertNotIn(".claude/claude.json", files)
            json.loads(files["opencode.json"].content)
            tomllib.loads(files[".codex/config.toml"].content.decode())
            self.assertEqual([], validate_rendered(files))

    def test_repository_and_packaged_agent_guided_skills_are_identical(self) -> None:
        packaged = (ROOT / "src/agentic_bootstrap/templates/core/skills/agentic-bootstrap/SKILL.md").read_bytes()
        self.assertEqual(packaged, (ROOT / ".agents/skills/agentic-bootstrap/SKILL.md").read_bytes())
        self.assertEqual(packaged, (ROOT / ".claude/skills/agentic-bootstrap/SKILL.md").read_bytes())

    def test_agent_guided_skill_stops_before_apply_and_is_provider_neutral(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            files = render_project(request(Path(directory), ["pi"]))
            skill = files[".agents/skills/agentic-bootstrap/SKILL.md"].content.decode()
            self.assertIn("Stop", skill)
            self.assertIn("Never invoke agent-guided apply yourself", skill)
            self.assertIn("integrity only", skill)
            for token in ("mcp__", "Task tool", ".claude/", ".codex/", ".opencode/", ".pi/"):
                self.assertNotIn(token, skill)

    def test_release_skill_and_documentation_are_part_of_the_core(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            files = render_project(request(Path(directory), ["pi"]))
            skill = files[".agents/skills/semantic-versioning/SKILL.md"].content.decode()
            releasing = files["docs/RELEASING.md"].content.decode()
            self.assertIn("name: semantic-versioning", skill)
            self.assertIn("explicit human confirmation", skill)
            self.assertIn("vMAJOR.MINOR.PATCH", releasing)
            self.assertIn("docs/RELEASING.md", files["AGENTS.md"].content.decode())

    def test_portable_agents_has_no_adapter_syntax(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            text = render_project(request(Path(directory)))["AGENTS.md"].content.decode()
            for token in ("mcp__", "Task tool", ".claude/", ".codex/", ".opencode/", ".pi/"):
                self.assertNotIn(token, text)
            self.assertIn("docs/adr/README.md", text)
            self.assertIn("Do not read every ADR", text)

    def test_no_ticket_has_no_tracker_or_broken_task_name(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            files = render_project(request(Path(directory), ticket_prefix=None))
            combined = b"\n".join(item.content for item in files.values()).decode()
            self.assertNotIn("Jira", combined)
            self.assertNotIn("Atlassian", combined)
            self.assertNotIn("-001.md", combined)
            self.assertIn("No issue-tracker", files["AGENTS.md"].content.decode())

    def test_scheduled_audit_is_explicit_and_renders_weekly_trigger(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            files = render_project(request(Path(directory), github=True, scheduled_audit=True))
            workflow = files[".github/workflows/docs-check.yml"].content.decode()
            self.assertIn("schedule:", workflow)
            self.assertIn("cron: '0 9 * * 1'", workflow)
            config = json.loads(files[".agentic/config.json"].content)
            self.assertTrue(config["features"]["requested"]["scheduled_audit"])

    def test_structured_values_escape_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            req = request(Path(directory))
            req.facts.name = 'quoted " project'
            files = render_project(req)
            config = json.loads(files[".agentic/config.json"].content)
            self.assertEqual('quoted " project', config["project"]["name"])


if __name__ == "__main__":
    unittest.main()
