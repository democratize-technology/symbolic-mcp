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


class TestCyclomaticComplexity:
    """Test cyclomatic complexity calculation."""

    def test_simple_function_complexity(self):
        """Function with no decision points should have complexity 1."""
        code = """
def simple_function(x: int) -> int:
    return x + 1
"""
        result = analyze_branches(
            code=code, function_name="simple_function", timeout_seconds=10
        )

        assert result["status"] == "complete"
        assert (
            result["cyclomatic_complexity"] == 1
        ), f"Expected complexity 1, got {result['cyclomatic_complexity']}"

    def test_single_if_complexity(self):
        """Single if statement: complexity = 1 (base) + 1 (if) = 2."""
        code = """
def single_if(x: int) -> int:
    if x > 0:
        return 1
    return 0
"""
        result = analyze_branches(
            code=code, function_name="single_if", timeout_seconds=10
        )

        assert result["status"] == "complete"
        assert (
            result["cyclomatic_complexity"] == 2
        ), f"Expected complexity 2, got {result['cyclomatic_complexity']}"

    def test_if_elif_chain_complexity(self):
        """
        Test if/elif chain - THIS EXPOSES THE BUG.

        Code: if a: elif b: elif c: else:

        AST structure:
        - If node (main if)
          - orelse contains: [If (elif b), If (elif c)]

        Decision points:
        1. if a
        2. elif b (first elif)
        3. elif c (second elif)

        Correct complexity = 1 (base) + 3 (decision points) = 4

        BUGGY behavior:
        - ast.walk() finds main If -> +1 (complexity=2)
        - Explicit elif count -> +2 (complexity=4)
        - ast.walk() also visits elif If nodes -> +2 (complexity=6) <- BUG
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

    def test_nested_if_complexity(self):
        """Nested if statements should count each level."""
        code = """
def nested_if(x: int, y: int) -> int:
    if x > 0:
        if y > 0:
            return 1
        return 2
    return 0
"""
        result = analyze_branches(
            code=code, function_name="nested_if", timeout_seconds=10
        )

        # Complexity = 1 (base) + 2 (two if statements) = 3
        assert result["status"] == "complete"
        assert (
            result["cyclomatic_complexity"] == 3
        ), f"Expected complexity 3, got {result['cyclomatic_complexity']}"

    def test_while_loop_complexity(self):
        """While loop adds one decision point."""
        code = """
def while_loop(n: int) -> int:
    total = 0
    while n > 0:
        total += n
        n -= 1
    return total
"""
        result = analyze_branches(
            code=code, function_name="while_loop", timeout_seconds=10
        )

        # Complexity = 1 (base) + 1 (while) = 2
        assert result["status"] == "complete"
        assert (
            result["cyclomatic_complexity"] == 2
        ), f"Expected complexity 2, got {result['cyclomatic_complexity']}"

    def test_for_loop_complexity(self):
        """For loop adds one decision point."""
        code = """
def for_loop(items: list) -> int:
    total = 0
    for item in items:
        total += item
    return total
"""
        result = analyze_branches(
            code=code, function_name="for_loop", timeout_seconds=10
        )

        # Complexity = 1 (base) + 1 (for) = 2
        assert result["status"] == "complete"
        assert (
            result["cyclomatic_complexity"] == 2
        ), f"Expected complexity 2, got {result['cyclomatic_complexity']}"

    def test_boolop_and_complexity(self):
        """
        BoolOp with 'and' adds complexity for each additional operand.

        For 'a and b and c': 3 values -> +2 complexity
        """
        code = """
def boolop_and(x: int, y: int, z: int) -> bool:
    if x > 0 and y > 0 and z > 0:
        return True
    return False
"""
        result = analyze_branches(
            code=code, function_name="boolop_and", timeout_seconds=10
        )

        # Complexity = 1 (base) + 1 (if) + 2 (BoolOp with 3 values has 2 additional operands) = 4
        assert result["status"] == "complete"
        assert (
            result["cyclomatic_complexity"] == 4
        ), f"Expected complexity 4, got {result['cyclomatic_complexity']}"

    def test_boolop_or_complexity(self):
        """BoolOp with 'or' adds complexity for each additional operand."""
        code = """
def boolop_or(x: int, y: int) -> bool:
    if x < 0 or x > 100:
        return True
    return False
"""
        result = analyze_branches(
            code=code, function_name="boolop_or", timeout_seconds=10
        )

        # Complexity = 1 (base) + 1 (if) + 1 (BoolOp with 2 values has 1 additional operand) = 3
        assert result["status"] == "complete"
        assert (
            result["cyclomatic_complexity"] == 3
        ), f"Expected complexity 3, got {result['cyclomatic_complexity']}"

    def test_complex_function_complexity(self):
        """Complex function with multiple decision point types."""
        code = """
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
"""
        result = analyze_branches(
            code=code, function_name="complex_function", timeout_seconds=10
        )

        # Decision points:
        # - 1 for loop
        # - 1 if (item > 0)
        # - 1 elif (item < 0)
        # - 1 while loop
        # - 1 if (x > 10 or x < -10)
        # - 1 BoolOp (2 values, 1 additional operand)
        # Total: 1 (base) + 6 = 7
        assert result["status"] == "complete"
        assert (
            result["cyclomatic_complexity"] == 7
        ), f"Expected complexity 7, got {result['cyclomatic_complexity']}"

    def test_elif_without_else_complexity(self):
        """if/elif chain without else."""
        code = """
def if_elif_no_else(x: int) -> int:
    if x > 10:
        return 1
    elif x > 5:
        return 2
    return 0
"""
        result = analyze_branches(
            code=code, function_name="if_elif_no_else", timeout_seconds=10
        )

        # Complexity = 1 (base) + 2 (if + 1 elif) = 3
        assert result["status"] == "complete"
        assert (
            result["cyclomatic_complexity"] == 3
        ), f"Expected complexity 3, got {result['cyclomatic_complexity']}"

    def test_multiple_boolops_in_if(self):
        """Multiple BoolOps should each add complexity."""
        code = """
def multiple_boolops(x: int, y: int, z: int) -> bool:
    if x > 0 and y > 0:
        if z < 0 or z > 100:
            return True
    return False
"""
        result = analyze_branches(
            code=code, function_name="multiple_boolops", timeout_seconds=10
        )

        # Decision points:
        # - 2 if statements
        # - 1 BoolOp (x and y) -> 1 additional operand
        # - 1 BoolOp (z or z) -> 1 additional operand
        # Total: 1 (base) + 4 = 5
        assert result["status"] == "complete"
        assert (
            result["cyclomatic_complexity"] == 5
        ), f"Expected complexity 5, got {result['cyclomatic_complexity']}"

    def test_if_with_else_no_elif(self):
        """Simple if/else without elif."""
        code = """
def if_else(x: int) -> int:
    if x > 0:
        return 1
    else:
        return 0
"""
        result = analyze_branches(
            code=code, function_name="if_else", timeout_seconds=10
        )

        # Complexity = 1 (base) + 1 (if) = 2 (else doesn't add complexity)
        assert result["status"] == "complete"
        assert (
            result["cyclomatic_complexity"] == 2
        ), f"Expected complexity 2, got {result['cyclomatic_complexity']}"
