from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from agentic_bootstrap.inspection import inspect_project
from agentic_bootstrap.paths import UnsafePathError


class InspectionTests(unittest.TestCase):
    def test_inspection_derives_facts_without_raw_snippets_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(
                json.dumps({"scripts": {"build": "tsc", "test": "vitest"}}), encoding="utf-8"
            )
            (root / "pnpm-lock.yaml").write_text("", encoding="utf-8")
            artifact = inspect_project(root)
            payload = artifact.to_dict()
            self.assertEqual("untrusted-evidence", payload["authority"])
            self.assertEqual("pnpm build", payload["facts"]["build_command"])
            self.assertFalse(payload["raw_snippets_included"])
            self.assertTrue(all("snippet" not in item for item in payload["files"]))

    def test_raw_snippets_require_explicit_option_and_are_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "README.md").write_text("x" * 5000, encoding="utf-8")
            payload = inspect_project(root, include_snippets=True, max_bytes=10_000).to_dict()
            self.assertTrue(payload["raw_snippets_included"])
            self.assertLessEqual(len(payload["files"][0]["snippet"]), 2048)

    def test_secrets_binaries_symlinks_and_special_files_are_excluded(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            root = Path(directory)
            for relative in (
                ".env",
                ".envrc",
                ".yarnrc.yml",
                "server.key",
                "access-token.txt",
                "github_token.txt",
                "id_ecdsa",
            ):
                (root / relative).write_text("TOKEN=secret", encoding="utf-8")
            (root / ".Git").mkdir()
            (root / ".Git/config").write_text("credential=secret", encoding="utf-8")
            for generated in (".next", ".output", "generated", "target", "venv"):
                (root / generated).mkdir()
                (root / generated / "generated.txt").write_text("generated", encoding="utf-8")
            (root / "binary.bin").write_bytes(b"a\x00b")
            victim = Path(outside) / "victim.txt"
            victim.write_text("outside", encoding="utf-8")
            (root / "link.txt").symlink_to(victim)
            fifo = root / "pipe"
            if hasattr(os, "mkfifo"):
                os.mkfifo(fifo)
            payload = inspect_project(root, include_snippets=True).to_dict()
            paths = {item["path"] for item in payload["files"]}
            for relative in (
                ".env",
                ".envrc",
                ".yarnrc.yml",
                "server.key",
                "access-token.txt",
                "github_token.txt",
                "id_ecdsa",
                ".Git/config",
                ".next/generated.txt",
                ".output/generated.txt",
                "generated/generated.txt",
                "target/generated.txt",
                "venv/generated.txt",
            ):
                self.assertNotIn(relative, paths)
            self.assertNotIn("binary.bin", paths)
            self.assertNotIn("link.txt", paths)
            self.assertEqual("outside", victim.read_text(encoding="utf-8"))
            self.assertGreaterEqual(payload["exclusions"].get("secret-location", 0), 1)
            self.assertGreaterEqual(payload["exclusions"].get("symlink", 0), 1)

    def test_limits_report_truncation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(4):
                (root / f"{index}.txt").write_text("data", encoding="utf-8")
            payload = inspect_project(root, max_files=2, max_bytes=100).to_dict()
            self.assertTrue(payload["truncated"])
            self.assertEqual(2, len(payload["files"]))
            self.assertEqual(1, payload["exclusions"]["file-limit"])

    def test_directory_entry_budget_bounds_empty_tree_walks(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index in range(101):
                (root / f"dir-{index:03d}").mkdir()
            payload = inspect_project(root, max_files=1, max_bytes=100).to_dict()
            self.assertTrue(payload["truncated"])
            self.assertEqual(1, payload["exclusions"]["entry-limit"])
            self.assertEqual(100, payload["limits"]["max_entries"])

    def test_missing_root_is_not_created_and_symlink_root_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / "missing"
            payload = inspect_project(missing).to_dict()
            self.assertEqual("missing", payload["root_state"])
            self.assertFalse(missing.exists())
            link = Path(directory) / "link"
            link.symlink_to(Path(directory), target_is_directory=True)
            with self.assertRaises(UnsafePathError):
                inspect_project(link)

    def test_symlinked_target_ancestor_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory, tempfile.TemporaryDirectory() as outside:
            base = Path(directory)
            alias = base / "alias"
            alias.symlink_to(Path(outside), target_is_directory=True)
            with self.assertRaises(UnsafePathError):
                inspect_project(alias / "nested" / "project")
            self.assertFalse((Path(outside) / "nested" / "project").exists())


if __name__ == "__main__":
    unittest.main()
