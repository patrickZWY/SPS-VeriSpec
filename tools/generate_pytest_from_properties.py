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
    source_type: str
    target_module: str
    target_class: str
    target_arg: str
    target_type: str
    target_kind: str
    assertion: str
    input_kwargs: dict[str, object]


@dataclass(frozen=True)
class FunctionParam:
    module_name: str
    qualified_name: str
    name: str
    type_repr: str
    position: int


@dataclass(frozen=True)
class HelperBoundaryCase:
    id: str
    module_name: str
    class_name: str
    method_name: str
    param_name: str
    input_length: int
    expected_max_length: int
    relation_kind: str
    expression: str


@dataclass(frozen=True)
class CommonAstCase:
    id: str
    relation_kind: str
    module_name: str
    class_name: str
    method_name: str
    source_module: str
    source_class: str
    source_field: str
    source_type: str
    input_kwargs: dict[str, object]
    expected_value: object


@dataclass(frozen=True)
class InterproceduralCase:
    id: str
    class_module: str
    class_name: str
    method_name: str
    source_module: str
    source_class: str
    source_field: str
    source_type: str
    target_module: str
    target_class: str
    target_field: str
    slice_kind: str
    input_kwargs: dict[str, object]
    expected_value: object


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


def load_function_params(facts_dir: Path) -> dict[tuple[str, str], list[FunctionParam]]:
    params: dict[tuple[str, str], list[FunctionParam]] = {}
    for row in read_tsv(facts_dir / "function_param.facts"):
        if len(row) < 6:
            continue
        module_name, qualified_name, name, type_repr, position, _line = row[:6]
        param = FunctionParam(
            module_name=module_name,
            qualified_name=qualified_name,
            name=name,
            type_repr=type_repr,
            position=int(position),
        )
        params.setdefault((module_name, qualified_name), []).append(param)

    for values in params.values():
        values.sort(key=lambda param: param.position)
    return params


def load_method_owners(facts_dir: Path) -> dict[tuple[str, str], str]:
    owners: dict[tuple[str, str], str] = {}
    for row in read_tsv(facts_dir / "method_of_class.facts"):
        if len(row) < 3:
            continue
        module_name, class_name, qualified_name = row[:3]
        owners[(module_name, qualified_name)] = class_name
    return owners


def load_resolved_params(facts_dir: Path) -> dict[tuple[str, str, str, str], str]:
    params: dict[tuple[str, str, str, str], str] = {}
    for row in read_tsv(facts_dir / "resolved_param_type_ref.facts"):
        if len(row) < 5:
            continue
        module_name, qualified_name, param_name, type_module, type_name = row[:5]
        params[(module_name, qualified_name, type_module, type_name)] = param_name
    return params


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


