"""Parity suite: the Python oracle must reproduce every case in TypeTest.hs.

Each assertion below is a direct transcription of an `it "..."` example from
``cs4820/type-checker/test/TypeTest.hs``. Passing this suite is what lets the
rest of the case study trust ``infer_top_type`` as ground truth. Combinator
cases are tagged so the progressive loop can reuse them as seeds.
"""

from __future__ import annotations

import pytest

from type_checker_case_study.oracle import (
    App,
    EFalse,
    ETrue,
    If,
    Lam,
    Let,
    Lit,
    TBool,
    TFun,
    TInt,
    TVar,
    Var,
    infer_top_type,
)


def a(*ts):
    """Right-nested function type sugar: a(x, y, z) == x -> (y -> z)."""
    if len(ts) == 1:
        return ts[0]
    return TFun(ts[0], a(*ts[1:]))


# ---- Helper functions (Ty helpers / Subst / unify) are covered by the unit
# ---- tests in test_oracle_internals.py; here we focus on infer-top parity.


WELL_TYPED_CASES = {
    # name: (expr, expected normalized type)
    "id": (Lam("x", Var("x")), TFun(TVar(0), TVar(0))),
    "const_true": (Lam("x", ETrue()), TFun(TVar(0), TBool())),
    "const_false": (Lam("x", EFalse()), TFun(TVar(0), TBool())),
    "K_combinator": (
        Lam("x", Lam("y", Var("x"))),
        a(TVar(0), TVar(1), TVar(0)),
    ),
    "KI_combinator": (
        Lam("x", Lam("y", Var("y"))),
        a(TVar(0), TVar(1), TVar(1)),
    ),
    "apply_id_true": (App(Lam("x", Var("x")), ETrue()), TBool()),
    "K_applied": (
        App(App(Lam("x", Lam("y", Var("x"))), ETrue()), EFalse()),
        TBool(),
    ),
    "if_bool3": (If(ETrue(), EFalse(), ETrue()), TBool()),
    "if_bool4": (If(EFalse(), ETrue(), EFalse()), TBool()),
    "bool_to_bool": (
        Lam("x", If(Var("x"), ETrue(), EFalse())),
        TFun(TBool(), TBool()),
    ),
    "bool_to_bool2": (
        Lam("x", If(Var("x"), Var("x"), EFalse())),
        TFun(TBool(), TBool()),
    ),
    "bool_bool_bool": (
        Lam("x", Lam("y", If(Var("x"), Var("y"), ETrue()))),
        a(TBool(), TBool(), TBool()),
    ),
    "id_f": (Lam("f", Var("f")), TFun(TVar(0), TVar(0))),
    "id_via_app": (
        App(
            Lam("f", Lam("x", App(Var("f"), Var("x")))),
            Lam("z", Var("z")),
        ),
        TFun(TVar(0), TVar(0)),
    ),
    "apply_combinator": (
        Lam("f", Lam("x", App(Var("f"), Var("x")))),
        a(TFun(TVar(0), TVar(1)), TVar(0), TVar(1)),
    ),
    "B_combinator": (
        Lam("f", Lam("g", Lam("x", App(Var("f"), App(Var("g"), Var("x")))))),
        a(
            TFun(TVar(0), TVar(1)),
            TFun(TVar(2), TVar(0)),
            TVar(2),
            TVar(1),
        ),
    ),
    "bool_arrow_a": (
        Lam("f", App(Var("f"), ETrue())),
        a(TFun(TBool(), TVar(0)), TVar(0)),
    ),
    "bool_arrow_a_b": (
        Lam("f", Lam("x", App(Var("f"), ETrue()))),
        a(TFun(TBool(), TVar(0)), TVar(1), TVar(0)),
    ),
    "C_combinator": (
        Lam("f", Lam("x", Lam("y", App(App(Var("f"), Var("y")), Var("x"))))),
        a(
            a(TVar(0), TVar(1), TVar(2)),
            TVar(1),
            TVar(0),
            TVar(2),
        ),
    ),
    "W_combinator": (
        Lam("f", Lam("x", App(App(Var("f"), Var("x")), Var("x")))),
        a(
            a(TVar(0), TVar(0), TVar(1)),
            TVar(0),
            TVar(1),
        ),
    ),
    "S_combinator": (
        Lam(
            "f",
            Lam("g", Lam("x", App(App(Var("f"), Var("x")), App(Var("g"), Var("x"))))),
        ),
        a(
            a(TVar(0), TVar(1), TVar(2)),
            TFun(TVar(0), TVar(1)),
            TVar(0),
            TVar(2),
        ),
    ),
    "let_id": (
        Let("id", Lam("x", Var("x")), Var("id")),
        TFun(TVar(0), TVar(0)),
    ),
    "let_id_bool": (
        Let("id", Lam("x", Var("x")), App(Var("id"), ETrue())),
        TBool(),
    ),
    "let_id_int": (
        Let("id", Lam("x", Var("x")), App(Var("id"), Lit(3))),
        TInt(),
    ),
    "let_poly_id_int": (
        Let(
            "id",
            Lam("x", Var("x")),
            If(ETrue(), App(Var("id"), Lit(3)), App(Var("id"), Lit(4))),
        ),
        TInt(),
    ),
    "let_poly_const_bool": (
        Let(
            "const",
            Lam("x", Lam("y", Var("x"))),
            App(App(Var("const"), ETrue()), Lit(3)),
        ),
        TBool(),
    ),
    "let_poly_const_int": (
        Let(
            "const",
            Lam("x", Lam("y", Var("x"))),
            App(App(Var("const"), Lit(3)), ETrue()),
        ),
        TInt(),
    ),
    "let_id_bool_and_int": (
        Let(
            "id",
            Lam("x", Var("x")),
            App(
                App(
                    Lam("b", Lam("i", Var("b"))),
                    App(Var("id"), ETrue()),
                ),
                App(Var("id"), Lit(3)),
            ),
        ),
        TBool(),
    ),
    "nested_let": (
        Let(
            "id",
            Lam("x", Var("x")),
            Let("a", App(Var("id"), ETrue()), App(Var("id"), Lit(3))),
        ),
        TInt(),
    ),
    "let_in_lambda_poly": (
        Lam(
            "z",
            Let(
                "id",
                Lam("x", Var("x")),
                If(Var("z"), App(Var("id"), ETrue()), App(Var("id"), EFalse())),
            ),
        ),
        TFun(TBool(), TBool()),
    ),
}


