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
FAILING TESTS FOR CROSSHAIR API USAGE - Section 5.1 Specification Compliance

These tests verify the EXACT CrossHair API usage patterns from Section 5.1 specification.
They will fail initially because the current implementation doesn't use CrossHair at all.

The purpose is to ensure exact compliance with the specification before implementation.
"""

import pytest
import sys
import os

# Add the project root to the path so we can import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_section_5_1_exact_imports():
    """
    Test that the implementation uses the EXACT import paths from Section 5.1 spec.

    Section 5.1 specification REQUIRES:
    ```python
    import crosshair
    from crosshair.core_and_libs import analyze_function, AnalysisOptions, MessageType
    from crosshair.fnutil import resolve_signature
    ```
    """
    # This test will fail because main.py doesn't have CrossHair imports currently
    import main

    # Check for the EXACT imports required by Section 5.1 specification
    assert hasattr(main, 'crosshair'), "Missing 'import crosshair' from Section 5.1 spec"
    assert hasattr(main, 'analyze_function'), "Missing 'analyze_function' import from Section 5.1 spec"
    assert hasattr(main, 'AnalysisOptions'), "Missing 'AnalysisOptions' import from Section 5.1 spec"
    assert hasattr(main, 'MessageType'), "Missing 'MessageType' import from Section 5.1 spec"
    assert hasattr(main, 'resolve_signature'), "Missing 'resolve_signature' import from Section 5.1 spec"

    # Verify no incorrect imports (from compliance review)
    import importlib
    spec = importlib.util.find_spec("crosshair.options")

    # The current implementation incorrectly imports from crosshair.options
    # This should not be imported according to Section 5.1
    main_module = sys.modules['main']
    main_source = open(main_module.__file__, 'r').read()

    # Section 5.1 compliance: NO import from crosshair.options (both forms)
    assert "from crosshair.options import" not in main_source, "Incorrect import found: crosshair.options not in Section 5.1"
    assert "import crosshair.options" not in main_source, "Incorrect import found: crosshair.options not in Section 5.1"


def test_section_5_1_analysis_options_configuration():
    """
    Test that AnalysisOptions is configured with the EXACT values shown in Section 5.1 example.

    Section 5.1 specification shows:
    ```python
    options = AnalysisOptions(
        max_iterations=1000,
        per_condition_timeout=self.timeout,
        per_path_timeout=self.timeout / 10,
    )
    ```

    Note: Actual CrossHair API requires additional parameters, but the values
    from Section 5.1 must be exactly as specified.
    """
    import main

    # Check if SymbolicAnalyzer exists and has correct configuration
    assert hasattr(main, 'SymbolicAnalyzer'), "SymbolicAnalyzer class not found"

    analyzer = main.SymbolicAnalyzer(timeout_seconds=30)

    # The analyzer should create options with EXACT parameters from Section 5.1
    assert hasattr(analyzer, '_get_analysis_options'), "SymbolicAnalyzer needs _get_analysis_options method for testing"

    options = analyzer._get_analysis_options()

    # EXACT Section 5.1 specification compliance - these must match exactly
    assert options.max_iterations == 1000, "max_iterations must be exactly 1000 per Section 5.1"
    assert options.per_condition_timeout == 30, "per_condition_timeout must equal self.timeout (30)"
    assert options.per_path_timeout == 3.0, "per_path_timeout must equal self.timeout / 10 (30/10 = 3.0)"


def test_section_5_1_message_handling():
    """
    Test that message handling follows the EXACT pattern from Section 5.1.

    Section 5.1 specification shows:
    ```python
    for message in analyze_function(func, options):
        paths_explored += 1
        if message.state == MessageType.CONFIRMED:
            paths_verified += 1
        elif message.state == MessageType.COUNTEREXAMPLE:
            counterexamples.append({
                "args": message.args,
                "kwargs": message.kwargs or {},
                "violation": message.message,
                "path_condition": str(message.condition) if hasattr(message, 'condition') else None
            })
    ```
    """
    import main

    # Create a simple test function
    test_code = '''
def test_func(x: int) -> int:
    """Returns x if x > 0, else raises ValueError."""
    if x <= 0:
        raise ValueError("x must be positive")
    return x
'''

    # This will fail because current implementation doesn't use CrossHair
    # The test should pass with proper CrossHair integration
    result = main.logic_symbolic_check(test_code, "test_func", 10)

    # Verify the result follows Section 5.1 message handling pattern
    assert "status" in result, "Result missing status field"
    assert "counterexamples" in result, "Result missing counterexamples field"
    assert "paths_explored" in result, "Result missing paths_explored field"
    assert "paths_verified" in result, "Result missing paths_verified field"

    # If counterexamples exist, verify they follow Section 5.1 structure
    if result["counterexamples"]:
        for counterexample in result["counterexamples"]:
            assert "args" in counterexample, "Counterexample missing 'args' field (Section 5.1 spec)"
            assert "kwargs" in counterexample, "Counterexample missing 'kwargs' field (Section 5.1 spec)"
            assert "violation" in counterexample, "Counterexample missing 'violation' field (Section 5.1 spec)"
            assert "path_condition" in counterexample, "Counterexample missing 'path_condition' field (Section 5.1 spec)"


def test_section_5_1_no_extra_imports():
    """
    Test that the implementation doesn't import extra modules not mentioned in Section 5.1.

    Section 5.1 only allows these specific CrossHair imports:
    - import crosshair
    - from crosshair.core_and_libs import analyze_function, AnalysisOptions, MessageType
    - from crosshair.fnutil import resolve_signature
    """
    import main

    main_module = sys.modules['main']
    main_source = open(main_module.__file__, 'r').read()

    # These should NOT be imported (from compliance review issues):
    forbidden_imports = [
        "from crosshair.options import",
        "import crosshair.options",
        "from crosshair.statespace import",
        "from crosshair.tracers import",
        "from crosshair.util import"
    ]

    for forbidden in forbidden_imports:
        assert forbidden not in main_source, f"Forbidden import found: {forbidden}. Not in Section 5.1 spec."


def test_section_5_1_resolve_signature_usage():
    """
    Test that resolve_signature is imported and used as intended in Section 5.1.

    Section 5.1 imports resolve_signature but doesn't show its usage in the example.
    It's likely intended for function signature analysis.
    """
    import main

    # Verify resolve_signature is imported
    assert hasattr(main, 'resolve_signature'), "resolve_signature not imported per Section 5.1"

    # Test function signature resolution (intended usage)
    test_code = '''
def test_func(x: int, y: str = "default") -> bool:
    return len(y) > x
'''

    # This would normally require resolve_signature for proper analysis
    # The test will fail until proper CrossHair integration is implemented
    try:
        result = main.logic_symbolic_check(test_code, "test_func", 10)
        # If we get here, verify the function was properly analyzed
        assert result["status"] in ["verified", "counterexample", "timeout", "error"]
    except Exception as e:
        # Expected to fail until proper CrossHair integration
        pytest.fail(f"resolve_signature not properly used for function analysis: {e}")


if __name__ == "__main__":
    # Run these failing tests to demonstrate what needs to be fixed
    pytest.main([__file__, "-v"])