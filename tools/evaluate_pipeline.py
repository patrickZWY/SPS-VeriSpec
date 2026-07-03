from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class StepResult:
    name: str
    command: list[str]
    returncode: int
    outputs: list[str]
    enabled: bool


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the SPS-VeriSpec pipeline for one target and collect stage artifacts."
    )
    parser.add_argument("--target-project", required=True)
    parser.add_argument("--project-name", required=True)
    parser.add_argument("--work-dir", default="/tmp/sps-evaluate-pipeline")
    parser.add_argument("--source-root", help="Source root for coverage/evaluation. Defaults to --target-project.")
    parser.add_argument("--target-tests", action="append", default=[])
    parser.add_argument("--include-tests", action="store_true")
    parser.add_argument("--rule-mode", choices=("static", "llm", "combined"), default="static")
    parser.add_argument("--import-prefix", default="")
    parser.add_argument("--pytest-arg", action="append", default=[])
    parser.add_argument("--skip-mutation", action="store_true")
    parser.add_argument("--with-static-metamorphic", action="store_true")
    parser.add_argument("--with-invariants", action="store_true")
    parser.add_argument("--invariant-spec")
    parser.add_argument("--with-plateau", action="store_true")
    parser.add_argument("--llm-proposals")
    parser.add_argument(
        "--with-local-llm-semantic-assist",
        action="store_true",
        help=(
            "After plateau candidate extraction, ask a local LLM for quarantined "
            "semantic test proposals and re-render plateau candidates with them."
        ),
    )
    parser.add_argument("--local-llm-provider", choices=("ollama", "openai-compatible"), default="ollama")
    parser.add_argument("--local-llm-base-url")
    parser.add_argument("--local-llm-model", default="qwen2.5-coder:7b")
    parser.add_argument("--local-llm-max-candidates", type=int, default=12)
    parser.add_argument("--report", help="Markdown report path. Defaults to <work-dir>/pipeline_report.md.")
    parser.add_argument("--json-report", help="JSON report path. Defaults to Markdown path with .json suffix.")
    return parser.parse_args()


def run_step(name: str, command: list[str], *, check: bool = True) -> StepResult:
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=ROOT,
    )
    outputs = [
        line.strip()
        for line in completed.stdout.splitlines()
        if line.strip().startswith("/")
    ]
    if check and completed.returncode != 0:
        raise subprocess.CalledProcessError(
            completed.returncode,
            command,
            output=completed.stdout,
        )
    return StepResult(
        name=name,
        command=command,
        returncode=completed.returncode,
        outputs=outputs,
        enabled=True,
    )


def disabled_step(name: str) -> StepResult:
    return StepResult(name=name, command=[], returncode=0, outputs=[], enabled=False)


