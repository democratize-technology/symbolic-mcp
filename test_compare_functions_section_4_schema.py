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
FAILING TESTS for compare_functions Section 4 Schema Compliance

These tests verify the EXACT schema specification from Section 4.
They are designed to FAIL with the current implementation and PASS
with the corrected implementation.

Section 4 specification:
{
  "status": "equivalent" | "different" | "timeout" | "error",
  "distinguishing_input": {
    "args": {"x": 0},
    "function_a_result": 0,
    "function_b_result": 1,
    "explanation": "Functions differ when x == 0"
  },
  "paths_compared": 234,
  "time_seconds": 15.2,
  "confidence": "proven" | "high" | "partial"
}
"""

import pytest
import json
import sys
import os

# Add project root to path for imports
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

try:
    from main import logic_compare_functions as compare_functions
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Current directory: {os.getcwd()}")
    print(f"Project root: {project_root}")
    print("Make sure you're in the project directory with venv activated")
    raise


def test_section_4_schema_exact_compliance():
    """Test that compare_functions returns EXACT Section 4 schema with no extra fields."""

    # Simple equivalent functions
    code = """
def add_one(x):
    return x + 1

def increment(x):
    return x + 1
"""

    result = compare_functions(code, "add_one", "increment", timeout_seconds=30)

    # Test required top-level fields exist and are correct type
    required_fields = {
        "status": str,
        "distinguishing_input": (dict, type(None)),
        "paths_compared": int,
        "time_seconds": float,
        "confidence": str
    }

    for field, expected_type in required_fields.items():
        assert field in result, f"Missing required field: {field}"
        assert isinstance(result[field], expected_type), f"Field {field} has wrong type: {type(result[field])} != {expected_type}"

    # Test no extra fields (strict schema compliance)
    allowed_fields = set(required_fields.keys())
    actual_fields = set(result.keys())
    extra_fields = actual_fields - allowed_fields
    assert not extra_fields, f"Schema contains extra fields not in Section 4: {extra_fields}"

    # Test status values are exactly as specified
    valid_statuses = {"equivalent", "different", "timeout", "error"}
    assert result["status"] in valid_statuses, f"Invalid status: {result['status']} must be one of {valid_statuses}"

    # Test confidence values are exactly as specified
    valid_confidences = {"proven", "high", "partial"}
    assert result["confidence"] in valid_confidences, f"Invalid confidence: {result['confidence']} must be one of {valid_confidences}"


def test_different_functions_schema():
    """Test schema for different functions with proper distinguishing_input structure."""

    # Functions that differ at x=0
    code = """
def function_a(x):
    if x == 0:
        return 0
    return 1

def function_b(x):
    if x == 0:
        return 1
    return 1
"""

    result = compare_functions(code, "function_a", "function_b", timeout_seconds=30)

    assert result["status"] == "different", f"Expected 'different' status, got: {result['status']}"

    # Test distinguishing_input structure when functions differ
    if result["distinguishing_input"]:
        di = result["distinguishing_input"]

        # Required fields in distinguishing_input
        required_di_fields = {"args", "function_a_result", "function_b_result", "explanation"}
        assert set(di.keys()) == required_di_fields, f"distinguishing_input missing required fields: {di.keys()}"

        # Test field types in distinguishing_input
        assert isinstance(di["args"], dict), f"args must be dict, got: {type(di['args'])}"
        assert isinstance(di["explanation"], str), f"explanation must be string, got: {type(di['explanation'])}"

        # Verify actual results are different
        assert di["function_a_result"] != di["function_b_result"], "Function results should be different in distinguishing_input"

        # Explanation should be meaningful
        assert len(di["explanation"]) > 0, "Explanation should not be empty"


def test_equivalent_functions_schema():
    """Test schema for equivalent functions."""

    # Identical functions
    code = """
def double(x):
    return x * 2

def multiply_by_two(x):
    return x * 2
"""

    result = compare_functions(code, "double", "multiply_by_two", timeout_seconds=30)

    assert result["status"] == "equivalent", f"Expected 'equivalent' status, got: {result['status']}"
    assert result["distinguishing_input"] is None, f"distinguishing_input should be None for equivalent functions, got: {result['distinguishing_input']}"


def test_timeout_handling_schema():
    """Test timeout handling with proper schema."""

    # Complex function that might timeout
    code = """
def complex_a(x):
    # Simulate expensive computation
    result = 0
    for i in range(1000000):
        result += (x * i) % 1000
    return result

def complex_b(x):
    # Similar but different implementation
    result = 0
    for i in range(1000000):
        result += (x * i) % 1000
    return result
"""

    result = compare_functions(code, "complex_a", "complex_b", timeout_seconds=1)

    assert result["status"] in {"timeout", "equivalent", "error"}, f"Expected timeout/equivalent/error status, got: {result['status']}"
    assert isinstance(result["time_seconds"], float), "time_seconds should be float"
    assert result["time_seconds"] >= 0, "time_seconds should be non-negative"


def test_error_handling_schema():
    """Test error handling with proper schema."""

    # Code with syntax error
    code = """
