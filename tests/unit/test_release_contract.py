from __future__ import annotations

import tomllib
import unittest
from pathlib import Path

from agentic_bootstrap import __version__
from agentic_bootstrap.manifest import Manifest


ROOT = Path(__file__).resolve().parents[2]


class ReleaseContractTests(unittest.TestCase):
    def test_authoritative_versions_and_changelog_match(self) -> None:
        pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(__version__, pyproject["project"]["version"])
        self.assertEqual(__version__, Manifest().generator_version)
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn(f"## [{__version__}]", changelog)

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
