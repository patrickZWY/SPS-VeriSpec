from __future__ import annotations

import argparse
import dataclasses
import importlib
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.oracle_synthesis import OracleManifestEntry, write_manifest


@dataclass(frozen=True)
class CallSpec:
    case_id: str
    callable_path: str
    args: list[object]
    kwargs: dict[str, object]


@dataclass(frozen=True)
class Observation:
    call: CallSpec
    result: object
    normalized_result: object
    output_kind: str
    output_type_tag: str
    output_fields: dict[str, object]
    input_paths: dict[str, object]


@dataclass(frozen=True)
class InvariantCandidate:
    property_id: str
    test_id: str
    callable_path: str
    candidate_kind: str
    reason: str
    oracle_strength: str
    output_selector: dict[str, str]
    input_path: str | None
    expected_type_tag: str | None
    case_specs: list[dict[str, object]]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Mine quarantined invariant candidates from structured Python outputs "
            "using explicit replayable call specifications."
        )
    )
    parser.add_argument(
        "--spec",
        required=True,
        help="JSON file describing replayable calls.",
    )
    parser.add_argument(
        "--target-project",
        required=True,
        help="Target Python project checkout to put on PYTHONPATH.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "generated_tests"),
        help="Directory where generated tests and manifests are written.",
    )
    parser.add_argument(
        "--project-name",
        required=True,
        help="Name used for the generated subdirectory.",
    )
    return parser.parse_args()


def safe_id(*parts: str) -> str:
    joined = "-".join(parts)
    normalized = []
    for char in joined:
        normalized.append(char if char.isalnum() or char in "._-" else "-")
    return "".join(normalized).strip("-") or "candidate"


def safe_py_id(*parts: str) -> str:
    identifier = safe_id(*parts).replace("-", "_").replace(".", "_")
    if not identifier or identifier[0].isdigit():
        identifier = f"candidate_{identifier}"
    return identifier


def load_spec(path: Path) -> list[CallSpec]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    calls = payload.get("calls", payload)
    loaded: list[CallSpec] = []
    for index, item in enumerate(calls, start=1):
        loaded.append(
            CallSpec(
                case_id=item.get("id", f"case_{index:03d}"),
                callable_path=item["callable"],
                args=item.get("args", []),
                kwargs=item.get("kwargs", {}),
            )
        )
    return loaded


def materialize_value(value: object) -> object:
    if isinstance(value, list):
        return [materialize_value(item) for item in value]
    if isinstance(value, dict):
        symbol = value.get("__symbol__") if isinstance(value, dict) else None
        if isinstance(symbol, str):
            return load_symbol(symbol)
        marker = value.get("__dataclass__") if isinstance(value, dict) else None
        if isinstance(marker, str):
            cls = load_symbol(marker)
            fields = value.get("fields", {})
            if not isinstance(fields, dict):
                raise TypeError(f"Dataclass fields for `{marker}` must be a dict.")
            kwargs = {key: materialize_value(raw) for key, raw in fields.items()}
            return cls(**kwargs)
        return {key: materialize_value(raw) for key, raw in value.items()}
    return value


def load_symbol(path: str) -> object:
    module_name, symbol_name = path.split(":", 1)
    importlib.invalidate_caches()
    sys.modules.pop(module_name, None)
    module = importlib.import_module(module_name)
    symbol = module
    for part in symbol_name.split("."):
        symbol = getattr(symbol, part)
    return symbol


def normalize_value(value: object) -> object:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {
            "__kind__": "dataclass",
            "type": type_tag(value),
            "fields": {
                field.name: normalize_value(getattr(value, field.name))
                for field in dataclasses.fields(value)
            },
        }
    if isinstance(value, dict):
        return {str(key): normalize_value(raw) for key, raw in value.items()}
    if isinstance(value, list):
        return [normalize_value(item) for item in value]
    if isinstance(value, tuple):
        return [normalize_value(item) for item in value]
    return value


def type_tag(value: object) -> str:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return f"{type(value).__module__}:{type(value).__qualname__}"
    if isinstance(value, dict):
        return "builtins:dict"
    if isinstance(value, list):
        return "builtins:list"
    if isinstance(value, tuple):
        return "builtins:tuple"
    return f"{type(value).__module__}:{type(value).__qualname__}"


def top_level_output_fields(value: object) -> tuple[str, dict[str, object]]:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return (
            "dataclass",
            {
                field.name: getattr(value, field.name)
                for field in dataclasses.fields(value)
            },
        )
    if isinstance(value, dict):
        return ("dict", {str(key): raw for key, raw in value.items()})
    return ("scalar", {})


