from __future__ import annotations

import argparse
import csv
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Mutant:
    id: str
    module_name: str
    qualified_name: str
    relative_path: str
    line: int
    operator: str
    original: str
    replacement: str
    reason: str


@dataclass(frozen=True)
class SuiteResult:
    returncode: int
    output_tail: str

    @property
    def killed(self) -> bool:
        return self.returncode != 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run boundary-guided mutation evaluation for target and generated tests."
    )
    parser.add_argument("--analysis-dir", required=True)
    parser.add_argument("--target-project", required=True)
    parser.add_argument("--target-tests", action="append", default=[])
    parser.add_argument("--generated-tests", required=True)
    parser.add_argument("--report", help="Markdown report path. Defaults to <generated-tests>/mutation_eval.md.")
    parser.add_argument("--json-report", help="JSON report path. Defaults to Markdown report path with .json suffix.")
    parser.add_argument("--max-mutants", type=int, default=12)
    parser.add_argument("--pytest-arg", action="append", default=[])
    return parser.parse_args()


def read_tsv(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.reader(handle, delimiter="\t") if row]


def module_files(analysis_dir: Path) -> dict[str, str]:
    files: dict[str, str] = {}
    for row in read_tsv(analysis_dir / "facts" / "module_file.facts"):
        if len(row) >= 2:
            files[row[0]] = row[1]
    return files


def replace_first_token(line: str, original: str, replacement: str) -> str | None:
    pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(original)}(?![A-Za-z0-9_])")
    changed = pattern.sub(replacement, line, count=1)
    return changed if changed != line else None


def operator_mutations(line: str) -> list[tuple[str, str, str]]:
    mutations: list[tuple[str, str, str]] = []
    ordered = [
        ("<=", "<", "tighten inclusive upper/lower boundary"),
        (">=", ">", "tighten inclusive upper/lower boundary"),
        (">", ">=", "weaken exclusive lower boundary"),
        ("<", "<=", "weaken exclusive upper boundary"),
    ]
    for original, replacement, reason in ordered:
        if original in line:
            mutations.append((original, replacement, reason))
            break
    return mutations


def solved_constant_replacements(bound: int, relation_kind: str) -> list[tuple[int, str]]:
    candidates = {
        bound - 1: "solver-adjacent below boundary",
        bound + 1: "solver-adjacent above boundary",
    }
    if relation_kind == "upper_exclusive":
        candidates[bound + 3] = "solver-adjacent truncation/suffix stress"
    if relation_kind == "lower_exclusive":
        candidates[max(bound - 3, 0)] = "solver-adjacent lower-bound stress"
    return [(value, reason) for value, reason in candidates.items() if value >= 0 and value != bound]


def replacement_for_field(field_name: str) -> str:
    replacements = {
        "name": "pet.breed",
        "breed": "pet.species",
        "species": "pet.breed",
        "location": '"mutated-location"',
        "description": '""',
        "image_url": "None",
        "adoption_url": "None",
    }
    return replacements.get(field_name, '""')


def add_transform_mutants(
    analysis_dir: Path,
    target_project: Path,
    files: dict[str, str],
    mutants: list[Mutant],
    seen: set[tuple[str, int, str, str]],
    max_mutants: int,
    transform_limit: int,
) -> None:
    for row in read_tsv(analysis_dir / "facts" / "field_flows_to_constructor_arg.facts"):
        if len(row) < 7 or len(mutants) >= max_mutants or len(mutants) >= transform_limit:
            break
        module_name, qualified_name, source_owner, source_field, target_class, target_arg, line_text = row[:7]
        if "format_post" not in qualified_name:
            continue
        if source_owner != "pet":
            continue
        if target_class != "Post":
            continue
        relative_path = files.get(module_name)
        if relative_path is None:
            continue
        try:
            line_no = int(line_text)
        except ValueError:
            continue
        path = target_project / relative_path
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if line_no < 1 or line_no > len(lines):
            continue
        source_line = lines[line_no - 1]
        original = f"{source_owner}.{source_field}"
        if original not in source_line:
            continue
        replacement = replacement_for_field(source_field)
        key = (relative_path, line_no, original, replacement)
        if key in seen:
            continue
        seen.add(key)
        mutants.append(
            Mutant(
                id=f"m{len(mutants) + 1:03d}",
                module_name=module_name,
                qualified_name=qualified_name,
                relative_path=relative_path,
                line=line_no,
                operator="field_reference_replace",
                original=original,
                replacement=replacement,
                reason=f"relation-guided transform mutation for `{source_field} -> {target_arg}`",
            )
        )


