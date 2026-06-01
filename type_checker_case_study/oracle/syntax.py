"""Expression syntax for the type-checker case study.

Direct port of ``cs4820/type-checker/src/Syntax.hs``. These eight constructors
are the *elementary components* of the case study: every composite test
expression (the combinators, the let-polymorphism cases, the error cases) is
built by nesting these like Lego bricks.

    data Expr
        = Var String
        | Lam String Expr
        | App Expr Expr
        | If Expr Expr Expr
        | Let String Expr Expr
        | Lit Int
        | ETrue
        | EFalse

Expressions are frozen dataclasses so they are hashable and value-comparable,
which the composition loop relies on when deduplicating candidates.
"""

from __future__ import annotations

from dataclasses import dataclass


class Expr:
    """Base class for expression nodes."""

    __slots__ = ()


@dataclass(frozen=True)
class Var(Expr):
    name: str


@dataclass(frozen=True)
class Lam(Expr):
    var: str
    body: Expr


@dataclass(frozen=True)
class App(Expr):
    fun: Expr
    arg: Expr


@dataclass(frozen=True)
class If(Expr):
    cond: Expr
    then_branch: Expr
    else_branch: Expr


@dataclass(frozen=True)
class Let(Expr):
    name: str
    bound: Expr
    body: Expr


@dataclass(frozen=True)
class Lit(Expr):
    value: int


@dataclass(frozen=True)
class ETrue(Expr):
    pass


@dataclass(frozen=True)
class EFalse(Expr):
    pass


def expr_tag(expr: Expr) -> str:
    """The constructor tag, mirroring ``exprTag`` in Type.hs."""
    return type(expr).__name__


def pretty(expr: Expr) -> str:
    """A compact lambda-calculus rendering, useful in reports and test ids."""
    if isinstance(expr, Var):
        return expr.name
    if isinstance(expr, Lam):
        return f"(\\{expr.var}. {pretty(expr.body)})"
    if isinstance(expr, App):
        return f"({pretty(expr.fun)} {pretty(expr.arg)})"
    if isinstance(expr, If):
        return (
            f"(if {pretty(expr.cond)} then {pretty(expr.then_branch)} "
            f"else {pretty(expr.else_branch)})"
        )
    if isinstance(expr, Let):
        return f"(let {expr.name} = {pretty(expr.bound)} in {pretty(expr.body)})"
    if isinstance(expr, Lit):
        return str(expr.value)
    if isinstance(expr, ETrue):
        return "True"
    if isinstance(expr, EFalse):
        return "False"
    raise TypeError(f"Unknown expression node: {expr!r}")
