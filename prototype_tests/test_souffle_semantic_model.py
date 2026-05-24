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
    def _run_semantic_model(self, facts) -> Path:
        work_dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, work_dir, ignore_errors=True)
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
        return out_dir

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

        out_dir = self._run_semantic_model(facts)
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

    def test_derives_common_ast_semantic_relations(self) -> None:
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
    result = await client.fetch(names[0])
    match batch:
        case Batch(pets=pets) if batch.status:
            return result
            """.strip(),
            module_name="sample",
        )

        out_dir = self._run_semantic_model(facts)

        self.assertIn(
            ("sample", "process", "alias", "batch"),
            read_rows(out_dir / "local_alias_reaches.csv"),
        )
        self.assertIn(
            ("sample", "process", "sample", "Batch", "pets", "pet", "for"),
            read_rows(out_dir / "dataclass_collection_iteration.csv"),
        )
        self.assertIn(
            (
                "sample",
                "process",
                "sample",
                "Batch",
                "pets",
                "pet",
                "comprehension",
            ),
            read_rows(out_dir / "dataclass_collection_iteration.csv"),
        )
        self.assertIn(
            ("sample", "process", "sample", "Batch", "status", "alias.status"),
            read_rows(out_dir / "asserted_dataclass_field.csv"),
        )
        self.assertIn(
            ("sample", "process", "sample", "Batch", "MatchClass:Batch"),
            read_rows(out_dir / "matched_dataclass_subject.csv"),
        )
        self.assertIn(
            ("sample", "process", "client.fetch(names[0])"),
            read_rows(out_dir / "async_obligation_candidate.csv"),
        )
        self.assertIn(
            ("sample", "process", "pet"),
            read_rows(out_dir / "generator_output_candidate.csv"),
        )

    def test_derives_interprocedural_field_summaries_and_slices(self) -> None:
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
    return Mid(normalized=source.raw.strip())

def render(mid: Mid) -> Output:
    return Output(label=f"Label: {mid.normalized}")

class Pipeline:
    def process(self, source: Source) -> Output:
        mid = normalize(source)
        return render(mid)
            """.strip(),
            module_name="sample",
        )

        out_dir = self._run_semantic_model(facts)

        self.assertIn(
            (
                "sample",
                "normalize",
                "sample",
                "Source",
                "raw",
                "sample",
                "Mid",
                "normalized",
                "constructor_arg",
            ),
            read_rows(out_dir / "function_summary_input_to_output.csv"),
        )
        self.assertIn(
            ("sample", "Source", "raw", "sample", "Output", "label"),
            read_rows(out_dir / "multi_hop_interprocedural_field_flow.csv"),
        )
        self.assertIn(
            (
                "sample",
                "Source",
                "raw",
                "sample",
                "Output",
                "label",
                "string_output",
            ),
            read_rows(out_dir / "observable_output_slice.csv"),
        )
        self.assertIn(
            (
                "sample",
                "Pipeline.process",
                "mid",
                "sample",
                "Source",
                "raw",
                "sample",
                "Mid",
                "normalized",
            ),
            read_rows(out_dir / "interprocedural_local_field_flow.csv"),
        )
        self.assertIn(
            (
                "sample",
                "Pipeline.process",
                "sample",
                "Source",
                "raw",
                "sample",
                "Output",
                "label",
                "return_call_local",
            ),
            read_rows(out_dir / "function_summary_input_to_output.csv"),
        )
        self.assertIn(
            (
                "sample",
                "Pipeline",
                "Pipeline.process",
                "sample",
                "Source",
                "sample",
                "Output",
            ),
            read_rows(out_dir / "interprocedural_method_transform.csv"),
        )

    def test_derives_slices_abstract_states_and_protocol_candidates(self) -> None:
        facts = extract_facts_from_source(
            """
from dataclasses import dataclass

@dataclass
class Post:
    image_url: str | None
    text: str

@dataclass
class Result:
    success: bool

class Publisher:
    def _ensure_ready(self, post: Post) -> None:
        if not post.image_url:
            raise ValueError("missing image")

    def unsafe_publish(self, post: Post) -> Result:
        self.session.status_post(post.image_url)
        return Result(success=False)

    def safe_publish(self, post: Post) -> Result:
        self._ensure_ready(post)
        self.session.status_post(post.image_url)
        return Result(success=True)
            """.strip(),
            module_name="sample",
        )

        out_dir = self._run_semantic_model(facts)

        self.assertIn(
            (
                "sample",
                "Publisher.unsafe_publish",
                "self.session.status_post",
                "post.image_url",
                "sample",
                "Post",
                "image_url",
                "18",
            ),
            read_rows(out_dir / "external_call_field_slice.csv"),
        )
        self.assertIn(
            (
                "sample",
                "Publisher._ensure_ready",
                "post.image_url",
                "sample",
                "Post",
                "image_url",
                "raises_exception",
                "ValueError",
                "15",
            ),
            read_rows(out_dir / "control_dependence_slice.csv"),
        )
        self.assertIn(
            (
                "sample",
                "Publisher._ensure_ready",
                "post.image_url",
                "nullness",
                "maybe_none",
                "falsy",
                "14",
            ),
            read_rows(out_dir / "abstract_value_state.csv"),
        )
        self.assertIn(
            (
                "sample",
                "Publisher.unsafe_publish",
                "sample",
                "Post",
                "image_url",
                "18",
                "optional_field_read_without_prior_guard_or_validation",
            ),
            read_rows(out_dir / "nullable_use_before_guard_candidate.csv"),
        )
        self.assertIn(
            (
                "sample",
                "Publisher.unsafe_publish",
                "self.session",
                "authenticate_or_validate_before_publish",
                "18",
                "publish_without_prior_authenticate_or_validate",
            ),
            read_rows(out_dir / "protocol_obligation_candidate.csv"),
        )
        self.assertIn(
            (
                "sample",
                "Publisher.safe_publish",
                "self",
                "unknown",
                "validated",
                "validate",
                "22",
            ),
            read_rows(out_dir / "typestate_transition.csv"),
        )
        self.assertIn(
            (
                "sample",
                "Publisher.unsafe_publish",
                "success",
                "status",
                "failure",
                "bool_literal_false",
                "0",
            ),
            read_rows(out_dir / "abstract_value_state.csv"),
        )


if __name__ == "__main__":
    unittest.main()
