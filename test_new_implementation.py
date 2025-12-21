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
"""Test the new find_path_to_exception implementation"""

import sys
import os
sys.path.insert(0, os.getcwd())

try:
    from main import logic_find_path_to_exception as find_path_to_exception
    print("✅ Successfully imported find_path_to_exception")

    # Test 1: IndexError case
    print("\n🧪 Test 1: IndexError")
    code1 = '''
def risky_access(lst, idx):
    return lst[idx]
'''

    result1 = find_path_to_exception(
        code=code1,
        function_name="risky_access",
        exception_type="IndexError",
        timeout_seconds=10
    )

    print(f"Status: {result1['status']}")
    print(f"Schema compliance: {set(result1.keys()) == {'status', 'triggering_inputs', 'paths_to_exception', 'total_paths_explored', 'time_seconds'}}")
    if result1['status'] == 'found' and result1['triggering_inputs']:
        trigger = result1['triggering_inputs'][0]
        print(f"Args: {trigger['args']}")
        print(f"Path condition: {trigger['path_condition']}")
        print(f"Stack trace: {trigger['stack_trace']}")

    # Test 2: Unreachable exception
    print("\n🧪 Test 2: Unreachable ZeroDivisionError")
    code2 = '''
def safe_divide(a, b):
    if b == 0:
        return float('inf')
    return a / b
'''

    result2 = find_path_to_exception(
        code=code2,
        function_name="safe_divide",
        exception_type="ZeroDivisionError",
        timeout_seconds=10
    )

    print(f"Status: {result2['status']}")
    print(f"Schema compliance: {set(result2.keys()) == {'status', 'triggering_inputs', 'paths_to_exception', 'total_paths_explored', 'time_seconds'}}")

    # Test 3: Syntax error
    print("\n🧪 Test 3: Syntax error")
    code3 = "def f(x) pass"

    result3 = find_path_to_exception(
        code=code3,
        function_name="f",
        exception_type="ValueError",
        timeout_seconds=10
    )

    print(f"Status: {result3['status']}")
    print(f"Schema compliance: {set(result3.keys()) == {'status', 'triggering_inputs', 'paths_to_exception', 'total_paths_explored', 'time_seconds'}}")

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()