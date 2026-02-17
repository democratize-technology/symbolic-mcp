"""Consolidated error handling tests for symbolic execution functions.

All symbolic execution functions share the same validation layer, so testing
error handling once with parameterized tests covers all entry points.
"""

from typing import Callable, Union

import pytest

from main import _ExceptionPathResult, _FunctionComparisonResult, _SymbolicCheckResult
from main import logic_compare_functions as compare_functions
from main import logic_find_path_to_exception as find_path_to_exception
from main import logic_symbolic_check as symbolic_check

# Type alias for the test functions
_TestFunc = Callable[
    [str], Union[_SymbolicCheckResult, _FunctionComparisonResult, _ExceptionPathResult]
]

# All tests in this file are integration tests
pytestmark = pytest.mark.integration


# Test cases for error handling across all functions
SYNTAX_ERROR_CASES = [
    (
        "symbolic_check",
        lambda code: symbolic_check(
            code=code, function_name="broken", timeout_seconds=5
        ),
    ),
    (
        "compare_functions",
        lambda code: compare_functions(
            code=f"{code}\ndef good(x): return x",
            function_a="good",
            function_b="broken",
            timeout_seconds=5,
        ),
    ),
    (
        "find_path_to_exception",
        lambda code: find_path_to_exception(
            code=code,
            function_name="broken",
            exception_type="ValueError",
            timeout_seconds=5,
        ),
    ),
]

MISSING_FUNCTION_CASES = [
    (
        "symbolic_check",
        lambda code: symbolic_check(
            code=code, function_name="nonexistent", timeout_seconds=5
        ),
    ),
    (
        "compare_functions",
        lambda code: compare_functions(
            code=code, function_a="existing", function_b="missing", timeout_seconds=5
        ),
    ),
    (
        "find_path_to_exception",
        lambda code: find_path_to_exception(
            code=code,
            function_name="missing",
            exception_type="ValueError",
            timeout_seconds=5,
        ),
    ),
]

SANDBOX_VIOLATION_CASES = [
    (
        "symbolic_check",
        lambda code: symbolic_check(
            code=code, function_name="restricted", timeout_seconds=5
        ),
    ),
    (
        "compare_functions",
        lambda code: compare_functions(
            code=f"{code}\ndef safe(x): return x",
            function_a="safe",
            function_b="restricted",
            timeout_seconds=5,
        ),
    ),
    (
        "find_path_to_exception",
        lambda code: find_path_to_exception(
            code=code,
            function_name="restricted",
            exception_type="ValueError",
            timeout_seconds=5,
        ),
    ),
]


class TestSyntaxErrorHandling:
    """Tests for syntax error handling across all symbolic execution functions."""

    @pytest.mark.parametrize("func_name,func", SYNTAX_ERROR_CASES)
    def test_handles_syntax_error(self, func_name: str, func: _TestFunc) -> None:
        """Test that all functions handle syntax errors gracefully."""
        code = "def broken(\n"  # Incomplete function
        result = func(code)
        assert result["status"] == "error"
        assert "syntax" in result.get(
            "message", ""
        ).lower() or "SyntaxError" in result.get("error_type", "")


class TestMissingFunctionHandling:
    """Tests for missing function handling across all symbolic execution functions."""

    @pytest.mark.parametrize("func_name,func", MISSING_FUNCTION_CASES)
    def test_handles_missing_function(self, func_name: str, func: _TestFunc) -> None:
        """Test that all functions handle missing functions gracefully."""
        code = "def existing(x): return x"
        result = func(code)
        assert result["status"] == "error"
        assert (
            "NameError" in result.get("error_type", "")
            or "not found" in result.get("message", "").lower()
        )


class TestSandboxViolationHandling:
    """Tests for sandbox violation handling across all symbolic execution functions."""

    @pytest.mark.parametrize("func_name,func", SANDBOX_VIOLATION_CASES)
    def test_blocks_dangerous_imports(self, func_name: str, func: _TestFunc) -> None:
        """Test that all functions block dangerous imports."""
        code = """
import os
def restricted():
    return os.getcwd()
"""
        result = func(code)
        assert result["status"] == "error"
        error_msg = result.get("message", "").lower()
        assert (
            "blocked" in error_msg
            or "sandbox" in error_msg
            or "import" in error_msg
            or "os" in error_msg
        )
