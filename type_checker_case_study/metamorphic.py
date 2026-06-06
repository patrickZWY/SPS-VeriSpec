"""Metamorphic relations for the type-checker case study (Phase 1).

A metamorphic relation (MR) pairs a transform ``T`` with a relation ``R`` such
that ``R(classify(e), classify(T(e)))`` must hold for any correct checker --
*without* a reference answer for either expression. That breaks the circularity
of the label-based boundary suite: an MR violation indicts the checker even
though the checker produced the corpus.

Phase 1 ships the relations that are sound with no new inference machinery:

  * MR-LIT     -- interchange Int/Bool literals               -> equal outcome
  * MR-ALPHA   -- rename a bound variable to a fresh name      -> equal outcome
  * MR-DEADLET -- wrap in an unused, well-typed let binding    -> equal outcome
  * MR-LAM     -- wrap in a lambda over a fresh unused param   -> `fresh -> T`
  * MR-ERRPROP -- embed a closed ill-typed term in a context   -> error stays

(MR-DET, determinism, is already covered by the engine determinism test, since
``classify`` is a pure function; it is not re-emitted as corpus cases.)

All transforms keep expressions closed and use globally fresh names, so capture
is impossible. Type comparisons go through ``normalize_ty``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator

from .compose import positions, replace_at
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
)
from .oracle.types import TFun, TVar, normalize_ty
from .outcome import Outcome, classify

# MR identifiers.
MR_LIT = "MR-LIT"
MR_ALPHA = "MR-ALPHA"
MR_DEADLET = "MR-DEADLET"
MR_LAM = "MR-LAM"
MR_ERRPROP = "MR-ERRPROP"

# Relation kinds (used by both the evaluator and the generated tests).
REL_EQUAL = "equal_outcome"
REL_PROPAGATES_ERROR = "propagates_error"
REL_LAMBDA_WRAP = "lambda_wrap"

# A type-variable id guaranteed not to collide with anything in a normalized
# type, used to build the expected ``fresh -> T`` shape for MR-LAM.
_FRESH_TVAR = 10**9


# --------------------------------------------------------------------------
# Name hygiene
# --------------------------------------------------------------------------
def all_names(expr: Expr) -> set[str]:
    """Every variable name occurring in ``expr``, bound or free."""
    names: set[str] = set()

    def walk(node: Expr) -> None:
        if isinstance(node, Var):
            names.add(node.name)
        elif isinstance(node, Lam):
            names.add(node.var)
            walk(node.body)
        elif isinstance(node, App):
            walk(node.fun)
            walk(node.arg)
        elif isinstance(node, If):
            walk(node.cond)
            walk(node.then_branch)
            walk(node.else_branch)
        elif isinstance(node, Let):
            names.add(node.name)
            walk(node.bound)
            walk(node.body)
        # leaves contribute nothing

    walk(expr)
    return names


def fresh_name(expr: Expr) -> str:
    used = all_names(expr)
    i = 0
    while f"w{i}" in used:
        i += 1
    return f"w{i}"


# --------------------------------------------------------------------------
# Capture-avoiding variable renaming (for MR-ALPHA)
# --------------------------------------------------------------------------
def subst_var(expr: Expr, old: str, new: str) -> Expr:
    """Rename free occurrences of ``old`` to ``new``, stopping at shadowing.

    ``new`` must be globally fresh, so no capture can occur.
    """
    if isinstance(expr, Var):
        return Var(new) if expr.name == old else expr
    if isinstance(expr, (Lit, ETrue, EFalse)):
        return expr
    if isinstance(expr, Lam):
        if expr.var == old:
            return expr  # old shadowed below here
        return Lam(expr.var, subst_var(expr.body, old, new))
    if isinstance(expr, App):
        return App(subst_var(expr.fun, old, new), subst_var(expr.arg, old, new))
    if isinstance(expr, If):
        return If(
            subst_var(expr.cond, old, new),
            subst_var(expr.then_branch, old, new),
            subst_var(expr.else_branch, old, new),
        )
    if isinstance(expr, Let):
        bound = subst_var(expr.bound, old, new)  # name not in scope in bound
        body = expr.body if expr.name == old else subst_var(expr.body, old, new)
        return Let(expr.name, bound, body)
    raise TypeError(f"Unknown expression node: {expr!r}")


def alpha_rename_at(expr: Expr, path: tuple[str, ...], new: str) -> Expr:
    """Rename the binder at ``path`` (a Lam or Let) and its bound occurrences."""
    target = _subexpr_at(expr, path)
    if isinstance(target, Lam):
        renamed: Expr = Lam(new, subst_var(target.body, target.var, new))
    elif isinstance(target, Let):
        renamed = Let(new, target.bound, subst_var(target.body, target.name, new))
    else:
        raise ValueError(f"Cannot alpha-rename a {type(target).__name__} node")
    return replace_at(expr, path, renamed)


def _subexpr_at(expr: Expr, path: tuple[str, ...]) -> Expr:
    for pos in positions(expr):
        if pos.path == path:
            return pos.subexpr
    raise ValueError(f"No subterm at path {path!r}")


# --------------------------------------------------------------------------
# MR instances
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class MRInstance:
    mr: str
    relation: str
    source: Expr
    transformed: Expr


def _lit_instances(source: Expr, _outcome: Outcome) -> Iterator[MRInstance]:
    for pos in positions(source):
        node = pos.subexpr
        if isinstance(node, Lit):
            swapped: Expr = Lit(node.value + 1)
        elif isinstance(node, ETrue):
            swapped = EFalse()
        elif isinstance(node, EFalse):
            swapped = ETrue()
        else:
            continue
        yield MRInstance(MR_LIT, REL_EQUAL, source, replace_at(source, pos.path, swapped))


def _alpha_instances(source: Expr, _outcome: Outcome) -> Iterator[MRInstance]:
    new = fresh_name(source)
    for pos in positions(source):
        if isinstance(pos.subexpr, (Lam, Let)):
            yield MRInstance(
                MR_ALPHA, REL_EQUAL, source, alpha_rename_at(source, pos.path, new)
            )


def _deadlet_instances(source: Expr, _outcome: Outcome) -> Iterator[MRInstance]:
    z = fresh_name(source)
    yield MRInstance(MR_DEADLET, REL_EQUAL, source, Let(z, ETrue(), source))


def _lam_instances(source: Expr, _outcome: Outcome) -> Iterator[MRInstance]:
    z = fresh_name(source)
    yield MRInstance(MR_LAM, REL_LAMBDA_WRAP, source, Lam(z, source))


def _errprop_instances(source: Expr, outcome: Outcome) -> Iterator[MRInstance]:
    # Sound only for closed ill-typed sources. The corpus is closed; we gate on
    # ill-typedness here. Lam-wrapping is omitted because MR-LAM already covers it.
    if outcome.well_typed:
        return
    z = fresh_name(source)
    identity = Lam("a", Var("a"))
    contexts: list[Expr] = [
        App(source, ETrue()),
        App(identity, source),
        If(source, ETrue(), EFalse()),
        If(ETrue(), source, EFalse()),
        If(ETrue(), ETrue(), source),
        Let(z, source, ETrue()),
        Let(z, ETrue(), source),
    ]
    for ctx in contexts:
        yield MRInstance(MR_ERRPROP, REL_PROPAGATES_ERROR, source, ctx)


MR_GENERATORS: dict[str, Callable[[Expr, Outcome], Iterator[MRInstance]]] = {
    MR_LIT: _lit_instances,
    MR_ALPHA: _alpha_instances,
    MR_DEADLET: _deadlet_instances,
    MR_LAM: _lam_instances,
    MR_ERRPROP: _errprop_instances,
}


def instances_for(source: Expr, outcome: Outcome) -> Iterator[MRInstance]:
    for generator in MR_GENERATORS.values():
        yield from generator(source, outcome)


# --------------------------------------------------------------------------
# Relation checking (shared by the evaluator and the generated tests)
# --------------------------------------------------------------------------
def relation_holds(relation: str, src: Outcome, dst: Outcome) -> bool:
    if relation == REL_EQUAL:
        return src.label == dst.label
    if relation == REL_PROPAGATES_ERROR:
        return not dst.well_typed
    if relation == REL_LAMBDA_WRAP:
        if not src.well_typed:
            # Wrapping an ill-typed body in a lambda stays ill-typed.
            return not dst.well_typed
        if not dst.well_typed or dst.type_shape is None or src.type_shape is None:
            return False
        expected = normalize_ty(TFun(TVar(_FRESH_TVAR), src.type_shape))
        return dst.type_shape == expected
    raise ValueError(f"Unknown relation: {relation!r}")


def check_instance(inst: MRInstance) -> tuple[bool, Outcome, Outcome]:
    """Classify both expressions and report whether the relation holds."""
    src = classify(inst.source)
    dst = classify(inst.transformed)
    return relation_holds(inst.relation, src, dst), src, dst
