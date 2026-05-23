from __future__ import annotations

import argparse
import contextlib
import io
import json
import os
import sys
import trace
from dataclasses import dataclass
from pathlib import Path


DEFAULT_OMIT_DIRS = {"tests", "manual_testing", "docs", "__pycache__"}


@dataclass(frozen=True)
class FileCoverage:
    path: Path
    relative_path: str
    executable_lines: int
    covered_lines: int
    percent: float
    missing_lines: list[int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run pytest under stdlib trace and report target-project line coverage."
    )
    parser.add_argument(
        "--target-project",
        required=True,
        help="Target Python project checkout whose source coverage should be measured.",
    )
    parser.add_argument(
        "--target-tests",
        action="append",
        default=[],
        help="Target project test path. Repeat for multiple paths.",
    )
    parser.add_argument(
        "--generated-tests",
        action="append",
        default=[],
        help="Generated test path. Repeat for multiple paths.",
    )
    parser.add_argument(
        "--source-root",
        help="Source root to measure. Defaults to --target-project.",
    )
    parser.add_argument(
        "--report",
        help="Markdown report path. Defaults to <generated-tests-dir>/coverage_stats.md when available, otherwise /tmp/sps-coverage-stats.md.",
    )
    parser.add_argument(
        "--json-report",
        help="JSON report path. Defaults to the Markdown report path with .json suffix.",
    )
    parser.add_argument(
        "--include-test-source",
        action="store_true",
        help="Include target project test files in measured source coverage.",
    )
    parser.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        help="Extra argument passed to pytest. Repeat for multiple arguments.",
    )
    parser.add_argument(
        "--no-default-tests",
        action="store_true",
        help="Do not default to <target-project>/tests when no --target-tests or --generated-tests paths are provided.",
    )
    return parser.parse_args()


def executable_lines(path: Path) -> set[int]:
    raw = trace._find_executable_linenos(str(path))  # type: ignore[attr-defined]
    return {line for line in raw if line > 0}


def should_measure(path: Path, source_root: Path, include_test_source: bool) -> bool:
    source_root = source_root.resolve()
    if path.suffix != ".py":
        return False
    try:
        relative = path.resolve().relative_to(source_root)
    except ValueError:
        return False
    if not include_test_source and any(part in DEFAULT_OMIT_DIRS for part in relative.parts):
        return False
    return True


def collect_source_files(source_root: Path, include_test_source: bool) -> list[Path]:
    source_root = source_root.resolve()
    return sorted(
        path
        for path in source_root.rglob("*.py")
        if should_measure(path, source_root, include_test_source)
    )


def summarize_coverage(
    counts: dict[tuple[str, int], int],
    source_root: Path,
    include_test_source: bool = False,
) -> list[FileCoverage]:
    source_root = source_root.resolve()
    hits_by_file: dict[Path, set[int]] = {}
    for (filename, line), count in counts.items():
        if count <= 0:
            continue
        path = Path(filename).resolve()
        if not should_measure(path, source_root, include_test_source):
            continue
        hits_by_file.setdefault(path, set()).add(line)

    summaries: list[FileCoverage] = []
    for path in collect_source_files(source_root, include_test_source):
        executable = executable_lines(path)
        hits = hits_by_file.get(path.resolve(), set()) & executable
        total = len(executable)
        covered = len(hits)
        percent = 100.0 if total == 0 else (covered / total) * 100
        summaries.append(
            FileCoverage(
                path=path,
                relative_path=str(path.relative_to(source_root)),
                executable_lines=total,
                covered_lines=covered,
                percent=percent,
                missing_lines=sorted(executable - hits),
            )
        )
    return summaries


def run_pytest_under_trace(
    pytest_args: list[str],
    target_project: Path,
) -> tuple[int, str, dict[tuple[str, int], int]]:
    import pytest

    target = str(target_project)
    if target not in sys.path:
        sys.path.insert(0, target)

    tracer = trace.Trace(
        count=True,
        trace=False,
        ignoredirs=(sys.base_prefix, sys.prefix),
    )
    output = io.StringIO()
    with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):
        returncode = tracer.runfunc(pytest.main, pytest_args)
    return returncode, output.getvalue(), tracer.results().counts


