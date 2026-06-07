from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tools.metamorphic_eval_static_analysis import (
    DEFAULT_RELATIONS,
    LocalRenameTransformer,
    evaluate_metamorphic_relations,
)


ROOT = Path(__file__).resolve().parents[1]


class LocalRenameTransformerTests(unittest.TestCase):
    def test_renames_function_bound_locals_but_not_parameters(self) -> None:
        source = "\n".join(
            [
                "def build(name: str) -> str:",
                "    value = name.strip()",
                "    alias = value.upper()",
                "    return alias",
                "",
            ]
        )
        tree = LocalRenameTransformer().visit(__import__("ast").parse(source))
        rendered = __import__("ast").unparse(tree)

        self.assertIn("name.strip()", rendered)
        self.assertIn("__sps_mr_1", rendered)
        self.assertIn("__sps_mr_2", rendered)
        self.assertNotIn("value =", rendered)
        self.assertNotIn("alias =", rendered)


@unittest.skipIf(shutil.which("souffle") is None, "souffle is not installed")
class StaticAnalysisMetamorphicTests(unittest.TestCase):
    def test_metamorphic_transforms_preserve_stable_relations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "sample_project"
            project.mkdir()
            (project / "pipeline.py").write_text(
                "\n".join(
                    [
                        "from dataclasses import dataclass",
                        "",
                        "@dataclass",
                        "class Source:",
                        "    raw: str",
                        "",
                        "@dataclass",
                        "class Mid:",
                        "    normalized: str",
                        "",
                        "@dataclass",
                        "class Output:",
                        "    label: str",
                        "",
                        "def normalize(source: Source) -> Mid:",
                        "    cleaned = source.raw.strip()",
                        "    if len(cleaned) > 8:",
                        "        cleaned = cleaned[:8]",
                        "    return Mid(normalized=cleaned)",
                        "",
                        "def render(mid: Mid) -> Output:",
                        "    label = f'Label: {mid.normalized}'",
                        "    return Output(label=label)",
                        "",
                        "class Pipeline:",
                        "    def process(self, source: Source) -> Output:",
                        "        mid = normalize(source)",
                        "        return render(mid)",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            results = evaluate_metamorphic_relations(
                project,
                root / "work",
                include_tests=False,
                transforms=[
                    "reorder_facts",
                    "duplicate_facts",
                    "add_unused_helper",
                    "local_rename",
                ],
                relations=list(DEFAULT_RELATIONS),
            )

            self.assertEqual([result.transform for result in results], [
                "reorder_facts",
                "duplicate_facts",
                "add_unused_helper",
                "local_rename",
            ])
            self.assertTrue(all(result.preserved for result in results))
            observed = {
                delta.relation
                for result in results
                for delta in result.deltas
            }
            expected = {f"{output_dir}/{filename}" for output_dir, filename in DEFAULT_RELATIONS}
            self.assertEqual(observed, expected)

    def test_json_report_shape_matches_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            project = root / "sample_project"
            project.mkdir()
            (project / "simple.py").write_text(
                "\n".join(
                    [
                        "from dataclasses import dataclass",
                        "",
                        "@dataclass",
                        "class Item:",
                        "    name: str",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            results = evaluate_metamorphic_relations(
                project,
                root / "work",
                include_tests=False,
                transforms=["reorder_facts"],
                relations=[("schema_out", "dataclass_shape.csv")],
            )
            payload = {
                "results": [
                    {
                        "transform": result.transform,
                        "preserved": result.preserved,
                        "deltas": [
                            {
                                "relation": delta.relation,
                                "baseline_count": delta.baseline_count,
                                "transformed_count": delta.transformed_count,
                                "preserved": delta.preserved,
                            }
                            for delta in result.deltas
                        ],
                    }
                    for result in results
                ]
            }

            encoded = json.dumps(payload)
            self.assertIn("reorder_facts", encoded)
            self.assertIn("schema_out/dataclass_shape.csv", encoded)


if __name__ == "__main__":
    unittest.main()
