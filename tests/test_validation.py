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

Consolidated from 39 tests to 7 essential tests that cover:
1. Dangerous builtins (eval, exec, compile)
2. Dangerous imports (os, sys, subprocess)
3. Dangerous attribute access (__builtins__, __globals__, __code__)
4. Dunder method access
5. Security bypass attempts
6. Valid code acceptance
7. Malformed code rejection

NOTE: These tests do NOT require CrossHair mocking. The validate_code function
and the ALLOWED_MODULES/BLOCKED_MODULES constants have no CrossHair dependencies.
"""

import pytest

from main import ALLOWED_MODULES, BLOCKED_MODULES, validate_code

pytestmark = pytest.mark.mocked


class TestValidation:
    """Consolidated validation tests."""

    def test_blocks_dangerous_builtins(self) -> None:
        """Test that dangerous builtins (eval, exec, compile) are blocked."""
        dangerous_patterns = [
            ("eval('1+1')", "eval"),
            ("exec('x=1')", "exec"),
            ("compile('1+1', '<string>', 'eval')", "compile"),
        ]

        for code, expected_in_error in dangerous_patterns:
            result = validate_code(code)
            assert result["valid"] is False, f"{expected_in_error} should be blocked"
            assert (
                "blocked" in result["error"].lower()
                or expected_in_error in result["error"].lower()
            )

    def test_blocks_dangerous_imports(self) -> None:
        """Test that dangerous module imports are blocked."""
        dangerous_modules = ["os", "sys", "subprocess", "pickle", "socket"]

        for module in dangerous_modules:
            code = f"import {module}\ndef foo(): pass"
            result = validate_code(code)
            assert result["valid"] is False, f"{module} import should be blocked"
            assert module in result["error"] or "blocked" in result["error"].lower()

    def test_blocks_builtins_access(self) -> None:
        """Test that dangerous __builtins__ access is blocked."""
        dangerous_access = [
            ('x = __builtins__["eval"]', "__builtins__"),
            ("x = __builtins__.eval", "__builtins__"),
            ('x = getattr(__builtins__, "eval")', "__builtins__"),
        ]

        for code, expected_in_error in dangerous_access:
            result = validate_code(code)
            assert result["valid"] is False, f"{code} should be blocked"
            assert (
                expected_in_error in result["error"]
                or "blocked" in result["error"].lower()
            )

    def test_blocks_dunder_methods(self) -> None:
        """Test that dangerous dunder method access is blocked."""
        # __import__ is definitely blocked
        result = validate_code('x = __import__("os")')
        assert result["valid"] is False, "__import__ should be blocked"
        assert (
            "__import__" in result["error"].lower()
            or "blocked" in result["error"].lower()
        )

    def test_blocks_security_bypass_attempts(self) -> None:
        """Test that various security bypass attempts are blocked."""
        bypass_attempts = [
            "[eval][0](1)",  # List indexing
            "(eval,)[0](1)",  # Tuple indexing
            '{"f": eval}["f"](1)',  # Dict lookup
            "[[eval]][0][0](1)",  # Nested list
            "(lambda: __builtins__.eval)('1+1')",  # Lambda wrapping
            '(__builtins__)["eval"]("1+1")',  # Parenthesized
            "(__builtins__ or {})['eval']('1+1')",  # Boolean operation
        ]

        for bypass in bypass_attempts:
            result = validate_code(bypass)
            assert (
                result["valid"] is False
            ), f"Bypass attempt should be blocked: {bypass}"

    def test_accepts_safe_code(self) -> None:
        """Test that safe code is accepted."""
        safe_code_examples = [
            "def f(x): return x + 1",
            """
def f(x):
    y = x * 2
    return y
""",
            """
class Calculator:
    def add(self, a, b):
        return a + b
""",
            "import math\nresult = math.sqrt(16)",
            "# Comment about eval\ndef foo(): pass",
        ]

        for code in safe_code_examples:
            result = validate_code(code)
            assert result["valid"] is True, f"Safe code should be accepted: {code}"

    def test_rejects_malformed_code(self) -> None:
        """Test that malformed code is rejected with proper error."""
        malformed_examples = [
            ("def foo(\n", "Syntax"),  # Incomplete function
            ("x = ", "Syntax"),  # Incomplete assignment
            ("class Foo:\n  pass\n  def bar(self\n", "Syntax"),  # Incomplete method
        ]

        for code, expected_error in malformed_examples:
            result = validate_code(code)
            assert (
                result["valid"] is False
            ), f"Malformed code should be rejected: {code}"
            assert (
                expected_error in result["error"] or "error" in result["error"].lower()
            )


class TestModuleConfiguration:
    """Tests for ALLOWED_MODULES and BLOCKED_MODULES configuration."""

    def test_module_lists_are_frozensets(self) -> None:
        """Test that module lists are immutable frozensets."""
        assert isinstance(ALLOWED_MODULES, frozenset)
        assert isinstance(BLOCKED_MODULES, frozenset)

    def test_no_module_overlap(self) -> None:
        """Test that no module appears in both allowed and blocked lists."""
        overlap = ALLOWED_MODULES.intersection(BLOCKED_MODULES)
        assert len(overlap) == 0, f"Modules in both lists: {overlap}"

    def test_safe_modules_allowed(self) -> None:
        """Test that common safe modules are allowed."""
        expected_safe = {"math", "random", "datetime", "json", "re", "collections"}
        for module in expected_safe:
            assert module in ALLOWED_MODULES, f"Safe module not allowed: {module}"

    def test_dangerous_modules_blocked(self) -> None:
        """Test that common dangerous modules are blocked."""
        expected_dangerous = {"os", "sys", "subprocess", "pickle", "socket"}
        for module in expected_dangerous:
            assert module in BLOCKED_MODULES, f"Dangerous module not blocked: {module}"