def flatten_input_paths(args: list[object], kwargs: dict[str, object]) -> dict[str, object]:
    flattened: dict[str, object] = {}
    for index, value in enumerate(args):
        flatten_value(f"args[{index}]", value, flattened)
    for key, value in kwargs.items():
        flatten_value(f"kwargs.{key}", value, flattened)
    return flattened


def flatten_value(prefix: str, value: object, output: dict[str, object]) -> None:
    output[prefix] = value
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        for field in dataclasses.fields(value):
            flatten_value(f"{prefix}.{field.name}", getattr(value, field.name), output)
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if isinstance(key, str):
                flatten_value(f"{prefix}.{key}", item, output)
        return


def execute_calls(call_specs: list[CallSpec], target_project: Path) -> list[Observation]:
    target = str(target_project)
    if target not in sys.path:
        sys.path.insert(0, target)

    observations: list[Observation] = []
    for call in call_specs:
        target_callable = load_symbol(call.callable_path)
        args = [materialize_value(value) for value in call.args]
        kwargs = {key: materialize_value(value) for key, value in call.kwargs.items()}
        result = target_callable(*args, **kwargs)
        output_kind, output_fields = top_level_output_fields(result)
        observations.append(
            Observation(
                call=call,
                result=result,
                normalized_result=normalize_value(result),
                output_kind=output_kind,
                output_type_tag=type_tag(result),
                output_fields=output_fields,
                input_paths=flatten_input_paths(args, kwargs),
            )
        )
    return observations


def comparable_value(value: object) -> object:
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        return normalize_value(value)
    if isinstance(value, dict):
        return normalize_value(value)
    if isinstance(value, list):
        return normalize_value(value)
    if isinstance(value, tuple):
        return normalize_value(value)
    return value


def case_payload(call: CallSpec) -> dict[str, object]:
    return {
        "id": call.case_id,
        "callable": call.callable_path,
        "args": call.args,
        "kwargs": call.kwargs,
    }


def mine_candidates(observations: list[Observation]) -> list[InvariantCandidate]:
    by_callable: dict[str, list[Observation]] = defaultdict(list)
    for observation in observations:
        by_callable[observation.call.callable_path].append(observation)

    candidates: list[InvariantCandidate] = []
    for callable_path, group in sorted(by_callable.items()):
        case_specs = [case_payload(item.call) for item in group]
        if len({item.output_type_tag for item in group}) == 1:
            type_tag_value = group[0].output_type_tag
            property_id = safe_id("dynamic_invariant", callable_path, "return_type")
            candidates.append(
                InvariantCandidate(
                    property_id=property_id,
                    test_id=safe_py_id("test", property_id),
                    callable_path=callable_path,
                    candidate_kind="return_type_is",
                    reason=f"Observed fixed structured return type `{type_tag_value}` for `{callable_path}`.",
                    oracle_strength="exact",
                    output_selector={"kind": "return"},
                    input_path=None,
                    expected_type_tag=type_tag_value,
                    case_specs=case_specs,
                )
            )

        if group[0].output_kind not in {"dataclass", "dict"}:
            continue
        shared_fields = set(group[0].output_fields)
        for observation in group[1:]:
            shared_fields &= set(observation.output_fields)

        for field_name in sorted(shared_fields):
            property_id = safe_id("dynamic_invariant", callable_path, field_name, "present")
            candidates.append(
                InvariantCandidate(
                    property_id=property_id,
                    test_id=safe_py_id("test", property_id),
                    callable_path=callable_path,
                    candidate_kind="output_field_present",
                    reason=f"Observed `{field_name}` present in every structured output for `{callable_path}`.",
                    oracle_strength="observational",
                    output_selector={"kind": group[0].output_kind, "field": field_name},
                    input_path=None,
                    expected_type_tag=None,
                    case_specs=case_specs,
                )
            )

            candidate_input_paths = set(group[0].input_paths)
            for observation in group[1:]:
                candidate_input_paths &= set(observation.input_paths)

            for input_path in sorted(candidate_input_paths):
                if all(
                    comparable_value(observation.output_fields[field_name])
                    == comparable_value(observation.input_paths[input_path])
                    for observation in group
                ):
                    property_id = safe_id("dynamic_invariant", callable_path, field_name, input_path, "equals")
                    candidates.append(
                        InvariantCandidate(
                            property_id=property_id,
                            test_id=safe_py_id("test", property_id),
                            callable_path=callable_path,
                            candidate_kind="output_field_equals_input",
                            reason=(
                                f"Observed `{field_name}` equal to `{input_path}` across "
                                f"{len(group)} replayed calls for `{callable_path}`."
                            ),
                            oracle_strength="exact",
                            output_selector={"kind": group[0].output_kind, "field": field_name},
                            input_path=input_path,
                            expected_type_tag=None,
                            case_specs=case_specs,
                        )
                    )

                field_value = group[0].output_fields[field_name]
                input_value = group[0].input_paths[input_path]
                if not hasattr(field_value, "__len__") or not hasattr(input_value, "__len__"):
                    continue
                if all(
                    len(observation.output_fields[field_name]) == len(observation.input_paths[input_path])  # type: ignore[arg-type]
                    for observation in group
                ):
                    property_id = safe_id("dynamic_invariant", callable_path, field_name, input_path, "length")
                    candidates.append(
                        InvariantCandidate(
                            property_id=property_id,
                            test_id=safe_py_id("test", property_id),
                            callable_path=callable_path,
                            candidate_kind="output_field_length_equals_input_length",
                            reason=(
                                f"Observed `len({field_name}) == len({input_path})` across "
                                f"{len(group)} replayed calls for `{callable_path}`."
                            ),
                            oracle_strength="observational",
                            output_selector={"kind": group[0].output_kind, "field": field_name},
                            input_path=input_path,
                            expected_type_tag=None,
                            case_specs=case_specs,
                        )
                    )
    unique: dict[str, InvariantCandidate] = {}
    for candidate in candidates:
        unique[candidate.property_id] = candidate
    return list(unique.values())


