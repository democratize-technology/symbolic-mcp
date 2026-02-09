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
Tests for find_path_to_exception Section 4 schema compliance.

These tests verify the EXACT JSON schema specification from Section 4:
{
  "status": "found" | "unreachable" | "timeout" | "error",
  "triggering_inputs": [
    {
      "args": {"lst": [], "idx": 0},
      "kwargs": {},
      "path_condition": "len(lst) == 0 and idx >= 0",
      "stack_trace": "IndexError at line 5: list index out of range"
    }
  ],
  "paths_to_exception": 3,
  "total_paths_explored": 156,
  "time_seconds": 1.8
}
"""

import jsonschema
import pytest

from main import logic_find_path_to_exception as find_path_to_exception

# EXACT Section 4 schema
SECTION_4_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["found", "unreachable", "timeout", "error"],
        },
        "triggering_inputs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "args": {"type": "object"},
                    "kwargs": {"type": "object"},
                    "path_condition": {"type": "string"},
                    "stack_trace": {"type": "string"},
                },
                "required": ["args", "kwargs", "path_condition", "stack_trace"],
                "additionalProperties": False,
            },
        },
        "paths_to_exception": {"type": "integer"},
        "total_paths_explored": {"type": "integer"},
        "time_seconds": {"type": "number"},
    },
    "required": [
        "status",
        "triggering_inputs",
        "paths_to_exception",
        "total_paths_explored",
        "time_seconds",
    ],
    "additionalProperties": False,
}


def validate_section_4_schema(result):
    """Validate result against EXACT Section 4 schema."""
    jsonschema.validate(result, SECTION_4_SCHEMA)


def test_exact_schema_fields_found_status():
    """Test exact schema compliance when exception is found."""
    # This test will FAIL with current implementation
    code = """
def risky_access(lst, idx):
    return lst[idx]
"""
    result = find_path_to_exception(
        code=code,
        function_name="risky_access",
        exception_type="IndexError",
        timeout_seconds=10,
    )

    # Should have EXACT fields from Section 4 spec
    validate_section_4_schema(result)

    assert result["status"] in ["found", "unreachable", "timeout", "error"]
    assert isinstance(result["paths_to_exception"], int)
    assert isinstance(result["total_paths_explored"], int)
    assert isinstance(result["time_seconds"], (int, float))
    assert isinstance(result["triggering_inputs"], list)

    # If status is "found", should have triggering_inputs with required sub-fields
    if result["status"] == "found" and result["triggering_inputs"]:
        trigger = result["triggering_inputs"][0]
        assert "args" in trigger
        assert "kwargs" in trigger
        assert "path_condition" in trigger
        assert "stack_trace" in trigger

        # Verify field types
        assert isinstance(trigger["args"], dict)
        assert isinstance(trigger["kwargs"], dict)
        assert isinstance(trigger["path_condition"], str)
        assert isinstance(trigger["stack_trace"], str)


def test_exact_schema_fields_unreachable_status():
    """Test exact schema compliance when exception is unreachable."""
    code = """
def safe_div(a, b):
    if b == 0:
        return 0.0
    return a / b
"""
    result = find_path_to_exception(
        code=code,
        function_name="safe_div",
        exception_type="ZeroDivisionError",
        timeout_seconds=10,
    )

    # Should have EXACT fields from Section 4 spec
    validate_section_4_schema(result)

    assert result["status"] == "unreachable"
    assert result["paths_to_exception"] == 0
    assert isinstance(result["total_paths_explored"], int)
    assert isinstance(result["time_seconds"], (int, float))
    assert result["triggering_inputs"] == []  # Empty for unreachable


def test_no_extra_fields_allowed():
    """Test that NO extra fields are present beyond Section 4 specification."""
    code = """
def f(x):
    return x
"""
    result = find_path_to_exception(
        code=code, function_name="f", exception_type="ValueError", timeout_seconds=10
    )

    # Get exact set of fields from Section 4 spec
    allowed_fields = {
        "status",
        "triggering_inputs",
        "paths_to_exception",
        "total_paths_explored",
        "time_seconds",
    }
    actual_fields = set(result.keys())

    # Should have NO extra fields
    extra_fields = actual_fields - allowed_fields
    assert extra_fields == set(), f"Extra fields found: {extra_fields}"


def test_triggering_inputs_structure_exact():
    """Test exact triggering_inputs structure when exception is found."""
    code = """
def divide_by_zero(x):
    return 10 / x
