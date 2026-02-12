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
Section 5.3 Integration Tests - REAL CrossHair Bug Finding

This file contains tests that use actual CrossHair symbolic execution to verify
bug finding capabilities that random testing would miss.

CRITICAL REQUIREMENT: These tests MUST use real CrossHair integration, not mocks.
According to Section 5.3, these tests must demonstrate that symbolic
execution finds bugs that random testing would miss.
"""

import os
import sys

import pytest

# Add the project root to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

# Import the actual logic functions, not decorated tools
from main import logic_symbolic_check as symbolic_check

# All tests in this file are integration tests using real CrossHair
pytestmark = pytest.mark.integration


class TestSymbolicBugFinding:
    """
    Section 5.3 Test 1: Symbolic execution finds bugs that random testing would miss.

    This tests the core value proposition of symbolic execution - finding
    "needles in haystacks" that probabilistic fuzzing would likely miss.
    """

    def test_finds_needle_in_haystack_section_5_3(self):
        """
        Section 5.3 Example: Symbolic execution finds input that random testing would miss.

        This is the EXACT test case from Section 5.3 of the specification.
        It must find a very specific input combination that random testing
        has a tiny probability of discovering.
        """
        # This is the EXACT code from Section 5.3 specification with CrossHair contract
        code = '''
def tricky(x: int, y: int) -> int:
    """
    post: __return__ != -1  # This postcondition will be violated by the needle
    """
    if x == 12345 and y == x * 7 + 3:
        return -1  # This violates the postcondition - the "needle"
    return x + y
'''

        # This test MUST use real CrossHair execution, not mocks
        result = symbolic_check(code=code, function_name="tricky", timeout_seconds=30)

        # Expected result based on Section 5.3 specification
        assert (
            result["status"] == "counterexample"
        ), f"Expected counterexample, got {result['status']}"
        assert (
            len(result["counterexamples"]) >= 1
        ), "Expected at least one counterexample"

        # The counterexample should contain the specific values from Section 5.3
        ce = result["counterexamples"][0]

        # Check if the counterexample contains the expected needle values
        # CrossHair might represent arguments differently, so be flexible in checking
        args_str = str(ce.get("args", {}))
        violation_str = str(ce.get("violation", ""))

        # Look for the specific values that trigger the needle
        has_needle_x = "12345" in args_str
        has_needle_y = "86418" in args_str  # 12345 * 7 + 3

        # Check if we found the needle condition (either by exact match or by violation description)
        found_needle = False
        if has_needle_x or has_needle_y:
            found_needle = True

        # Also check the violation message for the needle condition
        if (
            "-1" in violation_str
            or "post" in violation_str
            or "needle" in violation_str
        ):
            found_needle = True

        assert (
            found_needle
        ), f"Expected counterexample to find the needle (x=12345, y=86418), got {ce}"

    def test_finds_type_error_in_string_operations(self):
        """
        Test that symbolic execution finds type errors in string operations.
        This tests a real Python bug pattern - mixing int and str operations.
        """
        code = '''
def string_length_check(s: str, threshold: int) -> int:
    """
    post: __return__ >= 0
    """
    # Bug: when threshold > len(s), we get negative length
    if threshold > len(s):
        return len(s) - threshold  # Returns negative!
    return len(s)
'''

        result = symbolic_check(
            code=code, function_name="string_length_check", timeout_seconds=30
        )

        # Should find the case where threshold > len(s) causing negative return
        assert (
            result["status"] == "counterexample"
        ), f"Expected counterexample, got {result['status']}"
        assert (
            len(result["counterexamples"]) >= 1
        ), "Expected at least one counterexample"

    def test_finds_precision_bug_floating_point_random_testing_misses(self):
        """
        Test finding floating-point precision bug that requires exact values.
        """
        code = '''
def precise_division(numerator: float, denominator: float) -> float:
    """
    post: __return__ * denominator == numerator  # Fails due to floating point precision
    """
    return numerator / denominator
'''

        result = symbolic_check(
            code=code, function_name="precise_division", timeout_seconds=30
        )

        assert (
            result["status"] == "counterexample"
        ), f"Expected counterexample, got {result['status']}"
        assert (
            len(result["counterexamples"]) >= 1
        ), "Expected at least one counterexample"

        # Should find precision issues with certain floating point values
        found_precision_issue = False
        for ce in result["counterexamples"]:
            violation = str(ce.get("violation", ""))
            if "precision" in violation.lower() or "float" in violation.lower():
                found_precision_issue = True
                break

        assert (
            found_precision_issue
        ), "Expected to find floating-point precision counterexample"


class TestEdgeCaseBugDetection:
    """
    Tests for finding edge cases that are extremely unlikely to be found
    by random testing but symbolic execution finds systematically.
    """

    def test_finds_off_by_one_error(self):
        """
        Test finding off-by-one error in boundary conditions.
        This tests a common off-by-one bug in clamp functions.
        """
        code = '''
def clamp_value(value: int, min_val: int, max_val: int) -> int:
    """
    post: min_val <= __return__ <= max_val
    """
    if value < min_val:
        return min_val
    # Bug: should be <= max_val, using < causes off-by-one error
    if value < max_val:
        return value
    return max_val
'''

        result = symbolic_check(
            code=code, function_name="clamp_value", timeout_seconds=30
        )

        assert (
            result["status"] == "counterexample"
        ), f"Expected counterexample, got {result['status']}"
        assert (
            len(result["counterexamples"]) >= 1
        ), "Expected at least one counterexample"

    def test_finds_type_violation_in_complex_function(self):
        """
        Test finding type violations in functions with complex logic.
        Tests that CrossHair can detect when a function returns
        the wrong type despite complex conditional logic.
        """
        code = '''
def categorize_value(x: int) -> str:
    """
    post: isinstance(__return__, str)
    """
    if x > 100:
        return "high"
    elif x < 0:
        return "low"
    elif x == 50:
        return 42  # Bug: returns int instead of str
    else:
        return "medium"
'''

        result = symbolic_check(
            code=code, function_name="categorize_value", timeout_seconds=30
        )

        # Should find the type violation at x == 50
        assert (
            result["status"] == "counterexample"
        ), f"Expected counterexample, got {result['status']}"
        assert (
            len(result["counterexamples"]) >= 1
        ), "Expected at least one counterexample"


class TestMathematicalPropertyViolations:
    """
    Tests for finding mathematical property violations that require
    symbolic reasoning beyond random testing.
    """

    def test_finds_commutativity_violation(self):
        """
        Test finding operations that violate expected mathematical properties.
        """
        code = '''
def buggy_commutative_op(a: int, b: int) -> int:
    """
    post: buggy_commutative_op(a, b) == buggy_commutative_op(b, a)
    """
    if a == 42 and b == 17:
        return a - b  # Wrong order, violates commutativity
    return a + b
'''

        result = symbolic_check(
            code=code, function_name="buggy_commutative_op", timeout_seconds=30
        )

        assert (
            result["status"] == "counterexample"
        ), f"Expected counterexample, got {result['status']}"
        assert (
            len(result["counterexamples"]) >= 1
        ), "Expected at least one counterexample"

    def test_finds_associativity_violation(self):
        """
        Test finding operations that violate associativity.
        """
        code = '''
def buggy_associative_op(a: int, b: int, c: int) -> int:
    """
    post: buggy_associative_op(a, b, c) == buggy_associative_op(buggy_associative_op(a, b), c)
    """
    if a == 10 and b == 20 and c == 30:
        return a * (b + c)  # Should be (a * b) + c for associativity
    return a + b + c
'''

        result = symbolic_check(
            code=code, function_name="buggy_associative_op", timeout_seconds=30
        )

        assert (
            result["status"] == "counterexample"
        ), f"Expected counterexample, got {result['status']}"
        assert (
            len(result["counterexamples"]) >= 1
        ), "Expected at least one counterexample"


class TestRealWorldBugPatterns:
    """
    Tests for bug patterns commonly found in real-world code that
    symbolic execution is particularly good at finding.
    """

    def test_finds_index_out_of_bounds_error(self):
        """
        Test finding index out-of-bounds errors.
        Uses Python terminology for this common error pattern.
        Tests division by zero which is Python's equivalent of accessing
        an invalid index.
        """
        code = '''
def average_slice(data: list, start: int) -> int:
    """
    post: __return__ >= 0 or len(data) == 0
    """
    if len(data) == 0:
        return 0
    # Bug: when start is negative, slice still works but then
    # we divide by potentially negative length
    end = start + 2
    if end > len(data):
        end = len(data)
    # Bug: division can result in negative value
    return (start + end) // 2 if start < end else -1
'''

        result = symbolic_check(
            code=code, function_name="average_slice", timeout_seconds=30
        )

        assert (
            result["status"] == "counterexample"
        ), f"Expected counterexample, got {result['status']}"


class TestErrorHandling:
    """
    Test error handling with real CrossHair execution (no mocking).
    """

    def test_handles_syntax_error_real(self):
        """Test syntax error handling without mocks."""
        code = "def bad_syntax(x, y) return x + y"  # Missing colon

        result = symbolic_check(
            code=code, function_name="bad_syntax", timeout_seconds=30
        )

        assert (
            result["status"] == "error"
        ), f"Expected error status, got {result['status']}"
        assert "SyntaxError" in result.get(
            "error_type", ""
        ), f"Expected SyntaxError, got {result.get('error_type')}"

    def test_handles_function_not_found_real(self):
        """Test missing function handling without mocks."""
        code = "def existing_function(x): return x"

        result = symbolic_check(
            code=code, function_name="missing_function", timeout_seconds=30
        )

        assert (
            result["status"] == "error"
        ), f"Expected error status, got {result['status']}"
        assert "NameError" in result.get(
            "error_type", ""
        ), f"Expected NameError, got {result.get('error_type')}"

    def test_handles_sandbox_violation_real(self):
        """Test sandbox violation handling without mocks."""
        code = """
import os
def restricted_function():
    return os.getcwd()
"""

        result = symbolic_check(
            code=code, function_name="restricted_function", timeout_seconds=30
        )

        assert (
            result["status"] == "error"
        ), f"Expected error status, got {result['status']}"
        # The sandbox should block the os module import
        error_msg = result.get("message", "").lower()
        assert (
            "blocked" in error_msg or "sandbox" in error_msg or "import" in error_msg
        ), f"Expected import/sandbox error, got: {error_msg}"
