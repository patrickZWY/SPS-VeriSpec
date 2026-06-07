from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.generator_coverage import build_family_coverage, read_tsv
from tools.oracle_synthesis import (
    ReviewCandidate,
    build_manifest_entries,
    load_oracle_proposals,
    render_quarantined_oracle_tests,
    safe_id,
    stable_hash,
    write_llm_input_contract,
    write_manifest,
)


FAMILY_SOURCES: dict[str, tuple[str, str]] = {
    "transform_required_field": ("test_out", "transform_required_field_test_target.csv"),
    "transform_optional_field": ("test_out", "transform_optional_field_test_target.csv"),
    "helper_boundary": ("semantic_out", "numeric_bound.csv"),
    "common_ast_collection_iteration": ("semantic_out", "dataclass_collection_iteration.csv"),
    "interprocedural_observable_slice": ("semantic_out", "observable_output_slice.csv"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate targeted quarantined LLM candidate prompts from uncovered or "
            "weak-oracle semantic families."
        )
    )
    parser.add_argument("--analysis-dir", required=True)
    parser.add_argument("--generated-tests", required=True)
    parser.add_argument(
        "--output-dir",
        help="Output directory. Defaults to --generated-tests.",
    )
    parser.add_argument(
        "--max-candidates",
        type=int,
        default=50,
        help="Maximum plateau candidates to emit.",
    )
    parser.add_argument(
        "--llm-proposals",
        help="Optional JSON file with externally generated plateau proposals.",
    )
    return parser.parse_args()


def list_constant(path: Path, name: str) -> list[dict[str, object]]:
    if not path.exists():
        return []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    value = ast.literal_eval(node.value)
                    return value if isinstance(value, list) else []
    return []


def load_generated_family_cases(generated_tests: Path) -> dict[str, list[dict[str, object]]]:
    return {
        "transform_required_field": [
            case
            for case in list_constant(generated_tests / "test_generated_dataclass_properties.py", "CASES")
            if case.get("target_kind") != "optional"
        ],
        "transform_optional_field": [
            case
            for case in list_constant(generated_tests / "test_generated_dataclass_properties.py", "CASES")
            if case.get("target_kind") == "optional"
        ],
        "helper_boundary": list_constant(
            generated_tests / "test_generated_helper_boundaries.py",
            "HELPER_BOUNDARY_CASES",
        ),
        "common_ast_collection_iteration": list_constant(
            generated_tests / "test_generated_common_ast_properties.py",
            "COMMON_AST_CASES",
        ),
        "interprocedural_observable_slice": list_constant(
            generated_tests / "test_generated_interprocedural_properties.py",
            "INTERPROCEDURAL_CASES",
        ),
    }


def key_for_source_row(family: str, row: list[str]) -> tuple[object, ...] | None:
    if family in {"transform_required_field", "transform_optional_field"} and len(row) >= 7:
        module_name, class_name, qualified_name, source_class, source_field, _target_class, target_arg = row[:7]
        return (module_name, class_name, qualified_name.rsplit(".", 1)[-1], source_class, source_field, target_arg)
    if family == "helper_boundary" and len(row) >= 6:
        module_name, qualified_name = row[0], row[1]
        return (module_name, qualified_name.rsplit(".", 1)[-1], qualified_name)
    if family == "common_ast_collection_iteration" and len(row) >= 7:
        module_name, qualified_name, _source_module, source_class, source_field = row[:5]
        return (module_name, qualified_name.rsplit(".", 1)[-1], source_class, source_field)
    if family == "interprocedural_observable_slice" and len(row) >= 7 and row[6] == "string_output":
        source_module, source_class, source_field, _target_module, target_class, target_field = row[:6]
        return (source_class, source_field, target_class, target_field)
    return None


def key_for_generated_case(family: str, case: dict[str, object]) -> tuple[object, ...] | None:
    if family in {"transform_required_field", "transform_optional_field"}:
        return (
            case.get("class_module"),
            case.get("class_name"),
            case.get("method_name"),
            case.get("source_class"),
            case.get("source_field"),
            case.get("target_arg"),
        )
    if family == "helper_boundary":
        return (
            case.get("module_name"),
            case.get("method_name"),
            f"{case.get('class_name')}.{case.get('method_name')}",
        )
    if family == "common_ast_collection_iteration":
        return (
            case.get("module_name"),
            case.get("method_name"),
            case.get("source_class"),
            case.get("source_field"),
        )
    if family == "interprocedural_observable_slice":
        return (
            case.get("source_class"),
            case.get("source_field"),
            case.get("target_class"),
            case.get("target_field"),
        )
    return None


def source_location_for_row(row: list[str]) -> dict[str, str]:
    module_name = row[0] if row else ""
    qualified_name = row[1] if len(row) > 1 else ""
    return {"module": module_name, "qualified_name": qualified_name}


def symbol_for_row(row: list[str], family: str) -> str:
    location = source_location_for_row(row)
    if location["qualified_name"]:
        return f"{location['module']}.{location['qualified_name']}"
    if row:
        return f"{family}:{row[0]}"
    return family