def load_helper_boundary_cases(
    semantic_dir: Path,
    params: dict[tuple[str, str], list[FunctionParam]],
    owners: dict[tuple[str, str], str],
    max_cases: int,
) -> tuple[list[HelperBoundaryCase], list[str]]:
    cases: list[HelperBoundaryCase] = []
    skipped: list[str] = []
    seen: set[tuple[str, str, str, int, int]] = set()
    emitted_helpers: set[tuple[str, str]] = set()

    for row in read_tsv(semantic_dir / "numeric_bound.csv"):
        if len(row) < 6:
            continue
        module_name, qualified_name, expression, relation_kind, bound_text, _line = row[:6]
        method = method_name(qualified_name)
        if not method.startswith("_"):
            continue
        if not expression.startswith("len("):
            if (module_name, qualified_name) in emitted_helpers:
                continue
            skipped.append(
                f"- `{qualified_name}` boundary skipped: only `len(...)` helper boundaries are generated automatically."
            )
            continue

        try:
            bound = int(bound_text)
        except ValueError:
            skipped.append(
                f"- `{qualified_name}` boundary skipped: non-integer bound `{bound_text}`."
            )
            continue
        if bound <= 0:
            skipped.append(
                f"- `{qualified_name}` boundary skipped: non-positive bound `{bound}` needs custom input construction."
            )
            continue

        class_name = owners.get((module_name, qualified_name))
        if class_name is None:
            skipped.append(
                f"- `{qualified_name}` boundary skipped: method owner class was not resolved."
            )
            continue

        non_self_params = [
            param
            for param in params.get((module_name, qualified_name), [])
            if param.name not in {"self", "cls"}
        ]
        string_params = [
            param
            for param in non_self_params
            if "str" in param.type_repr.lower() and "list" not in param.type_repr.lower()
        ]
        if len(non_self_params) != 1 or len(string_params) != 1:
            skipped.append(
                f"- `{qualified_name}` boundary skipped: helper has parameters that need custom construction."
            )
            continue

        param = string_params[0]
        for variant, input_length in (
            ("below", max(bound - 1, 0)),
            ("at", bound),
            ("above", bound + 1),
        ):
            if len(cases) >= max_cases:
                skipped.append("- Helper boundary generation stopped after reaching --max-cases.")
                return cases, skipped
            key = (module_name, qualified_name, param.name, input_length, bound)
            if key in seen:
                continue
            seen.add(key)
            emitted_helpers.add((module_name, qualified_name))
            cases.append(
                HelperBoundaryCase(
                    id=safe_id(
                        qualified_name,
                        param.name,
                        expression,
                        relation_kind,
                        str(bound),
                        variant,
                    ),
                    module_name=module_name,
                    class_name=class_name,
                    method_name=method,
                    param_name=param.name,
                    input_length=input_length,
                    expected_max_length=bound,
                    relation_kind=relation_kind,
                    expression=expression,
                )
            )

    if emitted_helpers:
        skipped = [
            item
            for item in skipped
            if not any(f"`{qualified_name}`" in item for _, qualified_name in emitted_helpers)
        ]
    return cases, skipped


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
                f"- `{target.qualified_name}` skipped: dataclass-transform generator only emits public `format*` transforms."
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
                    source_type=source_field.type_repr,
                    target_module=target_module,
                    target_class=target.target_class,
                    target_arg=target.target_arg,
                    target_type=target_field.type_repr if target_field else "",
                    target_kind=target.target_kind,
                    assertion=assertion,
                    input_kwargs=make_input_kwargs(source_fields, target.source_field, value),
                )
            )

    return cases, skipped


def load_common_ast_cases(
    semantic_dir: Path,
    fields: dict[tuple[str, str], list[DataclassField]],
    params: dict[tuple[str, str], list[FunctionParam]],
    owners: dict[tuple[str, str], str],
    resolved_params: dict[tuple[str, str, str, str], str],
    max_cases: int,
) -> tuple[list[CommonAstCase], list[str]]:
    cases: list[CommonAstCase] = []
    skipped: list[str] = []
    seen: set[tuple[str, str, str, str]] = set()

    for row in read_tsv(semantic_dir / "dataclass_collection_iteration.csv"):
        if len(row) < 7:
            continue
        module_name, qualified_name, source_module, source_class, source_field, _item_name, iteration_kind = row[:7]
        if len(cases) >= max_cases:
            skipped.append("- Common-AST generation stopped after reaching --max-cases.")
            break

        class_name = owners.get((module_name, qualified_name))
        if class_name is None:
            skipped.append(
                f"- `{qualified_name}` collection iteration skipped: method owner class was not resolved."
            )
            continue

        source_param = resolved_params.get(
            (module_name, qualified_name, source_module, source_class)
        )
        if source_param is None:
            skipped.append(
                f"- `{qualified_name}` collection iteration skipped: dataclass parameter was not resolved."
            )
            continue

        non_self_params = [
            param
            for param in params.get((module_name, qualified_name), [])
            if param.name not in {"self", "cls"}
        ]
        if [param.name for param in non_self_params] != [source_param]:
            skipped.append(
                f"- `{qualified_name}` collection iteration skipped: method needs additional custom arguments."
            )
            continue

        source_fields = fields.get((source_module, source_class), [])
        iterated_field = field_by_name(fields, source_module, source_class, source_field)
        if iterated_field is None:
            skipped.append(
                f"- `{qualified_name}` collection iteration skipped: field `{source_field}` was not found."
            )
            continue
        if "list" not in iterated_field.type_repr.lower():
            skipped.append(
                f"- `{qualified_name}` collection iteration skipped: `{source_field}` is not a list-like field."
            )
            continue

        key = (module_name, qualified_name, source_class, source_field)
        if key in seen:
            continue
        seen.add(key)

        expected_value = f"generated_{source_field}_item"
        input_kwargs = make_input_kwargs(source_fields, source_field, [expected_value])
        cases.append(
            CommonAstCase(
                id=safe_id(
                    "collection",
                    qualified_name,
                    source_class,
                    source_field,
                    iteration_kind,
                ),
                relation_kind="dataclass_collection_iteration",
                module_name=module_name,
                class_name=class_name,
                method_name=method_name(qualified_name),
                source_module=source_module,
                source_class=source_class,
                source_field=source_field,
                source_type=iterated_field.type_repr,
                input_kwargs=input_kwargs,
                expected_value=expected_value,
            )
        )

    review_files = [
        ("asserted_dataclass_field.csv", "asserted field"),
        ("matched_dataclass_subject.csv", "pattern match"),
        ("async_obligation_candidate.csv", "async obligation"),
        ("generator_output_candidate.csv", "generator output"),
        ("alias_attribute_read.csv", "alias attribute read"),
    ]
    for filename, label in review_files:
        for row in read_tsv(semantic_dir / filename):
            if len(row) >= 2:
                skipped.append(
                    f"- `{row[1]}` {label} relation kept for review: no conservative executable oracle yet."
                )

    return cases, skipped


