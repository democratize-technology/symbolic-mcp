"""
SPDX-License-Identifier: MIT
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

"""
Section 5.3 Integration Tests - REAL CrossHair Unreachable Exception Analysis

This file contains tests that use actual CrossHair symbolic execution to verify
that exceptions cannot occur for any valid input.

CRITICAL REQUIREMENT: These tests MUST use real CrossHair integration, not mocks.
According to Section 5.3, these tests must demonstrate that symbolic
execution can prove that exceptions are unreachable or find paths to exceptions.
"""

import os
import sys

import pytest

# Add the project root to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import the actual logic functions, not decorated tools
from main import logic_find_path_to_exception as find_path_to_exception

# All tests in this file are integration tests using real CrossHair
pytestmark = pytest.mark.integration


class TestUnreachableException:
    """
    Section 5.3 Test 3: Prove that an exception cannot occur.

    This tests the ability to prove that certain code paths are unreachable
    or that exceptions cannot be triggered for any valid input.
    """

    def test_proves_safe_section_5_3(self):
        """
        Section 5.3 Example: Prove an exception cannot occur.

        This is the EXACT test case from Section 5.3 of the specification.
        """
        # This is the EXACT code from Section 5.3 specification
        code = """
def safe_div(a: int, b: int) -> float:
    if b == 0:
        return 0.0
    return a / b
"""

        result = find_path_to_exception(
            code=code,
            function_name="safe_div",
            exception_type="ZeroDivisionError",
            timeout_seconds=30,
        )

        # Expected result based on Section 5.3 specification
        assert (
            result["status"] == "unreachable"
        ), f"Expected 'unreachable', got {result['status']}"

    def test_proves_assertion_cannot_fail(self):
        """
        Test proving that an assertion cannot fail for any valid input.
        """
        code = '''
def safe_index_access(arr: list, idx: int) -> int:
    """Safe array access that prevents IndexError."""
    if not isinstance(arr, list):
        return -1
    if idx < 0 or idx >= len(arr):
        return -1
    # This assertion should never fail
    assert 0 <= idx < len(arr)
    return arr[idx]
'''

        result = find_path_to_exception(
            code=code,
            function_name="safe_index_access",
            exception_type="AssertionError",
            timeout_seconds=30,
        )

        # The assertion should be proven unreachable
        assert result["status"] in [
            "unreachable",
            "verified",
        ], f"Expected 'unreachable' or 'verified', got {result['status']}"

    def test_proves_bounds_check_prevents_exception(self):
        """
        Test proving that bounds checking prevents array index errors.
        """
        code = '''
def safe_array_access(data: list, index: int) -> int:
    """Access array with bounds checking."""
    n = len(data)
    if 0 <= index < n:
        return data[index]
    else:
        return -1  # Safe fallback
'''

        result = find_path_to_exception(
            code=code,
            function_name="safe_array_access",
            exception_type="IndexError",
            timeout_seconds=30,
        )

        # IndexError should be unreachable due to bounds checking
        assert (
            result["status"] == "unreachable"
        ), f"Expected 'unreachable', got {result['status']}"

    def test_proves_type_check_prevents_exception(self):
        """
        Test proving that type checking prevents type errors.
        """
        code = '''
def safe_math_operation(x) -> float:
    """Safe math operation with type checking."""
    if isinstance(x, (int, float)):
        return x * 2.5
    else:
        return 0.0  # Safe fallback
'''

        result = find_path_to_exception(
            code=code,
            function_name="safe_math_operation",
            exception_type="TypeError",
            timeout_seconds=30,
        )

        # TypeError should be unreachable due to type checking
        assert (
            result["status"] == "unreachable"
        ), f"Expected 'unreachable', got {result['status']}"

    def test_proves_division_by_zero_prevented(self):
        """
        Test proving that division by zero is properly prevented.
        """
        code = '''
def calculate_average(numbers: list) -> float:
    """Calculate average with division by zero protection."""
    if not numbers:
        return 0.0
    total = sum(numbers)
    count = len(numbers)
    # Division by zero is prevented by the not numbers check
    return total / count
'''

        result = find_path_to_exception(
            code=code,
            function_name="calculate_average",
            exception_type="ZeroDivisionError",
            timeout_seconds=30,
        )

        # ZeroDivisionError should be unreachable
        assert (
            result["status"] == "unreachable"
        ), f"Expected 'unreachable', got {result['status']}"

    def test_finds_path_to_key_error(self):
        """
        Test finding a path where KeyError can occur (opposite test).
        """
        code = '''
def unsafe_dict_access(data: dict, key: str) -> int:
    """Unsafe dictionary access without key checking."""
    return data[key]  # Can raise KeyError
'''

        result = find_path_to_exception(
            code=code,
            function_name="unsafe_dict_access",
            exception_type="KeyError",
            timeout_seconds=30,
        )

        # Should find that KeyError is reachable
        assert (
            result["status"] == "reachable"
        ), f"Expected 'reachable', got {result['status']}"

    def test_proves_modulo_by_zero_prevented(self):
        """
        Test proving that modulo by zero is prevented.
        """
        code = '''
def safe_modulo(a: int, b: int) -> int:
    """Safe modulo operation."""
    if b == 0:
        return 0  # Safe fallback
    return a % b
'''

        result = find_path_to_exception(
            code=code,
            function_name="safe_modulo",
            exception_type="ZeroDivisionError",
            timeout_seconds=30,
        )

        # ZeroDivisionError should be unreachable
        assert (
            result["status"] == "unreachable"
        ), f"Expected 'unreachable', got {result['status']}"

    def test_proves_conversion_error_prevented(self):
        """
        Test proving that conversion errors are prevented.
        """
        code = '''
def safe_string_to_int(s: str) -> int:
    """Safe string to int conversion."""
    try:
        return int(s)
    except ValueError:
        return 0  # Safe fallback
'''

        result = find_path_to_exception(
            code=code,
            function_name="safe_string_to_int",
            exception_type="ValueError",
            timeout_seconds=30,
        )

        # ValueError should be unreachable due to exception handling
        assert (
            result["status"] == "unreachable"
        ), f"Expected 'unreachable', got {result['status']}"

    def test_proves_memory_error_prevented_with_limits(self):
        """
        Test proving that memory errors are prevented with reasonable limits.
        """
        code = '''
def safe_large_array_creation(size: int) -> list:
    """Safe large array creation with size limits."""
    MAX_SIZE = 1000000  # Reasonable limit
    if size > MAX_SIZE:
        return []  # Safe fallback
    return [0] * size
'''

        result = find_path_to_exception(
            code=code,
            function_name="safe_large_array_creation",
            exception_type="MemoryError",
            timeout_seconds=30,
        )

        # MemoryError should be unreachable with size limits
        assert (
            result["status"] == "unreachable"
        ), f"Expected 'unreachable', got {result['status']}"

    def test_proves_recursion_limit_prevented(self):
        """
        Test proving that recursion limit errors are prevented.
        """
        code = '''
def safe_recursive_sum(n: int, depth: int = 0) -> int:
    """Safe recursive sum with depth tracking."""
    MAX_DEPTH = 1000
    if depth > MAX_DEPTH:
        return 0  # Prevent stack overflow
    if n <= 0:
        return 0
    return n + safe_recursive_sum(n - 1, depth + 1)
'''

        result = find_path_to_exception(
            code=code,
            function_name="safe_recursive_sum",
            exception_type="RecursionError",
            timeout_seconds=30,
        )

        # RecursionError should be unreachable with depth tracking
        assert (
            result["status"] == "unreachable"
        ), f"Expected 'unreachable', got {result['status']}"

    def test_proves_file_operation_errors_prevented(self):
        """
        Test proving that file operation errors are handled.
        """
        code = '''
def safe_file_read(filename: str) -> str:
    """Safe file reading with error handling."""
    try:
        with open(filename, 'r') as f:
            return f.read()
    except (FileNotFoundError, PermissionError, IOError):
        return ""  # Safe fallback for all file errors
'''

        result = find_path_to_exception(
            code=code,
            function_name="safe_file_read",
            exception_type="FileNotFoundError",
            timeout_seconds=30,
        )

        # FileNotFoundError should be unreachable due to exception handling
        assert (
            result["status"] == "unreachable"
        ), f"Expected 'unreachable', got {result['status']}"

    def test_proves_overflow_prevented_with_checks(self):
        """
        Test proving that overflow is prevented with proper checks.
        """
        code = '''
def safe_multiply(a: int, b: int) -> int:
    """Safe multiplication with overflow checks."""
    # Simple overflow check for demonstration
    if abs(a) > 1000000 or abs(b) > 1000000:
        return 0  # Safe fallback
    return a * b
'''

        result = find_path_to_exception(
            code=code,
            function_name="safe_multiply",
            exception_type="OverflowError",
            timeout_seconds=30,
        )

        # OverflowError should be unreachable with proper checks
        assert result["status"] in [
            "unreachable",
            "verified",
        ], f"Expected 'unreachable' or 'verified', got {result['status']}"


class TestErrorHandling:
    """
    Test error handling with real CrossHair execution (no mocking).
    """

    def test_handles_missing_function_real(self):
        """Test missing function handling without mocks."""
        code = """
