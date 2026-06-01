"""Progressive, scope-aware composition of elementary expression forms.

This is the engine behind the milestone idea: rather than trying to *prove*
statically what composite expressions are well-typed (conservative), we
optimistically *grow* expressions one subcomponent at a time -- "the let
expression within an expression within an if" -- and let the oracle tell us
what actually holds (progressive). Each growth step replaces a single
subcomponent with a strictly larger, well-scoped sub-expression built from the
elementary forms, so every candidate stays closed and runnable.

The search is a breadth-first walk over a *mutation graph* rooted at seeds.
Edges record exactly which subcomponent was grown, so the summary can surface
the boundary cases -- a one-step mutation that flips a well-typed expression
into an ill-typed one (or changes its principal type). Those flips are the
combinator-style bug probes the README is after.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Iterator, Optional

from .oracle.syntax import (
    App,
    EFalse,
    ETrue,
    Expr,
    If,
    Lam,
    Let,
    Lit,
    Var,
    expr_tag,
    pretty,
)

# Canonical, small variable pool. Keeping the alphabet fixed makes the search
# finite and the generated expressions comparable across runs.
_FRESH_VARS = ("x", "y", "z", "f", "g")


# --------------------------------------------------------------------------
# Structural helpers
# --------------------------------------------------------------------------
def size(expr: Expr) -> int:
    """Node count, used as the progressive-deepening budget."""
    if isinstance(expr, (Var, Lit, ETrue, EFalse)):
        return 1
    if isinstance(expr, Lam):
        return 1 + size(expr.body)
    if isinstance(expr, App):
        return 1 + size(expr.fun) + size(expr.arg)
    if isinstance(expr, If):
        return 1 + size(expr.cond) + size(expr.then_branch) + size(expr.else_branch)
    if isinstance(expr, Let):
        return 1 + size(expr.bound) + size(expr.body)
    raise TypeError(f"Unknown expression node: {expr!r}")


def free_vars(expr: Expr) -> frozenset[str]:
    if isinstance(expr, Var):
        return frozenset((expr.name,))
    if isinstance(expr, (Lit, ETrue, EFalse)):
        return frozenset()
    if isinstance(expr, Lam):
        return free_vars(expr.body) - {expr.var}
    if isinstance(expr, App):
        return free_vars(expr.fun) | free_vars(expr.arg)
    if isinstance(expr, If):
        return free_vars(expr.cond) | free_vars(expr.then_branch) | free_vars(
            expr.else_branch
        )
    if isinstance(expr, Let):
        # `name` is in scope only within the body, not the bound expression.
        return free_vars(expr.bound) | (free_vars(expr.body) - {expr.name})
    raise TypeError(f"Unknown expression node: {expr!r}")


def is_closed(expr: Expr) -> bool:
    return not free_vars(expr)


# A position is a path of (slot) strings from the root to a subterm.
Path = tuple[str, ...]


@dataclass(frozen=True)
class Position:
    path: Path
    subexpr: Expr
    scope: frozenset[str]  # variables bound at this subterm


def positions(expr: Expr, scope: frozenset[str] = frozenset()) -> Iterator[Position]:
    """Every subterm with the set of variables in scope there."""
    yield Position((), expr, scope)
    if isinstance(expr, Lam):
        inner = scope | {expr.var}
        for pos in positions(expr.body, inner):
            yield Position(("body",) + pos.path, pos.subexpr, pos.scope)
    elif isinstance(expr, App):
        for pos in positions(expr.fun, scope):
            yield Position(("fun",) + pos.path, pos.subexpr, pos.scope)
        for pos in positions(expr.arg, scope):
            yield Position(("arg",) + pos.path, pos.subexpr, pos.scope)
    elif isinstance(expr, If):
        for slot, child in (
            ("cond", expr.cond),
            ("then", expr.then_branch),
            ("else", expr.else_branch),
        ):
            for pos in positions(child, scope):
                yield Position((slot,) + pos.path, pos.subexpr, pos.scope)
    elif isinstance(expr, Let):
        for pos in positions(expr.bound, scope):  # name not in scope here
            yield Position(("bound",) + pos.path, pos.subexpr, pos.scope)
        inner = scope | {expr.name}
        for pos in positions(expr.body, inner):
            yield Position(("body",) + pos.path, pos.subexpr, pos.scope)
    # leaves (Var, Lit, ETrue, EFalse) have no children


def replace_at(expr: Expr, path: Path, new_sub: Expr) -> Expr:
    """Return ``expr`` with the subterm at ``path`` replaced by ``new_sub``."""
    if not path:
        return new_sub
    head, rest = path[0], path[1:]
    if isinstance(expr, Lam) and head == "body":
        return Lam(expr.var, replace_at(expr.body, rest, new_sub))
    if isinstance(expr, App) and head == "fun":
        return App(replace_at(expr.fun, rest, new_sub), expr.arg)
    if isinstance(expr, App) and head == "arg":
        return App(expr.fun, replace_at(expr.arg, rest, new_sub))
    if isinstance(expr, If) and head == "cond":
        return If(replace_at(expr.cond, rest, new_sub), expr.then_branch, expr.else_branch)
    if isinstance(expr, If) and head == "then":
        return If(expr.cond, replace_at(expr.then_branch, rest, new_sub), expr.else_branch)
    if isinstance(expr, If) and head == "else":
        return If(expr.cond, expr.then_branch, replace_at(expr.else_branch, rest, new_sub))
    if isinstance(expr, Let) and head == "bound":
        return Let(expr.name, replace_at(expr.bound, rest, new_sub), expr.body)
    if isinstance(expr, Let) and head == "body":
        return Let(expr.name, expr.bound, replace_at(expr.body, rest, new_sub))
    raise ValueError(f"Bad path {path!r} for node {expr_tag(expr)}")


# --------------------------------------------------------------------------
# Local replacement candidates
# --------------------------------------------------------------------------
def _fresh_var(scope: frozenset[str]) -> str:
    for name in _FRESH_VARS:
        if name not in scope:
            return name
    # Fall back to a numbered variable if the small pool is exhausted.
    i = 0
    while f"v{i}" in scope:
        i += 1
    return f"v{i}"


def local_candidates(scope: frozenset[str]) -> list[Expr]:
    """Small, well-scoped sub-expressions to graft in at a position.

    These are the "more complicated" replacements that drive progressive
    deepening. Each only references variables in ``scope`` so grafting it keeps
    the whole expression closed. The set is intentionally small and built from
    the elementary forms; depth comes from repeated grafting, not from large
    one-shot templates.
    """
    in_scope = sorted(scope)
    cands: list[Expr] = [ETrue(), EFalse(), Lit(0)]
    cands.extend(Var(v) for v in in_scope)
    # one-step compositions over in-scope material
    for v in in_scope:
        for w in in_scope:
            cands.append(App(Var(v), Var(w)))  # application (drives occurs-check)
    for v in in_scope:
        cands.append(If(Var(v), ETrue(), EFalse()))  # use v at Bool
        cands.append(App(Var(v), ETrue()))           # use v as a function
    # a fresh lambda (introduces a new binder -> richer composites)
    fresh = _fresh_var(scope)
    cands.append(Lam(fresh, Var(fresh)))
    cands.append(Lam(fresh, ETrue()))
    return cands


def mutate(expr: Expr, max_size: int) -> Iterator[Expr]:
    """Yield closed expressions that grow one subcomponent of ``expr``.

    For every subterm position we try each well-scoped replacement that is
    *strictly larger* than what was there (so the candidate is "more
    complicated") and keeps the whole expression within ``max_size``. We also
    wrap the whole expression in each elementary binder/context, which is how
    a `let` ends up "within an expression within an if".
    """
    seen: set[Expr] = set()

    def emit(candidate: Expr) -> Iterator[Expr]:
        if (
            candidate not in seen
            and is_closed(candidate)
            and size(candidate) <= max_size
            and candidate != expr
        ):
            seen.add(candidate)
            yield candidate

    # 1. Grow a subcomponent in place.
    for pos in positions(expr):
        old_size = size(pos.subexpr)
        for repl in local_candidates(pos.scope):
            if size(repl) <= old_size:
                continue  # must be strictly more complicated
            yield from emit(replace_at(expr, pos.path, repl))

    # 2. Wrap the whole expression in an elementary context.
    fresh = _fresh_var(free_vars(expr))
    yield from emit(Lam(fresh, expr))
    yield from emit(If(ETrue(), expr, expr))
    yield from emit(Let(fresh, expr, ETrue()))
    yield from emit(App(Lam(fresh, Var(fresh)), expr))


# --------------------------------------------------------------------------
# The progressive loop
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class MutationEdge:
    """A single growth step parent -> child in the mutation graph."""

    parent: Expr
    child: Expr
    round_: int


def default_seeds() -> list[Expr]:
    """Minimal closed seeds: the leaves and the identity combinator.

    Everything else in the catalog is reached by progressive mutation of these.
    """
    return [
        ETrue(),
        EFalse(),
        Lit(0),
        Lam("x", Var("x")),
    ]


@dataclass
class CompositionResult:
    expressions: list[Expr]
    edges: list[MutationEdge]
    rounds: int
    max_size: int


def grow(
    seeds: Optional[Iterable[Expr]] = None,
    *,
    max_size: int = 9,
    max_rounds: int = 4,
    cap_per_round: int = 400,
) -> CompositionResult:
    """Breadth-first progressive composition rooted at ``seeds``.

    Returns every distinct closed expression discovered within the size budget,
    plus the mutation edges that produced them. The caller validates outcomes
    via :mod:`outcome`; this function is pure structure generation so it can be
    tested independently of the oracle.
    """
    seed_list = list(seeds) if seeds is not None else default_seeds()
    discovered: list[Expr] = []
    known: set[Expr] = set()
    edges: list[MutationEdge] = []

    frontier: list[Expr] = []
    for s in seed_list:
        if s not in known and is_closed(s) and size(s) <= max_size:
            known.add(s)
            discovered.append(s)
            frontier.append(s)

    for round_ in range(1, max_rounds + 1):
        next_frontier: list[Expr] = []
        for parent in frontier:
            for child in mutate(parent, max_size):
                if child in known:
                    continue
                known.add(child)
                discovered.append(child)
                edges.append(MutationEdge(parent, child, round_))
                next_frontier.append(child)
        # Deterministic, bounded frontier: prefer smaller expressions so the
        # search broadens before it deepens.
        next_frontier.sort(key=lambda e: (size(e), pretty(e)))
        frontier = next_frontier[:cap_per_round]
        if not frontier:
            break

    return CompositionResult(
        expressions=discovered,
        edges=edges,
        rounds=round_,
        max_size=max_size,
    )
