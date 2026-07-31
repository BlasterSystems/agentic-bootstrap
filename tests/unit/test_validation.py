from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from agentic_bootstrap.apply import apply_plan
from agentic_bootstrap.planner import build_plan
from agentic_bootstrap.renderer import render_project
from agentic_bootstrap.validation import validate_target
from tests.helpers import request


class ValidationTests(unittest.TestCase):
    def test_adr_requires_sections_status_heading_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root)
            apply_plan(build_plan(root, render_project(req)), req.features.normalized_platforms())
            bad = root / "docs/adr/0001-bad.md"
            bad.write_text(
                "# ADR-9999: Bad\n\n- **Status:** Unknown\n\n## Context\n\nMissing sections.\n",
                encoding="utf-8",
            )
            errors = validate_target(root)
            self.assertTrue(any("heading ID" in error for error in errors))
            self.assertTrue(any("invalid or missing Status" in error for error in errors))
            self.assertTrue(any("missing ## Decision" in error for error in errors))
            self.assertTrue(any("missing from ADR index" in error for error in errors))

    def test_stale_index_and_status_mismatch_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root)
            apply_plan(build_plan(root, render_project(req)), req.features.normalized_platforms())
            template = (root / "docs/adr/template.md").read_text(encoding="utf-8")
            text = template.replace("ADR-NNNN", "ADR-0001")
            (root / "docs/adr/0001-current.md").write_text(text, encoding="utf-8")
            index = root / "docs/adr/README.md"
            index.write_text(
                index.read_text(encoding="utf-8")
                + "\n| [ADR-0001](0001-current.md) | Accepted | test | tag | current | — |\n"
                + "| [ADR-9998](9998-missing.md) | Accepted | test | tag | missing | — |\n",
                encoding="utf-8",
            )
            errors = validate_target(root)
            self.assertTrue(any("index status" in error for error in errors))
            self.assertTrue(any("index references missing ADR-9998" in error for error in errors))

    def test_valid_reciprocal_supersession_and_mutable_index_pass(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root)
            apply_plan(build_plan(root, render_project(req)), req.features.normalized_platforms())
            template = (root / "docs/adr/template.md").read_text(encoding="utf-8")
            old = (
                template.replace("ADR-NNNN", "ADR-0001")
                .replace("**Status:** Proposed", "**Status:** Superseded")
                .replace("**Superseded by:** None", "**Superseded by:** ADR-0002")
            )
            new = (
                template.replace("ADR-NNNN", "ADR-0002")
                .replace("**Status:** Proposed", "**Status:** Accepted")
                .replace("**Supersedes:** None", "**Supersedes:** ADR-0001")
            )
            (root / "docs/adr/0001-old.md").write_text(old, encoding="utf-8")
            (root / "docs/adr/0002-new.md").write_text(new, encoding="utf-8")
            index = root / "docs/adr/README.md"
            index.write_text(
                index.read_text(encoding="utf-8")
                + "\n| [ADR-0001](0001-old.md) | Superseded | test | tag | old | — |\n"
                + "| [ADR-0002](0002-new.md) | Accepted | test | tag | new | ADR-0001 |\n",
                encoding="utf-8",
            )
            self.assertEqual([], validate_target(root))
            standalone = subprocess.run(
                [str(root / ".agentic/bin/validate")], cwd=root,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=30, check=False,
            )
            self.assertEqual(0, standalone.returncode, standalone.stdout)
            plan = build_plan(root, render_project(req))
            self.assertFalse(plan.conflicts)
            index_operation = next(op for op in plan.operations if op.path == "docs/adr/README.md")
            self.assertEqual("NO_CHANGE", index_operation.action.value)

    def test_runtime_artifacts_are_ignored_without_weakening_owned_validation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root)
            apply_plan(build_plan(root, render_project(req)), req.features.normalized_platforms())
            runtime = root / ".pi-subagents/session"
            runtime.mkdir(parents=True)
            runtime_token = "{{" + "RUNTIME_TOKEN" + "}}\n"
            (runtime / "transcript.md").write_text(runtime_token, encoding="utf-8")

            self.assertEqual([], validate_target(root))
            standalone = subprocess.run(
                [str(root / ".agentic/bin/validate")], cwd=root,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=30, check=False,
            )
            self.assertEqual(0, standalone.returncode, standalone.stdout)

            (root / ".agentic/manifest.json").unlink()
            self.assertEqual([], validate_target(root))

            nested_runtime = root / "src/.pi-subagents"
            nested_runtime.mkdir(parents=True)
            (nested_runtime / "invalid.json").write_text("{invalid\n", encoding="utf-8")
            errors = validate_target(root)
            self.assertTrue(
                any("src/.pi-subagents/invalid.json: invalid JSON" in error for error in errors),
                errors,
            )

    def test_missing_supersession_references_are_diagnostics_not_tracebacks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root)
            apply_plan(build_plan(root, render_project(req)), req.features.normalized_platforms())
            template = (root / "docs/adr/template.md").read_text(encoding="utf-8")
            old = (
                template.replace("ADR-NNNN", "ADR-0001")
                .replace("**Status:** Proposed", "**Status:** Superseded")
                .replace("**Superseded by:** None", "**Superseded by:** ADR-9998")
            )
            current = (
                template.replace("ADR-NNNN", "ADR-0002")
                .replace("**Status:** Proposed", "**Status:** Accepted")
                .replace("**Supersedes:** None", "**Supersedes:** ADR-9999")
            )
            (root / "docs/adr/0001-old.md").write_text(old, encoding="utf-8")
            (root / "docs/adr/0002-current.md").write_text(current, encoding="utf-8")
            index = root / "docs/adr/README.md"
            index.write_text(
                index.read_text(encoding="utf-8")
                + "\n| [ADR-0001](0001-old.md) | Superseded | test | tag | old | — |\n"
                + "| [ADR-0002](0002-current.md) | Accepted | test | tag | current | ADR-9999 |\n",
                encoding="utf-8",
            )

            errors = validate_target(root)
            self.assertTrue(any("references missing ADR-9998" in error for error in errors))
            self.assertTrue(any("references missing ADR-9999" in error for error in errors))

            standalone = subprocess.run(
                [str(root / ".agentic/bin/validate")], cwd=root,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=30, check=False,
            )
            self.assertEqual(1, standalone.returncode, standalone.stdout)
            self.assertIn("references missing ADR-9998", standalone.stdout)
            self.assertIn("references missing ADR-9999", standalone.stdout)
            self.assertNotIn("Traceback", standalone.stdout)

    def test_standalone_validator_checks_all_manifest_owned_toml(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root, ["codex"], agents=True)
            apply_plan(build_plan(root, render_project(req)), req.features.normalized_platforms())
            (root / ".codex/agents/architecture-reviewer.toml").write_text("invalid = [\n", encoding="utf-8")
            result = subprocess.run(
                [str(root / ".agentic/bin/validate")], cwd=root,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=30, check=False,
            )
            self.assertEqual(1, result.returncode, result.stdout)
            self.assertIn("invalid TOML", result.stdout)

    def test_superseded_by_requires_superseded_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root)
            apply_plan(build_plan(root, render_project(req)), req.features.normalized_platforms())
            template = (root / "docs/adr/template.md").read_text(encoding="utf-8")
            old = (
                template.replace("ADR-NNNN", "ADR-0001")
                .replace("**Status:** Proposed", "**Status:** Accepted")
                .replace("**Superseded by:** None", "**Superseded by:** ADR-0002")
            )
            new = (
                template.replace("ADR-NNNN", "ADR-0002")
                .replace("**Status:** Proposed", "**Status:** Accepted")
                .replace("**Supersedes:** None", "**Supersedes:** ADR-0001")
            )
            (root / "docs/adr/0001-old.md").write_text(old, encoding="utf-8")
            (root / "docs/adr/0002-new.md").write_text(new, encoding="utf-8")
            index = root / "docs/adr/README.md"
            index.write_text(
                index.read_text(encoding="utf-8")
                + "\n| [ADR-0001](0001-old.md) | Accepted | test | tag | old | — |\n"
                + "| [ADR-0002](0002-new.md) | Accepted | test | tag | new | ADR-0001 |\n",
                encoding="utf-8",
            )
            errors = validate_target(root)
            self.assertTrue(any("Superseded by requires status Superseded" in error for error in errors))
            self.assertTrue(any("must have status Superseded" in error for error in errors))

    def test_superseded_adr_requires_replacement_link(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root)
            apply_plan(build_plan(root, render_project(req)), req.features.normalized_platforms())
            template = (root / "docs/adr/template.md").read_text(encoding="utf-8")
            text = template.replace("ADR-NNNN", "ADR-0001").replace("**Status:** Proposed", "**Status:** Superseded")
            path = root / "docs/adr/0001-old.md"
            path.write_text(text, encoding="utf-8")
            index = root / "docs/adr/README.md"
            index.write_text(index.read_text(encoding="utf-8") + "\n| ADR-0001 | Superseded | test | old | — |\n", encoding="utf-8")
            errors = validate_target(root)
            self.assertTrue(any("missing Superseded by link" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
