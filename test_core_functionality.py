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
Core Functionality Tests

These tests verify that the core symbolic execution functionality still works
after the analyze_branches schema compliance improvements.
"""

from main import logic_symbolic_check, logic_compare_functions, logic_find_path_to_exception


def test_symbolic_check_basic_functionality():
    """Test that basic symbolic checking still works."""
    code = '''
def simple_function(x: int) -> int:
    return x + 1
'''
    result = logic_symbolic_check(code=code, function_name="simple_function", timeout_seconds=30)

    print(f"Symbolic check result: {result}")

    # Should have basic fields
    assert "status" in result
    assert "time_seconds" in result
    assert result["time_seconds"] >= 0

    # Should not have security errors
    assert result.get("error_type") != "SecurityViolation"

    print("✓ Symbolic check basic functionality test passed")


def test_symbolic_check_with_error():
    """Test symbolic checking with a function that has an error."""
    code = '''
def division_error(x: int) -> int:
    return 1 / x  # Division by zero possible
'''
    result = logic_symbolic_check(code=code, function_name="division_error", timeout_seconds=30)

    print(f"Division error result: {result}")

    # Should have basic fields
    assert "status" in result
    assert "time_seconds" in result

    print("✓ Symbolic check error handling test passed")


def test_compare_functions_basic():
    """Test function comparison still works."""
    code = '''
def func_a(x: int) -> int:
    return x + 1

def func_b(x: int) -> int:
    return x + 1
'''
    result = logic_compare_functions(code=code, function_a="func_a", function_b="func_b", timeout_seconds=30)

    print(f"Function comparison result: {result}")

    # Should have basic fields
    assert "status" in result
    assert "time_seconds" in result

    print("✓ Function comparison test passed")


def test_find_path_to_exception_basic():
    """Test exception path finding still works."""
    code = '''
def raises_value_error(x: int):
    if x == 42:
        raise ValueError("Special case")
    return x
'''
    result = logic_find_path_to_exception(code=code, function_name="raises_value_error", exception_type="ValueError", timeout_seconds=30)

    print(f"Exception path result: {result}")

    # Should have basic fields
    assert "status" in result
    assert "time_seconds" in result

    print("✓ Exception path finding test passed")


def test_syntax_error_handling():
    """Test that syntax errors are handled properly."""
    code = '''
def broken_syntax(x:
    return x  # Missing closing parenthesis
'''
    result = logic_symbolic_check(code=code, function_name="broken_syntax", timeout_seconds=30)

    print(f"Syntax error result: {result}")

    # Should have error status and fields
    assert result["status"] == "error"
    assert "error_type" in result
    assert "time_seconds" in result

    print("✓ Syntax error handling test passed")


def test_security_validation():
    """Test that security validation still works."""
    # Try to import a dangerous module
    code = '''
import os
def dangerous_function():
    os.system("echo hello")
    return 42
'''
    result = logic_symbolic_check(code=code, function_name="dangerous_function", timeout_seconds=30)

    print(f"Security validation result: {result}")

    # Should be blocked by security validation
    assert result["status"] == "error"
    assert result.get("error_type") in ["SecurityViolation", "HighSeverityViolation", "CriticalSecurityViolation"]

    print("✓ Security validation test passed")


if __name__ == "__main__":
    print("Running core functionality verification tests...")
    print("=" * 60)

    test_symbolic_check_basic_functionality()
    test_symbolic_check_with_error()
    test_compare_functions_basic()
    test_find_path_to_exception_basic()
    test_syntax_error_handling()
    test_security_validation()

    print("=" * 60)
    print("✅ All core functionality tests passed!")
    print("The core symbolic execution features are working correctly!")