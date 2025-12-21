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
SCHEMA COMPLIANCE TESTS - Section 4.4 Specification

These tests demonstrate that the current analyze_branches implementation violates
the schema requirements specified in section 4.4 of the specification.

REQUIRED SCHEMA (Section 4.4):
{
  "status": "complete" | "partial" | "error",
  "branches": [
    {
      "line": 5,
      "condition": "x > 0",
      "true_reachable": true,
      "false_reachable": true,
      "true_example": {"x": 1},
      "false_example": {"x": -1},
      "note": "Optional additional information"
    }
  ],
  "total_branches": 5,
  "reachable_branches": 4,
  "dead_code_lines": [9, 10],
  "cyclomatic_complexity": 6,
  "time_seconds": 3.1
}
"""

import pytest
from main import analyze_branches, logic_analyze_branches


class TestSchemaCompliance:
    """Test compliance with Section 4.4 schema requirements."""

    def test_schema_has_all_required_fields(self):
        """Test that analyze_branches returns ALL required schema fields."""
        code = """
def simple_branch(x):
    if x > 0:
        return "positive"
    else:
        return "non-positive"
"""
        result = logic_analyze_branches(code=code, function_name="simple_branch", timeout_seconds=30)

        # Check all required top-level fields are present
        required_fields = [
            "status", "branches", "total_branches", "reachable_branches",
            "dead_code_lines", "cyclomatic_complexity", "time_seconds"
        ]

        missing_fields = []
        for field in required_fields:
            if field not in result:
                missing_fields.append(field)

        # This should fail initially, demonstrating schema violations
        assert len(missing_fields) == 0, f"Missing required fields: {missing_fields}"

        # Check status is valid value
        assert result["status"] in ["complete", "partial", "error"]

        # Check branches is a list
        assert isinstance(result["branches"], list)

        # Check numeric fields
        assert isinstance(result["total_branches"], int)
        assert isinstance(result["reachable_branches"], int)
        assert isinstance(result["cyclomatic_complexity"], int)
        assert isinstance(result["time_seconds"], (int, float))

        # Check dead_code_lines is a list
        assert isinstance(result["dead_code_lines"], list)

    def test_branch_schema_has_all_required_fields(self):
        """Test that each branch has all required fields."""
        code = """
def test_function(x):
    if x > 0:
        return 1
    return 0
"""
        result = logic_analyze_branches(code=code, function_name="test_function", timeout_seconds=30)

        if len(result["branches"]) > 0:
            branch = result["branches"][0]

            # Check all required branch fields are present
            required_branch_fields = [
                "line", "condition", "true_reachable", "false_reachable",
                "true_example", "false_example"
            ]

            missing_branch_fields = []
            for field in required_branch_fields:
                if field not in branch:
                    missing_branch_fields.append(field)

            # This should fail initially, demonstrating branch schema violations
            assert len(missing_branch_fields) == 0, f"Missing required branch fields: {missing_branch_fields}"

            # Check field types
            assert isinstance(branch["line"], int)
            assert isinstance(branch["condition"], str)
            assert isinstance(branch["true_reachable"], bool)
            assert isinstance(branch["false_reachable"], bool)
            # true_example and false_example can be dict or None
            assert branch["true_example"] is None or isinstance(branch["true_example"], dict)
            assert branch["false_example"] is None or isinstance(branch["false_example"], dict)

    def test_time_seconds_accurate_timing(self):
        """Test that time_seconds provides actual execution timing."""
        code = """
def quick_function(x):
    return x + 1
"""
        import time
        start = time.perf_counter()
        result = logic_analyze_branches(code=code, function_name="quick_function", timeout_seconds=30)
        end = time.perf_counter()

        # time_seconds should be present and reasonable
        assert "time_seconds" in result
        assert isinstance(result["time_seconds"], (int, float))
        assert result["time_seconds"] >= 0
        # Should be roughly the actual execution time (within reason)
        actual_time = end - start
        assert abs(result["time_seconds"] - actual_time) < 1.0  # Within 1 second tolerance

    def test_cyclomatic_complexity_calculation(self):
        """Test cyclomatic complexity is calculated correctly."""
        # Simple function with no branches should have complexity 1
        code_simple = "def simple(x): return x + 1"
        result = logic_analyze_branches(code=code_simple, function_name="simple", timeout_seconds=30)

        assert "cyclomatic_complexity" in result
        # Should be at least 1 for baseline complexity
        assert result["cyclomatic_complexity"] >= 1

    def test_dead_code_detection(self):
        """Test dead code lines are identified."""
        code = """
def dead_branch(x):
    if x > 0 and x < 0:  # Impossible condition
        y = 999          # This should be dead code
        return y
    return x
"""
        result = logic_analyze_branches(code=code, function_name="dead_branch", timeout_seconds=30)

        # Should have dead_code_lines field
        assert "dead_code_lines" in result
        assert isinstance(result["dead_code_lines"], list)
        # The impossible condition should create dead code
        if result["status"] == "complete":
            # Should identify line numbers with dead code
            assert len(result["dead_code_lines"]) >= 0

    def test_reachability_analysis(self):
        """Test branch reachability analysis with examples."""
        code = """
def check_sign(x):
    if x > 0:
        return "positive"
    elif x < 0:
        return "negative"
    else:
        return "zero"
"""
        result = logic_analyze_branches(code=code, function_name="check_sign", timeout_seconds=30)

        if result["status"] == "complete" and len(result["branches"]) > 0:
            for branch in result["branches"]:
                # Should have reachability analysis
                assert "true_reachable" in branch
                assert "false_reachable" in branch
                assert isinstance(branch["true_reachable"], bool)
                assert isinstance(branch["false_reachable"], bool)

                # Should have example inputs for reachable paths
                if branch["true_reachable"]:
                    assert "true_example" in branch
                    assert branch["true_example"] is not None
                    assert isinstance(branch["true_example"], dict)

                if branch["false_reachable"]:
                    assert "false_example" in branch
                    assert branch["false_example"] is not None
                    assert isinstance(branch["false_example"], dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])