def render_quarantined_invariant_tests(candidates: list[InvariantCandidate]) -> str:
    lines = [
        '"""',
        "Quarantined dynamically mined invariant candidates.",
        "",
        "These tests are review artifacts, not trusted generated-suite evidence.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "import dataclasses",
        "import importlib",
        "import pytest",
        "",
        "pytestmark = [",
        "    pytest.mark.xfail(reason=\"quarantined mined invariant candidate\", strict=False),",
        "]",
        "",
        "",
        "def _load_symbol(path: str):",
        "    module_name, symbol_name = path.split(\":\", 1)",
        "    module = importlib.import_module(module_name)",
        "    symbol = module",
        "    for part in symbol_name.split(\".\"):",
        "        symbol = getattr(symbol, part)",
        "    return symbol",
        "",
        "",
        "def _materialize_value(value):",
        "    if isinstance(value, list):",
        "        return [_materialize_value(item) for item in value]",
        "    if isinstance(value, dict):",
        "        symbol = value.get(\"__symbol__\")",
        "        if isinstance(symbol, str):",
        "            return _load_symbol(symbol)",
        "        marker = value.get(\"__dataclass__\")",
        "        if isinstance(marker, str):",
        "            cls = _load_symbol(marker)",
        "            fields = value.get(\"fields\", {})",
        "            return cls(**{key: _materialize_value(raw) for key, raw in fields.items()})",
        "        return {key: _materialize_value(raw) for key, raw in value.items()}",
        "    return value",
        "",
        "",
        "def _resolve_path(call_spec, path: str):",
        "    args = [_materialize_value(item) for item in call_spec['args']]",
        "    kwargs = {key: _materialize_value(value) for key, value in call_spec['kwargs'].items()}",
        "    current = {'args': args, 'kwargs': kwargs}",
        "    token = ''",
        "    parts = []",
        "    index = 0",
        "    while index < len(path):",
        "        char = path[index]",
        "        if char == '.':",
        "            if token:",
        "                parts.append(token)",
        "                token = ''",
        "            index += 1",
        "            continue",
        "        if char == '[':",
        "            if token:",
        "                parts.append(token)",
        "                token = ''",
        "            end = path.index(']', index)",
        "            parts.append(int(path[index + 1:end]))",
        "            index = end + 1",
        "            continue",
        "        token += char",
        "        index += 1",
        "    if token:",
        "        parts.append(token)",
        "    for part in parts:",
        "        if isinstance(part, int):",
        "            current = current[part]",
        "        elif dataclasses.is_dataclass(current) and not isinstance(current, type):",
        "            current = getattr(current, part)",
        "        else:",
        "            current = current[part]",
        "    return current",
        "",
        "",
        "def _invoke(call_spec):",
        "    target = _load_symbol(call_spec['callable'])",
        "    args = [_materialize_value(item) for item in call_spec['args']]",
        "    kwargs = {key: _materialize_value(value) for key, value in call_spec['kwargs'].items()}",
        "    return target(*args, **kwargs)",
        "",
        "",
        "def _output_value(result, selector):",
        "    if selector['kind'] == 'return':",
        "        return result",
        "    field = selector['field']",
        "    if selector['kind'] == 'dataclass':",
        "        return getattr(result, field)",
        "    return result[field]",
        "",
        "",
    ]
    if not candidates:
        lines.extend(
            [
                "def test_no_mined_invariant_candidates_emitted():",
                '    pytest.skip("No invariant candidates were mined.")',
                "",
            ]
        )
        return "\n".join(lines)

    for candidate in candidates:
        lines.extend(
            [
                f"# property_id: {candidate.property_id}",
                f"# reason: {candidate.reason}",
                f"{candidate.test_id}_CASES = {json.dumps(candidate.case_specs, indent=2, sort_keys=True)}",
                "",
                f"@pytest.mark.parametrize('call_spec', {candidate.test_id}_CASES, ids=[case['id'] for case in {candidate.test_id}_CASES])",
                f"def {candidate.test_id}(call_spec):",
                "    result = _invoke(call_spec)",
            ]
        )
        if candidate.candidate_kind == "return_type_is":
            lines.append(f"    assert type(result).__module__ + ':' + type(result).__qualname__ == {candidate.expected_type_tag!r}")
        elif candidate.candidate_kind == "output_field_present":
            if candidate.output_selector["kind"] == "dataclass":
                lines.append(f"    assert hasattr(result, {candidate.output_selector['field']!r})")
            else:
                lines.append(f"    assert {candidate.output_selector['field']!r} in result")
        elif candidate.candidate_kind == "output_field_equals_input":
            lines.append(f"    observed = _output_value(result, {json.dumps(candidate.output_selector, sort_keys=True)})")
            lines.append(f"    expected = _resolve_path(call_spec, {candidate.input_path!r})")
            lines.append("    assert observed == expected")
        elif candidate.candidate_kind == "output_field_length_equals_input_length":
            lines.append(f"    observed = _output_value(result, {json.dumps(candidate.output_selector, sort_keys=True)})")
            lines.append(f"    expected = _resolve_path(call_spec, {candidate.input_path!r})")
            lines.append("    assert len(observed) == len(expected)")
        else:
            lines.append("    pytest.skip('Unsupported candidate kind')")
        lines.append("")
    return "\n".join(lines)


