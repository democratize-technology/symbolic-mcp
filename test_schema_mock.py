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
Test schema compliance using mocks to avoid CrossHair import issues.
"""

import unittest.mock
import sys
import os

def test_schema_compliance_with_mock():
    """Test symbolic_check schema compliance with mocked CrossHair."""

    # Mock CrossHair to avoid import issues
    with unittest.mock.patch.dict('sys.modules', {
        'crosshair': unittest.mock.MagicMock(),
        'crosshair.core_and_libs': unittest.mock.MagicMock(),
        'crosshair.options': unittest.mock.MagicMock()
    }):
        # Mock the analyze_function to return a counterexample
        with unittest.mock.patch('main.analyze_function') as mock_analyze:
            from main import symbolic_check

            # Set up mock to return a counterexample
            mock_message = unittest.mock.MagicMock()
            mock_message.state = "COUNTEREXAMPLE"
            mock_message.args = {"x": -1.0}
            mock_message.kwargs = {}
            mock_message.message = "postcondition: result >= 0"
            mock_message.condition = "x < 0"

            mock_analyze.return_value = [mock_message]

            # Test code with postcondition violation
            code = '''
def sqrt_func(x: float) -> float:
    """
    post: result >= 0
    """
    return x ** 0.5  # Returns complex for negative x
'''

            result = symbolic_check(code=code, function_name="sqrt_func", timeout_seconds=10)

            print("Result with mock counterexample:")
            print(f"Keys: {list(result.keys())}")

            # Check exact schema compliance
            expected_keys = ["status", "counterexamples", "paths_explored", "paths_verified", "time_seconds", "coverage_estimate"]
            actual_keys = list(result.keys())

            print(f"Expected keys: {expected_keys}")
            print(f"Actual keys: {actual_keys}")

            # Check for extra fields (should be none)
            extra_fields = set(actual_keys) - set(expected_keys)
            print(f"Extra fields: {extra_fields}")

            # Check for missing fields (should be none)
            missing_fields = set(expected_keys) - set(actual_keys)
            print(f"Missing fields: {missing_fields}")

            # Check status
            print(f"Status: {result['status']}")

            # Check counterexample structure
            if result.get("counterexamples"):
                ce = result["counterexamples"][0]
                print(f"Counterexample keys: {list(ce.keys())}")
                expected_ce_keys = ["args", "kwargs", "violation", "actual_result", "path_condition"]
                ce_extra = set(ce.keys()) - set(expected_ce_keys)
                ce_missing = set(expected_ce_keys) - set(ce.keys())
                print(f"Counterexample extra fields: {ce_extra}")
                print(f"Counterexample missing fields: {ce_missing}")

                # Check specific fields
                print(f"actual_result field present: {'actual_result' in ce}")
                print(f"path_condition field present: {'path_condition' in ce}")

            # Test success if schema is compliant
            schema_compliant = (
                len(extra_fields) == 0 and
                len(missing_fields) == 0 and
                result["status"] in ["verified", "counterexample", "timeout", "error"]
            )

            if result.get("counterexamples"):
                ce = result["counterexamples"][0]
                ce_compliant = (
                    "actual_result" in ce and
                    "path_condition" in ce and
                    len(set(ce.keys()) - set(expected_ce_keys)) == 0
                )
                schema_compliant = schema_compliant and ce_compliant

            print(f"\nSchema compliant: {schema_compliant}")
            return schema_compliant

if __name__ == "__main__":
    print("Testing symbolic_check schema compliance with mocks...")
    compliant = test_schema_compliance_with_mock()
    if compliant:
        print("✅ SCHEMA COMPLIANT")
    else:
        print("❌ SCHEMA NON-COMPLIANT")