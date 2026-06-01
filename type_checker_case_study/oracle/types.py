"""Types, substitutions, unification, and Algorithm W.

Direct port of ``cs4820/type-checker/src/Type.hs``. This is the *trusted
oracle* for the case study: the progressive composition loop proposes composite
expressions and asks ``infer_top_type`` what they actually do. Where a Datalog
composition policy disagrees with this oracle, that disagreement is the finding.

The port keeps the Haskell structure deliberately literal -- substitutions are
ordered association lists, ``compose_subst`` preserves the same priority order,
and ``normalize_ty`` renumbers type variables in first-appearance order -- so
parity with the Haskell test suite is easy to audit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .syntax import App, EFalse, ETrue, Expr, If, Lam, Let, Lit, Var


# --------------------------------------------------------------------------
# Types and schemes
# --------------------------------------------------------------------------
class Ty:
    __slots__ = ()


@dataclass(frozen=True)
class TVar(Ty):
    n: int


@dataclass(frozen=True)
class TFun(Ty):
    dom: Ty
    cod: Ty


@dataclass(frozen=True)
class TBool(Ty):
    pass


@dataclass(frozen=True)
class TInt(Ty):
    pass


@dataclass(frozen=True)
class Scheme:
    """Forall [vars] ty."""

    vars: tuple[int, ...]
    ty: Ty


# A substitution is an ordered list of (type-var-id, type) pairs. Earlier
# entries shadow later ones on lookup, matching Haskell's ``lookup``.
Subst = list[tuple[int, Ty]]
# A typing environment is an ordered list of (name, scheme) pairs.
TyEnv = list[tuple[str, Scheme]]


# --------------------------------------------------------------------------
# Free type variables
# --------------------------------------------------------------------------
def ftv_ty(ty: Ty) -> list[int]:
    if isinstance(ty, TVar):
        return [ty.n]
    if isinstance(ty, TFun):
        return _nub(ftv_ty(ty.dom) + ftv_ty(ty.cod))
    return []  # TBool, TInt


def ftv_scheme(scheme: Scheme) -> list[int]:
    return _diff(ftv_ty(scheme.ty), list(scheme.vars))


def ftv_env(env: TyEnv) -> list[int]:
    acc: list[int] = []
    for _, scheme in env:
        acc.extend(ftv_scheme(scheme))
    return _nub(acc)


def _nub(xs: list[int]) -> list[int]:
    """Order-preserving dedup, like Data.List.nub."""
    seen: set[int] = set()
    out: list[int] = []
    for x in xs:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _diff(xs: list[int], ys: list[int]) -> list[int]:
    """List difference xs \\ ys, removing each element of ys once."""
    ys_remaining = list(ys)
    out: list[int] = []
    for x in xs:
        if x in ys_remaining:
            ys_remaining.remove(x)
        else:
            out.append(x)
    return out


# --------------------------------------------------------------------------
# Substitution
# --------------------------------------------------------------------------
def subst_lookup(n: int, subst: Subst) -> Optional[Ty]:
    for k, ty in subst:
        if k == n:
            return ty
    return None


def env_lookup(name: str, env: TyEnv) -> Optional[Scheme]:
    for k, scheme in env:
        if k == name:
            return scheme
    return None


def remove_subst_keys(vars_: list[int], subst: Subst) -> Subst:
    return [(k, ty) for (k, ty) in subst if k not in vars_]


def apply_subst_ty(subst: Subst, ty: Ty) -> Ty:
    if isinstance(ty, TBool):
        return ty
    if isinstance(ty, TInt):
        return ty
    if isinstance(ty, TVar):
        found = subst_lookup(ty.n, subst)
        return found if found is not None else ty
    if isinstance(ty, TFun):
        return TFun(apply_subst_ty(subst, ty.dom), apply_subst_ty(subst, ty.cod))
    raise TypeError(f"Unknown type node: {ty!r}")


def apply_subst_scheme(subst: Subst, scheme: Scheme) -> Scheme:
    subst2 = remove_subst_keys(list(scheme.vars), subst)
    return Scheme(scheme.vars, apply_subst_ty(subst2, scheme.ty))


def apply_subst_env(subst: Subst, env: TyEnv) -> TyEnv:
    return [(name, apply_subst_scheme(subst, scheme)) for (name, scheme) in env]


def occurs_in_ty(n: int, ty: Ty) -> bool:
    if isinstance(ty, (TBool, TInt)):
        return False
    if isinstance(ty, TVar):
        return n == ty.n
    if isinstance(ty, TFun):
        return occurs_in_ty(n, ty.dom) or occurs_in_ty(n, ty.cod)
    raise TypeError(f"Unknown type node: {ty!r}")


def subst_has_key(n: int, subst: Subst) -> bool:
    return any(k == n for k, _ in subst)


def compose_subst(s1: Subst, s2: Subst) -> Subst:
    """Compose substitutions, preserving Haskell's priority order.

    filtered = [(k, apply s2 ty) for (k, ty) in s1 if k not in s2]
    result   = filtered ++ s2
    """
    filtered = [
        (k, apply_subst_ty(s2, ty)) for (k, ty) in s1 if not subst_has_key(k, s2)
    ]
    return filtered + list(s2)


# --------------------------------------------------------------------------
# Unification
# --------------------------------------------------------------------------
class UnifyFail(Exception):
    """Carries the same message text as the Haskell ``UnifyFail``."""


def bind_tvar(n: int, ty: Ty) -> Subst:
    if ty == TVar(n):
        return []
    if occurs_in_ty(n, ty):
        raise UnifyFail(
            f"Occurs check failed: cannot unify {show_ty_raw(TVar(n))} "
            f"with {show_ty_raw(ty)}"
        )
    return [(n, ty)]


def unify(ty1: Ty, ty2: Ty) -> Subst:
    if isinstance(ty1, TBool) and isinstance(ty2, TBool):
        return []
    if isinstance(ty1, TInt) and isinstance(ty2, TInt):
        return []
    if isinstance(ty1, TVar):
        return bind_tvar(ty1.n, ty2)
    if isinstance(ty2, TVar):
        return bind_tvar(ty2.n, ty1)
    if isinstance(ty1, TFun) and isinstance(ty2, TFun):
        subst1 = unify(ty1.dom, ty2.dom)
        subst2 = unify(
            apply_subst_ty(subst1, ty1.cod), apply_subst_ty(subst1, ty2.cod)
        )
        return compose_subst(subst2, subst1)
    raise UnifyFail(
        f"Failed to unify types: {show_ty_raw(ty1)} and {show_ty_raw(ty2)}"
    )


# --------------------------------------------------------------------------
# Generalization / instantiation
# --------------------------------------------------------------------------
def generalize(env: TyEnv, ty: Ty) -> Scheme:
    vars_ = _diff(ftv_ty(ty), ftv_env(env))
    return Scheme(tuple(vars_), ty)


def instantiate(scheme: Scheme, next_: int) -> tuple[Ty, int]:
    fresh_vars = list(range(next_, next_ + len(scheme.vars)))
    subst: Subst = list(zip(scheme.vars, [TVar(v) for v in fresh_vars]))
    return apply_subst_ty(subst, scheme.ty), next_ + len(scheme.vars)


def fresh_ty_var(next_: int) -> tuple[Ty, int]:
    return TVar(next_), next_ + 1


def env_extend(name: str, scheme: Scheme, env: TyEnv) -> TyEnv:
    return [(name, scheme)] + env


# --------------------------------------------------------------------------
# Algorithm W
# --------------------------------------------------------------------------
class InferFail(Exception):
    """Type-inference failure, carrying the Haskell-style reason chain."""


# An InferResult is (subst, ty, next) on success; failure raises InferFail.
def infer(env: TyEnv, expr: Expr, next_: int) -> tuple[Subst, Ty, int]:
    if isinstance(expr, ETrue):
        return [], TBool(), next_
    if isinstance(expr, EFalse):
        return [], TBool(), next_
    if isinstance(expr, Lit):
        return [], TInt(), next_
    if isinstance(expr, Var):
        return _infer_var(env, expr, next_)
    if isinstance(expr, Lam):
        return _infer_lam(env, expr, next_)
    if isinstance(expr, App):
        return _infer_app(env, expr, next_)
    if isinstance(expr, If):
        return _infer_if(env, expr, next_)
    if isinstance(expr, Let):
        return _infer_let(env, expr, next_)
    raise TypeError(f"Unknown expression node: {expr!r}")


def _infer_var(env: TyEnv, expr: Var, next_: int) -> tuple[Subst, Ty, int]:
    scheme = env_lookup(expr.name, env)
    if scheme is None:
        raise InferFail(f"Unbound variable: {expr.name}")
    ty, next1 = instantiate(scheme, next_)
    return [], ty, next1


def _infer_lam(env: TyEnv, expr: Lam, next_: int) -> tuple[Subst, Ty, int]:
    param_ty, next1 = fresh_ty_var(next_)
    # Lambda-bound variable is monomorphic: wrapped in an empty-quantifier scheme.
    env2 = env_extend(expr.var, Scheme((), param_ty), env)
    try:
        subst, body_ty, next2 = infer(env2, expr.body, next1)
    except InferFail as exc:
        raise InferFail(f"Failed to infer lambda body: {exc}") from exc
    fun_ty = TFun(apply_subst_ty(subst, param_ty), body_ty)
    return subst, fun_ty, next2


def _infer_app(env: TyEnv, expr: App, next_: int) -> tuple[Subst, Ty, int]:
    try:
        subst_fun, fun_ty, next1 = infer(env, expr.fun, next_)
    except InferFail as exc:
        raise InferFail(f"Failed to infer function: {exc}") from exc
    try:
        subst_arg, arg_ty, next2 = infer(
            apply_subst_env(subst_fun, env), expr.arg, next1
        )
    except InferFail as exc:
        raise InferFail(f"Failed to infer argument: {exc}") from exc
    result_ty, next3 = fresh_ty_var(next2)
    fun_ty_expected = TFun(arg_ty, result_ty)
    try:
        subst_unify = unify(apply_subst_ty(subst_arg, fun_ty), fun_ty_expected)
    except UnifyFail as exc:
        raise InferFail(f"Failed to unify function type: {exc}") from exc
    subst = compose_subst(subst_unify, compose_subst(subst_arg, subst_fun))
    return subst, apply_subst_ty(subst, result_ty), next3


def _infer_if(env: TyEnv, expr: If, next_: int) -> tuple[Subst, Ty, int]:
    try:
        subst_cond, cond_ty, next1 = infer(env, expr.cond, next_)
    except InferFail as exc:
        raise InferFail(f"Failed to infer condition: {exc}") from exc
    try:
        subst_unify_cond = unify(cond_ty, TBool())
    except UnifyFail as exc:
        raise InferFail(
            f"Condition must be of type Bool: {exc} "
            f"Inferred type: {show_ty_raw(cond_ty)}"
        ) from exc
    subst1 = compose_subst(subst_unify_cond, subst_cond)
    try:
        subst_then, then_ty, next2 = infer(
            apply_subst_env(subst1, env), expr.then_branch, next1
        )
    except InferFail as exc:
        raise InferFail(f"Failed to infer then branch: {exc}") from exc
    try:
        subst_else, else_ty, next3 = infer(
            apply_subst_env(subst_then, apply_subst_env(subst1, env)),
            expr.else_branch,
            next2,
        )
    except InferFail as exc:
        raise InferFail(f"Failed to infer else branch: {exc}") from exc
    then_ty_s = apply_subst_ty(subst_else, then_ty)
    try:
        subst_unify_else = unify(then_ty_s, else_ty)
    except UnifyFail as exc:
        raise InferFail(
            f"Then and Else branch must be of same type: {exc} "
            f"Then branch: {show_ty_raw(then_ty_s)} "
            f"Else branch: {show_ty_raw(else_ty)}"
        ) from exc
    s = subst_unify_else
    for nxt in (subst_else, subst_then, subst_unify_cond, subst_cond):
        s = compose_subst(s, nxt)
    return s, apply_subst_ty(s, else_ty), next3


def _infer_let(env: TyEnv, expr: Let, next_: int) -> tuple[Subst, Ty, int]:
    try:
        subst1, bound_ty, next1 = infer(env, expr.bound, next_)
    except InferFail as exc:
        raise InferFail(f"Failed to infer let-bound expression: {exc}") from exc
    env1 = apply_subst_env(subst1, env)
    bound_ty1 = apply_subst_ty(subst1, bound_ty)
    scheme = generalize(env1, bound_ty1)
    env2 = env_extend(expr.name, scheme, env1)
    try:
        subst2, body_ty, next2 = infer(env2, expr.body, next1)
    except InferFail as exc:
        raise InferFail(f"Failed to infer let body: {exc}") from exc
    subst = compose_subst(subst2, subst1)
    return subst, apply_subst_ty(subst, body_ty), next2


def infer_top(expr: Expr) -> tuple[Subst, Ty, int]:
    return infer([], expr, 0)


# --------------------------------------------------------------------------
# Normalization and rendering
# --------------------------------------------------------------------------
def normalize_ty(ty: Ty) -> Ty:
    """Renumber type variables in first-appearance order, starting at 0."""
    renaming: dict[int, int] = {}

    def go(t: Ty) -> Ty:
        if isinstance(t, (TBool, TInt)):
            return t
        if isinstance(t, TVar):
            if t.n not in renaming:
                renaming[t.n] = len(renaming)
            return TVar(renaming[t.n])
        if isinstance(t, TFun):
            dom = go(t.dom)
            cod = go(t.cod)
            return TFun(dom, cod)
        raise TypeError(f"Unknown type node: {t!r}")

    return go(ty)


def infer_top_type(expr: Expr) -> Optional[Ty]:
    """Principal type of a closed expression, normalized; ``None`` if ill-typed.

    Mirrors ``inferTopType``: the public oracle entry point used by the loop.
    """
    try:
        subst, ty, _ = infer_top(expr)
    except InferFail:
        return None
    return normalize_ty(apply_subst_ty(subst, ty))


def show_ty_raw(ty: Ty) -> str:
    """Haskell ``show`` rendering, used inside failure messages for parity."""
    if isinstance(ty, TVar):
        return f"TVar {ty.n}"
    if isinstance(ty, TBool):
        return "TBool"
    if isinstance(ty, TInt):
        return "TInt"
    if isinstance(ty, TFun):
        return f"TFun ({show_ty_raw(ty.dom)}) ({show_ty_raw(ty.cod)})"
    raise TypeError(f"Unknown type node: {ty!r}")


def show_ty(ty: Ty) -> str:
    """Human-friendly rendering, e.g. ``(a -> a)`` or ``(Bool -> Bool)``."""

    def name(n: int) -> str:
        # 0->a, 1->b, ... 25->z, 26->a1, ...
        letter = chr(ord("a") + n % 26)
        suffix = n // 26
        return letter if suffix == 0 else f"{letter}{suffix}"

    if isinstance(ty, TVar):
        return name(ty.n)
    if isinstance(ty, TBool):
        return "Bool"
    if isinstance(ty, TInt):
        return "Int"
    if isinstance(ty, TFun):
        return f"({show_ty(ty.dom)} -> {show_ty(ty.cod)})"
    raise TypeError(f"Unknown type node: {ty!r}")
