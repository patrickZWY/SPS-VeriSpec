from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.python_to_souffle import extract_facts_from_path, write_souffle_facts
from tools.run_souffle_models import MODELS, write_summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run one static-analysis backend over a Python project."
    )
    parser.add_argument("project_root", help="Path to the Python project to analyze.")
    parser.add_argument(
        "--engine",
        choices=("souffle", "python"),
        default="souffle",
        help=(
            "`souffle` runs the Datalog analysis backend. `python` runs only "
            "the Python extractor/fact inventory backend."
        ),
    )
    parser.add_argument(
        "--work-dir",
        default="/tmp/sps-static-analysis",
        help="Directory for generated facts, backend outputs, and the summary report.",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include tests and manual testing files when extracting facts.",
    )
    return parser.parse_args()


def run_command(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, cwd=ROOT)


def extract_to_facts_dir(project_root: Path, facts_dir: Path, include_tests: bool) -> int:
    facts = extract_facts_from_path(project_root, include_tests=include_tests)
    write_souffle_facts(facts, facts_dir)
    return len(facts)


def write_python_fact_inventory(facts_dir: Path, work_dir: Path, fact_count: int) -> Path:
    python_dir = work_dir / "python_out"
    python_dir.mkdir(parents=True, exist_ok=True)

    counts: Counter[str] = Counter()
    for path in sorted(facts_dir.glob("*.facts")):
        with path.open(encoding="utf-8", newline="") as handle:
            counts[path.stem] = sum(1 for row in csv.reader(handle, delimiter="\t") if row)

    fact_counts_path = python_dir / "fact_counts.csv"
    with fact_counts_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        for predicate, count in sorted(counts.items()):
            writer.writerow([predicate, count])

    summary_path = work_dir / "summary.md"
    lines = [
        "# Python Static Fact Summary",
        "",
        "This run used only the Python extractor/fact-inventory backend. It did not",
        "run Souffle, so derived Datalog relations such as interprocedural flows,",
        "program slices, abstract states, typestate candidates, and boundary",
        "behaviors are intentionally absent from this output.",
        "",
        "## Inventory",
        "",
        f"- Total facts emitted: {fact_count}",
        f"- Predicate families: {len(counts)}",
        f"- Fact count table: `{fact_counts_path}`",
        "",
        "## Largest Fact Relations",
        "",
    ]
    for predicate, count in counts.most_common(20):
        lines.append(f"- `{predicate}`: {count}")
    lines.append("")
    summary_path.write_text("\n".join(lines), encoding="utf-8")
    return summary_path


def run_python_backend(project_root: Path, work_dir: Path, include_tests: bool) -> Path:
    facts_dir = work_dir / "facts"
    facts_dir.mkdir(parents=True, exist_ok=True)
    fact_count = extract_to_facts_dir(project_root, facts_dir, include_tests)
    return write_python_fact_inventory(facts_dir, work_dir, fact_count)


def run_souffle_backend(project_root: Path, work_dir: Path, include_tests: bool) -> Path:
    if shutil.which("souffle") is None:
        raise SystemExit("souffle is not installed or not on PATH.")

    facts_dir = work_dir / "facts"
    output_dirs = {
        "schema": work_dir / "schema_out",
        "effect": work_dir / "effect_out",
        "deduction": work_dir / "deduction_out",
        "test": work_dir / "test_out",
        "semantic": work_dir / "semantic_out",
    }
    for path in (facts_dir, *output_dirs.values()):
        path.mkdir(parents=True, exist_ok=True)

    extract_to_facts_dir(project_root, facts_dir, include_tests)

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

    return write_summary(work_dir)


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    work_dir = Path(args.work_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    if args.engine == "python":
        summary_path = run_python_backend(project_root, work_dir, args.include_tests)
    else:
        summary_path = run_souffle_backend(project_root, work_dir, args.include_tests)
    print(summary_path)


if __name__ == "__main__":
    main()
