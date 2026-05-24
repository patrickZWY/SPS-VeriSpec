from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
from collections import Counter
from pathlib import Path
from typing import Callable


ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / "tools" / "python_to_souffle.py"
SOUFFLE_ANALYSIS_DIR = ROOT / "souffle_static_analysis"
MODELS = {
    "schema": SOUFFLE_ANALYSIS_DIR / "dataclass_schema_model.dl",
    "effect": SOUFFLE_ANALYSIS_DIR / "dataclass_effect_model.dl",
    "deduction": SOUFFLE_ANALYSIS_DIR / "dataclass_deduction_model.dl",
    "test": SOUFFLE_ANALYSIS_DIR / "dataclass_test_model.dl",
    "semantic": SOUFFLE_ANALYSIS_DIR / "semantic_model.dl",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compatibility wrapper for the Souffle static-analysis backend. "
            "Prefer tools/run_static_analysis.py --engine souffle for new runs."
        )
    )
    parser.add_argument("project_root", help="Path to the Python project to analyze.")
    parser.add_argument(
        "--work-dir",
        default="/tmp/souffle-model-run",
        help="Directory for generated facts, Souffle outputs, and the summary report.",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include tests and manual testing files when extracting facts.",
    )
    return parser.parse_args()


def run_command(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, cwd=ROOT)


def read_tsv_rows(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.reader(handle, delimiter="\t") if row]


def append_section(
    lines: list[str],
    title: str,
    rows: list[list[str]],
    render_row: Callable[[list[str]], str],
    limit: int = 20,
) -> None:
    if not rows:
        return
    lines.extend([title, ""])
    lines.extend(render_row(row) for row in rows[:limit])
    lines.append("")


