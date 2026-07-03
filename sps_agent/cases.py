from __future__ import annotations

import ast
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PUBLIC_DIR = Path(__file__).resolve().parent / "public"

VALIDATION_KEYS = {
    "Return code": "return_code",
    "Passed": "passed",
    "Failed": "failed",
    "Errors": "errors",
    "Skipped": "skipped",
    "XFailed": "xfailed",
    "XPassed": "xpassed",
}

STANDARD_FAMILIES = {
    "dataclass_schema": "dataclass schema",
    "dataclass_constructor": "constructor/defaults",
    "conversion_profile": "conversion profile",
    "transform_required_field": "required-field transform",
    "transform_optional_field": "optional-field transform",
    "helper_boundary": "helper boundary",
    "common_ast": "common AST",
    "interprocedural": "interprocedural slice",
}

CASE_MANIFEST: list[dict[str, Any]] = [
    {
        "id": "cutepetsboston",
        "title": "CutePetsBoston",
        "summary": "Successful end-to-end replay with field-flow, helper-boundary, common-AST, and interprocedural generated tests.",
        "target_path": "CutePetsBoston",
        "generated_tests_path": "generated_tests/cutepetsboston",
        "primary_report": "generated_tests/cutepetsboston/README.md",
        "validation_report": "generated_tests/cutepetsboston/validation_report.md",
        "mode": "replay",
        "live_enabled": True,
        "relation_metrics": {
            "candidate_review": 16,
            "helper_review": 3,
            "common_ast_review": 4,
            "interprocedural_review": 38,
        },
        "family_overrides": {
            "helper_boundary": {"discovered_relations": 6},
            "common_ast": {"discovered_relations": 6},
            "interprocedural": {"discovered_relations": 42},
        },
    },
    {
        "id": "dacite",
        "title": "dacite",
        "summary": "Small dataclass-generalization target with a generated conversion-profile test around dacite.core.from_dict.",
        "target_path": "dacite",
        "generated_tests_path": "generated_tests/dacite",
        "primary_report": "generated_tests/dacite/analysis_report.md",
        "validation_report": "generated_tests/dacite/validation_report.md",
        "mode": "replay",
        "live_enabled": True,
        "family_overrides": {
            "dataclass_schema": {"discovered_relations": 1},
            "dataclass_constructor": {"discovered_relations": 1},
            "conversion_profile": {"discovered_relations": 1},
            "helper_boundary": {"discovered_relations": 3},
            "common_ast": {"discovered_relations": 1},
            "interprocedural": {"discovered_relations": 312},
        },
    },
    {
        "id": "transformers",
        "title": "Transformers slice",
        "summary": "Scale/dependency stress replay focused on generated dataclass schema and constructor/default tests.",
        "target_path": "transformers/src",
        "generated_tests_path": "generated_tests/transformers",
        "primary_report": "generated_tests/transformers/analysis_report.md",
        "validation_report": "generated_tests/transformers/validation_report.md",
        "mode": "replay",
        "live_enabled": False,
        "relation_metrics": {
            "dependency_validated_passed": 99,
            "dependency_validated_skipped": 7,
            "local_replay_skipped": 106,
        },
        "family_overrides": {
            "dataclass_schema": {"discovered_relations": 52},
            "dataclass_constructor": {"discovered_relations": 48},
            "helper_boundary": {"discovered_relations": 99, "review_findings": 4},
            "common_ast": {"discovered_relations": 17, "review_findings": 17},
            "interprocedural": {"discovered_relations": 4},
        },
    },
    {
        "id": "type_checker_case_study",
        "title": "Type-checker case study",
        "summary": "Review-only metamorphic findings are shown as corroborated findings, not trusted generated-suite failures.",
        "target_path": "type_checker_case_study",
        "generated_tests_path": "generated_tests/type_checker_case_study",
        "primary_report": "type_checker_case_study/METAMORPHIC_FINDINGS.md",
        "validation_report": "generated_tests/type_checker_case_study/validation_report.md",
        "secondary_reports": ["type_checker_case_study/out/metamorphic_report.md"],
        "mode": "replay",
        "live_enabled": False,
        "custom_families": {
            "metamorphic_relations": {
                "label": "metamorphic relations",
                "discovered_relations": 67351,
                "emitted_tests": 120,
                "strict_oracles": 0,
                "weak_oracles": 120,
                "review_findings": 224,
            },
            "composition_boundaries": {
                "label": "composition boundaries",
                "discovered_relations": 75,
                "emitted_tests": 75,
                "strict_oracles": 75,
                "weak_oracles": 0,
                "review_findings": 0,
            },
            "composition_chains": {
                "label": "composition chains",
                "discovered_relations": 20,
                "emitted_tests": 20,
                "strict_oracles": 20,
                "weak_oracles": 0,
                "review_findings": 0,
            },
        },
        "relation_metrics": {
            "source_expressions": 5617,
            "metamorphic_applications": 67351,
            "violations": 224,
            "MR-LETLAM": 136,
            "MR-DEADLET": 44,
            "MR-KPROJ": 44,
            "xfail_review_cases": 24,
        },
    },
]

