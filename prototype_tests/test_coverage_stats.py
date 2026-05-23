from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.coverage_stats import summarize_coverage


class CoverageStatsTests(unittest.TestCase):
    def test_summarizes_source_coverage_and_omits_tests_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            app = root / "app.py"
            tests_dir = root / "tests"
            test_file = tests_dir / "test_app.py"
            tests_dir.mkdir()
            app.write_text(
                "\n".join(
                    [
                        "def covered():",
                        "    return 1",
                        "",
                        "def missed():",
                        "    return 2",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            test_file.write_text("def test_placeholder():\n    assert True\n", encoding="utf-8")

            counts = {
                (str(app.resolve()), 1): 1,
                (str(app.resolve()), 2): 1,
                (str(test_file.resolve()), 1): 1,
            }
            summaries = summarize_coverage(counts, root)

            self.assertEqual([item.relative_path for item in summaries], ["app.py"])
            self.assertEqual(summaries[0].covered_lines, 2)
            self.assertGreaterEqual(summaries[0].executable_lines, 4)
            self.assertIn(4, summaries[0].missing_lines)


if __name__ == "__main__":
    unittest.main()