def invalid_func(x):
    # This will cause a syntax error
    return x *  # incomplete expression
"""

    result = compare_functions(code, "invalid_func", "invalid_func", timeout_seconds=30)

    assert result["status"] == "error", f"Expected 'error' status for invalid code, got: {result['status']}"
    assert isinstance(result["time_seconds"], float), "time_seconds should be float even for errors"


def test_paths_compared_field():
    """Test that paths_compared is present and reasonable."""

    code = """
def simple_a(x):
    if x > 0:
        return 1
    elif x < 0:
        return -1
    else:
        return 0

def simple_b(x):
    return 1 if x > 0 else -1 if x < 0 else 0
"""

    result = compare_functions(code, "simple_a", "simple_b", timeout_seconds=30)

    assert isinstance(result["paths_compared"], int), "paths_compared should be int"
    assert result["paths_compared"] >= 0, "paths_compared should be non-negative"
    # For simple functions, should explore some paths
    if result["status"] in {"equivalent", "different"}:
        assert result["paths_compared"] > 0, "Should explore at least some paths for successful analysis"


def test_no_extra_fields_compliance():
    """Strict test that no extra fields are present beyond Section 4 specification."""

    code = """
def func_a(x):
    return x + 1

def func_b(x):
    return x + 1
"""

    result = compare_functions(code, "func_a", "func_b", timeout_seconds=30)

    # Section 4 specifies EXACTLY these fields
    allowed_fields = {"status", "distinguishing_input", "paths_compared", "time_seconds", "confidence"}
    actual_fields = set(result.keys())

    # Remove any fields that shouldn't be there (like "bandit_secured")
    extra_fields = actual_fields - allowed_fields
    assert not extra_fields, f"STRICT SCHEMA VIOLATION: Extra fields found: {extra_fields}. Section 4 allows only: {allowed_fields}"


def test_field_value_formats():
    """Test that field values match Section 4 formats exactly."""

    code = """
def func_a(x):
    return x * 2

def func_b(x):
    return x * 2
"""

    result = compare_functions(code, "func_a", "func_b", timeout_seconds=30)

    # Test time_seconds format (should be float with reasonable precision)
    assert isinstance(result["time_seconds"], float), "time_seconds must be float"
    assert 0 <= result["time_seconds"] <= 1000, "time_seconds should be reasonable"

    # Test paths_compared format
    assert isinstance(result["paths_compared"], int), "paths_compared must be int"
    assert 0 <= result["paths_compared"] <= 1000000, "paths_compared should be reasonable"


def test_distinguishing_input_complete_structure():
    """Test complete structure of distinguishing_input when present."""

    code = """
def returns_zero(x):
    return 0

def returns_one(x):
    return 1
"""

    result = compare_functions(code, "returns_zero", "returns_one", timeout_seconds=30)

    if result["status"] == "different" and result["distinguishing_input"]:
        di = result["distinguishing_input"]

        # Test args structure (should contain actual function arguments)
        assert isinstance(di["args"], dict), "args should be dict"

        # Test function results are actual values from functions
        assert di["function_a_result"] == 0, f"function_a_result should be 0, got: {di['function_a_result']}"
        assert di["function_b_result"] == 1, f"function_b_result should be 1, got: {di['function_b_result']}"

        # Test explanation is descriptive
        explanation = di["explanation"]
        assert isinstance(explanation, str), "explanation should be string"
        assert len(explanation) > 10, "explanation should be descriptive"
        assert "differ" in explanation.lower() or "x ==" in explanation, "explanation should mention the difference"


if __name__ == "__main__":
    print("Running Section 4 Schema Compliance Tests...")
    print("These tests are designed to FAIL with current implementation.")
    print()

    # Run all tests
    import traceback

    test_functions = [
        test_section_4_schema_exact_compliance,
        test_different_functions_schema,
        test_equivalent_functions_schema,
        test_timeout_handling_schema,
        test_error_handling_schema,
        test_paths_compared_field,
        test_no_extra_fields_compliance,
        test_field_value_formats,
        test_distinguishing_input_complete_structure
    ]

    failed_tests = []
    passed_tests = []

    for test_func in test_functions:
        try:
            test_func()
            print(f"✅ {test_func.__name__}: PASSED")
            passed_tests.append(test_func.__name__)
        except Exception as e:
            print(f"❌ {test_func.__name__}: FAILED")
            print(f"   Error: {e}")
            traceback.print_exc()
            failed_tests.append(test_func.__name__)
        print()

    print(f"Test Results: {len(passed_tests)} passed, {len(failed_tests)} failed")
    if failed_tests:
        print(f"Failed tests: {failed_tests}")
        print("\nThese failures are expected with the current implementation.")
        print("The implementation needs to be fixed to match Section 4 schema exactly.")
    else:
        print("All tests passed! Implementation matches Section 4 schema.")