def write_reports(path: Path, json_path: Path, steps: list[StepResult]) -> None:
    lines = [
        "# SPS-VeriSpec Pipeline Report",
        "",
        "## Steps",
        "",
    ]
    for step in steps:
        status = "disabled" if not step.enabled else ("ok" if step.returncode == 0 else f"failed ({step.returncode})")
        lines.append(f"- `{step.name}`: {status}")
        if step.command:
            lines.append(f"  command: `{' '.join(step.command)}`")
        for output in step.outputs:
            lines.append(f"  output: `{output}`")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")
    json_path.write_text(
        json.dumps({"steps": [asdict(step) for step in steps]}, indent=2),
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    target_project = Path(args.target_project).resolve()
    work_dir = Path(args.work_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    generated_tests_dir = work_dir / "generated_tests" / args.project_name
    analysis_dir = work_dir / "analysis"
    source_root = Path(args.source_root).resolve() if args.source_root else target_project
    report_path = Path(args.report).resolve() if args.report else work_dir / "pipeline_report.md"
    json_report_path = Path(args.json_report).resolve() if args.json_report else report_path.with_suffix(".json")

    python = sys.executable
    target_tests = list(args.target_tests)
    pytest_args = list(args.pytest_arg)
    llm_proposals = Path(args.llm_proposals).resolve() if args.llm_proposals else None

    steps: list[StepResult] = []

    static_cmd = [
        python,
        str(ROOT / "tools" / "run_static_analysis.py"),
        str(target_project),
        "--work-dir",
        str(analysis_dir),
        "--rule-mode",
        args.rule_mode,
    ]
    if args.include_tests:
        static_cmd.append("--include-tests")
    steps.append(run_step("static_analysis", static_cmd))

    generate_cmd = [
        python,
        str(ROOT / "tools" / "generate_pytest_from_properties.py"),
        "--analysis-dir",
        str(analysis_dir),
        "--output-dir",
        str(work_dir / "generated_tests"),
        "--project-name",
        args.project_name,
        "--import-prefix",
        args.import_prefix,
    ]
    if llm_proposals is not None:
        generate_cmd.extend(["--llm-oracle-proposals", str(llm_proposals)])
    steps.append(run_step("generate_tests", generate_cmd))

    validate_cmd = [
        python,
        str(ROOT / "tools" / "validate_generated_tests.py"),
        str(generated_tests_dir),
        "--target-project",
        str(target_project),
    ]
    for arg in pytest_args:
        validate_cmd.extend(["--pytest-arg", arg])
    steps.append(run_step("validate_generated", validate_cmd, check=False))

    generator_cov_cmd = [
        python,
        str(ROOT / "tools" / "generator_coverage.py"),
        "--analysis-dir",
        str(analysis_dir),
        "--generated-tests",
        str(generated_tests_dir),
    ]
    steps.append(run_step("generator_coverage", generator_cov_cmd))

    eval_cmd = [
        python,
        str(ROOT / "tools" / "evaluation_stats.py"),
        "--analysis-dir",
        str(analysis_dir),
        "--target-project",
        str(target_project),
        "--generated-tests",
        str(generated_tests_dir),
        "--source-root",
        str(source_root),
    ]
    for target_test in target_tests:
        eval_cmd.extend(["--target-tests", target_test])
    for arg in pytest_args:
        eval_cmd.extend(["--pytest-arg", arg])
    steps.append(run_step("evaluation_stats", eval_cmd, check=False))

    if args.skip_mutation:
        steps.append(disabled_step("mutation_eval"))
    else:
        mutation_cmd = [
            python,
            str(ROOT / "tools" / "mutation_eval.py"),
            "--analysis-dir",
            str(analysis_dir),
            "--target-project",
            str(target_project),
            "--generated-tests",
            str(generated_tests_dir),
        ]
        for target_test in target_tests:
            mutation_cmd.extend(["--target-tests", target_test])
        for arg in pytest_args:
            mutation_cmd.extend(["--pytest-arg", arg])
        steps.append(run_step("mutation_eval", mutation_cmd, check=False))

    if args.with_static_metamorphic:
        metamorphic_cmd = [
            python,
            str(ROOT / "tools" / "metamorphic_eval_static_analysis.py"),
            str(target_project),
            "--work-dir",
            str(work_dir / "static_analysis_metamorphic"),
        ]
        if args.include_tests:
            metamorphic_cmd.append("--include-tests")
        steps.append(run_step("static_metamorphic", metamorphic_cmd))
    else:
        steps.append(disabled_step("static_metamorphic"))

    if args.with_invariants and args.invariant_spec:
        invariant_cmd = [
            python,
            str(ROOT / "tools" / "mine_invariants.py"),
            "--spec",
            str(Path(args.invariant_spec).resolve()),
            "--target-project",
            str(target_project),
            "--output-dir",
            str(work_dir / "generated_tests"),
            "--project-name",
            args.project_name,
        ]
        steps.append(run_step("mine_invariants", invariant_cmd))
    else:
        steps.append(disabled_step("mine_invariants"))

    if args.with_plateau:
        plateau_cmd = [
            python,
            str(ROOT / "tools" / "llm_candidate_generation.py"),
            "--analysis-dir",
            str(analysis_dir),
            "--generated-tests",
            str(generated_tests_dir),
            "--output-dir",
            str(generated_tests_dir),
        ]
        if llm_proposals is not None:
            plateau_cmd.extend(["--llm-proposals", str(llm_proposals)])
        steps.append(run_step("llm_plateau", plateau_cmd))
        if args.with_local_llm_semantic_assist:
            local_proposals = generated_tests_dir / "local_llm_semantic_proposals.json"
            local_cmd = [
                python,
                str(ROOT / "tools" / "local_llm_semantic_assist.py"),
                "--input",
                str(generated_tests_dir / "llm_plateau_input.json"),
                "--output",
                str(local_proposals),
                "--provider",
                args.local_llm_provider,
                "--model",
                args.local_llm_model,
                "--max-candidates",
                str(args.local_llm_max_candidates),
            ]
            if args.local_llm_base_url:
                local_cmd.extend(["--base-url", args.local_llm_base_url])
            local_result = run_step("local_llm_semantic_assist", local_cmd, check=False)
            steps.append(local_result)
            if local_result.returncode == 0:
                rerender_cmd = [
                    python,
                    str(ROOT / "tools" / "llm_candidate_generation.py"),
                    "--analysis-dir",
                    str(analysis_dir),
                    "--generated-tests",
                    str(generated_tests_dir),
                    "--output-dir",
                    str(generated_tests_dir),
                    "--llm-proposals",
                    str(local_proposals),
                ]
                steps.append(run_step("llm_plateau_with_local_proposals", rerender_cmd))
    else:
        steps.append(disabled_step("llm_plateau"))
        if args.with_local_llm_semantic_assist:
            steps.append(disabled_step("local_llm_semantic_assist"))

    write_reports(report_path, json_report_path, steps)
    print(report_path)
    print(json_report_path)

    enabled_returncodes = [step.returncode for step in steps if step.enabled]
    raise SystemExit(max(enabled_returncodes) if enabled_returncodes else 0)


if __name__ == "__main__":
    main()
