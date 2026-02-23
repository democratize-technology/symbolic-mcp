# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Symbolic MCP Contributors

"""Security validation for symbolic execution.

This module contains security constants, the AST visitor for detecting
dangerous code patterns, and the main validation function.
"""

import ast
import textwrap

from symbolic_mcp.config import CODE_SIZE_LIMIT
from symbolic_mcp.types import _ValidationResult

# --- Security: Import Whitelist ---

# Modules allowed in user code for symbolic execution
ALLOWED_MODULES = frozenset(
    {
        "math",
        "random",
        "string",
        "collections",
        "itertools",
        "functools",
        "operator",
        "typing",
        "re",
        "json",
        "datetime",
        "decimal",
        "fractions",
        "statistics",
        "dataclasses",
        "enum",
        "copy",
        "heapq",
        "bisect",
        "typing_extensions",
        "abc",
    }
)

# Modules that are dangerous and should be blocked
BLOCKED_MODULES = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "pathlib",
        "socket",
        "http",
        "urllib",
        "requests",
        "ftplib",
        "pickle",
        "shelve",
        "marshal",
        "ctypes",
        "multiprocessing",
        "importlib",
        "runpy",
        "code",
        "codeop",
        "pty",
        "tty",
        "termios",
        "threading",
        "signal",
        "fcntl",
        "resource",
        "syslog",
        "getpass",
    }
)

# Built-in functions that are dangerous and should be blocked
DANGEROUS_BUILTINS = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "__import__",
        "open",
        "globals",
        "locals",
        "vars",
        "dir",
    }
)