def existing_function(x: int) -> int:
    return x
"""

        result = find_path_to_exception(
            code=code,
            function_name="missing_function",
            exception_type="ValueError",
            timeout_seconds=30,
        )

        assert (
            result["status"] == "error"
        ), f"Expected error status, got {result['status']}"
        assert "NameError" in result.get(
            "error_type", ""
        ), f"Expected NameError, got {result.get('error_type')}"

    def test_handles_syntax_error_real(self):
        """Test syntax error handling without mocks."""
        code = """
def bad_function(y: int) -> int
    return y  # Missing colon
"""

        result = find_path_to_exception(
            code=code,
            function_name="bad_function",
            exception_type="ValueError",
            timeout_seconds=30,
        )

        assert (
            result["status"] == "error"
        ), f"Expected error status, got {result['status']}"
        assert "SyntaxError" in result.get(
            "error_type", ""
        ), f"Expected SyntaxError, got {result.get('error_type')}"

    def test_handles_sandbox_violation_real(self):
        """Test sandbox violation handling without mocks."""
        code = """
def restricted_function():
    import os  # Blocked import
    return os.getcwd()
"""

        result = find_path_to_exception(
            code=code,
            function_name="restricted_function",
            exception_type="ValueError",
            timeout_seconds=30,
        )

        assert (
            result["status"] == "error"
        ), f"Expected error status, got {result['status']}"
        # The sandbox should block the os module import
        error_msg = result.get("message", "").lower()
        assert (
            "blocked" in error_msg or "sandbox" in error_msg or "import" in error_msg
        ), f"Expected import/sandbox error, got: {error_msg}"
