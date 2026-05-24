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
        self.assertIn('import_alias("sample", "os", "os").', rendered)
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

@dataclass(frozen=True, order=True, kw_only=True, slots=True, repr=False)
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
            'dataclass_option("sample", "Item", "init", "true", 0).',
            rendered,
        )
        self.assertIn(
            'dataclass_option("sample", "Item", "repr", "false", 1).',
            rendered,
        )
        self.assertIn(
            'dataclass_option("sample", "Item", "eq", "true", 0).',
            rendered,
        )
        self.assertIn(
            'dataclass_option("sample", "Item", "order", "true", 1).',
            rendered,
        )
        self.assertIn(
            'dataclass_option("sample", "Item", "frozen", "true", 1).',
            rendered,
        )
        self.assertIn(
            'dataclass_option("sample", "Item", "kw_only", "true", 1).',
            rendered,
        )
        self.assertIn(
            'dataclass_option("sample", "Item", "slots", "true", 1).',
            rendered,
        )
        self.assertIn(
            'dataclass_option("sample", "Item", "match_args", "true", 0).',
            rendered,
        )
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
            'resolved_param_type_ref("sample", "Poster.format_post", "pet", "sample", "Pet").',
            rendered,
        )
        self.assertIn(
            'resolved_return_type_ref("sample", "Poster.format_post", "sample", "Post").',
            rendered,
        )
        self.assertIn(
            'resolved_returns_dataclass("sample", "Poster.format_post", "sample", "Post", 14).',
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

    def test_extracts_local_field_dependencies_for_constructor_args(self) -> None:
        facts = extract_facts_from_source(
            """
from dataclasses import dataclass

@dataclass
class Pet:
    name: str
    breed: str
    image_url: str | None = None

@dataclass
class Post:
    image_url: str | None = None
    alt_text: str | None = None

class Poster:
    def format_post(self, pet: Pet) -> Post:
        url = pet.image_url
        alt = f"Photo of {pet.name}, a {pet.breed}"
        return Post(image_url=url, alt_text=alt)
            """.strip(),
            module_name="sample",
        )
        rendered = {fact.render() for fact in facts}

        self.assertIn(
            'local_depends_on_field("sample", "Poster.format_post", "url", "pet", "image_url", 16).',
            rendered,
        )
        self.assertIn(
            'local_depends_on_field("sample", "Poster.format_post", "alt", "pet", "name", 17).',
            rendered,
        )
        self.assertIn(
            'field_flows_to_constructor_arg("sample", "Poster.format_post", "pet", "image_url", "Post", "image_url", 18).',
            rendered,
        )
        self.assertIn(
            'field_flows_to_constructor_arg("sample", "Poster.format_post", "pet", "name", "Post", "alt_text", 18).',
            rendered,
        )
        self.assertIn(
            'field_flows_to_constructor_arg("sample", "Poster.format_post", "pet", "breed", "Post", "alt_text", 18).',
            rendered,
        )

    def test_extracts_call_result_assignment_for_inferred_reads(self) -> None:
        facts = extract_facts_from_source(
            """
from dataclasses import dataclass

@dataclass
class Post:
    text: str

@dataclass
class PostResult:
    success: bool

class Poster:
    def publish(self, post: Post) -> PostResult:
        return PostResult(success=True)

def run(poster: Poster, post: Post):
    result = poster.publish(post)
    if not result.success:
        return None
    return result
            """.strip(),
            module_name="sample",
        )
        rendered = {fact.render() for fact in facts}

        self.assertIn(
            'call_result_assigned("sample", "run", "result", "publish", 16).',
            rendered,
        )
        self.assertIn(
            'attribute_read("sample", "run", "result", "success", 17).',
            rendered,
        )
        self.assertIn('returns_none("sample", "run", 18).', rendered)

    def test_resolves_call_targets_arguments_and_return_calls(self) -> None:
        facts = extract_facts_from_source(
            """
from dataclasses import dataclass

@dataclass
class Source:
    raw: str

@dataclass
class Mid:
    normalized: str

@dataclass
class Output:
    label: str

def normalize(source: Source) -> Mid:
    return Mid(normalized=source.raw)

class Pipeline:
    def render(self, mid: Mid) -> Output:
        return Output(label=mid.normalized)

    def process(self, source: Source) -> Output:
        mid = normalize(source)
        return self.render(mid)
            """.strip(),
            module_name="sample",
        )
        rendered = {fact.render() for fact in facts}

        self.assertIn(
            'call_argument("sample", "Pipeline.process", "normalize", 1, "", "source", 23).',
            rendered,
        )
        self.assertIn(
            'call_target("sample", "Pipeline.process", "normalize", "sample", "normalize", "function", 23).',
            rendered,
        )
        self.assertIn(
            'resolved_call_result_assigned("sample", "Pipeline.process", "mid", "sample", "normalize", 23).',
            rendered,
        )
        self.assertIn(
            'return_call("sample", "Pipeline.process", "self.render", 24).',
            rendered,
        )
        self.assertIn(
            'call_target("sample", "Pipeline.process", "self.render", "sample", "Pipeline.render", "bound_method", 24).',
            rendered,
        )
        self.assertIn(
            'resolved_return_call("sample", "Pipeline.process", "sample", "Pipeline.render", 24).',
            rendered,
        )

    def test_extracts_branch_atoms_and_protocol_call_events(self) -> None:
        facts = extract_facts_from_source(
            """
from dataclasses import dataclass

@dataclass
class Post:
    image_url: str | None
    text: str

class Publisher:
    def authenticate(self):
        return True

    def publish(self, post: Post):
        if not post.image_url:
            return None
        self.authenticate()
        self.session.status_post(post.text)
            """.strip(),
            module_name="sample",
        )
        rendered = {fact.render() for fact in facts}

        self.assertIn(
            'branch_condition("sample", "Publisher.publish", "not post.image_url", 13).',
            rendered,
        )
        self.assertIn(
            'condition_atom("sample", "Publisher.publish", "post.image_url", "falsy", 13).',
            rendered,
        )
        self.assertIn(
            'call_protocol_event("sample", "Publisher.publish", "self", "authenticate", "self.authenticate", 15).',
            rendered,
        )
        self.assertIn(
            'call_protocol_event("sample", "Publisher.publish", "self.session", "publish", "self.session.status_post", 16).',
            rendered,
        )

    def test_extracts_semantic_value_and_numeric_facts(self) -> None:
        facts = extract_facts_from_source(
            """
from dataclasses import dataclass

@dataclass
class Post:
    text: str

@dataclass
class Result:
    success: bool
    error: str | None = None

def make(name: str) -> Post:
    limit = 12
    text = f"Meet {name}"
    if len(text) > limit:
        text = text[:limit]
    return Post(text=text)

def publish() -> Result:
    return Result(success=False, error="missing media")
            """.strip(),
            module_name="sample",
        )
        rendered = {fact.render() for fact in facts}

        self.assertIn(
            'numeric_assignment("sample", "make", "limit", 12, 13).',
            rendered,
        )
        self.assertIn(
            'literal_assigned("sample", "make", "limit", "number", "12", 13).',
            rendered,
        )
        self.assertIn(
            'len_call("sample", "make", "text", 15).',
            rendered,
        )
        self.assertIn(
            'numeric_compare("sample", "make", "len(text)", "gt", 12, 15).',
            rendered,
        )
        self.assertIn(
            'string_slice_upper_bound("sample", "make", "text", 12, 16).',
            rendered,
        )
        self.assertIn(
            'return_constructor_arg_literal("sample", "publish", "Result", "success", "bool", "False", 20).',
            rendered,
        )
        self.assertIn(
            'return_constructor_arg_literal("sample", "publish", "Result", "error", "str", "missing media", 20).',
            rendered,
        )

    def test_resolves_imported_class_references_across_project(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "models.py").write_text(
                """
from dataclasses import dataclass

@dataclass
class Pet:
    name: str

@dataclass
class Post:
    text: str
                """.strip(),
                encoding="utf-8",
            )
            (root / "poster.py").write_text(
                """
from models import Pet as Animal, Post

class BasePoster:
    pass

class Poster(BasePoster):
    def format_post(self, pet: Animal) -> Post:
        return Post(text=pet.name)
                """.strip(),
                encoding="utf-8",
            )

            rendered = {fact.render() for fact in extract_facts_from_path(root)}

        self.assertIn(
            'import_alias("poster", "Animal", "models.Pet").',
            rendered,
        )
        self.assertIn(
            'resolved_extends("poster", "Poster", "poster", "BasePoster").',
            rendered,
        )
        self.assertIn(
            'resolved_param_type_ref("poster", "Poster.format_post", "pet", "models", "Pet").',
            rendered,
        )
        self.assertIn(
            'resolved_return_type_ref("poster", "Poster.format_post", "models", "Post").',
            rendered,
        )
        self.assertIn(
            'resolved_returns_dataclass("poster", "Poster.format_post", "models", "Post", 8).',
            rendered,
        )

    def test_extracts_common_ast_relations_and_local_aliases(self) -> None:
        facts = extract_facts_from_source(
            """
from dataclasses import dataclass

@dataclass
class Batch:
    pets: list[str]
    status: str

async def process(batch: Batch, client):
    alias = batch
    assert alias.status
    for pet in alias.pets:
        yield pet
    names = [pet.upper() for pet in alias.pets if alias.status]
    async with client.session() as session:
        result = await session.fetch(names[0])
    match alias:
        case Batch(pets=pets) if alias.status:
            return result
            """.strip(),
            module_name="sample",
        )
        rendered = {fact.render() for fact in facts}

        self.assertIn(
            'local_alias("sample", "process", "alias", "batch", 9).',
            rendered,
        )
        self.assertIn(
            'condition_reads_attribute("sample", "process", "batch", "status", 10).',
            rendered,
        )
        self.assertIn(
            'loop_iterates("sample", "process", "pet", "batch.pets", 11).',
            rendered,
        )
        self.assertIn(
            'yield_value("sample", "process", "pet", 12).',
            rendered,
        )
        self.assertIn(
            'comprehension_iterates("sample", "process", "pet", "batch.pets", 13).',
            rendered,
        )
        self.assertIn(
            'comprehension_filter("sample", "process", "pet", "batch.status", 13).',
            rendered,
        )
        self.assertIn(
            'with_resource("sample", "process", "client.session()", "session", 14).',
            rendered,
        )
        self.assertIn(
            'await_expr("sample", "process", "session.fetch(names[0])", 15).',
            rendered,
        )
        self.assertIn(
            'subscript_access("sample", "process", "names", "int", 15).',
            rendered,
        )
        self.assertIn(
            'match_subject("sample", "process", "batch", 16).',
            rendered,
        )
        self.assertIn(
            'match_case("sample", "process", "MatchClass:Batch", "batch.status", 17).',
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
            self.assertIn(
                "sample\tExample\tfrozen\tfalse\t0\n",
                (facts_dir / "dataclass_option.facts").read_text(encoding="utf-8"),
            )
            self.assertEqual(
                (facts_dir / "dataclass_field.facts").read_text(encoding="utf-8"),
                "sample\tExample\tname\tstr\t0\t0\tmissing\t1\t5\n",
            )
            self.assertTrue((facts_dir / "calls.facts").exists())


if __name__ == "__main__":
    unittest.main()
