from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.oracle_synthesis import ALLOWED_ORACLE_STRENGTHS, safe_id

Provider = Literal["ollama", "openai-compatible"]

DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OPENAI_COMPATIBLE_URL = "http://127.0.0.1:1234/v1"


@dataclass(frozen=True)
class LocalLlmConfig:
    provider: Provider
    base_url: str
    model: str
    timeout_seconds: int = 120


@dataclass(frozen=True)
class ProposalResult:
    tests: list[dict[str, str]]
    rejected: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Ask a local LLM for quarantined semantic test proposals from an "
            "SPS-VeriSpec LLM input contract."
        )
    )
    parser.add_argument("--input", required=True, help="llm_plateau_input.json or llm_oracle_input.json.")
    parser.add_argument("--output", required=True, help="Proposal JSON path consumed by --llm-proposals.")
    parser.add_argument(
        "--report",
        help="Markdown report path. Defaults to the output path with .md suffix.",
    )
    parser.add_argument("--provider", choices=("ollama", "openai-compatible"), default="ollama")
    parser.add_argument(
        "--base-url",
        help=(
            "Local model server URL. Defaults to Ollama on 127.0.0.1:11434 or "
            "OpenAI-compatible /v1 on 127.0.0.1:1234."
        ),
    )
    parser.add_argument("--model", default="qwen2.5-coder:7b")
    parser.add_argument("--timeout-seconds", type=int, default=120)
    parser.add_argument("--max-candidates", type=int, default=12)
    return parser.parse_args()


def load_contract(path: Path, max_candidates: int) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    candidates = payload.get("candidates", [])
    if not isinstance(candidates, list):
        candidates = []
    payload["candidates"] = candidates[: max(0, max_candidates)]
    return payload


def compact_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    related_facts = candidate.get("related_facts", {})
    if isinstance(related_facts, dict):
        related_facts = {
            name: rows[:3] if isinstance(rows, list) else rows
            for name, rows in related_facts.items()
        }
    return {
        "property_id": candidate.get("property_id"),
        "relation_names": candidate.get("relation_names", []),
        "relation_rows": candidate.get("relation_rows", [])[:2],
        "source_provenance": candidate.get("source_provenance", "static"),
        "reason": candidate.get("reason", ""),
        "symbol": candidate.get("symbol", ""),
        "source_location": candidate.get("source_location", {}),
        "related_facts": related_facts,
    }


def build_messages(contract: dict[str, Any]) -> list[dict[str, str]]:
    compact = {
        "policy": contract.get("policy", {}),
        "candidates": [
            compact_candidate(candidate)
            for candidate in contract.get("candidates", [])
            if isinstance(candidate, dict)
        ],
    }
    system = (
        "You are helping SPS-VeriSpec propose quarantined pytest candidates. "
        "Use only the supplied facts and relations. Do not claim the target "
        "program is wrong. Return only JSON."
    )
    user = (
        "For each useful candidate, supply semantic information as a minimal "
        "pytest test proposal. Output exactly this JSON shape:\n"
        "{\n"
        "  \"tests\": [\n"
        "    {\n"
        "      \"property_id\": \"one supplied property_id\",\n"
        "      \"test_id\": \"stable pytest function name\",\n"
        "      \"oracle_strength\": \"exact|metamorphic|observational|exception|weak\",\n"
        "      \"test_code\": \"def test_...():\\n    ...\",\n"
        "      \"semantic_notes\": \"brief grounding in supplied facts\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Reject candidates that require network, credentials, wall-clock timing, "
        "nondeterminism, unsupported imports, or business rules not grounded in "
        "the input. Candidate contract:\n"
        f"{json.dumps(compact, indent=2, sort_keys=True)}"
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def http_json(url: str, payload: dict[str, Any], timeout_seconds: int) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"local LLM request failed: {exc}") from exc


def call_local_model(config: LocalLlmConfig, messages: list[dict[str, str]]) -> str:
    base_url = config.base_url.rstrip("/")
    if config.provider == "ollama":
        response = http_json(
            f"{base_url}/api/chat",
            {
                "model": config.model,
                "stream": False,
                "messages": messages,
                "options": {"temperature": 0},
            },
            config.timeout_seconds,
        )
        message = response.get("message", {})
        if isinstance(message, dict):
            return str(message.get("content", ""))
        return str(response.get("response", ""))

    response = http_json(
        f"{base_url}/chat/completions",
        {
            "model": config.model,
            "temperature": 0,
            "messages": messages,
        },
        config.timeout_seconds,
    )
    choices = response.get("choices", [])
    if choices and isinstance(choices[0], dict):
        message = choices[0].get("message", {})
        if isinstance(message, dict):
            return str(message.get("content", ""))
    return ""


