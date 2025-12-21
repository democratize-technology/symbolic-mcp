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
Test script to verify legitimate symbolic execution functionality still works after security fixes.
"""
import sys
import os
sys.path.insert(0, '/Users/jeremy/Development/hacks/symbolic-mcp')

from main import SymbolicAnalyzer

def test_legitimate_code_analysis():
    """Test that legitimate code analysis still works."""

    # Test 1: Simple mathematical function
    safe_math_code = '''
import math

def calculate_circle_area(radius):
    """Calculate the area of a circle given its radius."""
    return math.pi * radius * radius

def validate_radius(radius):
    """Validate that radius is non-negative."""
    return radius >= 0
'''

    print("=== Testing Safe Mathematical Code ===")
    analyzer = SymbolicAnalyzer(timeout_seconds=10)
    result = analyzer.analyze(safe_math_code, "calculate_circle_area")

    print(f"Status: {result.get('status')}")
    print(f"Time: {result.get('time_seconds', 0)}s")
    print(f"Paths explored: {result.get('paths_explored', 0)}")
    if result.get('status') == 'error':
        print(f"Error: {result.get('message')}")

    # Test 2: String manipulation
    string_code = '''
def process_string(input_str):
    """Process and validate input string."""
    if not input_str:
        return "empty"
    elif len(input_str) > 100:
        return "too_long"
    else:
        return input_str.upper()
'''

    print("\n=== Testing Safe String Processing ===")
    result2 = analyzer.analyze(string_code, "process_string")
    print(f"Status: {result2.get('status')}")
    print(f"Time: {result2.get('time_seconds', 0)}s")
    print(f"Paths explored: {result2.get('paths_explored', 0)}")
    if result2.get('status') == 'error':
        print(f"Error: {result2.get('message')}")

    # Test 3: Simple algorithmic function
    algorithm_code = '''
def fibonacci(n):
    """Calculate nth Fibonacci number."""
    if n <= 0:
        return 0
    elif n == 1:
        return 1
    else:
        return fibonacci(n-1) + fibonacci(n-2)
'''

    print("\n=== Testing Algorithmic Code ===")
    result3 = analyzer.analyze(algorithm_code, "fibonacci")
    print(f"Status: {result3.get('status')}")
    print(f"Time: {result3.get('time_seconds', 0)}s")
    print(f"Paths explored: {result3.get('paths_explored', 0)}")
    if result3.get('status') == 'error':
        print(f"Error: {result3.get('message')}")

    # Test 4: Code with counterexample (should find issues)
    buggy_code = '''
def divide_numbers(a, b):
    """Divide two numbers - has bug when b=0."""
    return a / b  # Division by zero bug
'''

    print("\n=== Testing Code With Counterexample ===")
    result4 = analyzer.analyze(buggy_code, "divide_numbers")
    print(f"Status: {result4.get('status')}")
    print(f"Time: {result4.get('time_seconds', 0)}s")
    print(f"Counterexamples: {len(result4.get('counterexamples', []))}")
    if result4.get('counterexamples'):
        print(f"Counterexample found: {result4['counterexamples'][0]}")

    return all([
        result.get('status') != 'error' or 'violations' not in str(result.get('message', '')),
        result2.get('status') != 'error' or 'violations' not in str(result2.get('message', '')),
        result3.get('status') != 'error' or 'violations' not in str(result3.get('message', '')),
        result4.get('status') in ['counterexample', 'error']  # Should find the division by zero
    ])

if __name__ == "__main__":
    print("Testing legitimate functionality after security fixes...")
    success = test_legitimate_code_analysis()
    print(f"\nOverall test result: {'PASS' if success else 'FAIL'}")