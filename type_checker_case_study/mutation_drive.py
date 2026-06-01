"""Mutation evaluation for the type-checker case study.

The repo's ``tools/mutation_eval.py`` generates mutants from dataclass-specific
facts, so it has nothing to mutate here. But its report machinery is generic, so
this driver reuses ``Mutant``, ``apply_mutant``, ``score``, and ``write_reports``
and supplies its own mutation operators: deliberate breakages of the *type
checker logic* (disable the occurs check, skip branch/condition unification,
short-circuit application unification).

A mutant is "killed" if a suite fails on the mutated oracle. We score three
suites, matching the dataclass lane's report shape:

  * target    -- the handwritten parity/unit tests (`tests/`)
  * generated -- the strict-oracle boundary suite from `generate_flip_tests.py`
  * combined  -- both

Each mutant runs against a fresh copy of the package so the real source is never
touched. We run with ``cwd`` set to the temp root (not the repo root) so that
``python -m pytest`` puts the *mutated* copy first on ``sys.path``.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.mutation_eval import Mutant, apply_mutant, score, write_reports

PKG = "type_checker_case_study"
GENERATED_SUITE_REL = f"generated_tests/{PKG}/test_generated_composition_boundaries.py"
PARITY_SUITE_REL = f"{PKG}/tests"


@dataclass(frozen=True)
class MutantSpec:
    """A token mutation anchored by a unique source substring.

    The anchor avoids hard-coded line numbers: we resolve the line at runtime by
    scanning the oracle source, so the spec survives edits to the file.
    """

    file_rel: str  # relative to the package, e.g. "oracle/types.py"
    anchor: str  # unique substring identifying the line to mutate
    original: str  # token to replace on that line
    replacement: str
    operator: str
    reason: str


# Each spec breaks one rule of Algorithm W. If the rule matters, some suite kills
# it; a survivor means no test exercises that rule (a coverage gap worth knowing).
MUTANT_SPECS = [
    MutantSpec(
        file_rel="oracle/types.py",
        anchor="if occurs_in_ty(n, ty):",
        original="occurs_in_ty(n, ty)",
        replacement="False",
        operator="disable_occurs_check",
        reason="never trigger the occurs check (lets self-application type-check)",
    ),
    MutantSpec(
        file_rel="oracle/types.py",
        anchor="subst_unify_cond = unify(cond_ty, TBool())",
        original="TBool()",
        replacement="cond_ty",
        operator="skip_condition_unify",
        reason="unify the if-condition with itself instead of Bool (drops the Bool requirement)",
    ),
    MutantSpec(
        file_rel="oracle/types.py",
        anchor="subst_unify_else = unify(then_ty_s, else_ty)",
        original="unify(then_ty_s, else_ty)",
        replacement="[]",
        operator="skip_branch_unify",
        reason="skip unifying the if branches (drops the heterogeneous-if check)",
    ),
    MutantSpec(
        file_rel="oracle/types.py",
        anchor="subst_unify = unify(apply_subst_ty(subst_arg, fun_ty), fun_ty_expected)",
        original="unify(apply_subst_ty(subst_arg, fun_ty), fun_ty_expected)",
        replacement="[]",
        operator="skip_application_unify",
        reason="skip unifying the applied function type (drops application-mismatch)",
    ),
    MutantSpec(
        file_rel="oracle/types.py",
        anchor="fun_ty = TFun(apply_subst_ty(subst, param_ty), body_ty)",
        original="TFun(apply_subst_ty(subst, param_ty), body_ty)",
        replacement="TFun(body_ty, body_ty)",
        operator="corrupt_lambda_type",
        reason="build the lambda type from the body twice instead of param->body",
    ),
]


def resolve_mutants(package_dir: Path) -> list[Mutant]:
    mutants: list[Mutant] = []
    for index, spec in enumerate(MUTANT_SPECS, start=1):
        source_path = package_dir / spec.file_rel
        lines = source_path.read_text(encoding="utf-8").splitlines()
        line_no = next(
            (i for i, line in enumerate(lines, start=1) if spec.anchor in line),
            None,
        )
        if line_no is None:
            raise SystemExit(
                f"Anchor not found for mutant {spec.operator!r}: {spec.anchor!r}"
            )
        mutants.append(
            Mutant(
                id=f"m{index:03d}",
                module_name=f"{PKG}.{spec.file_rel.replace('/', '.').removesuffix('.py')}",
                qualified_name=spec.operator,
                relative_path=f"{PKG}/{spec.file_rel}",
                line=line_no,
                operator=spec.operator,
                original=spec.original,
                replacement=spec.replacement,
                reason=spec.reason,
            )
        )
    return mutants


def copy_workspace(temp_root: Path) -> None:
    """Copy the package and the generated suite into a fresh temp workspace."""
    ignore = shutil.ignore_patterns(
        "__pycache__", "*.pyc", ".pytest_cache", "out", "policy_work"
    )
    shutil.copytree(ROOT / PKG, temp_root / PKG, ignore=ignore)
    suite_src = ROOT / GENERATED_SUITE_REL
    suite_dst = temp_root / GENERATED_SUITE_REL
    suite_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(suite_src, suite_dst)


def run_suite(temp_root: Path, test_rel_paths: list[str], pytest_args: list[str]) -> bool:
    """Return True if the suite was *killed* (i.e. failed) on the mutated copy."""
    env = os.environ.copy()
    # Put the temp workspace first so the mutated package wins over any installed copy.
    env["PYTHONPATH"] = str(temp_root) + (
        os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else ""
    )
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        *test_rel_paths,
        *pytest_args,
    ]
    completed = subprocess.run(
        command,
        check=False,
        cwd=temp_root,  # `python -m` prepends cwd, so the mutated copy is sys.path[0]
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return completed.returncode != 0


def evaluate(mutants: list[Mutant], pytest_args: list[str]) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for mutant in mutants:
        with tempfile.TemporaryDirectory(prefix="sps-tc-mutant-") as temp_dir:
            temp_root = Path(temp_dir)
            copy_workspace(temp_root)
            apply_mutant(temp_root, mutant)
            target_killed = run_suite(temp_root, [PARITY_SUITE_REL], pytest_args)
            generated_killed = run_suite(temp_root, [GENERATED_SUITE_REL], pytest_args)
            combined_killed = run_suite(
                temp_root, [PARITY_SUITE_REL, GENERATED_SUITE_REL], pytest_args
            )
            results.append(
                {
                    "mutant": mutant.__dict__,
                    "target": {"killed": target_killed},
                    "generated": {"killed": generated_killed},
                    "combined": {"killed": combined_killed},
                }
            )
    return results


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report",
        help="Markdown report path. Defaults to the generated suite dir / mutation_eval.md.",
    )
    parser.add_argument("--json-report")
    parser.add_argument("--pytest-arg", action="append", default=[])
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    markdown_path = (
        Path(args.report).resolve()
        if args.report
        else ROOT / "generated_tests" / PKG / "mutation_eval.md"
    )
    json_path = (
        Path(args.json_report).resolve()
        if args.json_report
        else markdown_path.with_suffix(".json")
    )

    mutants = resolve_mutants(ROOT / PKG)
    results = evaluate(mutants, list(args.pytest_arg))
    write_reports(markdown_path, json_path, results)

    killed, total, percent = score(results, "combined")
    print(f"combined mutation score: {killed}/{total} ({percent:.1f}%)")
    print(markdown_path)
    print(json_path)


if __name__ == "__main__":
    main()
