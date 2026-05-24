from __future__ import annotations

import argparse
import ast
import csv
import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class CoverageTotals:
    covered_lines: int
    executable_lines: int
    percent: float
    returncode: int


@dataclass(frozen=True)
class RelationStats:
    required_transform_targets: int
    optional_transform_targets: int
    transform_targets: int
    unique_transform_relations_tested: int
    example_cases: int
    hypothesis_cases: int
    helper_boundary_cases: int
    helper_boundary_candidates: int
    common_ast_cases: int
    common_ast_candidates: int
    interprocedural_cases: int
    interprocedural_candidates: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write an SPS-VeriSpec evaluation report with relation yield and coverage deltas."
    )
    parser.add_argument(
        "--analysis-dir",
        required=True,
        help="Directory produced by tools/run_souffle_models.py.",
    )
    parser.add_argument(
        "--target-project",
        required=True,
        help="Target Python project checkout.",
    )
    parser.add_argument(
        "--target-tests",
        action="append",
        default=[],
        help="Target project test path. Repeat for multiple paths.",
    )
    parser.add_argument(
        "--generated-tests",
        required=True,
        help="Generated test directory.",
    )
    parser.add_argument(
        "--source-root",
        help="Source root to measure. Defaults to --target-project.",
    )
    parser.add_argument(
        "--report",
        help="Markdown report path. Defaults to <generated-tests>/evaluation_stats.md.",
    )
    parser.add_argument(
        "--json-report",
        help="JSON report path. Defaults to the Markdown report path with .json suffix.",
    )
    parser.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        help="Extra argument passed to pytest. Repeat for multiple arguments.",
    )
    return parser.parse_args()


def read_tsv(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.reader(handle, delimiter="\t") if row]


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


def relation_stats(analysis_dir: Path, generated_tests: Path) -> RelationStats:
    required = read_tsv(analysis_dir / "test_out" / "transform_required_field_test_target.csv")
    optional = read_tsv(analysis_dir / "test_out" / "transform_optional_field_test_target.csv")
    numeric_bounds = read_tsv(analysis_dir / "semantic_out" / "numeric_bound.csv")
    helper_boundary_candidates = sum(
        1
        for row in numeric_bounds
        if len(row) >= 3 and row[1].rsplit(".", 1)[-1].startswith("_")
    )

    example_cases = list_constant(
        generated_tests / "test_generated_dataclass_properties.py",
        "CASES",
    )
    hypothesis_cases = list_constant(
        generated_tests / "test_generated_dataclass_hypothesis.py",
        "CASES",
    )
    helper_cases = list_constant(
        generated_tests / "test_generated_helper_boundaries.py",
        "HELPER_BOUNDARY_CASES",
    )
    common_ast_cases = list_constant(
        generated_tests / "test_generated_common_ast_properties.py",
        "COMMON_AST_CASES",
    )
    common_ast_candidates = sum(
        len(read_tsv(analysis_dir / "semantic_out" / filename))
        for filename in (
            "dataclass_collection_iteration.csv",
            "asserted_dataclass_field.csv",
            "matched_dataclass_subject.csv",
            "async_obligation_candidate.csv",
            "generator_output_candidate.csv",
            "alias_attribute_read.csv",
        )
    )
    interprocedural_cases = list_constant(
        generated_tests / "test_generated_interprocedural_properties.py",
        "INTERPROCEDURAL_CASES",
    )
    interprocedural_candidates = len(
        read_tsv(analysis_dir / "semantic_out" / "observable_output_slice.csv")
    )
    unique_transform_relations = {
        (
            case.get("class_module"),
            case.get("class_name"),
            case.get("method_name"),
            case.get("source_class"),
            case.get("source_field"),
            case.get("target_arg"),
        )
        for case in example_cases
    }
    return RelationStats(
        required_transform_targets=len(required),
        optional_transform_targets=len(optional),
        transform_targets=len(required) + len(optional),
        unique_transform_relations_tested=len(unique_transform_relations),
        example_cases=len(example_cases),
        hypothesis_cases=len(hypothesis_cases),
        helper_boundary_cases=len(helper_cases),
        helper_boundary_candidates=helper_boundary_candidates,
        common_ast_cases=len(common_ast_cases),
        common_ast_candidates=common_ast_candidates,
        interprocedural_cases=len(interprocedural_cases),
        interprocedural_candidates=interprocedural_candidates,
    )


def coverage_totals(
    pytest_args: list[str],
    target_project: Path,
    source_root: Path,
) -> CoverageTotals:
    with tempfile.TemporaryDirectory() as temp_dir:
        report_path = Path(temp_dir) / "coverage.md"
        json_path = Path(temp_dir) / "coverage.json"
        command = [
            sys.executable,
            str(ROOT / "tools" / "coverage_stats.py"),
            "--target-project",
            str(target_project),
            "--source-root",
            str(source_root),
            "--report",
            str(report_path),
            "--json-report",
            str(json_path),
            "--no-default-tests",
        ]
        for arg in pytest_args:
            command.extend(["--pytest-arg", arg])

        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        if json_path.exists():
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            total = payload["total"]
            covered = int(total["covered_lines"])
            executable = int(total["executable_lines"])
            percent = float(total["percent"])
            returncode = int(payload["pytest_returncode"])
        else:
            covered = 0
            executable = 0
            percent = 0.0
            returncode = completed.returncode or 1

    return CoverageTotals(
        covered_lines=covered,
        executable_lines=executable,
        percent=percent,
        returncode=returncode,
    )


