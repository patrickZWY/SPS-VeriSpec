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
                        "sample\tclean\tlen(text)\tlower_exclusive\t500\t2",
                        "sample\tclean\ttext\tupper_exclusive\t497\t3",
                    ]
                ),
                encoding="utf-8",
            )
            (analysis / "facts" / "field_flows_to_constructor_arg.facts").write_text(
                "sample\tPoster.format_post\tpet\tname\tPost\ttext\t4\n",
                encoding="utf-8",
            )
            (target / "sample.py").write_text(
                "\n".join(
                    [
                        "def clean(text):",
                        "    if len(text) > 500:",
                        "        return text[:497] + \"...\"",
                        "    text = pet.name",
                        "    return text",
                    ]
                ),
                encoding="utf-8",
            )

            mutants = generate_mutants(analysis, target, max_mutants=12)

            self.assertTrue(any(mutant.operator == "field_reference_replace" for mutant in mutants))
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
