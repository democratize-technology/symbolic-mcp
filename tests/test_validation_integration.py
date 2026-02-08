"""SPDX-License-Identifier: MIT
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

"""Integration tests that validate main.py has the same security as test_validation.py

These tests actually import from main.py to verify the production code has
the same security protections as the test code.

Note: These tests require CrossHair/Z3 to be properly installed.
"""

import os  # noqa: E402
import sys  # noqa: E402

# Add parent directory to path to import main
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main_validate_code(code: str):
    """Import and call validate_code from main.py"""
    # Import here to avoid early failure if crosshair not available
    from main import validate_code

    return validate_code(code)


class TestMainSecurityIntegration:
    """Test that main.py validate_code has the same security as test version."""

    def test_main_blocks_eval_with_space(self):
        """Verify main.py catches eval with space before paren."""
        code = "x = eval (1)"
        result = main_validate_code(code)
        assert result["valid"] is False
        assert "eval" in result["error"].lower()

    def test_main_blocks_exec_with_space(self):
        """Verify main.py catches exec with space before paren."""
        code = "x = exec ('print(1)')"
        result = main_validate_code(code)
        assert result["valid"] is False
        assert "exec" in result["error"].lower()

    def test_main_blocks_eval_in_list(self):
        """Verify main.py catches eval in list literal."""
        code = "x = [eval][0](1)"
        result = main_validate_code(code)
        assert result["valid"] is False
        assert "eval" in result["error"].lower()

    def test_main_blocks_eval_in_dict(self):
        """Verify main.py catches eval in dict literal."""
        code = 'x = {"f": eval}["f"](1)'
        result = main_validate_code(code)
        assert result["valid"] is False
        assert "eval" in result["error"].lower()

    def test_main_blocks_os_system_call(self):
        """Verify main.py catches os.system() calls."""
        code = "os.system('ls')"
        result = main_validate_code(code)
        assert result["valid"] is False
        assert "os" in result["error"].lower()

    def test_main_blocks_double_underscore_import(self):
        """Verify main.py catches __import__() calls."""
        code = "x = __import__('os')"
        result = main_validate_code(code)
        assert result["valid"] is False
        assert (
            "__import__" in result["error"].lower()
            or "import" in result["error"].lower()
        )

    def test_main_accepts_safe_code(self):
        """Verify main.py accepts safe code."""
        code = "def f(x): return x + 1"
        result = main_validate_code(code)
        assert result["valid"] is True

    def test_main_blocks_os_import(self):
        """Verify main.py blocks os import."""
        code = "import os\ndef foo(): pass"
        result = main_validate_code(code)
        assert result["valid"] is False
        assert "os" in result["error"].lower()

    def test_main_blocks_subprocess_import(self):
        """Verify main.py blocks subprocess import."""
        code = "import subprocess\ndef foo(): pass"
        result = main_validate_code(code)
        assert result["valid"] is False
        assert "subprocess" in result["error"].lower()

    def test_main_has_dangerous_builtins_constant(self):
        """Verify main.py exports DANGEROUS_BUILTINS constant."""
        from main import DANGEROUS_BUILTINS

        assert isinstance(DANGEROUS_BUILTINS, frozenset)
        assert "eval" in DANGEROUS_BUILTINS
        assert "exec" in DANGEROUS_BUILTINS
        assert "compile" in DANGEROUS_BUILTINS

    def test_main_has_blocked_modules_constant(self):
        """Verify main.py exports BLOCKED_MODULES constant."""
        from main import BLOCKED_MODULES

        assert isinstance(BLOCKED_MODULES, frozenset)
        assert "os" in BLOCKED_MODULES
        assert "sys" in BLOCKED_MODULES
        assert "subprocess" in BLOCKED_MODULES
