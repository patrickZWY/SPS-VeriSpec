from __future__ import annotations

import argparse
import ast
import csv
import json
import re
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.python_to_souffle import extract_facts_from_path, extract_facts_from_source, write_souffle_facts
from tools.run_souffle_models import MODELS
from tools.run_static_analysis import output_dirs_for, run_models


DEFAULT_RELATIONS: tuple[tuple[str, str], ...] = (
    ("schema_out", "dataclass_shape.csv"),
    ("test_out", "transform_required_field_test_target.csv"),
    ("test_out", "transform_optional_field_test_target.csv"),
    ("semantic_out", "observable_output_slice.csv"),
    ("semantic_out", "numeric_bound.csv"),
)
DEFAULT_TRANSFORMS = (
    "reorder_facts",
    "duplicate_facts",
    "add_unused_helper",
    "local_rename",
)
PY_EXTENSIONS = (".py",)


@dataclass(frozen=True)
class RelationDelta:
    output_dir: str
    filename: str
    baseline_count: int
    transformed_count: int
    preserved: bool
    added_rows: list[tuple[str, ...]]
    removed_rows: list[tuple[str, ...]]

    @property
    def relation(self) -> str:
        return f"{self.output_dir}/{self.filename}"


@dataclass(frozen=True)
class TransformResult:
    transform: str
    preserved: bool
    deltas: list[RelationDelta]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate metamorphic stability of the static-analysis pipeline by "
            "applying semantics-preserving transforms and comparing stable "
            "derived relations."
        )
    )
    parser.add_argument("project_root", help="Path to the Python project to analyze.")
    parser.add_argument(
        "--work-dir",
        default="/tmp/sps-static-analysis-metamorphic",
        help="Directory for intermediate outputs and reports.",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include tests and manual testing files when extracting facts.",
    )
    parser.add_argument(
        "--transform",
        action="append",
        choices=DEFAULT_TRANSFORMS,
        default=[],
        help="Metamorphic transform to apply. Repeat for multiple transforms.",
    )
    parser.add_argument(
        "--relation",
        action="append",
        default=[],
        help=(
            "Stable derived relation to compare, in the form output_dir/filename.csv. "
            "Repeat for multiple relations."
        ),
    )
    parser.add_argument(
        "--report",
        help="Markdown report path. Defaults to <work-dir>/static_analysis_metamorphic_report.md.",
    )
    parser.add_argument(
        "--json-report",
        help="JSON report path. Defaults to the Markdown report path with .json suffix.",
    )
    return parser.parse_args()


