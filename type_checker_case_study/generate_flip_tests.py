"""Promote discriminating mutations into generated pytest suites.

Mirrors the repo's ``tools/generate_pytest_from_properties.py`` lane: select
validated cases, embed them as a literal in a generated test module, and let
pytest parametrize over them. Here the cases are the *discriminating mutations*
from the progressive composition loop -- single growth steps that flip the
validated outcome -- and the oracle under test is the ported type checker
itself.

Unlike the dataclass lane's loose ``_assert_observed`` oracle, every assertion
here is strict equality on the normalized outcome label (a principal-type shape
like ``(a -> a)`` or an error class like ``error:occurs-check``). That gives the
generated suite a strong oracle, which the repo README explicitly asks for.

The suites are regenerated deterministically from the same pipeline that writes
``out/flips.csv``; the CSV is the human-readable artifact, these are the
executable ones.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from .compose import Expr, MutationEdge, grow, size
from .groundtruth import Flip, build_ground_truth
from .oracle.syntax import App, EFalse, ETrue, If, Lam, Let, Lit, Var

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "generated_tests" / "type_checker_case_study"


@dataclass(frozen=True)
class ChainCase:
    """A multi-step path through the mutation graph with changing outcomes."""

    kind: str
    expressions: tuple[Expr, ...]
    outcomes: tuple[str, ...]


CHAIN_TEST_PATH = "test_generated_composition_chains.py"
BOUNDARY_TEST_PATH = "test_generated_composition_boundaries.py"


def to_source(expr: Expr) -> str:
    """Render an expression as the Python constructor call that rebuilds it."""
    if isinstance(expr, Var):
        return f"Var({expr.name!r})"
    if isinstance(expr, Lam):
        return f"Lam({expr.var!r}, {to_source(expr.body)})"
    if isinstance(expr, App):
        return f"App({to_source(expr.fun)}, {to_source(expr.arg)})"
    if isinstance(expr, If):
        return (
            f"If({to_source(expr.cond)}, {to_source(expr.then_branch)}, "
            f"{to_source(expr.else_branch)})"
        )
    if isinstance(expr, Let):
        return f"Let({expr.name!r}, {to_source(expr.bound)}, {to_source(expr.body)})"
    if isinstance(expr, Lit):
        return f"Lit({expr.value!r})"
    if isinstance(expr, ETrue):
        return "ETrue()"
    if isinstance(expr, EFalse):
        return "EFalse()"
    raise TypeError(f"Unknown expression node: {expr!r}")


def safe_id(*parts: str) -> str:
    import re

    text = "-".join(parts)
    text = re.sub(r"[^A-Za-z0-9_.-]+", "-", text).strip("-")
    return text or "case"


def select_flips(flips: list[Flip], per_kind: int) -> list[Flip]:
    """Deterministically sample up to ``per_kind`` flips of each kind.

    Sorted by total size then text so minimal, easiest-to-read probes win, and
    so the suite is stable across runs.
    """
    by_kind: dict[str, list[Flip]] = {}
    for flip in flips:
        by_kind.setdefault(flip.kind, []).append(flip)
    selected: list[Flip] = []
    for kind in sorted(by_kind):
        ranked = sorted(
            by_kind[kind],
            key=lambda f: (size(f.parent) + size(f.child), to_source(f.parent), to_source(f.child)),
        )
        selected.extend(ranked[:per_kind])
    return selected


def _edge_index(edges: list[MutationEdge]) -> dict[Expr, list[MutationEdge]]:
    by_parent: dict[Expr, list[MutationEdge]] = {}
    for edge in edges:
        by_parent.setdefault(edge.parent, []).append(edge)
    for children in by_parent.values():
        children.sort(
            key=lambda edge: (
                size(edge.parent) + size(edge.child),
                to_source(edge.parent),
                to_source(edge.child),
            )
        )
    return by_parent


def _chain_kind(outcomes: tuple[str, ...]) -> str:
    err_flags = tuple(label.startswith("error:") for label in outcomes)
    if all(not flag for flag in err_flags):
        return "type-ladder"
    if all(flag for flag in err_flags):
        return "error-ladder"
    if not err_flags[0] and err_flags[-1]:
        return "well->ill-chain"
    if err_flags[0] and not err_flags[-1]:
        return "ill->well-chain"
    return "mixed-chain"


def _is_redundant_chain(outcomes: tuple[str, ...]) -> bool:
    # Keep only paths that show a genuine progression rather than repeating
    # the same outcome label along the way.
    return len(set(outcomes)) != len(outcomes)


def select_chains(
    edges: list[MutationEdge],
    outcomes: dict[Expr, object],
    *,
    steps: int = 4,
    per_kind: int = 5,
) -> list[ChainCase]:
    """Select deterministic multi-hop paths with distinct outcomes.

    ``steps`` counts expressions, so the default picks four-level cases
    ``expr0 -> expr1 -> expr2 -> expr3``. We rank by total size and source text
    so minimal, readable chains win.
    """
    if steps < 2:
        raise ValueError("steps must be at least 2")

    by_parent = _edge_index(edges)
    chains: list[ChainCase] = []

    def visit(path: tuple[Expr, ...]) -> None:
        if len(path) == steps:
            labels = tuple(outcomes[expr].label for expr in path)
            if not _is_redundant_chain(labels):
                chains.append(ChainCase(_chain_kind(labels), path, labels))
            return
        parent = path[-1]
        for edge in by_parent.get(parent, []):
            child = edge.child
            if child in path:
                continue
            visit(path + (child,))

    roots = sorted(by_parent, key=lambda expr: (size(expr), to_source(expr)))
    for root in roots:
        visit((root,))

    by_kind: dict[str, list[ChainCase]] = {}
    for chain in chains:
        by_kind.setdefault(chain.kind, []).append(chain)

    selected: list[ChainCase] = []
    for kind in sorted(by_kind):
        ranked = sorted(
            by_kind[kind],
            key=lambda chain: (
                sum(size(expr) for expr in chain.expressions),
                tuple(to_source(expr) for expr in chain.expressions),
                chain.outcomes,
            ),
        )
        selected.extend(ranked[:per_kind])
    return selected


def render_cases(flips: list[Flip]) -> str:
    entries = []
    seen_ids: set[str] = set()
    for flip in flips:
        case_id = safe_id(flip.kind, to_source(flip.parent), to_source(flip.child))
        # keep ids unique even after sanitizing
        base = case_id
        n = 1
        while case_id in seen_ids:
            n += 1
            case_id = f"{base}-{n}"
        seen_ids.add(case_id)
        entries.append(
            "\n".join(
                [
                    "    {",
                    f"        'id': {case_id!r},",
                    f"        'kind': {flip.kind!r},",
                    f"        'parent': {to_source(flip.parent)},",
                    f"        'parent_outcome': {flip.parent_label!r},",
                    f"        'child': {to_source(flip.child)},",
                    f"        'child_outcome': {flip.child_label!r},",
                    "    }",
                ]
            )
        )
    return "[\n" + ",\n".join(entries) + "\n]"


def render_chain_cases(chains: list[ChainCase]) -> str:
    entries = []
    seen_ids: set[str] = set()
    for chain in chains:
        case_id = safe_id(
            chain.kind,
            *(to_source(expr) for expr in chain.expressions),
        )
        base = case_id
        n = 1
        while case_id in seen_ids:
            n += 1
            case_id = f"{base}-{n}"
        seen_ids.add(case_id)
        expr_list = ", ".join(to_source(expr) for expr in chain.expressions)
        label_list = ", ".join(repr(label) for label in chain.outcomes)
        entries.append(
            "\n".join(
                [
                    "    {",
                    f"        'id': {case_id!r},",
                    f"        'kind': {chain.kind!r},",
                    f"        'expressions': [{expr_list}],",
                    f"        'outcomes': [{label_list}],",
                    "    }",
                ]
            )
        )
    return "[\n" + ",\n".join(entries) + "\n]"


def render_test_file(flips: list[Flip]) -> str:
    return f'''"""