LIVE_TARGETS = {
    "cutepetsboston": {
        "target_project": ROOT / "CutePetsBoston",
        "project_name": "cutepetsboston",
    },
    "dacite": {
        "target_project": ROOT / "dacite",
        "project_name": "dacite",
    },
}


@dataclass(frozen=True)
class RunCommandResult:
    command: list[str]
    returncode: int
    output: str
    timed_out: bool
    truncated: bool


class CaseNotFound(KeyError):
    pass


class LiveRunRejected(ValueError):
    pass


def manifest_by_id() -> dict[str, dict[str, Any]]:
    return {case["id"]: case for case in CASE_MANIFEST}


def get_manifest(case_id: str) -> dict[str, Any]:
    try:
        return manifest_by_id()[case_id]
    except KeyError as exc:
        raise CaseNotFound(case_id) from exc


def rel_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def safe_repo_path(relative_path: str) -> Path:
    path = (ROOT / relative_path).resolve()
    if ROOT.resolve() not in path.parents and path != ROOT.resolve():
        raise ValueError(f"path escapes repository root: {relative_path}")
    return path


def read_text(relative_path: str) -> str:
    path = safe_repo_path(relative_path)
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def excerpt(text: str, *, max_chars: int = 1400) -> str:
    clean = text.strip()
    if len(clean) <= max_chars:
        return clean
    return clean[: max_chars - 18].rstrip() + "\n...[truncated]"


def excerpt_section(text: str, heading: str, *, max_chars: int = 1400) -> str:
    pattern = re.compile(rf"(^##+\s+{re.escape(heading)}\s*$.*?)(?=^##+\s+|\Z)", re.M | re.S)
    match = pattern.search(text)
    return excerpt(match.group(1) if match else text, max_chars=max_chars)


def parse_validation_report(relative_path: str) -> dict[str, int]:
    text = read_text(relative_path)
    result = {
        "return_code": 0,
        "passed": 0,
        "failed": 0,
        "errors": 0,
        "skipped": 0,
        "xfailed": 0,
        "xpassed": 0,
    }
    for label, key in VALIDATION_KEYS.items():
        match = re.search(rf"^- {re.escape(label)}:\s+`?(-?\d+)`?", text, re.M)
        if match:
            result[key] = int(match.group(1))
    return result


def list_constant(path: Path, name: str) -> list[Any]:
    if not path.exists():
        return []
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == name:
                try:
                    value = ast.literal_eval(node.value)
                except (ValueError, TypeError):
                    return []
                return value if isinstance(value, list) else []
    return []


def count_literal_case_ids(path: Path) -> int:
    if not path.exists():
        return 0
    return len(re.findall(r"^\s+'id':\s+", path.read_text(encoding="utf-8"), re.M))


def generated_constants(generated_tests_path: str) -> dict[str, list[Any]]:
    root = safe_repo_path(generated_tests_path)
    return {
        "properties": list_constant(root / "test_generated_dataclass_properties.py", "CASES"),
        "schema": list_constant(root / "test_generated_dataclass_schema.py", "SCHEMA_CASES"),
        "constructor": list_constant(root / "test_generated_dataclass_schema.py", "CONSTRUCTOR_CASES"),
        "conversion": list_constant(root / "test_generated_dataclass_conversions.py", "CONVERSION_CASES"),
        "helper": list_constant(root / "test_generated_helper_boundaries.py", "HELPER_BOUNDARY_CASES"),
        "common_ast": list_constant(root / "test_generated_common_ast_properties.py", "COMMON_AST_CASES"),
        "interprocedural": list_constant(root / "test_generated_interprocedural_properties.py", "INTERPROCEDURAL_CASES"),
    }


def summarize_examples(cases: list[Any], limit: int = 3) -> list[str]:
    examples: list[str] = []
    for case in cases[:limit]:
        if isinstance(case, dict):
            case_id = case.get("id")
            if isinstance(case_id, str):
                examples.append(case_id)
                continue
            if "module_name" in case and "class_name" in case:
                examples.append(f"{case['module_name']}.{case['class_name']}")
                continue
        examples.append(str(case)[:120])
    return examples


