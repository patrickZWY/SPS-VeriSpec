"""Emit elementary-form facts for the Datalog composition policy.

Mirrors the repo's extractor/Datalog split: Python resolves binding structure
(the equivalent of the ``resolved_*`` facts in base_facts.dl), and the Souffle
policy reasons over the resolved facts. For each composite expression we emit
its node/child/variable-reference structure so the policy can predict outcomes
purely from the elementary forms and their scoping.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

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
)


@dataclass
class ExprFacts:
    nodes: list[tuple[int, str]] = field(default_factory=list)  # (node_id, tag)
    children: list[tuple[int, str, int]] = field(default_factory=list)  # parent, slot, child
    # (node_id, name, binder_node_id, binder_kind) ; binder_node_id == -1 if unbound
    var_refs: list[tuple[int, str, int, str]] = field(default_factory=list)


def resolve_expr(expr: Expr) -> ExprFacts:
    """Number nodes pre-order and resolve every Var occurrence to its binder.

    A binder kind of ``"Lam"`` vs ``"Let"`` is what lets the policy distinguish
    always-failing lambda self-application from polymorphic let self-application.
    """
    out = ExprFacts()
    counter = [0]

    def fresh() -> int:
        nid = counter[0]
        counter[0] += 1
        return nid

    def walk(node: Expr, env: dict[str, tuple[int, str]]) -> int:
        nid = fresh()
        out.nodes.append((nid, expr_tag(node)))
        if isinstance(node, Var):
            binder: Optional[tuple[int, str]] = env.get(node.name)
            if binder is None:
                out.var_refs.append((nid, node.name, -1, "unbound"))
            else:
                out.var_refs.append((nid, node.name, binder[0], binder[1]))
        elif isinstance(node, (Lit, ETrue, EFalse)):
            pass
        elif isinstance(node, Lam):
            inner = dict(env)
            inner[node.var] = (nid, "Lam")
            out.children.append((nid, "body", walk(node.body, inner)))
        elif isinstance(node, App):
            out.children.append((nid, "fun", walk(node.fun, env)))
            out.children.append((nid, "arg", walk(node.arg, env)))
        elif isinstance(node, If):
            out.children.append((nid, "cond", walk(node.cond, env)))
            out.children.append((nid, "then", walk(node.then_branch, env)))
            out.children.append((nid, "else", walk(node.else_branch, env)))
        elif isinstance(node, Let):
            # `name` is bound only in the body, not the bound expression.
            out.children.append((nid, "bound", walk(node.bound, env)))
            inner = dict(env)
            inner[node.name] = (nid, "Let")
            out.children.append((nid, "body", walk(node.body, inner)))
        else:
            raise TypeError(f"Unknown expression node: {node!r}")
        return nid

    walk(expr, {})
    return out


def write_facts(expressions: list[Expr], facts_dir: Path) -> dict[str, Path]:
    """Write tab-separated Souffle .facts files for a list of expressions.

    Expression ids are the list indices, so callers can align Souffle output
    rows back to expressions by position.
    """
    facts_dir.mkdir(parents=True, exist_ok=True)
    node_rows: list[tuple[int, int, str]] = []
    child_rows: list[tuple[int, int, str, int]] = []
    var_rows: list[tuple[int, int, str, int, str]] = []

    for eid, expr in enumerate(expressions):
        ef = resolve_expr(expr)
        for nid, tag in ef.nodes:
            node_rows.append((eid, nid, tag))
        for parent, slot, child in ef.children:
            child_rows.append((eid, parent, slot, child))
        for nid, name, binder, kind in ef.var_refs:
            var_rows.append((eid, nid, name, binder, kind))

    paths = {
        "node": facts_dir / "node.facts",
        "child": facts_dir / "child.facts",
        "var_ref": facts_dir / "var_ref.facts",
    }
    _write_tsv(paths["node"], node_rows)
    _write_tsv(paths["child"], child_rows)
    _write_tsv(paths["var_ref"], var_rows)
    return paths


def _write_tsv(path: Path, rows: list[tuple]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerows(rows)
