from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools.python_to_souffle import (
    extract_facts_from_path,
    extract_facts_from_source,
    write_souffle_facts,
)


ROOT = Path(__file__).resolve().parents[1]


class ExtractFactsFromSourceTests(unittest.TestCase):
    def test_extracts_core_relations_from_inline_source(self) -> None:
        facts = extract_facts_from_source(
            """
import os

class Worker(BaseWorker):
    def run(self, item):
        token = os.getenv("API_TOKEN")
        return Helper(item)
            """.strip(),
            module_name="sample",
        )
        rendered = {fact.render() for fact in facts}

        self.assertIn('module("sample").', rendered)
        self.assertIn('imports("sample", "os").', rendered)
        self.assertIn('defines_class("sample", "Worker").', rendered)
        self.assertIn('extends("sample", "Worker", "BaseWorker").', rendered)
        self.assertIn('defines_function("sample", "Worker.run", 2).', rendered)
        self.assertIn('calls("sample", "Worker.run", "os.getenv", 5).', rendered)
        self.assertIn(
            'reads_env_var("sample", "Worker.run", "API_TOKEN", 5).',
            rendered,
        )
        self.assertIn(
            'instantiates("sample", "Worker.run", "Helper", 6).',
            rendered,
        )

    def test_extracts_dataclass_schema_facts(self) -> None:
        facts = extract_facts_from_source(
            """
from dataclasses import dataclass, field
from typing import Optional

@dataclass(frozen=True)
class Item:
    name: str
    count: int = 1
    tags: list[str] = field(default_factory=list)
    note: Optional[str] = None
            """.strip(),
            module_name="sample",
        )
        rendered = {fact.render() for fact in facts}

        self.assertIn('dataclass("sample", "Item", 1, 5).', rendered)
        self.assertIn(
            'dataclass_field("sample", "Item", "name", "str", 0, 0, "missing", 1, 6).',
            rendered,
        )
        self.assertIn(
            'dataclass_field("sample", "Item", "count", "int", 0, 1, "literal", 2, 7).',
            rendered,
        )
        self.assertIn(
            'dataclass_field("sample", "Item", "tags", "list[str]", 0, 1, "factory", 3, 8).',
            rendered,
        )
        self.assertIn(
            'dataclass_field_default_factory("sample", "Item", "tags", "list").',
            rendered,
        )
        self.assertIn(
            'dataclass_field("sample", "Item", "note", "Optional[str]", 1, 1, "literal", 4, 9).',
            rendered,
        )
        self.assertIn(
            'dataclass_field_type_ref("sample", "Item", "note", "Optional").',
            rendered,
        )

    def test_extracts_dataclass_effect_linking_facts(self) -> None:
        facts = extract_facts_from_source(
            """
from dataclasses import dataclass

@dataclass
class Pet:
    name: str

@dataclass
class Post:
    text: str

class Poster:
    def format_post(self, pet: Pet) -> Post:
        try:
            return Post(text=pet.name)
        except ValueError:
            raise RuntimeError("bad pet")
            """.strip(),
            module_name="sample",
        )
        rendered = {fact.render() for fact in facts}

        self.assertIn(
            'method_of_class("sample", "Poster", "Poster.format_post").',
            rendered,
        )
        self.assertIn(
            'function_param("sample", "Poster.format_post", "pet", "Pet", 2, 12).',
            rendered,
        )
        self.assertIn(
            'function_param_type_ref("sample", "Poster.format_post", "pet", "Pet").',
            rendered,
        )
        self.assertIn(
            'function_return_type("sample", "Poster.format_post", "Post", 12).',
            rendered,
        )
        self.assertIn(
            'function_return_type_ref("sample", "Poster.format_post", "Post").',
            rendered,
        )
        self.assertIn(
            'attribute_read("sample", "Poster.format_post", "pet", "name", 14).',
            rendered,
        )
        self.assertIn(
            'returns_dataclass("sample", "Poster.format_post", "Post", 14).',
            rendered,
        )
        self.assertIn(
            'handles_exception("sample", "Poster.format_post", "ValueError", 15).',
            rendered,
        )
        self.assertIn(
            'raises_exception("sample", "Poster.format_post", "RuntimeError", 16).',
            rendered,
        )


class ExtractFactsFromProjectTests(unittest.TestCase):
    def test_extracts_main_module_facts_from_cutepetsboston(self) -> None:
        facts = extract_facts_from_path(ROOT / "CutePetsBoston")
        rendered = {fact.render() for fact in facts}

        self.assertIn('module("main").', rendered)
        self.assertIn('module_file("main", "main.py").', rendered)
        self.assertIn('defines_function("main", "run", 2).', rendered)
        self.assertIn('calls("main", "run", "pick_pet", 67).', rendered)
        self.assertIn(
            'reads_env_var("main", "notify_slack_of_exception", "SLACK_WEBHOOK_URL", 104).',
            rendered,
        )
        self.assertIn(
            'dataclass("abstractions", "AdoptablePet", 0, 14).',
            rendered,
        )
        self.assertIn(
            'dataclass_field("abstractions", "Post", "tags", "list[str]", 0, 1, "factory", 5, 58).',
            rendered,
        )
        self.assertIn(
            'function_param_type_ref("abstractions", "SocialPoster.format_post", "pet", "AdoptablePet").',
            rendered,
        )
        self.assertIn(
            'function_return_type_ref("abstractions", "SocialPoster.publish", "PostResult").',
            rendered,
        )

    def test_writes_souffle_fact_files(self) -> None:
        facts = extract_facts_from_source(
            """
from dataclasses import dataclass

@dataclass
class Example:
    name: str
            """.strip(),
            module_name="sample",
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            facts_dir = Path(temp_dir)
            write_souffle_facts(facts, facts_dir)

            self.assertEqual(
                (facts_dir / "module.facts").read_text(encoding="utf-8"),
                "sample\n",
            )
            self.assertEqual(
                (facts_dir / "dataclass.facts").read_text(encoding="utf-8"),
                "sample\tExample\t0\t4\n",
            )
            self.assertEqual(
                (facts_dir / "dataclass_field.facts").read_text(encoding="utf-8"),
                "sample\tExample\tname\tstr\t0\t0\tmissing\t1\t5\n",
            )
            self.assertTrue((facts_dir / "calls.facts").exists())


if __name__ == "__main__":
    unittest.main()