Generated by type_checker_case_study/generate_flip_tests.py.

Each case is a discriminating mutation discovered by the progressive composition
loop: a single growth step that flips the type checker's validated outcome.
These pin the boundaries between well-typed and ill-typed composites (and
between distinct principal types) as regression tests.

Run from the repo root:

    pytest generated_tests/type_checker_case_study/{BOUNDARY_TEST_PATH}
"""

from __future__ import annotations

import pytest

from type_checker_case_study.oracle.syntax import (
    App,
    EFalse,
    ETrue,
    If,
    Lam,
    Let,
    Lit,
    Var,
)
from type_checker_case_study.outcome import classify


CASES = {render_cases(flips)}


def _outcome_label(expr):
    return classify(expr).label


def _is_error(label):
    return label.startswith("error:")


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_composition_boundary(case):
    # The recorded validated outcomes must still hold exactly (strict oracle).
    assert _outcome_label(case["parent"]) == case["parent_outcome"]
    assert _outcome_label(case["child"]) == case["child_outcome"]

    # The mutation must genuinely change the outcome, in the recorded direction.
    assert case["parent_outcome"] != case["child_outcome"]
    parent_err = _is_error(case["parent_outcome"])
    child_err = _is_error(case["child_outcome"])
    if case["kind"] == "well->ill":
        assert not parent_err and child_err
    elif case["kind"] == "ill->well":
        assert parent_err and not child_err
    elif case["kind"] == "type-change":
        assert not parent_err and not child_err
    else:  # pragma: no cover - defensive
        pytest.fail(f"unknown flip kind: {{case['kind']!r}}")
'''


def render_chain_test_file(chains: list[ChainCase]) -> str:
    return f'''"""
