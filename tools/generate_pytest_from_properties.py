from __future__ import annotations

import argparse
import csv
import keyword
import re
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class DataclassField:
    module_name: str
    class_name: str
    field_name: str
    type_repr: str
    is_optional: bool
    has_default: bool
    default_kind: str
    position: int


@dataclass(frozen=True)
class TransformTarget:
    class_module: str
    class_name: str
    qualified_name: str
    source_class: str
    source_field: str
    target_class: str
    target_arg: str
    target_kind: str


@dataclass(frozen=True)
class ExecutableCase:
    id: str
    class_module: str
    class_name: str
    method_name: str
    source_module: str
    source_class: str
    source_field: str
    target_module: str
    target_class: str
    target_arg: str
    assertion: str
    input_kwargs: dict[str, object]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate portable pytest tests from SPS-VeriSpec property outputs."
    )
    parser.add_argument(
        "--analysis-dir",
        required=True,
        help="Directory produced by tools/run_souffle_models.py.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "generated_tests"),
        help="Directory where generated tests and reports are written.",
    )
    parser.add_argument(
        "--project-name",
        help="Name used for the generated subdirectory. Defaults to analysis dir name.",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=100,
        help="Maximum executable cases to emit.",
    )
    return parser.parse_args()


def read_tsv(path: Path) -> list[list[str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return [row for row in csv.reader(handle, delimiter="\t") if row]


def load_dataclass_fields(facts_dir: Path) -> dict[tuple[str, str], list[DataclassField]]:
    fields: dict[tuple[str, str], list[DataclassField]] = {}
    for row in read_tsv(facts_dir / "dataclass_field.facts"):
        if len(row) < 9:
            continue
        module_name, class_name, field_name, type_repr = row[:4]
        field = DataclassField(
            module_name=module_name,
            class_name=class_name,
            field_name=field_name,
            type_repr=type_repr,
            is_optional=row[4] == "1",
            has_default=row[5] == "1",
            default_kind=row[6],
            position=int(row[7]),
        )
        fields.setdefault((module_name, class_name), []).append(field)

    for values in fields.values():
        values.sort(key=lambda field: field.position)
    return fields


def load_transform_modules(test_dir: Path) -> dict[tuple[str, str, str], tuple[str, str]]:
    modules: dict[tuple[str, str, str], tuple[str, str]] = {}
    for row in read_tsv(test_dir / "method_dataclass_transform.csv"):
        if len(row) < 7:
            continue
        class_module, class_name, qualified_name, src_module, src_class, tgt_module, tgt_class = row
        modules[(class_module, qualified_name, src_class)] = (src_module, tgt_module)
        modules[(class_module, qualified_name, tgt_class)] = (tgt_module, tgt_module)
    return modules


def load_targets(test_dir: Path) -> list[TransformTarget]:
    targets: list[TransformTarget] = []
    for target_kind, filename in (
        ("required", "transform_required_field_test_target.csv"),
        ("optional", "transform_optional_field_test_target.csv"),
    ):
        for row in read_tsv(test_dir / filename):
            if len(row) < 7:
                continue
            targets.append(TransformTarget(*row[:7], target_kind=target_kind))
    return targets


def method_name(qualified_name: str) -> str:
    return qualified_name.rsplit(".", 1)[-1]


def is_supported_transform(target: TransformTarget) -> bool:
    name = method_name(target.qualified_name)
    if name.startswith("_") or name == "publish":
        return False
    return name.startswith("format")


def is_supported_target_type(field: DataclassField | None) -> bool:
    if field is None:
        return False
    lowered = field.type_repr.lower()
    return "str" in lowered or "list" in lowered


def python_string(value: object) -> str:
    return repr(value)


def python_dict_literal(values: dict[str, object]) -> str:
    rendered = ", ".join(
        f"{python_string(key)}: {python_string(value)}" for key, value in values.items()
    )
    return "{" + rendered + "}"


def safe_id(*parts: str) -> str:
    text = "-".join(parts)
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", text).strip("-")
    return text or "case"


def sample_value(field: DataclassField, variant: str = "default") -> object:
    name = field.field_name.lower()
    type_repr = field.type_repr.lower()

    if variant == "none":
        return None
    if variant == "empty":
        return ""

    if "list" in type_repr:
        return ["generatedtag", "secondtag"]
    if "bool" in type_repr:
        return True
    if "int" in type_repr:
        return 7

    if "url" in name or "link" in name:
        return "https://example.com/generated-value"
    if name == "location":
        return "generatedcity, MA"
    if name == "breed":
        return "generatedbreed"
    if name == "species":
        return "generatedspecies"
    if name == "name":
        return "generatedname"
    if name in {"description", "text", "caption_text"}:
        return "generatedtext"
    if name == "tag_suffix":
        return "\n\n#generatedtag"

    return f"generated_{name}"


def make_input_kwargs(
    fields: list[DataclassField],
    source_field: str,
    source_value: object,
) -> dict[str, object]:
    kwargs: dict[str, object] = {}
    for field in fields:
        if field.field_name == source_field:
            kwargs[field.field_name] = source_value
        elif field.has_default:
            if field.is_optional:
                kwargs[field.field_name] = None
            elif field.default_kind == "factory":
                kwargs[field.field_name] = sample_value(field)
            else:
                kwargs[field.field_name] = sample_value(field)
        else:
            kwargs[field.field_name] = sample_value(field)
    return kwargs


def field_by_name(
    fields: dict[tuple[str, str], list[DataclassField]],
    module_name: str,
    class_name: str,
    field_name: str,
) -> DataclassField | None:
    for field in fields.get((module_name, class_name), []):
        if field.field_name == field_name:
            return field
    return None


def build_cases(
    fields: dict[tuple[str, str], list[DataclassField]],
    modules: dict[tuple[str, str, str], tuple[str, str]],
    targets: list[TransformTarget],
    max_cases: int,
) -> tuple[list[ExecutableCase], list[str]]:
    cases: list[ExecutableCase] = []
    skipped: list[str] = []

    for target in targets:
        if len(cases) >= max_cases:
            skipped.append("Stopped after reaching --max-cases.")
            break

        source_module, target_module = modules.get(
            (target.class_module, target.qualified_name, target.source_class),
            ("", ""),
        )
        if not source_module or not target_module:
            skipped.append(
                f"- `{target.qualified_name}` skipped: source/target modules were not resolved."
            )
            continue

        source_fields = fields.get((source_module, target.source_class), [])
        target_field = field_by_name(fields, target_module, target.target_class, target.target_arg)
        if not source_fields:
            skipped.append(
                f"- `{target.qualified_name}` skipped: no fields found for `{target.source_class}`."
            )
            continue
        if not is_supported_transform(target):
            skipped.append(
                f"- `{target.qualified_name}` skipped: default generator only emits public `format*` transforms."
            )
            continue
        if not is_supported_target_type(target_field):
            skipped.append(
                f"- `{target.qualified_name}` skipped: target `{target.target_class}.{target.target_arg}` is not a string/list field."
            )
            continue

        source_field = field_by_name(
            fields, source_module, target.source_class, target.source_field
        )
        if source_field is None:
            skipped.append(
                f"- `{target.qualified_name}` skipped: source field `{target.source_field}` was not found."
            )
            continue

        values: list[tuple[str, object, str]]
        if target.target_kind == "optional":
            values = [
                ("none", None, "equals"),
                ("empty", "", "equals"),
                ("value", sample_value(source_field), "equals"),
            ]
        else:
            values = [("value", sample_value(source_field), "observes")]

        for variant, value, assertion in values:
            if len(cases) >= max_cases:
                break
            case_id = safe_id(
                target.qualified_name,
                target.source_class,
                target.source_field,
                target.target_class,
                target.target_arg,
                variant,
            )
            cases.append(
                ExecutableCase(
                    id=case_id,
                    class_module=target.class_module,
                    class_name=target.class_name,
                    method_name=method_name(target.qualified_name),
                    source_module=source_module,
                    source_class=target.source_class,
                    source_field=target.source_field,
                    target_module=target_module,
                    target_class=target.target_class,
                    target_arg=target.target_arg,
                    assertion=assertion,
                    input_kwargs=make_input_kwargs(source_fields, target.source_field, value),
                )
            )

    return cases, skipped


def render_cases(cases: list[ExecutableCase]) -> str:
    entries = []
    for case in cases:
        entries.append(
            "\n".join(
                [
                    "    {",
                    f"        'id': {case.id!r},",
                    f"        'class_module': {case.class_module!r},",
                    f"        'class_name': {case.class_name!r},",
                    f"        'method_name': {case.method_name!r},",
                    f"        'source_module': {case.source_module!r},",
                    f"        'source_class': {case.source_class!r},",
                    f"        'source_field': {case.source_field!r},",
                    f"        'target_arg': {case.target_arg!r},",
                    f"        'assertion': {case.assertion!r},",
                    f"        'input_kwargs': {python_dict_literal(case.input_kwargs)},",
                    "    }",
                ]
            )
        )
    return "[\n" + ",\n".join(entries) + "\n]"


def render_test_file(cases: list[ExecutableCase]) -> str:
    return f'''"""
Generated by tools/generate_pytest_from_properties.py.

These tests are intentionally portable: keep them outside the analyzed project
and run them with PYTHONPATH pointing at the target checkout, for example:

    PYTHONPATH=/path/to/CutePetsBoston pytest generated_tests/<project>
"""

from __future__ import annotations

import abc
import importlib

import pytest


CASES = {render_cases(cases)}


def _load_class(module_name, class_name):
    try:
        module = importlib.import_module(module_name)
    except ModuleNotFoundError as exc:
        pytest.skip(f"Cannot import {{module_name}}: {{exc}}")
    return getattr(module, class_name)


def _dummy_method(*args, **kwargs):
    return None


def _instance_for(cls):
    try:
        return cls()
    except TypeError:
        attrs = {{}}
        abstract_names = getattr(cls, "__abstractmethods__", set())
        for name in abstract_names:
            descriptor = getattr(cls, name, None)
            if isinstance(descriptor, property):
                attrs[name] = property(lambda self, _name=name: f"generated-{{_name}}")
            else:
                attrs[name] = _dummy_method

        harness = abc.ABCMeta(f"Generated{{cls.__name__}}Harness", (cls,), attrs)
        return harness()


def _assert_observed(actual, expected):
    if actual == expected:
        return

    if expected is None:
        assert actual is None
        return

    expected_text = str(expected)

    if isinstance(actual, str):
        assert expected_text in actual
        return

    if isinstance(actual, list):
        normalized = expected_text.lower().replace(" ", "")
        location_prefix = expected_text.split(",", 1)[0].capitalize()
        actual_texts = [str(item) for item in actual]
        actual_normalized = [item.lower().replace(" ", "") for item in actual_texts]
        assert (
            expected_text in actual_texts
            or normalized in actual_normalized
            or location_prefix in actual_texts
        )
        return

    assert actual == expected


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_generated_dataclass_transform_property(case):
    source_cls = _load_class(case["source_module"], case["source_class"])
    owner_cls = _load_class(case["class_module"], case["class_name"])

    source = source_cls(**case["input_kwargs"])
    expected = case["input_kwargs"][case["source_field"]]

    owner = _instance_for(owner_cls)
    result = getattr(owner, case["method_name"])(source)
    actual = getattr(result, case["target_arg"])

    if case["assertion"] == "equals":
        assert actual == expected
    else:
        _assert_observed(actual, expected)
'''


def write_report(
    path: Path,
    analysis_dir: Path,
    tests_path: Path,
    cases: list[ExecutableCase],
    skipped: list[str],
) -> None:
    cwd = Path.cwd().resolve()

    def display(path: Path) -> str:
        try:
            return str(path.resolve().relative_to(cwd))
        except ValueError:
            return str(path)

    tests_display = display(tests_path)
    lines = [
        "# Generated Test Report",
        "",
        f"- Analysis directory: `{analysis_dir}`",
        f"- Test file: `{tests_display}`",
        f"- Executable cases emitted: {len(cases)}",
        f"- Candidate relations left as review items: {len(skipped)}",
        "",
        "## Run",
        "",
        "Set `PYTHONPATH` to the target project checkout and run pytest against this directory:",
        "",
        "```bash",
        f"PYTHONPATH=/path/to/target-project pytest {display(tests_path.parent)}",
        "```",
        "",
        "## Emitted Cases",
        "",
    ]
    if cases:
        for case in cases:
            lines.append(
                f"- `{case.id}`: `{case.source_class}.{case.source_field}` -> `{case.target_arg}` via `{case.class_module}.{case.class_name}.{case.method_name}`"
            )
    else:
        lines.append("- No executable cases were emitted by the conservative generator.")

    lines.extend(["", "## Review Candidates", ""])
    if skipped:
        lines.extend(skipped)
    else:
        lines.append("- No candidates were skipped.")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "The default generator only emits public `format*` method tests with string/list observations.",
            "Relations involving publishing, private helpers, branch-only facts, lossy flows, or non-string outputs are kept as review candidates until stronger oracles are available.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    analysis_dir = Path(args.analysis_dir).resolve()
    project_name = args.project_name or analysis_dir.name
    project_name = project_name if project_name.isidentifier() else re.sub(r"\W+", "_", project_name)
    if keyword.iskeyword(project_name):
        project_name = f"{project_name}_project"

    output_dir = Path(args.output_dir).resolve() / project_name
    output_dir.mkdir(parents=True, exist_ok=True)

    fields = load_dataclass_fields(analysis_dir / "facts")
    modules = load_transform_modules(analysis_dir / "test_out")
    targets = load_targets(analysis_dir / "test_out")
    cases, skipped = build_cases(fields, modules, targets, args.max_cases)

    tests_path = output_dir / "test_generated_dataclass_properties.py"
    report_path = output_dir / "README.md"
    tests_path.write_text(render_test_file(cases), encoding="utf-8")
    write_report(report_path, analysis_dir, tests_path, cases, skipped)

    print(tests_path)
    print(report_path)


if __name__ == "__main__":
    main()
