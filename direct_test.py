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

#!/usr/bin/env python3.11
"""
Direct testing of symbolic analyzer functionality to understand actual behavior
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import SymbolicAnalyzer, analyze_branches, symbolic_check, find_path_to_exception, compare_functions

def test_symbolic_analyzer_simple():
    """Test SymbolicAnalyzer with a simple correct function"""
    print("=== Testing SymbolicAnalyzer with Simple Function ===")

    code = '''
def simple_add(x: int, y: int) -> int:
    """Simple addition function that should be correct"""
    return x + y
'''

    analyzer = SymbolicAnalyzer(timeout_seconds=5)
    result = analyzer.analyze(code, "simple_add")

    print(f"Result: {result}")
    print(f"Status: {result.get('status')}")
    print(f"Paths explored: {result.get('paths_explored')}")
    print(f"Paths verified: {result.get('paths_verified')}")
    print(f"Time: {result.get('time_seconds')}s")
    print()

def test_symbolic_analyzer_with_bug():
    """Test SymbolicAnalyzer with a function that has a bug"""
    print("=== Testing SymbolicAnalyzer with Buggy Function ===")

    code = '''
def divide_by_zero_if_negative(x: int) -> float:
    """Function with a clear bug"""
    if x < 0:
        return 1 / 0  # Division by zero!
    return 1.0 / (x + 1)
'''

    analyzer = SymbolicAnalyzer(timeout_seconds=5)
    result = analyzer.analyze(code, "divide_by_zero_if_negative")

    print(f"Result: {result}")
    print(f"Status: {result.get('status')}")
    print(f"Counterexamples: {result.get('counterexamples')}")
    print(f"Paths explored: {result.get('paths_explored')}")
    print(f"Time: {result.get('time_seconds')}s")
    print()

def test_symbolic_check_tool():
    """Test the symbolic_check MCP tool function directly"""
    print("=== Testing symbolic_check Tool Function ===")

    code = '''
def buggy_function(n: int) -> int:
    """Function with assertion that should fail"""
    assert n != 0, "n cannot be zero"
    return 100 // n
'''

    result = symbolic_check(code, "buggy_function", timeout_seconds=5)

    print(f"Result: {result}")
    print(f"Status: {result.get('status')}")
    print(f"Counterexamples: {result.get('counterexamples')}")
    print()

def test_analyze_branches_real():
    """Test analyze_branches function with actual code"""
    print("=== Testing analyze_branches Function ===")

    code = '''
def complex_branching(x: int, y: int) -> str:
    """Function with multiple branches"""
    if x > 0:
        if y > 0:
            return "both positive"
        else:
            return "x positive, y non-positive"
    elif x == 0:
        return "x is zero"
    else:
        return "x negative"
'''

    result = analyze_branches(code, "complex_branching", timeout_seconds=10)

    print(f"Result: {result}")
    print(f"Status: {result.get('status')}")
    print(f"Total branches: {result.get('total_branches')}")
    print(f"Branches: {result.get('branches')}")
    print(f"Note: {result.get('note')}")
    print()

def test_find_path_to_exception():
    """Test find_path_to_exception function"""
    print("=== Testing find_path_to_exception Function ===")

    code = '''
def risky_operation(value: int) -> int:
    """Function that can raise ValueError"""
    if value < 0:
        raise ValueError("Negative value not allowed")
    return value * 2
'''

    result = find_path_to_exception(code, "risky_operation", "ValueError", timeout_seconds=5)

    print(f"Result: {result}")
    print(f"Status: {result.get('status')}")
    print(f"Triggering inputs: {result.get('triggering_inputs')}")
    print()

def test_compare_functions():
    """Test compare_functions function"""
    print("=== Testing compare_functions Function ===")

    code = '''
def add1(a: int, b: int) -> int:
    return a + b

def add2(a: int, b: int) -> int:
    return b + a

def subtract(a: int, b: int) -> int:
    return a - b
'''

    # Test equivalent functions
    result1 = compare_functions(code, "add1", "add2", timeout_seconds=5)
    print("Comparing add1 and add2 (should be equivalent):")
    print(f"Status: {result1.get('status')}")
    print(f"Confidence: {result1.get('confidence')}")

    # Test different functions
    result2 = compare_functions(code, "add1", "subtract", timeout_seconds=5)
    print("\nComparing add1 and subtract (should be different):")
    print(f"Status: {result2.get('status')}")
    print(f"Distinguishing input: {result2.get('distinguishing_input')}")
    print()

def test_restricted_importer():
    """Test if the RestrictedImporter actually blocks modules"""
    print("=== Testing RestrictedImporter ===")

    code_with_bad_imports = '''
import os
import subprocess

def malicious_function():
    os.system("echo 'pwned'")
    subprocess.run(["echo", "should be blocked"], shell=True)
    return 42
'''

    analyzer = SymbolicAnalyzer(timeout_seconds=5)
    result = analyzer.analyze(code_with_bad_imports, "malicious_function")

    print(f"Result with blocked imports: {result}")
    print(f"Status: {result.get('status')}")
    print(f"Error type: {result.get('error_type')}")
    print()

if __name__ == "__main__":
    print("🔍 Testing Symbolic Execution MCP Server - Real Behavior Analysis")
    print("=" * 70)

    try:
        test_symbolic_analyzer_simple()
        test_symbolic_analyzer_with_bug()
        test_symbolic_check_tool()
        test_analyze_branches_real()
        test_find_path_to_exception()
        test_compare_functions()
        test_restricted_importer()

        print("🎯 All tests completed!")

    except Exception as e:
        print(f"💥 Error during testing: {e}")
        import traceback
        traceback.print_exc()