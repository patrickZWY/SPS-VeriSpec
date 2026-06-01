"""Run the Datalog policy and measure it against the oracle's ground truth.

This closes the informal-to-formal loop for the case study: the Souffle policy
in ``policy/expr_policy.dl`` predicts outcomes structurally; the oracle validates
what actually holds. We report three things:

  * soundness   -- when the policy predicts an error class, does the oracle agree?
  * coverage    -- of the oracle's ill-typed expressions, what fraction does the
                   policy decide structurally?
  * residual    -- the ill-typed expressions only the oracle/tests can catch
                   (occurs-check that is not lambda self-application,
                   heterogeneous-if, application-mismatch). This residual is the
                   argument for progressive, test-based validation over a purely
                   conservative static policy.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .compose import grow
from .facts import write_facts
from .groundtruth import build_ground_truth
from .oracle.syntax import Expr, pretty
from .outcome import Outcome

ROOT = Path(__file__).resolve().parent
POLICY_MODEL = ROOT / "policy" / "expr_policy.dl"
OUT_DIR = ROOT / "out"


@dataclass
class PolicyEval:
    predictions: dict[int, str]          # expr_id -> predicted error class
    outcomes: dict[Expr, Outcome]
    expressions: list[Expr]
    # predicted ill-typed but oracle says well-typed: the dangerous unsoundness.
    false_positives: list[tuple[Expr, str, str]]
    # predicted ill-typed AND oracle agrees it is ill-typed, but a different
    # error fires first under composition (e.g. an if-condition constrains a
    # variable before its self-application is reached). Sound for the
    # well-typed/ill-typed decision; imprecise only about which error wins.
    reclassified: list[tuple[Expr, str, str]]


def run_souffle(facts_dir: Path, out_dir: Path) -> dict[int, str]:
    if shutil.which("souffle") is None:
        raise SystemExit("souffle is not installed or not on PATH.")
    out_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["souffle", "-F", str(facts_dir), "-D", str(out_dir), str(POLICY_MODEL)],
        check=True,
        cwd=ROOT.parent,
    )
    predicted_path = out_dir / "predicted_ill.csv"
    predictions: dict[int, str] = {}
    with predicted_path.open(encoding="utf-8", newline="") as handle:
        for row in csv.reader(handle, delimiter="\t"):
            if not row:
                continue
            eid, error_class = int(row[0]), row[1]
            # unbound-variable wins over occurs-check (model already orders, but
            # keep deterministic if both rows appear).
            if eid not in predictions or error_class == "unbound-variable":
                predictions[eid] = error_class
    return predictions


def evaluate(
    *,
    max_size: int = 9,
    max_rounds: int = 4,
    cap_per_round: int = 400,
    work_dir: Path | None = None,
) -> PolicyEval:
    composition = grow(
        max_size=max_size, max_rounds=max_rounds, cap_per_round=cap_per_round
    )
    gt = build_ground_truth(composition)
    expressions = composition.expressions

    work = work_dir or (OUT_DIR / "policy_work")
    facts_dir = work / "facts"
    souffle_out = work / "souffle_out"
    write_facts(expressions, facts_dir)
    predictions = run_souffle(facts_dir, souffle_out)

    false_positives: list[tuple[Expr, str, str]] = []
    reclassified: list[tuple[Expr, str, str]] = []
    for eid, predicted in predictions.items():
        expr = expressions[eid]
        outcome = gt.outcomes[expr]
        if outcome.well_typed:
            false_positives.append((expr, predicted, outcome.label))
        elif outcome.error_class != predicted:
            reclassified.append((expr, predicted, outcome.label))

    return PolicyEval(
        predictions=predictions,
        outcomes=gt.outcomes,
        expressions=expressions,
        false_positives=false_positives,
        reclassified=reclassified,
    )


def render_report(ev: PolicyEval) -> str:
    n = len(ev.expressions)
    ill = {
        e: o for e, o in ev.outcomes.items() if not o.well_typed
    }
    oracle_ill_by_class = Counter(o.error_class for o in ill.values())

    decided = len(ev.predictions)

    # Exact-class agreement: of each oracle error class, how many did the policy
    # decide with the same class label?
    eid_of = {id(e): i for i, e in enumerate(ev.expressions)}
    exact_by_class: Counter[str] = Counter()
    for e, o in ill.items():
        eid = eid_of[id(e)]
        if ev.predictions.get(eid) == o.error_class:
            exact_by_class[o.error_class] += 1

    lines: list[str] = []
    lines.append("# Datalog policy vs. oracle ground truth")
    lines.append("")
    lines.append(
        "The structural policy predicts only what follows soundly from the "
        "elementary forms and their binding. Everything else is left to the "
        "oracle. This report quantifies the gap -- the residual that justifies "
        "progressive, test-based validation."
    )
    lines.append("")
    lines.append("## Soundness of the ill-typed decision")
    lines.append("")
    lines.append(f"- Expressions the policy decided: {decided} / {n}")
    lines.append(
        f"- False positives (policy said ill-typed, oracle says well-typed): "
        f"{len(ev.false_positives)}"
    )
    if ev.false_positives:
        lines.append("")
        lines.append("  These are real soundness violations to investigate:")
        for expr, predicted, actual in ev.false_positives[:20]:
            lines.append(
                f"  - `{pretty(expr)}` predicted `{predicted}` but oracle says `{actual}`"
            )
    else:
        lines.append(
            "- Zero false positives: every expression the policy flags is genuinely "
            "ill-typed. The structural policy is sound for the well-typed/ill-typed "
            "decision on this set."
        )
    lines.append("")
    lines.append("## Error-class precision under composition")
    lines.append("")
    lines.append(
        f"- Reclassified (ill-typed both ways, but a different error fires first): "
        f"{len(ev.reclassified)}"
    )
    lines.append(
        "  Finding: lambda self-application is a sound predictor of *failure*, but "
        "not of *which* failure. When the same variable is also constrained "
        "elsewhere -- e.g. used as an `if` condition -- that constraint fires "
        "first and the checker reports `application-mismatch`/`non-bool-condition` "
        "instead of `occurs-check`. The error class is a property of the whole "
        "composition, not of the self-application alone."
    )
    if ev.reclassified:
        lines.append("")
        for expr, predicted, actual in ev.reclassified[:12]:
            lines.append(
                f"  - `{pretty(expr)}` predicted `{predicted}`, oracle `{actual}`"
            )
    lines.append("")
    lines.append("## Coverage of ill-typed expressions")
    lines.append("")
    lines.append(f"- Oracle ill-typed total: {len(ill)}")
    for cls, total in oracle_ill_by_class.most_common():
        caught = exact_by_class.get(cls, 0)
        lines.append(
            f"- `{cls}`: policy decided exactly {caught} / {total} ({_pct(caught, total)})"
        )
    lines.append("")
    lines.append("## Residual (only the oracle/tests can decide)")
    lines.append("")
    lines.append(
        "Ill-typed expressions the structural policy does not claim. These are "
        "the cases where composition outcome genuinely depends on unification, "
        "let-generalization, or branch agreement -- not on syntax alone."
    )
    lines.append("")
    decided_eids = set(ev.predictions)
    residual = Counter(
        o.error_class
        for e, o in ill.items()
        if eid_of[id(e)] not in decided_eids
    )
    for cls, count in residual.most_common():
        lines.append(f"- `{cls}`: {count}")
    lines.append("")
    return "\n".join(lines)


def _pct(num: int, denom: int) -> str:
    return f"{(100.0 * num / denom):.1f}%" if denom else "0.0%"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-size", type=int, default=9)
    parser.add_argument("--max-rounds", type=int, default=4)
    parser.add_argument("--cap-per-round", type=int, default=400)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    ev = evaluate(
        max_size=args.max_size,
        max_rounds=args.max_rounds,
        cap_per_round=args.cap_per_round,
    )
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "policy_report.md"
    report_path.write_text(render_report(ev), encoding="utf-8")
    print(
        f"decided={len(ev.predictions)} "
        f"false_positives={len(ev.false_positives)} "
        f"reclassified={len(ev.reclassified)} "
        f"report={report_path}"
    )


if __name__ == "__main__":
    main()
