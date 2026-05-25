from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.oracle_synthesis import update_manifest_validation


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run generated pytest tests against a target checkout and write a validation report."
    )
    parser.add_argument(
        "generated_tests_dir",
        help="Directory containing generated pytest files.",
    )
    parser.add_argument(
        "--target-project",
        required=True,
        help="Target Python project checkout to put on PYTHONPATH.",
    )
    parser.add_argument(
        "--report",
        help="Markdown report path. Defaults to <generated_tests_dir>/validation_report.md.",
    )
    parser.add_argument(
        "--pytest-arg",
        action="append",
        default=[],
        help="Extra argument passed to pytest. Repeat for multiple arguments.",
    )
    parser.add_argument(
        "--oracle-candidates-manifest",
        help=(
            "Optional oracle_candidates.json path. When supplied, failures are "
            "recorded as quarantined oracle conflicts and this command exits 0."
        ),
    )
    return parser.parse_args()


def parse_pytest_counts(output: str) -> dict[str, int]:
    counts = {"passed": 0, "failed": 0, "skipped": 0, "xfailed": 0, "xpassed": 0, "errors": 0}
    pattern = re.compile(
        r"(?P<count>\d+)\s+"
        r"(?P<kind>passed|failed|skipped|xfailed|xpassed|errors?)"
    )
    for match in pattern.finditer(output):
        kind = match.group("kind")
        if kind == "error":
            kind = "errors"
        counts[kind] = counts.get(kind, 0) + int(match.group("count"))
    return counts


def write_report(
    path: Path,
    generated_tests_dir: Path,
    target_project: Path,
    command: list[str],
    returncode: int,
    counts: dict[str, int],
    output: str,
    oracle_manifest: Path | None = None,
    oracle_classification: str | None = None,
) -> None:
    clipped_output = output[-12000:]
    lines = [
        "# Generated Test Validation Report",
        "",
        f"- Generated tests: `{generated_tests_dir}`",
        f"- Target project: `{target_project}`",
        f"- Return code: `{returncode}`",
        f"- Passed: {counts.get('passed', 0)}",
        f"- Failed: {counts.get('failed', 0)}",
        f"- Errors: {counts.get('errors', 0)}",
        f"- Skipped: {counts.get('skipped', 0)}",
        f"- XFailed: {counts.get('xfailed', 0)}",
        f"- XPassed: {counts.get('xpassed', 0)}",
    ]
    if oracle_manifest is not None:
        lines.extend(
            [
                f"- Oracle candidates manifest: `{oracle_manifest}`",
                f"- Quarantined oracle classification: `{oracle_classification}`",
                "- Quarantined oracle failures are review records, not trusted generated-suite failures.",
            ]
        )
    lines.extend(
        [
            "",
            "## Command",
            "",
            "```bash",
            " ".join(command),
            "```",
            "",
            "## Pytest Output",
            "",
            "```text",
            clipped_output,
            "```",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def classify_oracle_validation(returncode: int, counts: dict[str, int]) -> tuple[str, str]:
    if counts.get("errors", 0):
        return "error", "dependency_blocked"
    if counts.get("failed", 0):
        return "failed", "design_conflict"
    if counts.get("passed", 0):
        return "passed", "promotion_candidate"
    if counts.get("skipped", 0) or counts.get("xfailed", 0):
        return "skipped", "needs_review"
    if returncode == 0:
        return "passed", "promotion_candidate"
    return "error", "dependency_blocked"


def main() -> None:
    args = parse_args()
    generated_tests_dir = Path(args.generated_tests_dir).resolve()
    target_project = Path(args.target_project).resolve()
    default_report_dir = generated_tests_dir if generated_tests_dir.is_dir() else generated_tests_dir.parent
    report_path = Path(args.report).resolve() if args.report else default_report_dir / "validation_report.md"
    oracle_manifest = (
        Path(args.oracle_candidates_manifest).resolve()
        if args.oracle_candidates_manifest
        else None
    )

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(target_project)
        if not existing_pythonpath
        else f"{target_project}{os.pathsep}{existing_pythonpath}"
    )

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        str(generated_tests_dir),
        *args.pytest_arg,
    ]
    if oracle_manifest is not None and "--runxfail" not in command:
        command.append("--runxfail")
    completed = subprocess.run(
        command,
        check=False,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    counts = parse_pytest_counts(completed.stdout)
    oracle_classification = None
    if oracle_manifest is not None:
        validation_result, oracle_classification = classify_oracle_validation(
            completed.returncode,
            counts,
        )
        update_manifest_validation(
            oracle_manifest,
            validation_result,  # type: ignore[arg-type]
            oracle_classification,  # type: ignore[arg-type]
        )
    write_report(
        report_path,
        generated_tests_dir,
        target_project,
        command,
        completed.returncode,
        counts,
        completed.stdout,
        oracle_manifest,
        oracle_classification,
    )
    print(report_path)
    if oracle_manifest is not None:
        raise SystemExit(0)
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
