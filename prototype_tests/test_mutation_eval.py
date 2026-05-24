from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.mutation_eval import generate_mutants, score


class MutationEvalTests(unittest.TestCase):
    def test_generate_mutants_from_numeric_bound_facts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            analysis = root / "analysis"
            target = root / "target"
            (analysis / "facts").mkdir(parents=True)
            (analysis / "semantic_out").mkdir()
            target.mkdir()
            (target / "sample.py").write_text(
                "\n".join(
                    [
                        "def clean(text):",
                        "    if len(text) > 500:",
                        "        return text[:497] + \"...\"",
                        "    return text",
                    ]
                ),
                encoding="utf-8",
            )
            (analysis / "facts" / "module_file.facts").write_text(
                "sample\tsample.py\n",
                encoding="utf-8",
            )
            (analysis / "semantic_out" / "numeric_bound.csv").write_text(
                "\n".join(
                    [
                        "sample\tclean\tlen(text)\tlower_exclusive\t500\t8",
                        "sample\tclean\ttext\tupper_exclusive\t497\t9",
                    ]
                ),
                encoding="utf-8",
            )
            (analysis / "facts" / "field_flows_to_constructor_arg.facts").write_text(
                "sample\tPoster.format_post\tpet\tname\tPost\ttext\t10\n",
                encoding="utf-8",
            )
            (analysis / "semantic_out" / "dataclass_collection_iteration.csv").write_text(
                "sample\tformat_tags\tsample\tPost\ttags\ttag\tcomprehension\n",
                encoding="utf-8",
            )
            (analysis / "semantic_out" / "multi_hop_interprocedural_field_flow.csv").write_text(
                "sample\tPet\tname\tsample\tCaptionThread\tmain_caption\n",
                encoding="utf-8",
            )
            (analysis / "test_out").mkdir()
            (analysis / "test_out" / "method_dataclass_transform.csv").write_text(
                "sample\tPoster\tPoster.build_formatting_pipeline\tsample\tPet\tsample\tCaptionThread\n",
                encoding="utf-8",
            )
            (target / "sample.py").write_text(
                "\n".join(
                    [
                        "class Post: pass",
                        "class PreparedCaption: pass",
                        "class Poster:",
                        "    def build_formatting_pipeline(self, pet):",
                        "        pipeline = self.format_post",
                        "        pipeline = self._prepare_caption",
                        "def clean(text):",
                        "    if len(text) > 500:",
                        "        return text[:497] + \"...\"",
                        "    text = pet.name",
                        "    tags = [f'#{tag}' for tag in post.tags if tag]",
                        "    return text",
                    ]
                ),
                encoding="utf-8",
            )

            mutants = generate_mutants(analysis, target, max_mutants=20)

            self.assertTrue(any(mutant.operator == "field_reference_replace" for mutant in mutants))
            self.assertTrue(any(mutant.operator == "collection_iteration_replace" for mutant in mutants))
            self.assertTrue(any(mutant.operator == "interprocedural_pipeline_replace" for mutant in mutants))
            self.assertTrue(any(mutant.operator == "operator_replace" for mutant in mutants))
            self.assertTrue(any(mutant.operator == "constant_replace" for mutant in mutants))
            self.assertTrue(any(mutant.operator == "string_literal_replace" for mutant in mutants))

    def test_score_counts_killed_mutants(self) -> None:
        results = [
            {"target": {"killed": True}},
            {"target": {"killed": False}},
            {"target": {"killed": True}},
        ]

        killed, total, percent = score(results, "target")
        self.assertEqual((killed, total), (2, 3))
        self.assertAlmostEqual(percent, 100 * 2 / 3)


if __name__ == "__main__":
    unittest.main()
