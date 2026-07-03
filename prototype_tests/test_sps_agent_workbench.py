from __future__ import annotations

import sys
import tempfile
import time
import unittest
from pathlib import Path

from sps_agent.cases import (
    CaseNotFound,
    LiveRunRejected,
    artifact_text,
    case_detail,
    list_cases,
    run_command_with_limits,
    run_live_case,
)
from sps_agent.server import is_local_request


class SpsAgentWorkbenchTests(unittest.TestCase):
    def test_manifest_lists_expected_replay_cases(self) -> None:
        cases = {case["id"]: case for case in list_cases()}
        self.assertEqual(
            set(cases),
            {"cutepetsboston", "dacite", "transformers", "type_checker_case_study"},
        )
        self.assertEqual(cases["cutepetsboston"]["validation"]["passed"], 73)
        self.assertTrue(cases["cutepetsboston"]["live_enabled"])
        self.assertFalse(cases["transformers"]["live_enabled"])

    def test_graph_shape_for_each_curated_case(self) -> None:
        for case_id in ["cutepetsboston", "dacite", "transformers", "type_checker_case_study"]:
            with self.subTest(case_id=case_id):
                payload = case_detail(case_id)
                self.assertEqual(payload["case"]["id"], case_id)
                self.assertTrue(payload["nodes"])
                self.assertTrue(payload["edges"])
                self.assertIn("families", payload["metrics"])
                self.assertIn("validation", payload["metrics"])
                self.assertTrue(payload["artifacts"])
                self.assertTrue(any(node["kind"] == "validation" for node in payload["nodes"]))

        cute = case_detail("cutepetsboston")
        self.assertEqual(cute["metrics"]["families"]["transform_required_field"]["emitted_tests"], 20)
        self.assertEqual(cute["metrics"]["validation"]["passed"], 73)

        dacite = case_detail("dacite")
        self.assertEqual(dacite["metrics"]["families"]["conversion_profile"]["emitted_tests"], 1)

        type_checker = case_detail("type_checker_case_study")
        self.assertTrue(any(node["kind"] == "finding" for node in type_checker["nodes"]))
        self.assertEqual(type_checker["metrics"]["totals"]["review_findings"], 224)

    def test_artifact_access_is_case_scoped(self) -> None:
        path, text = artifact_text("cutepetsboston", "validation_report")
        self.assertEqual(path, "generated_tests/cutepetsboston/validation_report.md")
        self.assertIn("73 passed", text)
        with self.assertRaises(CaseNotFound):
            artifact_text("cutepetsboston", "../README.md")

    def test_live_run_rejects_non_allowlisted_targets(self) -> None:
        with self.assertRaises(LiveRunRejected):
            run_live_case("transformers")

    def test_live_run_host_guard_rejects_tunneled_hosts(self) -> None:
        self.assertTrue(is_local_request("127.0.0.1", "127.0.0.1:8765"))
        self.assertTrue(is_local_request("::1", "[::1]:8765"))
        self.assertFalse(is_local_request("127.0.0.1", "sps-demo.zhengwangyuan-patrick.com"))
        self.assertFalse(is_local_request("203.0.113.10", "127.0.0.1:8765"))

    def test_command_timeout_and_output_truncation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_command_with_limits(
                [
                    sys.executable,
                    "-c",
                    "import time; print('begin', flush=True); time.sleep(2)",
                ],
                cwd=Path(temp_dir),
                timeout_seconds=1,
                output_limit=1000,
            )
            self.assertTrue(result.timed_out)
            self.assertEqual(result.returncode, 124)
            self.assertIn("timed out", result.output)

            noisy = run_command_with_limits(
                [sys.executable, "-c", "print('x' * 2000)"],
                cwd=Path(temp_dir),
                timeout_seconds=5,
                output_limit=120,
            )
            self.assertFalse(noisy.timed_out)
            self.assertTrue(noisy.truncated)
            self.assertLessEqual(len(noisy.output), 140)


if __name__ == "__main__":
    unittest.main()
