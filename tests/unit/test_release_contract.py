from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import stat
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

from agentic_bootstrap import __version__
from agentic_bootstrap.manifest import Manifest


ROOT = Path(__file__).resolve().parents[2]


def load_sync_version_module():
    path = ROOT / "scripts/sync-version.py"
    spec = importlib.util.spec_from_file_location("sync_version", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseContractTests(unittest.TestCase):
    def test_authoritative_versions_and_changelog_match(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(__version__, pyproject["project"]["version"])
        self.assertEqual(__version__, Manifest().generator_version)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## [{__version__}]", changelog)

        root_config = json.loads((ROOT / ".agentic/config.json").read_text(encoding="utf-8"))
        self.assertEqual(__version__, root_config["generator_version"])
        sync = ROOT / "scripts/sync-version.py"
        self.assertTrue(os.access(sync, os.X_OK))
        check = subprocess.run(
            [sys.executable, str(sync), "--check"], cwd=ROOT,
            text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            timeout=30, check=False,
        )
        self.assertEqual(0, check.returncode, check.stdout)

        for relative in ("examples/minimal", "examples/all-platforms"):
            example = ROOT / relative
            manifest = json.loads(
                (example / ".agentic/manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(__version__, manifest["generator_version"])
            validation = subprocess.run(
                [str(example / ".agentic/bin/validate")], cwd=example,
                text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                timeout=30, check=False,
            )
            self.assertEqual(0, validation.returncode, validation.stdout)

    def test_sync_version_writes_atomically_and_ignores_predictable_symlink(self) -> None:
        module = load_sync_version_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agentic = root / ".agentic"
            agentic.mkdir()
            config = agentic / "config.json"
            config.write_text('{"generator_version": "0.0.0"}\n', encoding="utf-8")
            config.chmod(0o640)

            external = root / "external.txt"
            external.write_text("external\n", encoding="utf-8")
            predictable = agentic / "config.json.tmp"
            predictable.symlink_to(external)

            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                result = module.synchronize(root, "9.8.7", check=False)

            self.assertEqual(0, result, output.getvalue())
            self.assertEqual(
                "9.8.7",
                json.loads(config.read_text(encoding="utf-8"))["generator_version"],
            )
            self.assertEqual(0o640, stat.S_IMODE(config.stat().st_mode))
            self.assertEqual("external\n", external.read_text(encoding="utf-8"))
            self.assertTrue(predictable.is_symlink())
            self.assertEqual([], list(agentic.glob(".config.json.*.tmp")))

    def test_sync_version_rejects_symlink_destination(self) -> None:
        module = load_sync_version_module()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            agentic = root / ".agentic"
            agentic.mkdir()
            external = root / "external.json"
            external.write_text('{"generator_version": "0.0.0"}\n', encoding="utf-8")
            (agentic / "config.json").symlink_to(external)

            output = io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
                result = module.synchronize(root, "9.8.7", check=False)

            self.assertEqual(1, result)
            self.assertIn("must be a regular file", output.getvalue())
            self.assertEqual(
                "0.0.0",
                json.loads(external.read_text(encoding="utf-8"))["generator_version"],
            )

    def test_release_example_refreshes_prune_obsolete_owned_files(self) -> None:
        releasing = (ROOT / "docs/RELEASING.md").read_text(encoding="utf-8")
        self.assertEqual(2, releasing.count("--remove-obsolete"))

    def test_preview_command_cleans_up_and_preserves_failure_status(self) -> None:
        instructions = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("(\n  set -e", instructions)
        self.assertIn("trap 'rmdir \"$preview_target\"' EXIT", instructions)
        self.assertNotIn("rmdir \"$preview_target\"\n```", instructions)

    def test_shared_release_skill_is_identical_and_confirmation_gated(self) -> None:
        template = (
            ROOT / "src/agentic_bootstrap/templates/core/skills/semantic-versioning/SKILL.md"
        ).read_text(encoding="utf-8")
        self.assertEqual(
            template,
            (ROOT / ".agents/skills/semantic-versioning/SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertEqual(
            template,
            (ROOT / ".claude/skills/semantic-versioning/SKILL.md").read_text(encoding="utf-8"),
        )
        self.assertIn("explicit human confirmation", template)
        self.assertIn("Never push commits, tags, or packages", template)
        self.assertIn('git tag -a "vX.Y.Z"', template)


if __name__ == "__main__":
    unittest.main()
