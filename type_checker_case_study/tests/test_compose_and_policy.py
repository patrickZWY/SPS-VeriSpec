"""Tests for the progressive composition engine and outcome classification."""

from __future__ import annotations

from type_checker_case_study.compose import (
    MutationEdge,
    free_vars,
    grow,
    is_closed,
    mutate,
    positions,
    replace_at,
    size,
)
from type_checker_case_study.generate_flip_tests import select_chains
from type_checker_case_study.facts import resolve_expr
from type_checker_case_study.oracle.syntax import App, ETrue, If, Lam, Let, Lit, Var
from type_checker_case_study.outcome import classify


def test_size_and_free_vars():
    expr = Lam("x", App(Var("x"), Var("y")))
    assert size(expr) == 4
    assert free_vars(expr) == {"y"}
    assert not is_closed(expr)
    assert is_closed(Lam("x", Var("x")))


def test_let_scopes_name_only_in_body():
    # `x` is bound in the body but NOT in the bound expression.
    expr = Let("x", Var("x"), Var("x"))
    assert free_vars(expr) == {"x"}  # the occurrence in the bound expr is free


def test_positions_track_scope():
    expr = Lam("x", If(Var("x"), ETrue(), Var("x")))
    scoped = {pos.path: pos.scope for pos in positions(expr)}
    # inside the lambda body, x is in scope
    assert scoped[("body", "cond")] == frozenset({"x"})
    # at the root, nothing is in scope
    assert scoped[()] == frozenset()


def test_replace_at_roundtrip():
    expr = If(ETrue(), Lit(1), Lit(2))
    replaced = replace_at(expr, ("then",), ETrue())
    assert replaced == If(ETrue(), ETrue(), Lit(2))
    # original is untouched (expressions are immutable)
    assert expr == If(ETrue(), Lit(1), Lit(2))


def test_mutations_are_closed_and_bounded():
    seed = Lam("x", Var("x"))
    for child in mutate(seed, max_size=8):
        assert is_closed(child)
        assert size(child) <= 8
        assert child != seed


def test_self_application_is_occurs_check():
    # The canonical bug probe: identity mutated into self-application.
    expr = Lam("x", App(Var("x"), Var("x")))
    out = classify(expr)
    assert not out.well_typed
    assert out.error_class == "occurs-check"


def test_let_polymorphic_self_application_is_well_typed():
    # Same self-application shape, but let-bound: polymorphism makes it fine.
    expr = Let("id", Lam("x", Var("x")), App(Var("id"), Var("id")))
    out = classify(expr)
    assert out.well_typed


def test_resolve_distinguishes_lam_and_let_binders():
    expr = Let("id", Lam("x", Var("x")), App(Var("id"), Var("id")))
    facts = resolve_expr(expr)
    kinds = {name: kind for (_, name, _, kind) in facts.var_refs}
    assert kinds["id"] == "Let"  # the self-applied var is let-bound, so safe
    assert kinds["x"] == "Lam"


def test_grow_is_deterministic_and_finds_known_cases():
    a = grow(max_size=6, max_rounds=2, cap_per_round=50)
    b = grow(max_size=6, max_rounds=2, cap_per_round=50)
    assert [str(e) for e in a.expressions] == [str(e) for e in b.expressions]
    # the identity and a self-application should both be reachable
    assert Lam("x", Var("x")) in set(a.expressions)


def test_select_chains_finds_four_level_progressions():
    e0 = Lam("x", Var("x"))
    e1 = Lam("x", App(Var("x"), ETrue()))
    e2 = Lam("x", App(Var("x"), Var("x")))
    e3 = Lam("x", App(Lam("y", ETrue()), Var("x")))
    outcomes = {expr: classify(expr) for expr in (e0, e1, e2, e3)}
    chains = select_chains(
        [
            MutationEdge(e0, e1, 1),
            MutationEdge(e1, e2, 2),
            MutationEdge(e2, e3, 3),
        ],
        outcomes,
        steps=4,
        per_kind=5,
    )

    assert len(chains) == 1
    chain = chains[0]
    assert chain.kind == "mixed-chain"
    assert chain.expressions == (e0, e1, e2, e3)
    assert chain.outcomes == (
        "(a -> a)",
        "((Bool -> a) -> a)",
        "error:occurs-check",
        "(a -> Bool)",
    )


def test_select_chains_drops_redundant_repeated_outcomes():
    e0 = ETrue()
    e1 = Let("x", ETrue(), ETrue())
    e2 = Let("x", ETrue(), Let("y", ETrue(), ETrue()))
    e3 = Lam("x", Let("x", ETrue(), Let("y", ETrue(), ETrue())))
    outcomes = {expr: classify(expr) for expr in (e0, e1, e2, e3)}

    chains = select_chains(
        [
            MutationEdge(e0, e1, 1),
            MutationEdge(e1, e2, 2),
            MutationEdge(e2, e3, 3),
        ],
        outcomes,
        steps=4,
        per_kind=5,
    )

    assert chains == []
