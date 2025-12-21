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
Realistic test to verify the security fix works in practice.

The challenge is that once modules are imported, they stay in sys.modules.
The key test is whether NEW import attempts of blocked modules are blocked.
"""
import sys
import pytest
import tempfile
import importlib.util
import os
import subprocess

# Import the actual RestrictedImporter from main.py
from main import RestrictedImporter

def test_security_fix_blocks_new_imports():
    """
    Test that the security fix blocks NEW import attempts of blocked modules.

    This tests the realistic scenario where an attacker tries to import
    blocked modules in their code.
    """
    # Install the FIXED RestrictedImporter
    RestrictedImporter.install()
    original_meta_path = sys.meta_path.copy()

    try:
        # Create malicious code that tries to import blocked modules
        malicious_code = """
import sys  # This should be blocked
import os   # This should be blocked
import subprocess  # This should be blocked

def malicious_function():
    # This code should never execute due to import blocks
    return "attacker_success"
"""

        # Try to execute malicious code in a sandbox
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(malicious_code)
            temp_path = f.name

        try:
            # This should fail due to blocked imports
            spec = importlib.util.spec_from_file_location("malicious_code", temp_path)
            module = importlib.util.module_from_spec(spec)

            # This should raise ImportError due to our security fix
            with pytest.raises(ImportError, match="Import of 'sys' is blocked"):
                spec.loader.exec_module(module)

        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    finally:
        # Cleanup: Restore original meta_path
        sys.meta_path = original_meta_path


def test_security_fix_allows_symbolic_execution():
    """
    Test that the fix allows the symbolic analyzer to work properly.
    The SymbolicAnalyzer should be able to analyze code without blocked imports.
    """
    from main import SymbolicAnalyzer

    analyzer = SymbolicAnalyzer(timeout_seconds=5)

    # Test code that doesn't use blocked modules
    safe_code = """
def safe_function(x, y):
    return x + y

def another_function(data):
    return len(data)
"""

    result = analyzer.analyze(safe_code, "safe_function")

    # Should succeed without errors
    assert result["status"] in ["verified", "counterexample", "unknown"]
    assert "error" not in result.get("status", "").lower()


def test_blocked_modules_in_symbolic_context():
    """
    Test that blocked modules are properly blocked in symbolic execution context.
    """
    from main import SymbolicAnalyzer

    analyzer = SymbolicAnalyzer(timeout_seconds=5)

    # Test code that tries to use blocked modules
    blocked_code = """
import os  # This should be blocked

def unsafe_function():
    return os.system("echo 'attacker code'")
"""

    result = analyzer.analyze(blocked_code, "unsafe_function")

    # Should result in a SandboxViolation error
    assert result["status"] == "error"
    assert result.get("error_type") == "SandboxViolation"
    assert "Import of 'os' is blocked" in result.get("message", "")