def percent_delta(new: CoverageTotals, old: CoverageTotals) -> float:
    return new.percent - old.percent


def line_delta(new: CoverageTotals, old: CoverageTotals) -> int:
    return new.covered_lines - old.covered_lines


def svg_bar_chart(
    title: str,
    rows: list[tuple[str, float, str]],
    *,
    width: int = 760,
    row_height: int = 38,
    max_value: float = 100.0,
) -> str:
    label_width = 210
    chart_width = width - label_width - 120
    height = 58 + row_height * len(rows)
    parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{title}">',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:13px;fill:#1f2933}.title{font-size:16px;font-weight:600}.axis{fill:#6b7280}.track{fill:#e5e7eb}.bar{fill:#2563eb}.bar2{fill:#059669}.bar3{fill:#7c3aed}</style>',
        f'<text x="0" y="20" class="title">{title}</text>',
    ]
    colors = ["bar", "bar2", "bar3"]
    for index, (label, value, value_label) in enumerate(rows):
        y = 48 + index * row_height
        bounded = max(0.0, min(value, max_value))
        bar_width = 0 if max_value == 0 else (bounded / max_value) * chart_width
        parts.extend(
            [
                f'<text x="0" y="{y + 15}">{label}</text>',
                f'<rect x="{label_width}" y="{y}" width="{chart_width}" height="20" rx="3" class="track"/>',
                f'<rect x="{label_width}" y="{y}" width="{bar_width:.1f}" height="20" rx="3" class="{colors[index % len(colors)]}"/>',
                f'<text x="{label_width + chart_width + 14}" y="{y + 15}" class="axis">{value_label}</text>',
            ]
        )
    parts.append("</svg>")
    return "\n".join(parts)


def svg_stacked_bar(
    title: str,
    segments: list[tuple[str, int, str]],
    *,
    width: int = 760,
) -> str:
    total = sum(value for _label, value, _color in segments)
    chart_x = 0
    chart_y = 54
    chart_width = width - 20
    height = 132
    parts = [
        f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{title}">',
        '<style>text{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;font-size:13px;fill:#1f2933}.title{font-size:16px;font-weight:600}.legend{fill:#4b5563}</style>',
        f'<text x="0" y="20" class="title">{title}</text>',
    ]
    cursor = chart_x
    for label, value, color in segments:
        segment_width = 0 if total == 0 else (value / total) * chart_width
        parts.append(
            f'<rect x="{cursor:.1f}" y="{chart_y}" width="{segment_width:.1f}" height="24" rx="3" fill="{color}"/>'
        )
        cursor += segment_width
    legend_x = 0
    for label, value, color in segments:
        parts.extend(
            [
                f'<rect x="{legend_x}" y="94" width="11" height="11" rx="2" fill="{color}"/>',
                f'<text x="{legend_x + 16}" y="104" class="legend">{label}: {value}</text>',
            ]
        )
        legend_x += 205
    parts.append("</svg>")
    return "\n".join(parts)


