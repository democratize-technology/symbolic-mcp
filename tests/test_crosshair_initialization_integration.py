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
Integration Test: CrossHair Opcode Patches Initialization

CRITICAL BUG FIX VERIFICATION:
This test verifies that the CrossHair "Opcode patches haven't been loaded yet"
error has been completely fixed.

The issue was that CrossHair's opcode_intercept.make_registrations() function
was not being called to register opcode interceptors before symbolic execution
was attempted.

SOLUTION IMPLEMENTED:
- Added global CrossHair opcode patches initialization at module import time
- CrossHair opcode patches are now loaded when main.py is imported
- This prevents the "Opcode patches haven't been loaded yet" error for all usage
"""

import pytest
import sys
import os

# Add the project root to Python path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))


def test_crosshair_opcode_patches_initialized():
    """
    Test that CrossHair opcode patches are properly initialized.

    This test verifies the CRITICAL FIX for the "Opcode patches haven't been loaded yet" error.
    """
    # Import main module - this should trigger global CrossHair initialization
    import main

    # Verify that CrossHair core has opcode patches loaded
    from crosshair.core import _OPCODE_PATCHES

    # CRITICAL VERIFICATION: Opcode patches must be loaded
    assert len(_OPCODE_PATCHES) > 0, f"Expected opcode patches to be loaded, got {len(_OPCODE_PATCHES)}"

    print(f"✅ CrossHair initialization: {len(_OPCODE_PATCHES)} opcode patches loaded")


def test_crosshair_symbolic_execution_works():
    """
    Test that CrossHair symbolic execution actually works after initialization.

    This verifies that the fix enables real CrossHair functionality, not just
    that the error is suppressed.
    """
    from main import logic_symbolic_check

    # Test a simple function with a clear contract
    code = '''
def simple_abs(x: int) -> int:
    """
    post: __return__ >= 0
    """
    return abs(x)
'''

    result = logic_symbolic_check(code=code, function_name="simple_abs", timeout_seconds=10)

    # The analysis should complete without the "Opcode patches haven't been loaded yet" error
    assert result["status"] != "error", f"Expected analysis to complete, got error: {result.get('message')}"

    # Should return a valid status (verified, counterexample, or timeout)
    assert result["status"] in ["verified", "counterexample", "timeout"], \
        f"Expected valid status, got {result['status']}"

    print(f"✅ CrossHair symbolic execution works: status={result['status']}")


def test_crosshair_can_find_counterexamples():
    """
    Test that CrossHair can actually find counterexamples.

    This verifies that CrossHair is working correctly, not just avoiding the error.
    """
    from main import logic_symbolic_check

    # Test a function with a clear bug that CrossHair should find
    code = '''
def buggy_max(x: int, y: int) -> int:
    """
    post: __return__ >= x and __return__ >= y
    """
    if x > y:
        return x
    else:
        return y  # Bug: should return x when x == y
'''

    result = logic_symbolic_check(code=code, function_name="buggy_max", timeout_seconds=10)

    # CrossHair should find a counterexample for the case x == y
    assert result["status"] == "counterexample", \
        f"Expected counterexample for buggy function, got {result['status']}"

    print(f"✅ CrossHair successfully found counterexample: {result['status']}")


def test_multiple_symbolic_analyzer_instances():
    """
    Test that multiple SymbolicAnalyzer instances work correctly.

    This verifies that the global initialization works for all instances.
    """
    from main import SymbolicAnalyzer

    # Create multiple instances
    analyzer1 = SymbolicAnalyzer(timeout_seconds=5)
    analyzer2 = SymbolicAnalyzer(timeout_seconds=5)

    # Both should work without initialization errors
    code = '''
def identity(x: int) -> int:
    """
    post: __return__ == x
    """
    return x
'''

    result1 = analyzer1.check_function(code, "identity")
    result2 = analyzer2.check_function(code, "identity")

    # Both should complete successfully
    assert result1["status"] != "error", f"Analyzer1 failed: {result1.get('message')}"
    assert result2["status"] != "error", f"Analyzer2 failed: {result2.get('message')}"

    print(f"✅ Multiple SymbolicAnalyzer instances work: {result1['status']}, {result2['status']}")


if __name__ == "__main__":
    print("=== CrossHair Initialization Integration Test ===")

    test_crosshair_opcode_patches_initialized()
    test_crosshair_symbolic_execution_works()
    test_crosshair_can_find_counterexamples()
    test_multiple_symbolic_analyzer_instances()

    print("\n🎉 All CrossHair initialization tests PASSED!")
    print("✅ CRITICAL BUG FIX VERIFIED: 'Opcode patches haven't been loaded yet' error is FIXED")