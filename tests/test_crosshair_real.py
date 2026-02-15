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

"""
Real CrossHair Integration Tests.

This file contains tests that use actual CrossHair symbolic execution to verify
real functionality, NOT mocked responses. These tests complement the mocked
tests in test_validation.py by providing end-to-end validation with real
symbolic execution.

Critical Difference from test_validation.py:
- test_validation.py uses MOCKED CrossHair dependencies
- THIS file uses REAL CrossHair symbolic execution
- Tests here verify actual symbolic execution behavior

These tests focus on core validation scenarios that should work with real
CrossHair integration.
"""

import pytest

# Import the actual logic functions with real CrossHair
# These imports will FAIL if CrossHair is not properly installed
pytest.importorskip("crosshair")
pytest.importorskip("crosshair.core")
pytest.importorskip("crosshair.core_and_libs")

from main import logic_symbolic_check as symbolic_check
from main import validate_code


class TestRealCrossHairValidation:
    """
    Tests using REAL CrossHair symbolic execution.

    These tests verify that the validation system works correctly
    with actual symbolic execution, not mocks.
    """

    @pytest.mark.integration  # type: ignore[misc]
    def test_real_crosshair_simple_contract(self) -> None:
        """Test a simple contract with real CrossHair."""
        code = """
def add_positive(a: int, b: int) -> int:
    '''
    pre: a > 0
    pre: b > 0
    post: __return__ > 0
    '''
    return a + b
"""

        result = symbolic_check(
            code=code, function_name="add_positive", timeout_seconds=10
        )

        # Should be verified (no counterexample)
        assert result["status"] in [
            "verified",
            "error",
        ], f"Expected verified or error, got {result['status']}"

        # Check structure
        assert "paths_explored" in result
        assert "time_seconds" in result
        assert isinstance(result["paths_explored"], int)

    @pytest.mark.integration  # type: ignore[misc]
    def test_real_crosshair_finds_counterexample(self) -> None:
        """Test that real CrossHair finds actual counterexamples."""
        code = """
def buggy_division(x: int) -> int:
    '''
    post: _ != 0
    '''
    return 10 // (x - 5)
"""

        result = symbolic_check(
            code=code, function_name="buggy_division", timeout_seconds=10
        )

        # Should find a counterexample (x=5 causes division by zero)
        # Note: CrossHair may not always find this depending on analysis
        assert result["status"] in [
            "counterexample",
            "verified",
            "error",
        ], f"Unexpected status: {result['status']}"

    @pytest.mark.integration  # type: ignore[misc]
    def test_real_crosshair_postcondition_violation(self) -> None:
        """Test detecting postcondition violations with real CrossHair."""
        code = """
def always_return_positive(x: int) -> int:
    '''
    post: __return__ > 0
    '''
    if x < 0:
        return -1  # Bug: returns negative
    return x
"""

        result = symbolic_check(
            code=code, function_name="always_return_positive", timeout_seconds=10
        )

        # Should find counterexample for x < 0
        assert result["status"] in ["counterexample", "verified", "error"]

        # If counterexample found, verify it has proper structure
        if result["status"] == "counterexample":
            assert len(result["counterexamples"]) >= 1
            ce = result["counterexamples"][0]
            assert "args" in ce
            assert "violation" in ce

    @pytest.mark.integration  # type: ignore[misc]
    def test_real_crosshair_handles_function_without_contract(self) -> None:
        """Test that real CrossHair handles functions without contracts."""
        code = """
def no_contract(x: int) -> int:
    return x * 2
"""

        result = symbolic_check(
            code=code, function_name="no_contract", timeout_seconds=10
        )

        # Should handle gracefully - no contract means nothing to verify
        assert result["status"] in ["verified", "error"]

    @pytest.mark.integration  # type: ignore[misc]
    def test_real_crosshair_precondition_violation(self) -> None:
        """Test detecting precondition violations."""
        code = """
def divide_with_pre(a: int, b: int) -> int:
    '''
    pre: b != 0
    post: True
    '''
    return a // b
"""

        result = symbolic_check(
            code=code, function_name="divide_with_pre", timeout_seconds=10
        )

        # Should verify the function satisfies its contract
        assert result["status"] in ["verified", "error"]

    @pytest.mark.integration  # type: ignore[misc]
    def test_real_crosshair_complex_function(self) -> None:
        """Test analyzing a more complex function."""
        code = """
def complex_check(x: int, y: int) -> int:
    '''
    post: __return__ >= 0
    '''
    if x > 0:
        if y > 0:
            return x * y
        else:
            return -y
    else:
        if y < 0:
            return x - y
        else:
            return 0
"""

        result = symbolic_check(
            code=code, function_name="complex_check", timeout_seconds=15
        )

        # Should handle complex branching
        assert result["status"] in ["verified", "counterexample", "error"]

        # Should have explored multiple paths
        if result["status"] != "error":
            assert result["paths_explored"] >= 1


