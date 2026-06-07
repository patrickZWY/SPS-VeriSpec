from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.generator_coverage import build_family_coverage


class GeneratorCoverageTests(unittest.TestCase):
    def test_build_family_coverage_counts_families_and_oracle_strength(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            analysis = root / "analysis"
            facts = analysis / "facts"
            test_out = analysis / "test_out"
            semantic = analysis / "semantic_out"
            generated = root / "generated"
            facts.mkdir(parents=True)
            test_out.mkdir()
            semantic.mkdir()
            generated.mkdir()

            (facts / "dataclass.facts").write_text("m\tPet\t0\t1\nm\tPost\t0\t5\n", encoding="utf-8")
            (facts / "dataclass_field.facts").write_text(
                "\n".join(
                    [
                        "m\tPet\tname\tstr\t0\t0\tmissing\t1\t2",
                        "m\tPet\ttags\tlist[str]\t0\t1\tfactory\t2\t3",
                        "m\tPost\ttext\tstr\t0\t0\tmissing\t1\t6",
                    ]
                ),
                encoding="utf-8",
            )
            (facts / "function_name.facts").write_text("m\tfrom_dict\tfrom_dict\n", encoding="utf-8")
            (facts / "method_of_class.facts").write_text("", encoding="utf-8")
            (test_out / "transform_required_field_test_target.csv").write_text(
                "m\tPoster\tPoster.format_post\tPet\tname\tPost\ttext\n",
                encoding="utf-8",
            )
            (test_out / "transform_optional_field_test_target.csv").write_text(
                "m\tPoster\tPoster.format_post\tPet\ttags\tPost\ttext\n",
                encoding="utf-8",
            )
            (semantic / "numeric_bound.csv").write_text(
                "m\tPoster._clean\tlen(text)\tlower_exclusive\t10\t5\n",
                encoding="utf-8",
            )
            (semantic / "dataclass_collection_iteration.csv").write_text(
                "m\tPoster.format_post\tm\tPet\ttags\ttag\tcomprehension\n",
                encoding="utf-8",
            )
            (semantic / "observable_output_slice.csv").write_text(
                "m\tPet\tname\tm\tPost\ttext\tstring_output\n",
                encoding="utf-8",
            )

            (generated / "test_generated_dataclass_properties.py").write_text(
                "CASES = [\n"
                "    {'target_kind': 'required', 'assertion': 'equals'},\n"
                "    {'target_kind': 'required', 'assertion': 'observes'},\n"
                "    {'target_kind': 'optional', 'assertion': 'equals'},\n"
                "]\n",
                encoding="utf-8",
            )
            (generated / "test_generated_dataclass_schema.py").write_text(
                "SCHEMA_CASES = [{'id': 'schema'}]\nCONSTRUCTOR_CASES = [{'id': 'ctor'}]\n",
                encoding="utf-8",
            )
            (generated / "test_generated_dataclass_conversions.py").write_text(
                "CONVERSION_CASES = [{'id': 'conv'}]\n",
                encoding="utf-8",
            )
            (generated / "test_generated_helper_boundaries.py").write_text(
                "HELPER_BOUNDARY_CASES = [{'id': 'helper_a'}, {'id': 'helper_b'}, {'id': 'helper_c'}]\n",
                encoding="utf-8",
            )
            (generated / "test_generated_common_ast_properties.py").write_text(
                "COMMON_AST_CASES = [{'id': 'ast'}]\n",
                encoding="utf-8",
            )
            (generated / "test_generated_interprocedural_properties.py").write_text(
                "INTERPROCEDURAL_CASES = [{'id': 'inter'}]\n",
                encoding="utf-8",
            )

            families = {family.name: family for family in build_family_coverage(analysis, generated)}

            self.assertEqual(families["dataclass_schema"].discovered, 2)
            self.assertEqual(families["dataclass_constructor"].emitted, 1)
            self.assertEqual(families["conversion_profile"].emitted, 1)
            self.assertEqual(families["transform_required_field"].emitted, 1)
            self.assertEqual(families["transform_required_field"].emitted_cases, 2)
            self.assertEqual(families["transform_required_field"].strict_oracle, 1)
            self.assertEqual(families["transform_required_field"].weak_oracle, 1)
            self.assertEqual(families["transform_optional_field"].emitted, 1)
            self.assertEqual(families["helper_boundary"].emitted, 1)
            self.assertEqual(families["helper_boundary"].emitted_cases, 3)
            self.assertEqual(families["common_ast_collection_iteration"].weak_oracle, 1)
            self.assertEqual(families["interprocedural_observable_slice"].emitted, 1)


if __name__ == "__main__":
    unittest.main()