def load_interprocedural_cases(
    semantic_dir: Path,
    test_dir: Path,
    fields: dict[tuple[str, str], list[DataclassField]],
    max_cases: int,
) -> tuple[list[InterproceduralCase], list[str]]:
    cases: list[InterproceduralCase] = []
    skipped: list[str] = []
    multi_hop = {
        tuple(row[:6])
        for row in read_tsv(semantic_dir / "multi_hop_interprocedural_field_flow.csv")
        if len(row) >= 6
    }
    direct_methods: dict[tuple[str, str, str, str], list[tuple[str, str, str]]] = {}
    for row in read_tsv(test_dir / "method_dataclass_transform.csv"):
        if len(row) < 7:
            continue
        class_module, class_name, qualified_name, source_module, source_class, target_module, target_class = row[:7]
        direct_methods.setdefault(
            (source_module, source_class, target_module, target_class),
            [],
        ).append((class_module, class_name, qualified_name))
    for row in read_tsv(semantic_dir / "interprocedural_method_transform.csv"):
        if len(row) < 7:
            continue
        class_module, class_name, qualified_name, source_module, source_class, target_module, target_class = row[:7]
        direct_methods.setdefault(
            (source_module, source_class, target_module, target_class),
            [],
        ).append((class_module, class_name, qualified_name))

    seen: set[tuple[str, str, str, str, str]] = set()
    for row in read_tsv(semantic_dir / "observable_output_slice.csv"):
        if len(row) < 7 or len(cases) >= max_cases:
            break
        source_module, source_class, source_field, target_module, target_class, target_field, slice_kind = row[:7]
        if (source_module, source_class, source_field, target_module, target_class, target_field) not in multi_hop:
            continue
        if slice_kind != "string_output":
            skipped.append(
                f"- `{source_class}.{source_field} -> {target_class}.{target_field}` interprocedural slice skipped: unsupported slice kind `{slice_kind}`."
            )
            continue

        methods = direct_methods.get((source_module, source_class, target_module, target_class), [])
        methods = [
            method
            for method in methods
            if not method[2].rsplit(".", 1)[-1].startswith("_")
            and method[2].rsplit(".", 1)[-1] != "publish"
        ]
        if not methods:
            skipped.append(
                f"- `{source_class}.{source_field} -> {target_class}.{target_field}` interprocedural slice skipped: no public executable method path was found."
            )
            continue

        source_fields = fields.get((source_module, source_class), [])
        source_field_info = field_by_name(fields, source_module, source_class, source_field)
        if source_field_info is None:
            skipped.append(
                f"- `{source_class}.{source_field}` interprocedural slice skipped: source field was not found."
            )
            continue

        for class_module, class_name, qualified_name in methods:
            key = (qualified_name, source_class, source_field, target_class, target_field)
            if key in seen:
                continue
            seen.add(key)
            expected_value = sample_value(source_field_info)
            case_id = safe_id(
                "interproc",
                qualified_name,
                source_class,
                source_field,
                target_class,
                target_field,
            )
            cases.append(
                InterproceduralCase(
                    id=case_id,
                    class_module=class_module,
                    class_name=class_name,
                    method_name=method_name(qualified_name),
                    source_module=source_module,
                    source_class=source_class,
                    source_field=source_field,
                    source_type=source_field_info.type_repr,
                    target_module=target_module,
                    target_class=target_class,
                    target_field=target_field,
                    slice_kind=slice_kind,
                    input_kwargs=make_input_kwargs(
                        source_fields,
                        source_field,
                        expected_value,
                    ),
                    expected_value=expected_value,
                )
            )
            if len(cases) >= max_cases:
                break

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
                    f"        'source_type': {case.source_type!r},",
                    f"        'target_arg': {case.target_arg!r},",
                    f"        'target_type': {case.target_type!r},",
                    f"        'target_kind': {case.target_kind!r},",
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