def extract_json_payload(text: str) -> Any:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return json.loads(stripped[start : end + 1])


def validate_proposals(model_text: str, allowed_property_ids: set[str]) -> ProposalResult:
    payload = extract_json_payload(model_text)
    raw_tests = payload.get("tests", payload if isinstance(payload, list) else [])
    tests: list[dict[str, str]] = []
    rejected: list[str] = []
    if not isinstance(raw_tests, list):
        return ProposalResult(tests=[], rejected=["model response did not contain a tests list"])

    for index, item in enumerate(raw_tests):
        if not isinstance(item, dict):
            rejected.append(f"item {index}: not an object")
            continue
        property_id = str(item.get("property_id", ""))
        if property_id not in allowed_property_ids:
            rejected.append(f"item {index}: unknown property_id {property_id!r}")
            continue
        test_code = str(item.get("test_code", "")).rstrip()
        if "def test_" not in test_code:
            rejected.append(f"item {index}: test_code does not define a pytest test")
            continue
        oracle_strength = str(item.get("oracle_strength", "weak"))
        if oracle_strength not in ALLOWED_ORACLE_STRENGTHS:
            oracle_strength = "weak"
        tests.append(
            {
                "property_id": property_id,
                "test_id": safe_id(str(item.get("test_id", property_id))),
                "oracle_strength": oracle_strength,
                "test_code": test_code,
                "semantic_notes": str(item.get("semantic_notes", "")),
                "source": "local_llm_semantic_assist",
            }
        )
    return ProposalResult(tests=tests, rejected=rejected)


def write_outputs(
    output_path: Path,
    report_path: Path,
    result: ProposalResult,
    *,
    config: LocalLlmConfig,
    input_path: Path,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "metadata": {
            "source": "local_llm_semantic_assist",
            "provider": config.provider,
            "model": config.model,
            "input": str(input_path),
            "policy": "quarantined proposals only; validate before promotion",
        },
        "tests": result.tests,
        "rejected": result.rejected,
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# Local LLM Semantic Assist",
        "",
        f"- Provider: `{config.provider}`",
        f"- Model: `{config.model}`",
        f"- Input contract: `{input_path}`",
        f"- Proposal output: `{output_path}`",
        f"- Accepted proposals: {len(result.tests)}",
        f"- Rejected proposals: {len(result.rejected)}",
        "",
        "These proposals remain quarantined. Feed the JSON to `--llm-proposals`,",
        "then validate the generated candidate tests before promotion.",
        "",
    ]
    if result.tests:
        lines.extend(["## Accepted", ""])
        for proposal in result.tests:
            lines.append(f"- `{proposal['property_id']}` -> `{proposal['test_id']}` ({proposal['oracle_strength']})")
        lines.append("")
    if result.rejected:
        lines.extend(["## Rejected", ""])
        for reason in result.rejected:
            lines.append(f"- {reason}")
        lines.append("")
    report_path.write_text("\n".join(lines), encoding="utf-8")


def config_from_args(args: argparse.Namespace) -> LocalLlmConfig:
    base_url = args.base_url
    if not base_url:
        base_url = DEFAULT_OLLAMA_URL if args.provider == "ollama" else DEFAULT_OPENAI_COMPATIBLE_URL
    return LocalLlmConfig(
        provider=args.provider,
        base_url=base_url,
        model=args.model,
        timeout_seconds=args.timeout_seconds,
    )


def main() -> None:
    args = parse_args()
    input_path = Path(args.input).resolve()
    output_path = Path(args.output).resolve()
    report_path = Path(args.report).resolve() if args.report else output_path.with_suffix(".md")
    config = config_from_args(args)
    contract = load_contract(input_path, args.max_candidates)
    allowed_ids = {
        str(candidate.get("property_id"))
        for candidate in contract.get("candidates", [])
        if isinstance(candidate, dict) and candidate.get("property_id")
    }
    if not allowed_ids:
        raise SystemExit("input contract did not contain any candidates")
    messages = build_messages(contract)
    model_text = call_local_model(config, messages)
    result = validate_proposals(model_text, allowed_ids)
    write_outputs(output_path, report_path, result, config=config, input_path=input_path)
    print(output_path)
    print(report_path)
    if not result.tests:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
