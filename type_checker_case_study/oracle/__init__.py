"""Trusted oracle for the type-checker case study.

A literal Python port of the Hindley-Milner type checker in
``cs4820/type-checker``. The progressive composition loop treats
``infer_top_type`` as ground truth when validating composite expressions.
"""

from .syntax import (
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
from .types import (
    TBool,
    TFun,
    TInt,
    TVar,
    Ty,
    infer_top_type,
    normalize_ty,
    show_ty,
)

__all__ = [
    "App",
    "EFalse",
    "ETrue",
    "Expr",
    "If",
    "Lam",
    "Let",
    "Lit",
    "Var",
    "expr_tag",
    "pretty",
    "TBool",
    "TFun",
    "TInt",
    "TVar",
    "Ty",
    "infer_top_type",
    "normalize_ty",
    "show_ty",
]