def build_manifest_entries(
    candidates: list[InvariantCandidate],
    generated_test_path: str,
) -> list[OracleManifestEntry]:
    entries: list[OracleManifestEntry] = []
    for candidate in candidates:
        relation_row = [
            candidate.callable_path,
            candidate.candidate_kind,
            json.dumps(candidate.output_selector, sort_keys=True),
            candidate.input_path or "",
            candidate.expected_type_tag or "",
        ]
        entries.append(
            OracleManifestEntry(
                property_id=candidate.property_id,
                relation_names=["dynamic_invariant"],
                relation_rows=[relation_row],
                source_provenance="static",
                prompt_input_hash=candidate.property_id,
                generated_test_path=generated_test_path,
                test_id=candidate.test_id,
                oracle_strength=candidate.oracle_strength,  # type: ignore[arg-type]
                validation_result="not_run",
                classification="needs_review",
                reason=candidate.reason,
            )
        )
    return entries


def write_report(
    path: Path,
    spec_path: Path,
    candidates: list[InvariantCandidate],
    test_path: Path,
    manifest_path: Path,
) -> None:
    lines = [
        "# Mined Invariant Candidates",
        "",
        f"- Spec: `{spec_path}`",
        f"- Quarantined test file: `{test_path}`",
        f"- Manifest: `{manifest_path}`",
        f"- Candidate count: {len(candidates)}",
        "",
        "## Candidates",
        "",
    ]
    for candidate in candidates:
        lines.append(f"- `{candidate.property_id}`: {candidate.reason}")
    lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    spec_path = Path(args.spec).resolve()
    target_project = Path(args.target_project).resolve()
    output_dir = Path(args.output_dir).resolve() / args.project_name
    output_dir.mkdir(parents=True, exist_ok=True)

    calls = load_spec(spec_path)
    observations = execute_calls(calls, target_project)
    candidates = mine_candidates(observations)

    test_path = output_dir / "test_generated_invariant_candidates.py"
    manifest_path = output_dir / "invariant_candidates.json"
    report_path = output_dir / "invariant_candidates_report.md"

    test_path.write_text(
        render_quarantined_invariant_tests(candidates),
        encoding="utf-8",
    )
    write_manifest(manifest_path, build_manifest_entries(candidates, test_path.name))
    write_report(report_path, spec_path, candidates, test_path, manifest_path)

    print(test_path)
    print(manifest_path)
    print(report_path)


if __name__ == "__main__":
    main()
