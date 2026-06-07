r"""Metamorphic relations for the type-checker case study (Phase 1).

A metamorphic relation (MR) pairs a transform ``T`` with a relation ``R`` such
that ``R(classify(e), classify(T(e)))`` must hold for any correct checker --
*without* a reference answer for either expression. That breaks the circularity
of the label-based boundary suite: an MR violation indicts the checker even
though the checker produced the corpus.

Phase 1 ships the relations that are sound with no new inference machinery:

  * MR-LIT     -- interchange Int/Bool literals               -> equal outcome
  * MR-ALPHA   -- rename a bound variable to a fresh name      -> equal outcome
  * MR-DEADLET -- wrap in an unused, well-typed let binding    -> equal outcome
                  (EMI-style dead code after Le, Afshari, and Su,
                  "Compiler Validation via Equivalence Modulo Inputs",
                  PLDI 2014, doi:10.1145/2594291.2594334)
  * MR-LAM     -- wrap in a lambda over a fresh unused param   -> `fresh -> T`
  * MR-ERRPROP -- embed a closed ill-typed term in a context   -> error stays

(MR-DET, determinism, is already covered by the engine determinism test, since
``classify`` is a pure function; it is not re-emitted as corpus cases.)

Phase 1.5 adds three relations adapted from recent literature (full citations in
``metamorphic-related-work.md``):

  * MR-CLASH   -- graft a ground-typed term into a slot pinned to a different
                  ground type; the result must be rejected. Adapted from the
                  type-overwriting mutation of Chaliasos et al., "Finding Typing
                  Compiler Bugs", PLDI 2022 (doi:10.1145/3519939.3523427).
  * MR-KPROJ   -- `K e junk` must have the same type as `e` (a dead context).
                  An equivalence-modulo-inputs instance, after Le, Afshari, and
                  Su, "Compiler Validation via Equivalence Modulo Inputs",
                  PLDI 2014 (doi:10.1145/2594291.2594334).
  * MR-LETLAM  -- if the application form `(\x.body) v` type-checks, the let
                  form `let x=v in body` must too, and the app-form type must be
                  an instance of the (more general) let-form type. A precision
                  relation, after Kaindlstorfer, Isychev, Wuestholz, and
                  Christakis, "Interrogation Testing of Program Analyzers for
                  Soundness and Precision Issues", ASE 2024
                  (doi:10.1145/3691620.3695034).

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
from .oracle.types import TBool, TFun, TInt, Ty, TVar, normalize_ty
from .outcome import Outcome, classify

# MR identifiers.
MR_LIT = "MR-LIT"
MR_ALPHA = "MR-ALPHA"
MR_DEADLET = "MR-DEADLET"
MR_LAM = "MR-LAM"
MR_ERRPROP = "MR-ERRPROP"
# Added from the related-work scan (metamorphic-related-work.md):
MR_CLASH = "MR-CLASH"      # type-overwriting (Chaliasos et al., PLDI 2022)
MR_KPROJ = "MR-KPROJ"      # EMI dead context (Le, Afshari, Su, PLDI 2014)
MR_LETLAM = "MR-LETLAM"    # precision (Kaindlstorfer et al., ASE 2024)

# Relation kinds (used by both the evaluator and the generated tests).
REL_EQUAL = "equal_outcome"
REL_PROPAGATES_ERROR = "propagates_error"
REL_LAMBDA_WRAP = "lambda_wrap"
REL_MUST_REJECT = "must_reject"    # the transformed expression must be ill-typed
REL_INSTANCE = "app_instance_of_let"  # app-form type is an instance of the let-form type

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
    # EMI-style dead-code wrapper; citation in module docstring.
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


# --------------------------------------------------------------------------
# MR-CLASH: type-overwriting / negative substitution.
# After Chaliasos et al., "Finding Typing Compiler Bugs", PLDI 2022.
#
# Grafting a closed term of a *ground* type into a slot that is unified to a
# *different* ground type must make the whole expression ill-typed. This is
# sound and reference-free: distinct ground types are non-unifiable, and a
# closed subterm's type is context-independent, so the clash is forced. It is
# the rejection direction the other (preserve) relations lack.
# --------------------------------------------------------------------------
def is_ground(ty: Ty) -> bool:
    """True if ``ty`` has no type variables."""
    if isinstance(ty, (TBool, TInt)):
        return True
    if isinstance(ty, TVar):
        return False
    if isinstance(ty, TFun):
        return is_ground(ty.dom) and is_ground(ty.cod)
    raise TypeError(f"Unknown type node: {ty!r}")


# Closed value witnesses with known ground types, used to force a clash.
_BOOL_FN = Lam("x", If(Var("x"), ETrue(), EFalse()))   # Bool -> Bool
_INT_FN = Lam("x", If(ETrue(), Var("x"), Lit(0)))       # Int -> Int
_VALUE_WITNESSES: list[tuple[Expr, Ty]] = [
    (ETrue(), TBool()),
    (Lit(0), TInt()),
    (_BOOL_FN, TFun(TBool(), TBool())),
]
# Closed function witnesses with known ground domains.
_FUNCTION_WITNESSES: list[tuple[Expr, Ty]] = [
    (_BOOL_FN, TBool()),
    (_INT_FN, TInt()),
]


def _clash_instances(source: Expr, outcome: Outcome) -> Iterator[MRInstance]:
    if not outcome.well_typed or outcome.type_shape is None:
        return
    x_ty = outcome.type_shape
    if not is_ground(x_ty):
        return
    # Branch clash: the two if-branches have distinct ground types.
    for w_expr, w_ty in _VALUE_WITNESSES:
        if w_ty != x_ty:
            yield MRInstance(
                MR_CLASH, REL_MUST_REJECT, source, If(ETrue(), w_expr, source)
            )
    # Condition clash: a non-Bool ground condition.
    if x_ty != TBool():
        yield MRInstance(
            MR_CLASH, REL_MUST_REJECT, source, If(source, ETrue(), EFalse())
        )
    # Argument clash: a function whose ground domain differs from the argument.
    for f_expr, f_dom in _FUNCTION_WITNESSES:
        if f_dom != x_ty:
            yield MRInstance(MR_CLASH, REL_MUST_REJECT, source, App(f_expr, source))


# --------------------------------------------------------------------------
# MR-KPROJ: EMI-style dead context (the K combinator discards its argument).
# `K e junk` has the same type as `e` (junk's type is inferred but discarded).
# A structurally different dead context than the dead `let` of MR-DEADLET.
# After Le, Afshari, Su, "Compiler Validation via Equivalence Modulo Inputs",
# PLDI 2014.
# --------------------------------------------------------------------------
_K_COMBINATOR = Lam("a", Lam("b", Var("a")))


def _kproj_instances(source: Expr, _outcome: Outcome) -> Iterator[MRInstance]:
    # source is closed, so K's binders cannot capture anything in it.
    transformed = App(App(_K_COMBINATOR, source), ETrue())
    yield MRInstance(MR_KPROJ, REL_EQUAL, source, transformed)


# --------------------------------------------------------------------------
# MR-LETLAM: precision / generality. After Kaindlstorfer, Isychev, Wuestholz,
# Christakis, "Interrogation Testing of Program Analyzers ...", ASE 2024.
# For a lambda `\x. body`, the application form `(\x. body) v` is monomorphic in
# x, while the let form `let x = v in body` generalizes x. So whenever the app
# form type-checks, the let form must too, and the app-form type must be an
# *instance* of the let-form type. `v` is a polymorphic identity so the two
# forms can genuinely differ.
# --------------------------------------------------------------------------
_POLY_ID = Lam("i", Var("i"))


def is_instance_of(general: Ty, specific: Ty) -> bool:
    """True if ``specific`` is a substitution instance of ``general``.

    One-directional matching: type variables in ``general`` may be bound to
    arbitrary subtypes of ``specific``; variables in ``specific`` are rigid.
    Both arguments are expected to be normalized.
    """
    subst: dict[int, Ty] = {}

    def match(g: Ty, s: Ty) -> bool:
        if isinstance(g, TVar):
            bound = subst.get(g.n)
            if bound is not None:
                return bound == s
            subst[g.n] = s
            return True
        if isinstance(g, TBool):
            return isinstance(s, TBool)
        if isinstance(g, TInt):
            return isinstance(s, TInt)
        if isinstance(g, TFun):
            return (
                isinstance(s, TFun)
                and match(g.dom, s.dom)
                and match(g.cod, s.cod)
            )
        raise TypeError(f"Unknown type node: {g!r}")

    return match(general, specific)


def _letlam_instances(source: Expr, _outcome: Outcome) -> Iterator[MRInstance]:
    if not isinstance(source, Lam):
        return
    app_form: Expr = App(source, _POLY_ID)
    let_form: Expr = Let(source.var, _POLY_ID, source.body)
    # Only meaningful when the (monomorphic) app form type-checks; otherwise the
    # relation places no constraint on the let form.
    if not classify(app_form).well_typed:
        return
    yield MRInstance(MR_LETLAM, REL_INSTANCE, app_form, let_form)


MR_GENERATORS: dict[str, Callable[[Expr, Outcome], Iterator[MRInstance]]] = {
    MR_LIT: _lit_instances,
    MR_ALPHA: _alpha_instances,
    MR_DEADLET: _deadlet_instances,
    MR_LAM: _lam_instances,
    MR_ERRPROP: _errprop_instances,
    MR_CLASH: _clash_instances,
    MR_KPROJ: _kproj_instances,
    MR_LETLAM: _letlam_instances,
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
    if relation == REL_MUST_REJECT:
        return not dst.well_typed
    if relation == REL_INSTANCE:
        # src = application form, dst = let form. The generator only emits cases
        # where the app form type-checks, so the let form must too and the
        # app-form type must be an instance of the (more general) let-form type.
        if not src.well_typed or src.type_shape is None:
            return True
        if not dst.well_typed or dst.type_shape is None:
            return False
        return is_instance_of(dst.type_shape, src.type_shape)
    raise ValueError(f"Unknown relation: {relation!r}")


def check_instance(inst: MRInstance) -> tuple[bool, Outcome, Outcome]:
    """Classify both expressions and report whether the relation holds."""
    src = classify(inst.source)
    dst = classify(inst.transformed)
    return relation_holds(inst.relation, src, dst), src, dst
