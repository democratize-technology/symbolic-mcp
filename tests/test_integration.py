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

import pytest
from main import (
    logic_symbolic_check,
    logic_find_path_to_exception,
    logic_compare_functions,
    logic_analyze_branches
)

# Test 1: Basic Counterexample Finding
def test_finds_needle_in_haystack():
    code = """
def tricky(x: int, y: int) -> int:
    if x == 7 and y == 25:
        raise ValueError("Found the needle")
    return x + y
    """
    # Calling the LOGIC function, not the TOOL object
    result = logic_symbolic_check(code=code, function_name="tricky", timeout_seconds=10)

    assert result["status"] == "counterexample"
    ce = result["counterexamples"][0]
    assert ce["args"]["x"] == 7
    assert ce["args"]["y"] == 25

# Test 2: Exception Hunting
def test_find_path_to_exception():
    code = """
def unsafe(x: int):
    if x == 123:
        raise IndexError("Boom")
    """
    result = logic_find_path_to_exception(code=code, function_name="unsafe", exception_type="IndexError", timeout_seconds=10)

    assert result["status"] == "found"
    assert result["triggering_inputs"][0]["args"]["x"] == 123

# Test 3: Unreachable Exception
def test_unreachable_exception():
    code = """
def safe(x: int):
    if x > 0 and x < 0:
        raise IndexError("Impossible")
    """
    result = logic_find_path_to_exception(code=code, function_name="safe", exception_type="IndexError", timeout_seconds=10)

    assert result["status"] == "unreachable"

# Test 4: Equivalence Checking
def test_equivalence_check_bug():
    code = """
def impl_a(x: int) -> int:
    return x * 2

def impl_b(x: int) -> int:
    return x + x if x != 0 else 1  # Bug at 0
    """
    result = logic_compare_functions(code=code, function_a="impl_a", function_b="impl_b", timeout_seconds=10)

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
    result = logic_analyze_branches(code=code, function_name="branches", timeout_seconds=10)

    assert result["status"] == "partial"
    assert result["total_branches"] == 1
    assert "x > 0" in result["branches"][0]["condition"]