def default_report_path(generated_tests: list[str]) -> Path:
    if generated_tests:
        return Path(generated_tests[0]).resolve() / "coverage_stats.md"
    return Path("/tmp/sps-coverage-stats.md")


def write_reports(
    markdown_path: Path,
    json_path: Path,
    source_root: Path,
    target_project: Path,
    pytest_args: list[str],
    returncode: int,
    pytest_output: str,
    summaries: list[FileCoverage],
) -> None:
    total_lines = sum(item.executable_lines for item in summaries)
    total_covered = sum(item.covered_lines for item in summaries)
    total_percent = 100.0 if total_lines == 0 else (total_covered / total_lines) * 100
    uncovered = sorted(summaries, key=lambda item: (item.percent, -item.executable_lines))

    markdown_lines = [
        "# SPS-VeriSpec Coverage Stats",
        "",
        f"- Target project: `{target_project}`",
        f"- Source root: `{source_root}`",
        f"- Pytest return code: `{returncode}`",
        f"- Total line coverage: {total_covered}/{total_lines} ({total_percent:.1f}%)",
        f"- Files measured: {len(summaries)}",
        "",
        "## Command",
        "",
        "```bash",
        " ".join([sys.executable, "-m", "pytest", *pytest_args]),
        "```",
        "",
        "## Lowest Coverage Files",
        "",
    ]
    for item in uncovered[:15]:
        markdown_lines.append(
            f"- `{item.relative_path}`: {item.covered_lines}/{item.executable_lines} ({item.percent:.1f}%)"
        )

    markdown_lines.extend(
        [
            "",
            "## File Coverage",
            "",
            "| File | Covered | Total | Coverage | Missing lines |",
            "| --- | ---: | ---: | ---: | --- |",
        ]
    )
    for item in summaries:
        missing = ", ".join(str(line) for line in item.missing_lines[:30])
        if len(item.missing_lines) > 30:
            missing = f"{missing}, ..."
        markdown_lines.append(
            f"| `{item.relative_path}` | {item.covered_lines} | {item.executable_lines} | {item.percent:.1f}% | {missing or '-'} |"
        )

    markdown_lines.extend(
        [
            "",
            "## Pytest Output",
            "",
            "```text",
            pytest_output[-12000:],
            "```",
            "",
        ]
    )
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(markdown_lines), encoding="utf-8")

    json_payload = {
        "target_project": str(target_project),
        "source_root": str(source_root),
        "pytest_args": pytest_args,
        "pytest_returncode": returncode,
        "total": {
            "covered_lines": total_covered,
            "executable_lines": total_lines,
            "percent": total_percent,
        },
        "files": [
            {
                "path": item.relative_path,
                "covered_lines": item.covered_lines,
                "executable_lines": item.executable_lines,
                "percent": item.percent,
                "missing_lines": item.missing_lines,
            }
            for item in summaries
        ],
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(json_payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    target_project = Path(args.target_project).resolve()
    source_root = Path(args.source_root).resolve() if args.source_root else target_project
    target_tests = [str(Path(path).resolve()) for path in args.target_tests]
    generated_tests = [str(Path(path).resolve()) for path in args.generated_tests]
    if not target_tests and not generated_tests and not args.no_default_tests:
        target_tests = [str(target_project / "tests")]

    pytest_args = [*target_tests, *generated_tests, *args.pytest_arg]
    returncode, pytest_output, counts = run_pytest_under_trace(pytest_args, target_project)
    summaries = summarize_coverage(counts, source_root, args.include_test_source)

    markdown_path = Path(args.report).resolve() if args.report else default_report_path(generated_tests)
    json_path = (
        Path(args.json_report).resolve()
        if args.json_report
        else markdown_path.with_suffix(".json")
    )
    write_reports(
        markdown_path,
        json_path,
        source_root,
        target_project,
        pytest_args,
        returncode,
        pytest_output,
        summaries,
    )
    print(markdown_path)
    print(json_path)
    raise SystemExit(returncode)


if __name__ == "__main__":
    main()
