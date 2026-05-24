from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.generate_pytest_from_properties import main as generate_main
from tools.validate_generated_tests import parse_pytest_counts


class GeneratePytestFromPropertiesTests(unittest.TestCase):
    def test_generator_writes_example_hypothesis_and_report_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            analysis_dir = root / "analysis"
            facts_dir = analysis_dir / "facts"
            test_dir = analysis_dir / "test_out"
            output_dir = root / "generated"
            facts_dir.mkdir(parents=True)
            test_dir.mkdir(parents=True)

            (facts_dir / "dataclass_field.facts").write_text(
                "\n".join(
                    [
                        "sample\tPet\tname\tstr\t0\t0\tmissing\t1\t4",
                        "sample\tPet\ttags\tlist[str]\t0\t1\tfactory\t2\t5",
                        "sample\tPost\ttext\tstr\t0\t0\tmissing\t1\t8",
                    ]
                ),
                encoding="utf-8",
            )
            (facts_dir / "function_param.facts").write_text(
                "\n".join(
                    [
                        "sample\tPoster._clean_text\tself\t\t1\t20",
                        "sample\tPoster._clean_text\ttext\tstr\t2\t20",
                        "sample\tPoster.format_post\tself\t\t1\t30",
                        "sample\tPoster.format_post\tpet\tPet\t2\t30",
                    ]
                ),
                encoding="utf-8",
            )
            (facts_dir / "method_of_class.facts").write_text(
                "sample\tPoster\tPoster._clean_text\nsample\tPoster\tPoster.format_post\n",
                encoding="utf-8",
            )
            (facts_dir / "resolved_param_type_ref.facts").write_text(
                "sample\tPoster.format_post\tpet\tsample\tPet\n",
                encoding="utf-8",
            )
            (analysis_dir / "semantic_out").mkdir()
            (analysis_dir / "semantic_out" / "numeric_bound.csv").write_text(
                "sample\tPoster._clean_text\tlen(text)\tlower_exclusive\t10\t22\n",
                encoding="utf-8",
            )
            (analysis_dir / "semantic_out" / "dataclass_collection_iteration.csv").write_text(
                "sample\tPoster.format_post\tsample\tPet\ttags\ttag\tcomprehension\n",
                encoding="utf-8",
            )
            (analysis_dir / "semantic_out" / "asserted_dataclass_field.csv").write_text(
                "sample\tPoster.format_post\tsample\tPet\tname\tpet.name\n",
                encoding="utf-8",
            )
            (analysis_dir / "semantic_out" / "multi_hop_interprocedural_field_flow.csv").write_text(
                "sample\tPet\tname\tsample\tPost\ttext\n",
                encoding="utf-8",
            )
            (analysis_dir / "semantic_out" / "observable_output_slice.csv").write_text(
                "sample\tPet\tname\tsample\tPost\ttext\tstring_output\n",
                encoding="utf-8",
            )
            (test_dir / "method_dataclass_transform.csv").write_text(
                "sample\tPoster\tPoster.format_post\tsample\tPet\tsample\tPost\n",
                encoding="utf-8",
            )
            (test_dir / "transform_required_field_test_target.csv").write_text(
                "sample\tPoster\tPoster.format_post\tPet\tname\tPost\ttext\n",
                encoding="utf-8",
            )
            (test_dir / "transform_optional_field_test_target.csv").write_text(
                "",
                encoding="utf-8",
            )

            import sys

            previous_argv = sys.argv
            sys.argv = [
                "generate_pytest_from_properties.py",
                "--analysis-dir",
                str(analysis_dir),
                "--output-dir",
                str(output_dir),
                "--project-name",
                "sample_project",
            ]
            try:
                generate_main()
            finally:
                sys.argv = previous_argv

            project_dir = output_dir / "sample_project"
            example_test = project_dir / "test_generated_dataclass_properties.py"
            hypothesis_test = project_dir / "test_generated_dataclass_hypothesis.py"
            helper_boundary_test = project_dir / "test_generated_helper_boundaries.py"
            common_ast_test = project_dir / "test_generated_common_ast_properties.py"
            interprocedural_test = project_dir / "test_generated_interprocedural_properties.py"
            report = project_dir / "README.md"

            self.assertTrue(example_test.exists())
            self.assertTrue(hypothesis_test.exists())
            self.assertTrue(helper_boundary_test.exists())
            self.assertTrue(common_ast_test.exists())
            self.assertTrue(interprocedural_test.exists())
            self.assertTrue(report.exists())
            self.assertIn("'source_type': 'str'", example_test.read_text(encoding="utf-8"))
            self.assertIn("from hypothesis import", hypothesis_test.read_text(encoding="utf-8"))
            self.assertIn("HELPER_BOUNDARY_CASES", helper_boundary_test.read_text(encoding="utf-8"))
            self.assertIn("COMMON_AST_CASES", common_ast_test.read_text(encoding="utf-8"))
            self.assertIn("INTERPROCEDURAL_CASES", interprocedural_test.read_text(encoding="utf-8"))
            self.assertIn("Hypothesis test file", report.read_text(encoding="utf-8"))
            self.assertIn("Helper boundary test file", report.read_text(encoding="utf-8"))
            self.assertIn("Common-AST test file", report.read_text(encoding="utf-8"))
            self.assertIn("Interprocedural test file", report.read_text(encoding="utf-8"))

    def test_parse_pytest_counts_handles_common_summary(self) -> None:
        counts = parse_pytest_counts("12 passed, 3 skipped, 1 failed, 2 errors in 0.42s")

        self.assertEqual(counts["passed"], 12)
        self.assertEqual(counts["skipped"], 3)
        self.assertEqual(counts["failed"], 1)
        self.assertEqual(counts["errors"], 2)


if __name__ == "__main__":
    unittest.main()