def read_tsv(path: Path) -> list[tuple[str, ...]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [tuple(row) for row in csv.reader(handle, delimiter="\t") if row]


def write_tsv(path: Path, rows: list[tuple[str, ...]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerows(rows)


def parse_relation_specs(values: list[str]) -> list[tuple[str, str]]:
    if not values:
        return list(DEFAULT_RELATIONS)
    parsed: list[tuple[str, str]] = []
    for value in values:
        if "/" not in value:
            raise SystemExit(f"Invalid relation spec `{value}`. Expected output_dir/filename.csv.")
        output_dir, filename = value.split("/", 1)
        parsed.append((output_dir, filename))
    return parsed


def relation_rows(work_dir: Path, relation: tuple[str, str]) -> set[tuple[str, ...]]:
    output_dir, filename = relation
    return set(read_tsv(work_dir / output_dir / filename))


def extract_project_facts(project_root: Path, facts_dir: Path, include_tests: bool) -> None:
    facts = extract_facts_from_path(project_root, include_tests=include_tests)
    write_souffle_facts(facts, facts_dir)


def run_analysis_from_facts(facts_dir: Path, work_dir: Path) -> None:
    run_models(facts_dir, output_dirs_for(work_dir), MODELS)


def copy_tree(src: Path, dst: Path) -> None:
    shutil.copytree(src, dst, dirs_exist_ok=True)


def reorder_fact_rows(facts_dir: Path) -> None:
    for path in sorted(facts_dir.glob("*.facts")):
        rows = read_tsv(path)
        if len(rows) > 1:
            write_tsv(path, list(reversed(rows)))


def duplicate_fact_rows(facts_dir: Path) -> None:
    for path in sorted(facts_dir.glob("*.facts")):
        rows = read_tsv(path)
        if rows:
            write_tsv(path, rows + rows)


def add_unused_helper_module(project_root: Path) -> None:
    helper_path = project_root / "__sps_mr_unused_helper.py"
    helper_path.write_text(
        "\n".join(
            [
                "def _unused_helper(value: str) -> str:",
                '    token = value.strip()',
                "    return token.upper()",
                "",
            ]
        ),
        encoding="utf-8",
    )


class LocalRenameTransformer(ast.NodeTransformer):
    def visit_FunctionDef(self, node: ast.FunctionDef) -> ast.AST:
        return self._rename_function_locals(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> ast.AST:
        return self._rename_function_locals(node)

    def _rename_function_locals(
        self,
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> ast.AST:
        collector = LocalBindingCollector()
        collector.visit(node)
        if not collector.bound_names:
            return node

        mapping = {
            name: f"__sps_mr_{index}"
            for index, name in enumerate(sorted(collector.bound_names), start=1)
        }
        rewriter = FunctionLocalNameRewriter(mapping)
        renamed = rewriter.visit(node)
        return ast.fix_missing_locations(renamed)


class LocalBindingCollector(ast.NodeVisitor):
    def __init__(self) -> None:
        self.bound_names: set[str] = set()
        self._params: set[str] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._params.update(arg.arg for arg in node.args.posonlyargs)
        self._params.update(arg.arg for arg in node.args.args)
        self._params.update(arg.arg for arg in node.args.kwonlyargs)
        if node.args.vararg is not None:
            self._params.add(node.args.vararg.arg)
        if node.args.kwarg is not None:
            self._params.add(node.args.kwarg.arg)
        for statement in node.body:
            self.visit(statement)

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_Name(self, node: ast.Name) -> None:
        if isinstance(node.ctx, ast.Store):
            self._maybe_add(node.id)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        if node.name:
            self._maybe_add(node.name)
        self.generic_visit(node)

    def _maybe_add(self, name: str) -> None:
        if name in self._params:
            return
        if name in {"self", "cls"}:
            return
        self.bound_names.add(name)


class FunctionLocalNameRewriter(ast.NodeTransformer):
    def __init__(self, mapping: dict[str, str]) -> None:
        self.mapping = mapping

    def visit_Name(self, node: ast.Name) -> ast.AST:
        replacement = self.mapping.get(node.id)
        if replacement is None:
            return node
        return ast.copy_location(ast.Name(id=replacement, ctx=node.ctx), node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> ast.AST:
        if node.name in self.mapping:
            node.name = self.mapping[node.name]
        self.generic_visit(node)
        return node


def rename_project_locals(project_root: Path) -> None:
    for path in sorted(project_root.rglob("*.py")):
        if not path.is_file():
            continue
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        renamed = LocalRenameTransformer().visit(tree)
        rendered = ast.unparse(ast.fix_missing_locations(renamed)) + "\n"
        path.write_text(rendered, encoding="utf-8")


def prepare_variant_from_transform(
    project_root: Path,
    include_tests: bool,
    transform: str,
    variant_root: Path,
) -> Path:
    project_variant = variant_root / "project"
    facts_variant = variant_root / "facts"
    if transform in {"add_unused_helper", "local_rename"}:
        copy_tree(project_root, project_variant)
        if transform == "add_unused_helper":
            add_unused_helper_module(project_variant)
        else:
            rename_project_locals(project_variant)
        extract_project_facts(project_variant, facts_variant, include_tests)
        return facts_variant

    extract_project_facts(project_root, facts_variant, include_tests)
    if transform == "reorder_facts":
        reorder_fact_rows(facts_variant)
    elif transform == "duplicate_facts":
        duplicate_fact_rows(facts_variant)
    else:
        raise ValueError(f"Unknown transform `{transform}`.")
    return facts_variant


def compare_relations(
    baseline_work_dir: Path,
    transformed_work_dir: Path,
    relations: list[tuple[str, str]],
    transform: str,
) -> list[RelationDelta]:
    deltas: list[RelationDelta] = []
    for relation in relations:
        baseline = normalize_relation_rows(relation, relation_rows(baseline_work_dir, relation), transform)
        transformed = normalize_relation_rows(
            relation,
            relation_rows(transformed_work_dir, relation),
            transform,
        )
        added = sorted(transformed - baseline)
        removed = sorted(baseline - transformed)
        deltas.append(
            RelationDelta(
                output_dir=relation[0],
                filename=relation[1],
                baseline_count=len(baseline),
                transformed_count=len(transformed),
                preserved=not added and not removed,
                added_rows=added[:5],
                removed_rows=removed[:5],
            )
        )
    return deltas


def normalize_relation_rows(
    relation: tuple[str, str],
    rows: set[tuple[str, ...]],
    transform: str,
) -> set[tuple[str, ...]]:
    if transform != "local_rename":
        return rows
    if relation != ("semantic_out", "numeric_bound.csv"):
        return rows
    return {normalize_numeric_bound_row(row) for row in rows}


def normalize_numeric_bound_row(row: tuple[str, ...]) -> tuple[str, ...]:
    if len(row) < 6:
        return row
    expression = re.sub(r"len\([A-Za-z_][A-Za-z0-9_]*\)", "len(<local>)", row[2])
    if expression == row[2] and "." not in expression and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", expression):
        expression = "<local>"
    return (row[0], row[1], expression, row[3], row[4], "<line>")


def evaluate_metamorphic_relations(
    project_root: Path,
    work_dir: Path,
    include_tests: bool,
    transforms: list[str],
    relations: list[tuple[str, str]],
) -> list[TransformResult]:
    baseline_facts_dir = work_dir / "baseline" / "facts"
    baseline_work_dir = work_dir / "baseline" / "analysis"
    extract_project_facts(project_root, baseline_facts_dir, include_tests)
    run_analysis_from_facts(baseline_facts_dir, baseline_work_dir)

    results: list[TransformResult] = []
    for transform in transforms:
        transform_root = work_dir / transform
        variant_facts_dir = prepare_variant_from_transform(
            project_root,
            include_tests,
            transform,
            transform_root,
        )
        transformed_work_dir = transform_root / "analysis"
        run_analysis_from_facts(variant_facts_dir, transformed_work_dir)
        deltas = compare_relations(baseline_work_dir, transformed_work_dir, relations, transform)
        results.append(
            TransformResult(
                transform=transform,
                preserved=all(delta.preserved for delta in deltas),
                deltas=deltas,
            )
        )
    return results


def write_reports(
    report_path: Path,
    json_path: Path,
    project_root: Path,
    transforms: list[str],
    relations: list[tuple[str, str]],
    results: list[TransformResult],
) -> None:
    lines = [
        "# Static Analysis Metamorphic Report",
        "",
        f"- Project root: `{project_root}`",
        f"- Transforms: {', '.join(f'`{value}`' for value in transforms)}",
        f"- Relations: {', '.join(f'`{a}/{b}`' for a, b in relations)}",
        "",
        "## Summary",
        "",
    ]
    for result in results:
        status = "preserved" if result.preserved else "violated"
        lines.append(f"- `{result.transform}`: {status}")
    lines.append("")

    for result in results:
        lines.extend([f"## {result.transform}", ""])
        for delta in result.deltas:
            lines.append(
                f"- `{delta.relation}`: baseline={delta.baseline_count}, transformed={delta.transformed_count}, preserved={delta.preserved}"
            )
            if delta.added_rows:
                lines.append(f"  added sample: `{delta.added_rows[0]}`")
            if delta.removed_rows:
                lines.append(f"  removed sample: `{delta.removed_rows[0]}`")
        lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")

    payload = {
        "project_root": str(project_root),
        "transforms": transforms,
        "relations": [f"{a}/{b}" for a, b in relations],
        "results": [
            {
                "transform": result.transform,
                "preserved": result.preserved,
                "deltas": [
                    {
                        "relation": delta.relation,
                        "baseline_count": delta.baseline_count,
                        "transformed_count": delta.transformed_count,
                        "preserved": delta.preserved,
                        "added_rows": [list(row) for row in delta.added_rows],
                        "removed_rows": [list(row) for row in delta.removed_rows],
                    }
                    for delta in result.deltas
                ],
            }
            for result in results
        ],
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    work_dir = Path(args.work_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    transforms = args.transform or list(DEFAULT_TRANSFORMS)
    relations = parse_relation_specs(args.relation)
    report_path = (
        Path(args.report).resolve()
        if args.report
        else work_dir / "static_analysis_metamorphic_report.md"
    )
    json_path = (
        Path(args.json_report).resolve()
        if args.json_report
        else report_path.with_suffix(".json")
    )

    if shutil.which("souffle") is None:
        raise SystemExit("souffle is not installed or not on PATH.")

    with tempfile.TemporaryDirectory(prefix="sps-static-analysis-mr-") as temp_dir:
        temp_work_dir = Path(temp_dir)
        results = evaluate_metamorphic_relations(
            project_root,
            temp_work_dir,
            args.include_tests,
            transforms,
            relations,
        )
    write_reports(report_path, json_path, project_root, transforms, relations, results)
    print(report_path)


if __name__ == "__main__":
    main()
