from __future__ import annotations

import argparse
import ast
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable


EXCLUDED_DIRS = {"__pycache__", ".git", ".venv", "venv", "tests", "manual_testing"}

DATACLASS_OPTION_DEFAULTS: dict[str, str] = {
    "init": "true",
    "repr": "true",
    "eq": "true",
    "order": "false",
    "unsafe_hash": "false",
    "frozen": "false",
    "match_args": "true",
    "kw_only": "false",
    "slots": "false",
    "weakref_slot": "false",
}

SOUFFLE_SCHEMA: dict[str, tuple[str, ...]] = {
    "module": ("symbol",),
    "module_file": ("symbol", "symbol"),
    "imports": ("symbol", "symbol"),
    "import_alias": ("symbol", "symbol", "symbol"),
    "defines_class": ("symbol", "symbol"),
    "extends": ("symbol", "symbol", "symbol"),
    "resolved_extends": ("symbol", "symbol", "symbol", "symbol"),
    "dataclass": ("symbol", "symbol", "number", "number"),
    "dataclass_option": ("symbol", "symbol", "symbol", "symbol", "number"),
    "dataclass_field": (
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "number",
        "number",
        "symbol",
        "number",
        "number",
    ),
    "dataclass_field_default_factory": ("symbol", "symbol", "symbol", "symbol"),
    "dataclass_field_type_ref": ("symbol", "symbol", "symbol", "symbol"),
    "resolved_dataclass_field_type_ref": (
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "symbol",
    ),
    "method_of_class": ("symbol", "symbol", "symbol"),
    "function_param": ("symbol", "symbol", "symbol", "symbol", "number", "number"),
    "function_param_type_ref": ("symbol", "symbol", "symbol", "symbol"),
    "resolved_param_type_ref": ("symbol", "symbol", "symbol", "symbol", "symbol"),
    "function_return_type": ("symbol", "symbol", "symbol", "number"),
    "function_return_type_ref": ("symbol", "symbol", "symbol"),
    "resolved_return_type_ref": ("symbol", "symbol", "symbol", "symbol"),
    "returns_dataclass": ("symbol", "symbol", "symbol", "number"),
    "resolved_returns_dataclass": (
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "number",
    ),
    "attribute_read": ("symbol", "symbol", "symbol", "symbol", "number"),
    "attribute_write": ("symbol", "symbol", "symbol", "symbol", "number"),
    "local_alias": ("symbol", "symbol", "symbol", "symbol", "number"),
    "loop_iterates": ("symbol", "symbol", "symbol", "symbol", "number"),
    "comprehension_iterates": ("symbol", "symbol", "symbol", "symbol", "number"),
    "comprehension_filter": ("symbol", "symbol", "symbol", "symbol", "number"),
    "assertion": ("symbol", "symbol", "symbol", "number"),
    "branch_condition": ("symbol", "symbol", "symbol", "number"),
    "condition_atom": ("symbol", "symbol", "symbol", "symbol", "number"),
    "with_resource": ("symbol", "symbol", "symbol", "symbol", "number"),
    "await_expr": ("symbol", "symbol", "symbol", "number"),
    "yield_value": ("symbol", "symbol", "symbol", "number"),
    "match_subject": ("symbol", "symbol", "symbol", "number"),
    "match_case": ("symbol", "symbol", "symbol", "symbol", "number"),
    "subscript_access": ("symbol", "symbol", "symbol", "symbol", "number"),
    "handles_exception": ("symbol", "symbol", "symbol", "number"),
    "raises_exception": ("symbol", "symbol", "symbol", "number"),
    "defines_function": ("symbol", "symbol", "number"),
    "function_name": ("symbol", "symbol", "symbol"),
    "calls": ("symbol", "symbol", "symbol", "number"),
    "call_protocol_event": (
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "number",
    ),
    "call_target": (
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "number",
    ),
    "call_argument": (
        "symbol",
        "symbol",
        "symbol",
        "number",
        "symbol",
        "symbol",
        "number",
    ),
    "return_call": ("symbol", "symbol", "symbol", "number"),
    "resolved_return_call": ("symbol", "symbol", "symbol", "symbol", "number"),
    "return_local": ("symbol", "symbol", "symbol", "number"),
    "instantiates": ("symbol", "symbol", "symbol", "number"),
    "resolved_instantiates": ("symbol", "symbol", "symbol", "symbol", "number"),
    "reads_env_var": ("symbol", "symbol", "symbol", "number"),
    "constructor_kwarg": ("symbol", "symbol", "symbol", "symbol", "symbol", "number"),
    "return_constructor_kwarg": (
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "number",
    ),
    "field_flows_to_constructor_arg": (
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "number",
    ),
    "condition_reads_attribute": ("symbol", "symbol", "symbol", "symbol", "number"),
    "returns_none": ("symbol", "symbol", "number"),
    "returns_literal": ("symbol", "symbol", "symbol", "symbol", "number"),
    "method_override": ("symbol", "symbol", "symbol", "symbol", "symbol"),
    "local_depends_on_field": (
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "number",
    ),
    "call_result_assigned": ("symbol", "symbol", "symbol", "symbol", "number"),
    "resolved_call_result_assigned": (
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "number",
    ),
    "local_dataclass_value": ("symbol", "symbol", "symbol", "symbol", "number"),
    "resolved_local_dataclass_value": (
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "number",
    ),
    "literal_assigned": ("symbol", "symbol", "symbol", "symbol", "symbol", "number"),
    "constructor_arg_literal": (
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "number",
    ),
    "return_constructor_arg_literal": (
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "number",
    ),
    "constructor_arg_string_composition": (
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "number",
    ),
    "return_arg_string_composition": (
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "number",
    ),
    "numeric_literal": ("symbol", "symbol", "number", "number"),
    "numeric_assignment": ("symbol", "symbol", "symbol", "number", "number"),
    "len_call": ("symbol", "symbol", "symbol", "number"),
    "numeric_compare": (
        "symbol",
        "symbol",
        "symbol",
        "symbol",
        "number",
        "number",
    ),
    "string_slice_upper_bound": ("symbol", "symbol", "symbol", "number", "number"),
}


@dataclass(frozen=True, order=True)
class Fact:
    predicate: str
    args: tuple[str | int, ...]

    def render(self) -> str:
        rendered_args = ", ".join(_render_arg(arg) for arg in self.args)
        return f"{self.predicate}({rendered_args})."

    def to_souffle_row(self) -> str:
        return "\t".join(_render_souffle_value(arg) for arg in self.args)


def _render_arg(value: str | int) -> str:
    if isinstance(value, int):
        return str(value)
    return json.dumps(value)


def _render_souffle_value(value: str | int) -> str:
    if isinstance(value, int):
        return str(value)
    return value.replace("\t", "\\t").replace("\n", "\\n")


