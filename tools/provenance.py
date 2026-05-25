from __future__ import annotations

import csv
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal


Provenance = Literal["static", "llm", "mixed"]


@dataclass(frozen=True)
class ProvenanceFinding:
    relation: str
    provenance: Provenance
    row: tuple[str, ...]


def combine_provenance(provenances: Iterable[str]) -> Provenance:
    values = {value for value in provenances if value}
    if not values:
        return "static"
    if values == {"static"}:
        return "static"
    if values == {"llm"}:
        return "llm"
    return "mixed"


def read_csv_rows(path: Path) -> set[tuple[str, ...]]:
    if not path.exists():
        return set()
    with path.open(encoding="utf-8", newline="") as handle:
        return {tuple(row) for row in csv.reader(handle, delimiter="\t") if row}


def read_relation_dir(path: Path) -> dict[str, set[tuple[str, ...]]]:
    rows: dict[str, set[tuple[str, ...]]] = {}
    if not path.exists():
        return rows
    for csv_path in sorted(path.glob("*.csv")):
        rows[csv_path.stem] = read_csv_rows(csv_path)
    return rows


def classify_relation_rows(
    static_rows: dict[str, set[tuple[str, ...]]],
    llm_rows: dict[str, set[tuple[str, ...]]],
) -> list[ProvenanceFinding]:
    findings: list[ProvenanceFinding] = []
    for relation in sorted(set(static_rows) | set(llm_rows)):
        static_relation_rows = static_rows.get(relation, set())
        llm_relation_rows = llm_rows.get(relation, set())
        for row in sorted(static_relation_rows | llm_relation_rows):
            provenance = combine_provenance(
                [
                    "static" if row in static_relation_rows else "",
                    "llm" if row in llm_relation_rows else "",
                ]
            )
            findings.append(ProvenanceFinding(relation, provenance, row))
    return findings


def merge_relation_dirs(
    output_dir: Path,
    static_dir: Path | None = None,
    llm_dir: Path | None = None,
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    relations = set()
    if static_dir and static_dir.exists():
        relations.update(path.stem for path in static_dir.glob("*.csv"))
    if llm_dir and llm_dir.exists():
        relations.update(path.stem for path in llm_dir.glob("*.csv"))

    for relation in sorted(relations):
        rows: set[tuple[str, ...]] = set()
        if static_dir:
            rows.update(read_csv_rows(static_dir / f"{relation}.csv"))
        if llm_dir:
            rows.update(read_csv_rows(llm_dir / f"{relation}.csv"))
        with (output_dir / f"{relation}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle, delimiter="\t")
            writer.writerows(sorted(rows))


def write_finding_provenance(
    output_path: Path,
    findings: Iterable[ProvenanceFinding],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["relation", "provenance", "row_json"])
        for finding in findings:
            writer.writerow(
                [
                    finding.relation,
                    finding.provenance,
                    json.dumps(list(finding.row), sort_keys=True),
                ]
            )


def write_provenance_report(path: Path, findings: Iterable[ProvenanceFinding]) -> None:
    findings = list(findings)
    counts: Counter[tuple[str, str]] = Counter(
        (finding.relation, finding.provenance) for finding in findings
    )
    examples: dict[tuple[str, str], list[ProvenanceFinding]] = defaultdict(list)
    for finding in findings:
        key = (finding.relation, finding.provenance)
        if len(examples[key]) < 3:
            examples[key].append(finding)

    lines = [
        "# Rule Provenance Report",
        "",
        "Findings are tainted as `static`, `llm`, or `mixed` based on whether",
        "the output row was produced by the trusted static rules, the optional",
        "LLM-assisted rule layer, or both.",
        "",
        "## Counts",
        "",
    ]
    if counts:
        for (relation, provenance), count in sorted(counts.items()):
            lines.append(f"- `{relation}` `{provenance}`: {count}")
    else:
        lines.append("- No findings were emitted.")

    lines.extend(["", "## Examples", ""])
    for key in sorted(examples):
        relation, provenance = key
        lines.append(f"### {relation} / {provenance}")
        lines.append("")
        for finding in examples[key]:
            lines.append(f"- `{' | '.join(finding.row)}`")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")


def write_provenance_outputs(
    work_dir: Path,
    relation_dirs: dict[str, tuple[Path | None, Path | None]],
) -> list[ProvenanceFinding]:
    all_findings: list[ProvenanceFinding] = []
    for model_name, (static_dir, llm_dir) in relation_dirs.items():
        static_rows = read_relation_dir(static_dir) if static_dir else {}
        llm_rows = read_relation_dir(llm_dir) if llm_dir else {}
        for finding in classify_relation_rows(static_rows, llm_rows):
            all_findings.append(
                ProvenanceFinding(
                    relation=f"{model_name}.{finding.relation}",
                    provenance=finding.provenance,
                    row=finding.row,
                )
            )

    provenance_dir = work_dir / "provenance_out"
    write_finding_provenance(provenance_dir / "finding_provenance.csv", all_findings)
    write_provenance_report(provenance_dir / "provenance_report.md", all_findings)
    return all_findings
