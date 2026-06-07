from __future__ import annotations

import argparse
import ast
import csv
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@dataclass(frozen=True)
class FamilyCoverage:
    name: str
    discovered: int
    emitted: int
    emitted_cases: int
    strict_oracle: int
    weak_oracle: int

    @property
    def coverage_percent(self) -> float:
        if self.discovered == 0:
            return 100.0 if self.emitted == 0 else 0.0
        return (self.emitted / self.discovered) * 100.0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compute semantic family coverage for generated SPS-VeriSpec tests."
    )
    parser.add_argument("--analysis-dir", required=True)
    parser.add_argument("--generated-tests", required=True)
    parser.add_argument("--report", help="Markdown report path. Defaults to <generated-tests>/generator_coverage.md.")
    parser.add_argument("--json-report", help="JSON report path. Defaults to Markdown path with .json suffix.")
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


def dataclass_constructor_discovered(facts_dir: Path) -> int:
    by_class: dict[tuple[str, str], list[list[str]]] = {}
    for row in read_tsv(facts_dir / "dataclass_field.facts"):
        if len(row) >= 9:
            by_class.setdefault((row[0], row[1]), []).append(row)
    eligible = 0
    for rows in by_class.values():
        if any(field[5] == "0" or field[5] == "1" for field in rows):
            eligible += 1
    return eligible


def conversion_discovered(facts_dir: Path) -> int:
    owners = {
        (row[0], row[2]): row[1]
        for row in read_tsv(facts_dir / "method_of_class.facts")
        if len(row) >= 3
    }
    eligible = 0
    for row in read_tsv(facts_dir / "function_name.facts"):
        if len(row) < 3:
            continue
        module_name, qualified_name, function_name = row[:3]
        if function_name not in {"from_dict", "structure", "to_dict", "asdict", "unstructure"}:
            continue
        owner_class = owners.get((module_name, qualified_name), "")
        if owner_class and function_name not in {"structure", "unstructure"}:
            continue
        if owner_class and owner_class not in {"Converter", "BaseConverter"}:
            continue
        if owner_class and qualified_name.rsplit(".", 1)[-1].startswith("_"):
            continue
        eligible += 1
    return eligible


