from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal


OracleStrength = Literal["exact", "metamorphic", "observational", "exception", "weak"]
ValidationResult = Literal["passed", "failed", "error", "skipped", "not_run"]
Classification = Literal[
    "promotion_candidate",
    "design_conflict",
    "weak_oracle",
    "dependency_blocked",
    "needs_review",
]
SourceProvenance = Literal["static", "llm", "mixed"]


ALLOWED_ORACLE_STRENGTHS: set[str] = {
    "exact",
    "metamorphic",
    "observational",
    "exception",
    "weak",
}

REVIEW_RELATIONS: tuple[tuple[str, str], ...] = (
    ("semantic_out/asserted_dataclass_field.csv", "asserted dataclass field needs a public oracle"),
    ("semantic_out/matched_dataclass_subject.csv", "pattern-match behavior needs a public oracle"),
    ("semantic_out/async_obligation_candidate.csv", "async obligation needs review"),
    ("semantic_out/generator_output_candidate.csv", "generator output needs review"),
    ("semantic_out/alias_attribute_read.csv", "aliasing relation needs review"),
    ("semantic_out/lossy_required_field_candidate.csv", "lossy required-field candidate needs review"),
    ("semantic_out/nullable_use_before_guard_candidate.csv", "nullable use-before-guard candidate needs review"),
    ("semantic_out/protocol_obligation_candidate.csv", "protocol obligation candidate needs review"),
    ("semantic_out/typestate_protocol_violation.csv", "typestate protocol conflict needs review"),
    ("semantic_out/numeric_bound_conflict_candidate.csv", "numeric bound conflict needs review"),
)


@dataclass(frozen=True)
class ReviewCandidate:
    property_id: str
    relation_names: list[str]
    relation_rows: list[list[str]]
    source_provenance: SourceProvenance
    reason: str
    symbol: str
    source_location: dict[str, str]
    related_facts: dict[str, list[list[str]]]
    prompt_input_hash: str


@dataclass(frozen=True)
class OracleManifestEntry:
    property_id: str
    relation_names: list[str]
    relation_rows: list[list[str]]
    source_provenance: SourceProvenance
    prompt_input_hash: str
    generated_test_path: str
    test_id: str
    oracle_strength: OracleStrength
    validation_result: ValidationResult
    classification: Classification
    reason: str


@dataclass(frozen=True)
class OracleProposal:
    property_id: str
    test_id: str
    test_code: str
    oracle_strength: OracleStrength


def read_tsv(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.reader(handle, delimiter="\t") if row]


