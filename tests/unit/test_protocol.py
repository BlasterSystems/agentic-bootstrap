from __future__ import annotations

import inspect
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import agentic_bootstrap
from agentic_bootstrap.facade import apply_bootstrap, prepare_bootstrap
from agentic_bootstrap.model import GeneratedFile
from agentic_bootstrap.planner import build_plan
from agentic_bootstrap.protocol import AgentIntent, ResultArtifact, plan_document, plan_identifier
from tests.helpers import request


class ProtocolTests(unittest.TestCase):
    def test_agent_intent_is_strict_and_unverified(self) -> None:
        intent = AgentIntent.from_dict(
            {
                "schema": "agentic-bootstrap-intent/v1",
                "project": {"name": "safe-project", "test_command": "python -m unittest"},
                "features": {"platforms": ["pi"], "mcp": False},
            }
        )
        self.assertEqual("unverified-proposal", intent.to_dict()["authority"])
        self.assertEqual(intent, AgentIntent.from_dict(intent.to_dict()))
        for forbidden in (
            {"confirmed": True},
            {"content": "payload"},
            {"path": "AGENTS.md"},
            {"mutable": True},
        ):
            with self.subTest(forbidden=forbidden):
                with self.assertRaises(ValueError):
                    AgentIntent.from_dict(
                        {
                            "schema": "agentic-bootstrap-intent/v1",
                            "project": {"name": "safe"},
                            "features": forbidden,
                        }
                    )

    def test_agent_intent_rejects_markdown_controls_and_non_nfc(self) -> None:
        bad_names = (
            "bad\nname",
            "**bold**",
            "{{" + "TOKEN" + "}}",
            "e\u0301",
            "bad\u0085name",
            "bad\u009bname",
            "bad\u2028name",
            "bad\u2029name",
            "bad\u200bname",
        )
        for name in bad_names:
            with self.subTest(name=name):
                with self.assertRaises(ValueError):
                    AgentIntent.from_dict(
                        {
                            "schema": "agentic-bootstrap-intent/v1",
                            "project": {"name": name},
                            "features": {},
                        }
                    )
        with self.assertRaises(ValueError):
            AgentIntent.from_dict(
                {
                    "schema": "agentic-bootstrap-intent/v1",
                    "project": {"name": "safe", "test_command": "`unsafe`"},
                    "features": {},
                }
            )

    def test_agent_intent_file_is_bounded_and_not_symlinked(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            real = root / "intent.json"
            real.write_text('{"schema":"agentic-bootstrap-intent/v1","project":{},"features":{}}', encoding="utf-8")
            link = root / "link.json"
            link.symlink_to(real)
            with self.assertRaises(ValueError):
                AgentIntent.load(link)
            large = root / "large.json"
            large.write_bytes(b" " * 65_537)
            with self.assertRaises(ValueError):
                AgentIntent.load(large)

    def test_public_facade_does_not_accept_desired_file_maps(self) -> None:
        self.assertIs(agentic_bootstrap.prepare_bootstrap, prepare_bootstrap)
        parameters = inspect.signature(prepare_bootstrap).parameters
        self.assertEqual({"request", "remove_obsolete"}, set(parameters))

    def test_plan_identifier_is_deterministic_and_binds_root_and_owned_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            req = request(root, ["pi"])
            first = prepare_bootstrap(req)
            second = prepare_bootstrap(req)
            self.assertEqual(first.plan_id, second.plan_id)
            aliased = request(root.parent / "unused" / ".." / root.name, ["pi"])
            self.assertEqual(first.plan_id, prepare_bootstrap(aliased).plan_id)
            root.mkdir()
            existing_root = prepare_bootstrap(req)
            self.assertNotEqual(first.plan_id, existing_root.plan_id)

            desired = dict(existing_root.desired)
            original = desired["AGENTS.md"]
            desired["AGENTS.md"] = GeneratedFile(
                path=original.path,
                content=original.content,
                executable=original.executable,
                mutable=False,
            )
            changed_plan = build_plan(root, desired)
            changed_document = plan_document(req, desired, changed_plan, remove_obsolete=False)
            self.assertNotEqual(existing_root.plan_id, plan_identifier(changed_document))

    def test_plan_observation_does_not_follow_symlinked_parent(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            external = Path(outside)
            (external / "ARCHITECTURE.md").write_text("outside secret\n", encoding="utf-8")
            (root / "docs").symlink_to(external, target_is_directory=True)
            prepared = prepare_bootstrap(request(root, ["pi"]))
            self.assertEqual("parent-symlink", prepared.document["observed"]["docs/ARCHITECTURE.md"]["state"])
            self.assertTrue(prepared.plan.conflicts)

    def test_apply_recomputes_and_rejects_changed_destination(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            prepared = prepare_bootstrap(request(root, ["pi"]))
            (root / "AGENTS.md").write_text("appeared after preview\n", encoding="utf-8")
            result = apply_bootstrap(prepared, expected_plan_id=prepared.plan_id)
            self.assertFalse(result.applied)
            self.assertEqual("apply-failed", result.status)
            self.assertEqual("not-needed", result.rollback_status)
            self.assertIn("plan identifier mismatch", result.errors[0])
            self.assertFalse((root / ".agentic/manifest.json").exists())

    def test_plan_and_result_artifacts_are_schema_versioned(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            prepared = prepare_bootstrap(request(Path(directory), ["pi"]))
            self.assertEqual("agentic-bootstrap-plan/v1", prepared.artifact.to_dict()["schema"])
            result = ResultArtifact(
                target=str(Path(directory)), status="applied", applied=True, plan_id=prepared.plan_id
            ).to_dict()
            self.assertEqual("agentic-bootstrap-result/v1", result["schema"])
            self.assertEqual("deterministic-result", result["authority"])
            self.assertEqual("not-needed", result["rollback_status"])

    def test_plan_payload_contains_the_complete_canonical_document(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            prepared = prepare_bootstrap(request(Path(directory) / "project", ["pi"]))
            payload = prepared.payload(status="dry-run", applied=False, warnings=[])
            for key in (
                "generator_version",
                "target_root",
                "request",
                "desired",
                "observed",
                "operations",
                "resulting_ownership",
                "remove_obsolete",
                "manifest_claim",
            ):
                self.assertEqual(prepared.document[key], payload[key])
            self.assertEqual(prepared.plan_id, payload["plan_id"])
            self.assertIn("diffs", payload)

    def test_plan_identifier_binds_output_paths_content_modes_and_removal_policy(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            root.mkdir()
            req = request(root, ["pi"])
            prepared = prepare_bootstrap(req)
            original = prepared.desired["AGENTS.md"]
            variants = []
            changed_content = dict(prepared.desired)
            changed_content["AGENTS.md"] = GeneratedFile(
                path=original.path,
                content=original.content + b"changed\n",
                executable=original.executable,
                mutable=original.mutable,
            )
            variants.append(changed_content)
            changed_mode = dict(prepared.desired)
            changed_mode["AGENTS.md"] = GeneratedFile(
                path=original.path,
                content=original.content,
                executable=not original.executable,
                mutable=original.mutable,
            )
            variants.append(changed_mode)
            changed_path = dict(prepared.desired)
            changed_path["RENAMED.md"] = changed_path.pop("AGENTS.md")
            variants.append(changed_path)
            for desired in variants:
                plan = build_plan(root, desired)
                document = plan_document(req, desired, plan, remove_obsolete=False)
                self.assertNotEqual(prepared.plan_id, plan_identifier(document))
            self.assertNotEqual(
                prepared.plan_id,
                plan_identifier(plan_document(req, prepared.desired, prepared.plan, remove_obsolete=True)),
            )

    def test_apply_with_malformed_expected_identifier_returns_result(self) -> None:
        for malformed in ("", "not-a-plan-id"):
            with self.subTest(malformed=malformed), tempfile.TemporaryDirectory() as directory:
                root = Path(directory) / "project"
                prepared = prepare_bootstrap(request(root, ["pi"]))
                result = apply_bootstrap(prepared, expected_plan_id=malformed)
                self.assertFalse(result.applied)
                self.assertEqual("apply-failed", result.status)
                self.assertEqual(prepared.plan_id, result.plan_id)
                self.assertIn("plan identifier mismatch", result.errors[0])
                self.assertFalse(root.exists())

    def test_apply_result_reports_rollback_status(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "project"
            prepared = prepare_bootstrap(request(root, ["pi"]))
            real_link = os.link
            calls = 0

            def fail_second(source, destination, **kwargs):
                nonlocal calls
                calls += 1
                if calls == 2:
                    raise OSError("injected failure")
                return real_link(source, destination, **kwargs)

            with mock.patch("agentic_bootstrap.apply.os.link", side_effect=fail_second):
                result = apply_bootstrap(prepared)
            self.assertFalse(result.applied)
            self.assertEqual("apply-failed", result.status)
            self.assertEqual("succeeded", result.rollback_status)
            self.assertFalse(root.exists())

    def test_manifest_is_labeled_as_unauthenticated_claim(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            req = request(root, ["pi"])
            prepared = prepare_bootstrap(req)
            apply_bootstrap(prepared)
            next_plan = prepare_bootstrap(req)
            self.assertEqual(
                "repository-supplied-unauthenticated-claim",
                next_plan.document["manifest_claim"]["provenance"],
            )


if __name__ == "__main__":
    unittest.main()
