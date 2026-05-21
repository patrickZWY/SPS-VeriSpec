from __future__ import annotations

import argparse
import ast
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


EXCLUDED_DIRS = {"__pycache__", ".git", ".venv", "venv", "tests", "manual_testing"}

SOUFFLE_SCHEMA: dict[str, tuple[str, ...]] = {
    "module": ("symbol",),
    "module_file": ("symbol", "symbol"),
    "imports": ("symbol", "symbol"),
    "defines_class": ("symbol", "symbol"),
    "extends": ("symbol", "symbol", "symbol"),
    "dataclass": ("symbol", "symbol", "number", "number"),
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
    "method_of_class": ("symbol", "symbol", "symbol"),
    "function_param": ("symbol", "symbol", "symbol", "symbol", "number", "number"),
    "function_param_type_ref": ("symbol", "symbol", "symbol", "symbol"),
    "function_return_type": ("symbol", "symbol", "symbol", "number"),
    "function_return_type_ref": ("symbol", "symbol", "symbol"),
    "returns_dataclass": ("symbol", "symbol", "symbol", "number"),
    "attribute_read": ("symbol", "symbol", "symbol", "symbol", "number"),
    "attribute_write": ("symbol", "symbol", "symbol", "symbol", "number"),
    "handles_exception": ("symbol", "symbol", "symbol", "number"),
    "raises_exception": ("symbol", "symbol", "symbol", "number"),
    "defines_function": ("symbol", "symbol", "number"),
    "calls": ("symbol", "symbol", "symbol", "number"),
    "instantiates": ("symbol", "symbol", "symbol", "number"),
    "reads_env_var": ("symbol", "symbol", "symbol", "number"),
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

    def extract(self, tree: ast.AST, relative_path: str) -> list[Fact]:
        self.facts.add(Fact("module", (self.module_name,)))
        self.facts.add(Fact("module_file", (self.module_name, relative_path)))
        self.visit(tree)
        return sorted(self.facts)

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.facts.add(Fact("imports", (self.module_name, alias.name)))
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        for alias in node.names:
            target = f"{module}.{alias.name}" if module else alias.name
            self.facts.add(Fact("imports", (self.module_name, target)))
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

        is_dataclass, is_frozen = self._extract_dataclass_metadata(node)
        if is_dataclass:
            self.facts.add(
                Fact("dataclass", (self.module_name, class_name, is_frozen, node.lineno))
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
            class_name = self._class_like_name(callee)
            if class_name:
                self.facts.add(
                    Fact(
                        "instantiates",
                        (self.module_name, caller, class_name, node.lineno),
                    )
                )

        env_var = self._extract_env_var(node)
        if env_var:
            self.facts.add(
                Fact("reads_env_var", (self.module_name, caller, env_var, node.lineno))
            )

        self.generic_visit(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        qualname = self._push_name(node.name)
        self.facts.add(
            Fact(
                "defines_function",
                (self.module_name, qualname, self._function_arity(node.args)),
            )
        )
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
        self.generic_visit(node)
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
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parent = self._render_expr(node.value)
            return f"{parent}.{node.attr}" if parent else node.attr
        if isinstance(node, ast.Call):
            return self._render_expr(node.func)
        if isinstance(node, ast.Subscript):
            return self._render_expr(node.value)
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        return None

    def visit_Attribute(self, node: ast.Attribute) -> None:
        owner = self._render_expr(node.value)
        caller = self._current_callable()
        if owner:
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

    def visit_Return(self, node: ast.Return) -> None:
        caller = self._current_callable()
        if node.value is not None:
            class_name = self._returned_class_name(node.value)
            if class_name:
                self.facts.add(
                    Fact(
                        "returns_dataclass",
                        (self.module_name, caller, class_name, node.lineno),
                    )
                )
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

    def _extract_dataclass_metadata(self, node: ast.ClassDef) -> tuple[bool, int]:
        for decorator in node.decorator_list:
            callee = decorator
            frozen = 0
            if isinstance(decorator, ast.Call):
                callee = decorator.func
                for keyword in decorator.keywords:
                    if keyword.arg == "frozen" and self._is_truthy_literal(keyword.value):
                        frozen = 1

            rendered = self._render_expr(callee)
            if rendered and rendered.split(".")[-1] == "dataclass":
                return True, frozen
        return False, 0

    @staticmethod
    def _is_truthy_literal(node: ast.AST) -> bool:
        return isinstance(node, ast.Constant) and bool(node.value)

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
            base = self._render_expr(node.value)
            return base is not None and base.split(".")[-1] == "ClassVar"
        rendered = self._render_expr(node)
        return rendered is not None and rendered.split(".")[-1] == "ClassVar"

    def _is_optional_annotation(self, node: ast.AST | None) -> int:
        if node is None:
            return 0
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return int(
                self._contains_none_annotation(node.left)
                or self._contains_none_annotation(node.right)
            )
        if isinstance(node, ast.Subscript):
            base = self._render_expr(node.value)
            if base is not None and base.split(".")[-1] == "Optional":
                return 1
            return self._is_optional_annotation(node.slice)
        return 0

    def _contains_none_annotation(self, node: ast.AST) -> bool:
        if isinstance(node, ast.Constant) and node.value is None:
            return True
        if isinstance(node, ast.Name) and node.id == "None":
            return True
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            return self._contains_none_annotation(node.left) or self._contains_none_annotation(
                node.right
            )
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
        refs: set[str] = set()
        if node is None:
            return refs

        for child in ast.walk(node):
            if isinstance(child, ast.Name):
                refs.add(child.id)
            elif isinstance(child, ast.Attribute):
                rendered = self._render_expr(child)
                if rendered:
                    refs.add(rendered)

        return refs

    def _returned_class_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Call):
            return self._class_like_name(self._render_expr(node.func) or "")
        return None


def extract_facts_from_source(
    source: str,
    module_name: str,
    relative_path: str = "<memory>",
) -> list[Fact]:
    tree = ast.parse(source, filename=relative_path)
    extractor = PythonFactExtractor(module_name)
    return extractor.extract(tree, relative_path)


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
    return sorted(facts)


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
