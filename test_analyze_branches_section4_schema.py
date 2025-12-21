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

#!/usr/bin/env python3
"""
TEST-DRIVEN DEVELOPMENT: analyze_branches Section 4 Schema Compliance

This file contains FAILING tests that verify EXACT Section 4 schema compliance.
All tests MUST FAIL initially, then pass after proper implementation.

Section 4 Schema Specification:
{
  "status": "complete" | "partial" | "error",
  "branches": [
    {
      "line": int,
      "condition": str,
      "true_reachable": bool,
      "false_reachable": bool,
      "true_example": dict|null,
      "false_example": dict|null,
      "note": str (optional)
    }
  ],
  "total_branches": int,
  "reachable_branches": int,
  "dead_code_lines": list[int],
  "cyclomatic_complexity": int,
  "time_seconds": float
}

CRITICAL REQUIREMENTS:
- EXACT schema compliance - no extra fields
- Concrete input examples for branches
- Real dead code detection
- Actual cyclomatic complexity calculation
- Proper field types (string, int, float, array, boolean, object)
"""

import pytest
import json
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import logic_analyze_branches


class TestAnalyzeBranchesSchemaCompliance:
    """Test EXACT Section 4 schema compliance."""

    def test_exact_schema_structure_complete_status(self):
        """Test that output matches EXACT schema when status is 'complete'."""
        code = '''
def simple_branch(x):
    if x > 0:
        return 1
    return 0
'''
        result = logic_analyze_branches(code=code, function_name="simple_branch", timeout_seconds=30)

        # Test exact top-level schema
        assert isinstance(result, dict)

        # Required top-level fields
        required_fields = {
            "status", "branches", "total_branches", "reachable_branches",
            "dead_code_lines", "cyclomatic_complexity", "time_seconds"
        }
        assert set(result.keys()) == required_fields, f"Extra fields: {set(result.keys()) - required_fields}"

        # Field types
        assert isinstance(result["status"], str)
        assert result["status"] in {"complete", "partial", "error"}
        assert isinstance(result["branches"], list)
        assert isinstance(result["total_branches"], int)
        assert isinstance(result["reachable_branches"], int)
        assert isinstance(result["dead_code_lines"], list)
        assert isinstance(result["cyclomatic_complexity"], int)
        assert isinstance(result["time_seconds"], float)

        # Dead code lines must be list of ints
        assert all(isinstance(line, int) for line in result["dead_code_lines"])

    def test_branch_structure_exact_schema(self):
        """Test that each branch has EXACT schema structure."""
        code = '''
def test_function(x):
    if x > 0:
        return "positive"
    elif x < 0:
        return "negative"
    else:
        return "zero"
'''
        result = logic_analyze_branches(code=code, function_name="test_function", timeout_seconds=30)

        assert len(result["branches"]) >= 2, "Should find at least 2 branches"

        for branch in result["branches"]:
            # Test exact branch schema
            required_branch_fields = {
                "line", "condition", "true_reachable", "false_reachable",
                "true_example", "false_example"
            }
            # Optional 'note' field may be present
            actual_fields = set(branch.keys())
            assert actual_fields.issuperset(required_branch_fields), f"Missing required fields: {required_branch_fields - actual_fields}"
            # Only 'note' is allowed as extra field
            extra_fields = actual_fields - required_branch_fields
            assert extra_fields.issubset({"note"}), f"Unexpected extra fields: {extra_fields}"

            # Field types
            assert isinstance(branch["line"], int)
            assert isinstance(branch["condition"], str)
            assert isinstance(branch["true_reachable"], bool)
            assert isinstance(branch["false_reachable"], bool)
            # Examples must be dict or null
            assert branch["true_example"] is None or isinstance(branch["true_example"], dict)
            assert branch["false_example"] is None or isinstance(branch["false_example"], dict)
            # Note must be string if present
            if "note" in branch:
                assert isinstance(branch["note"], str)

    def test_concrete_examples_for_branches(self):
        """Test that branches have concrete input examples, not None."""
        code = '''
def check_value(x):
    if x > 5:
        return "big"
    else:
        return "small"
'''
        result = logic_analyze_branches(code=code, function_name="check_value", timeout_seconds=30)

        assert len(result["branches"]) >= 1, "Should find at least 1 branch"
        branch = result["branches"][0]

        # Should provide concrete examples for reachable branches
        if branch["true_reachable"]:
            assert branch["true_example"] is not None, "True branch should have concrete example"
            assert isinstance(branch["true_example"], dict), "Example should be dict"
            # Example should actually satisfy the condition
            example = branch["true_example"]
            assert "x" in example, "Example should contain variable"
            assert example["x"] > 5, "Example should satisfy condition x > 5"

        if branch["false_reachable"]:
            assert branch["false_example"] is not None, "False branch should have concrete example"
            assert isinstance(branch["false_example"], dict), "Example should be dict"
            # Example should actually NOT satisfy the condition
            example = branch["false_example"]
            assert "x" in example, "Example should contain variable"
            assert example["x"] <= 5, "Example should not satisfy condition x > 5"

    def test_dead_code_detection(self):
        """Test detection of unreachable branches (dead code)."""
        code = '''
def impossible_condition(x):
    if x > 0 and x < 0:  # Impossible - x cannot be both > 0 and < 0
        return 999  # Dead code
    return 0
'''
        result = logic_analyze_branches(code=code, function_name="impossible_condition", timeout_seconds=30)

        assert len(result["branches"]) >= 1, "Should find the impossible branch"
        branch = result["branches"][0]

        # Should detect that condition is unsatisfiable
        assert not branch["true_reachable"], "True branch should be unreachable"
        assert branch["false_reachable"], "False branch should be reachable"
        assert branch["true_example"] is None, "Unreachable branch should have no example"
        assert branch["false_example"] is not None, "Reachable branch should have example"

        # Should detect dead code lines
        assert len(result["dead_code_lines"]) > 0, "Should identify dead code lines"
        # Line containing return 999 should be marked as dead
        assert any(line >= 4 for line in result["dead_code_lines"]), "Should include dead return statement"

    def test_cyclomatic_complexity_calculation(self):
        """Test proper cyclomatic complexity calculation."""
        # Simple case: complexity = 1 (no decisions)
        code_simple = '''
def no_decisions(x):
    return x + 1
'''
        result_simple = logic_analyze_branches(code=code_simple, function_name="no_decisions", timeout_seconds=30)
        assert result_simple["cyclomatic_complexity"] == 1, "Simple function should have complexity 1"

        # Complex case: multiple decisions
        code_complex = '''
def complex_flow(a, b, c):
    if a and b:  # +2 complexity (and counts as 2 decisions)
        return 1
    if c:        # +1 complexity
        return 2
    for i in range(a):  # +1 complexity
        if i > 5:       # +1 complexity
            return 3
    return 0
'''
        result_complex = logic_analyze_branches(code=code_complex, function_name="complex_flow", timeout_seconds=30)
        # Expected: 1 (base) + 2 (a and b) + 1 (c) + 1 (for) + 1 (i > 5) = 6
        assert result_complex["cyclomatic_complexity"] >= 5, "Complex function should have higher complexity"

    def test_status_values(self):
        """Test that status field has correct values."""
        code = '''
def test_func(x):
    return x
'''
        result = logic_analyze_branches(code=code, function_name="test_func", timeout_seconds=30)
        assert result["status"] in {"complete", "partial", "error"}, f"Invalid status: {result['status']}"

    def test_reachable_branches_count(self):
        """Test that reachable_branches count matches actual reachable branches."""
        code = '''
def multiple_branches(x):
    if x > 10:
        return "big"
    elif x > 5:
        return "medium"
    elif x > 0:
        return "small"
    else:
        return "zero"
'''
        result = logic_analyze_branches(code=code, function_name="multiple_branches", timeout_seconds=30)

        # Count actual reachable branches
        reachable_count = sum(
            1 for branch in result["branches"]
            if branch["true_reachable"] or branch["false_reachable"]
        )

        assert result["reachable_branches"] == reachable_count, \
            f"reachable_branches count {result['reachable_branches']} doesn't match actual {reachable_count}"

    def test_timing_field(self):
        """Test that time_seconds is a positive float."""
        code = '''
def timing_test(x):
    if x:
        return 1
    return 0
'''
        result = logic_analyze_branches(code=code, function_name="timing_test", timeout_seconds=30)

        assert isinstance(result["time_seconds"], float), "time_seconds should be float"
        assert result["time_seconds"] >= 0, "time_seconds should be non-negative"
        assert result["time_seconds"] > 0, "time_seconds should be positive for real execution"

    def test_error_status_schema(self):
        """Test schema when status is 'error'."""
        code = '''
def syntax_error():
    if x = 1:  # Syntax error
        return 1
'''
        result = logic_analyze_branches(code=code, function_name="syntax_error", timeout_seconds=30)

        # Should still have basic schema structure
        assert isinstance(result, dict)
        assert result["status"] == "error"
        # Should still have timing info
        assert "time_seconds" in result
        assert isinstance(result["time_seconds"], float)

    def test_no_extra_fields_in_schema(self):
        """Test strict schema compliance - no extra fields allowed."""
        code = '''
def test_func(x):
    return x
'''
        result = logic_analyze_branches(code=code, function_name="test_func", timeout_seconds=30)

        # Convert to JSON and back to detect non-serializable fields
        result_json = json.dumps(result)
        result_from_json = json.loads(result_json)

        # Should be identical (no non-serializable fields)
        assert result == result_from_json, "Result should be JSON-serializable without loss"

        # Check for unexpected top-level fields
        allowed_fields = {
            "status", "branches", "total_branches", "reachable_branches",
            "dead_code_lines", "cyclomatic_complexity", "time_seconds"
        }
        actual_fields = set(result.keys())
        unexpected_fields = actual_fields - allowed_fields
        assert not unexpected_fields, f"Unexpected fields found: {unexpected_fields}"


if __name__ == "__main__":
    print("🧪 RUNNING FAILING TESTS FOR analyze_branches Section 4 SCHEMA")
    print("=" * 70)

    # Run tests with pytest
    exit_code = pytest.main([__file__, "-v", "--tb=short"])

    if exit_code == 0:
        print("\n❌ UNEXPECTED: All tests passed! Implementation may already be correct.")
    else:
        print("\n✅ EXPECTED: Tests failed. Now implement the fix.")

    print(f"\nExit code: {exit_code}")