def write_reports(
    markdown_path: Path,
    json_path: Path,
    stats: RelationStats,
    target_only: CoverageTotals,
    generated_only: CoverageTotals,
    combined: CoverageTotals,
    target_tests: list[str],
    generated_tests: str,
) -> None:
    relation_yield = (
        0.0
        if stats.transform_targets == 0
        else (stats.unique_transform_relations_tested / stats.transform_targets) * 100
    )
    helper_yield = (
        0.0
        if stats.helper_boundary_candidates == 0
        else (stats.helper_boundary_cases / stats.helper_boundary_candidates) * 100
    )
    common_ast_yield = (
        0.0
        if stats.common_ast_candidates == 0
        else (stats.common_ast_cases / stats.common_ast_candidates) * 100
    )
    interprocedural_yield = (
        0.0
        if stats.interprocedural_candidates == 0
        else (stats.interprocedural_cases / stats.interprocedural_candidates) * 100
    )
    coverage_chart = svg_bar_chart(
        "Line Coverage by Suite",
        [
            ("Handwritten target tests", target_only.percent, f"{target_only.percent:.1f}%"),
            ("Generated tests", generated_only.percent, f"{generated_only.percent:.1f}%"),
            ("Combined", combined.percent, f"{combined.percent:.1f}%"),
        ],
    )
    yield_chart = svg_bar_chart(
        "Relation-to-Test Yield",
        [
            ("Transform relations", relation_yield, f"{stats.unique_transform_relations_tested}/{stats.transform_targets}"),
            ("Helper boundaries", helper_yield, f"{stats.helper_boundary_cases}/{stats.helper_boundary_candidates}"),
            ("Common AST", common_ast_yield, f"{stats.common_ast_cases}/{stats.common_ast_candidates}"),
            ("Interproc", interprocedural_yield, f"{stats.interprocedural_cases}/{stats.interprocedural_candidates}"),
        ],
    )
    composition_chart = svg_stacked_bar(
        "Generated Test Composition",
        [
            ("Examples", stats.example_cases, "#2563eb"),
            ("Hypothesis", stats.hypothesis_cases, "#059669"),
            ("Helper boundaries", stats.helper_boundary_cases, "#7c3aed"),
            ("Common AST", stats.common_ast_cases, "#db2777"),
            ("Interproc", stats.interprocedural_cases, "#ea580c"),
        ],
    )

    lines = [
        "# SPS-VeriSpec Evaluation Stats",
        "",
        "## Test Inputs",
        "",
        f"- Target tests: `{', '.join(target_tests)}`",
        f"- Generated tests: `{generated_tests}`",
        "",
        "## Visual Summary",
        "",
        coverage_chart,
        "",
        yield_chart,
        "",
        composition_chart,
        "",
        "## Relation-to-Test Yield",
        "",
        f"- Required transform targets: {stats.required_transform_targets}",
        f"- Optional transform targets: {stats.optional_transform_targets}",
        f"- Transform targets total: {stats.transform_targets}",
        f"- Unique transform relations tested: {stats.unique_transform_relations_tested} ({relation_yield:.1f}%)",
        f"- Deterministic example cases: {stats.example_cases}",
        f"- Hypothesis property cases: {stats.hypothesis_cases}",
        f"- Helper boundary candidates: {stats.helper_boundary_candidates}",
        f"- Helper boundary cases: {stats.helper_boundary_cases} ({helper_yield:.1f}%)",
        f"- Common-AST candidates: {stats.common_ast_candidates}",
        f"- Common-AST cases: {stats.common_ast_cases} ({common_ast_yield:.1f}%)",
        f"- Interprocedural candidates: {stats.interprocedural_candidates}",
        f"- Interprocedural cases: {stats.interprocedural_cases} ({interprocedural_yield:.1f}%)",
        "",
        "## Coverage Delta",
        "",
        "| Suite | Covered | Total | Coverage | Return code |",
        "| --- | ---: | ---: | ---: | ---: |",
        f"| Handwritten target tests | {target_only.covered_lines} | {target_only.executable_lines} | {target_only.percent:.1f}% | {target_only.returncode} |",
        f"| Generated tests | {generated_only.covered_lines} | {generated_only.executable_lines} | {generated_only.percent:.1f}% | {generated_only.returncode} |",
        f"| Combined | {combined.covered_lines} | {combined.executable_lines} | {combined.percent:.1f}% | {combined.returncode} |",
        "",
        f"- Generated tests add {line_delta(combined, target_only)} covered lines over handwritten tests.",
        f"- Generated tests add {percent_delta(combined, target_only):.1f} percentage points over handwritten tests.",
        "",
    ]
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines), encoding="utf-8")

    payload = {
        "relations": stats.__dict__,
        "coverage": {
            "target_only": target_only.__dict__,
            "generated_only": generated_only.__dict__,
            "combined": combined.__dict__,
            "combined_minus_target": {
                "covered_lines": line_delta(combined, target_only),
                "percent_points": percent_delta(combined, target_only),
            },
        },
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    analysis_dir = Path(args.analysis_dir).resolve()
    target_project = Path(args.target_project).resolve()
    source_root = Path(args.source_root).resolve() if args.source_root else target_project
    generated_tests = Path(args.generated_tests).resolve()
    target_tests = [str(Path(path).resolve()) for path in args.target_tests]
    if not target_tests:
        target_tests = [str(target_project / "tests")]
    pytest_extra = list(args.pytest_arg)

    stats = relation_stats(analysis_dir, generated_tests)
    target_only = coverage_totals(target_tests + pytest_extra, target_project, source_root)
    generated_only = coverage_totals([str(generated_tests), *pytest_extra], target_project, source_root)
    combined = coverage_totals([*target_tests, str(generated_tests), *pytest_extra], target_project, source_root)

    markdown_path = (
        Path(args.report).resolve()
        if args.report
        else generated_tests / "evaluation_stats.md"
    )
    json_path = (
        Path(args.json_report).resolve()
        if args.json_report
        else markdown_path.with_suffix(".json")
    )
    write_reports(
        markdown_path,
        json_path,
        stats,
        target_only,
        generated_only,
        combined,
        target_tests,
        str(generated_tests),
    )
    print(markdown_path)
    print(json_path)
    raise SystemExit(max(target_only.returncode, generated_only.returncode, combined.returncode))


if __name__ == "__main__":
    main()
