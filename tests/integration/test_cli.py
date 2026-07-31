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

    def test_cli_exposes_only_mvp_commands(self) -> None:
        help_result = run_cli("--help")
        self.assertEqual(0, help_result.returncode, help_result.stdout)
        self.assertIn("{init,retrofit,validate}", help_result.stdout)
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
