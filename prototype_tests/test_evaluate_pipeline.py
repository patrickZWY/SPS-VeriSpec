from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tools.evaluate_pipeline import StepResult, main as pipeline_main, write_reports


class EvaluatePipelineTests(unittest.TestCase):
    def test_write_reports_records_enabled_and_disabled_steps(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            markdown = root / "pipeline.md"
            json_report = root / "pipeline.json"
            write_reports(
                markdown,
                json_report,
                [
                    StepResult("static_analysis", ["python", "run_static_analysis.py"], 0, ["/tmp/summary.md"], True),
                    StepResult("mutation_eval", [], 0, [], False),
                ],
            )
            rendered = markdown.read_text(encoding="utf-8")
            self.assertIn("static_analysis", rendered)
            self.assertIn("mutation_eval", rendered)
            self.assertIn("disabled", rendered)
            payload = json.loads(json_report.read_text(encoding="utf-8"))
            self.assertEqual(payload["steps"][0]["name"], "static_analysis")

    def test_main_orchestrates_expected_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            target = root / "target"
            target.mkdir()
            proposal = root / "proposal.json"
            proposal.write_text('{"tests":[]}', encoding="utf-8")
            calls: list[list[str]] = []

            def fake_run(command, check, text, stdout, stderr, cwd):
                calls.append(command)

                class Completed:
                    returncode = 0
                    stdout = "/tmp/output.md\n"

                return Completed()

            import sys

            previous_argv = sys.argv
            sys.argv = [
                "evaluate_pipeline.py",
                "--target-project",
                str(target),
                "--project-name",
                "sample_project",
                "--work-dir",
                str(root / "work"),
                "--skip-mutation",
                "--with-static-metamorphic",
                "--with-plateau",
                "--llm-proposals",
                str(proposal),
            ]
            try:
                with patch("tools.evaluate_pipeline.subprocess.run", side_effect=fake_run):
                    with self.assertRaises(SystemExit) as exc:
                        pipeline_main()
            finally:
                sys.argv = previous_argv

            self.assertEqual(exc.exception.code, 0)
            joined = [" ".join(command) for command in calls]
            self.assertTrue(any("run_static_analysis.py" in command for command in joined))
            self.assertTrue(any("generate_pytest_from_properties.py" in command for command in joined))
            self.assertTrue(any("validate_generated_tests.py" in command for command in joined))
            self.assertTrue(any("generator_coverage.py" in command for command in joined))
            self.assertTrue(any("evaluation_stats.py" in command for command in joined))
            self.assertTrue(any("metamorphic_eval_static_analysis.py" in command for command in joined))
            self.assertTrue(any("llm_candidate_generation.py" in command for command in joined))


if __name__ == "__main__":
    unittest.main()