ILL_TYPED_CASES = {
    "unbound_var": Var("x"),
    "unbound_in_lambda": Lam("x", Var("y")),
    "apply_non_function": App(ETrue(), EFalse()),
    "apply_non_function_nested": Lam("x", App(ETrue(), Var("x"))),
    "hetero_if_then_lambda": If(ETrue(), EFalse(), Lam("x", ETrue())),
    "hetero_if_else_lambda": If(ETrue(), Lam("x", ETrue()), EFalse()),
    "bad_if_condition": If(Lam("x", ETrue()), EFalse(), ETrue()),
    "occurs_self_app": Lam("x", App(Var("x"), Var("x"))),
    "occurs_f_f": Lam("f", Lam("x", App(Var("f"), Var("f")))),
    "let_bound_ill_typed": Let("bad", App(ETrue(), EFalse()), Var("bad")),
    "let_body_ill_typed": Let("id", Lam("x", Var("x")), App(ETrue(), Var("id"))),
    "lambda_param_monomorphic": Lam(
        "f",
        If(ETrue(), App(Var("f"), ETrue()), App(Var("f"), Lit(3))),
    ),
}


@pytest.mark.parametrize("name", sorted(WELL_TYPED_CASES))
def test_well_typed_parity(name):
    expr, expected = WELL_TYPED_CASES[name]
    assert infer_top_type(expr) == expected


@pytest.mark.parametrize("name", sorted(ILL_TYPED_CASES))
def test_ill_typed_parity(name):
    expr = ILL_TYPED_CASES[name]
    assert infer_top_type(expr) is None
