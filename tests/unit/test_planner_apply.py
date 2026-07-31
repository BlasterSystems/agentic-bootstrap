from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agentic_bootstrap.apply import ApplyError, apply_plan
from agentic_bootstrap.manifest import Manifest, sha256_path
from agentic_bootstrap.model import GeneratedFile
from agentic_bootstrap.planner import Action, build_plan
from agentic_bootstrap.renderer import render_project
from tests.helpers import request


class PlannerApplyTests(unittest.TestCase):
    def test_apply_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            req = request(root)
            first = build_plan(root, render_project(req))
            self.assertTrue(
                all(op.action in {Action.CREATE, Action.MANIFEST_CREATE} for op in first.operations)
            )
            apply_plan(first, req.features.normalized_platforms())
            second = build_plan(root, render_project(req))
            self.assertFalse(second.changes)
            self.assertFalse(second.conflicts)
            manifest_path = root / ".agentic/manifest.json"
            before = manifest_path.read_bytes()
            apply_plan(second, req.features.normalized_platforms())
            self.assertEqual(before, manifest_path.read_bytes())

    def test_unmanaged_file_is_conflict_and_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agents = root / "AGENTS.md"
            agents.write_text("user owned\n", encoding="utf-8")
            original = sha256_path(agents)
            plan = build_plan(root, render_project(request(root)))
            self.assertTrue(any(op.path == "AGENTS.md" and op.action == Action.CONFLICT for op in plan.operations))
            with self.assertRaises(ApplyError):
                apply_plan(plan, ["claude"])
            self.assertEqual(original, sha256_path(agents))

    def test_user_modified_generated_file_becomes_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            req = request(root)
            apply_plan(build_plan(root, render_project(req)), req.features.normalized_platforms())
            (root / ".agentic/bin/validate").write_text("modified\n", encoding="utf-8")
            plan = build_plan(root, render_project(req))
            self.assertTrue(
                any(
                    op.path == ".agentic/bin/validate" and op.action == Action.CONFLICT
                    for op in plan.operations
                )
            )

    def test_apply_failure_rolls_back(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            req = request(root)
            plan = build_plan(root, render_project(req))
            real_link = os.link
            calls = 0

            def fail_second(source, destination, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("injected failure")
                return real_link(source, destination, **kwargs)

            with mock.patch("agentic_bootstrap.apply.os.link", side_effect=fail_second):
                with self.assertRaises(ApplyError):
                    apply_plan(plan, req.features.normalized_platforms())
            self.assertFalse(root.exists())

    def test_mode_drift_is_repaired(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            req = request(root)
            apply_plan(build_plan(root, render_project(req)), req.features.normalized_platforms())
            validator = root / ".agentic/bin/validate"
            validator.chmod(0o644)
            plan = build_plan(root, render_project(req))
            operation = next(op for op in plan.operations if op.path == ".agentic/bin/validate")
            self.assertEqual(Action.UPDATE_GENERATED, operation.action)
            apply_plan(plan, req.features.normalized_platforms())
            self.assertTrue(os.access(validator, os.X_OK))

    def test_stale_no_change_plan_never_rebaselines_modified_owned_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root)
            apply_plan(build_plan(root, render_project(req)), req.features.normalized_platforms())
            plan = build_plan(root, render_project(req))
            validator = root / ".agentic/bin/validate"
            validator.write_text("changed after planning\n", encoding="utf-8")
            with self.assertRaises(ApplyError):
                apply_plan(plan, req.features.normalized_platforms())
            self.assertEqual("changed after planning\n", validator.read_text(encoding="utf-8"))

    def test_stale_skip_unmanaged_plan_never_accepts_changed_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root)
            desired = render_project(req)
            (root / "AGENTS.md").write_bytes(desired["AGENTS.md"].content)
            plan = build_plan(root, desired)
            (root / "AGENTS.md").write_text("changed after planning\n", encoding="utf-8")
            with self.assertRaises(ApplyError):
                apply_plan(plan, req.features.normalized_platforms())
            self.assertFalse((root / ".agentic/manifest.json").exists())

    def test_stale_create_plan_never_overwrites_new_unmanaged_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root)
            plan = build_plan(root, render_project(req))
            agents = root / "AGENTS.md"
            agents.write_text("appeared after planning\n", encoding="utf-8")
            with self.assertRaises(ApplyError):
                apply_plan(plan, req.features.normalized_platforms())
            self.assertEqual("appeared after planning\n", agents.read_text(encoding="utf-8"))

    def test_symlinked_parent_is_conflict_and_external_files_are_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as external_directory:
            root = Path(directory)
            external = Path(external_directory)
            victim = external / "ARCHITECTURE.md"
            victim.write_text("external\n", encoding="utf-8")
            (root / "docs").symlink_to(external, target_is_directory=True)
            plan = build_plan(root, render_project(request(root)))
            self.assertTrue(any(op.action == Action.CONFLICT and op.path.startswith("docs/") for op in plan.operations))
            with self.assertRaises(ApplyError):
                apply_plan(plan, ["pi"])
            self.assertEqual("external\n", victim.read_text(encoding="utf-8"))

    def test_malicious_manifest_path_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".agentic").mkdir()
            manifest = {
                "schema": "agentic-bootstrap-manifest/v1",
                "generator_version": "0.1.0",
                "platforms": ["pi"],
                "files": {"../victim": {"sha256": "0" * 64, "executable": False}},
            }
            (root / ".agentic/manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            plan = build_plan(root, render_project(request(root)))
            self.assertTrue(any(op.path == ".agentic/manifest.json" and op.action == Action.CONFLICT for op in plan.operations))

    def test_unmanaged_manifest_is_conflict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".agentic").mkdir()
            original = '{"files": {}}\n'
            path = root / ".agentic/manifest.json"
            path.write_text(original, encoding="utf-8")
            plan = build_plan(root, render_project(request(root)))
            self.assertTrue(plan.conflicts)
            with self.assertRaises(ApplyError):
                apply_plan(plan, ["pi"])
            self.assertEqual(original, path.read_text(encoding="utf-8"))

    def test_rollback_removes_created_directories_in_existing_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root)
            plan = build_plan(root, render_project(req))
            real_link = os.link
            calls = 0

            def fail_second(source, destination, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("injected failure")
                return real_link(source, destination, **kwargs)

            with mock.patch("agentic_bootstrap.apply.os.link", side_effect=fail_second):
                with self.assertRaises(ApplyError):
                    apply_plan(plan, req.features.normalized_platforms())
            self.assertEqual([], list(root.iterdir()))

    def test_obsolete_files_require_explicit_removal_and_manifest_is_pruned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            desired = {"owned.txt": GeneratedFile.text("owned.txt", "owned")}
            apply_plan(build_plan(root, desired), ["pi"])
            keep_plan = build_plan(root, {})
            self.assertTrue(any(op.action == Action.REMOVE_OBSOLETE for op in keep_plan.operations))
            before = (root / ".agentic/manifest.json").read_bytes()
            apply_plan(keep_plan, ["pi"], remove_obsolete=False)
            self.assertTrue((root / "owned.txt").exists())
            self.assertEqual(before, (root / ".agentic/manifest.json").read_bytes())
            remove_plan = build_plan(root, {}, remove_obsolete=True)
            apply_plan(remove_plan, ["pi"], remove_obsolete=True)
            self.assertFalse((root / "owned.txt").exists())
            manifest = Manifest.load(root)
            self.assertNotIn("owned.txt", manifest.files)

    def test_identical_unmanaged_file_remains_unowned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            desired = render_project(request(root))
            (root / "AGENTS.md").write_bytes(desired["AGENTS.md"].content)
            plan = build_plan(root, desired)
            op = next(op for op in plan.operations if op.path == "AGENTS.md")
            self.assertEqual(Action.SKIP_UNMANAGED, op.action)


if __name__ == "__main__":
    unittest.main()
