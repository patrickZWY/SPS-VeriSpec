from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.mine_invariants import main as mine_main
from tools.validate_generated_tests import main as validate_main


class MineInvariantsTests(unittest.TestCase):
    def test_mines_quarantined_candidates_for_structured_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "project"
            project.mkdir()
            (project / "sample_api.py").write_text(
                "\n".join(
                    [
                        "from dataclasses import dataclass",
                        "",
                        "@dataclass",
                        "class Item:",
                        "    name: str",
                        "    tags: list[str]",
                        "",
                        "@dataclass",
                        "class Result:",
                        "    name: str",
                        "    tags: list[str]",
                        "",
                        "def build_result(item: Item) -> Result:",
                        "    return Result(name=item.name, tags=list(item.tags))",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            spec_path = root / "calls.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "calls": [
                            {
                                "id": "case_one",
                                "callable": "sample_api:build_result",
                                "args": [
                                    {
                                        "__dataclass__": "sample_api:Item",
                                        "fields": {"name": "alpha", "tags": ["a", "b"]},
                                    }
                                ],
                            },
                            {
                                "id": "case_two",
                                "callable": "sample_api:build_result",
                                "args": [
                                    {
                                        "__dataclass__": "sample_api:Item",
                                        "fields": {"name": "beta", "tags": ["x"]},
                                    }
                                ],
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            import sys

            previous_argv = sys.argv
            sys.argv = [
                "mine_invariants.py",
                "--spec",
                str(spec_path),
                "--target-project",
                str(project),
                "--output-dir",
                str(root / "generated"),
                "--project-name",
                "sample_project",
            ]
            try:
                mine_main()
            finally:
                sys.argv = previous_argv

            generated_root = root / "generated" / "sample_project"
            test_path = generated_root / "test_generated_invariant_candidates.py"
            manifest_path = generated_root / "invariant_candidates.json"
            report_path = generated_root / "invariant_candidates_report.md"

            self.assertTrue(test_path.exists())
            self.assertTrue(manifest_path.exists())
            self.assertTrue(report_path.exists())
            rendered = test_path.read_text(encoding="utf-8")
            self.assertIn("quarantined mined invariant candidate", rendered)
            self.assertIn("assert observed == expected", rendered)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertGreaterEqual(len(manifest["oracle_candidates"]), 4)
            reasons = [entry["reason"] for entry in manifest["oracle_candidates"]]
            self.assertTrue(any("equal to `args[0].name`" in reason for reason in reasons))

    def test_validation_promotes_passing_mined_candidates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "project"
            project.mkdir()
            (project / "sample_api.py").write_text(
                "\n".join(
                    [
                        "def build_payload(name: str, tags: list[str]) -> dict[str, object]:",
                        "    return {'name': name, 'tags': list(tags)}",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            spec_path = root / "calls.json"
            spec_path.write_text(
                json.dumps(
                    {
                        "calls": [
                            {
                                "id": "case_one",
                                "callable": "sample_api:build_payload",
                                "kwargs": {"name": "alpha", "tags": ["a", "b"]},
                            },
                            {
                                "id": "case_two",
                                "callable": "sample_api:build_payload",
                                "kwargs": {"name": "beta", "tags": ["x"]},
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            import sys

            previous_argv = sys.argv
            sys.argv = [
                "mine_invariants.py",
                "--spec",
                str(spec_path),
                "--target-project",
                str(project),
                "--output-dir",
                str(root / "generated"),
                "--project-name",
                "sample_project",
            ]
            try:
                mine_main()
            finally:
                sys.argv = previous_argv

            generated_root = root / "generated" / "sample_project"
            previous_argv = sys.argv
            sys.argv = [
                "validate_generated_tests.py",
                str(generated_root / "test_generated_invariant_candidates.py"),
                "--target-project",
                str(project),
                "--oracle-candidates-manifest",
                str(generated_root / "invariant_candidates.json"),
            ]
            try:
                validate_main()
            except SystemExit as exc:
                self.assertEqual(exc.code, 0)
            finally:
                sys.argv = previous_argv

            manifest = json.loads((generated_root / "invariant_candidates.json").read_text(encoding="utf-8"))
            self.assertTrue(manifest["oracle_candidates"])
            self.assertTrue(
                all(entry["classification"] == "promotion_candidate" for entry in manifest["oracle_candidates"])
            )


if __name__ == "__main__":
    unittest.main()
