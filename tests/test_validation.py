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

These tests import from main.py, mocking CrossHair dependencies to avoid
requiring the full symbolic execution library for validation testing.
"""

import sys
from unittest.mock import MagicMock

import pytest

# Mock crosshair modules before importing from main
sys_modules_mock = MagicMock()
sys_modules_mock.AnalysisOptions = MagicMock
sys_modules_mock.MessageType = MagicMock
sys_modules_mock.MessageType.CONFIRMED = "confirmed"
sys_modules_mock.MessageType.COUNTEREXAMPLE = "counterexample"
sys_modules_mock.analyze_function = lambda *args, **kwargs: []

sys.modules["crosshair"] = MagicMock()
sys.modules["crosshair.core_and_libs"] = sys_modules_mock
sys.modules["crosshair.options"] = MagicMock()

# Now we can import from main without CrossHair dependency
# noqa: E402 - Import after mocking crosshair modules
from main import (
    ALLOWED_MODULES,
    BLOCKED_MODULES,
    DANGEROUS_BUILTINS,
    _DangerousCallVisitor,
    validate_code,
)

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