def build_family_coverage(analysis_dir: Path, generated_tests: Path) -> list[FamilyCoverage]:
    facts_dir = analysis_dir / "facts"
    test_dir = analysis_dir / "test_out"
    semantic_dir = analysis_dir / "semantic_out"

    example_cases = list_constant(generated_tests / "test_generated_dataclass_properties.py", "CASES")
    schema_cases = list_constant(generated_tests / "test_generated_dataclass_schema.py", "SCHEMA_CASES")
    constructor_cases = list_constant(generated_tests / "test_generated_dataclass_schema.py", "CONSTRUCTOR_CASES")
    conversion_cases = list_constant(generated_tests / "test_generated_dataclass_conversions.py", "CONVERSION_CASES")
    helper_cases = list_constant(generated_tests / "test_generated_helper_boundaries.py", "HELPER_BOUNDARY_CASES")
    common_ast_cases = list_constant(generated_tests / "test_generated_common_ast_properties.py", "COMMON_AST_CASES")
    interprocedural_cases = list_constant(
        generated_tests / "test_generated_interprocedural_properties.py",
        "INTERPROCEDURAL_CASES",
    )

    required_emitted = [case for case in example_cases if case.get("target_kind") != "optional"]
    optional_emitted = [case for case in example_cases if case.get("target_kind") == "optional"]
    required_relations = {
        (
            case.get("class_module"),
            case.get("class_name"),
            case.get("method_name"),
            case.get("source_class"),
            case.get("source_field"),
            case.get("target_arg"),
        )
        for case in required_emitted
    }
    optional_relations = {
        (
            case.get("class_module"),
            case.get("class_name"),
            case.get("method_name"),
            case.get("source_class"),
            case.get("source_field"),
            case.get("target_arg"),
        )
        for case in optional_emitted
    }
    helper_relation_count = len(
        {
            (case.get("module_name"), case.get("class_name"), case.get("method_name"))
            for case in helper_cases
        }
    )
    common_ast_relation_count = len(
        {
            (case.get("module_name"), case.get("class_name"), case.get("method_name"), case.get("source_field"))
            for case in common_ast_cases
        }
    )
    interprocedural_relation_count = len(
        {
            (
                case.get("class_module"),
                case.get("class_name"),
                case.get("method_name"),
                case.get("source_class"),
                case.get("source_field"),
                case.get("target_class"),
                case.get("target_field"),
            )
            for case in interprocedural_cases
        }
    )

    helper_discovered = sum(
        1
        for row in read_tsv(semantic_dir / "numeric_bound.csv")
        if len(row) >= 3 and row[1].rsplit(".", 1)[-1].startswith("_") and row[2].startswith("len(")
    )
    common_ast_discovered = len(read_tsv(semantic_dir / "dataclass_collection_iteration.csv"))
    interprocedural_discovered = sum(
        1
        for row in read_tsv(semantic_dir / "observable_output_slice.csv")
        if len(row) >= 7 and row[6] == "string_output"
    )

    return [
        FamilyCoverage(
            name="dataclass_schema",
            discovered=len(read_tsv(facts_dir / "dataclass.facts")),
            emitted=len(schema_cases),
            emitted_cases=len(schema_cases),
            strict_oracle=len(schema_cases),
            weak_oracle=0,
        ),
        FamilyCoverage(
            name="dataclass_constructor",
            discovered=dataclass_constructor_discovered(facts_dir),
            emitted=len(constructor_cases),
            emitted_cases=len(constructor_cases),
            strict_oracle=len(constructor_cases),
            weak_oracle=0,
        ),
        FamilyCoverage(
            name="conversion_profile",
            discovered=conversion_discovered(facts_dir),
            emitted=len(conversion_cases),
            emitted_cases=len(conversion_cases),
            strict_oracle=len(conversion_cases),
            weak_oracle=0,
        ),
        FamilyCoverage(
            name="transform_required_field",
            discovered=len(read_tsv(test_dir / "transform_required_field_test_target.csv")),
            emitted=len(required_relations),
            emitted_cases=len(required_emitted),
            strict_oracle=sum(1 for case in required_emitted if case.get("assertion") == "equals"),
            weak_oracle=sum(1 for case in required_emitted if case.get("assertion") != "equals"),
        ),
        FamilyCoverage(
            name="transform_optional_field",
            discovered=len(read_tsv(test_dir / "transform_optional_field_test_target.csv")),
            emitted=len(optional_relations),
            emitted_cases=len(optional_emitted),
            strict_oracle=len(optional_emitted),
            weak_oracle=0,
        ),
        FamilyCoverage(
            name="helper_boundary",
            discovered=helper_discovered,
            emitted=helper_relation_count,
            emitted_cases=len(helper_cases),
            strict_oracle=len(helper_cases),
            weak_oracle=0,
        ),
        FamilyCoverage(
            name="common_ast_collection_iteration",
            discovered=common_ast_discovered,
            emitted=common_ast_relation_count,
            emitted_cases=len(common_ast_cases),
            strict_oracle=0,
            weak_oracle=len(common_ast_cases),
        ),
        FamilyCoverage(
            name="interprocedural_observable_slice",
            discovered=interprocedural_discovered,
            emitted=interprocedural_relation_count,
            emitted_cases=len(interprocedural_cases),
            strict_oracle=0,
            weak_oracle=len(interprocedural_cases),
        ),
    ]


def write_reports(markdown_path: Path, json_path: Path, families: list[FamilyCoverage]) -> None:
    lines = [
        "# Generator Coverage",
        "",
        "| Family | Discovered | Emitted relations | Emitted cases | Coverage | Strict cases | Weak cases |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for family in families:
        lines.append(
            f"| `{family.name}` | {family.discovered} | {family.emitted} | {family.emitted_cases} | {family.coverage_percent:.1f}% | {family.strict_oracle} | {family.weak_oracle} |"
        )
    lines.append("")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text("\n".join(lines), encoding="utf-8")

    payload = {
        "families": [
            {
                **asdict(family),
                "coverage_percent": family.coverage_percent,
            }
            for family in families
        ]
    }
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main() -> None:
    args = parse_args()
    analysis_dir = Path(args.analysis_dir).resolve()
    generated_tests = Path(args.generated_tests).resolve()
    markdown_path = (
        Path(args.report).resolve()
        if args.report
        else generated_tests / "generator_coverage.md"
    )
    json_path = (
        Path(args.json_report).resolve()
        if args.json_report
        else markdown_path.with_suffix(".json")
    )
    families = build_family_coverage(analysis_dir, generated_tests)
    write_reports(markdown_path, json_path, families)
    print(markdown_path)
    print(json_path)


if __name__ == "__main__":
    main()
