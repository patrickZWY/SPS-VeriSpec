from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.llm_candidate_generation import collect_plateau_candidates, main as plateau_main


class LlmCandidateGenerationTests(unittest.TestCase):
    def test_collects_uncovered_and_weak_family_candidates(self) -> None:
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

            (facts / "dataclass.facts").write_text("m\tPet\t0\t1\n", encoding="utf-8")
            (facts / "dataclass_field.facts").write_text("m\tPet\tname\tstr\t0\t0\tmissing\t1\t2\n", encoding="utf-8")
            (test_out / "transform_required_field_test_target.csv").write_text(
                "\n".join(
                    [
                        "m\tPoster\tPoster.format_post\tPet\tname\tPost\ttext",
                        "m\tPoster\tPoster.format_post\tPet\tname\tPost\ttitle",
                    ]
                ),
                encoding="utf-8",
            )
            (test_out / "transform_optional_field_test_target.csv").write_text("", encoding="utf-8")
            (semantic / "numeric_bound.csv").write_text("", encoding="utf-8")
            (semantic / "dataclass_collection_iteration.csv").write_text("", encoding="utf-8")
            (semantic / "observable_output_slice.csv").write_text("", encoding="utf-8")

            (generated / "test_generated_dataclass_properties.py").write_text(
                "CASES = [\n"
                "    {\n"
                "        'class_module': 'm',\n"
                "        'class_name': 'Poster',\n"
                "        'method_name': 'format_post',\n"
                "        'source_class': 'Pet',\n"
                "        'source_field': 'name',\n"
                "        'target_arg': 'text',\n"
                "        'target_kind': 'required',\n"
                "        'assertion': 'observes',\n"
                "    }\n"
                "]\n",
                encoding="utf-8",
            )
            (generated / "test_generated_dataclass_schema.py").write_text(
                "SCHEMA_CASES = []\nCONSTRUCTOR_CASES = []\n",
                encoding="utf-8",
            )
            (generated / "test_generated_dataclass_conversions.py").write_text("CONVERSION_CASES = []\n", encoding="utf-8")
            (generated / "test_generated_helper_boundaries.py").write_text("HELPER_BOUNDARY_CASES = []\n", encoding="utf-8")
            (generated / "test_generated_common_ast_properties.py").write_text("COMMON_AST_CASES = []\n", encoding="utf-8")
            (generated / "test_generated_interprocedural_properties.py").write_text("INTERPROCEDURAL_CASES = []\n", encoding="utf-8")

            candidates = collect_plateau_candidates(analysis, generated, max_candidates=10)

            self.assertGreaterEqual(len(candidates), 2)
            reasons = [candidate.reason for candidate in candidates]
            self.assertTrue(any("uncovered relation" in reason for reason in reasons))
            self.assertTrue(any("weak or observational oracles" in reason for reason in reasons))

    def test_main_writes_input_contract_and_manifest_from_proposals(self) -> None:
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

            (facts / "dataclass.facts").write_text("m\tPet\t0\t1\n", encoding="utf-8")
            (facts / "dataclass_field.facts").write_text("m\tPet\tname\tstr\t0\t0\tmissing\t1\t2\n", encoding="utf-8")
            (test_out / "transform_required_field_test_target.csv").write_text(
                "m\tPoster\tPoster.format_post\tPet\tname\tPost\ttext\n",
                encoding="utf-8",
            )
            (test_out / "transform_optional_field_test_target.csv").write_text("", encoding="utf-8")
            (semantic / "numeric_bound.csv").write_text("", encoding="utf-8")
            (semantic / "dataclass_collection_iteration.csv").write_text("", encoding="utf-8")
            (semantic / "observable_output_slice.csv").write_text("", encoding="utf-8")
            (generated / "test_generated_dataclass_properties.py").write_text("CASES = []\n", encoding="utf-8")
            (generated / "test_generated_dataclass_schema.py").write_text(
                "SCHEMA_CASES = []\nCONSTRUCTOR_CASES = []\n",
                encoding="utf-8",
            )
            (generated / "test_generated_dataclass_conversions.py").write_text("CONVERSION_CASES = []\n", encoding="utf-8")
            (generated / "test_generated_helper_boundaries.py").write_text("HELPER_BOUNDARY_CASES = []\n", encoding="utf-8")
            (generated / "test_generated_common_ast_properties.py").write_text("COMMON_AST_CASES = []\n", encoding="utf-8")
            (generated / "test_generated_interprocedural_properties.py").write_text("INTERPROCEDURAL_CASES = []\n", encoding="utf-8")

            candidates = collect_plateau_candidates(analysis, generated, max_candidates=10)
            self.assertEqual(len(candidates), 1)

            proposal_path = root / "proposal.json"
            proposal_path.write_text(
                json.dumps(
                    {
                        "tests": [
                            {
                                "property_id": candidates[0].property_id,
                                "test_id": "plateau_candidate",
                                "oracle_strength": "observational",
                                "test_code": "def test_plateau_candidate():\n    assert True",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            import sys

            previous_argv = sys.argv
            sys.argv = [
                "llm_candidate_generation.py",
                "--analysis-dir",
                str(analysis),
                "--generated-tests",
                str(generated),
                "--output-dir",
                str(root / "out"),
                "--llm-proposals",
                str(proposal_path),
            ]
            try:
                plateau_main()
            finally:
                sys.argv = previous_argv

            out_dir = root / "out"
            input_path = out_dir / "llm_plateau_input.json"
            manifest_path = out_dir / "llm_plateau_candidates.json"
            test_path = out_dir / "test_generated_llm_plateau_candidates.py"

            self.assertTrue(input_path.exists())
            self.assertTrue(manifest_path.exists())
            self.assertTrue(test_path.exists())
            payload = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(len(payload["candidates"]), 1)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["oracle_candidates"][0]["classification"], "needs_review")
            self.assertIn("plateau_candidate", test_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