def empty_family(family_id: str, label: str) -> dict[str, Any]:
    return {
        "id": family_id,
        "label": label,
        "discovered_relations": 0,
        "emitted_tests": 0,
        "strict_oracles": 0,
        "weak_oracles": 0,
        "review_findings": 0,
        "examples": [],
    }


def build_standard_families(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    constants = generated_constants(manifest["generated_tests_path"])
    properties = constants["properties"]
    required = [case for case in properties if not isinstance(case, dict) or case.get("target_kind") != "optional"]
    optional = [case for case in properties if isinstance(case, dict) and case.get("target_kind") == "optional"]

    families = {key: empty_family(key, label) for key, label in STANDARD_FAMILIES.items()}
    families["dataclass_schema"].update(
        emitted_tests=len(constants["schema"]),
        strict_oracles=len(constants["schema"]),
        examples=summarize_examples(constants["schema"]),
    )
    families["dataclass_constructor"].update(
        emitted_tests=len(constants["constructor"]),
        strict_oracles=len(constants["constructor"]),
        examples=summarize_examples(constants["constructor"]),
    )
    families["conversion_profile"].update(
        emitted_tests=len(constants["conversion"]),
        strict_oracles=len(constants["conversion"]),
        examples=summarize_examples(constants["conversion"]),
    )
    families["transform_required_field"].update(
        emitted_tests=len(required),
        strict_oracles=sum(1 for case in required if isinstance(case, dict) and case.get("assertion") == "equals"),
        weak_oracles=sum(1 for case in required if not isinstance(case, dict) or case.get("assertion") != "equals"),
        examples=summarize_examples(required),
    )
    families["transform_optional_field"].update(
        emitted_tests=len(optional),
        strict_oracles=len(optional),
        examples=summarize_examples(optional),
    )
    families["helper_boundary"].update(
        emitted_tests=len(constants["helper"]),
        strict_oracles=len(constants["helper"]),
        examples=summarize_examples(constants["helper"]),
    )
    families["common_ast"].update(
        emitted_tests=len(constants["common_ast"]),
        weak_oracles=len(constants["common_ast"]),
        examples=summarize_examples(constants["common_ast"]),
    )
    families["interprocedural"].update(
        emitted_tests=len(constants["interprocedural"]),
        weak_oracles=len(constants["interprocedural"]),
        examples=summarize_examples(constants["interprocedural"]),
    )

    for family in families.values():
        family["discovered_relations"] = max(
            int(family["discovered_relations"]),
            int(family["emitted_tests"]),
        )

    for family_id, override in manifest.get("family_overrides", {}).items():
        if family_id in families:
            families[family_id].update(override)

    return families


def build_custom_families(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    families: dict[str, dict[str, Any]] = {}
    for family_id, spec in manifest.get("custom_families", {}).items():
        family = empty_family(family_id, spec.get("label", family_id.replace("_", " ")))
        family.update({key: value for key, value in spec.items() if key != "label"})
        families[family_id] = family

    generated = safe_repo_path(manifest["generated_tests_path"])
    if "metamorphic_relations" in families:
        text = (generated / "test_generated_metamorphic.py").read_text(encoding="utf-8", errors="replace")
        families["metamorphic_relations"]["emitted_tests"] = text.count("pytest.param(")
        families["metamorphic_relations"]["review_findings"] = 224
        families["metamorphic_relations"]["weak_oracles"] = families["metamorphic_relations"]["emitted_tests"]
        families["metamorphic_relations"]["examples"] = [
            "MR-LETLAM app-instance violation",
            "MR-DEADLET substitution violation",
            "MR-KPROJ corroborating violation",
        ]
    if "composition_boundaries" in families:
        families["composition_boundaries"]["emitted_tests"] = count_literal_case_ids(
            generated / "test_generated_composition_boundaries.py"
        )
        families["composition_boundaries"]["strict_oracles"] = families["composition_boundaries"]["emitted_tests"]
        families["composition_boundaries"]["examples"] = ["ill->well boundary", "well->ill boundary"]
    if "composition_chains" in families:
        families["composition_chains"]["emitted_tests"] = count_literal_case_ids(
            generated / "test_generated_composition_chains.py"
        )
        families["composition_chains"]["strict_oracles"] = families["composition_chains"]["emitted_tests"]
        families["composition_chains"]["examples"] = ["type ladder", "mixed composition chain"]
    return families


def build_families(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if manifest.get("custom_families"):
        return build_custom_families(manifest)
    return build_standard_families(manifest)


def artifact_list(manifest: dict[str, Any]) -> list[dict[str, str]]:
    paths = [
        ("primary_report", "Primary report", manifest.get("primary_report")),
        ("validation_report", "Validation report", manifest.get("validation_report")),
    ]
    for index, path in enumerate(manifest.get("secondary_reports", []), start=1):
        paths.append((f"secondary_report_{index}", "Supporting report", path))
    generated_root = safe_repo_path(manifest["generated_tests_path"])
    for path in sorted(generated_root.glob("test_generated_*.py")):
        paths.append((path.stem, path.name, rel_path(path)))

    artifacts: list[dict[str, str]] = []
    for artifact_id, label, relative_path in paths:
        if not relative_path:
            continue
        text = read_text(relative_path)
        if not text:
            continue
        artifacts.append(
            {
                "id": artifact_id,
                "label": label,
                "path": relative_path,
                "excerpt": excerpt(text),
                "href": f"/api/cases/{manifest['id']}/artifacts/{artifact_id}",
            }
        )
    return artifacts


def build_graph(manifest: dict[str, Any], families: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes: list[dict[str, Any]] = [
        {
            "id": "target",
            "kind": "pipeline",
            "label": "Python target",
            "metrics": {"path": manifest["target_path"]},
            "detail": manifest["summary"],
        },
        {
            "id": "facts",
            "kind": "pipeline",
            "label": "AST facts",
            "metrics": {},
            "detail": "Python source facts extracted from dataclasses, functions, calls, literals, field reads/writes, and control surfaces.",
        },
        {
            "id": "relations",
            "kind": "pipeline",
            "label": "Souffle relations",
            "metrics": manifest.get("relation_metrics", {}),
            "detail": "Datalog-derived relation families are normalized before generated tests or review findings are shown.",
        },
    ]
    edges: list[dict[str, Any]] = [
        {"id": "target-facts", "source": "target", "target": "facts", "label": "extract", "count": 1},
        {"id": "facts-relations", "source": "facts", "target": "relations", "label": "derive", "count": 1},
    ]

    for family_id, family in families.items():
        node_id = f"family:{family_id}"
        nodes.append(
            {
                "id": node_id,
                "kind": "test-family",
                "label": family["label"],
                "metrics": {
                    "discovered_relations": family["discovered_relations"],
                    "emitted_tests": family["emitted_tests"],
                    "strict_oracles": family["strict_oracles"],
                    "weak_oracles": family["weak_oracles"],
                    "review_findings": family["review_findings"],
                },
                "examples": family.get("examples", []),
                "detail": "Generated tests are grouped by family; raw files are secondary artifacts.",
            }
        )
        edges.append(
            {
                "id": f"relations-{family_id}",
                "source": "relations",
                "target": node_id,
                "label": f"{family['discovered_relations']} discovered / {family['emitted_tests']} emitted",
                "count": max(int(family["discovered_relations"]), int(family["emitted_tests"]), 1),
            }
        )
        if family["emitted_tests"]:
            edges.append(
                {
                    "id": f"{family_id}-validation",
                    "source": node_id,
                    "target": "validation",
                    "label": f"{family['emitted_tests']} tests",
                    "count": max(int(family["emitted_tests"]), 1),
                }
            )

    validation = parse_validation_report(manifest["validation_report"])
    nodes.append(
        {
            "id": "validation",
            "kind": "validation",
            "label": "pytest validation",
            "metrics": validation,
            "detail": "Checked-in validation replay for the generated suite.",
        }
    )

    review_findings = sum(int(family.get("review_findings", 0)) for family in families.values())
    review_findings += int(manifest.get("relation_metrics", {}).get("candidate_review", 0))
    if review_findings:
        nodes.append(
            {
                "id": "findings",
                "kind": "finding",
                "label": "review findings",
                "metrics": {"review_findings": review_findings, **manifest.get("relation_metrics", {})},
                "detail": "Review-only findings are intentionally not treated as trusted generated-suite failures.",
            }
        )
        edges.append(
            {
                "id": "relations-findings",
                "source": "relations",
                "target": "findings",
                "label": f"{review_findings} review items",
                "count": review_findings,
            }
        )

    return nodes, edges


def list_cases() -> list[dict[str, Any]]:
    result = []
    for manifest in CASE_MANIFEST:
        validation = parse_validation_report(manifest["validation_report"])
        families = build_families(manifest)
        result.append(
            {
                "id": manifest["id"],
                "title": manifest["title"],
                "summary": manifest["summary"],
                "mode": manifest["mode"],
                "live_enabled": bool(manifest.get("live_enabled")),
                "validation": validation,
                "emitted_tests": sum(int(family["emitted_tests"]) for family in families.values()),
                "review_findings": sum(int(family.get("review_findings", 0)) for family in families.values())
                + int(manifest.get("relation_metrics", {}).get("candidate_review", 0)),
            }
        )
    return result


def case_detail(case_id: str) -> dict[str, Any]:
    manifest = get_manifest(case_id)
    families = build_families(manifest)
    nodes, edges = build_graph(manifest, families)
    artifacts = artifact_list(manifest)
    primary_text = read_text(manifest["primary_report"])
    validation = parse_validation_report(manifest["validation_report"])
    metrics = {
        "validation": validation,
        "families": families,
        "totals": {
            "discovered_relations": sum(int(family["discovered_relations"]) for family in families.values()),
            "emitted_tests": sum(int(family["emitted_tests"]) for family in families.values()),
            "strict_oracles": sum(int(family["strict_oracles"]) for family in families.values()),
            "weak_oracles": sum(int(family["weak_oracles"]) for family in families.values()),
            "review_findings": sum(int(family.get("review_findings", 0)) for family in families.values())
            + int(manifest.get("relation_metrics", {}).get("candidate_review", 0)),
        },
    }
    return {
        "case": {
            "id": manifest["id"],
            "title": manifest["title"],
            "summary": manifest["summary"],
            "mode": manifest["mode"],
            "live_enabled": bool(manifest.get("live_enabled")),
            "target_path": manifest["target_path"],
            "generated_tests_path": manifest["generated_tests_path"],
        },
        "nodes": nodes,
        "edges": edges,
        "metrics": metrics,
        "artifacts": artifacts,
        "excerpts": {
            "analysis": excerpt_section(primary_text, "Analysis Results"),
            "generated_tests": excerpt_section(primary_text, "Generated Tests"),
            "validation": excerpt(read_text(manifest["validation_report"])),
        },
    }


def artifact_text(case_id: str, artifact_id: str) -> tuple[str, str]:
    manifest = get_manifest(case_id)
    artifacts = {artifact["id"]: artifact for artifact in artifact_list(manifest)}
    if artifact_id not in artifacts:
        raise CaseNotFound(f"{case_id}/{artifact_id}")
    artifact = artifacts[artifact_id]
    return artifact["path"], read_text(artifact["path"])


def truncate_output(output: str, limit: int) -> tuple[str, bool]:
    if limit <= 0 or len(output) <= limit:
        return output, False
    marker = "\n...[output truncated]\n"
    keep = max(limit - len(marker), 0)
    return marker + output[-keep:], True


def run_command_with_limits(
    command: list[str],
    *,
    cwd: Path = ROOT,
    timeout_seconds: int = 120,
    output_limit: int = 12000,
) -> RunCommandResult:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_seconds,
        )
        output, truncated = truncate_output(completed.stdout, output_limit)
        return RunCommandResult(command, completed.returncode, output, False, truncated)
    except subprocess.TimeoutExpired as exc:
        raw_output = exc.output or ""
        if isinstance(raw_output, bytes):
            raw_output = raw_output.decode("utf-8", errors="replace")
        output, truncated = truncate_output(str(raw_output), output_limit)
        message = f"\n...[command timed out after {timeout_seconds}s]\n"
        return RunCommandResult(command, 124, output + message, True, truncated)


def build_live_command(case_id: str, work_dir: Path) -> list[str]:
    if case_id not in LIVE_TARGETS:
        raise LiveRunRejected(f"live runs are allowlisted; unsupported target: {case_id}")
    spec = LIVE_TARGETS[case_id]
    return [
        sys.executable,
        str(ROOT / "tools" / "evaluate_pipeline.py"),
        "--target-project",
        str(spec["target_project"]),
        "--project-name",
        spec["project_name"],
        "--work-dir",
        str(work_dir),
        "--skip-mutation",
    ]


def run_live_case(
    case_id: str,
    *,
    work_dir: Path | None = None,
    timeout_seconds: int = 120,
    output_limit: int = 12000,
) -> dict[str, Any]:
    run_dir = work_dir or Path("/tmp") / f"sps-agent-{case_id}"
    command = build_live_command(case_id, run_dir)
    result = run_command_with_limits(
        command,
        cwd=ROOT,
        timeout_seconds=timeout_seconds,
        output_limit=output_limit,
    )
    return {
        **asdict(result),
        "work_dir": str(run_dir),
        "case_id": case_id,
        "report_path": str(run_dir / "pipeline_report.md"),
        "json_report_path": str(run_dir / "pipeline_report.json"),
    }
