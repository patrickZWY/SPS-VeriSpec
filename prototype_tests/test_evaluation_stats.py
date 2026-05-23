from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.evaluation_stats import (
    CoverageTotals,
    line_delta,
    percent_delta,
    relation_stats,
    svg_bar_chart,
    svg_stacked_bar,
)


class EvaluationStatsTests(unittest.TestCase):
    def test_relation_stats_counts_generated_cases_and_relations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            analysis = root / "analysis"
            generated = root / "generated"
            (analysis / "test_out").mkdir(parents=True)
            (analysis / "semantic_out").mkdir()
            generated.mkdir()

            (analysis / "test_out" / "transform_required_field_test_target.csv").write_text(
                "m\tPoster\tPoster.format_post\tPet\tname\tPost\ttext\n",
                encoding="utf-8",
            )
            (analysis / "test_out" / "transform_optional_field_test_target.csv").write_text(
                "m\tPoster\tPoster.format_post\tPet\turl\tPost\tlink\n",
                encoding="utf-8",
            )
            (analysis / "semantic_out" / "numeric_bound.csv").write_text(
                "m\tPoster._clean\tlen(text)\tlower_exclusive\t10\t5\n",
                encoding="utf-8",
            )
            cases = """CASES = [
    {
        'class_module': 'm',
        'class_name': 'Poster',
        'method_name': 'format_post',
        'source_class': 'Pet',
        'source_field': 'name',
        'target_arg': 'text',
    }
]
"""
            (generated / "test_generated_dataclass_properties.py").write_text(cases, encoding="utf-8")
            (generated / "test_generated_dataclass_hypothesis.py").write_text(cases, encoding="utf-8")
            (generated / "test_generated_helper_boundaries.py").write_text(
                "HELPER_BOUNDARY_CASES = [{'id': 'one'}]\n",
                encoding="utf-8",
            )

            stats = relation_stats(analysis, generated)

            self.assertEqual(stats.transform_targets, 2)
            self.assertEqual(stats.unique_transform_relations_tested, 1)
            self.assertEqual(stats.example_cases, 1)
            self.assertEqual(stats.hypothesis_cases, 1)
            self.assertEqual(stats.helper_boundary_candidates, 1)
            self.assertEqual(stats.helper_boundary_cases, 1)

    def test_coverage_deltas(self) -> None:
        old = CoverageTotals(covered_lines=10, executable_lines=100, percent=10.0, returncode=0)
        new = CoverageTotals(covered_lines=25, executable_lines=100, percent=25.0, returncode=0)

        self.assertEqual(line_delta(new, old), 15)
        self.assertEqual(percent_delta(new, old), 15.0)

    def test_svg_helpers_emit_inline_svg(self) -> None:
        bar = svg_bar_chart("Coverage", [("Generated", 28.5, "28.5%")])
        stacked = svg_stacked_bar("Composition", [("Examples", 32, "#2563eb")])

        self.assertIn("<svg", bar)
        self.assertIn("Coverage", bar)
        self.assertIn("Generated", bar)
        self.assertIn("<svg", stacked)
        self.assertIn("Composition", stacked)


if __name__ == "__main__":
    unittest.main()