def render_helper_boundary_cases(cases: list[HelperBoundaryCase]) -> str:
    entries = []
    for case in cases:
        entries.append(
            "\n".join(
                [
                    "    {",
                    f"        'id': {case.id!r},",
                    f"        'module_name': {case.module_name!r},",
                    f"        'class_name': {case.class_name!r},",
                    f"        'method_name': {case.method_name!r},",
                    f"        'param_name': {case.param_name!r},",
                    f"        'input_length': {case.input_length!r},",
                    f"        'expected_max_length': {case.expected_max_length!r},",
                    f"        'relation_kind': {case.relation_kind!r},",
                    f"        'expression': {case.expression!r},",
                    "    }",
                ]
            )
        )
    return "[\n" + ",\n".join(entries) + "\n]"


def render_helper_boundary_test_file(cases: list[HelperBoundaryCase]) -> str:
    return f'''"""
Generated by tools/generate_pytest_from_properties.py.

These are lower-confidence helper-boundary tests. They may call private helper
methods directly when the static boundary relation can be driven with a simple
string argument.
"""

from __future__ import annotations

import abc
import importlib

import pytest


HELPER_BOUNDARY_CASES = {render_helper_boundary_cases(cases)}


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


@pytest.mark.parametrize("case", HELPER_BOUNDARY_CASES, ids=[case["id"] for case in HELPER_BOUNDARY_CASES])
def test_generated_helper_boundary(case):
    owner_cls = _load_class(case["module_name"], case["class_name"])
    owner = _instance_for(owner_cls)
    value = "x" * case["input_length"]

    result = getattr(owner, case["method_name"])(value)

    assert isinstance(result, str)
    assert len(result) <= case["expected_max_length"]
'''


def render_common_ast_cases(cases: list[CommonAstCase]) -> str:
    entries = []
    for case in cases:
        entries.append(
            "\n".join(
                [
                    "    {",
                    f"        'id': {case.id!r},",
                    f"        'relation_kind': {case.relation_kind!r},",
                    f"        'module_name': {case.module_name!r},",
                    f"        'class_name': {case.class_name!r},",
                    f"        'method_name': {case.method_name!r},",
                    f"        'source_module': {case.source_module!r},",
                    f"        'source_class': {case.source_class!r},",
                    f"        'source_field': {case.source_field!r},",
                    f"        'source_type': {case.source_type!r},",
                    f"        'input_kwargs': {python_dict_literal(case.input_kwargs)},",
                    f"        'expected_value': {python_string(case.expected_value)},",
                    "    }",
                ]
            )
        )
    return "[\n" + ",\n".join(entries) + "\n]"


def render_common_ast_test_file(cases: list[CommonAstCase]) -> str:
    return f'''"""
Generated by tools/generate_pytest_from_properties.py.

These tests exercise conservative common-AST semantic relations such as
iteration over dataclass collection fields.
"""

from __future__ import annotations

import abc
import importlib

import pytest


COMMON_AST_CASES = {render_common_ast_cases(cases)}


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


def _flatten_observable(value):
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        values = []
        for item in value.values():
            values.extend(_flatten_observable(item))
        return values
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(_flatten_observable(item))
        return values
    return [str(value)]


@pytest.mark.parametrize("case", COMMON_AST_CASES, ids=[case["id"] for case in COMMON_AST_CASES])
def test_generated_common_ast_relation(case):
    source_cls = _load_class(case["source_module"], case["source_class"])
    owner_cls = _load_class(case["module_name"], case["class_name"])

    source = source_cls(**case["input_kwargs"])
    owner = _instance_for(owner_cls)
    result = getattr(owner, case["method_name"])(source)

    observed = "\\n".join(str(item) for item in _flatten_observable(result))
    assert str(case["expected_value"]) in observed
'''


