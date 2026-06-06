"""Tests for the Phase-1 metamorphic relations and the bug they exposed."""

from __future__ import annotations

import pytest

from type_checker_case_study.metamorphic import (
    MR_DEADLET,
    REL_EQUAL,
    REL_LAMBDA_WRAP,
    REL_PROPAGATES_ERROR,
    all_names,
    alpha_rename_at,
    fresh_name,
    instances_for,
    relation_holds,
    subst_var,
)
from type_checker_case_study.compose import is_closed
from type_checker_case_study.metamorphic_eval import evaluate
from type_checker_case_study.oracle.syntax import App, EFalse, ETrue, Lam, Let, Lit, Var
from type_checker_case_study.oracle.types import TBool, TFun, TVar
from type_checker_case_study.oracle import infer_top_type
from type_checker_case_study.outcome import Outcome, classify


def test_fresh_name_avoids_all_bound_and_free_names():
    expr = Lam("w0", App(Var("w0"), Var("w1")))
    assert all_names(expr) == {"w0", "w1"}
    fresh = fresh_name(expr)
    assert fresh not in all_names(expr)


def test_subst_var_respects_shadowing():
    # outer x should rename; inner lambda rebinds x, so its body is untouched.
    expr = App(Var("x"), Lam("x", Var("x")))
    renamed = subst_var(expr, "x", "q")
    assert renamed == App(Var("q"), Lam("x", Var("x")))


def test_alpha_rename_preserves_outcome():
    expr = Lam("x", Lam("y", Var("x")))  # K combinator
    renamed = alpha_rename_at(expr, (), "q")  # rename outer binder
    assert renamed == Lam("q", Lam("y", Var("q")))
    assert classify(expr).label == classify(renamed).label


def test_relation_equal():
    a = Outcome(True, TBool(), None)
    b = Outcome(True, TBool(), None)
    assert relation_holds(REL_EQUAL, a, b)
    assert not relation_holds(REL_EQUAL, a, Outcome(False, None, "occurs-check"))


def test_relation_propagates_error():
    ill = Outcome(False, None, "occurs-check")
    assert relation_holds(REL_PROPAGATES_ERROR, ill, Outcome(False, None, "type-mismatch"))
    assert not relation_holds(REL_PROPAGATES_ERROR, ill, Outcome(True, TBool(), None))


def test_relation_lambda_wrap_shape():
    # source : (a -> a); wrapping should give (b -> (a -> a)).
    src = Outcome(True, TFun(TVar(0), TVar(0)), None)
    good = Outcome(True, TFun(TVar(0), TFun(TVar(1), TVar(1))), None)
    bad = Outcome(True, TFun(TVar(0), TVar(0)), None)
    assert relation_holds(REL_LAMBDA_WRAP, src, good)
    assert not relation_holds(REL_LAMBDA_WRAP, src, bad)


def test_errprop_only_for_ill_typed_and_stays_closed():
    well = Lam("x", Var("x"))
    assert list(
        i for i in instances_for(well, classify(well)) if i.mr == "MR-ERRPROP"
    ) == []

    ill = Lam("x", App(Var("x"), Var("x")))  # occurs-check
    errprop = [
        i for i in instances_for(ill, classify(ill)) if i.mr == "MR-ERRPROP"
    ]
    assert errprop
    for inst in errprop:
        assert is_closed(inst.transformed)
        assert not classify(inst.transformed).well_typed  # error propagates


# --- The bug found by MR-DEADLET ------------------------------------------
@pytest.mark.xfail(
    strict=True,
    reason=(
        "Known checker bug: inferLam leaves a non-idempotent substitution, so "
        "the standalone type of `\\x.\\y. x (x y)` is the unsound `(a->b)->(b->b)` "
        "while a dead `let` (which re-applies the full subst) yields the correct "
        "`(a->a)->(a->a)`. A dead binding must preserve the type; this xfail flips "
        "to a failure when the checker is fixed."
    ),
)
def test_dead_let_preserves_type_apply_twice():
    e = Lam("x", Lam("y", App(Var("x"), App(Var("x"), Var("y")))))
    assert infer_top_type(e) == infer_top_type(Let("w", ETrue(), e))


def test_metamorphic_eval_surfaces_the_deadlet_bug():
    # A small corpus is enough to detect the bug class; this pins that the
    # metamorphic lane is actually catching it.
    result = evaluate(max_size=8, max_rounds=4, cap_per_round=200)
    deadlet_violations = [v for v in result.violations if v.instance.mr == MR_DEADLET]
    assert deadlet_violations, "expected MR-DEADLET to expose the substitution bug"
