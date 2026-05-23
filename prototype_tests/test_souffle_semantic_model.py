from __future__ import annotations

import csv
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.python_to_souffle import extract_facts_from_source, write_souffle_facts


ROOT = Path(__file__).resolve().parents[1]


def read_rows(path: Path) -> set[tuple[str, ...]]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8", newline="") as handle:
        return {tuple(row) for row in csv.reader(handle, delimiter="\t") if row}


@unittest.skipIf(shutil.which("souffle") is None, "souffle is not installed")
class SemanticModelSouffleTests(unittest.TestCase):
    def test_derives_dataclass_and_helper_boundary_behaviors(self) -> None:
        facts = extract_facts_from_source(
            """
from dataclasses import dataclass

@dataclass
class Post:
    text: str

class Cleaner:
    def clean(self, description: str) -> str:
        text = description.strip()
        if len(text) > 500:
            text = text[:497] + "..."
        return text

class Poster:
    def caption(self, post: Post) -> str:
        caption = post.text
        if len(caption) > 10:
            return caption[:10]
        return caption
            """.strip(),
            module_name="sample",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            work_dir = Path(temp_dir)
            facts_dir = work_dir / "facts"
            out_dir = work_dir / "semantic_out"
            write_souffle_facts(facts, facts_dir)
            out_dir.mkdir()

            subprocess.run(
                [
                    "souffle",
                    "-F",
                    str(facts_dir),
                    "-D",
                    str(out_dir),
                    str(ROOT / "rule_layer" / "semantic_model.dl"),
                ],
                check=True,
            )

            boundary_behaviors = read_rows(out_dir / "boundary_behavior.csv")
            helper_behaviors = read_rows(out_dir / "helper_boundary_behavior.csv")

        self.assertIn(
            (
                "sample",
                "Poster",
                "Poster.caption",
                "caption",
                "upper_exclusive",
                "10",
                "sample",
                "Post",
                "text",
                "<primitive>",
                "str",
                "<return>",
                "max_length",
            ),
            boundary_behaviors,
        )
        self.assertIn(
            (
                "sample",
                "Cleaner",
                "Cleaner.clean",
                "text",
                "upper_exclusive",
                "497",
                "description",
                "return",
                "truncate_or_include",
            ),
            helper_behaviors,
        )


if __name__ == "__main__":
    unittest.main()
