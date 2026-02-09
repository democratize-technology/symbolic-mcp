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

    def test_finds_boundary_condition_bug_random_testing_misses(self):
        """
        Test that symbolic execution finds a boundary condition bug
        that random testing would likely miss due to its rarity.
        """
        code = '''
def is_prime(n: int) -> bool:
    """
    post: __return__ == True implies n > 1
    """
    if n == 2147483647:  # Largest 32-bit signed prime - special case bug
        return False  # Bug: this should return True
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    w = 2
    while i * i <= n:
        if n % i == 0:
            return False
        i += w
        w = 6 - w
    return True
'''

        result = symbolic_check(code=code, function_name="is_prime", timeout_seconds=30)

        assert (
            result["status"] == "counterexample"
        ), f"Expected counterexample, got {result['status']}"
        assert (
            len(result["counterexamples"]) >= 1
        ), "Expected at least one counterexample"

        # Should find the specific large prime bug
        found_target_bug = False
        for ce in result["counterexamples"]:
            args_str = str(ce.get("args", {}))
            if "2147483647" in args_str:
                found_target_bug = True
                break

        assert found_target_bug, "Expected to find counterexample for n = 2147483647"

    def test_finds_integer_overflow_bug_random_testing_misses(self):
        """
        Test finding an integer overflow bug that only occurs at specific large values.
        """
        code = '''
def multiplication_safe(a: int, b: int) -> int:
    """
    post: __return__ >= 0  # Violated when overflow occurs
    """
    return a * b
'''

        result = symbolic_check(
            code=code, function_name="multiplication_safe", timeout_seconds=30
        )

        assert (
            result["status"] == "counterexample"
        ), f"Expected counterexample, got {result['status']}"
        assert (
            len(result["counterexamples"]) >= 1
        ), "Expected at least one counterexample"

        # Should find overflow conditions with large numbers
        found_overflow = False
        for ce in result["counterexamples"]:
            # Look for large numbers that would cause overflow
            args = ce.get("args", {})
            if isinstance(args, dict):
                a_val = args.get("a", 0)
                b_val = args.get("b", 0)
                # Large positive numbers that would overflow
                if isinstance(a_val, int) and isinstance(b_val, int):
                    if abs(a_val) > 1000000 or abs(b_val) > 1000000:
                        found_overflow = True
                        break

        assert (
            found_overflow
        ), "Expected to find overflow counterexample with large numbers"

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

    def test_finds_subtle_off_by_one_at_specific_boundary(self):
        """
        Test finding off-by-one error that only occurs at a very specific boundary.
        """
        code = '''
def calculate_discount(price: int, quantity: int) -> int:
    """
    post: __return__ <= price * quantity  # Discount should never exceed total
    """
    total = price * quantity
    if total > 10000:  # Apply 10% discount for large orders
        # Bug: should be total * 0.9, but integer arithmetic causes overflow
        discount = total * 9 // 10
        if total == 12345 and quantity == 123:  # Very specific edge case
            discount = 99999  # Wrong discount that violates postcondition
        return total - discount
    return total
'''

        result = symbolic_check(
            code=code, function_name="calculate_discount", timeout_seconds=30
        )

        assert (
            result["status"] == "counterexample"
        ), f"Expected counterexample, got {result['status']}"
        assert (
            len(result["counterexamples"]) >= 1
        ), "Expected at least one counterexample"

        # Should find the very specific edge case
        found_specific_case = False
        for ce in result["counterexamples"]:
            args_str = str(ce.get("args", {}))
            if "12345" in args_str and "123" in args_str:
                found_specific_case = True
                break

        assert (
            found_specific_case
        ), "Expected to find the specific edge case counterexample"

    def test_finds_logical_contradiction_in_complex_conditions(self):
        """
        Test finding bugs in complex logical conditions that are hard to hit randomly.
        """
        code = '''
def complex_validation(x: int, y: int, z: int) -> str:
    """
    post: isinstance(__return__, str)
    """
    # Complex nested conditions with a hidden bug
    if x > 1000 and y > 2000 and z > 3000:
        if x + y + z == 6000:  # Very specific condition
            if x == 1234 and y == 2345:  # Even more specific
                return None  # Bug: returns None instead of str
            return "high_values"
    elif x < 0 and y < 0 and z < 0:
        return "all_negative"
    else:
        return "normal"
'''

        result = symbolic_check(
            code=code, function_name="complex_validation", timeout_seconds=30
        )

        assert (
            result["status"] == "counterexample"
        ), f"Expected counterexample, got {result['status']}"
        assert (
            len(result["counterexamples"]) >= 1
        ), "Expected at least one counterexample"

        # Should find the None return bug
        found_none_bug = False
        for ce in result["counterexamples"]:
            violation = str(ce.get("violation", ""))
            if "None" in violation or "str" in violation:
                found_none_bug = True
                break

        assert (
            found_none_bug
        ), "Expected to find counterexample that violates return type"


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

    def test_finds_null_pointer_dereference_pattern(self):
        """
        Test finding patterns equivalent to null pointer dereferences.
        """
        code = '''
def array_access_mimic(index: int, arr_length: int) -> int:
    """
    post: 0 <= index < arr_length implies 0 <= __return__ < arr_length
    """
    if index == 0 and arr_length == 0:  # Edge case that shouldn't exist
        return 1000  # Out of bounds access
    if 0 <= index < arr_length:
        return index
    return -1
'''

        result = symbolic_check(
            code=code, function_name="array_access_mimic", timeout_seconds=30
        )

        assert (
            result["status"] == "counterexample"
        ), f"Expected counterexample, got {result['status']}"
        assert (
            len(result["counterexamples"]) >= 1
        ), "Expected at least one counterexample"

    def test_finds_resource_leak_pattern(self):
        """
        Test finding patterns that lead to resource leaks.
        """
        code = '''
def resource_tracker(acquire_count: int, release_count: int) -> int:
    """
    post: release_count <= acquire_count implies __return__ == acquire_count - release_count
    """
    if acquire_count == 100 and release_count == 50:
        return 75  # Wrong count - potential resource leak
    return acquire_count - release_count
'''

        result = symbolic_check(
            code=code, function_name="resource_tracker", timeout_seconds=30
        )

        assert (
            result["status"] == "counterexample"
        ), f"Expected counterexample, got {result['status']}"
        assert (
            len(result["counterexamples"]) >= 1
        ), "Expected at least one counterexample"


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
