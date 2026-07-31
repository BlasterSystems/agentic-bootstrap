from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/agentic-bootstrap.sh"


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(SCRIPT), *args],
        cwd=cwd or ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
        check=False,
    )


class CliIntegrationTests(unittest.TestCase):
    def test_dry_run_does_not_create_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "absent"
            result = run_cli("init", "--platform", "all", "--yes", "--dry-run", "--target", str(target))
            self.assertEqual(0, result.returncode, result.stdout)
            self.assertFalse(target.exists())

    def test_cli_exposes_additive_read_only_inspect_command(self) -> None:
        help_result = run_cli("--help")
        self.assertEqual(0, help_result.returncode, help_result.stdout)
        self.assertIn("{init,retrofit,inspect,validate}", help_result.stdout)
        self.assertNotIn("migrate", help_result.stdout)

    def test_generation_help_explains_safe_public_flags(self) -> None:
        result = run_cli("init", "--help")
        self.assertEqual(0, result.returncode, result.stdout)
        help_text = " ".join(result.stdout.split())
        self.assertIn("print the plan without creating the target", help_text)
        self.assertIn("apply without prompting", help_text)
        self.assertIn("remove unchanged obsolete files", help_text)
        self.assertIn("docs/ANSWERS.md", help_text)

    def test_all_features_apply_and_validate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            result = run_cli(
                "init", "--platform", "all", "--yes", "--target", str(target),
                "--mcp", "--agents", "--github", "--hooks",
            )
            self.assertEqual(0, result.returncode, result.stdout)
            validation = run_cli("validate", "--target", str(target))
            self.assertEqual(0, validation.returncode, validation.stdout)
            standalone = subprocess.run(
                [str(target / ".agentic/bin/validate")],
                cwd=target,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=30,
                check=False,
            )
            self.assertEqual(0, standalone.returncode, standalone.stdout)

    def test_plan_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            result = run_cli(
                "init", "--platform", "opencode", "--yes", "--dry-run",
                "--plan-format", "json", "--target", str(target),
            )
            self.assertEqual(0, result.returncode, result.stdout)
            data = json.loads(result.stdout)
            self.assertEqual(str(target.absolute()), data["target"])
            self.assertEqual("dry-run", data["status"])
            self.assertFalse(data["applied"])
            self.assertTrue(data["operations"])

    def test_inspect_is_json_and_does_not_create_missing_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "missing"
            result = run_cli("inspect", "--target", str(target))
            self.assertEqual(0, result.returncode, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual("agentic-bootstrap-inspection/v1", payload["schema"])
            self.assertEqual("missing", payload["root_state"])
            self.assertFalse(target.exists())

    def test_agent_guided_preview_is_non_writing_and_has_integrity_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            intent = Path(directory) / "intent.json"
            intent.write_text(
                json.dumps(
                    {
                        "schema": "agentic-bootstrap-intent/v1",
                        "project": {"name": "guided-project", "test_command": "python -m unittest"},
                        "features": {"platforms": ["pi"], "mcp": False},
                    }
                ),
                encoding="utf-8",
            )
            result = run_cli(
                "init", "--agent-guided", "--agent-intent", str(intent), "--dry-run",
                "--plan-format", "json", "--target", str(target),
            )
            self.assertEqual(0, result.returncode, result.stdout)
            payload = json.loads(result.stdout)
            self.assertEqual("agentic-bootstrap-plan/v1", payload["schema"])
            self.assertEqual(64, len(payload["plan_id"]))
            self.assertEqual("integrity-only-not-identity-or-authorization", payload["plan_id_semantics"])
            self.assertTrue(payload["human_handoff_required"])
            self.assertEqual("untrusted-preview", payload["authority"])
            self.assertFalse(target.exists())

    def test_agent_intent_null_explicitly_clears_detected_command(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            target.mkdir()
            (target / "package.json").write_text(
                json.dumps({"scripts": {"dev": "vite"}}), encoding="utf-8"
            )
            intent = Path(directory) / "intent.json"
            intent.write_text(
                json.dumps(
                    {
                        "schema": "agentic-bootstrap-intent/v1",
                        "project": {"name": "guided-project", "run_command": None},
                        "features": {"platforms": ["pi"]},
                    }
                ),
                encoding="utf-8",
            )
            result = run_cli(
                "retrofit", "--agent-guided", "--agent-intent", str(intent), "--dry-run",
                "--plan-format", "json", "--target", str(target),
            )
            self.assertEqual(0, result.returncode, result.stdout)
            payload = json.loads(result.stdout)
            self.assertIsNone(payload["request"]["project"]["run_command"])
            self.assertFalse((target / "AGENTS.md").exists())

    def test_agent_guided_rejects_yes_and_noninteractive_apply(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            yes = run_cli("init", "--agent-guided", "--yes", "--dry-run", "--target", str(target))
            self.assertEqual(1, yes.returncode, yes.stdout)
            self.assertIn("--yes is not allowed", yes.stdout)
            apply = run_cli(
                "init", "--agent-guided", "--expected-plan", "0" * 64, "--target", str(target)
            )
            self.assertEqual(1, apply.returncode, apply.stdout)
            self.assertIn("interactive trusted terminal", apply.stdout)
            self.assertFalse(target.exists())

    def test_agent_guided_cli_values_use_same_strict_proposal_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            result = run_cli(
                "init", "--agent-guided", "--name", "**injected**", "--dry-run", "--target", str(target)
            )
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("Markdown delimiters", result.stdout)
            self.assertFalse(target.exists())

    def test_agent_intent_rejects_arbitrary_content(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            intent = Path(directory) / "intent.json"
            intent.write_text(
                json.dumps(
                    {
                        "schema": "agentic-bootstrap-intent/v1",
                        "project": {"name": "guided", "content": "arbitrary"},
                        "features": {},
                    }
                ),
                encoding="utf-8",
            )
            result = run_cli(
                "init", "--agent-guided", "--agent-intent", str(intent), "--dry-run",
                "--target", str(target),
            )
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("unknown fields", result.stdout)
            self.assertFalse(target.exists())

    def test_retrofit_preserves_custom_hooks_path(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            subprocess.run(["git", "init"], cwd=target, stdout=subprocess.DEVNULL, check=True)
            subprocess.run(["git", "config", "core.hooksPath", ".husky"], cwd=target, check=True)
            result = run_cli("retrofit", "--platform", "all", "--yes", "--hooks", "--target", str(target))
            self.assertEqual(0, result.returncode, result.stdout)
            current = subprocess.run(
                ["git", "config", "--get", "core.hooksPath"], cwd=target,
                text=True, stdout=subprocess.PIPE, check=True,
            ).stdout.strip()
            self.assertEqual(".husky", current)
            self.assertTrue((target / "setup-hooks.sh").is_file())

    def test_answers_require_real_booleans(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            answers = Path(directory) / "answers.json"
            answers.write_text('{"features": {"mcp": "false"}}', encoding="utf-8")
            result = run_cli("init", "--yes", "--answers", str(answers), "--target", str(target))
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("must be a boolean", result.stdout)
            self.assertFalse(target.exists())

    def test_validation_failure_rolls_back_apply(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            (target / "docs/adr").mkdir(parents=True)
            (target / "docs/adr/bad-name.md").write_text("invalid ADR\n", encoding="utf-8")
            result = run_cli("init", "--platform", "pi", "--yes", "--target", str(target))
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertFalse((target / "AGENTS.md").exists())
            self.assertFalse((target / ".agentic/manifest.json").exists())
            self.assertTrue((target / "docs/adr/bad-name.md").is_file())

    def test_strict_docs_check_fails_when_diff_evidence_is_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            result = run_cli("init", "--platform", "pi", "--yes", "--target", str(target))
            self.assertEqual(0, result.returncode, result.stdout)
            check = subprocess.run(
                [str(target / ".agentic/bin/docs-check"), "--strict"], cwd=target,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=30, check=False,
            )
            self.assertEqual(2, check.returncode, check.stdout)
            self.assertIn("could not establish a reliable diff", check.stdout)


if __name__ == "__main__":
    unittest.main()
