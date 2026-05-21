from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = ROOT / "tools" / "python_to_souffle.py"
MODELS = {
    "schema": ROOT / "rule_layer" / "dataclass_schema_model.dl",
    "effect": ROOT / "rule_layer" / "dataclass_effect_model.dl",
    "deduction": ROOT / "rule_layer" / "dataclass_deduction_model.dl",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the generic Souffle dataclass models and write a summary report."
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
    subprocess.run(cmd, check=True)


def read_tsv_rows(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.reader(handle, delimiter="\t") if row]


def write_summary(work_dir: Path) -> Path:
    schema_dir = work_dir / "schema_out"
    effect_dir = work_dir / "effect_out"
    deduction_dir = work_dir / "deduction_out"

    modeled_dataclasses = read_tsv_rows(schema_dir / "modeled_dataclass.csv")
    dataclass_shapes = read_tsv_rows(schema_dir / "dataclass_shape.csv")
    direct_transforms = read_tsv_rows(deduction_dir / "dataclass_transform.csv")
    reachable_transforms = read_tsv_rows(
        deduction_dir / "reachable_dataclass_transform.csv"
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

    effect_counts = Counter(row[2] for row in effectful_dataclasses if len(row) >= 3)

    lines: list[str] = []
    lines.append("# Souffle Model Summary")
    lines.append("")
    lines.append("## Inventory")
    lines.append("")
    lines.append(f"- Dataclasses discovered: {len(modeled_dataclasses)}")
    lines.append(f"- Direct dataclass transformations: {len(direct_transforms)}")
    lines.append(
        f"- Reachable dataclass transformation pairs: {len(reachable_transforms)}"
    )
    lines.append(f"- Dataclass-linked functions: {len(dataclass_functions)}")
    lines.append("")

    if modeled_dataclasses:
        lines.append("## Dataclasses")
        lines.append("")
        for row in modeled_dataclasses[:20]:
            module_name, class_name, frozen, line = row
            lines.append(
                f"- `{module_name}.{class_name}` at line {line} (`frozen={frozen}`)"
            )
        lines.append("")

    if dataclass_shapes:
        lines.append("## Shapes")
        lines.append("")
        for row in dataclass_shapes[:10]:
            module_name, class_name, shape = row
            lines.append(f"- `{module_name}.{class_name}` -> `{shape}`")
        lines.append("")

    if direct_transforms:
        lines.append("## Direct Transformations")
        lines.append("")
        for row in direct_transforms[:20]:
            fn_module, qualified_name, src_module, src_class, tgt_module, tgt_class = row
            lines.append(
                f"- `{src_module}.{src_class} -> {tgt_module}.{tgt_class}` via `{fn_module}.{qualified_name}`"
            )
        lines.append("")

    if reachable_transforms:
        lines.append("## Reachable Transformations")
        lines.append("")
        for row in reachable_transforms[:20]:
            src_module, src_class, tgt_module, tgt_class = row
            lines.append(f"- `{src_module}.{src_class} => {tgt_module}.{tgt_class}`")
        lines.append("")

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

    if field_to_transform:
        lines.append("## Field-to-Transformation Relations")
        lines.append("")
        for row in field_to_transform[:20]:
            src_module, src_class, field_name, tgt_module, tgt_class, qualified_name = row
            lines.append(
                f"- `{src_module}.{src_class}.{field_name}` contributes to `{tgt_module}.{tgt_class}` via `{qualified_name}`"
            )
        lines.append("")

    if unread_required_fields:
        lines.append("## Unread Required Fields")
        lines.append("")
        for row in unread_required_fields[:20]:
            lines.append(f"- `{row[0]}.{row[1]}.{row[2]}`")
        lines.append("")

    if effect_counts:
        lines.append("## Effect Kinds")
        lines.append("")
        for effect_kind, count in sorted(effect_counts.items()):
            lines.append(f"- `{effect_kind}`: {count}")
        lines.append("")

    summary_path = work_dir / "summary.md"
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary_path


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    work_dir = Path(args.work_dir).resolve()
    facts_dir = work_dir / "facts"
    schema_out = work_dir / "schema_out"
    effect_out = work_dir / "effect_out"
    deduction_out = work_dir / "deduction_out"

    if shutil.which("souffle") is None:
        raise SystemExit("souffle is not installed or not on PATH.")

    for path in (facts_dir, schema_out, effect_out, deduction_out):
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

    run_command(
        ["souffle", "-F", str(facts_dir), "-D", str(schema_out), str(MODELS["schema"])]
    )
    run_command(
        ["souffle", "-F", str(facts_dir), "-D", str(effect_out), str(MODELS["effect"])]
    )
    run_command(
        [
            "souffle",
            "-F",
            str(facts_dir),
            "-D",
            str(deduction_out),
            str(MODELS["deduction"]),
        ]
    )

    summary_path = write_summary(work_dir)
    print(summary_path)


if __name__ == "__main__":
    main()
