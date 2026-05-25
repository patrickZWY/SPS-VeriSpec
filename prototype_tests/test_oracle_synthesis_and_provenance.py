from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.oracle_synthesis import (
    build_manifest_entries,
    collect_review_candidates,
    load_oracle_proposals,
    render_quarantined_oracle_tests,
    update_manifest_validation,
    write_llm_input_contract,
    write_manifest,
)
from tools.provenance import classify_relation_rows, combine_provenance
from tools.validate_generated_tests import classify_oracle_validation


class OracleSynthesisTests(unittest.TestCase):
    def test_manifest_generation_from_mocked_review_candidate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            analysis_dir = root / "analysis"
            semantic_dir = analysis_dir / "semantic_out"
            facts_dir = analysis_dir / "facts"
            semantic_dir.mkdir(parents=True)
            facts_dir.mkdir()
            (semantic_dir / "asserted_dataclass_field.csv").write_text(
                "sample\tPoster.render\tsample\tPet\tname\tpet.name\n",
                encoding="utf-8",
            )
            provenance_dir = analysis_dir / "provenance_out"
            provenance_dir.mkdir()
            (provenance_dir / "finding_provenance.csv").write_text(
                "\n".join(
                    [
                        "relation\tprovenance\trow_json",
                        'semantic.asserted_dataclass_field\tmixed\t["sample", "Poster.render", "sample", "Pet", "name", "pet.name"]',
                    ]
                ),
                encoding="utf-8",
            )
            (facts_dir / "function_param.facts").write_text(
                "sample\tPoster.render\tpet\tPet\t1\t10\n",
                encoding="utf-8",
            )

            candidates = collect_review_candidates(analysis_dir)
            self.assertEqual(len(candidates), 1)

            input_path = root / "llm_oracle_input.json"
            write_llm_input_contract(input_path, candidates)
            input_payload = json.loads(input_path.read_text(encoding="utf-8"))
            self.assertEqual(input_payload["candidates"][0]["source_provenance"], "mixed")
            self.assertIn("pytest_example", input_payload["policy"]["allowed_test_styles"])

            proposal_path = root / "proposal.json"
            proposal_path.write_text(
                json.dumps(
                    {
                        "tests": [
                            {
                                "property_id": candidates[0].property_id,
                                "test_id": "test_llm_candidate_observes_name",
                                "oracle_strength": "observational",
                                "test_code": "def test_llm_candidate_observes_name():\n    assert True",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            proposals = load_oracle_proposals(proposal_path)
            rendered = render_quarantined_oracle_tests(proposals)
            self.assertIn("pytest.mark.llm_oracle_candidate", rendered)
            self.assertIn("test_llm_candidate_observes_name", rendered)

            entries = build_manifest_entries(candidates, proposals, "test_generated_llm_oracle_candidates.py")
            manifest_path = root / "oracle_candidates.json"
            write_manifest(manifest_path, entries)
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["oracle_candidates"][0]["classification"], "needs_review")
            self.assertEqual(manifest["oracle_candidates"][0]["oracle_strength"], "observational")

    def test_failing_quarantined_validation_is_classified_as_conflict(self) -> None:
        validation_result, classification = classify_oracle_validation(
            1,
            {"passed": 0, "failed": 1, "skipped": 0, "xfailed": 0, "xpassed": 0, "errors": 0},
        )
        self.assertEqual(validation_result, "failed")
        self.assertEqual(classification, "design_conflict")

        with tempfile.TemporaryDirectory() as temp_dir:
            manifest_path = Path(temp_dir) / "oracle_candidates.json"
            manifest_path.write_text(
                json.dumps(
                    {
                        "oracle_candidates": [
                            {
                                "property_id": "p",
                                "validation_result": "not_run",
                                "classification": "needs_review",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            update_manifest_validation(manifest_path, "failed", "design_conflict")
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertEqual(manifest["oracle_candidates"][0]["validation_result"], "failed")
            self.assertEqual(manifest["oracle_candidates"][0]["classification"], "design_conflict")


class RuleProvenanceTests(unittest.TestCase):
    def test_provenance_propagation_for_static_llm_and_mixed_rows(self) -> None:
        findings = classify_relation_rows(
            {
                "finding": {
                    ("static_only",),
                    ("shared",),
                }
            },
            {
                "finding": {
                    ("llm_only",),
                    ("shared",),
                }
            },
        )
        provenance_by_row = {finding.row: finding.provenance for finding in findings}
        self.assertEqual(provenance_by_row[("static_only",)], "static")
        self.assertEqual(provenance_by_row[("llm_only",)], "llm")
        self.assertEqual(provenance_by_row[("shared",)], "mixed")
        self.assertEqual(combine_provenance(["static", "llm"]), "mixed")


if __name__ == "__main__":
    unittest.main()
