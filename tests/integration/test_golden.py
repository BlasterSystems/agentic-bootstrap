from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import json

from agentic_bootstrap.model import BootstrapRequest, FeatureSelection, ProjectFacts
from agentic_bootstrap.renderer import render_project
from tests.helpers import request

ROOT = Path(__file__).resolve().parents[2]


class GoldenTreeTests(unittest.TestCase):
    def assert_example_matches_renderer(self, relative: str) -> None:
        example = ROOT / relative
        config = json.loads((example / ".agentic/config.json").read_text(encoding="utf-8"))
        project = config["project"]
        requested = config["features"]["requested"]
        req = BootstrapRequest(
            target=example,
            mode="init",
            facts=ProjectFacts(
                name=project["name"],
                description=project.get("description") or "",
                languages=project.get("languages", []),
                build_command=project.get("commands", {}).get("build"),
                test_command=project.get("commands", {}).get("test"),
                run_command=project.get("commands", {}).get("run"),
                ticket_prefix=project.get("ticket_prefix"),
                components=project.get("components", []),
            ),
            features=FeatureSelection(
                platforms=requested["platforms"],
                mcp=requested["mcp"],
                agents=requested["agents"],
                github=requested["github"],
                scheduled_audit=requested.get("scheduled_audit", False),
                hooks=requested["hooks"],
            ),
        )
        desired = render_project(req)
        actual_paths = {
            path.relative_to(example).as_posix()
            for path in example.rglob("*")
            if path.is_file() and path.relative_to(example).as_posix() != ".agentic/manifest.json"
        }
        self.assertEqual(set(desired), actual_paths)
        for path, generated in desired.items():
            self.assertEqual(generated.content, (example / path).read_bytes(), path)

    def test_all_platform_tree_matches_golden(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            files = render_project(
                request(Path(directory), mcp=True, agents=True, github=True, hooks=True)
            )
            actual = "\n".join(sorted(files)) + "\n"
            expected = (ROOT / "tests/golden/all-platforms/tree.txt").read_text(encoding="utf-8")
            self.assertEqual(expected, actual)
            output_doc = (ROOT / "docs/GENERATED_OUTPUT.md").read_text(encoding="utf-8")
            documented = output_doc.split("```text\n", 1)[1].split("```", 1)[0]
            self.assertEqual(expected, documented)

    def test_checked_in_examples_match_renderer_content(self) -> None:
        self.assert_example_matches_renderer("examples/minimal")
        self.assert_example_matches_renderer("examples/all-platforms")


if __name__ == "__main__":
    unittest.main()
