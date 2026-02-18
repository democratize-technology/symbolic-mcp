"""
Tests for cyclomatic complexity calculation in logic_analyze_branches.

ISSUE #6: Fix complexity calculation logic - ast.walk() double-counts elif branches.

Cyclomatic complexity formula:
    CC = 1 + (number of decision points)

Decision points:
- if statements (including elif)
- while loops
- for loops
- each additional operand in BoolOp (and/or)

The bug: ast.walk() visits all nodes recursively. When counting if statements,
the code explicitly counts elif branches, but ast.walk() also visits those
same elif nodes as separate If nodes, causing double-counting.
"""

import pytest

from main import logic_analyze_branches as analyze_branches

# Test cases for cyclomatic complexity
# Format: (code, function_name, expected_complexity, description)
COMPLEXITY_CASES = [
    # Simple function with no decision points
    (
        """
def simple_function(x: int) -> int:
    return x + 1
""",
        "simple_function",
        1,
        "function with no decision points should have complexity 1",
    ),
    # Single if statement
    (
        """
def single_if(x: int) -> int:
    if x > 0:
        return 1
    return 0
""",
        "single_if",
        2,
        "single if statement: complexity = 1 (base) + 1 (if) = 2",
    ),
    # if/elif chain - THIS EXPOSES THE BUG
    (
        """
def if_elif_chain(x: int) -> int:
    if x > 10:
        return 1
    elif x > 5:
        return 2
    elif x > 0:
        return 3
    else:
        return 0
""",
        "if_elif_chain",
        4,
        "if/elif chain: 1 (base) + 3 (if + 2 elifs) = 4, buggy would return 6",
    ),
    # Nested if statements
    (
        """
def nested_if(x: int, y: int) -> int:
    if x > 0:
        if y > 0:
            return 1
        return 2
    return 0
""",
        "nested_if",
        3,
        "nested if statements: 1 (base) + 2 (two if statements) = 3",
    ),
    # While loop
    (
        """
def while_loop(n: int) -> int:
    total = 0
    while n > 0:
        total += n
        n -= 1
    return total
""",
        "while_loop",
        2,
        "while loop adds one decision point: 1 (base) + 1 (while) = 2",
    ),
    # For loop
    (
        """
def for_loop(items: list) -> int:
    total = 0
    for item in items:
        total += item
    return total
""",
        "for_loop",
        2,
        "for loop adds one decision point: 1 (base) + 1 (for) = 2",
    ),
    # BoolOp with 'and' (3 values -> +2 complexity)
    (
        """
def boolop_and(x: int, y: int, z: int) -> bool:
    if x > 0 and y > 0 and z > 0:
        return True
    return False
""",
        "boolop_and",
        4,
        "BoolOp 'and': 1 (base) + 1 (if) + 2 (BoolOp 3 values) = 4",
    ),
    # BoolOp with 'or' (2 values -> +1 complexity)
    (
        """
def boolop_or(x: int, y: int) -> bool:
    if x < 0 or x > 100:
        return True
    return False
""",
        "boolop_or",
        3,
        "BoolOp 'or': 1 (base) + 1 (if) + 1 (BoolOp 2 values) = 3",
    ),
    # Complex function with multiple decision point types
    (
        """
def complex_function(items: list, x: int) -> int:
    total = 0
    for item in items:
        if item > 0:
            total += item
        elif item < 0:
            total -= item

    while x > 0:
        total += x
        x -= 1

    if x > 10 or x < -10:
        return total

    return total
""",
        "complex_function",
        7,
        "complex: 1 (base) + 1 (for) + 1 (if) + 1 (elif) + 1 (while) + 1 (if) + 1 (BoolOp) = 7",
    ),
    # if/elif without else
    (
        """
def if_elif_no_else(x: int) -> int:
    if x > 10:
        return 1
    elif x > 5:
        return 2
    return 0
""",
        "if_elif_no_else",
        3,
        "if/elif no else: 1 (base) + 2 (if + 1 elif) = 3",
    ),
    # Multiple BoolOps
    (
        """
def multiple_boolops(x: int, y: int, z: int) -> bool:
    if x > 0 and y > 0:
        if z < 0 or z > 100:
            return True
    return False
""",
        "multiple_boolops",
        5,
        "multiple BoolOps: 1 (base) + 2 (if) + 1 (and) + 1 (or) = 5",
    ),
    # Simple if/else without elif
    (
        """
def if_else(x: int) -> int:
    if x > 0:
        return 1
    else:
        return 0
""",
        "if_else",
        2,
        "if/else: 1 (base) + 1 (if) = 2 (else doesn't add complexity)",
    ),
]


@pytest.mark.parametrize("code,func_name,expected,description", COMPLEXITY_CASES)
def test_cyclomatic_complexity(
    code: str, func_name: str, expected: int, description: str
) -> None:
    """Test cyclomatic complexity calculation for various code patterns.

    Given: Code with a function having a known cyclomatic complexity
    When: analyze_branches is called with the function
    Then: The result contains the correct cyclomatic complexity
    """
    result = analyze_branches(code=code, function_name=func_name, timeout_seconds=10)

    assert result["status"] == "complete"
    assert (
        result["cyclomatic_complexity"] == expected
    ), f"{description}. Expected complexity {expected}, got {result['cyclomatic_complexity']}"


def test_if_elif_chain_no_double_counting() -> None:
    """Test if/elif chain specifically to detect double-counting bug.

    This test explicitly validates that elif branches are not double-counted
    by ast.walk() when the code also explicitly counts them.

    Given: Code with if/elif/elif/else structure
    When: analyze_branches is called
    Then: Complexity is 4, not 6 (which would indicate double-counting)
    """
    code = """
def if_elif_chain(x: int) -> int:
    if x > 10:
        return 1
    elif x > 5:
        return 2
    elif x > 0:
        return 3
    else:
        return 0
"""
    result = analyze_branches(
        code=code, function_name="if_elif_chain", timeout_seconds=10
    )

    # Correct complexity: 1 (base) + 3 (if + 2 elifs) = 4
    # Buggy implementation would return 6
    assert result["status"] == "complete"
    assert result["cyclomatic_complexity"] == 4, (
        f"BUG: Expected complexity 4, got {result['cyclomatic_complexity']}. "
        f"This indicates elif branches are being double-counted by ast.walk()"
    )
