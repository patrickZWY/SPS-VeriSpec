"""Run metamorphic relations over the composition corpus and report violations.

For every source expression from ``compose.grow`` we apply each Phase-1 MR and
check the relation. On a faithful oracle we expect **zero** violations -- and
zero is itself a meaningful independent cross-check between the Python port and
the relations, over thousands of expressions the relations were not tuned to.
Any violation is either a checker bug or an MR bug and is surfaced for review.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .compose import grow
from .metamorphic import MR_GENERATORS, MRInstance, instances_for, relation_holds
from .oracle.syntax import Expr, pretty
from .outcome import Outcome, classify

OUT_DIR = Path(__file__).resolve().parent / "out"


@dataclass
class Violation:
    instance: MRInstance
    src: Outcome
    dst: Outcome


@dataclass
class MetamorphicResult:
    applications: Counter  # mr -> count
    violations: list[Violation]
    sources: int


def evaluate(
    *, max_size: int = 9, max_rounds: int = 4, cap_per_round: int = 400
) -> MetamorphicResult:
    composition = grow(
        max_size=max_size, max_rounds=max_rounds, cap_per_round=cap_per_round
    )
    # Cache source outcomes; transformed expressions are classified on demand.
    cache: dict[Expr, Outcome] = {}

    def cached(expr: Expr) -> Outcome:
        outcome = cache.get(expr)
        if outcome is None:
            outcome = classify(expr)
            cache[expr] = outcome
        return outcome

    applications: Counter = Counter()
    violations: list[Violation] = []

    for source in composition.expressions:
        src_outcome = cached(source)
        for inst in instances_for(source, src_outcome):
            applications[inst.mr] += 1
            # The relation is between the instance's own two expressions; most
            # MRs use the corpus source as inst.source, but some (e.g. MR-LETLAM)
            # do not, so classify inst.source rather than reusing src_outcome.
            inst_src_outcome = cached(inst.source)
            dst_outcome = cached(inst.transformed)
            if not relation_holds(inst.relation, inst_src_outcome, dst_outcome):
                violations.append(Violation(inst, inst_src_outcome, dst_outcome))

    return MetamorphicResult(
        applications=applications,
        violations=violations,
        sources=len(composition.expressions),
    )


def render_report(result: MetamorphicResult) -> str:
    total = sum(result.applications.values())
    lines = [
        "# Metamorphic oracle report (Phase 1)",
        "",
        "Each source expression from the composition corpus is transformed by "
        "every applicable metamorphic relation, and the relation is checked "
        "against the oracle. Violations are documented findings (real checker "
        "bugs); see METAMORPHIC_FINDINGS.md. MR-CLASH is a pure soundness check "
        "and is expected to stay at zero.",
        "",
        "## Coverage",
        "",
        f"- Source expressions: {result.sources}",
        f"- Total MR applications: {total}",
        f"- Violations: {len(result.violations)}",
        "",
        "### Applications per relation",
        "",
    ]
    for mr in sorted(MR_GENERATORS):
        lines.append(f"- `{mr}`: {result.applications.get(mr, 0)}")
    lines.append("")
    lines.append("## Violations")
    lines.append("")
    if not result.violations:
        lines.append(
            "None. Every metamorphic relation held across the corpus -- the "
            "relations and the oracle agree."
        )
    else:
        lines.append(
            "Each row is a checker bug or an MR bug; treat as a review record, "
            "not a trusted-suite failure."
        )
        lines.append("")
        by_mr = Counter(v.instance.mr for v in result.violations)
        for mr, count in by_mr.most_common():
            lines.append(f"- `{mr}`: {count}")
        lines.append("")
        for v in result.violations[:25]:
            lines.append(
                f"- **{v.instance.mr}** (`{v.instance.relation}`)"
            )
            lines.append(f"  - source `{pretty(v.instance.source)}` : `{v.src.label}`")
            lines.append(
                f"  - transformed `{pretty(v.instance.transformed)}` : `{v.dst.label}`"
            )
    lines.append("")
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-size", type=int, default=9)
    parser.add_argument("--max-rounds", type=int, default=4)
    parser.add_argument("--cap-per-round", type=int, default=400)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    result = evaluate(
        max_size=args.max_size,
        max_rounds=args.max_rounds,
        cap_per_round=args.cap_per_round,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "metamorphic_report.md"
    report_path.write_text(render_report(result), encoding="utf-8")
    print(
        f"sources={result.sources} "
        f"applications={sum(result.applications.values())} "
        f"violations={len(result.violations)} report={report_path}"
    )


if __name__ == "__main__":
    main()