"""
    result = find_path_to_exception(
        code=code,
        function_name="divide_by_zero",
        exception_type="ZeroDivisionError",
        timeout_seconds=10,
    )

    if result["status"] == "found":
        for trigger in result["triggering_inputs"]:
            # Must have EXACT required fields
            required_fields = {"args", "kwargs", "path_condition", "stack_trace"}
            trigger_fields = set(trigger.keys())

            assert (
                trigger_fields == required_fields
            ), f"Trigger fields mismatch: {trigger_fields} vs {required_fields}"

            # Types must be exact
            assert isinstance(trigger["args"], dict)
            assert isinstance(trigger["kwargs"], dict)
            assert isinstance(trigger["path_condition"], str)
            assert isinstance(trigger["stack_trace"], str)

            # Stack trace should contain line number and exception type
            assert "ZeroDivisionError" in trigger["stack_trace"]
            assert "line" in trigger["stack_trace"].lower()


def test_path_condition_present():
    """Test that path_condition is extracted and present."""
    code = """
def conditional_error(x, y):
    if x > 0:
        return y[10]  # IndexError when x > 0
    else:
        return 0
"""
    result = find_path_to_exception(
        code=code,
        function_name="conditional_error",
        exception_type="IndexError",
        timeout_seconds=10,
    )

    if result["status"] == "found":
        for trigger in result["triggering_inputs"]:
            # Should have path_condition that explains how to reach exception
            path_condition = trigger["path_condition"]
            assert isinstance(path_condition, str)
            assert len(path_condition) > 0

            # Path condition should relate to the triggering inputs
            # For example, if x > 0 leads to IndexError, condition should reflect that
            if "x" in trigger["args"] and trigger["args"].get("x", 0) > 0:
                assert "x" in path_condition or ">" in path_condition


def test_real_exception_analysis_not_assertion_hack():
    """Test that we're doing real exception analysis, not assertion wrapping."""
    # Current implementation uses assertion hack - this should fail
    code = """
def complex_function(lst, idx, flag):
    if flag:
        try:
            return lst[idx]
        except IndexError:
            return None
    else:
        return len(lst)
"""

    result = find_path_to_exception(
        code=code,
        function_name="complex_function",
        exception_type="IndexError",
        timeout_seconds=10,
    )

    # Real analysis should handle try/except blocks correctly
    # If exception is caught and handled, it should not be "found"
    if "try" in code and "except IndexError" in code:
        # If exception is properly caught, status should be "unreachable"
        # This will FAIL with current assertion-based implementation
        assert result["status"] in ["unreachable", "error", "timeout"]


def test_stack_trace_details():
    """Test that stack trace contains meaningful information."""
    code = """
def function_a(x):
    return x[0]  # IndexError here

def function_b():
    return function_a([])
"""

    result = find_path_to_exception(
        code=code,
        function_name="function_b",
        exception_type="IndexError",
        timeout_seconds=10,
    )

    if result["status"] == "found":
        for trigger in result["triggering_inputs"]:
            stack_trace = trigger["stack_trace"]

            # Should contain line number
            assert any(char.isdigit() for char in stack_trace)

            # Should contain exception type
            assert "IndexError" in stack_trace

            # Should contain file information (even if it's <string> for temp file)
            assert "line" in stack_trace.lower()

            # Should contain actual error message
            assert "out of range" in stack_trace.lower()


def test_performance_metrics():
    """Test that performance metrics are realistic."""
    code = """
def simple_function(x):
    if x == 42:
        raise ValueError("Found 42")
    return x
"""

    result = find_path_to_exception(
        code=code,
        function_name="simple_function",
        exception_type="ValueError",
        timeout_seconds=10,
    )

    # Performance metrics should be reasonable
    assert isinstance(result["time_seconds"], (int, float))
    assert result["time_seconds"] >= 0
    assert result["time_seconds"] < 300  # Should not take more than 5 minutes

    # Path counts should be integers
    assert isinstance(result["paths_to_exception"], int)
    assert isinstance(result["total_paths_explored"], int)
    assert result["paths_to_exception"] >= 0
    assert result["total_paths_explored"] >= 0

    # If exception found, paths_to_exception should match triggering_inputs count
    if result["status"] == "found":
        assert result["paths_to_exception"] == len(result["triggering_inputs"])

    # If unreachable, paths_to_exception should be 0
    if result["status"] == "unreachable":
        assert result["paths_to_exception"] == 0


def test_error_status_schema():
    """Test schema compliance for error status."""
    code = "def f(x) pass"  # Syntax error

    result = find_path_to_exception(
        code=code, function_name="f", exception_type="ValueError", timeout_seconds=10
    )

    # Even error status must follow exact schema
    validate_section_4_schema(result)
    assert result["status"] == "error"
    assert result["triggering_inputs"] == []
    assert result["paths_to_exception"] == 0
    assert result["total_paths_explored"] == 0
    assert isinstance(result["time_seconds"], (int, float))


if __name__ == "__main__":
    # Run a quick test to see current failures
    print("🧪 Running schema compliance tests (expected to FAIL)")
    pytest.main([__file__, "-v"])