def module_name_for_path(relative_path: Path) -> str:
    without_suffix = relative_path.with_suffix("")
    parts = list(without_suffix.parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else "<root>"


def iter_python_files(root: Path, include_tests: bool = False) -> Iterable[Path]:
    for path in sorted(root.rglob("*.py")):
        relative_parts = set(path.relative_to(root).parts)
        if not include_tests and relative_parts & EXCLUDED_DIRS:
            continue
        yield path


class PythonFactExtractor(ast.NodeVisitor):
    def __init__(self, module_name: str):
        self.module_name = module_name
        self.facts: set[Fact] = set()
        self._qualname_stack: list[str] = []
        self._local_field_deps_stack: list[dict[str, set[tuple[str, str]]]] = []
        self._local_dataclass_values_stack: list[dict[str, str]] = []
        self._local_numeric_values_stack: list[dict[str, int]] = []
        self._local_alias_stack: list[dict[str, str]] = []

    def extract(self, tree: ast.AST, relative_path: str) -> list[Fact]:
        self.facts.add(Fact("module", (self.module_name,)))
        self.facts.add(Fact("module_file", (self.module_name, relative_path)))
        self.visit(tree)
        return sorted(self.facts)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.facts.add(Fact("imports", (self.module_name, alias.name)))
            self.facts.add(
                Fact(
                    "import_alias",
                    (
                        self.module_name,
                        alias.asname or alias.name.split(".")[0],
                        alias.name,
                    ),
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            target = f"{module}.{alias.name}" if module else alias.name
            self.facts.add(Fact("imports", (self.module_name, target)))
            self.facts.add(
                Fact(
                    "import_alias",
                    (self.module_name, alias.asname or alias.name, target),
                )
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        class_name = self._push_name(node.name)
        self.facts.add(Fact("defines_class", (self.module_name, class_name)))
        for base in node.bases:
            rendered_base = self._render_expr(base)
            if rendered_base:
                self.facts.add(
                    Fact("extends", (self.module_name, class_name, rendered_base))
                )

        is_dataclass, dataclass_options = self._extract_dataclass_metadata(node)
        if is_dataclass:
            is_frozen = 1 if dataclass_options["frozen"][0] == "true" else 0
            self.facts.add(
                Fact("dataclass", (self.module_name, class_name, is_frozen, node.lineno))
            )
            for option_name, (option_value, is_explicit) in dataclass_options.items():
                self.facts.add(
                    Fact(
                        "dataclass_option",
                        (
                            self.module_name,
                            class_name,
                            option_name,
                            option_value,
                            is_explicit,
                        ),
                    )
                )
            for position, field_node in enumerate(
                self._iter_dataclass_fields(node), start=1
            ):
                field_name, annotation, value, line = field_node
                type_repr = self._annotation_repr(annotation)
                is_optional = self._is_optional_annotation(annotation)
                has_default, default_kind, default_factory = self._analyze_field_value(
                    value
                )
                self.facts.add(
                    Fact(
                        "dataclass_field",
                        (
                            self.module_name,
                            class_name,
                            field_name,
                            type_repr,
                            is_optional,
                            has_default,
                            default_kind,
                            position,
                            line,
                        ),
                    )
                )
                if default_factory:
                    self.facts.add(
                        Fact(
                            "dataclass_field_default_factory",
                            (
                                self.module_name,
                                class_name,
                                field_name,
                                default_factory,
                            ),
                        )
                    )
                for type_ref in sorted(self._iter_annotation_type_refs(annotation)):
                    self.facts.add(
                        Fact(
                            "dataclass_field_type_ref",
                            (self.module_name, class_name, field_name, type_ref),
                        )
                    )

        base_names = [
            rendered_base
            for base in node.bases
            if (rendered_base := self._render_expr(base))
        ]
        method_names = [
            stmt.name
            for stmt in node.body
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        for base_name in base_names:
            for method_name in method_names:
                self.facts.add(
                    Fact(
                        "method_override",
                        (
                            self.module_name,
                            class_name,
                            base_name.split(".")[-1],
                            method_name,
                            f"{class_name}.{method_name}",
                        ),
                    )
                )

        self.generic_visit(node)
        self._qualname_stack.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def visit_Call(self, node: ast.Call) -> None:
        caller = self._current_callable()
        callee = self._render_expr(node.func)
        if callee:
            self.facts.add(Fact("calls", (self.module_name, caller, callee, node.lineno)))
            self._add_call_protocol_event_facts(caller, callee, node.lineno)
            self._add_call_argument_facts(caller, callee, node)
            class_name = self._class_like_name(callee)
            if class_name:
                self.facts.add(
                    Fact(
                        "instantiates",
                        (self.module_name, caller, class_name, node.lineno),
                    )
                )
                self._add_constructor_kwarg_facts(caller, class_name, node)

        env_var = self._extract_env_var(node)
        if env_var:
            self.facts.add(
                Fact("reads_env_var", (self.module_name, caller, env_var, node.lineno))
            )

        if callee == "len" and node.args:
            self.facts.add(
                Fact(
                    "len_call",
                    (
                        self.module_name,
                        caller,
                        self._expression_repr(node.args[0]),
                        node.lineno,
                    ),
                )
            )

        self.generic_visit(node)

    def visit_Compare(self, node: ast.Compare) -> None:
        caller = self._current_callable()
        for op, comparator in zip(node.ops, node.comparators):
            left_expr = self._bounded_expr_repr(node.left)
            op_name = self._compare_op_name(op)
            numeric_value = self._numeric_bound_value(comparator)
            if left_expr and op_name and numeric_value is not None:
                self.facts.add(
                    Fact(
                        "numeric_compare",
                        (
                            self.module_name,
                            caller,
                            left_expr,
                            op_name,
                            numeric_value,
                            node.lineno,
                        ),
                    )
                )

            right_expr = self._bounded_expr_repr(comparator)
            reverse_op = self._reverse_compare_op_name(op)
            left_value = self._numeric_bound_value(node.left)
            if right_expr and reverse_op and left_value is not None:
                self.facts.add(
                    Fact(
                        "numeric_compare",
                        (
                            self.module_name,
                            caller,
                            right_expr,
                            reverse_op,
                            left_value,
                            node.lineno,
                        ),
                    )
                )
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        caller = self._current_callable()
        target = self._render_expr(node.value)
        if target:
            self.facts.add(
                Fact(
                    "subscript_access",
                    (
                        self.module_name,
                        caller,
                        self._resolve_local_alias(target),
                        self._subscript_index_kind(node.slice),
                        node.lineno,
                    ),
                )
            )
        upper_bound = self._slice_upper_bound(node.slice)
        if target and upper_bound is not None:
            self.facts.add(
                Fact(
                    "string_slice_upper_bound",
                    (self.module_name, caller, target, upper_bound, node.lineno),
                )
            )
        self.generic_visit(node)

    def visit_For(self, node: ast.For) -> None:
        self._record_loop_iterates(node.target, node.iter, node.lineno)
        self.generic_visit(node)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
        self._record_loop_iterates(node.target, node.iter, node.lineno)
        self.generic_visit(node)

    def visit_ListComp(self, node: ast.ListComp) -> None:
        self._record_comprehension(node)
        self.generic_visit(node)

    def visit_SetComp(self, node: ast.SetComp) -> None:
        self._record_comprehension(node)
        self.generic_visit(node)

    def visit_DictComp(self, node: ast.DictComp) -> None:
        self._record_comprehension(node)
        self.generic_visit(node)

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> None:
        self._record_comprehension(node)
        self.generic_visit(node)

    def visit_Assert(self, node: ast.Assert) -> None:
        caller = self._current_callable()
        self.facts.add(
            Fact(
                "assertion",
                (self.module_name, caller, self._expression_repr(node.test), node.lineno),
            )
        )
        self._add_condition_read_facts(node.test)
        self.generic_visit(node)

    def visit_With(self, node: ast.With) -> None:
        self._record_with_resources(node.items, node.lineno)
        self.generic_visit(node)

    def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
        self._record_with_resources(node.items, node.lineno)
        self.generic_visit(node)

    def visit_Await(self, node: ast.Await) -> None:
        self.facts.add(
            Fact(
                "await_expr",
                (
                    self.module_name,
                    self._current_callable(),
                    self._expression_repr(node.value),
                    node.lineno,
                ),
            )
        )
        self.generic_visit(node)

    def visit_Yield(self, node: ast.Yield) -> None:
        self._record_yield(node.value, node.lineno)
        self.generic_visit(node)

    def visit_YieldFrom(self, node: ast.YieldFrom) -> None:
        self._record_yield(node.value, node.lineno)
        self.generic_visit(node)

    def visit_Match(self, node: ast.Match) -> None:
        caller = self._current_callable()
        self.facts.add(
            Fact(
                "match_subject",
                (
                    self.module_name,
                    caller,
                    self._resolve_aliases_in_expr(self._expression_repr(node.subject)),
                    node.lineno,
                ),
            )
        )
        for case in node.cases:
            guard = self._expression_repr(case.guard) if case.guard is not None else ""
            guard = self._resolve_aliases_in_expr(guard) if guard else ""
            self.facts.add(
                Fact(
                    "match_case",
                    (
                        self.module_name,
                        caller,
                        self._pattern_kind(case.pattern),
                        guard,
                        case.pattern.lineno,
                    ),
                )
            )
            if case.guard is not None:
                self._add_condition_read_facts(case.guard)
        self.generic_visit(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        qualname = self._push_name(node.name)
        self.facts.add(
            Fact(
                "defines_function",
                (self.module_name, qualname, self._function_arity(node.args)),
            )
        )
        self.facts.add(Fact("function_name", (self.module_name, qualname, node.name)))
        if len(self._qualname_stack) >= 2:
            self.facts.add(
                Fact(
                    "method_of_class",
                    (self.module_name, self._qualname_stack[-2], qualname),
                )
            )
        for position, arg in enumerate(
            [*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs], start=1
        ):
            type_repr = self._annotation_repr(arg.annotation)
            self.facts.add(
                Fact(
                    "function_param",
                    (
                        self.module_name,
                        qualname,
                        arg.arg,
                        type_repr,
                        position,
                        arg.lineno,
                    ),
                )
            )
            for type_ref in sorted(self._iter_annotation_type_refs(arg.annotation)):
                self.facts.add(
                    Fact(
                        "function_param_type_ref",
                        (self.module_name, qualname, arg.arg, type_ref),
                    )
                )
        if node.args.vararg is not None:
            type_repr = self._annotation_repr(node.args.vararg.annotation)
            self.facts.add(
                Fact(
                    "function_param",
                    (
                        self.module_name,
                        qualname,
                        node.args.vararg.arg,
                        type_repr,
                        -1,
                        node.args.vararg.lineno,
                    ),
                )
            )
        if node.args.kwarg is not None:
            type_repr = self._annotation_repr(node.args.kwarg.annotation)
            self.facts.add(
                Fact(
                    "function_param",
                    (
                        self.module_name,
                        qualname,
                        node.args.kwarg.arg,
                        type_repr,
                        -2,
                        node.args.kwarg.lineno,
                    ),
                )
            )
        if node.returns is not None:
            return_type = self._annotation_repr(node.returns)
            self.facts.add(
                Fact(
                    "function_return_type",
                    (self.module_name, qualname, return_type, node.returns.lineno),
                )
            )
            for type_ref in sorted(self._iter_annotation_type_refs(node.returns)):
                self.facts.add(
                    Fact(
                        "function_return_type_ref",
                        (self.module_name, qualname, type_ref),
                    )
                )
        self._local_field_deps_stack.append({})
        self._local_dataclass_values_stack.append({})
        self._local_numeric_values_stack.append({})
        self._local_alias_stack.append({})
        self.generic_visit(node)
        self._local_alias_stack.pop()
        self._local_numeric_values_stack.pop()
        self._local_dataclass_values_stack.pop()
        self._local_field_deps_stack.pop()
        self._qualname_stack.pop()

    def _push_name(self, name: str) -> str:
        self._qualname_stack.append(name)
        return ".".join(self._qualname_stack)

    def _current_callable(self) -> str:
        return ".".join(self._qualname_stack) if self._qualname_stack else "<module>"

    @staticmethod
    def _function_arity(args: ast.arguments) -> int:
        arity = len(args.posonlyargs) + len(args.args) + len(args.kwonlyargs)
        if args.vararg is not None:
            arity += 1
        if args.kwarg is not None:
            arity += 1
        return arity

    def _render_expr(self, node: ast.AST) -> str | None:
        match node:
            case ast.Name(id=name):
                return name
            case ast.Attribute(value=value, attr=attr):
                return f"{parent}.{attr}" if (parent := self._render_expr(value)) else attr
            case ast.Call(func=func):
                return self._render_expr(func)
            case ast.Subscript(value=value):
                return self._render_expr(value)
            case ast.Constant(value=str(value)):
                return value
        return None

    def visit_Attribute(self, node: ast.Attribute) -> None:
        owner = self._render_expr(node.value)
        caller = self._current_callable()
        if owner:
            owner = self._resolve_local_alias(owner)
            if isinstance(node.ctx, ast.Load):
                self.facts.add(
                    Fact(
                        "attribute_read",
                        (self.module_name, caller, owner, node.attr, node.lineno),
                    )
                )
            elif isinstance(node.ctx, ast.Store):
                self.facts.add(
                    Fact(
                        "attribute_write",
                        (self.module_name, caller, owner, node.attr, node.lineno),
                    )
                )
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        self._record_assignment_targets(node.targets, node.value, node.lineno)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        self._record_assignment_targets([node.target], node.value, node.lineno)
        self.generic_visit(node)

    def visit_Return(self, node: ast.Return) -> None:
        caller = self._current_callable()
        if node.value is not None:
            if isinstance(node.value, ast.Call):
                callee = self._render_expr(node.value.func)
                if callee:
                    self.facts.add(
                        Fact("return_call", (self.module_name, caller, callee, node.lineno))
                    )
            elif isinstance(node.value, ast.Name):
                self.facts.add(
                    Fact(
                        "return_local",
                        (self.module_name, caller, node.value.id, node.lineno),
                    )
                )
            class_name = self._returned_class_name(node.value)
            if class_name:
                self.facts.add(
                    Fact(
                        "returns_dataclass",
                        (self.module_name, caller, class_name, node.lineno),
                    )
                )
                if isinstance(node.value, ast.Call):
                    self._add_return_constructor_kwarg_facts(caller, class_name, node.value)
            elif self._is_none_literal(node.value):
                self.facts.add(Fact("returns_none", (self.module_name, caller, node.lineno)))
            else:
                literal = self._literal_return(node.value)
                if literal:
                    literal_kind, literal_value = literal
                    self.facts.add(
                        Fact(
                            "returns_literal",
                            (
                                self.module_name,
                                caller,
                                literal_kind,
                                literal_value,
                                node.lineno,
                            ),
                        )
                    )
        self.generic_visit(node)

    def visit_If(self, node: ast.If) -> None:
        self._record_branch_condition(node.test, node.lineno)
        self._add_condition_read_facts(node.test)
        self.generic_visit(node)

    def visit_IfExp(self, node: ast.IfExp) -> None:
        self._record_branch_condition(node.test, node.lineno)
        self._add_condition_read_facts(node.test)
        self.generic_visit(node)

    def visit_While(self, node: ast.While) -> None:
        self._record_branch_condition(node.test, node.lineno)
        self._add_condition_read_facts(node.test)
        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        caller = self._current_callable()
        exception_type = self._render_expr(node.type) if node.type is not None else "*"
        self.facts.add(
            Fact(
                "handles_exception",
                (self.module_name, caller, exception_type or "*", node.lineno),
            )
        )
        self.generic_visit(node)

    def visit_Raise(self, node: ast.Raise) -> None:
        caller = self._current_callable()
        exception_type = (
            self._render_expr(node.exc)
            if node.exc is not None
            else "reraise"
        )
        self.facts.add(
            Fact(
                "raises_exception",
                (self.module_name, caller, exception_type or "unknown", node.lineno),
            )
        )
        self.generic_visit(node)

    def _annotation_repr(self, node: ast.AST | None) -> str:
        if node is None:
            return ""
        try:
            return ast.unparse(node)
        except Exception:
            rendered = self._render_expr(node)
            return rendered or ""

    @staticmethod
    def _class_like_name(callee: str) -> str | None:
        candidate = callee.split(".")[-1]
        if not candidate:
            return None
        return candidate if candidate[:1].isupper() else None

    def _extract_env_var(self, node: ast.Call) -> str | None:
        if not node.args:
            return None

        first_arg = node.args[0]
        if not isinstance(first_arg, ast.Constant) or not isinstance(
            first_arg.value, str
        ):
            return None

        callee = self._render_expr(node.func)
        if callee in {"os.getenv", "os.environ.get"}:
            return first_arg.value
        return None

    def _extract_dataclass_metadata(
        self, node: ast.ClassDef
    ) -> tuple[bool, dict[str, tuple[str, int]]]:
        for decorator in node.decorator_list:
            callee = decorator
            options = {
                name: (default_value, 0)
                for name, default_value in DATACLASS_OPTION_DEFAULTS.items()
            }
            if isinstance(decorator, ast.Call):
                callee = decorator.func
                for keyword in decorator.keywords:
                    if keyword.arg in DATACLASS_OPTION_DEFAULTS:
                        options[keyword.arg] = (
                            self._dataclass_option_value(keyword.value),
                            1,
                        )

            rendered = self._render_expr(callee)
            if rendered and rendered.split(".")[-1] == "dataclass":
                return True, options
        return False, {}

    def _dataclass_option_value(self, node: ast.AST) -> str:
        if isinstance(node, ast.Constant) and isinstance(node.value, bool):
            return "true" if node.value else "false"
        rendered = self._render_expr(node)
        return rendered or "<unknown>"

    def _iter_dataclass_fields(
        self, node: ast.ClassDef
    ) -> Iterable[tuple[str, ast.AST | None, ast.AST | None, int]]:
        for stmt in node.body:
            if not isinstance(stmt, ast.AnnAssign):
                continue
            if not isinstance(stmt.target, ast.Name):
                continue
            if self._is_classvar_annotation(stmt.annotation):
                continue
            yield stmt.target.id, stmt.annotation, stmt.value, stmt.lineno

    def _is_classvar_annotation(self, node: ast.AST | None) -> bool:
        if node is None:
            return False
        if isinstance(node, ast.Subscript):
            return self._last_name(self._render_expr(node.value)) == "ClassVar"
        rendered = self._render_expr(node)
        return self._last_name(rendered) == "ClassVar"

    def _is_optional_annotation(self, node: ast.AST | None) -> int:
        if node is None:
            return 0
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return int(
                self._contains_none_annotation(node.left)
                or self._contains_none_annotation(node.right)
            )
        if isinstance(node, ast.Subscript):
            if self._last_name(self._render_expr(node.value)) == "Optional":
                return 1
            return self._is_optional_annotation(node.slice)
        return 0

    def _contains_none_annotation(self, node: ast.AST) -> bool:
        match node:
            case ast.Constant(value=None) | ast.Name(id="None"):
                return True
            case ast.BinOp(left=left, op=ast.BitOr(), right=right):
                return self._contains_none_annotation(
                    left
                ) or self._contains_none_annotation(right)
            case _:
                return False

    def _analyze_field_value(
        self, value: ast.AST | None
    ) -> tuple[int, str, str | None]:
        if value is None:
            return 0, "missing", None

        if isinstance(value, ast.Call):
            callee = self._render_expr(value.func)
            if callee and callee.split(".")[-1] == "field":
                default_factory = None
                default_value = None
                for keyword in value.keywords:
                    if keyword.arg == "default_factory":
                        default_factory = self._render_expr(keyword.value) or ast.unparse(
                            keyword.value
                        )
                    if keyword.arg == "default":
                        default_value = keyword.value
                if default_factory:
                    return 1, "factory", default_factory
                if default_value is not None:
                    return 1, self._literal_default_kind(default_value), None
                return 0, "field_call", None

        return 1, self._literal_default_kind(value), None

    @staticmethod
    def _literal_default_kind(node: ast.AST) -> str:
        if isinstance(node, (ast.Constant, ast.List, ast.Tuple, ast.Set, ast.Dict)):
            return "literal"
        return "expression"

    def _iter_annotation_type_refs(self, node: ast.AST | None) -> set[str]:
        if node is None:
            return set()

        return {
            type_ref
            for child in ast.walk(node)
            if (type_ref := self._annotation_type_ref(child)) is not None
        }

    def _returned_class_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Call):
            return self._class_like_name(self._render_expr(node.func) or "")
        return None

    def _add_constructor_kwarg_facts(
        self,
        caller: str,
        class_name: str,
        node: ast.Call,
    ) -> None:
        for keyword in node.keywords:
            if keyword.arg is None:
                continue
            source_expr = self._expression_repr(keyword.value)
            self.facts.add(
                Fact(
                    "constructor_kwarg",
                    (
                        self.module_name,
                        caller,
                        class_name,
                        keyword.arg,
                        source_expr,
                        keyword.value.lineno,
                    ),
                )
            )
            literal = self._literal_value(keyword.value)
            if literal:
                literal_kind, literal_value = literal
                self.facts.add(
                    Fact(
                        "constructor_arg_literal",
                        (
                            self.module_name,
                            caller,
                            class_name,
                            keyword.arg,
                            literal_kind,
                            literal_value,
                            keyword.value.lineno,
                        ),
                    )
                )
            string_kind = self._string_composition_kind(keyword.value)
            if string_kind:
                self.facts.add(
                    Fact(
                        "constructor_arg_string_composition",
                        (
                            self.module_name,
                            caller,
                            class_name,
                            keyword.arg,
                            string_kind,
                            keyword.value.lineno,
                        ),
                    )
                )
            numeric_literal = self._numeric_literal(keyword.value)
            if numeric_literal is not None:
                self.facts.add(
                    Fact(
                        "numeric_literal",
                        (
                            self.module_name,
                            caller,
                            numeric_literal,
                            keyword.value.lineno,
                        ),
                    )
                )
            self._add_expression_numeric_facts(caller, keyword.value)
            field_flow = self._direct_attribute_flow(keyword.value)
            if field_flow:
                source_param, source_field = field_flow
                self.facts.add(
                    Fact(
                        "field_flows_to_constructor_arg",
                        (
                            self.module_name,
                            caller,
                            source_param,
                            source_field,
                            class_name,
                            keyword.arg,
                            keyword.value.lineno,
                        ),
                    )
                )
            for source_param, source_field in sorted(
                self._expression_field_deps(keyword.value)
            ):
                self.facts.add(
                    Fact(
                        "field_flows_to_constructor_arg",
                        (
                            self.module_name,
                            caller,
                            source_param,
                            source_field,
                            class_name,
                            keyword.arg,
                            keyword.value.lineno,
                        ),
                        )
                    )

    def _add_call_argument_facts(
        self,
        caller: str,
        callee: str,
        node: ast.Call,
    ) -> None:
        for position, argument in enumerate(node.args, start=1):
            self.facts.add(
                Fact(
                    "call_argument",
                    (
                        self.module_name,
                        caller,
                        callee,
                        position,
                        "",
                        self._expression_repr(argument),
                        argument.lineno,
                    ),
                )
            )
        for keyword in node.keywords:
            if keyword.arg is None:
                continue
            self.facts.add(
                Fact(
                    "call_argument",
                    (
                        self.module_name,
                        caller,
                        callee,
                        0,
                        keyword.arg,
                        self._expression_repr(keyword.value),
                        keyword.value.lineno,
                    ),
                )
            )

    def _add_call_protocol_event_facts(
        self,
        caller: str,
        callee: str,
        line: int,
    ) -> None:
        event_kind = self._call_protocol_event_kind(callee)
        if event_kind is None:
            return
        receiver = callee.rsplit(".", 1)[0] if "." in callee else ""
        self.facts.add(
            Fact(
                "call_protocol_event",
                (self.module_name, caller, receiver, event_kind, callee, line),
            )
        )

    def _add_return_constructor_kwarg_facts(
        self,
        caller: str,
        class_name: str,
        node: ast.Call,
    ) -> None:
        for keyword in node.keywords:
            if keyword.arg is None:
                continue
            self.facts.add(
                Fact(
                    "return_constructor_kwarg",
                    (
                        self.module_name,
                        caller,
                        class_name,
                        keyword.arg,
                        self._expression_repr(keyword.value),
                        keyword.value.lineno,
                    ),
                )
            )
            literal = self._literal_value(keyword.value)
            if literal:
                literal_kind, literal_value = literal
                self.facts.add(
                    Fact(
                        "return_constructor_arg_literal",
                        (
                            self.module_name,
                            caller,
                            class_name,
                            keyword.arg,
                            literal_kind,
                            literal_value,
                            keyword.value.lineno,
                        ),
                    )
                )
            string_kind = self._string_composition_kind(keyword.value)
            if string_kind:
                self.facts.add(
                    Fact(
                        "return_arg_string_composition",
                        (
                            self.module_name,
                            caller,
                            class_name,
                            keyword.arg,
                            string_kind,
                            keyword.value.lineno,
                        ),
                    )
                )
            numeric_literal = self._numeric_literal(keyword.value)
            if numeric_literal is not None:
                self.facts.add(
                    Fact(
                        "numeric_literal",
                        (
                            self.module_name,
                            caller,
                            numeric_literal,
                            keyword.value.lineno,
                        ),
                    )
                )
            self._add_expression_numeric_facts(caller, keyword.value)

    def _add_condition_read_facts(self, node: ast.AST) -> None:
        caller = self._current_callable()
        for child in ast.walk(node):
            if not isinstance(child, ast.Attribute):
                continue
            owner = self._render_expr(child.value)
            if owner:
                self.facts.add(
                    Fact(
                        "condition_reads_attribute",
                        (
                            self.module_name,
                            caller,
                            self._resolve_local_alias(owner),
                            child.attr,
                            child.lineno,
                        ),
                        )
                    )

    def _record_branch_condition(self, node: ast.AST, line: int) -> None:
        caller = self._current_callable()
        expression = self._resolve_aliases_in_expr(self._expression_repr(node))
        self.facts.add(
            Fact("branch_condition", (self.module_name, caller, expression, line))
        )
        for atom, state in sorted(self._condition_atoms(node)):
            self.facts.add(
                Fact(
                    "condition_atom",
                    (
                        self.module_name,
                        caller,
                        self._resolve_aliases_in_expr(atom),
                        state,
                        line,
                    ),
                )
            )

    def _condition_atoms(self, node: ast.AST, polarity: bool = True) -> set[tuple[str, str]]:
        atoms: set[tuple[str, str]] = set()
        match node:
            case ast.BoolOp(values=values):
                for value in values:
                    atoms.update(self._condition_atoms(value, polarity))
            case ast.UnaryOp(op=ast.Not(), operand=operand):
                atoms.update(self._condition_atoms(operand, not polarity))
            case ast.Compare(left=left, ops=ops, comparators=comparators):
                left_expr = self._render_expr(left)
                if left_expr:
                    for op, comparator in zip(ops, comparators):
                        if self._is_none_literal(comparator):
                            if isinstance(op, ast.Is):
                                atoms.add((left_expr, "is_none" if polarity else "non_null"))
                            elif isinstance(op, (ast.IsNot, ast.NotEq)):
                                atoms.add((left_expr, "non_null" if polarity else "is_none"))
                            elif isinstance(op, ast.Eq):
                                atoms.add((left_expr, "is_none" if polarity else "non_null"))
            case ast.Name() | ast.Attribute():
                rendered = self._render_expr(node)
                if rendered:
                    atoms.add((rendered, "truthy" if polarity else "falsy"))
            case ast.Call():
                rendered = self._expression_repr(node)
                atoms.add((rendered, "truthy" if polarity else "falsy"))
            case _:
                rendered = self._render_expr(node)
                if rendered:
                    atoms.add((rendered, "truthy" if polarity else "falsy"))
        return atoms

    @staticmethod
    def _call_protocol_event_kind(callee: str) -> str | None:
        name = callee.rsplit(".", 1)[-1]
        if name[:1].isupper():
            return None
        normalized = name.lower().lstrip("_")
        if normalized in {"authenticate", "login", "connect", "account_verify_credentials"}:
            return "authenticate"
        if normalized.startswith(("validate", "ensure", "check")):
            return "validate"
        if normalized in {"publish", "send", "upload", "status_post", "media_post"}:
            return "publish"
        if normalized.endswith("_publish"):
            return "publish"
        if normalized in {"open", "acquire", "start"}:
            return "open"
        if normalized in {"close", "release", "stop", "logout"}:
            return "close"
        return None

    def _expression_repr(self, node: ast.AST) -> str:
        try:
            return ast.unparse(node)
        except Exception:
            return self._render_expr(node) or "<expr>"

    def _direct_attribute_flow(self, node: ast.AST) -> tuple[str, str] | None:
        match node:
            case ast.Attribute(value=ast.Name(id=owner), attr=field_name):
                return owner, field_name
            case _:
                return None

    def _record_assignment_targets(
        self,
        targets: list[ast.AST],
        value: ast.AST | None,
        line: int,
    ) -> None:
        if not self._local_field_deps_stack:
            return
        if value is None:
            return

        caller = self._current_callable()
        field_deps = self._expression_field_deps(value)
        constructed_class = self._returned_class_name(value)
        callee = self._render_expr(value.func) if isinstance(value, ast.Call) else None
        callee_name = callee.split(".")[-1] if callee else None
        literal = self._literal_value(value)
        numeric_literal = self._numeric_literal(value)
        alias_target = self._alias_target(value)
        self._add_expression_numeric_facts(caller, value)

        for target in targets:
            for local_name in self._iter_assignment_target_names(target):
                if alias_target and alias_target != local_name:
                    resolved_alias = self._resolve_local_alias(alias_target)
                    self._set_local_alias(local_name, resolved_alias)
                    self.facts.add(
                        Fact(
                            "local_alias",
                            (
                                self.module_name,
                                caller,
                                local_name,
                                resolved_alias,
                                line,
                            ),
                        )
                    )
                if literal:
                    literal_kind, literal_value = literal
                    self.facts.add(
                        Fact(
                            "literal_assigned",
                            (
                                self.module_name,
                                caller,
                                local_name,
                                literal_kind,
                                literal_value,
                                line,
                            ),
                        )
                    )
                if numeric_literal is not None:
                    self._set_numeric_assignment(local_name, numeric_literal)
                    self.facts.add(
                        Fact(
                            "numeric_assignment",
                            (
                                self.module_name,
                                caller,
                                local_name,
                                numeric_literal,
                                line,
                            ),
                        )
                    )
                    self.facts.add(
                        Fact(
                            "numeric_literal",
                            (
                                self.module_name,
                                caller,
                                numeric_literal,
                                line,
                            ),
                        )
                    )
                if field_deps:
                    self._set_local_field_deps(local_name, field_deps)
                    for source_param, source_field in sorted(field_deps):
                        self.facts.add(
                            Fact(
                                "local_depends_on_field",
                                (
                                    self.module_name,
                                    caller,
                                    local_name,
                                    source_param,
                                    source_field,
                                    line,
                                ),
                            )
                        )

                if constructed_class:
                    self._set_local_dataclass_value(local_name, constructed_class)
                    self.facts.add(
                        Fact(
                            "local_dataclass_value",
                            (
                                self.module_name,
                                caller,
                                local_name,
                                constructed_class,
                                line,
                            ),
                        )
                    )

                if callee_name:
                    self.facts.add(
                        Fact(
                            "call_result_assigned",
                            (self.module_name, caller, local_name, callee_name, line),
                        )
                    )

    def _iter_assignment_target_names(self, node: ast.AST) -> Iterable[str]:
        if isinstance(node, ast.Name):
            yield node.id
            return
        if isinstance(node, (ast.Tuple, ast.List)):
            for element in node.elts:
                yield from self._iter_assignment_target_names(element)

    def _record_loop_iterates(
        self,
        target: ast.AST,
        iterator: ast.AST,
        line: int,
    ) -> None:
        caller = self._current_callable()
        iter_expr = self._expression_repr(iterator)
        for target_name in self._iter_assignment_target_names(target):
            self.facts.add(
                Fact(
                    "loop_iterates",
                    (
                        self.module_name,
                        caller,
                        target_name,
                        self._resolve_aliases_in_expr(iter_expr),
                        line,
                    ),
                )
            )

    def _record_comprehension(
        self,
        node: ast.ListComp | ast.SetComp | ast.DictComp | ast.GeneratorExp,
    ) -> None:
        caller = self._current_callable()
        for generator in node.generators:
            iter_expr = self._resolve_aliases_in_expr(self._expression_repr(generator.iter))
            for target_name in self._iter_assignment_target_names(generator.target):
                self.facts.add(
                    Fact(
                        "comprehension_iterates",
                        (
                            self.module_name,
                            caller,
                            target_name,
                            iter_expr,
                            generator.iter.lineno,
                        ),
                    )
                )
                for condition in generator.ifs:
                    self.facts.add(
                        Fact(
                            "comprehension_filter",
                            (
                                self.module_name,
                                caller,
                                target_name,
                                self._resolve_aliases_in_expr(
                                    self._expression_repr(condition)
                                ),
                                condition.lineno,
                            ),
                        )
                    )
                    self._add_condition_read_facts(condition)

    def _record_with_resources(self, items: list[ast.withitem], line: int) -> None:
        caller = self._current_callable()
        for item in items:
            optional_name = ""
            if item.optional_vars is not None:
                optional_name = ",".join(self._iter_assignment_target_names(item.optional_vars))
            self.facts.add(
                Fact(
                    "with_resource",
                    (
                        self.module_name,
                        caller,
                        self._expression_repr(item.context_expr),
                        optional_name,
                        line,
                    ),
                )
            )

    def _record_yield(self, value: ast.AST | None, line: int) -> None:
        self.facts.add(
            Fact(
                "yield_value",
                (
                    self.module_name,
                    self._current_callable(),
                    self._expression_repr(value) if value is not None else "",
                    line,
                ),
            )
        )

    def _alias_target(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            return self._expression_repr(node)
        return None

    def _resolve_aliases_in_expr(self, expression: str) -> str:
        parts = expression.split(".", 1)
        resolved = self._resolve_local_alias(parts[0])
        return ".".join([resolved, parts[1]]) if len(parts) == 2 else resolved

    def _field_dep_from_alias(self, alias_target: str) -> set[tuple[str, str]]:
        owner, separator, field_name = alias_target.partition(".")
        if separator and owner and field_name and "." not in field_name:
            return {(owner, field_name)}
        return set()

    def _subscript_index_kind(self, node: ast.AST) -> str:
        if isinstance(node, ast.Slice):
            return "slice"
        if isinstance(node, ast.Constant):
            return type(node.value).__name__
        if isinstance(node, ast.Name):
            return "name"
        return type(node).__name__

    def _pattern_kind(self, node: ast.pattern) -> str:
        name = type(node).__name__
        if isinstance(node, ast.MatchClass):
            class_name = self._render_expr(node.cls)
            return f"{name}:{class_name}" if class_name else name
        return name

    def _expression_field_deps(self, node: ast.AST) -> set[tuple[str, str]]:
        deps: set[tuple[str, str]] = set()
        if isinstance(node, ast.Name):
            local_name = self._resolve_local_alias(node.id)
            deps.update(self._field_dep_from_alias(local_name))
            deps.update(self._get_local_field_deps(local_name))
            return deps

        for child in ast.walk(node):
            if isinstance(child, ast.Attribute) and isinstance(child.value, ast.Name):
                deps.add((self._resolve_local_alias(child.value.id), child.attr))
            elif isinstance(child, ast.Name):
                local_name = self._resolve_local_alias(child.id)
                deps.update(self._field_dep_from_alias(local_name))
                deps.update(self._get_local_field_deps(local_name))
        return deps

    def _get_local_field_deps(self, local_name: str) -> set[tuple[str, str]]:
        if not self._local_field_deps_stack:
            return set()
        return set(self._local_field_deps_stack[-1].get(local_name, set()))

    def _set_local_field_deps(
        self,
        local_name: str,
        field_deps: set[tuple[str, str]],
    ) -> None:
        if self._local_field_deps_stack:
            self._local_field_deps_stack[-1][local_name] = set(field_deps)

    def _set_local_dataclass_value(self, local_name: str, class_name: str) -> None:
        if self._local_dataclass_values_stack:
            self._local_dataclass_values_stack[-1][local_name] = class_name

    def _get_numeric_assignment(self, local_name: str) -> int | None:
        if not self._local_numeric_values_stack:
            return None
        return self._local_numeric_values_stack[-1].get(local_name)

    def _set_numeric_assignment(self, local_name: str, value: int) -> None:
        if self._local_numeric_values_stack:
            self._local_numeric_values_stack[-1][local_name] = value

    def _set_local_alias(self, local_name: str, target_name: str) -> None:
        if self._local_alias_stack:
            self._local_alias_stack[-1][local_name] = target_name

    def _resolve_local_alias(self, name: str) -> str:
        if not self._local_alias_stack:
            return name
        seen: set[str] = set()
        current = name
        aliases = self._local_alias_stack[-1]
        while current in aliases and current not in seen:
            seen.add(current)
            current = aliases[current]
        return current

    @staticmethod
    def _is_none_literal(node: ast.AST) -> bool:
        return isinstance(node, ast.Constant) and node.value is None

    def _literal_return(self, node: ast.AST) -> tuple[str, str] | None:
        return self._literal_value(node)

    def _literal_value(self, node: ast.AST) -> tuple[str, str] | None:
        match node:
            case ast.Constant(value=bool(value)):
                return "bool", str(value)
            case ast.Constant(value=str(value)):
                return "str", value
            case ast.Constant(value=int(value) | float(value)):
                return "number", str(value)
            case ast.List():
                return "list", self._expression_repr(node)
            case ast.Tuple():
                return "tuple", self._expression_repr(node)
            case ast.Dict():
                return "dict", self._expression_repr(node)
            case ast.Set():
                return "set", self._expression_repr(node)
            case _:
                return None

    @staticmethod
    def _numeric_literal(node: ast.AST) -> int | None:
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, int)
            and not isinstance(node.value, bool)
        ):
            return node.value
        return None

    def _numeric_bound_value(self, node: ast.AST) -> int | None:
        numeric_literal = self._numeric_literal(node)
        if numeric_literal is not None:
            return numeric_literal
        if isinstance(node, ast.Name):
            return self._get_numeric_assignment(node.id)
        return None

    def _add_expression_numeric_facts(self, caller: str, node: ast.AST) -> None:
        for child in ast.walk(node):
            numeric_literal = self._numeric_literal(child)
            if numeric_literal is not None:
                self.facts.add(
                    Fact(
                        "numeric_literal",
                        (self.module_name, caller, numeric_literal, child.lineno),
                    )
                )
            if isinstance(child, ast.Call):
                callee = self._render_expr(child.func)
                if callee == "len" and child.args:
                    self.facts.add(
                        Fact(
                            "len_call",
                            (
                                self.module_name,
                                caller,
                                self._expression_repr(child.args[0]),
                                child.lineno,
                            ),
                        )
                    )

    def _string_composition_kind(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.JoinedStr):
            return "fstring"
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            if self._looks_string_expr(node.left) or self._looks_string_expr(node.right):
                return "concat"
        if isinstance(node, ast.Call):
            callee = self._render_expr(node.func)
            if callee and callee.endswith(".join"):
                return "join"
            if callee and callee.endswith(".format"):
                return "format"
        return None

    def _looks_string_expr(self, node: ast.AST) -> bool:
        if isinstance(node, (ast.JoinedStr, ast.Constant)) and isinstance(
            getattr(node, "value", ""), str
        ):
            return True
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            return self._looks_string_expr(node.left) or self._looks_string_expr(node.right)
        return False

    def _bounded_expr_repr(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Call) and self._render_expr(node.func) == "len" and node.args:
            return f"len({self._expression_repr(node.args[0])})"
        return self._render_expr(node)

    @staticmethod
    def _compare_op_name(node: ast.cmpop) -> str | None:
        if isinstance(node, ast.Lt):
            return "lt"
        if isinstance(node, ast.LtE):
            return "le"
        if isinstance(node, ast.Gt):
            return "gt"
        if isinstance(node, ast.GtE):
            return "ge"
        if isinstance(node, ast.Eq):
            return "eq"
        if isinstance(node, ast.NotEq):
            return "ne"
        return None

    @staticmethod
    def _reverse_compare_op_name(node: ast.cmpop) -> str | None:
        if isinstance(node, ast.Lt):
            return "gt"
        if isinstance(node, ast.LtE):
            return "ge"
        if isinstance(node, ast.Gt):
            return "lt"
        if isinstance(node, ast.GtE):
            return "le"
        if isinstance(node, ast.Eq):
            return "eq"
        if isinstance(node, ast.NotEq):
            return "ne"
        return None

    def _slice_upper_bound(self, node: ast.AST) -> int | None:
        if isinstance(node, ast.Slice) and node.upper is not None:
            return self._numeric_bound_value(node.upper)
        return None

    @staticmethod
    def _last_name(rendered: str | None) -> str | None:
        return rendered.split(".")[-1] if rendered else None

    def _annotation_type_ref(self, node: ast.AST) -> str | None:
        match node:
            case ast.Name(id=name):
                return name
            case ast.Attribute():
                return self._render_expr(node)
            case _:
                return None


def resolve_facts(facts: Iterable[Fact]) -> list[Fact]:
    resolved: set[Fact] = set(facts)
    class_defs = {
        (str(module_name), str(class_name))
        for fact in resolved
        if fact.predicate == "defines_class"
        for module_name, class_name in [fact.args]
    }
    modules = {
        str(fact.args[0])
        for fact in resolved
        if fact.predicate == "module"
    }
    module_suffix_index: dict[str, set[str]] = defaultdict(set)
    for module_name in modules:
        if "." not in module_name:
            continue
        module_suffix_index[module_name.rsplit(".", 1)[-1]].add(module_name)
    function_defs = {
        (str(module_name), str(qualified_name))
        for fact in resolved
        if fact.predicate == "defines_function"
        for module_name, qualified_name, _ in [fact.args]
    }
    aliases: dict[str, dict[str, str]] = defaultdict(dict)

    for fact in resolved:
        if fact.predicate == "import_alias":
            module_name, local_name, qualified_name = fact.args
            aliases[str(module_name)][str(local_name)] = str(qualified_name)

    class_name_to_defs: dict[str, set[str]] = defaultdict(set)
    for module_name, class_name in class_defs:
        class_name_to_defs[class_name].add(module_name)

    function_name_to_defs: dict[str, set[tuple[str, str]]] = defaultdict(set)
    function_names: dict[tuple[str, str], str] = {}
    for fact in resolved:
        if fact.predicate != "function_name":
            continue
        module_name, qualified_name, name = fact.args
        key = (str(module_name), str(qualified_name))
        function_names[key] = str(name)
        function_name_to_defs[str(name)].add(key)

    method_by_class: dict[tuple[str, str, str], str] = {}
    caller_class: dict[tuple[str, str], str] = {}
    for fact in resolved:
        if fact.predicate != "method_of_class":
            continue
        module_name, class_name, qualified_name = fact.args
        method_name = str(qualified_name).split(".")[-1]
        method_by_class[(str(module_name), str(class_name), method_name)] = str(
            qualified_name
        )
        caller_class[(str(module_name), str(qualified_name))] = str(class_name)

    def split_resolved_name(
        module_name: str,
        type_ref: str,
    ) -> tuple[str, str] | None:
        candidates = _resolution_candidates(
            module_name,
            type_ref,
            aliases,
            modules,
            module_suffix_index,
        )
        for candidate in candidates:
            matched = _split_known_class(candidate, class_defs, modules)
            if matched:
                return matched

        short_name = type_ref.split(".")[-1]
        modules_for_class = class_name_to_defs.get(short_name, set())
        if len(modules_for_class) == 1:
            return next(iter(modules_for_class)), short_name
        return None

    for fact in list(resolved):
        match fact:
            case Fact("extends", (module_name, class_name, base_name)):
                _add_resolved_fact(
                    resolved,
                    split_resolved_name(str(module_name), str(base_name)),
                    "resolved_extends",
                    str(module_name),
                    str(class_name),
                )
            case Fact("dataclass_field_type_ref", (
                module_name,
                class_name,
                field_name,
                type_ref,
            )):
                _add_resolved_fact(
                    resolved,
                    split_resolved_name(str(module_name), str(type_ref)),
                    "resolved_dataclass_field_type_ref",
                    str(module_name),
                    str(class_name),
                    str(field_name),
                )
            case Fact("function_param_type_ref", (
                module_name,
                qualified_name,
                param_name,
                type_ref,
            )):
                _add_resolved_fact(
                    resolved,
                    split_resolved_name(str(module_name), str(type_ref)),
                    "resolved_param_type_ref",
                    str(module_name),
                    str(qualified_name),
                    str(param_name),
                )
            case Fact("function_return_type_ref", (module_name, qualified_name, type_ref)):
                _add_resolved_fact(
                    resolved,
                    split_resolved_name(str(module_name), str(type_ref)),
                    "resolved_return_type_ref",
                    str(module_name),
                    str(qualified_name),
                )
            case Fact("returns_dataclass", (
                module_name,
                qualified_name,
                class_name,
                line,
            )):
                _add_resolved_fact(
                    resolved,
                    split_resolved_name(str(module_name), str(class_name)),
                    "resolved_returns_dataclass",
                    str(module_name),
                    str(qualified_name),
                    suffix=(int(line),),
                )
            case Fact("instantiates", (module_name, qualified_name, class_name, line)):
                _add_resolved_fact(
                    resolved,
                    split_resolved_name(str(module_name), str(class_name)),
                    "resolved_instantiates",
                    str(module_name),
                    str(qualified_name),
                    suffix=(int(line),),
                )
            case Fact("local_dataclass_value", (
                module_name,
                qualified_name,
                local_name,
                class_name,
                line,
            )):
                _add_resolved_fact(
                    resolved,
                    split_resolved_name(str(module_name), str(class_name)),
                    "resolved_local_dataclass_value",
                    str(module_name),
                    str(qualified_name),
                    str(local_name),
                    suffix=(int(line),),
                )
            case _:
                pass

    resolved_param_types = {
        (
            str(module_name),
            str(qualified_name),
            str(param_name),
        ): (str(type_module), str(type_name))
        for fact in resolved
        if fact.predicate == "resolved_param_type_ref"
        for (
            module_name,
            qualified_name,
            param_name,
            type_module,
            type_name,
        ) in [fact.args]
    }
    resolved_local_value_types = {
        (
            str(module_name),
            str(qualified_name),
            str(local_name),
        ): (str(type_module), str(type_name))
        for fact in resolved
        if fact.predicate == "resolved_local_dataclass_value"
        for (
            module_name,
            qualified_name,
            local_name,
            type_module,
            type_name,
            _,
        ) in [fact.args]
    }

    call_targets: dict[tuple[str, str, str, int], tuple[str, str, str]] = {}
    for fact in list(resolved):
        if fact.predicate != "calls":
            continue
        module_name, qualified_name, callee_name, line = fact.args
        call_target = _resolve_call_target(
            str(module_name),
            str(qualified_name),
            str(callee_name),
            aliases,
            modules,
            module_suffix_index,
            function_defs,
            function_name_to_defs,
            split_resolved_name,
            resolved_param_types,
            resolved_local_value_types,
            caller_class,
            method_by_class,
        )
        if call_target is None:
            continue
        callee_module, callee_qualified_name, call_kind = call_target
        call_targets[
            (str(module_name), str(qualified_name), str(callee_name), int(line))
        ] = call_target
        resolved.add(
            Fact(
                "call_target",
                (
                    str(module_name),
                    str(qualified_name),
                    str(callee_name),
                    callee_module,
                    callee_qualified_name,
                    call_kind,
                    int(line),
                ),
            )
        )

    for fact in list(resolved):
        match fact:
            case Fact("return_call", (module_name, qualified_name, callee_name, line)):
                call_target = call_targets.get(
                    (
                        str(module_name),
                        str(qualified_name),
                        str(callee_name),
                        int(line),
                    )
                )
                if call_target:
                    resolved.add(
                        Fact(
                            "resolved_return_call",
                            (
                                str(module_name),
                                str(qualified_name),
                                call_target[0],
                                call_target[1],
                                int(line),
                            ),
                        )
                    )
            case Fact(
                "call_result_assigned",
                (module_name, qualified_name, local_name, callee_name, line),
            ):
                for (
                    caller_module,
                    caller_qualified_name,
                    raw_callee_name,
                    call_line,
                ), call_target in call_targets.items():
                    if (
                        caller_module != str(module_name)
                        or caller_qualified_name != str(qualified_name)
                        or call_line != int(line)
                    ):
                        continue
                    target_function_name = function_names.get(
                        (call_target[0], call_target[1]), ""
                    )
                    if target_function_name != str(callee_name):
                        continue
                    resolved.add(
                        Fact(
                            "resolved_call_result_assigned",
                            (
                                str(module_name),
                                str(qualified_name),
                                str(local_name),
                                call_target[0],
                                call_target[1],
                                int(line),
                            ),
                        )
                    )
            case _:
                pass

    return sorted(resolved)


def _add_resolved_fact(
    facts: set[Fact],
    resolved_name: tuple[str, str] | None,
    predicate: str,
    *prefix: str,
    suffix: tuple[int, ...] = (),
) -> None:
    if resolved_name:
        type_module, type_name = resolved_name
        facts.add(Fact(predicate, (*prefix, type_module, type_name, *suffix)))


def _resolution_candidates(
    module_name: str,
    type_ref: str,
    aliases: dict[str, dict[str, str]],
    modules: set[str],
    module_suffix_index: dict[str, set[str]] | None = None,
) -> list[str]:
    candidates: list[str] = []
    parts = type_ref.split(".")
    local_name = parts[0]

    if local_name in aliases.get(module_name, {}):
        target = aliases[module_name][local_name]
        candidates.append(".".join([target, *parts[1:]]) if parts[1:] else target)

    candidates.append(type_ref)
    candidates.append(f"{module_name}.{type_ref}")

    if module_suffix_index is None:
        module_matches = [
            module_candidate
            for module_candidate in modules
            if module_candidate.endswith(f".{local_name}")
        ]
    else:
        module_matches = sorted(module_suffix_index.get(local_name, set()))
    for module_candidate in module_matches:
        candidates.append(".".join([module_candidate, *parts[1:]]))

    return candidates


def _split_known_class(
    qualified_name: str,
    class_defs: set[tuple[str, str]],
    modules: set[str],
) -> tuple[str, str] | None:
    parts = qualified_name.split(".")
    for index in range(len(parts) - 1, 0, -1):
        module_name = ".".join(parts[:index])
        class_name = ".".join(parts[index:])
        if (module_name, class_name) in class_defs:
            return module_name, class_name
        if module_name in modules and (module_name, parts[index]) in class_defs:
            return module_name, parts[index]
    if len(parts) == 1 and ("", parts[0]) in class_defs:
        return "", parts[0]
    return None


def _resolve_call_target(
    module_name: str,
    qualified_name: str,
    callee_name: str,
    aliases: dict[str, dict[str, str]],
    modules: set[str],
    module_suffix_index: dict[str, set[str]],
    function_defs: set[tuple[str, str]],
    function_name_to_defs: dict[str, set[tuple[str, str]]],
    split_resolved_name: Callable[[str, str], tuple[str, str] | None],
    resolved_param_types: dict[tuple[str, str, str], tuple[str, str]],
    resolved_local_value_types: dict[tuple[str, str, str], tuple[str, str]],
    caller_class: dict[tuple[str, str], str],
    method_by_class: dict[tuple[str, str, str], str],
) -> tuple[str, str, str] | None:
    parts = callee_name.split(".")
    if len(parts) >= 2:
        receiver = parts[0]
        method_name = parts[-1]

        if receiver == "self":
            class_name = caller_class.get((module_name, qualified_name))
            if class_name is not None:
                target = method_by_class.get((module_name, class_name, method_name))
                if target:
                    return module_name, target, "bound_method"

        receiver_type = resolved_param_types.get((module_name, qualified_name, receiver))
        if receiver_type is None:
            receiver_type = resolved_local_value_types.get(
                (module_name, qualified_name, receiver)
            )
        if receiver_type is not None:
            receiver_module, receiver_class = receiver_type
            target = method_by_class.get((receiver_module, receiver_class, method_name))
            if target:
                return receiver_module, target, "bound_method"

        class_ref = ".".join(parts[:-1])
        resolved_class = split_resolved_name(module_name, class_ref)
        if resolved_class is not None:
            class_module, class_name = resolved_class
            target = method_by_class.get((class_module, class_name, method_name))
            if target:
                return class_module, target, "function"

        for candidate in _resolution_candidates(
            module_name,
            callee_name,
            aliases,
            modules,
            module_suffix_index,
        ):
            target = _split_known_function(candidate, function_defs, modules)
            if target is not None:
                return target[0], target[1], "function"

    if (module_name, callee_name) in function_defs:
        return module_name, callee_name, "function"

    same_module_defs = {
        definition
        for definition in function_name_to_defs.get(callee_name, set())
        if definition[0] == module_name
    }
    if len(same_module_defs) == 1:
        target_module, target_qualified_name = next(iter(same_module_defs))
        return target_module, target_qualified_name, "function"

    for candidate in _resolution_candidates(
        module_name,
        callee_name,
        aliases,
        modules,
        module_suffix_index,
    ):
        target = _split_known_function(candidate, function_defs, modules)
        if target is not None:
            return target[0], target[1], "function"

    global_defs = function_name_to_defs.get(callee_name, set())
    if len(global_defs) == 1:
        target_module, target_qualified_name = next(iter(global_defs))
        return target_module, target_qualified_name, "function"
    return None


def _split_known_function(
    qualified_name: str,
    function_defs: set[tuple[str, str]],
    modules: set[str],
) -> tuple[str, str] | None:
    parts = qualified_name.split(".")
    for index in range(len(parts) - 1, 0, -1):
        module_name = ".".join(parts[:index])
        function_name = ".".join(parts[index:])
        if (module_name, function_name) in function_defs:
            return module_name, function_name
        if module_name in modules and (module_name, parts[index]) in function_defs:
            return module_name, parts[index]
    return None


def extract_facts_from_source(
    source: str,
    module_name: str,
    relative_path: str = "<memory>",
) -> list[Fact]:
    tree = ast.parse(source, filename=relative_path)
    extractor = PythonFactExtractor(module_name)
    return resolve_facts(extractor.extract(tree, relative_path))


def extract_facts_from_path(root: Path, include_tests: bool = False) -> list[Fact]:
    facts: set[Fact] = set()
    for path in iter_python_files(root, include_tests=include_tests):
        relative_path = path.relative_to(root)
        module_name = module_name_for_path(relative_path)
        facts.update(
            extract_facts_from_source(
                path.read_text(encoding="utf-8"),
                module_name=module_name,
                relative_path=str(relative_path),
            )
        )
    return resolve_facts(facts)


def write_debug_facts(facts: Iterable[Fact], output_path: Path | None = None) -> None:
    lines = [fact.render() for fact in facts]
    text = "\n".join(lines) + ("\n" if lines else "")
    if output_path is None:
        print(text, end="")
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")


def write_souffle_facts(facts: Iterable[Fact], output_dir: Path) -> None:
    grouped: dict[str, list[str]] = defaultdict(list)
    for fact in facts:
        if fact.predicate not in SOUFFLE_SCHEMA:
            raise ValueError(f"Unknown predicate {fact.predicate!r} for Souffle export.")
        grouped[fact.predicate].append(fact.to_souffle_row())

    output_dir.mkdir(parents=True, exist_ok=True)

    for predicate in sorted(SOUFFLE_SCHEMA):
        rows = grouped.get(predicate, [])
        text = "\n".join(rows) + ("\n" if rows else "")
        (output_dir / f"{predicate}.facts").write_text(text, encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Extract Python AST facts for Souffle or human-readable debug inspection."
    )
    parser.add_argument("project_root", help="Path to the Python project to analyze.")
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include tests and manual testing files in the extracted facts.",
    )
    parser.add_argument(
        "--output",
        help="Optional path to write human-readable fact syntax. Defaults to stdout in debug mode.",
    )
    parser.add_argument(
        "--format",
        choices=("souffle", "debug"),
        default="souffle",
        help="Output format. 'souffle' writes relation.facts files; 'debug' writes human-readable facts.",
    )
    parser.add_argument(
        "--souffle-facts-dir",
        help="Directory to write Souffle .facts files into. Required in souffle mode.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    root = Path(args.project_root).resolve()
    facts = extract_facts_from_path(root, include_tests=args.include_tests)

    if args.format == "souffle":
        if not args.souffle_facts_dir:
            parser.error("--souffle-facts-dir is required when --format=souffle")
        write_souffle_facts(facts, Path(args.souffle_facts_dir).resolve())
        return

    write_debug_facts(facts, Path(args.output).resolve() if args.output else None)


if __name__ == "__main__":
    main()