def render_interprocedural_cases(cases: list[InterproceduralCase]) -> str:
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
                    f"        'source_type': {case.source_type!r},",
                    f"        'target_module': {case.target_module!r},",
                    f"        'target_class': {case.target_class!r},",
                    f"        'target_field': {case.target_field!r},",
                    f"        'slice_kind': {case.slice_kind!r},",
                    f"        'input_kwargs': {python_dict_literal(case.input_kwargs)},",
                    f"        'expected_value': {python_string(case.expected_value)},",
                    "    }",
                ]
            )
        )
    return "[\n" + ",\n".join(entries) + "\n]"


def render_interprocedural_test_file(cases: list[InterproceduralCase]) -> str:
    return f'''"""
Generated by tools/generate_pytest_from_properties.py.

These tests exercise composed interprocedural dataflow slices when a public
method can drive a source dataclass to an observable output dataclass.
"""

from __future__ import annotations

import abc
import importlib

import pytest


INTERPROCEDURAL_CASES = {render_interprocedural_cases(cases)}


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


def _flatten_observable(value):
    if value is None:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        values = []
        for item in value.values():
            values.extend(_flatten_observable(item))
        return values
    if isinstance(value, (list, tuple, set)):
        values = []
        for item in value:
            values.extend(_flatten_observable(item))
        return values
    return [str(value)]


def _unwrap_pipeline_result(value):
    if hasattr(value, "value"):
        inner = getattr(value, "value")
        if inner is not None:
            return inner
    return value


@pytest.mark.parametrize("case", INTERPROCEDURAL_CASES, ids=[case["id"] for case in INTERPROCEDURAL_CASES])
def test_generated_interprocedural_observable_slice(case):
    source_cls = _load_class(case["source_module"], case["source_class"])
    owner_cls = _load_class(case["class_module"], case["class_name"])

    source = source_cls(**case["input_kwargs"])
    owner = _instance_for(owner_cls)
    result = _unwrap_pipeline_result(getattr(owner, case["method_name"])(source))

    actual = getattr(result, case["target_field"])
    observed = "\\n".join(str(item) for item in _flatten_observable(actual))
    assert str(case["expected_value"]) in observed
'''


def render_hypothesis_test_file(cases: list[ExecutableCase]) -> str:
    return f'''"""
Generated by tools/generate_pytest_from_properties.py.

These optional property tests use Hypothesis to vary source dataclass fields
for the same conservative transform relations as the generated example tests.
"""

from __future__ import annotations

import abc
import importlib

import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, settings, strategies as st


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


def _safe_text(min_size=1, max_size=24):
    alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 -_"
    return st.text(alphabet=alphabet, min_size=min_size, max_size=max_size)


def _strategy_for_case(case):
    name = case["source_field"].lower()
    type_repr = case["source_type"].lower()

    if case["assertion"] == "equals" and case["target_kind"] == "optional":
        if "url" in name or "link" in name:
            return st.one_of(
                st.none(),
                st.just(""),
                _safe_text(max_size=20).map(lambda value: f"https://example.com/{{value}}"),
            )
        return st.one_of(st.none(), st.just(""), _safe_text(max_size=32))

    if "list" in type_repr:
        return st.lists(_safe_text(max_size=12), min_size=1, max_size=4)
    if "bool" in type_repr:
        return st.booleans()
    if "int" in type_repr:
        return st.integers(min_value=-100, max_value=100)
    if name == "location":
        return _safe_text(max_size=16).map(lambda value: f"Generated {{value}}, MA")
    if "url" in name or "link" in name:
        return _safe_text(max_size=20).map(lambda value: f"https://example.com/{{value}}")
    return _safe_text(max_size=32)


def _run_case(case, source_value):
    source_cls = _load_class(case["source_module"], case["source_class"])
    owner_cls = _load_class(case["class_module"], case["class_name"])

    input_kwargs = dict(case["input_kwargs"])
    input_kwargs[case["source_field"]] = source_value
    source = source_cls(**input_kwargs)

    owner = _instance_for(owner_cls)
    result = getattr(owner, case["method_name"])(source)
    actual = getattr(result, case["target_arg"])

    if case["assertion"] == "equals":
        assert actual == source_value
    else:
        _assert_observed(actual, source_value)


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_generated_dataclass_transform_property_hypothesis(case):
    @settings(max_examples=25, deadline=None)
    @given(source_value=_strategy_for_case(case))
    def property_check(source_value):
        _run_case(case, source_value)

    property_check()
'''


