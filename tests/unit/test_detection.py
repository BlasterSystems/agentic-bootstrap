from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from agentic_bootstrap.detection import detect_project


class DetectionTests(unittest.TestCase):
    def test_node_scripts_become_package_manager_commands(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package.json").write_text(
                json.dumps({"scripts": {"build": "tsc", "test": "vitest", "dev": "vite"}}),
                encoding="utf-8",
            )
            (root / "tsconfig.json").write_text("{}", encoding="utf-8")
            (root / "pnpm-lock.yaml").write_text("", encoding="utf-8")
            facts = detect_project(root)
            self.assertIn("TypeScript", facts.languages)
            self.assertEqual("pnpm build", facts.build_command)
            self.assertEqual("pnpm test", facts.test_command)
            self.assertEqual("pnpm dev", facts.run_command)

    def test_multilanguage_detection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "go.mod").write_text("module example.test\n", encoding="utf-8")
            (root / "pyproject.toml").write_text("[project]\nname='x'\n", encoding="utf-8")
            facts = detect_project(root)
            self.assertEqual(["Python", "Go"], facts.languages)
            self.assertEqual(["python", "go"], facts.components)

    def test_unknown_values_remain_unconfigured(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            facts = detect_project(Path(directory))
            self.assertEqual([], facts.languages)
            self.assertIsNone(facts.build_command)
            self.assertIsNone(facts.ticket_prefix)


if __name__ == "__main__":
    unittest.main()