def add_collection_iteration_mutants(
    analysis_dir: Path,
    target_project: Path,
    files: dict[str, str],
    mutants: list[Mutant],
    seen: set[tuple[str, int, str, str]],
    max_mutants: int,
) -> None:
    for row in read_tsv(analysis_dir / "semantic_out" / "dataclass_collection_iteration.csv"):
        if len(row) < 7 or len(mutants) >= max_mutants:
            break
        module_name, qualified_name, _source_module, source_class, source_field, item_name, iteration_kind = row[:7]
        relative_path = files.get(module_name)
        if relative_path is None:
            continue
        path = target_project / relative_path
        if not path.exists():
            continue

        lines = path.read_text(encoding="utf-8").splitlines()
        for index, source_line in enumerate(lines, start=1):
            if source_field not in source_line or item_name not in source_line:
                continue
            if " for " not in source_line:
                continue

            replacements = [
                (f"{source_field})", "[])", "drop iterated dataclass collection"),
                (f"{source_field} ", "[] ", "drop iterated dataclass collection"),
                (f"{source_field}]", "[]]", "drop iterated dataclass collection"),
                (item_name, '""', "drop iterated item contribution"),
            ]
            for original, replacement, reason in replacements:
                key = (relative_path, index, original, replacement)
                if original not in source_line or key in seen or len(mutants) >= max_mutants:
                    continue
                seen.add(key)
                mutants.append(
                    Mutant(
                        id=f"m{len(mutants) + 1:03d}",
                        module_name=module_name,
                        qualified_name=qualified_name,
                        relative_path=relative_path,
                        line=index,
                        operator="collection_iteration_replace",
                        original=original,
                        replacement=replacement,
                        reason=(
                            f"common-AST collection iteration mutation for "
                            f"`{source_class}.{source_field}` via `{iteration_kind}`"
                        ),
                    )
                )
            break


def add_interprocedural_pipeline_mutants(
    analysis_dir: Path,
    target_project: Path,
    files: dict[str, str],
    mutants: list[Mutant],
    seen: set[tuple[str, int, str, str]],
    max_mutants: int,
) -> None:
    multi_hop_pairs = {
        (row[0], row[1], row[3], row[4])
        for row in read_tsv(analysis_dir / "semantic_out" / "multi_hop_interprocedural_field_flow.csv")
        if len(row) >= 6
    }
    if not multi_hop_pairs:
        return

    for row in read_tsv(analysis_dir / "test_out" / "method_dataclass_transform.csv"):
        if len(row) < 7 or len(mutants) >= max_mutants:
            break
        class_module, _class_name, qualified_name, source_module, source_class, target_module, target_class = row[:7]
        method = qualified_name.rsplit(".", 1)[-1]
        if method.startswith("_") or method == "publish":
            continue
        if (source_module, source_class, target_module, target_class) not in multi_hop_pairs:
            continue
        relative_path = files.get(class_module)
        if relative_path is None:
            continue
        path = target_project / relative_path
        if not path.exists():
            continue

        lines = path.read_text(encoding="utf-8").splitlines()
        method_start = None
        method_indent = 0
        method_pattern = re.compile(rf"^(\s*)def\s+{re.escape(method)}\s*\(")
        for index, source_line in enumerate(lines):
            match = method_pattern.match(source_line)
            if match:
                method_start = index
                method_indent = len(match.group(1))
                break
        if method_start is None:
            continue
        method_end = len(lines)
        next_def_pattern = re.compile(r"^(\s*)def\s+\w+")
        for index in range(method_start + 1, len(lines)):
            match = next_def_pattern.match(lines[index])
            if match and len(match.group(1)) <= method_indent:
                method_end = index
                break

        replacements = [
            (
                "self.format_post",
                "lambda pet: Post(text='', image_url=None, link=None, alt_text=None, tags=[])",
                "replace composed pipeline formatting phase with empty output",
            ),
            (
                "self._prepare_caption",
                "lambda post: PreparedCaption(post=post, caption_text='', tags=[], tag_suffix='')",
                "replace composed pipeline preparation phase with empty output",
            ),
        ]
        for index in range(method_start + 1, method_end):
            source_line = lines[index]
            if len(mutants) >= max_mutants:
                break
            if not any(original in source_line for original, _, _ in replacements):
                continue
            for original, replacement, reason in replacements:
                if original not in source_line or len(mutants) >= max_mutants:
                    continue
                key = (relative_path, index, original, replacement)
                if key in seen:
                    continue
                seen.add(key)
                mutants.append(
                    Mutant(
                        id=f"m{len(mutants) + 1:03d}",
                        module_name=class_module,
                        qualified_name=qualified_name,
                        relative_path=relative_path,
                        line=index + 1,
                        operator="interprocedural_pipeline_replace",
                        original=original,
                        replacement=replacement,
                        reason=(
                            f"interprocedural pipeline mutation for "
                            f"`{source_class} -> {target_class}`"
                        ),
                    )
                )


