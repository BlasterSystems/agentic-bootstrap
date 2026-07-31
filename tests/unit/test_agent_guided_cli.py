from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentic_bootstrap import cli
from agentic_bootstrap.facade import prepare_bootstrap
from agentic_bootstrap.manifest import Manifest, sha256_path
from agentic_bootstrap.model import BootstrapRequest, FeatureSelection, ProjectFacts
from agentic_bootstrap.protocol import ResultArtifact


class _TTY:
    def __init__(self) -> None:
        self.values: list[str] = []

    def isatty(self) -> bool:
        return True

    def write(self, value: str) -> int:
        self.values.append(value)
        return len(value)

    def flush(self) -> None:
        pass

    def getvalue(self) -> str:
        return "".join(self.values)


class AgentGuidedCliTests(unittest.TestCase):
    def test_interactive_handoff_recomputes_displays_and_confirms(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project-\x1b-\u202e"
            intent_path = Path(directory) / "intent.json"
            intent_path.write_text(
                json.dumps(
                    {
                        "schema": "agentic-bootstrap-intent/v1",
                        "project": {"name": "guided-project", "description": "Guided project"},
                        "features": {"platforms": ["pi"]},
                    }
                ),
                encoding="utf-8",
            )
            req = BootstrapRequest(
                target=target,
                mode="init",
                facts=ProjectFacts(name="guided-project", description="Guided project"),
                features=FeatureSelection(platforms=["pi"]),
            )
            expected = prepare_bootstrap(req).plan_id
            answers = ["", "", "", "", "", "", ""] + [""] * 5 + ["yes"]
            output = _TTY()
            with mock.patch("builtins.input", side_effect=answers), mock.patch.object(
                cli.sys, "stdin", _TTY()
            ), mock.patch.object(cli.sys, "stdout", output):
                result = cli.main(
                    [
                        "init",
                        "--agent-guided",
                        "--agent-intent",
                        str(intent_path),
                        "--expected-plan",
                        expected,
                        "--target",
                        str(target),
                    ]
                )
            self.assertEqual(0, result)
            displayed = output.getvalue()
            self.assertNotIn("\x1b", displayed)
            self.assertNotIn("\u202e", displayed)
            self.assertIn("\\u001b", displayed)
            self.assertIn("\\u202e", displayed)
            for required in (
                "Complete canonical plan bound by the plan identifier",
                '"generator_version"',
                '"target_root"',
                '"observed"',
                '"resulting_ownership"',
                '"remove_obsolete"',
                "Reviewable generated-file diffs",
                "Deterministic result",
                '"rollback_status": "not-needed"',
            ):
                self.assertIn(required, displayed)
            self.assertTrue((target / "AGENTS.md").is_file())
            self.assertTrue((target / ".agentic/manifest.json").is_file())

    def test_final_decline_leaves_target_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            req = BootstrapRequest(
                target=target,
                mode="init",
                facts=ProjectFacts(name="project", description="Software project project"),
                features=FeatureSelection(),
            )
            expected = prepare_bootstrap(req).plan_id
            answers = [""] * 12 + ["no"]
            output = _TTY()
            with mock.patch("builtins.input", side_effect=answers), mock.patch.object(
                cli.sys, "stdin", _TTY()
            ), mock.patch.object(cli.sys, "stdout", output):
                result = cli.main(
                    [
                        "init",
                        "--agent-guided",
                        "--expected-plan",
                        expected,
                        "--target",
                        str(target),
                    ]
                )
            self.assertEqual(0, result)
            self.assertIn("Cancelled; no files were changed.", output.getvalue())
            self.assertFalse(target.exists())

    def test_trusted_display_escapes_untrusted_target_controls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "unsafe-\x1b-\u202e"
            prepared = prepare_bootstrap(
                BootstrapRequest(
                    target=target,
                    mode="init",
                    facts=ProjectFacts(name="safe", description="safe"),
                    features=FeatureSelection(platforms=["pi"]),
                )
            )
            output = _TTY()
            with mock.patch.object(cli.sys, "stdout", output):
                cli._display_agent_review(prepared, [])
            displayed = output.getvalue()
            self.assertNotIn("\x1b", displayed)
            self.assertNotIn("\u202e", displayed)
            self.assertIn("\\u001b", displayed)
            self.assertIn("\\u202e", displayed)

    def test_agent_guided_failure_displays_rollback_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            req = BootstrapRequest(
                target=target,
                mode="init",
                facts=ProjectFacts(name="project", description="Software project project"),
                features=FeatureSelection(),
            )
            expected = prepare_bootstrap(req).plan_id
            failure = ResultArtifact(
                target=str(target),
                status="apply-failed",
                applied=False,
                plan_id=expected,
                rollback_status="failed",
                errors=("rollback failed \u202e",),
            )
            output = _TTY()
            error_output = _TTY()
            with mock.patch("builtins.input", side_effect=[""] * 12 + ["yes"]), mock.patch.object(
                cli.sys, "stdin", _TTY()
            ), mock.patch.object(cli.sys, "stdout", output), mock.patch.object(
                cli.sys, "stderr", error_output
            ), mock.patch.object(cli, "apply_bootstrap", return_value=failure):
                result = cli.main(
                    [
                        "init",
                        "--agent-guided",
                        "--expected-plan",
                        expected,
                        "--target",
                        str(target),
                    ]
                )
            self.assertEqual(1, result)
            self.assertIn('"rollback_status": "failed"', output.getvalue())
            self.assertNotIn("\u202e", output.getvalue())
            self.assertNotIn("\u202e", error_output.getvalue())
            self.assertIn("\\u202e", error_output.getvalue())
            self.assertFalse(target.exists())

    def test_agent_preview_withholds_existing_content_and_terminal_escapes_it(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            malicious = "GITHUB_TOKEN=ghp_EXFILTRATED\x1b[2J\u202e\n"
            agents = root / "AGENTS.md"
            agents.write_text(malicious, encoding="utf-8")
            (root / ".agentic").mkdir()
            manifest = Manifest(
                platforms=["pi"],
                files={
                    "AGENTS.md": {
                        "sha256": sha256_path(agents),
                        "executable": False,
                        "mutable": False,
                    }
                },
            )
            (root / ".agentic/manifest.json").write_bytes(manifest.to_bytes())
            prepared = prepare_bootstrap(
                BootstrapRequest(
                    target=root,
                    mode="retrofit",
                    facts=ProjectFacts(name="safe", description="safe"),
                    features=FeatureSelection(platforms=["pi"]),
                )
            )
            preview = json.dumps(prepared.payload(status="dry-run", applied=False, warnings=[]))
            self.assertNotIn("ghp_EXFILTRATED", preview)
            self.assertIn("existing repository content withheld", preview)
            output = _TTY()
            with mock.patch.object(cli.sys, "stdout", output):
                cli._display_agent_review(prepared, [])
            displayed = output.getvalue()
            self.assertIn("GITHUB_TOKEN=ghp_EXFILTRATED", displayed)
            self.assertNotIn("\x1b", displayed)
            self.assertNotIn("\u202e", displayed)
            self.assertIn("\\u001b", displayed)
            self.assertIn("\\u202e", displayed)

    def test_post_apply_validation_failure_displays_deterministic_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            req = BootstrapRequest(
                target=target,
                mode="init",
                facts=ProjectFacts(name="project", description="Software project project"),
                features=FeatureSelection(),
            )
            expected = prepare_bootstrap(req).plan_id
            output = _TTY()
            error_output = _TTY()
            with mock.patch("builtins.input", side_effect=[""] * 12 + ["yes"]), mock.patch.object(
                cli.sys, "stdin", _TTY()
            ), mock.patch.object(cli.sys, "stdout", output), mock.patch.object(
                cli.sys, "stderr", error_output
            ), mock.patch.object(cli, "validate_target", return_value=["unsafe \u202e validation"]):
                result = cli.main(
                    [
                        "init",
                        "--agent-guided",
                        "--expected-plan",
                        expected,
                        "--target",
                        str(target),
                    ]
                )
            self.assertEqual(1, result)
            self.assertIn('"status": "validation-failed"', output.getvalue())
            self.assertIn('"rollback_status": "not-needed"', output.getvalue())
            self.assertNotIn("\u202e", output.getvalue())
            self.assertNotIn("\u202e", error_output.getvalue())

    def test_post_apply_validation_exception_displays_deterministic_result(self) -> None:
        for exception_type in (OSError, RuntimeError):
            with self.subTest(exception_type=exception_type), tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / "project"
                req = BootstrapRequest(
                    target=target,
                    mode="init",
                    facts=ProjectFacts(name="project", description="Software project project"),
                    features=FeatureSelection(),
                )
                expected = prepare_bootstrap(req).plan_id
                output = _TTY()
                error_output = _TTY()
                with mock.patch("builtins.input", side_effect=[""] * 12 + ["yes"]), mock.patch.object(
                    cli.sys, "stdin", _TTY()
                ), mock.patch.object(cli.sys, "stdout", output), mock.patch.object(
                    cli.sys, "stderr", error_output
                ), mock.patch.object(
                    cli, "validate_target", side_effect=exception_type("bad \u202e validation")
                ):
                    result = cli.main(
                        [
                            "init",
                            "--agent-guided",
                            "--expected-plan",
                            expected,
                            "--target",
                            str(target),
                        ]
                    )
                self.assertEqual(1, result)
                self.assertIn('"status": "validation-failed"', output.getvalue())
                self.assertIn('"applied": true', output.getvalue())
                self.assertIn('"rollback_status": "not-needed"', output.getvalue())
                self.assertNotIn("\u202e", output.getvalue())
                self.assertNotIn("\u202e", error_output.getvalue())
                self.assertTrue((target / ".agentic/manifest.json").is_file())

    def test_exception_output_escapes_untrusted_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            alias = Path(directory) / "alias-\x1b[31m-\u202e"
            alias.symlink_to(Path(outside), target_is_directory=True)
            error_output = _TTY()
            with mock.patch.object(cli.sys, "stderr", error_output):
                result = cli.main(["inspect", "--target", str(alias)])
            self.assertEqual(1, result)
            self.assertNotIn("\x1b", error_output.getvalue())
            self.assertNotIn("\u202e", error_output.getvalue())
            self.assertIn("\\u001b", error_output.getvalue())
            self.assertIn("\\u202e", error_output.getvalue())

    def test_empty_expected_plan_is_rejected_in_all_modes(self) -> None:
        for guided in (False, True):
            with self.subTest(guided=guided), tempfile.TemporaryDirectory() as directory:
                target = Path(directory) / "project"
                arguments = ["init"]
                if guided:
                    arguments.append("--agent-guided")
                arguments.extend(["--expected-plan", "", "--target", str(target)])
                error_output = _TTY()
                with mock.patch.object(cli.sys, "stderr", error_output):
                    result = cli.main(arguments)
                self.assertEqual(1, result)
                self.assertFalse(target.exists())

    def test_expected_plan_does_not_suppress_recomputed_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "project"
            with mock.patch("builtins.input", side_effect=[""] * 12), mock.patch.object(
                cli.sys, "stdin", _TTY()
            ), mock.patch.object(cli.sys, "stdout", _TTY()), mock.patch.object(
                cli.sys, "stderr", _TTY()
            ):
                result = cli.main(
                    [
                        "init",
                        "--agent-guided",
                        "--expected-plan",
                        "0" * 64,
                        "--target",
                        str(target),
                    ]
                )
            self.assertEqual(1, result)
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