def write_summary(work_dir: Path) -> Path:
    schema_dir = work_dir / "schema_out"
    effect_dir = work_dir / "effect_out"
    deduction_dir = work_dir / "deduction_out"
    test_dir = work_dir / "test_out"
    semantic_dir = work_dir / "semantic_out"

    modeled_dataclasses = read_tsv_rows(schema_dir / "modeled_dataclass.csv")
    modeled_dataclass_options = read_tsv_rows(
        schema_dir / "modeled_dataclass_option.csv"
    )
    dataclass_shapes = read_tsv_rows(schema_dir / "dataclass_shape.csv")
    reachable_dependencies = read_tsv_rows(
        schema_dir / "reachable_dataclass_dependency.csv"
    )
    direct_transforms = read_tsv_rows(deduction_dir / "dataclass_transform.csv")
    reachable_transforms = read_tsv_rows(
        deduction_dir / "reachable_dataclass_transform.csv"
    )
    interprocedural_deduction_transforms = read_tsv_rows(
        deduction_dir / "interprocedural_dataclass_transform.csv"
    )
    bridge_dataclasses = read_tsv_rows(deduction_dir / "bridge_dataclass.csv")
    entry_dataclasses = read_tsv_rows(deduction_dir / "entry_dataclass.csv")
    terminal_dataclasses = read_tsv_rows(deduction_dir / "terminal_dataclass.csv")
    unread_required_fields = read_tsv_rows(
        deduction_dir / "unread_required_field.csv"
    )
    field_to_transform = read_tsv_rows(
        deduction_dir / "field_to_dataclass_transform.csv"
    )
    effectful_dataclasses = read_tsv_rows(deduction_dir / "effectful_dataclass.csv")
    dataclass_functions = read_tsv_rows(effect_dir / "dataclass_function.csv")
    reachable_function_calls = read_tsv_rows(effect_dir / "reachable_function_call.csv")
    interprocedural_effects = read_tsv_rows(
        effect_dir / "interprocedural_dataclass_effect.csv"
    )
    class_method_uses_dataclass = read_tsv_rows(
        test_dir / "class_method_uses_dataclass.csv"
    )
    method_dataclass_transforms = read_tsv_rows(
        test_dir / "method_dataclass_transform.csv"
    )
    interprocedural_method_dataclass_transforms = read_tsv_rows(
        test_dir / "interprocedural_method_dataclass_transform.csv"
    )
    field_to_constructor_args = read_tsv_rows(
        test_dir / "method_field_to_constructor_arg.csv"
    )
    optional_field_targets = read_tsv_rows(
        test_dir / "transform_optional_field_test_target.csv"
    )
    required_field_targets = read_tsv_rows(
        test_dir / "transform_required_field_test_target.csv"
    )
    optional_condition_reads = read_tsv_rows(
        test_dir / "optional_field_read_in_condition.csv"
    )
    frozen_mutable_fields = read_tsv_rows(
        test_dir / "frozen_contains_mutable_field.csv"
    )
    ordered_dataclasses = read_tsv_rows(test_dir / "ordered_dataclass.csv")
    comparable_dataclasses = read_tsv_rows(test_dir / "comparable_dataclass.csv")
    kw_only_dataclasses = read_tsv_rows(test_dir / "kw_only_dataclass.csv")
    slotted_dataclasses = read_tsv_rows(test_dir / "slotted_dataclass.csv")
    unsafe_hash_dataclasses = read_tsv_rows(test_dir / "unsafe_hash_dataclass.csv")
    override_contracts = read_tsv_rows(test_dir / "override_dataclass_contract.csv")
    semantic_field_flows = read_tsv_rows(semantic_dir / "semantic_field_flow.csv")
    composed_semantic_flows = read_tsv_rows(
        semantic_dir / "composed_semantic_field_flow.csv"
    )
    function_summaries = read_tsv_rows(
        semantic_dir / "function_summary_input_to_output.csv"
    )
    interprocedural_flows = read_tsv_rows(
        semantic_dir / "interprocedural_field_flow.csv"
    )
    multi_hop_interprocedural_flows = read_tsv_rows(
        semantic_dir / "multi_hop_interprocedural_field_flow.csv"
    )
    observable_output_slices = read_tsv_rows(
        semantic_dir / "observable_output_slice.csv"
    )
    observable_required_fields = read_tsv_rows(
        semantic_dir / "observable_required_field.csv"
    )
    lossy_required_fields = read_tsv_rows(
        semantic_dir / "lossy_required_field_candidate.csv"
    )
    dataclass_bool_literals = read_tsv_rows(semantic_dir / "dataclass_bool_literal.csv")
    dataclass_string_literals = read_tsv_rows(
        semantic_dir / "dataclass_string_literal.csv"
    )
    string_composition_targets = read_tsv_rows(
        semantic_dir / "string_composition_target.csv"
    )
    numeric_bounds = read_tsv_rows(semantic_dir / "numeric_bound.csv")
    boundary_test_candidates = read_tsv_rows(
        semantic_dir / "boundary_test_candidate.csv"
    )
    numeric_bound_conflicts = read_tsv_rows(
        semantic_dir / "numeric_bound_conflict_candidate.csv"
    )
    boundary_behaviors = read_tsv_rows(semantic_dir / "boundary_behavior.csv")
    helper_boundary_behaviors = read_tsv_rows(
        semantic_dir / "helper_boundary_behavior.csv"
    )
    alias_attribute_reads = read_tsv_rows(semantic_dir / "alias_attribute_read.csv")
    dataclass_collection_iterations = read_tsv_rows(
        semantic_dir / "dataclass_collection_iteration.csv"
    )
    asserted_dataclass_fields = read_tsv_rows(
        semantic_dir / "asserted_dataclass_field.csv"
    )
    matched_dataclass_subjects = read_tsv_rows(
        semantic_dir / "matched_dataclass_subject.csv"
    )
    async_obligation_candidates = read_tsv_rows(
        semantic_dir / "async_obligation_candidate.csv"
    )
    generator_output_candidates = read_tsv_rows(
        semantic_dir / "generator_output_candidate.csv"
    )
    call_parameter_bindings = read_tsv_rows(
        semantic_dir / "call_parameter_binding.csv"
    )
    interprocedural_local_field_flows = read_tsv_rows(
        semantic_dir / "interprocedural_local_field_flow.csv"
    )
    interprocedural_method_transforms = read_tsv_rows(
        semantic_dir / "interprocedural_method_transform.csv"
    )
    backward_output_slices = read_tsv_rows(
        semantic_dir / "backward_output_slice.csv"
    )
    function_backward_slices = read_tsv_rows(
        semantic_dir / "function_backward_slice.csv"
    )
    external_call_field_slices = read_tsv_rows(
        semantic_dir / "external_call_field_slice.csv"
    )
    control_dependence_slices = read_tsv_rows(
        semantic_dir / "control_dependence_slice.csv"
    )
    abstract_value_states = read_tsv_rows(
        semantic_dir / "abstract_value_state.csv"
    )
    abstract_numeric_states = read_tsv_rows(
        semantic_dir / "abstract_numeric_state.csv"
    )
    nullable_use_candidates = read_tsv_rows(
        semantic_dir / "nullable_use_before_guard_candidate.csv"
    )
    typestate_transitions = read_tsv_rows(
        semantic_dir / "typestate_transition.csv"
    )
    protocol_obligations = read_tsv_rows(
        semantic_dir / "protocol_obligation_candidate.csv"
    )
    typestate_violations = read_tsv_rows(
        semantic_dir / "typestate_protocol_violation.csv"
    )

    effect_counts = Counter(row[2] for row in effectful_dataclasses if len(row) >= 3)

    lines = [
        "# Souffle Model Summary",
        "",
        "## Inventory",
        "",
        f"- Dataclasses discovered: {len(modeled_dataclasses)}",
        f"- Dataclass option facts: {len(modeled_dataclass_options)}",
        f"- Reachable dataclass dependencies: {len(reachable_dependencies)}",
        f"- Comparable dataclasses: {len(comparable_dataclasses)}",
        f"- Ordered dataclasses: {len(ordered_dataclasses)}",
        f"- Keyword-only dataclasses: {len(kw_only_dataclasses)}",
        f"- Slotted dataclasses: {len(slotted_dataclasses)}",
        f"- Unsafe-hash dataclasses: {len(unsafe_hash_dataclasses)}",
        f"- Direct dataclass transformations: {len(direct_transforms)}",
        f"- Reachable dataclass transformation pairs: {len(reachable_transforms)}",
        f"- Callgraph-reachable function pairs: {len(reachable_function_calls)}",
        f"- Dataclass-linked functions: {len(dataclass_functions)}",
        f"- Interprocedural dataclass effects: {len(interprocedural_effects)}",
        f"- Interprocedural deduction transforms: {len(interprocedural_deduction_transforms)}",
        f"- Class/dataclass role links: {len(class_method_uses_dataclass)}",
        f"- Method dataclass transformations: {len(method_dataclass_transforms)}",
        f"- Interprocedural method dataclass transformations: {len(interprocedural_method_dataclass_transforms)}",
        f"- Field-to-constructor-arg flows: {len(field_to_constructor_args)}",
        f"- Call parameter bindings: {len(call_parameter_bindings)}",
        f"- Semantic field flows: {len(semantic_field_flows)}",
        f"- Composed semantic field flows: {len(composed_semantic_flows)}",
        f"- Function dataflow summaries: {len(function_summaries)}",
        f"- Interprocedural local field flows: {len(interprocedural_local_field_flows)}",
        f"- Interprocedural semantic method transforms: {len(interprocedural_method_transforms)}",
        f"- Backward output slices: {len(backward_output_slices)}",
        f"- Function backward slices: {len(function_backward_slices)}",
        f"- External-call field slices: {len(external_call_field_slices)}",
        f"- Control-dependence slices: {len(control_dependence_slices)}",
        f"- Abstract value states: {len(abstract_value_states)}",
        f"- Abstract numeric states: {len(abstract_numeric_states)}",
        f"- Nullable use-before-guard candidates: {len(nullable_use_candidates)}",
        f"- Typestate transitions: {len(typestate_transitions)}",
        f"- Protocol obligation candidates: {len(protocol_obligations)}",
        f"- Typestate protocol violations: {len(typestate_violations)}",
        f"- Interprocedural field flows: {len(interprocedural_flows)}",
        f"- Multi-hop interprocedural field flows: {len(multi_hop_interprocedural_flows)}",
        f"- Observable output slices: {len(observable_output_slices)}",
        f"- Observable required fields: {len(observable_required_fields)}",
        f"- Numeric boundary candidates: {len(boundary_test_candidates)}",
        f"- Boundary behaviors: {len(boundary_behaviors)}",
        f"- Helper boundary behaviors: {len(helper_boundary_behaviors)}",
        f"- Alias attribute reads: {len(alias_attribute_reads)}",
        f"- Dataclass collection iterations: {len(dataclass_collection_iterations)}",
        f"- Asserted dataclass fields: {len(asserted_dataclass_fields)}",
        f"- Matched dataclass subjects: {len(matched_dataclass_subjects)}",
        f"- Async obligation candidates: {len(async_obligation_candidates)}",
        f"- Generator output candidates: {len(generator_output_candidates)}",
        "",
    ]

    append_section(
        lines,
        "## Dataclasses",
        modeled_dataclasses,
        lambda row: f"- `{row[0]}.{row[1]}` at line {row[3]} (`frozen={row[2]}`)",
    )
    append_section(
        lines,
        "## Explicit Dataclass Options",
        [row for row in modeled_dataclass_options if len(row) >= 5 and row[4] == "1"],
        lambda row: f"- `{row[0]}.{row[1]}` sets `{row[2]}={row[3]}`",
    )
    append_section(
        lines,
        "## Shapes",
        dataclass_shapes,
        lambda row: f"- `{row[0]}.{row[1]}` -> `{row[2]}`",
        limit=10,
    )
    append_section(
        lines,
        "## Direct Transformations",
        direct_transforms,
        lambda row: (
            f"- `{row[2]}.{row[3]} -> {row[4]}.{row[5]}` "
            f"via `{row[0]}.{row[1]}`"
        ),
    )
    append_section(
        lines,
        "## Reachable Transformations",
        reachable_transforms,
        lambda row: f"- `{row[0]}.{row[1]} => {row[2]}.{row[3]}`",
    )
    append_section(
        lines,
        "## Interprocedural Deduction Transformations",
        interprocedural_deduction_transforms,
        lambda row: (
            f"- `{row[0]}.{row[1]}` reaches `{row[2]}.{row[3]}` "
            f"for `{row[4]}.{row[5]} -> {row[6]}.{row[7]}`"
        ),
    )

    if bridge_dataclasses or entry_dataclasses or terminal_dataclasses:
        lines.append("## Topology")
        lines.append("")
        for row in bridge_dataclasses[:10]:
            lines.append(f"- Bridge dataclass: `{row[0]}.{row[1]}`")
        for row in entry_dataclasses[:10]:
            lines.append(f"- Entry dataclass: `{row[0]}.{row[1]}`")
        for row in terminal_dataclasses[:10]:
            lines.append(f"- Terminal dataclass: `{row[0]}.{row[1]}`")
        lines.append("")

    append_section(
        lines,
        "## Field-to-Transformation Relations",
        field_to_transform,
        lambda row: (
            f"- `{row[0]}.{row[1]}.{row[2]}` contributes to "
            f"`{row[3]}.{row[4]}` via `{row[5]}`"
        ),
    )
    append_section(
        lines,
        "## Unread Required Fields",
        unread_required_fields,
        lambda row: f"- `{row[0]}.{row[1]}.{row[2]}`",
    )

    if effect_counts:
        lines.append("## Effect Kinds")
        lines.append("")
        for effect_kind, count in sorted(effect_counts.items()):
            lines.append(f"- `{effect_kind}`: {count}")
        lines.append("")

    append_section(
        lines,
        "## Class/Dataclass Roles",
        class_method_uses_dataclass,
        lambda row: (
            f"- `{row[0]}.{row[2]}` on `{row[1]}` {row[5]} "
            f"`{row[3]}.{row[4]}`"
        ),
    )
    append_section(
        lines,
        "## Method Dataclass Transformations",
        method_dataclass_transforms,
        lambda row: (
            f"- `{row[0]}.{row[2]}` on `{row[1]}` transforms "
            f"`{row[3]}.{row[4]}` to `{row[5]}.{row[6]}`"
        ),
    )
    append_section(
        lines,
        "## Interprocedural Method Transformations",
        interprocedural_method_dataclass_transforms,
        lambda row: (
            f"- `{row[0]}.{row[2]}` on `{row[1]}` reaches `{row[3]}.{row[4]}` "
            f"for `{row[5]}.{row[6]}` to `{row[7]}.{row[8]}`"
        ),
    )
    append_section(
        lines,
        "## Field-to-Constructor-Arg Flows",
        field_to_constructor_args,
        lambda row: (
            f"- `{row[0]}.{row[2]}` on `{row[1]}` maps "
            f"`{row[3]}.{row[4]}` to `{row[5]}.{row[6]}`"
        ),
    )

    if optional_field_targets or required_field_targets or optional_condition_reads:
        lines.append("## Test Targets")
        lines.append("")
        for row in optional_field_targets[:20]:
            class_module, class_name, qualified_name, src_class, field_name, tgt_class, tgt_arg = row
            lines.append(
                f"- Optional boundary: `{src_class}.{field_name}` -> `{tgt_class}.{tgt_arg}` in `{class_module}.{qualified_name}`"
            )
        for row in required_field_targets[:20]:
            class_module, class_name, qualified_name, src_class, field_name, tgt_class, tgt_arg = row
            lines.append(
                f"- Required mapping: `{src_class}.{field_name}` -> `{tgt_class}.{tgt_arg}` in `{class_module}.{qualified_name}`"
            )
        for row in optional_condition_reads[:20]:
            class_module, class_name, qualified_name, dc_module, dc_name, field_name = row
            lines.append(
                f"- Optional branch: `{dc_module}.{dc_name}.{field_name}` in `{class_module}.{qualified_name}`"
            )
        lines.append("")

    append_section(
        lines,
        "## Semantic Field Flows",
        semantic_field_flows,
        lambda row: (
            f"- `{row[2]}.{row[3]}.{row[4]}` -> "
            f"`{row[5]}.{row[6]}.{row[7]}` via `{row[0]}.{row[1]}` "
            f"(`{row[8]}`)"
        ),
    )
    append_section(
        lines,
        "## Composed Semantic Field Flows",
        composed_semantic_flows,
        lambda row: f"- `{row[0]}.{row[1]}.{row[2]}` => `{row[3]}.{row[4]}.{row[5]}`",
    )
    append_section(
        lines,
        "## Interprocedural Dataflow",
        [
            *[["binding", *row] for row in call_parameter_bindings[:10]],
            *[["local_flow", *row] for row in interprocedural_local_field_flows[:10]],
            *[["method", *row] for row in interprocedural_method_transforms[:10]],
            *[["summary", *row] for row in function_summaries[:10]],
            *[["multi_hop", *row] for row in multi_hop_interprocedural_flows[:10]],
            *[["slice", *row] for row in observable_output_slices[:10]],
        ],
        lambda row: f"- `{row[0]}`: `{' | '.join(row[1:])}`",
        limit=30,
    )
    append_section(
        lines,
        "## Program Slices",
        [
            *[["backward_output", *row] for row in backward_output_slices[:10]],
            *[["function_backward", *row] for row in function_backward_slices[:10]],
            *[["external_call", *row] for row in external_call_field_slices[:10]],
            *[["control", *row] for row in control_dependence_slices[:10]],
        ],
        lambda row: f"- `{row[0]}`: `{' | '.join(row[1:])}`",
        limit=30,
    )
    append_section(
        lines,
        "## Abstract Interpretation",
        [
            *[["value", *row] for row in abstract_value_states[:15]],
            *[["numeric", *row] for row in abstract_numeric_states[:15]],
            *[["nullable_use", *row] for row in nullable_use_candidates[:15]],
        ],
        lambda row: f"- `{row[0]}`: `{' | '.join(row[1:])}`",
        limit=30,
    )
    append_section(
        lines,
        "## Typestate and Protocols",
        [
            *[["transition", *row] for row in typestate_transitions[:15]],
            *[["obligation", *row] for row in protocol_obligations[:15]],
            *[["violation", *row] for row in typestate_violations[:15]],
        ],
        lambda row: f"- `{row[0]}`: `{' | '.join(row[1:])}`",
        limit=30,
    )
    append_section(
        lines,
        "## Observable Required Fields",
        observable_required_fields,
        lambda row: (
            f"- `{row[2]}.{row[3]}.{row[4]}` is observable as "
            f"`{row[5]}.{row[6]}.{row[7]}` via `{row[0]}.{row[1]}`"
        ),
    )
    append_section(
        lines,
        "## Lossy Required Field Candidates",
        lossy_required_fields,
        lambda row: (
            f"- `{row[2]}.{row[3]}.{row[4]}` has no detected flow to "
            f"`{row[5]}.{row[6]}` in `{row[0]}.{row[1]}`"
        ),
    )

    if dataclass_bool_literals or dataclass_string_literals or string_composition_targets:
        lines.append("## Literal and String Semantics")
        lines.append("")
        for row in dataclass_bool_literals[:20]:
            lines.append(
                f"- Bool literal: `{row[2]}.{row[3]}.{row[4]}` = `{row[5]}` in `{row[0]}.{row[1]}`"
            )
        for row in dataclass_string_literals[:20]:
            lines.append(
                f"- String literal: `{row[2]}.{row[3]}.{row[4]}` = `{row[5]}` in `{row[0]}.{row[1]}`"
            )
        for row in string_composition_targets[:20]:
            lines.append(
                f"- String composition: `{row[2]}.{row[3]}.{row[4]}` uses `{row[5]}` in `{row[0]}.{row[1]}`"
            )
        lines.append("")

    if numeric_bounds or boundary_test_candidates or numeric_bound_conflicts:
        lines.append("## Numeric Semantics")
        lines.append("")
        for row in numeric_bounds[:20]:
            lines.append(
                f"- Bound: `{row[2]}` has `{row[3]}` `{row[4]}` in `{row[0]}.{row[1]}` at line {row[5]}"
            )
        for row in boundary_test_candidates[:20]:
            lines.append(
                f"- Boundary test: `{row[2]}` `{row[3]}` -> `{row[4]}` in `{row[0]}.{row[1]}`"
            )
        for row in numeric_bound_conflicts[:20]:
            lines.append(
                f"- Conflicting bounds: `{row[2]}` lower `{row[3]}` exceeds upper `{row[4]}` in `{row[0]}.{row[1]}`"
            )
        lines.append("")

    append_section(
        lines,
        "## Boundary Behaviors",
        boundary_behaviors,
        lambda row: (
            f"- `{row[6]}.{row[7]}.{row[8]}` drives `{row[9]}.{row[10]}.{row[11]}` "
            f"as `{row[12]}` around `{row[2]}` `{row[3]}` `{row[4]}` = `{row[5]}`"
        ),
    )
    append_section(
        lines,
        "## Helper Boundary Behaviors",
        helper_boundary_behaviors,
        lambda row: (
            f"- `{row[2]}` maps input `{row[6]}` to `{row[7]}` as `{row[8]}` "
            f"around `{row[3]}` `{row[4]}` `{row[5]}`"
        ),
    )
    append_section(
        lines,
        "## Common AST Semantic Relations",
        [
            *[
                ["alias_attribute_read", *row]
                for row in alias_attribute_reads[:10]
            ],
            *[
                ["dataclass_collection_iteration", *row]
                for row in dataclass_collection_iterations[:10]
            ],
            *[
                ["asserted_dataclass_field", *row]
                for row in asserted_dataclass_fields[:10]
            ],
            *[
                ["matched_dataclass_subject", *row]
                for row in matched_dataclass_subjects[:10]
            ],
            *[
                ["async_obligation_candidate", *row]
                for row in async_obligation_candidates[:10]
            ],
            *[
                ["generator_output_candidate", *row]
                for row in generator_output_candidates[:10]
            ],
        ],
        lambda row: f"- `{row[0]}`: `{' | '.join(row[1:])}`",
        limit=30,
    )

    if frozen_mutable_fields or override_contracts:
        lines.append("## Design Review Candidates")
        lines.append("")
        for row in frozen_mutable_fields[:20]:
            module_name, class_name, field_name, factory_name = row
            lines.append(
                f"- Frozen dataclass contains mutable factory field: `{module_name}.{class_name}.{field_name}` via `{factory_name}`"
            )
        for row in override_contracts[:20]:
            module_name, class_name, base_name, method_name, qualified_name, dc_name, role = row
            lines.append(
                f"- Override contract: `{module_name}.{class_name}.{method_name}` overrides `{base_name}` and {role} `{dc_name}`"
            )
        lines.append("")

    summary_path = work_dir / "summary.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    work_dir = Path(args.work_dir).resolve()
    facts_dir = work_dir / "facts"
    output_dirs = {
        "schema": work_dir / "schema_out",
        "effect": work_dir / "effect_out",
        "deduction": work_dir / "deduction_out",
        "test": work_dir / "test_out",
        "semantic": work_dir / "semantic_out",
    }

    if shutil.which("souffle") is None:
        raise SystemExit("souffle is not installed or not on PATH.")

    for path in (facts_dir, *output_dirs.values()):
        path.mkdir(parents=True, exist_ok=True)

    extract_cmd = [
        "python3",
        str(EXTRACTOR),
        str(project_root),
        "--souffle-facts-dir",
        str(facts_dir),
    ]
    if args.include_tests:
        extract_cmd.append("--include-tests")
    run_command(extract_cmd)

    for model_name, output_dir in output_dirs.items():
        run_command(
            [
                "souffle",
                "-F",
                str(facts_dir),
                "-D",
                str(output_dir),
                str(MODELS[model_name]),
            ]
        )

    summary_path = write_summary(work_dir)
    print(summary_path)


if __name__ == "__main__":
    main()