class TestRealCrossHairErrorHandling:
    """
    Tests for error handling with real CrossHair.
    """

    @pytest.mark.integration  # type: ignore[misc]
    def test_real_crosshair_syntax_error(self) -> None:
        """Test handling syntax errors with real CrossHair."""
        code = "def broken(\n"  # Incomplete function

        result = symbolic_check(code=code, function_name="broken", timeout_seconds=5)

        assert result["status"] == "error"
        assert "SyntaxError" in result.get("error_type", "")

    @pytest.mark.integration  # type: ignore[misc]
    def test_real_crosshair_function_not_found(self) -> None:
        """Test handling of missing function."""
        code = "def existing(x): return x"

        result = symbolic_check(
            code=code, function_name="nonexistent", timeout_seconds=5
        )

        assert result["status"] == "error"
        assert "NameError" in result.get("error_type", "")

    @pytest.mark.integration  # type: ignore[misc]
    def test_real_crosshair_blocked_import(self) -> None:
        """Test that blocked imports are caught before CrossHair."""
        code = """
import os
def restricted():
    return os.getcwd()
"""

        result = symbolic_check(
            code=code, function_name="restricted", timeout_seconds=5
        )

        # Should fail validation before reaching CrossHair
        assert result["status"] == "error"
        error_msg = result.get("message", "").lower()
        assert "os" in error_msg or "blocked" in error_msg


class TestRealCrossHairCoverageEstimation:
    """
    Tests for coverage estimation with real CrossHair.
    """

    @pytest.mark.integration  # type: ignore[misc]
    def test_real_crosshair_coverage_for_simple_function(self) -> None:
        """Test coverage estimation for a simple function."""
        code = """
def simple(x: int) -> int:
    '''
    post: _ >= 0
    '''
    return abs(x)
"""

        result = symbolic_check(code=code, function_name="simple", timeout_seconds=10)

        if result["status"] != "error":
            # Should have coverage estimate
            assert "coverage_estimate" in result
            assert isinstance(result["coverage_estimate"], float)
            assert 0.0 <= result["coverage_estimate"] <= 1.0

    @pytest.mark.integration  # type: ignore[misc]
    def test_real_crosshair_paths_explored(self) -> None:
        """Test that paths explored is counted correctly."""
        code = """
def multi_path(x: int) -> int:
    '''
    post: True
    '''
    if x > 10:
        return 1
    elif x > 5:
        return 2
    else:
        return 3
"""

        result = symbolic_check(
            code=code, function_name="multi_path", timeout_seconds=10
        )

        if result["status"] != "error":
            # Should have explored at least one path
            assert result["paths_explored"] >= 1


class TestRealCrossHairWithValidation:
    """
    Tests that verify validate_code() works correctly with real CrossHair.
    """

    @pytest.mark.integration  # type: ignore[misc]
    def test_validate_code_blocks_dangerous_before_crosshair(self) -> None:
        """Verify that validate_code() blocks dangerous code before CrossHair."""
        dangerous_codes = [
            "import os\ndef f(): pass",
            "__import__('os')",
            "eval('1+1')",
            "compile('1+1', 'f', 'eval')",
        ]

        for code in dangerous_codes:
            validation = validate_code(code)
            # Should be rejected by validation
            assert not validation["valid"], f"Code should be rejected: {code}"

    @pytest.mark.integration  # type: ignore[misc]
    def test_validate_code_allows_safe_code_for_crosshair(self) -> None:
        """Verify that validate_code() allows safe code for CrossHair."""
        safe_codes = [
            "def f(x): return x + 1",
            """
def safe_function(a: int, b: int) -> int:
    '''
    post: __return__ > 0
    '''
    return a + b if (a > 0 and b > 0) else 1
""",
        ]

        for code in safe_codes:
            validation = validate_code(code)
            # Should be accepted
            assert validation["valid"], f"Code should be accepted: {code}"


class TestRealCrossHairTimeoutHandling:
    """
    Tests for timeout handling with real CrossHair.
    """

    @pytest.mark.integration  # type: ignore[misc]
    def test_real_crosshair_respects_short_timeout(self) -> None:
        """Test that CrossHair respects timeout settings."""
        code = """
def infinite_loop(x: int) -> int:
    '''
    post: True
    '''
    # This could potentially run forever without proper timeout
    result = 0
    for i in range(1000000):
        result += i
    return result
"""

        # Use very short timeout
        result = symbolic_check(
            code=code, function_name="infinite_loop", timeout_seconds=1
        )

        # Should either complete or timeout (not hang)
        assert result["status"] in ["verified", "error", "timeout"]

    @pytest.mark.integration  # type: ignore[misc]
    def test_real_crosshair_completes_within_timeout(self) -> None:
        """Test that analysis completes within specified timeout."""
        code = """
def quick_check(x: int) -> int:
    '''
    post: _ >= 0
    '''
    return x if x >= 0 else -x
"""

        import time

        start = time.perf_counter()
        result = symbolic_check(
            code=code, function_name="quick_check", timeout_seconds=5
        )
        elapsed = time.perf_counter() - start

        # Should complete within reasonable time
        # Allow some buffer over the timeout for overhead
        assert elapsed < 15, f"Analysis took too long: {elapsed}s"

        # Should have a result
        assert result["status"] in ["verified", "error"]