def write_report(
    path: Path,
    analysis_dir: Path,
    tests_path: Path,
    cases: list[ExecutableCase],
    helper_cases: list[HelperBoundaryCase],
    common_ast_cases: list[CommonAstCase],
    interprocedural_cases: list[InterproceduralCase],
    skipped: list[str],
    helper_skipped: list[str],
    common_ast_skipped: list[str],
    interprocedural_skipped: list[str],
) -> None:
    cwd = Path.cwd().resolve()

    def display(path: Path) -> str:
        try:
            return str(path.resolve().relative_to(cwd))
        except ValueError:
            return str(path)

    tests_display = display(tests_path)
    hypothesis_path = tests_path.with_name("test_generated_dataclass_hypothesis.py")
    helper_boundary_path = tests_path.with_name("test_generated_helper_boundaries.py")
    common_ast_path = tests_path.with_name("test_generated_common_ast_properties.py")
    interprocedural_path = tests_path.with_name("test_generated_interprocedural_properties.py")
    lines = [
        "# Generated Test Report",
        "",
        f"- Analysis directory: `{analysis_dir}`",
        f"- Test file: `{tests_display}`",
        f"- Hypothesis test file: `{display(hypothesis_path)}`",
        f"- Helper boundary test file: `{display(helper_boundary_path)}`",
        f"- Common-AST test file: `{display(common_ast_path)}`",
        f"- Interprocedural test file: `{display(interprocedural_path)}`",
        f"- Executable cases emitted: {len(cases)}",
        f"- Helper boundary cases emitted: {len(helper_cases)}",
        f"- Common-AST cases emitted: {len(common_ast_cases)}",
        f"- Interprocedural cases emitted: {len(interprocedural_cases)}",
        f"- Candidate relations left as review items: {len(skipped)}",
        f"- Helper boundary relations left as review items: {len(helper_skipped)}",
        f"- Common-AST relations left as review items: {len(common_ast_skipped)}",
        f"- Interprocedural relations left as review items: {len(interprocedural_skipped)}",
        "",
        "## Run",
        "",
        "Set `PYTHONPATH` to the target project checkout and run pytest against this directory:",
        "",
        "```bash",
        f"PYTHONPATH=/path/to/target-project pytest {display(tests_path.parent)}",
        "```",
        "",
        "Or run through the SPS-VeriSpec validation wrapper to produce a Markdown summary:",
        "",
        "```bash",
        f"python3 tools/validate_generated_tests.py {display(tests_path.parent)} --target-project /path/to/target-project",
        "```",
        "",
        "To produce relation-yield, common-AST/interprocedural yield, and coverage-delta evaluation stats:",
        "",
        "```bash",
        f"python3 tools/evaluation_stats.py --analysis-dir {analysis_dir} --target-project /path/to/target-project --target-tests /path/to/target-project/tests --generated-tests {display(tests_path.parent)} --report /tmp/sps-evaluation-stats.md",
        "```",
        "",
        "To run relation-guided transform, collection-iteration, interprocedural-pipeline, and boundary mutation evaluation against handwritten, generated, and combined suites:",
        "",
        "```bash",
        f"python3 tools/mutation_eval.py --analysis-dir {analysis_dir} --target-project /path/to/target-project --target-tests /path/to/target-project/tests --generated-tests {display(tests_path.parent)} --max-mutants 12 --report /tmp/sps-mutation-eval.md",
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

    lines.extend(["", "## Helper Boundary Cases", ""])
    if helper_cases:
        for case in helper_cases:
            lines.append(
                f"- `{case.id}`: `{case.module_name}.{case.class_name}.{case.method_name}` "
                f"with `{case.param_name}` length {case.input_length}; output length <= {case.expected_max_length}"
            )
    else:
        lines.append("- No helper boundary cases were emitted.")

    lines.extend(["", "## Helper Boundary Review Candidates", ""])
    if helper_skipped:
        lines.extend(helper_skipped)
    else:
        lines.append("- No helper boundary candidates were skipped.")

    lines.extend(["", "## Common-AST Cases", ""])
    if common_ast_cases:
        for case in common_ast_cases:
            lines.append(
                f"- `{case.id}`: `{case.module_name}.{case.class_name}.{case.method_name}` "
                f"iterates `{case.source_class}.{case.source_field}` and observes `{case.expected_value}`"
            )
    else:
        lines.append("- No common-AST cases were emitted.")

    lines.extend(["", "## Common-AST Review Candidates", ""])
    if common_ast_skipped:
        lines.extend(common_ast_skipped)
    else:
        lines.append("- No common-AST candidates were skipped.")

    lines.extend(["", "## Interprocedural Cases", ""])
    if interprocedural_cases:
        for case in interprocedural_cases:
            lines.append(
                f"- `{case.id}`: `{case.source_class}.{case.source_field}` reaches "
                f"`{case.target_class}.{case.target_field}` through "
                f"`{case.class_module}.{case.class_name}.{case.method_name}`"
            )
    else:
        lines.append("- No interprocedural cases were emitted.")

    lines.extend(["", "## Interprocedural Review Candidates", ""])
    if interprocedural_skipped:
        lines.extend(interprocedural_skipped)
    else:
        lines.append("- No interprocedural candidates were skipped.")

    lines.extend(
        [
            "",
            "## Notes",
            "",
            "The dataclass-transform generator only emits public `format*` method tests with string/list observations.",
            "The Hypothesis file is optional at runtime and is skipped by pytest when Hypothesis is not installed.",
            "Helper boundary tests are lower-confidence because they may call private helper methods directly.",
            "Common-AST tests are conservative and currently focus on observable collection iteration over dataclass fields.",
            "Interprocedural tests are conservative and currently require a public method that drives the source dataclass to the output dataclass.",
            "Relations involving publishing, private helpers, branch/control facts, lossy flows, nullable-use findings, protocol-order findings, or unsupported interprocedural outputs are kept as review candidates until stronger oracles are available.",
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
    params = load_function_params(analysis_dir / "facts")
    owners = load_method_owners(analysis_dir / "facts")
    resolved_params = load_resolved_params(analysis_dir / "facts")
    modules = load_transform_modules(analysis_dir / "test_out")
    targets = load_targets(analysis_dir / "test_out")
    cases, skipped = build_cases(fields, modules, targets, args.max_cases)
    helper_cases, helper_skipped = load_helper_boundary_cases(
        analysis_dir / "semantic_out",
        params,
        owners,
        args.max_cases,
    )
    common_ast_cases, common_ast_skipped = load_common_ast_cases(
        analysis_dir / "semantic_out",
        fields,
        params,
        owners,
        resolved_params,
        args.max_cases,
    )
    interprocedural_cases, interprocedural_skipped = load_interprocedural_cases(
        analysis_dir / "semantic_out",
        analysis_dir / "test_out",
        fields,
        args.max_cases,
    )

    tests_path = output_dir / "test_generated_dataclass_properties.py"
    hypothesis_path = output_dir / "test_generated_dataclass_hypothesis.py"
    helper_boundary_path = output_dir / "test_generated_helper_boundaries.py"
    common_ast_path = output_dir / "test_generated_common_ast_properties.py"
    interprocedural_path = output_dir / "test_generated_interprocedural_properties.py"
    report_path = output_dir / "README.md"
    tests_path.write_text(render_test_file(cases), encoding="utf-8")
    hypothesis_path.write_text(render_hypothesis_test_file(cases), encoding="utf-8")
    helper_boundary_path.write_text(
        render_helper_boundary_test_file(helper_cases),
        encoding="utf-8",
    )
    common_ast_path.write_text(
        render_common_ast_test_file(common_ast_cases),
        encoding="utf-8",
    )
    interprocedural_path.write_text(
        render_interprocedural_test_file(interprocedural_cases),
        encoding="utf-8",
    )
    write_report(
        report_path,
        analysis_dir,
        tests_path,
        cases,
        helper_cases,
        common_ast_cases,
        interprocedural_cases,
        skipped,
        helper_skipped,
        common_ast_skipped,
        interprocedural_skipped,
    )

    print(tests_path)
    print(hypothesis_path)
    print(helper_boundary_path)
    print(common_ast_path)
    print(interprocedural_path)
    print(report_path)


if __name__ == "__main__":
    main()
