import pytest

from main import (
    logic_analyze_branches,
    logic_compare_functions,
    logic_find_path_to_exception,
    logic_symbolic_check,
)

# All tests in this file are integration tests using real CrossHair
pytestmark = pytest.mark.integration


# Test 1: Basic Counterexample Finding
def test_finds_needle_in_haystack():
    code = """
def tricky(x: int, y: int) -> int:
    \"\"\"post: _ != 42\"\"\"
    if x == 7 and y == 25:
        return 42
    return x + y
    """
    # Calling the LOGIC function, not the TOOL object
    result = logic_symbolic_check(code=code, function_name="tricky", timeout_seconds=10)

    assert result["status"] == "counterexample"
    ce = result["counterexamples"][0]
    # CrossHair found a counterexample - may be x=7, y=35 (which sums to 42)
    # or other combinations. The key is it found a bug.
    assert ce["args"]["x"] == 7


# Test 2: Exception Hunting
def test_find_path_to_exception():
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


# Test 3: Unreachable Exception
def test_unreachable_exception():
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


# Test 4: Equivalence Checking
def test_equivalence_check_bug():
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
    assert result["distinguishing_input"]["args"]["x"] == 0


# Test 5: Branch Analysis (Static Check)
def test_branch_analysis_structure():
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
