from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from tools.local_llm_semantic_assist import (
    LocalLlmConfig,
    build_messages,
    load_contract,
    validate_proposals,
    write_outputs,
)


class LocalLlmSemanticAssistTests(unittest.TestCase):
    def test_build_messages_compacts_candidate_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "llm_plateau_input.json"
            path.write_text(
                json.dumps(
                    {
                        "policy": {"instruction": "test"},
                        "candidates": [
                            {
                                "property_id": "candidate_a",
                                "relation_names": ["semantic_field_flow"],
                                "relation_rows": [["module", "qual", "field"]],
                                "source_provenance": "static",
                                "reason": "needs a better oracle",
                                "symbol": "module.qual",
                                "related_facts": {"dataclass_field": [[str(i)] for i in range(8)]},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            contract = load_contract(path, max_candidates=1)
            messages = build_messages(contract)
            rendered = messages[-1]["content"]
            self.assertIn("candidate_a", rendered)
            self.assertIn("semantic_field_flow", rendered)
            self.assertNotIn('"7"', rendered)

    def test_validate_proposals_accepts_fenced_json_and_rejects_unknown_ids(self) -> None:
        model_text = """```json
{
  "tests": [
    {
      "property_id": "candidate_a",
      "test_id": "test_observes_candidate",
      "oracle_strength": "observational",
      "test_code": "def test_observes_candidate():\\n    assert True",
      "semantic_notes": "grounded in relation row"
    },
    {
      "property_id": "unknown",
      "test_id": "bad",
      "oracle_strength": "exact",
      "test_code": "def test_bad():\\n    assert True"
    }
  ]
}
```"""
        result = validate_proposals(model_text, {"candidate_a"})
        self.assertEqual(len(result.tests), 1)
        self.assertEqual(result.tests[0]["property_id"], "candidate_a")
        self.assertEqual(result.tests[0]["oracle_strength"], "observational")
        self.assertEqual(result.tests[0]["source"], "local_llm_semantic_assist")
        self.assertEqual(len(result.rejected), 1)

    def test_write_outputs_uses_llm_proposals_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output = root / "proposals.json"
            report = root / "report.md"
            result = validate_proposals(
                json.dumps(
                    {
                        "tests": [
                            {
                                "property_id": "candidate_a",
                                "test_id": "test_candidate",
                                "oracle_strength": "exact",
                                "test_code": "def test_candidate():\n    assert True",
                            }
                        ]
                    }
                ),
                {"candidate_a"},
            )
            write_outputs(
                output,
                report,
                result,
                config=LocalLlmConfig("ollama", "http://127.0.0.1:11434", "qwen-test"),
                input_path=root / "input.json",
            )
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["tests"][0]["property_id"], "candidate_a")
            self.assertIn("quarantined", payload["metadata"]["policy"])
            self.assertIn("qwen-test", report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
