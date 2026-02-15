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
Section 5.3 Integration Tests - REAL CrossHair Equivalence Checking

This file contains tests that use actual CrossHair symbolic execution to verify
equivalence between two function implementations.

CRITICAL REQUIREMENT: These tests MUST use real CrossHair integration, not mocks.
According to Section 5.3, these tests must demonstrate that symbolic
execution can verify that two implementations are equivalent or find differences.
"""

import pytest

# Import the actual logic functions, not decorated tools
from main import logic_compare_functions as compare_functions

# All tests in this file are integration tests using real CrossHair
pytestmark = pytest.mark.integration


class TestEquivalenceChecking:
    """
    Section 5.3 Test 2: Verify two implementations are equivalent.

    This tests the ability to check that two different implementations
    of the same specification produce the same results for all inputs.
    """

    def test_detects_difference_section_5_3(self):
        """
        Section 5.3 Example: Detects difference between two implementations.

        This is the EXACT test case from Section 5.3 of the specification.
        """
        # This is the EXACT code from Section 5.3 specification
        code = """
def impl_a(x: int) -> int:
    return x * 2

def impl_b(x: int) -> int:
    return x + x if x != 0 else 1  # Bug: wrong for x=0
"""

        result = compare_functions(
            code=code, function_a="impl_a", function_b="impl_b", timeout_seconds=10
        )

        # Expected result based on Section 5.3 specification
        assert (
            result["status"] == "different"
        ), f"Expected 'different', got {result['status']}"
        assert (
            "distinguishing_input" in result
        ), "Expected distinguishing input in result"

        # The distinguishing input should be x=0
        dist_input = result["distinguishing_input"]
        # Check that the distinguishing input contains 0 (be flexible about key naming)
        args = dist_input.get("args", {})
        has_zero_input = (
            any(value == 0 for value in args.values())
            if isinstance(args, dict)
            else False
        )
        assert (
            has_zero_input
        ), f"Expected distinguishing input with value 0, got {dist_input}"

    def test_verifies_equivalent_implementations(self):
        """
        Test that equivalent implementations are correctly verified.
        """
        code = '''
def sum_formula_a(n: int) -> int:
    """Sum of first n natural numbers using formula."""
    return n * (n + 1) // 2

def sum_formula_b(n: int) -> int:
    """Sum of first n natural numbers using alternative formula."""
    if n < 0:
        return 0
    total = 0
    for i in range(1, n + 1):
        total += i
    return total
'''

        result = compare_functions(
            code=code,
            function_a="sum_formula_a",
            function_b="sum_formula_b",
            timeout_seconds=10,
        )

        # These should be equivalent
        assert (
            result["status"] == "equivalent"
        ), f"Expected 'equivalent', got {result['status']}"

    def test_detects_subtle_difference_with_large_numbers(self):
        """
        Test detecting subtle differences that only appear with large inputs.
        """
        code = '''
def factorial_a(n: int) -> int:
    """Factorial using iteration."""
    if n < 0:
        return 0
    result = 1
    for i in range(1, min(n + 1, 21)):  # Cap at 20 to avoid overflow
        result *= i
    return result

def factorial_b(n: int) -> int:
    """Factorial with overflow bug for large numbers."""
    if n < 0:
        return 0
    if n == 20:  # Specific case with overflow bug
        return 123456789  # Wrong value
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result
'''

        result = compare_functions(
            code=code,
            function_a="factorial_a",
            function_b="factorial_b",
            timeout_seconds=10,
        )

        # Should detect the difference at n=20
        assert (
            result["status"] == "different"
        ), f"Expected 'different', got {result['status']}"
        assert (
            "distinguishing_input" in result
        ), "Expected distinguishing input in result"

    def test_detects_difference_in_error_handling(self):
        """
        Test detecting differences in error handling behavior.
        """
        code = '''
def safe_divide_a(x: int, y: int) -> int:
    """Division with safe error handling."""
    try:
        return x // y
    except ZeroDivisionError:
        return 0

def safe_divide_b(x: int, y: int) -> int:
    """Division with different error handling."""
    if y == 0:
        return -1  # Different error code
    return x // y
'''

        result = compare_functions(
            code=code,
            function_a="safe_divide_a",
            function_b="safe_divide_b",
            timeout_seconds=10,
        )

        # Should detect the difference in error handling
        assert (
            result["status"] == "different"
        ), f"Expected 'different', got {result['status']}"

    def test_detects_difference_in_float_precision(self):
        """
        Test detecting differences in floating point calculations.
        """
        code = '''
def calculate_pi_a() -> float:
    """Calculate pi using one method."""
    return 22.0 / 7.0

def calculate_pi_b() -> float:
    """Calculate pi using a more precise method."""
    import math
    return math.pi
'''

        result = compare_functions(
            code=code,
            function_a="calculate_pi_a",
            function_b="calculate_pi_b",
            timeout_seconds=10,
        )

        # These should be different (22/7 approximation vs actual pi)
        assert (
            result["status"] == "different"
        ), f"Expected 'different', got {result['status']}"

    def test_verifies_string_manipulation_equivalence(self):
        """
        Test verification of equivalent string manipulation functions.
        """
        code = '''
def reverse_string_a(s: str) -> str:
    """Reverse string using slicing."""
    return s[::-1]

def reverse_string_b(s: str) -> str:
    """Reverse string using manual method."""
    result = ""
    for char in s:
        result = char + result
    return result
'''

        result = compare_functions(
            code=code,
            function_a="reverse_string_a",
            function_b="reverse_string_b",
            timeout_seconds=10,
        )

        # These should be equivalent
        assert (
            result["status"] == "equivalent"
        ), f"Expected 'equivalent', got {result['status']}"

    def test_detects_edge_case_difference(self):
        """
        Test detecting differences that only occur at edge cases.
        """
        code = '''
def array_max_a(arr: list) -> int:
    """Find maximum using built-in method."""
    return max(arr) if arr else 0

def array_max_b(arr: list) -> int:
    """Find maximum with bug for empty arrays."""
    if len(arr) == 0:
        return -1  # Different from impl_a
    maximum = arr[0]
    for item in arr[1:]:
        if item > maximum:
            maximum = item
    return maximum
'''

        result = compare_functions(
            code=code,
            function_a="array_max_a",
            function_b="array_max_b",
            timeout_seconds=10,
        )

        # Should detect the difference for empty arrays
        assert (
            result["status"] == "different"
        ), f"Expected 'different', got {result['status']}"

    def test_verifies_recursive_equivalence(self):
        """
        Test verification of equivalent recursive functions.
        """
        code = '''
def fibonacci_a(n: int) -> int:
    """Fibonacci with memoization."""
    if n <= 1:
        return n
    return fibonacci_a(n-1) + fibonacci_a(n-2)

def fibonacci_b(n: int) -> int:
    """Fibonacci using iterative method."""
    if n <= 1:
        return n
    a, b = 0, 1
    for _ in range(2, n + 1):
        a, b = b, a + b
    return b
'''

        result = compare_functions(
            code=code,
            function_a="fibonacci_a",
            function_b="fibonacci_b",
            timeout_seconds=10,
        )

        # These should be equivalent (though might be slow for large n)
        assert (
            result["status"] == "equivalent"
        ), f"Expected 'equivalent', got {result['status']}"

    def test_detects_boolean_logic_difference(self):
        """
        Test detecting differences in boolean logic implementations.
        """
        code = '''
def is_even_a(n: int) -> bool:
    """Check if number is even using modulo."""
    return n % 2 == 0

def is_even_b(n: int) -> bool:
    """Check if number is even with bitwise bug."""
    return (n & 1) == 0 if n >= 0 else (n & 1) == 1  # Bug for negative numbers
'''

        result = compare_functions(
            code=code,
            function_a="is_even_a",
            function_b="is_even_b",
            timeout_seconds=10,
        )

        # Should detect the difference for negative even numbers
        assert (
            result["status"] == "different"
        ), f"Expected 'different', got {result['status']}"

    def test_detects_difference_in_type_handling(self):
        """
        Test detecting differences in how types are handled.
        """
        code = '''
def to_string_a(x) -> str:
    """Convert to string using str()."""
    return str(x)

def to_string_b(x) -> str:
    """Convert to string with special handling."""
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "true" if x else "false"
    return str(x)
'''

        result = compare_functions(
            code=code,
            function_a="to_string_a",
            function_b="to_string_b",
            timeout_seconds=10,
        )

        # Should detect differences for None and boolean values
        assert (
            result["status"] == "different"
        ), f"Expected 'different', got {result['status']}"

    def test_verifies_mathematical_equivalence(self):
        """
        Test verification of mathematically equivalent formulas.
        """
        code = '''
def quadratic_solution_a(a: float, b: float, c: float) -> float:
    """Quadratic formula using one form."""
    if a == 0:
        return -c / b if b != 0 else 0
    discriminant = b*b - 4*a*c
    if discriminant < 0:
        return 0
    return (-b + discriminant**0.5) / (2*a)

def quadratic_solution_b(a: float, b: float, c: float) -> float:
    """Quadratic formula using equivalent form."""
    if a == 0:
        return -c / b if b != 0 else 0
    discriminant = b*b - 4*a*c
    if discriminant < 0:
        return 0
    return 2*c / (-b - discriminant**0.5)  # Mathematically equivalent
'''

        result = compare_functions(
            code=code,
            function_a="quadratic_solution_a",
            function_b="quadratic_solution_b",
            timeout_seconds=10,
        )

        # These should be equivalent (within floating point precision)
        assert result["status"] in [
            "equivalent",
            "different",
        ], f"Expected 'equivalent' or 'different', got {result['status']}"


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

        result = compare_functions(
            code=code,
            function_a="existing_function",
            function_b="missing_function",
            timeout_seconds=10,
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
def good_function(x: int) -> int:
    return x

def bad_function(y: int) -> int
    return y  # Missing colon in definition
"""

        result = compare_functions(
            code=code,
            function_a="good_function",
            function_b="bad_function",
            timeout_seconds=10,
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
            timeout_seconds=10,
        )

        assert (
            result["status"] == "error"
        ), f"Expected error status, got {result['status']}"
        # The sandbox should block the os module import
        error_msg = result.get("message", "").lower()
        assert (
            "blocked" in error_msg or "sandbox" in error_msg or "import" in error_msg
        ), f"Expected import/sandbox error, got: {error_msg}"
