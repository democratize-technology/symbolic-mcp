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
Tests for EXACT symbolic_check schema compliance with Section 4 specification.

These tests MUST FAIL initially to prove the current implementation is non-compliant.
After implementation fixes, these tests MUST PASS to ensure exact specification compliance.
"""

import pytest
from typing import Dict, Any, List
import json
from main import logic_symbolic_check as symbolic_check


def test_exact_schema_compliance_counterexample():
    """
    Test that symbolic_check returns EXACT schema for counterexample status.

    This test must FAIL initially because current implementation is missing required fields.
    After fixes, this test must PASS to prove exact schema compliance.
    """
    # Function that should produce a counterexample (NaN issue)
    code = '''
def abs_value(x: float) -> float:
    """
    post: __return__ >= 0
    """
    return x if x >= 0 else -x
'''

    result = symbolic_check(code=code, function_name="abs_value", timeout_seconds=10)

    # Verify status values are exactly as specified
    assert result["status"] in ["verified", "counterexample", "timeout", "error"], \
        f"Status must be one of the four exact values, got: {result['status']}"

    if result["status"] == "counterexample":
        # Verify counterexamples array has EXACT structure
        assert "counterexamples" in result, "Missing required 'counterexamples' field"
        assert isinstance(result["counterexamples"], list), "counterexamples must be a list"

        if len(result["counterexamples"]) > 0:
            counterexample = result["counterexamples"][0]

            # Verify ALL required fields are present
            required_fields = ["args", "kwargs", "violation", "actual_result", "path_condition"]
            for field in required_fields:
                assert field in counterexample, f"Missing required field '{field}' in counterexample"

            # Verify field types match specification exactly
            assert isinstance(counterexample["args"], dict), "args must be a dict"
            assert isinstance(counterexample["kwargs"], dict), "kwargs must be a dict"
            assert isinstance(counterexample["violation"], str), "violation must be a string"
            assert isinstance(counterexample["actual_result"], str), "actual_result must be a string"
            assert isinstance(counterexample["path_condition"], str), "path_condition must be a string"

            # Verify no extra fields are present (strict schema compliance)
            extra_fields = set(counterexample.keys()) - set(required_fields)
            assert len(extra_fields) == 0, f"Extra fields not allowed in counterexample: {extra_fields}"


def test_exact_schema_compliance_verified():
    """
    Test that symbolic_check returns EXACT schema for verified status.
    """
    code = '''
def simple_add(x: int, y: int) -> int:
    """
    post: result == x + y
    """
    return x + y
'''

    result = symbolic_check(code=code, function_name="simple_add", timeout_seconds=10)

    # Verify ALL required top-level fields are present
    required_fields = ["status", "counterexamples", "paths_explored", "paths_verified", "time_seconds", "coverage_estimate"]
    for field in required_fields:
        assert field in result, f"Missing required field '{field}' in result"

    # Verify field types match specification exactly
    assert isinstance(result["status"], str), "status must be a string"
    assert isinstance(result["counterexamples"], list), "counterexamples must be a list"
    assert isinstance(result["paths_explored"], int), "paths_explored must be an int"
    assert isinstance(result["paths_verified"], int), "paths_verified must be an int"
    assert isinstance(result["time_seconds"], (int, float)), "time_seconds must be numeric"
    assert isinstance(result["coverage_estimate"], float), "coverage_estimate must be a float"

    # Verify no extra fields are present (strict schema compliance)
    allowed_fields = set(required_fields)
    extra_fields = set(result.keys()) - allowed_fields
    assert len(extra_fields) == 0, f"Extra fields not allowed in result: {extra_fields}"


def test_status_values_exact():
    """
    Test that status values are EXACTLY as specified in Section 4.
    """
    code = '''
def test_func(x: int) -> int:
    return x
'''

    result = symbolic_check(code=code, function_name="test_func", timeout_seconds=1)

    # Status must be EXACTLY one of these four values
    allowed_statuses = ["verified", "counterexample", "timeout", "error"]
    assert result["status"] in allowed_statuses, \
        f"Status must be exactly one of {allowed_statuses}, got: {result['status']}"


def test_coverage_estimate_calculation():
    """
    Test that coverage_estimate is calculated as specified.

    From specification: 1.0 = exhaustive, < 1.0 = partial
    Current implementation should cap at 0.99 for paths_explored >= 1000
    """
    code = '''
def simple_func(x: int) -> int:
    return x * 2
'''

    result = symbolic_check(code=code, function_name="simple_func", timeout_seconds=5)

    # Verify coverage_estimate is a float between 0.0 and 1.0
    coverage = result["coverage_estimate"]
    assert isinstance(coverage, float), "coverage_estimate must be a float"
    assert 0.0 <= coverage <= 1.0, f"coverage_estimate must be between 0.0 and 1.0, got: {coverage}"

    # If paths_explored < 1000, coverage should be 1.0 (exhaustive)
    # If paths_explored >= 1000, coverage should be 0.99 (partial but high)
    if result["paths_explored"] < 1000:
        assert coverage == 1.0, f"Exhaustive exploration should have coverage_estimate=1.0, got: {coverage}"
    else:
        assert coverage == 0.99, f"Large exploration should have coverage_estimate=0.99, got: {coverage}"


def test_no_extra_fields_compliance():
    """
    Test that no extra fields are present beyond Section 4 specification.

    This is critical for strict schema compliance.
    """
    code = '''
def func(x: int) -> int:
    return x
'''

    result = symbolic_check(code=code, function_name="func", timeout_seconds=1)

    # EXACT fields from Section 4 specification
    allowed_fields = {
        "status",           # "verified" | "counterexample" | "timeout" | "error"
        "counterexamples",  # array of counterexample objects
        "paths_explored",   # integer
        "paths_verified",   # integer
        "time_seconds",     # float
        "coverage_estimate" # float (1.0 = exhaustive, < 1.0 = partial)
    }

    # CRITICAL: No extra fields allowed for strict compliance
    actual_fields = set(result.keys())
    extra_fields = actual_fields - allowed_fields

    assert len(extra_fields) == 0, \
        f"STRICT SCHEMA VIOLATION: Extra fields found: {extra_fields}. " \
        f"Only allowed fields are: {allowed_fields}"


def test_counterexample_structure_exact():
    """
    Test that counterexample structure matches Section 4 EXACTLY.
    """
    code = '''
def divide(x: float, y: float) -> float:
    """
    pre: y != 0
    post: result == x / y
    """
    return x / y  # Should violate pre: y != 0
'''

    result = symbolic_check(code=code, function_name="divide", timeout_seconds=10)

    if result["status"] == "counterexample" and len(result["counterexamples"]) > 0:
        ce = result["counterexamples"][0]

        # EXACT counterexample structure from Section 4
        required_structure = {
            "args": dict,           # {"x": -1.0}
            "kwargs": dict,         # {}
            "violation": str,       # "postcondition: result >= 0"
            "actual_result": str,   # "complex number (nan)"
            "path_condition": str   # "x < 0"
        }

        # Verify each field has correct type
        for field, expected_type in required_structure.items():
            assert field in ce, f"Missing required field: {field}"
            assert isinstance(ce[field], expected_type), \
                f"Field '{field}' must be {expected_type.__name__}, got {type(ce[field]).__name__}"

        # CRITICAL: No extra fields allowed in counterexample
        allowed_ce_fields = set(required_structure.keys())
        actual_ce_fields = set(ce.keys())
        extra_ce_fields = actual_ce_fields - allowed_ce_fields

        assert len(extra_ce_fields) == 0, \
            f"STRICT SCHEMA VIOLATION: Extra counterexample fields: {extra_ce_fields}. " \
            f"Only allowed fields are: {allowed_ce_fields}"


def test_error_status_compliance():
    """
    Test that error status returns proper schema without extra fields.
    """
    # Code with syntax error to trigger error status
    code = '''
def broken_func(x: int)
    return x + 1  # Missing colon in function definition
'''

    result = symbolic_check(code=code, function_name="broken_func", timeout_seconds=1)

    assert result["status"] == "error", f"Expected error status, got: {result['status']}"

    # Even error responses must have required fields
    required_fields = ["status", "counterexamples", "paths_explored", "paths_verified", "time_seconds", "coverage_estimate"]
    for field in required_fields:
        assert field in result, f"Missing required field '{field}' in error response"

    # Error responses should have empty counterexamples and 0 paths
    assert result["counterexamples"] == [], "Error responses should have empty counterexamples"
    assert result["paths_explored"] == 0, "Error responses should have 0 paths_explored"
    assert result["paths_verified"] == 0, "Error responses should have 0 paths_verified"


def test_json_serializable_exact_schema():
    """
    Test that the result is valid JSON with exact schema.
    """
    code = '''
def test_func(x: int) -> int:
    return x
'''

    result = symbolic_check(code=code, function_name="test_func", timeout_seconds=1)

    # Should be JSON serializable
    json_str = json.dumps(result)
    parsed = json.loads(json_str)

    # Should match original exactly (except for potential float precision)
    assert parsed["status"] == result["status"]
    assert parsed["counterexamples"] == result["counterexamples"]
    assert parsed["paths_explored"] == result["paths_explored"]
    assert parsed["paths_verified"] == result["paths_verified"]
    assert abs(parsed["time_seconds"] - result["time_seconds"]) < 0.0001
    assert abs(parsed["coverage_estimate"] - result["coverage_estimate"]) < 0.0001


def test_actual_result_field_present():
    """
    Test that actual_result field is present in counterexamples.

    This is a critical missing field in current implementation.
    """
    code = '''
def sqrt_func(x: float) -> float:
    """
    post: result >= 0
    """
    return x ** 0.5  # Returns complex for negative x
'''

    result = symbolic_check(code=code, function_name="sqrt_func", timeout_seconds=10)

    if result["status"] == "counterexample" and len(result["counterexamples"]) > 0:
        ce = result["counterexamples"][0]

        # CRITICAL: actual_result field must be present
        assert "actual_result" in ce, "CRITICAL: actual_result field is missing from counterexample"
        assert isinstance(ce["actual_result"], str), "actual_result must be a string"
        assert len(ce["actual_result"]) > 0, "actual_result must not be empty"


def test_path_condition_field_present():
    """
    Test that path_condition field is present in counterexamples.

    This is a critical missing field in current implementation.
    """
    code = '''
def conditional_func(x: int) -> int:
    if x < 0:
        return -1
    return x
'''

    result = symbolic_check(code=code, function_name="conditional_func", timeout_seconds=10)

    if result["status"] == "counterexample" and len(result["counterexamples"]) > 0:
        ce = result["counterexamples"][0]

        # CRITICAL: path_condition field must be present
        assert "path_condition" in ce, "CRITICAL: path_condition field is missing from counterexample"
        assert isinstance(ce["path_condition"], str), "path_condition must be a string"
        # path_condition can be empty if no specific path condition


if __name__ == "__main__":
    # Run these tests to verify current non-compliance
    print("Running schema compliance tests...")
    print("These tests should FAIL initially to prove non-compliance.")

    pytest.main([__file__, "-v"])