def candidate_payload(
    family: str,
    row: list[str],
    nearby_cases: list[dict[str, object]],
    family_summary: dict[str, object],
    reason: str,
) -> dict[str, object]:
    return {
        "relation_names": [family],
        "relation_rows": [row],
        "reason": reason,
        "symbol": symbol_for_row(row, family),
        "source_location": source_location_for_row(row),
        "related_facts": {
            "nearby_generated_cases": nearby_cases[:3],
            "family_summary": [family_summary],
        },
        "allowed_test_styles": ["pytest_example", "hypothesis_property", "metamorphic_transform"],
        "policy": "target the uncovered or weak-oracle family only; synthesize the smallest executable witness and keep it quarantined",
    }


def collect_plateau_candidates(
    analysis_dir: Path,
    generated_tests: Path,
    max_candidates: int,
) -> list[ReviewCandidate]:
    family_stats = {family.name: family for family in build_family_coverage(analysis_dir, generated_tests)}
    generated_cases = load_generated_family_cases(generated_tests)
    candidates: list[ReviewCandidate] = []
    seen: set[str] = set()

    for family_name, family in family_stats.items():
        if family_name not in FAMILY_SOURCES:
            continue
        source_dir_name, filename = FAMILY_SOURCES[family_name]
        source_rows = read_tsv(analysis_dir / source_dir_name / filename)
        if family_name == "interprocedural_observable_slice":
            source_rows = [row for row in source_rows if len(row) >= 7 and row[6] == "string_output"]
        if family_name == "helper_boundary":
            source_rows = [
                row
                for row in source_rows
                if len(row) >= 3 and row[1].rsplit(".", 1)[-1].startswith("_") and row[2].startswith("len(")
            ]

        emitted_keys = {
            key_for_generated_case(family_name, case)
            for case in generated_cases.get(family_name, [])
        }
        emitted_keys.discard(None)
        family_summary = {
            "name": family_name,
            "discovered": family.discovered,
            "emitted_relations": family.emitted,
            "emitted_cases": family.emitted_cases,
            "strict_oracle_cases": family.strict_oracle,
            "weak_oracle_cases": family.weak_oracle,
            "coverage_percent": family.coverage_percent,
        }

        for row in source_rows:
            key = key_for_source_row(family_name, row)
            if key is None:
                continue
            if key not in emitted_keys:
                nearby_cases = generated_cases.get(family_name, [])
                reason = (
                    f"Semantic family `{family_name}` has an uncovered relation; "
                    "synthesize the smallest executable witness for this specific row."
                )
            elif family.weak_oracle > 0:
                nearby_cases = [
                    case
                    for case in generated_cases.get(family_name, [])
                    if key_for_generated_case(family_name, case) == key
                ]
                if not nearby_cases:
                    continue
                reason = (
                    f"Semantic family `{family_name}` is covered only with weak or observational "
                    "oracles; propose a stricter quarantined witness for this row."
                )
            else:
                continue

            payload = candidate_payload(family_name, row, nearby_cases, family_summary, reason)
            property_id = safe_id(family_name, stable_hash(payload)[:12])
            if property_id in seen:
                continue
            seen.add(property_id)
            candidates.append(
                ReviewCandidate(
                    property_id=property_id,
                    relation_names=payload["relation_names"],
                    relation_rows=payload["relation_rows"],
                    source_provenance="static",
                    reason=reason,
                    symbol=payload["symbol"],
                    source_location=payload["source_location"],
                    related_facts=payload["related_facts"],
                    prompt_input_hash=stable_hash(payload),
                )
            )
            if len(candidates) >= max_candidates:
                return candidates
    return candidates


def write_report(path: Path, candidates: list[ReviewCandidate], manifest_entries: int) -> None:
    lines = [
        "# LLM Plateau Candidates",
        "",
        f"- Candidate count: {len(candidates)}",
        f"- Manifest entries: {manifest_entries}",
        "",
        "## Candidates",
        "",
    ]
    for candidate in candidates:
        lines.append(f"- `{candidate.property_id}`: {candidate.reason}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    analysis_dir = Path(args.analysis_dir).resolve()
    generated_tests = Path(args.generated_tests).resolve()
    output_dir = Path(args.output_dir).resolve() if args.output_dir else generated_tests
    output_dir.mkdir(parents=True, exist_ok=True)

    candidates = collect_plateau_candidates(
        analysis_dir,
        generated_tests,
        args.max_candidates,
    )
    proposals = load_oracle_proposals(
        Path(args.llm_proposals).resolve() if args.llm_proposals else None
    )

    input_path = output_dir / "llm_plateau_input.json"
    test_path = output_dir / "test_generated_llm_plateau_candidates.py"
    manifest_path = output_dir / "llm_plateau_candidates.json"
    report_path = output_dir / "llm_plateau_report.md"

    write_llm_input_contract(input_path, candidates)
    test_path.write_text(render_quarantined_oracle_tests(proposals), encoding="utf-8")
    manifest_entries = build_manifest_entries(candidates, proposals, test_path.name)
    write_manifest(manifest_path, manifest_entries)
    write_report(report_path, candidates, len(manifest_entries))

    print(input_path)
    print(test_path)
    print(manifest_path)
    print(report_path)


if __name__ == "__main__":
    main()
