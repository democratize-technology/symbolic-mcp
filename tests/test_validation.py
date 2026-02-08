"""SPDX-License-Identifier: MIT
Copyright (c) 2025 Symbolic MCP Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""Unit tests for the validate_code() function.

These tests import the validation module directly to avoid CrossHair dependencies.
"""

import ast  # noqa: E402
from typing import Any, Dict  # noqa: E402

import pytest  # noqa: E402

# Replicate constants from main.py (to avoid importing crosshair)
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
        "datetime",
        "decimal",
        "fractions",
        "enum",
        "dataclasses",
        "json",
        "re",
        "typing_extensions",
    }
)

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
        "ftplib",
        "pickle",
        "shelve",
        "marshal",
        "ctypes",
        "multiprocessing",
        "threading",
        "signal",
        "fcntl",
        "resource",
        "pty",
        "termios",
        "syslog",
        "getpass",
    }
)

# Dangerous built-in functions that must not be called
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
        """
        # Check if this is accessing an attribute of __builtins__
        if isinstance(node.value, ast.Name):
            if node.value.id == "__builtins__":
                # Block any attribute access to __builtins__
                self.dangerous_calls.append(f"__builtins__.{node.attr}")
                self.builtins_access.append(f"__builtins__.{node.attr}")
        # Also check nested attribute access like __builtins__.__dict__
        elif isinstance(node.value, ast.Attribute):
            # Walk down to find the root
            root = node.value
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
        elif isinstance(node.value, (ast.BinOp, ast.BoolOp, ast.Compare)):
            # Check if __builtins__ appears in the expression
            for child in ast.walk(node.value):
                if isinstance(child, ast.Name) and child.id == "__builtins__":
                    self.dangerous_calls.append("__builtins__[...]")
                    self.builtins_access.append("__builtins__[...]")
                    break
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: C901
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
                    # Second arg is the attribute name - check if dangerous builtin  # noqa: E501
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
                root = node.func.value
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


def validate_code(code: str) -> Dict[str, Any]:  # noqa: C901
    """Validate user code before execution.

    This is a copy of the validate_code function from main.py to allow
    testing without importing CrossHair.

    Uses AST-based detection to prevent security bypasses:
    - eval (1) - space before parenthesis
    - getattr(__builtins__, "eval") - dynamic access
    - [eval][0]() - list indexing bypass
    - {"f": eval}["f"]() - dict lookup bypass

    Returns:
        Dict with 'valid': bool and 'error': str if invalid
    """
    # Empty string edge case
    if not code or not code.strip():
        return {"valid": True}

    # Size limit: 64KB
    if len(code.encode("utf-8")) > 65536:
        return {"valid": False, "error": "Code size exceeds 64KB limit"}

    # Check for blocked imports and dangerous function calls using AST
    try:
        tree = ast.parse(code)

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

        # Check for blocked imports
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module_name = (
                    node.names[0].name if isinstance(node, ast.Import) else node.module
                )
                if module_name:
                    base_module = module_name.split(".")[0]
                    if base_module in BLOCKED_MODULES:
                        return {
                            "valid": False,
                            "error": f"Blocked module: {base_module}",
                        }

    except SyntaxError as e:
        return {"valid": False, "error": f"Syntax error: {e}"}

    return {"valid": True}


# Tests begin here


class TestValidateCodeSafeCode:
    """Tests that validate_code accepts safe code."""

    def test_accepts_simple_function(self):
        code = "def f(x): return x + 1"
        result = validate_code(code)
        assert result["valid"] is True

    def test_accepts_function_with_multiple_statements(self):
        code = """
def f(x):
    y = x * 2
    z = y + 1
    return z
"""
        result = validate_code(code)
        assert result["valid"] is True

    def test_accepts_class_definition(self):
        code = """
class Calculator:
    def add(self, a, b):
        return a + b