Generated by type_checker_case_study/generate_flip_tests.py.

Each case is a multi-step composition chain discovered by the progressive
mutation graph. These preserve the intermediate validated outcomes, so the
tests can pin a deeper "do this, then one more time, then again" progression
rather than only a single boundary flip.

Run from the repo root:

    pytest generated_tests/type_checker_case_study/{CHAIN_TEST_PATH}
"""

from __future__ import annotations

import pytest

from type_checker_case_study.oracle.syntax import (
    App,
    EFalse,
    ETrue,
    If,
    Lam,
    Let,
    Lit,
    Var,
)
from type_checker_case_study.outcome import classify


CASES = {render_chain_cases(chains)}


def _outcome_label(expr):
    return classify(expr).label


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_composition_chain(case):
    expressions = case["expressions"]
    recorded = case["outcomes"]
    observed = [_outcome_label(expr) for expr in expressions]
    assert observed == recorded
    assert len(observed) >= 4
    assert len(set(observed)) == len(observed)
'''


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-size", type=int, default=9)
    parser.add_argument("--max-rounds", type=int, default=4)
    parser.add_argument("--cap-per-round", type=int, default=400)
    parser.add_argument(
        "--per-kind",
        type=int,
        default=25,
        help="Maximum cases to emit per flip kind (well->ill, ill->well, type-change).",
    )
    parser.add_argument(
        "--chain-steps",
        type=int,
        default=4,
        help="Expressions per generated chain case; 4 means expr0 -> expr1 -> expr2 -> expr3.",
    )
    parser.add_argument(
        "--chains-per-kind",
        type=int,
        default=5,
        help="Maximum generated chain cases to emit per chain kind.",
    )
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT))
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    composition = grow(
        max_size=args.max_size,
        max_rounds=args.max_rounds,
        cap_per_round=args.cap_per_round,
    )
    gt = build_ground_truth(composition)
    flips = select_flips(gt.flips, args.per_kind)
    chains = select_chains(
        composition.edges,
        gt.outcomes,
        steps=args.chain_steps,
        per_kind=args.chains_per_kind,
    )

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    boundary_path = out_dir / BOUNDARY_TEST_PATH
    boundary_path.write_text(render_test_file(flips), encoding="utf-8")
    chain_path = out_dir / CHAIN_TEST_PATH
    chain_path.write_text(render_chain_test_file(chains), encoding="utf-8")

    print(f"emitted {len(flips)} boundary cases -> {boundary_path}")
    print(f"emitted {len(chains)} chain cases -> {chain_path}")


if __name__ == "__main__":
    main()
