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
Test the core SymbolicAnalyzer class directly without MCP decorators
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import SymbolicAnalyzer
from crosshair.core_and_libs import AnalysisOptions, AnalysisKind

def test_fixed_analyzer():
    """Test SymbolicAnalyzer with fixed AnalysisOptions"""
    print("=== Testing Fixed SymbolicAnalyzer ===")

    code = '''
def simple_add(x: int, y: int) -> int:
    """Simple addition function that should be correct"""
    return x + y
'''

    analyzer = SymbolicAnalyzer(timeout_seconds=5)

    # Test if we can call the internal analyze method directly
    try:
        result = analyzer.analyze(code, "simple_add")
        print(f"Analyzer result: {result}")
    except Exception as e:
        print(f"Analyzer failed: {e}")
        import traceback
        traceback.print_exc()

def test_crosshair_direct():
    """Test CrossHair directly to see if it actually works"""
    print("\n=== Testing CrossHair Directly ===")

    try:
        from crosshair.core_and_libs import analyze_function
        from icontract import require

        @require(lambda x: x != 0)
        def safe_divide(x: int) -> int:
            return 100 // x

        options = AnalysisOptions(
            analysis_kind=[AnalysisKind.icontract],
            enabled=True,
            specs_complete=True,
            per_condition_timeout=5.0,
            max_iterations=1000,
            report_all=False,
            report_verbose=False,
            unblock=[],
            timeout=10.0,
            per_path_timeout=1.0,
            max_uninteresting_iterations=1000
        )

        print("Running CrossHair analysis...")
        messages = list(analyze_function(safe_divide, options))
        print(f"CrossHair messages: {messages}")

    except Exception as e:
        print(f"CrossHair direct test failed: {e}")
        import traceback
        traceback.print_exc()

def test_buggy_function_direct():
    """Test CrossHair with a function that should fail"""
    print("\n=== Testing CrossHair with Buggy Function ===")

    try:
        from crosshair.core_and_libs import analyze_function
        from icontract import require

        @require(lambda x: x > 0)  # Contract says x > 0
        def buggy_divide(x: int) -> int:
            return 100 // x  # But function fails when x <= 0

        options = AnalysisOptions(
            analysis_kind=[AnalysisKind.icontract],
            enabled=True,
            specs_complete=True,
            per_condition_timeout=5.0,
            max_iterations=1000,
            report_all=False,
            report_verbose=False,
            unblock=[],
            timeout=10.0,
            per_path_timeout=1.0,
            max_uninteresting_iterations=1000
        )

        print("Running CrossHair analysis on buggy function...")
        messages = list(analyze_function(buggy_divide, options))
        print(f"CrossHair messages: {messages}")

        # Check for counterexamples
        for msg in messages:
            if hasattr(msg, 'state'):
                print(f"Message state: {msg.state}")
            if hasattr(msg, 'args'):
                print(f"Counterexample args: {msg.args}")
            if hasattr(msg, 'message'):
                print(f"Message: {msg.message}")

    except Exception as e:
        print(f"Buggy function test failed: {e}")
        import traceback
        traceback.print_exc()

def test_analyze_branches_manual():
    """Test analyze_branches function manually"""
    print("\n=== Testing analyze_branches Manually ===")

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

    try:
        # Import the function directly from main module
        import main
        analyzer = SymbolicAnalyzer(timeout_seconds=5)

        # Test the analyze method directly
        result = analyzer.analyze(code, "complex_branching")
        print(f"Direct analyze result: {result}")

    except Exception as e:
        print(f"Manual analyze_branches test failed: {e}")
        import traceback
        traceback.print_exc()

def test_memory_limit():
    """Test if memory limit actually works"""
    print("\n=== Testing Memory Limit ===")

    try:
        import resource
        print(f"Current memory limit: {resource.getrlimit(resource.RLIMIT_AS)}")

        # Try to set memory limit
        limit_mb = 100
        try:
            limit_bytes = limit_mb * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, limit_bytes))
            print(f"Set memory limit to {limit_mb}MB")
            new_limit = resource.getrlimit(resource.RLIMIT_AS)
            print(f"New memory limit: {new_limit}")
        except ValueError as e:
            print(f"Failed to set memory limit: {e}")

    except Exception as e:
        print(f"Memory limit test failed: {e}")

if __name__ == "__main__":
    print("🔧 Testing Core Symbolic Analyzer Functionality")
    print("=" * 60)

    test_fixed_analyzer()
    test_crosshair_direct()
    test_buggy_function_direct()
    test_analyze_branches_manual()
    test_memory_limit()

    print("\n🎯 Core testing completed!")