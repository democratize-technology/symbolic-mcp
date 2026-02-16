"""Consolidated error handling tests for symbolic execution functions.

This module consolidates duplicate error handling tests from:
- test_crosshair_real.py
- test_equivalence_check.py
- test_symbolic_finds_bug.py
- test_unreachable_exception.py

All symbolic execution functions share the same validation layer, so testing
error handling once here covers all entry points.
"""

import pytest

from main import logic_compare_functions as compare_functions
from main import logic_find_path_to_exception as find_path_to_exception
from main import logic_symbolic_check as symbolic_check

# All tests in this file are integration tests
pytestmark = pytest.mark.integration


class TestSyntaxErrorHandling:
    """Tests for syntax error handling across all symbolic execution functions."""

    def test_symbolic_check_handles_syntax_error(self) -> None:
        """Test that symbolic_check handles syntax errors gracefully."""
        code = "def broken(\n"  # Incomplete function

        result = symbolic_check(code=code, function_name="broken", timeout_seconds=5)

        assert result["status"] == "error"
        assert "SyntaxError" in result.get("error_type", "")

    def test_compare_functions_handles_syntax_error(self) -> None:
        """Test that compare_functions handles syntax errors gracefully."""
        code = """
def good_function(x: int) -> int:
    return x

def bad_function(y: int) -> int
    return y  # Missing colon in definition
"""

        result = compare_functions(
            code=code,
            function_a="good_function",
            function_b="bad_function",
            timeout_seconds=5,
        )

        assert result["status"] == "error"
        # Syntax errors are caught by validation layer as ValidationError
        assert "SyntaxError" in result.get(
            "error_type", ""
        ) or "Validation" in result.get("error_type", "")

    def test_find_path_to_exception_handles_syntax_error(self) -> None:
        """Test that find_path_to_exception handles syntax errors gracefully."""
        code = """
def bad_function(y: int) -> int
    return y  # Missing colon
"""

        result = find_path_to_exception(
            code=code,
            function_name="bad_function",
            exception_type="ValueError",
            timeout_seconds=5,
        )

        assert result["status"] == "error"
        assert "syntax" in result.get("message", "").lower()


class TestMissingFunctionHandling:
    """Tests for missing function handling across all symbolic execution functions."""

    def test_symbolic_check_handles_missing_function(self) -> None:
        """Test that symbolic_check handles missing functions gracefully."""
        code = "def existing(x): return x"

        result = symbolic_check(
            code=code, function_name="nonexistent", timeout_seconds=5
        )

        assert result["status"] == "error"
        assert "NameError" in result.get("error_type", "")

    def test_compare_functions_handles_missing_function(self) -> None:
        """Test that compare_functions handles missing functions gracefully."""
        code = """
def existing_function(x: int) -> int:
    return x
"""

        result = compare_functions(
            code=code,
            function_a="existing_function",
            function_b="missing_function",
            timeout_seconds=5,
        )

        assert result["status"] == "error"
        assert "NameError" in result.get("error_type", "")

    def test_find_path_to_exception_handles_missing_function(self) -> None:
        """Test that find_path_to_exception handles missing functions gracefully."""
        code = """
def existing_function(x: int) -> int:
    return x
"""

        result = find_path_to_exception(
            code=code,
            function_name="missing_function",
            exception_type="ValueError",
            timeout_seconds=5,
        )

        assert result["status"] == "error"
        assert "NameError" in result.get("error_type", "")


class TestSandboxViolationHandling:
    """Tests for sandbox violation handling across all symbolic execution functions."""

    def test_symbolic_check_blocks_dangerous_imports(self) -> None:
        """Test that symbolic_check blocks dangerous imports."""
        code = """
import os
def restricted():
    return os.getcwd()
"""

        result = symbolic_check(
            code=code, function_name="restricted", timeout_seconds=5
        )

        assert result["status"] == "error"
        error_msg = result.get("message", "").lower()
        assert "os" in error_msg or "blocked" in error_msg

    def test_compare_functions_blocks_dangerous_imports(self) -> None:
        """Test that compare_functions blocks dangerous imports."""
        code = """
def safe_function(x: int) -> int:
    return x * 2

def unsafe_function(x: int) -> int:
    import os  # Blocked import
    return x * 2
"""

        result = compare_functions(
            code=code,
            function_a="safe_function",
            function_b="unsafe_function",
            timeout_seconds=5,
        )

        assert result["status"] == "error"
        error_msg = result.get("message", "").lower()
        assert "blocked" in error_msg or "sandbox" in error_msg or "import" in error_msg

    def test_find_path_to_exception_blocks_dangerous_imports(self) -> None:
        """Test that find_path_to_exception blocks dangerous imports."""
        code = """
def restricted_function():
    import os  # Blocked import
    return os.getcwd()
"""

        result = find_path_to_exception(
            code=code,
            function_name="restricted_function",
            exception_type="ValueError",
            timeout_seconds=5,
        )

        assert result["status"] == "error"
        error_msg = result.get("message", "").lower()
        assert "blocked" in error_msg or "sandbox" in error_msg or "import" in error_msg