def generate_mutants(analysis_dir: Path, target_project: Path, max_mutants: int) -> list[Mutant]:
    files = module_files(analysis_dir)
    mutants: list[Mutant] = []
    seen: set[tuple[str, int, str, str]] = set()
    transform_limit = max(1, max_mutants // 2)

    add_transform_mutants(
        analysis_dir,
        target_project,
        files,
        mutants,
        seen,
        max_mutants,
        transform_limit,
    )

    add_collection_iteration_mutants(
        analysis_dir,
        target_project,
        files,
        mutants,
        seen,
        max_mutants,
    )

    add_interprocedural_pipeline_mutants(
        analysis_dir,
        target_project,
        files,
        mutants,
        seen,
        max_mutants,
    )

    for row in read_tsv(analysis_dir / "semantic_out" / "numeric_bound.csv"):
        if len(row) < 6 or len(mutants) >= max_mutants:
            break
        module_name, qualified_name, expression, relation_kind, bound_text, line_text = row[:6]
        relative_path = files.get(module_name)
        if relative_path is None:
            continue
        try:
            bound = int(bound_text)
            line_no = int(line_text)
        except ValueError:
            continue

        path = target_project / relative_path
        if not path.exists():
            continue
        lines = path.read_text(encoding="utf-8").splitlines()
        if line_no < 1 or line_no > len(lines):
            continue
        source_line = lines[line_no - 1]

        for original, replacement, reason in operator_mutations(source_line):
            key = (relative_path, line_no, original, replacement)
            if key not in seen and len(mutants) < max_mutants:
                seen.add(key)
                mutants.append(
                    Mutant(
                        id=f"m{len(mutants) + 1:03d}",
                        module_name=module_name,
                        qualified_name=qualified_name,
                        relative_path=relative_path,
                        line=line_no,
                        operator="operator_replace",
                        original=original,
                        replacement=replacement,
                        reason=reason,
                    )
                )

        for value, reason in solved_constant_replacements(bound, relation_kind):
            changed = replace_first_token(source_line, str(bound), str(value))
            if changed is None:
                continue
            key = (relative_path, line_no, str(bound), str(value))
            if key not in seen and len(mutants) < max_mutants:
                seen.add(key)
                mutants.append(
                    Mutant(
                        id=f"m{len(mutants) + 1:03d}",
                        module_name=module_name,
                        qualified_name=qualified_name,
                        relative_path=relative_path,
                        line=line_no,
                        operator="constant_replace",
                        original=str(bound),
                        replacement=str(value),
                        reason=reason,
                    )
                )

        if '"..."' in source_line and len(mutants) < max_mutants:
            key = (relative_path, line_no, '"..."', '""')
            if key not in seen:
                seen.add(key)
                mutants.append(
                    Mutant(
                        id=f"m{len(mutants) + 1:03d}",
                        module_name=module_name,
                        qualified_name=qualified_name,
                        relative_path=relative_path,
                        line=line_no,
                        operator="string_literal_replace",
                        original='"..."',
                        replacement='""',
                        reason="remove truncation marker",
                    )
                )

    return mutants


def copy_target(source: Path, destination: Path) -> None:
    ignore = shutil.ignore_patterns(".git", "__pycache__", "*.pyc", ".pytest_cache")
    shutil.copytree(source, destination, ignore=ignore)


def apply_mutant(project_root: Path, mutant: Mutant) -> None:
    path = project_root / mutant.relative_path
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    index = mutant.line - 1
    original_line = lines[index]
    if mutant.operator == "operator_replace":
        if mutant.original not in original_line:
            raise ValueError(f"Cannot find operator {mutant.original!r} in {path}:{mutant.line}")
        lines[index] = original_line.replace(mutant.original, mutant.replacement, 1)
    else:
        pattern = re.compile(rf"(?<![A-Za-z0-9_]){re.escape(mutant.original)}(?![A-Za-z0-9_])")
        changed = pattern.sub(mutant.replacement, original_line, count=1)
        if changed == original_line:
            raise ValueError(f"Cannot find token {mutant.original!r} in {path}:{mutant.line}")
        lines[index] = changed
    path.write_text("".join(lines), encoding="utf-8")


def run_suite(project_root: Path, test_paths: list[Path], pytest_args: list[str]) -> SuiteResult:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(project_root)
        if not existing_pythonpath
        else f"{project_root}{os.pathsep}{existing_pythonpath}"
    )
    command = [sys.executable, "-m", "pytest", "-q", *(str(path) for path in test_paths), *pytest_args]
    completed = subprocess.run(
        command,
        check=False,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    return SuiteResult(returncode=completed.returncode, output_tail=completed.stdout[-4000:])


def evaluate_mutants(
    mutants: list[Mutant],
    target_project: Path,
    target_tests: list[Path],
    generated_tests: Path,
    pytest_args: list[str],
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    for mutant in mutants:
        with tempfile.TemporaryDirectory(prefix="sps-mutant-") as temp_dir:
            project_copy = Path(temp_dir) / target_project.name
            copy_target(target_project, project_copy)
            apply_mutant(project_copy, mutant)
            copied_target_tests = [
                project_copy / path.relative_to(target_project)
                if path.resolve().is_relative_to(target_project)
                else path
                for path in target_tests
            ]
            target_result = run_suite(project_copy, copied_target_tests, pytest_args)
            generated_result = run_suite(project_copy, [generated_tests], pytest_args)
            combined_result = run_suite(
                project_copy,
                [*copied_target_tests, generated_tests],
                pytest_args,
            )
            results.append(
                {
                    "mutant": mutant.__dict__,
                    "target": target_result.__dict__ | {"killed": target_result.killed},
                    "generated": generated_result.__dict__ | {"killed": generated_result.killed},
                    "combined": combined_result.__dict__ | {"killed": combined_result.killed},
                }
            )
    return results


def score(results: list[dict[str, object]], suite: str) -> tuple[int, int, float]:
    total = len(results)
    killed = sum(1 for result in results if result[suite]["killed"])  # type: ignore[index]
    percent = 0.0 if total == 0 else (killed / total) * 100
    return killed, total, percent


def write_reports(markdown_path: Path, json_path: Path, results: list[dict[str, object]]) -> None:
    target_score = score(results, "target")
    generated_score = score(results, "generated")
    combined_score = score(results, "combined")
    generated_only = [
        result for result in results
        if result["generated"]["killed"] and not result["target"]["killed"]  # type: ignore[index]
    ]
    survived = [
        result for result in results
        if not result["combined"]["killed"]  # type: ignore[index]
    ]

    lines = [
        "# SPS-VeriSpec Mutation Evaluation",
        "",
        "## Mutation Score",
        "",
        "| Suite | Killed | Total | Score |",
        "| --- | ---: | ---: | ---: |",
        f"| Handwritten target tests | {target_score[0]} | {target_score[1]} | {target_score[2]:.1f}% |",
        f"| Generated tests | {generated_score[0]} | {generated_score[1]} | {generated_score[2]:.1f}% |",
        f"| Combined | {combined_score[0]} | {combined_score[1]} | {combined_score[2]:.1f}% |",
        "",
        f"- Mutants killed by generated tests but not handwritten tests: {len(generated_only)}",
        f"- Mutants surviving the combined suite: {len(survived)}",
        "",
        "## Mutants",
        "",
        "| ID | Location | Mutation | Reason | Handwritten | Generated | Combined |",
        "| --- | --- | --- | --- | ---: | ---: | ---: |",
    ]
    for result in results:
        mutant = result["mutant"]  # type: ignore[assignment]
        assert isinstance(mutant, dict)
        location = f"{mutant['relative_path']}:{mutant['line']}"
        mutation = f"`{mutant['original']}` -> `{mutant['replacement']}`"
        lines.append(
            "| {id} | `{location}` | {mutation} | {reason} | {target} | {generated} | {combined} |".format(
                id=mutant["id"],
                location=location,
                mutation=mutation,
                reason=mutant["reason"],
                target="killed" if result["target"]["killed"] else "survived",  # type: ignore[index]
                generated="killed" if result["generated"]["killed"] else "survived",  # type: ignore[index]
                combined="killed" if result["combined"]["killed"] else "survived",  # type: ignore[index]
            )
        )
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines), encoding="utf-8")

    payload = {
        "scores": {
            "target": {"killed": target_score[0], "total": target_score[1], "percent": target_score[2]},
            "generated": {"killed": generated_score[0], "total": generated_score[1], "percent": generated_score[2]},
            "combined": {"killed": combined_score[0], "total": combined_score[1], "percent": combined_score[2]},
            "generated_only_kills": len(generated_only),
            "survived_combined": len(survived),
        },
        "results": results,
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    analysis_dir = Path(args.analysis_dir).resolve()
    target_project = Path(args.target_project).resolve()
    generated_tests = Path(args.generated_tests).resolve()
    target_tests = [Path(path).resolve() for path in args.target_tests]
    if not target_tests:
        target_tests = [target_project / "tests"]
    markdown_path = (
        Path(args.report).resolve()
        if args.report
        else generated_tests / "mutation_eval.md"
    )
    json_path = (
        Path(args.json_report).resolve()
        if args.json_report
        else markdown_path.with_suffix(".json")
    )

    mutants = generate_mutants(analysis_dir, target_project, args.max_mutants)
    results = evaluate_mutants(
        mutants,
        target_project,
        target_tests,
        generated_tests,
        list(args.pytest_arg),
    )
    write_reports(markdown_path, json_path, results)
    print(markdown_path)
    print(json_path)


if __name__ == "__main__":
    main()
