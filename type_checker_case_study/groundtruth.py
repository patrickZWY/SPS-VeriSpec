"""Validate the progressively composed expressions and summarize ground truth.

This ties the engine to the oracle: grow composites, classify each with the
oracle, and report *what holds for the program*. The summary highlights
discriminating mutations -- single growth steps that flip a well-typed
expression into an ill-typed one or change its principal type -- because those
boundaries are exactly the combinator-style probes that expose type-checker
behavior (and bugs).
"""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .compose import CompositionResult, MutationEdge, grow, size
from .oracle.syntax import Expr, pretty
from .outcome import Outcome, classify

OUT_DIR = Path(__file__).resolve().parent / "out"


@dataclass(frozen=True)
class Flip:
    """A mutation that changed the validated outcome."""

    parent: Expr
    child: Expr
    parent_label: str
    child_label: str
    kind: str  # "well->ill", "ill->well", "type-change"


@dataclass
class GroundTruth:
    outcomes: dict[Expr, Outcome]
    flips: list[Flip]
    composition: CompositionResult

    @property
    def well_typed(self) -> list[Expr]:
        return [e for e, o in self.outcomes.items() if o.well_typed]

    @property
    def ill_typed(self) -> list[Expr]:
        return [e for e, o in self.outcomes.items() if not o.well_typed]


def _flip_kind(parent: Outcome, child: Outcome) -> str | None:
    if parent.well_typed and not child.well_typed:
        return "well->ill"
    if not parent.well_typed and child.well_typed:
        return "ill->well"
    if parent.well_typed and child.well_typed and parent.type_shape != child.type_shape:
        return "type-change"
    return None


def build_ground_truth(composition: CompositionResult) -> GroundTruth:
    outcomes: dict[Expr, Outcome] = {
        expr: classify(expr) for expr in composition.expressions
    }
    flips: list[Flip] = []
    for edge in composition.edges:
        po, co = outcomes[edge.parent], outcomes[edge.child]
        kind = _flip_kind(po, co)
        if kind is not None:
            flips.append(
                Flip(edge.parent, edge.child, po.label, co.label, kind)
            )
    return GroundTruth(outcomes=outcomes, flips=flips, composition=composition)


def render_report(gt: GroundTruth) -> str:
    comp = gt.composition
    n = len(gt.outcomes)
    well = gt.well_typed
    ill = gt.ill_typed

    type_shapes = Counter(
        gt.outcomes[e].label for e in well
    )
    error_classes = Counter(
        gt.outcomes[e].label for e in ill
    )
    flip_kinds = Counter(f.kind for f in gt.flips)

    lines: list[str] = []
    lines.append("# Type-checker case study: validated ground truth")
    lines.append("")
    lines.append(
        "Progressive composition of the eight elementary expression forms, each "
        "composite validated against the ported Algorithm W oracle. This is the "
        "set of facts that *hold for the program* within the search budget -- not "
        "a conservative over-approximation."
    )
    lines.append("")
    lines.append("## Search budget")
    lines.append("")
    lines.append(f"- Mutation rounds: {comp.rounds}")
    lines.append(f"- Max expression size (nodes): {comp.max_size}")
    lines.append(f"- Distinct closed expressions discovered: {n}")
    lines.append(f"- Mutation edges explored: {len(comp.edges)}")
    lines.append("")
    lines.append("## What holds")
    lines.append("")
    lines.append(f"- Well-typed: {len(well)} ({_pct(len(well), n)})")
    lines.append(f"- Ill-typed: {len(ill)} ({_pct(len(ill), n)})")
    lines.append("")
    lines.append("### Principal-type shapes (well-typed)")
    lines.append("")
    for shape, count in type_shapes.most_common():
        lines.append(f"- `{shape}`: {count}")
    lines.append("")
    lines.append("### Error classes (ill-typed)")
    lines.append("")
    for cls, count in error_classes.most_common():
        lines.append(f"- `{cls}`: {count}")
    lines.append("")
    lines.append("## Discriminating mutations (boundary findings)")
    lines.append("")
    lines.append(
        "Each row is a single growth step where adding one subcomponent flipped "
        "the validated outcome. These are the combinator-style probes: minimal "
        "structural deltas that change what the type checker decides."
    )
    lines.append("")
    for kind, count in flip_kinds.most_common():
        lines.append(f"- {kind}: {count}")
    lines.append("")
    lines.append("### Sample boundary cases")
    lines.append("")
    for flip in _sample_flips(gt.flips):
        lines.append(f"- **{flip.kind}**")
        lines.append(f"  - parent `{pretty(flip.parent)}` : `{flip.parent_label}`")
        lines.append(f"  - child  `{pretty(flip.child)}` : `{flip.child_label}`")
    lines.append("")
    return "\n".join(lines)


def _sample_flips(flips: list[Flip], per_kind: int = 4) -> list[Flip]:
    by_kind: dict[str, list[Flip]] = {}
    for f in flips:
        by_kind.setdefault(f.kind, [])
        if len(by_kind[f.kind]) < per_kind:
            by_kind[f.kind].append(f)
    out: list[Flip] = []
    for kind in sorted(by_kind):
        out.extend(by_kind[kind])
    return out


def _pct(num: int, denom: int) -> str:
    return f"{(100.0 * num / denom):.1f}%" if denom else "0.0%"


def write_outputs(gt: GroundTruth, out_dir: Path = OUT_DIR) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "ground_truth.md"
    catalog_path = out_dir / "catalog.csv"
    flips_path = out_dir / "flips.csv"

    report_path.write_text(render_report(gt), encoding="utf-8")

    with catalog_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["expression", "size", "well_typed", "outcome"])
        for expr in sorted(gt.outcomes, key=lambda e: (size(e), pretty(e))):
            o = gt.outcomes[expr]
            writer.writerow([pretty(expr), size(expr), int(o.well_typed), o.label])

    with flips_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["kind", "parent", "parent_outcome", "child", "child_outcome"])
        for f in gt.flips:
            writer.writerow(
                [f.kind, pretty(f.parent), f.parent_label, pretty(f.child), f.child_label]
            )

    return {"report": report_path, "catalog": catalog_path, "flips": flips_path}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-size", type=int, default=9)
    parser.add_argument("--max-rounds", type=int, default=4)
    parser.add_argument("--cap-per-round", type=int, default=400)
    parser.add_argument("--out-dir", default=str(OUT_DIR))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    composition = grow(
        max_size=args.max_size,
        max_rounds=args.max_rounds,
        cap_per_round=args.cap_per_round,
    )
    gt = build_ground_truth(composition)
    paths = write_outputs(gt, Path(args.out_dir))
    print(f"discovered={len(gt.outcomes)} "
          f"well={len(gt.well_typed)} ill={len(gt.ill_typed)} "
          f"flips={len(gt.flips)}")
    for label, path in paths.items():
        print(f"{label}: {path}")


if __name__ == "__main__":
    main()
