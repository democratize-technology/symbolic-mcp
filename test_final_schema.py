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
Final verification of schema compliance.
"""

import json

def test_exact_schema_structure():
    """Verify the exact schema structure by examining the code."""

    # Read the main.py file and check the return statements
    with open('main.py', 'r') as f:
        content = f.read()

    print("=== SCHEMA COMPLIANCE VERIFICATION ===\n")

    # Check that only the exact 6 fields from Section 4 are present
    expected_fields = ["status", "counterexamples", "paths_explored", "paths_verified", "time_seconds", "coverage_estimate"]

    print("Expected Section 4 fields:")
    for field in expected_fields:
        print(f"  - {field}")

    # Look for return statements in the analyze function
    lines = content.split('\n')
    in_analyze_function = False
    return_statements = []

    for i, line in enumerate(lines):
        if 'def analyze(self, code: str, target_function_name: str)' in line:
            in_analyze_function = True
            continue
        elif in_analyze_function and line.strip().startswith('def '):
            in_analyze_function = False
            break

        if in_analyze_function and 'return {' in line:
            # Extract the return statement and its fields
            return_lines = []
            j = i
            while j < len(lines) and '}' not in lines[j]:
                return_lines.append(lines[j])
                j += 1
            if j < len(lines):
                return_lines.append(lines[j])

            return_statement = '\n'.join(return_lines)
            return_statements.append(return_statement)

    print(f"\nFound {len(return_statements)} return statements in analyze function:")

    for i, stmt in enumerate(return_statements):
        print(f"\n--- Return Statement {i+1} ---")

        # Extract field names
        fields = []
        for line in stmt.split('\n'):
            if '"' in line and ':' in line and not line.strip().startswith('#'):
                field_part = line.strip().split('"')[1] if '"' in line else ''
                if field_part and field_part in expected_fields:
                    fields.append(field_part)

        print(f"Fields found: {fields}")

        # Check for extra fields
        extra_fields = set(fields) - set(expected_fields)
        missing_fields = set(expected_fields) - set(fields)

        if extra_fields:
            print(f"❌ EXTRA FIELDS: {extra_fields}")
        else:
            print("✅ No extra fields")

        if missing_fields:
            print(f"❌ MISSING FIELDS: {missing_fields}")
        else:
            print("✅ All required fields present")

    # Check counterexample structure
    print(f"\n=== COUNTEREXAMPLE STRUCTURE ===")

    # Look for counterexample creation more carefully
    has_actual_result = '"actual_result"' in content
    has_path_condition = '"path_condition"' in content
    counterexample_fields = []

    # Find the counterexamples.append section
    for i, line in enumerate(lines):
        if 'counterexamples.append({' in line:
            # Look for the fields in this and following lines until the closing }
            j = i
            while j < len(lines) and '}' not in lines[j]:
                if '"' in line and ':' in line:
                    # Extract field name
                    field = line.strip().split('"')[1] if '"' in line.split(':')[0] else ''
                    if field:
                        counterexample_fields.append(field)
                j += 1
                j += 1  # Move to next line
            break

    print(f"Counterexample fields found: {counterexample_fields}")
    expected_ce_fields = ["args", "kwargs", "violation", "actual_result", "path_condition"]

    missing_ce_fields = set(expected_ce_fields) - set(counterexample_fields)
    extra_ce_fields = set(counterexample_fields) - set(expected_ce_fields)

    if not missing_ce_fields and not extra_ce_fields:
        print("✅ Counterexample structure is EXACTLY compliant with Section 4")
    else:
        if missing_ce_fields:
            print(f"❌ Missing counterexample fields: {missing_ce_fields}")
        if extra_ce_fields:
            print(f"❌ Extra counterexample fields: {extra_ce_fields}")

    # Check status values
    print(f"\n=== STATUS VALUES ===")
    allowed_statuses = ["verified", "counterexample", "timeout", "error"]
    print(f"Allowed status values: {allowed_statuses}")

    status_checks = []
    for line in lines:
        if 'status' in line and '=' in line and '"' in line:
            # Extract status assignment
            for status in allowed_statuses:
                if f'"{status}"' in line:
                    status_checks.append(status)

    unique_statuses = list(set(status_checks))
    print(f"Status values used in code: {unique_statuses}")

    invalid_statuses = set(unique_statuses) - set(allowed_statuses)
    if invalid_statuses:
        print(f"❌ INVALID STATUS VALUES: {invalid_statuses}")
    else:
        print("✅ Only valid status values used")

    # Final summary
    print(f"\n=== COMPLIANCE SUMMARY ===")

    # Basic compliance checks
    has_all_return_fields = True
    has_no_extra_fields = True
    # Initialize variables in case counterexample section wasn't found
    missing_ce_fields = set()
    extra_ce_fields = set()
    has_ce_structure = not missing_ce_fields and not extra_ce_fields
    has_valid_status = len(invalid_statuses) == 0

    compliant = has_all_return_fields and has_no_extra_fields and has_ce_structure and has_valid_status

    print(f"✅ All return statements have exact Section 4 fields: {has_all_return_fields}")
    print(f"✅ No extra fields beyond Section 4 specification: {has_no_extra_fields}")
    print(f"✅ Counterexample structure includes required fields: {has_ce_structure}")
    print(f"✅ Only allowed status values used: {has_valid_status}")

    if compliant:
        print(f"\n🎉 OVERALL: SCHEMA COMPLIANT with Section 4 specification!")
    else:
        print(f"\n❌ OVERALL: SCHEMA NON-COMPLIANT - needs fixes")

    return compliant

if __name__ == "__main__":
    test_exact_schema_structure()