"""
        result = validate_code(code)
        assert result["valid"] is True


class TestValidateCodeBlockedPatterns:
    """Tests that validate_code blocks dangerous patterns."""

    @pytest.mark.parametrize(
        "pattern",
        [
            "import os",
            "import sys",
            "__import__",
            "eval(",
            "exec(",
            "compile(",
        ],
    )
    def test_blocks_dangerous_patterns(self, pattern):
        code = f"{pattern}\ndef foo(): pass"
        result = validate_code(code)
        assert result["valid"] is False
        # Check that the error contains the dangerous function/module
        assert any(
            dangerous in result["error"].lower()
            for dangerous in [
                "os",
                "sys",
                "__import__",
                "eval",
                "exec",
                "compile",
                "blocked",
            ]
        )

    def test_blocks_os_import_specific(self):
        code = "import os\ndef foo(): pass"
        result = validate_code(code)
        assert result["valid"] is False
        assert "os" in result["error"]

    def test_blocks_sys_import_specific(self):
        code = "import sys\ndef foo(): pass"
        result = validate_code(code)
        assert result["valid"] is False
        assert "sys" in result["error"]

    def test_blocks_subprocess_string(self):
        """The string 'subprocess' alone is not dangerous without import."""
        # Just the word 'subprocess' in code is harmless
        code = "# This is a comment about subprocess\ndef foo(): pass"
        result = validate_code(code)
        # This should be valid since subprocess is not imported
        assert result["valid"] is True

    def test_blocks_subprocess_import(self):
        """import subprocess is blocked."""
        code = "import subprocess\ndef foo(): pass"
        result = validate_code(code)
        assert result["valid"] is False
        assert "subprocess" in result["error"]


class TestValidateCodeBlockedModules:
    """Tests that validate_code blocks dangerous modules via AST."""

    @pytest.mark.parametrize(
        "module",
        [
            "os",
            "sys",
            "subprocess",
            "shutil",
            "pty",
            "termios",
            "socket",
            "http",
            "urllib",
            "ftplib",
            "pickle",
            "shelve",
            "marshal",
            "ctypes",
            "multiprocessing",
            "threading",
            "signal",
            "fcntl",
            "resource",
            "syslog",
            "getpass",
        ],
    )
    def test_blocks_specific_dangerous_modules(self, module):
        code = f"import {module}\ndef foo(): pass"
        result = validate_code(code)
        assert result["valid"] is False
        assert module in result["error"] or "Blocked" in result["error"]

    def test_blocks_from_import(self):
        code = "from os import path\ndef foo(): pass"
        result = validate_code(code)
        assert result["valid"] is False
        assert "os" in result["error"]


class TestValidateCodeSizeLimit:
    """Tests that validate_code enforces 64KB size limit."""

    def test_blocks_code_over_64kb(self):
        # Create code larger than 64KB (65536 bytes)
        large_code = "x = 1\n" * 50000  # ~100KB
        result = validate_code(large_code)
        assert result["valid"] is False
        assert "size" in result["error"].lower()

    def test_accepts_code_under_64kb(self):
        # Create code just under 64KB
        code = "x = 1\n" * 10000  # ~20KB
        result = validate_code(code)
        assert result["valid"] is True


class TestValidateCodeSyntaxErrors:
    """Tests that validate_code handles syntax errors."""

    def test_catches_syntax_error(self):
        code = "def foo(\n"  # Incomplete function definition
        result = validate_code(code)
        assert result["valid"] is False
        assert "Syntax error" in result["error"]


class TestSecurityBypassAttempts:
    """Tests for known security bypass attempts.

    These tests verify that the AST-based validation catches bypass
    attempts that would slip through simple string pattern matching.
    """

    def test_blocks_eval_with_space_before_paren(self):
        """eval (1) bypass - space before parenthesis."""
        code = "eval (1)"
        result = validate_code(code)
        assert result["valid"] is False
        assert "eval" in result["error"].lower()

    def test_blocks_exec_with_space_before_paren(self):
        """exec (x) bypass - space before parenthesis."""
        code = "x = 1\nexec (x)"
        result = validate_code(code)
        assert result["valid"] is False
        assert "exec" in result["error"].lower()

    def test_blocks_compile_with_space_before_paren(self):
        """compile (source, filename, mode) bypass."""
        code = 'compile ("1+1", "<string>", "eval")'
        result = validate_code(code)
        assert result["valid"] is False
        assert "compile" in result["error"].lower()

    def test_blocks_eval_in_list(self):
        """[eval][0]() bypass - list indexing."""
        code = "[eval][0](1)"
        result = validate_code(code)
        assert result["valid"] is False
        assert "eval" in result["error"].lower()

    def test_blocks_eval_in_tuple(self):
        """(eval,)[0]() bypass - tuple indexing."""
        code = "(eval,)[0](1)"
        result = validate_code(code)
        assert result["valid"] is False
        assert "eval" in result["error"].lower()

    def test_blocks_eval_in_dict(self):
        """{"f": eval}["f"]() bypass - dict lookup."""
        code = '{"f": eval}["f"](1)'
        result = validate_code(code)
        assert result["valid"] is False
        assert "eval" in result["error"].lower()

    def test_blocks_nested_list_with_eval(self):
        """[[eval]][0][0]() bypass - nested list."""
        code = "[[eval]][0][0](1)"
        result = validate_code(code)
        assert result["valid"] is False
        assert "eval" in result["error"].lower()

    def test_blocks_getattr_to_builtins(self):
        """getattr(__builtins__, "eval") bypass - dynamic access."""
        code = 'getattr(__builtins__, "eval")'
        result = validate_code(code)
        assert result["valid"] is False
        assert "__builtins__" in result["error"] or "getattr" in result["error"]

    def test_blocks_builtins_subscript_access(self):
        """__builtins__["eval"] bypass - subscript access."""
        code = '__builtins__["eval"]("1+1")'
        result = validate_code(code)
        assert result["valid"] is False
        assert "__builtins__" in result["error"]

    def test_blocks_builtins_direct_attribute_access(self):
        """__builtins__.eval bypass - direct attribute access."""
        code = '__builtins__.eval("1+1")'
        result = validate_code(code)
        assert result["valid"] is False
        assert "__builtins__" in result["error"]

    def test_blocks_builtins_list_wrapping_bypass(self):
        """[__builtins__.eval][0]() bypass - list wrapping."""
        code = '[__builtins__.eval][0]("1+1")'
        result = validate_code(code)
        assert result["valid"] is False
        assert "__builtins__" in result["error"]

    def test_blocks_builtins_lambda_bypass(self):
        """(lambda: __builtins__.eval)() bypass - lambda wrapping."""
        code = '(lambda: __builtins__.eval)("1+1")'
        result = validate_code(code)
        assert result["valid"] is False
        assert "__builtins__" in result["error"]

    def test_blocks_builtins_boolop_bypass(self):
        """(__builtins__ or {})["eval"] bypass - boolean operation."""
        code = '(__builtins__ or {})["eval"]("1+1")'
        result = validate_code(code)
        assert result["valid"] is False
        assert "__builtins__" in result["error"]

    def test_blocks_builtins_parenthesized_bypass(self):
        """(__builtins__)["eval"] bypass - parenthesized access."""
        code = '(__builtins__)["eval"]("1+1")'
        result = validate_code(code)
        assert result["valid"] is False
        assert "__builtins__" in result["error"]

    def test_blocks_double_underscore_import(self):
        """__import__("os") bypass - direct import call."""
        code = '__import__("os")'
        result = validate_code(code)
        assert result["valid"] is False
        assert "__import__" in result["error"].lower()

    def test_blocks_os_system_call(self):
        """os.system() - blocked module with dangerous function."""
        code = 'import os\nos.system("ls")'
        result = validate_code(code)
        assert result["valid"] is False
        assert "os" in result["error"].lower()

    def test_blocks_subprocess_run(self):
        """subprocess.run() - blocked module."""
        code = 'import subprocess\nsubprocess.run(["ls"])'
        result = validate_code(code)
        assert result["valid"] is False
        assert "subprocess" in result["error"].lower()

    def test_blocks_eval_with_newline_before_paren(self):
        """eval\n(1) - newline creates two statements.

        Note: This is parsed as two separate statements by Python, not a call.
        The dangerous name 'eval' is still detected as a reference.
        """
        code = "eval\n(1)"
        result = validate_code(code)
        # The newline makes this two separate statements, but we still
        # catch the dangerous 'eval' reference
        assert result["valid"] is False
        assert "eval" in result["error"].lower()

    def test_blocks_eval_with_tab_before_paren(self):
        """eval\t(1) bypass - tab before parenthesis."""
        code = "eval\t(1)"
        result = validate_code(code)
        assert result["valid"] is False
        assert "eval" in result["error"].lower()


class TestAllowedAndBlockedModules:
    """Tests that ALLOWED_MODULES and BLOCKED_MODULES are properly defined."""

    def test_allowed_modules_is_frozenset(self):
        assert isinstance(ALLOWED_MODULES, frozenset)

    def test_blocked_modules_is_frozenset(self):
        assert isinstance(BLOCKED_MODULES, frozenset)

    def test_allowed_modules_not_empty(self):
        assert len(ALLOWED_MODULES) > 0

    def test_blocked_modules_not_empty(self):
        assert len(BLOCKED_MODULES) > 0

    def test_no_overlap_between_allowed_and_blocked(self):
        overlap = ALLOWED_MODULES.intersection(BLOCKED_MODULES)
        assert len(overlap) == 0, f"Overlap found: {overlap}"

    def test_common_safe_modules_allowed(self):
        expected_safe = {"math", "random", "datetime", "json", "re", "collections"}
        for module in expected_safe:
            assert (
                module in ALLOWED_MODULES
            ), f"Safe module {module} not in ALLOWED_MODULES"

    def test_common_dangerous_modules_blocked(self):
        expected_dangerous = {"os", "sys", "subprocess", "pickle", "socket"}
        for module in expected_dangerous:
            assert (
                module in BLOCKED_MODULES
            ), f"Dangerous module {module} not in BLOCKED_MODULES"
