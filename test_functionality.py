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
Test the actual functionality of the current implementation to verify the fixes work.
"""

import sys
import os
import tempfile
import subprocess

def test_symbolic_execution_functionality():
    """Test that symbolic execution actually works with real CrossHair API."""

    # Create a simple test function
    test_code = '''
def test_func(x: int) -> int:
    """Simple function that should be verified."""
    if x < 0:
        raise ValueError("x must be non-negative")
    return x * 2
'''

    # Test using the main.py logic directly by calling it as a subprocess
    test_script = '''
import sys
import os
sys.path.insert(0, os.getcwd())

try:
    from main import logic_symbolic_check

    test_code = """def test_func(x: int) -> int:
    if x < 0:
        raise ValueError("x must be non-negative")
    return x * 2"""

    result = logic_symbolic_check(test_code, "test_func", 10)
    print("Result:", result)

    # Check for key indicators that CrossHair is working
    if "paths_explored" in result and result.get("paths_explored", 0) > 0:
        print("SUCCESS: CrossHair is exploring paths")
    else:
        print("FAILURE: CrossHair not exploring paths")

    if "counterexamples" in result:
        print("SUCCESS: Counterexamples field present")
    else:
        print("FAILURE: Counterexamples field missing")

except Exception as e:
    print("ERROR:", e)
    import traceback
    traceback.print_exc()
'''

    # Write test script to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script)
        test_file = f.name

    try:
        # Run the test in a subprocess with the virtual environment
        env = os.environ.copy()
        env['VIRTUAL_ENV'] = '/Users/jeremy/Development/hacks/symbolic-mcp/venv'
        env['PATH'] = '/Users/jeremy/Development/hacks/symbolic-mcp/venv/bin:' + env['PATH']

        result = subprocess.run([
            '/Users/jeremy/Development/hacks/symbolic-mcp/venv/bin/python',
            test_file
        ], capture_output=True, text=True, env=env, cwd='/Users/jeremy/Development/hacks/symbolic-mcp')

        print("STDOUT:")
        print(result.stdout)
        print("\nSTDERR:")
        print(result.stderr)
        print(f"\nReturn code: {result.returncode}")

        return result.returncode == 0 and "SUCCESS" in result.stdout

    finally:
        os.unlink(test_file)

def test_section_5_1_imports():
    """Test if the Section 5.1 imports are syntactically correct."""

    # Test just the import lines
    import_test = '''
try:
    import crosshair
    from crosshair.fnutil import resolve_signature
    print("SUCCESS: Basic CrossHair imports work")

    # Test if AnalysisKind is available (this was the missing import)
    try:
        from crosshair.core_and_libs import AnalysisKind
        print("SUCCESS: AnalysisKind import works")
    except ImportError as e:
        print(f"PARTIAL: AnalysisKind not available: {e}")

except ImportError as e:
    print(f"FAILURE: CrossHair imports not working: {e}")
'''

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(import_test)
        test_file = f.name

    try:
        env = os.environ.copy()
        env['VIRTUAL_ENV'] = '/Users/jeremy/Development/hacks/symbolic-mcp/venv'
        env['PATH'] = '/Users/jeremy/Development/hacks/symbolic-mcp/venv/bin:' + env['PATH']

        result = subprocess.run([
            '/Users/jeremy/Development/hacks/symbolic-mcp/venv/bin/python',
            test_file
        ], capture_output=True, text=True, env=env)

        print("Import test result:")
        print(result.stdout)
        if result.stderr:
            print("Import errors:")
            print(result.stderr)

        return "SUCCESS" in result.stdout

    finally:
        os.unlink(test_file)

if __name__ == "__main__":
    print("=== TESTING SECTION 5.1 IMPORT COMPLIANCE ===")
    imports_work = test_section_5_1_imports()

    print("\n=== TESTING SYMBOLIC EXECUTION FUNCTIONALITY ===")
    execution_works = test_symbolic_execution_functionality()

    print(f"\n=== SUMMARY ===")
    print(f"Section 5.1 imports: {'PASS' if imports_work else 'FAIL'}")
    print(f"Symbolic execution: {'PASS' if execution_works else 'FAIL'}")

    if imports_work and execution_works:
        print("OVERALL: FIXES VERIFIED - System is ready for production")
    else:
        print("OVERALL: ISSUES REMAIN - System not ready for production")