"""Integration tests for symbolic-mcp using real CrossHair.

All tests in this file are integration tests that exercise the full
analysis pipeline with real CrossHair symbolic execution.
"""

import pytest

from main import (
    logic_analyze_branches,
    logic_compare_functions,
    logic_find_path_to_exception,
    logic_symbolic_check,
)

# All tests in this file are integration tests using real CrossHair
pytestmark = pytest.mark.integration


# ============================================================================
# Basic Counterexample Finding
# ============================================================================


def test_finds_needle_in_haystack() -> None:
    """Test that symbolic execution can find specific counterexamples.

    Given: A function with a hidden bug at specific input values
    When: symbolic_check is called
    Then: CrossHair finds the counterexample with x=7
    """
    code = """
def tricky(x: int, y: int) -> int:
    \"\"\"post: _ != 42\"\"\"
    if x == 7 and y == 25:
        return 42
    return x + y
    """
    result = logic_symbolic_check(code=code, function_name="tricky", timeout_seconds=10)

    assert result["status"] == "counterexample"
    ce = result["counterexamples"][0]
    # CrossHair found a counterexample - may be x=7, y=35 (which sums to 42)
    # or other combinations. The key is it found a bug.
    assert ce["args"]["x"] == 7


# ============================================================================
# Exception Hunting
# ============================================================================


def test_find_path_to_exception() -> None:
    """Test finding a path that raises a specific exception.

    Given: A function that raises IndexError at x=123
    When: find_path_to_exception is called
    Then: The triggering input x=123 is found
    """
    code = """
def unsafe(x: int) -> int:
    \"\"\"post: True\"\"\"
    if x == 123:
        raise IndexError("Boom")
    return x
    """
    result = logic_find_path_to_exception(
        code=code,
        function_name="unsafe",
        exception_type="IndexError",
        timeout_seconds=10,
    )

    assert result["status"] == "found"
    assert result["triggering_inputs"][0]["args"]["x"] == 123


def test_unreachable_exception() -> None:
    """Test that unreachable exceptions are correctly identified.

    Given: A function with an unreachable exception (x > 0 and x < 0)
    When: find_path_to_exception is called
    Then: Status is 'unreachable'
    """
    code = """
def safe(x: int) -> int:
    \"\"\"post: True\"\"\"
    if x > 0 and x < 0:
        raise IndexError("Impossible")
    return x
    """
    result = logic_find_path_to_exception(
        code=code, function_name="safe", exception_type="IndexError", timeout_seconds=10
    )

    assert result["status"] == "unreachable"


# ============================================================================
# Equivalence Checking
# ============================================================================


def test_equivalence_check_bug() -> None:
    """Test that equivalence checking finds implementation differences.

    Given: Two implementations that differ at x=0
    When: compare_functions is called
    Then: The distinguishing input x=0 is found
    """
    code = """
def impl_a(x: int) -> int:
    return x * 2

def impl_b(x: int) -> int:
    return x + x if x != 0 else 1  # Bug at 0
    """
    result = logic_compare_functions(
        code=code, function_a="impl_a", function_b="impl_b", timeout_seconds=10
    )

    assert result["status"] == "different"
    assert result["distinguishing_input"] is not None
    assert result["distinguishing_input"]["args"]["x"] == 0


# ============================================================================
# Branch Analysis
# ============================================================================


def test_branch_analysis_structure() -> None:
    """Test that branch analysis returns correct structure.

    Given: A function with a single if/else branch
    When: analyze_branches is called
    Then: Branch count and condition are correct
    """
    code = """
def branches(x: int):
    if x > 0:
        return 1
    else:
        return 0
    """
    result = logic_analyze_branches(
        code=code, function_name="branches", timeout_seconds=10
    )

    assert result["status"] == "complete"
    assert result["total_branches"] == 1
    assert "x > 0" in result["branches"][0]["condition"]


# ============================================================================
# Error Path Tests
# ============================================================================


def test_empty_function_handling() -> None:
    """Test handling of empty function body.

    Given: A function with only a pass statement
    When: analyze_branches is called
    Then: Analysis completes with zero branches
    """
    code = """
def empty_func(x: int) -> None:
    pass
    """
    result = logic_analyze_branches(
        code=code, function_name="empty_func", timeout_seconds=10
    )

    assert result["status"] == "complete"
    assert result["total_branches"] == 0
    assert result["cyclomatic_complexity"] == 1  # Base complexity


def test_missing_postcondition_handling() -> None:
    """Test handling of function without postcondition.

    Given: A function without a postcondition docstring
    When: symbolic_check is called
    Then: Analysis completes (CrossHair handles this)
    """
    code = """
def no_postcondition(x: int) -> int:
    return x + 1
    """
    result = logic_symbolic_check(
        code=code, function_name="no_postcondition", timeout_seconds=10
    )

    # Should return a status, not crash
    assert "status" in result


def test_syntax_error_in_code() -> None:
    """Test handling of Python syntax errors.

    Given: Code with invalid Python syntax
    When: Any analysis function is called
    Then: An error status is returned (not an exception)
    """
    code = """
def broken_syntax(x: int) -> int:
    return x +  # Missing operand
    """
    result = logic_symbolic_check(
        code=code, function_name="broken_syntax", timeout_seconds=10
    )

    # Should return error status, not crash
    assert result["status"] == "error"


def test_nonexistent_function() -> None:
    """Test handling of function that doesn't exist.

    Given: Code and a function name that doesn't exist
    When: analyze_branches is called
    Then: The analysis handles it gracefully (error or complete with defaults)
    """
    code = """
def existing_func(x: int) -> int:
    return x + 1
    """
    result = logic_analyze_branches(
        code=code, function_name="nonexistent_func", timeout_seconds=10
    )

    # analyze_branches handles missing functions gracefully by analyzing
    # the whole module - this is acceptable behavior
    assert result["status"] in ("complete", "error")


def test_division_by_zero_detection() -> None:
    """Test finding division by zero paths.

    Given: A function that divides by a parameter
    When: find_path_to_exception is called for ZeroDivisionError
    Then: The path to y=0 is found
    """
    code = """
def divide(x: int, y: int) -> float:
    return x / y
    """
    result = logic_find_path_to_exception(
        code=code,
        function_name="divide",
        exception_type="ZeroDivisionError",
        timeout_seconds=10,
    )

    assert result["status"] == "found"
    assert result["triggering_inputs"][0]["args"]["y"] == 0