class _DangerousCallVisitor(ast.NodeVisitor):
    """AST visitor that detects dangerous function calls and attribute access.

    This prevents bypasses like:
    - eval (1) - space before parenthesis
    - getattr(__builtins__, "eval") - dynamic access
    - [eval][0]() - list indexing bypass
    - {"f": eval}["f"]() - dict lookup bypass
    - (eval,) - tuple unpacking bypass
    - __builtins__["eval"] - subscript access to __builtins__
    - __builtins__.eval - attribute access to __builtins__
    """

    # Blocked global names that provide access to dangerous functions
    BLOCKED_GLOBALS = frozenset({"__builtins__"})

    def __init__(self) -> None:
        self.dangerous_calls: list[str] = []
        self.dangerous_references: list[str] = []
        self.builtins_access: list[str] = []

    def _is_dangerous_name(self, name: str) -> bool:
        """Check if a name refers to a dangerous builtin."""
        return name in DANGEROUS_BUILTINS

    def _is_blocked_module(self, name: str) -> bool:
        """Check if a name is a blocked module."""
        return name in BLOCKED_MODULES

    def _is_blocked_global(self, name: str) -> bool:
        """Check if a name is a blocked global variable."""
        return name in self.BLOCKED_GLOBALS

    def _check_subscript_for_dangerous(self, node: ast.Subscript) -> None:
        """Check if a subscript accesses a dangerous function.

        Handles: [eval][0](), (eval,)[0](), {"f": eval}["f"]()
        """
        # Check the value being subscripted
        if isinstance(node.value, ast.Name):
            if self._is_dangerous_name(node.value.id):
                self.dangerous_calls.append(node.value.id)
        elif isinstance(node.value, (ast.List, ast.Tuple)):
            self._check_sequence_for_dangerous(node.value)
        elif isinstance(node.value, ast.Dict):
            self._check_dict_for_dangerous(node.value)
        elif isinstance(node.value, ast.Subscript):
            self._check_subscript_for_dangerous(node.value)

    def _check_sequence_for_dangerous(self, node: ast.List | ast.Tuple) -> None:
        """Check a list or tuple literal for dangerous builtin references.

        Handles: [eval], (eval,), [[eval]]
        """
        for elt in node.elts:
            if isinstance(elt, ast.Name) and self._is_dangerous_name(elt.id):
                self.dangerous_calls.append(elt.id)
                self.dangerous_references.append(elt.id)
            elif isinstance(elt, (ast.List, ast.Tuple)):
                self._check_sequence_for_dangerous(elt)

    def _check_dict_for_dangerous(self, node: ast.Dict) -> None:
        """Check a dict literal for dangerous builtin references.

        Handles: {"f": eval}, {"f": [eval]}
        """
        for value in node.values:
            if isinstance(value, ast.Name) and self._is_dangerous_name(value.id):
                self.dangerous_calls.append(value.id)
                self.dangerous_references.append(value.id)
            elif isinstance(value, (ast.List, ast.Tuple)):
                self._check_sequence_for_dangerous(value)
            elif isinstance(value, ast.Dict):
                self._check_dict_for_dangerous(value)

    def visit_List(self, node: ast.List) -> None:
        """Visit list nodes to detect dangerous function references."""
        self._check_sequence_for_dangerous(node)
        self.generic_visit(node)

    def visit_Tuple(self, node: ast.Tuple) -> None:
        """Visit tuple nodes to detect dangerous function references."""
        self._check_sequence_for_dangerous(node)
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        """Visit dict nodes to detect dangerous function references."""
        self._check_dict_for_dangerous(node)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Track dangerous names that might be called indirectly."""
        # If we see a dangerous name being referenced anywhere in the code,
        # it could be called indirectly
        if self._is_dangerous_name(node.id):
            self.dangerous_references.append(node.id)
        # Check for blocked globals like __builtins__
        if self._is_blocked_global(node.id):
            self.dangerous_references.append(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Detect dangerous attribute access patterns.

        Handles:
        - __builtins__.eval
        - __builtins__.exec
        - __builtins__.compile
        - Introspection gadgets: __subclasses__, __bases__, __mro__, __globals__
        """
        # check for introspection gadgets
        if node.attr in (
            "__subclasses__",
            "__bases__",
            "__mro__",
            "__globals__",
            "__class__",
            "__code__",
        ):
            self.dangerous_calls.append(f"introspection via {node.attr}")

        # Check if this is accessing an attribute of __builtins__
        if isinstance(node.value, ast.Name):
            if node.value.id == "__builtins__":
                # Block any attribute access to __builtins__
                self.dangerous_calls.append(f"__builtins__.{node.attr}")
                self.builtins_access.append(f"__builtins__.{node.attr}")
        # Also check nested attribute access like __builtins__.__dict__
        elif isinstance(node.value, ast.Attribute):
            # Walk down to find the root
            root: ast.expr = node.value
            parts = [node.attr]
            while isinstance(root, ast.Attribute):
                parts.append(root.attr)
                root = root.value
            if isinstance(root, ast.Name) and root.id == "__builtins__":
                parts.append("__builtins__")
                full_chain = ".".join(reversed(parts))
                self.dangerous_calls.append(full_chain)
                self.builtins_access.append(full_chain)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Detect dangerous subscript access patterns.

        Handles:
        - __builtins__["eval"]
        - (__builtins__)["eval"]
        - (__builtins__ or {})["eval"]
        """
        # Check if we're subscripting __builtins__
        if isinstance(node.value, ast.Name):
            if node.value.id == "__builtins__":
                self.dangerous_calls.append("__builtins__[...]")
                self.builtins_access.append("__builtins__[...]")
        # Check for subscripted expressions like (__builtins__)["eval"]
        # Use a targeted visitor instead of ast.walk to avoid O(n²) complexity
        elif isinstance(node.value, (ast.BinOp, ast.BoolOp, ast.Compare)):
            # Check if __builtins__ appears in the expression using a visitor
            class _BuiltinsFinder(ast.NodeVisitor):
                def __init__(self) -> None:
                    self.found = False

                def visit_Name(self, n: ast.Name) -> None:
                    if n.id == "__builtins__":
                        self.found = True
                    # Don't continue traversal if found
                    if not self.found:
                        self.generic_visit(n)

            finder = _BuiltinsFinder()
            finder.visit(node.value)
            if finder.found:
                self.dangerous_calls.append("__builtins__[...]")
                self.builtins_access.append("__builtins__[...]")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Detect dangerous function calls including getattr bypasses.

        Handles:
        - getattr(__builtins__, "eval")
        - getattr(__builtins__, "exec")
        """
        # Check for getattr(__builtins__, "dangerous")
        if isinstance(node.func, ast.Name) and node.func.id == "getattr":
            if len(node.args) >= 2:
                # First arg should be __builtins__
                if (
                    isinstance(node.args[0], ast.Name)
                    and node.args[0].id == "__builtins__"
                ):
                    # Second arg is the attribute name - check if it's a dangerous builtin
                    if isinstance(node.args[1], ast.Constant):
                        attr_name = node.args[1].value
                        if isinstance(attr_name, str) and self._is_dangerous_name(
                            attr_name
                        ):
                            self.dangerous_calls.append(
                                f'getattr(__builtins__, "{attr_name}")'
                            )
                    # Even if we can't determine the attribute name statically,
                    # getattr on __builtins__ is dangerous
                    self.dangerous_calls.append("getattr(__builtins__, ...)")
                    self.builtins_access.append("getattr(__builtins__, ...)")

        # Now check for other dangerous calls (original logic)
        # Direct name call: eval(), exec(), compile()
        if isinstance(node.func, ast.Name):
            if self._is_dangerous_name(node.func.id):
                self.dangerous_calls.append(node.func.id)

        # Attribute access: os.system(), subprocess.run()
        elif isinstance(node.func, ast.Attribute):
            # Check for dangerous attribute chains
            if isinstance(node.func.value, ast.Name):
                # module.dangerous_function()
                attr_chain = f"{node.func.value.id}.{node.func.attr}"
                if self._is_blocked_module(node.func.value.id):
                    self.dangerous_calls.append(attr_chain)
            elif isinstance(node.func.value, ast.Attribute):
                # nested.module.dangerous_function()
                # Walk up to find the root module
                root: ast.expr = node.func.value
                parts = [node.func.attr]
                while isinstance(root, ast.Attribute):
                    parts.append(root.attr)
                    root = root.value
                if isinstance(root, ast.Name):
                    parts.append(root.id)
                    full_name = ".".join(reversed(parts))
                    if any(
                        self._is_blocked_module(part) for part in full_name.split(".")
                    ):
                        self.dangerous_calls.append(full_name)

        # Subscript call: [eval][0]()
        elif isinstance(node.func, ast.Subscript):
            self._check_subscript_for_dangerous(node.func)

        self.generic_visit(node)

    def visit_Import(self, node: ast.Import) -> None:
        """Check for blocked module imports.

        This eliminates the need for a separate ast.walk() traversal
        in validate_code(), improving performance.
        """
        if node.names:
            module_name = node.names[0].name
            if module_name:
                base_module = module_name.split(".")[0]
                if self._is_blocked_module(base_module):
                    self.dangerous_calls.append(f"import {base_module}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check for blocked module imports in 'from X import Y' statements.

        This eliminates the need for a separate ast.walk() traversal
        in validate_code(), improving performance.
        """
        # For ImportFrom, node.module can be None (relative imports)
        if node.module and node.names:
            base_module = node.module.split(".")[0]
            if self._is_blocked_module(base_module):
                self.dangerous_calls.append(f"from {base_module} import ...")
        self.generic_visit(node)


def validate_code(code: str) -> _ValidationResult:
    """Validate user code before execution.

    Uses AST-based detection to prevent security bypasses:
    - eval (1) - space before parenthesis
    - getattr(__builtins__, "eval") - dynamic access
    - [eval][0]() - list indexing bypass
    - {"f": eval}["f"]() - dict lookup bypass

    Returns:
        ValidationResult with 'valid': bool and optional 'error': str if invalid
    """
    # Empty string edge case
    if not code or not code.strip():
        return {"valid": True}

    # Size limit check (configurable via SYMBOLIC_CODE_SIZE_LIMIT env var)
    code_size = len(code.encode("utf-8"))
    if code_size > CODE_SIZE_LIMIT:
        return {
            "valid": False,
            "error": f"Code size exceeds {CODE_SIZE_LIMIT // 1024}KB limit",
        }

    # Check for blocked imports and dangerous function calls using AST
    # Use textwrap.dedent for consistency with _temporary_module and logic_analyze_branches
    # This allows users to pass indented code snippets (e.g., from markdown blocks)
    try:
        tree = ast.parse(textwrap.dedent(code))

        # First check for dangerous function calls
        visitor = _DangerousCallVisitor()
        visitor.visit(tree)

        if visitor.dangerous_calls:
            dangerous = ", ".join(set(visitor.dangerous_calls))
            return {"valid": False, "error": f"Blocked function call: {dangerous}"}

        # Check for dangerous function references in data structures
        # These might not be called directly but are still dangerous
        if visitor.dangerous_references:
            # Filter out references that are already in dangerous_calls
            refs = set(visitor.dangerous_references) - set(visitor.dangerous_calls)
            if refs:
                dangerous = ", ".join(refs)
                return {
                    "valid": False,
                    "error": f"Blocked function reference: {dangerous}",
                }

    except SyntaxError as e:
        return {
            "valid": False,
            "error": f"Syntax error: {e}",
            "error_type": "SyntaxError",
        }

    return {"valid": True}


__all__ = [
    "ALLOWED_MODULES",
    "BLOCKED_MODULES",
    "DANGEROUS_BUILTINS",
    "_DangerousCallVisitor",
    "validate_code",
]