def stable_hash(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def safe_id(*parts: str) -> str:
    text = "-".join(parts)
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", text).strip("-")
    return text or "candidate"


def _relation_name(relative_path: str) -> str:
    return Path(relative_path).stem


def _load_provenance_map(analysis_dir: Path) -> dict[tuple[str, tuple[str, ...]], SourceProvenance]:
    mapping: dict[tuple[str, tuple[str, ...]], SourceProvenance] = {}
    path = analysis_dir / "provenance_out" / "finding_provenance.csv"
    for row in read_tsv(path):
        if len(row) < 3 or row[:2] == ["relation", "provenance"]:
            continue
        relation, provenance, row_json = row[:3]
        if provenance not in {"static", "llm", "mixed"}:
            continue
        relation_name = relation.rsplit(".", 1)[-1]
        try:
            relation_row = tuple(json.loads(row_json))
        except json.JSONDecodeError:
            continue
        mapping[(relation_name, relation_row)] = provenance  # type: ignore[assignment]
    return mapping


def _source_location(row: list[str]) -> dict[str, str]:
    module_name = row[0] if row else ""
    qualified_name = row[1] if len(row) > 1 else ""
    return {"module": module_name, "qualified_name": qualified_name}


def _symbol(row: list[str]) -> str:
    location = _source_location(row)
    if location["qualified_name"]:
        return f"{location['module']}.{location['qualified_name']}"
    return location["module"]


def _related_facts(analysis_dir: Path, row: list[str]) -> dict[str, list[list[str]]]:
    module_name = row[0] if row else ""
    qualified_name = row[1] if len(row) > 1 else ""
    facts_dir = analysis_dir / "facts"
    related: dict[str, list[list[str]]] = {}
    for fact_name in (
        "dataclass.facts",
        "dataclass_field.facts",
        "function_param.facts",
        "function_name.facts",
        "method_of_class.facts",
        "resolved_param_type_ref.facts",
    ):
        rows = []
        for fact_row in read_tsv(facts_dir / fact_name):
            if module_name and module_name not in fact_row:
                continue
            if qualified_name and qualified_name in fact_row:
                rows.append(fact_row)
            elif len(rows) < 5:
                rows.append(fact_row)
        if rows:
            related[Path(fact_name).stem] = rows[:10]
    return related


def _candidate_payload(
    relation_name: str,
    row: list[str],
    reason: str,
    related_facts: dict[str, list[list[str]]],
) -> dict[str, Any]:
    return {
        "relation_names": [relation_name],
        "relation_rows": [row],
        "reason": reason,
        "symbol": _symbol(row),
        "source_location": _source_location(row),
        "related_facts": related_facts,
        "allowed_test_styles": ["pytest_example", "hypothesis_property"],
        "policy": "synthesize the smallest executable witness; do not decide whether the program is wrong",
    }


def collect_review_candidates(
    analysis_dir: Path,
    source_provenance: SourceProvenance | None = None,
    max_candidates: int = 100,
) -> list[ReviewCandidate]:
    candidates: list[ReviewCandidate] = []
    seen: set[str] = set()
    provenance_map = _load_provenance_map(analysis_dir)
    for relative_path, reason in REVIEW_RELATIONS:
        relation_name = _relation_name(relative_path)
        for row in read_tsv(analysis_dir / relative_path):
            related_facts = _related_facts(analysis_dir, row)
            payload = _candidate_payload(relation_name, row, reason, related_facts)
            property_id = safe_id(relation_name, stable_hash(payload)[:12])
            if property_id in seen:
                continue
            seen.add(property_id)
            prompt_input_hash = stable_hash(payload)
            candidates.append(
                ReviewCandidate(
                    property_id=property_id,
                    relation_names=[relation_name],
                    relation_rows=[row],
                    source_provenance=source_provenance
                    or provenance_map.get((relation_name, tuple(row)), "static"),
                    reason=reason,
                    symbol=payload["symbol"],
                    source_location=payload["source_location"],
                    related_facts=related_facts,
                    prompt_input_hash=prompt_input_hash,
                )
            )
            if len(candidates) >= max_candidates:
                return candidates
    return candidates


def write_llm_input_contract(path: Path, candidates: list[ReviewCandidate]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "policy": {
            "instruction": "Synthesize the smallest executable witness for each risky property. Do not decide whether the program is wrong.",
            "allowed_test_styles": ["pytest_example", "hypothesis_property"],
            "oracle_strengths": sorted(ALLOWED_ORACLE_STRENGTHS),
            "reject_tests_that": [
                "assert private implementation details unless helper-boundary analysis requested",
                "require network, credentials, wall-clock timing, or nondeterministic external services",
                "encode a business rule not grounded in the supplied facts or source",
            ],
        },
        "candidates": [asdict(candidate) for candidate in candidates],
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_oracle_proposals(path: Path | None) -> list[OracleProposal]:
    if path is None or not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    raw_proposals = payload.get("tests", payload if isinstance(payload, list) else [])
    proposals: list[OracleProposal] = []
    for item in raw_proposals:
        strength = item.get("oracle_strength", "weak")
        if strength not in ALLOWED_ORACLE_STRENGTHS:
            strength = "weak"
        test_code = item.get("test_code", "")
        if not test_code.strip():
            continue
        proposals.append(
            OracleProposal(
                property_id=item["property_id"],
                test_id=safe_id(item.get("test_id", item["property_id"])),
                test_code=test_code.rstrip(),
                oracle_strength=strength,  # type: ignore[arg-type]
            )
        )
    return proposals


def render_quarantined_oracle_tests(proposals: list[OracleProposal]) -> str:
    blocks = [
        '"""',
        "Quarantined LLM-assisted oracle candidates.",
        "",
        "These tests are review artifacts, not trusted generated-suite evidence.",
        "Run them deliberately and classify failures as design conflicts, weak",
        "oracles, dependency blockers, or possible bugs after human review.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "import pytest",
        "",
        "pytestmark = [",
        "    pytest.mark.llm_oracle_candidate,",
        "    pytest.mark.xfail(reason=\"quarantined LLM oracle candidate\", strict=False),",
        "]",
        "",
    ]
    if not proposals:
        blocks.extend(
            [
                "",
                "def test_no_llm_oracle_candidates_emitted():",
                '    pytest.skip("No LLM oracle proposals were supplied.")',
                "",
            ]
        )
        return "\n".join(blocks)

    for proposal in proposals:
        blocks.extend(
            [
                "",
                f"# property_id: {proposal.property_id}",
                f"# oracle_strength: {proposal.oracle_strength}",
                proposal.test_code,
                "",
            ]
        )
    return "\n".join(blocks)


def initial_classification(strength: OracleStrength) -> Classification:
    if strength == "weak":
        return "weak_oracle"
    return "needs_review"


def build_manifest_entries(
    candidates: list[ReviewCandidate],
    proposals: list[OracleProposal],
    generated_test_path: str,
) -> list[OracleManifestEntry]:
    candidates_by_id = {candidate.property_id: candidate for candidate in candidates}
    entries: list[OracleManifestEntry] = []
    for proposal in proposals:
        candidate = candidates_by_id.get(proposal.property_id)
        if candidate is None:
            continue
        entries.append(
            OracleManifestEntry(
                property_id=candidate.property_id,
                relation_names=candidate.relation_names,
                relation_rows=candidate.relation_rows,
                source_provenance=candidate.source_provenance,
                prompt_input_hash=candidate.prompt_input_hash,
                generated_test_path=generated_test_path,
                test_id=proposal.test_id,
                oracle_strength=proposal.oracle_strength,
                validation_result="not_run",
                classification=initial_classification(proposal.oracle_strength),
                reason=candidate.reason,
            )
        )
    return entries


def write_manifest(path: Path, entries: list[OracleManifestEntry]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"oracle_candidates": [asdict(entry) for entry in entries]}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def update_manifest_validation(
    manifest_path: Path,
    validation_result: ValidationResult,
    classification: Classification,
) -> None:
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    for entry in payload.get("oracle_candidates", []):
        entry["validation_result"] = validation_result
        entry["classification"] = classification
    manifest_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
