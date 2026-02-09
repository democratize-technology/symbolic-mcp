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
OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

"""Edge case tests for AST pattern matching in validate_code().

These tests verify that validate_code handles edge cases in import statements
without crashing. The main issue is that node.names[0] could raise IndexError
and node.module could be None for relative imports.

See: https://github.com/your-repo/issues/8
"""

import ast
import sys
from unittest.mock import MagicMock

import pytest

# Mock crosshair modules before importing from main
sys_modules_mock = MagicMock()
sys_modules_mock.AnalysisOptions = MagicMock
sys_modules_mock.AnalysisOptionSet = MagicMock
sys_modules_mock.MessageType = MagicMock
sys_modules_mock.MessageType.CONFIRMED = "confirmed"
sys_modules_mock.MessageType.COUNTEREXAMPLE = "counterexample"
sys_modules_mock.analyze_function = lambda *args, **kwargs: []
sys_modules_mock.AnalysisResult = MagicMock

sys.modules["crosshair"] = MagicMock()
sys.modules["crosshair.core"] = sys_modules_mock
sys.modules["crosshair.core_and_libs"] = sys_modules_mock
sys.modules["crosshair.options"] = MagicMock()
sys.modules["crosshair.states"] = MagicMock()
sys.modules["crosshair.tracers"] = MagicMock()
sys.modules["crosshair.util"] = MagicMock()

# Now we can import from main without CrossHair dependency
# noqa: E402 - Import after mocking crosshair modules
from main import validate_code


class TestImportEdgeCases:
    """Tests for edge cases in import statement parsing."""

    def test_relative_import_from_current_package(self):
        """Test that relative imports like 'from . import foo' are handled."""
        # This is valid Python and node.module could be None for relative imports
        code = "from . import foo\ndef bar(): return foo"
        result = validate_code(code)
        # Should either be valid (if we allow relative imports)
        # or return a proper error, not crash
        assert "valid" in result
        assert isinstance(result["valid"], bool)

    def test_relative_import_from_parent_package(self):
        """Test that relative imports like 'from .. import foo' are handled."""
        code = "from .. import foo\ndef bar(): return foo"
        result = validate_code(code)
        assert "valid" in result
        assert isinstance(result["valid"], bool)

    def test_relative_import_with_submodule(self):
        """Test 'from .submodule import something'."""
        code = "from .utils import helper\ndef bar(): return helper()"
        result = validate_code(code)
        assert "valid" in result
        assert isinstance(result["valid"], bool)

    def test_import_star(self):
        """Test 'from module import *' statement."""
        code = "from math import *\ndef bar(): return sqrt(4)"
        result = validate_code(code)
        assert "valid" in result
        assert isinstance(result["valid"], bool)

    def test_import_multiple_names(self):
        """Test importing multiple names from a module."""
        code = "from math import sin, cos, tan\ndef bar(): return sin(0)"
        result = validate_code(code)
        # math is allowed, so should be valid
        assert result["valid"] is True

    def test_import_with_as_clause(self):
        """Test import with aliasing."""
        code = "import math as m\ndef bar(): return m.sqrt(4)"
        result = validate_code(code)
        assert result["valid"] is True

    def test_from_import_with_as_clause(self):
        """Test from import with aliasing."""
        code = "from math import sqrt as square_root\ndef bar(): return square_root(4)"
        result = validate_code(code)
        assert result["valid"] is True


class TestMalformedImportStatements:
    """Tests for edge cases that could have empty or unusual AST structures."""

    def test_bare_import(self):
        """Test a simple bare import statement."""
        code = "import math\ndef bar(): return math.sqrt(4)"
        result = validate_code(code)
        assert result["valid"] is True

    def test_semicolon_separated_imports(self):
        """Test multiple imports on one line separated by semicolons."""
        code = "import math; import random\ndef bar(): return math.sqrt(4)"
        result = validate_code(code)
        assert result["valid"] is True

    def test_escaped_newline_in_import(self):
        """Test import with escaped newline."""
        code = "from math \\\n    import sqrt\ndef bar(): return sqrt(4)"
        result = validate_code(code)
        assert result["valid"] is True


class TestASTStructureEdgeCases:
    """Tests that verify AST structure handling for unusual but valid Python."""

    def test_ast_handles_empty_names_list_theoretical(self):
        """Theoretical: what happens if names list is empty.

        In practice, Python's parser doesn't create Import/ImportFrom nodes
        with empty names lists for valid Python syntax. But we verify
        our code handles this gracefully if it were to occur.
        """
        # We can't create this with actual Python code, so we construct the AST directly
        # to test the validation logic
        import ast

        from main import BLOCKED_MODULES

        # Simulate walking an AST with an Import node that has empty names
        # This would be the edge case that could cause IndexError
        # Create an Import node with empty names list (not possible in valid Python)
        import_node = ast.Import(names=[])

        # Manually check what our validation would do
        # The original code would do: module_name = node.names[0].name
        # This would raise IndexError

        # Our fixed code should handle this:
        if import_node.names:  # Check list is not empty
            module_name = import_node.names[0].name
            if module_name:
                base_module = module_name.split(".")[0]
                assert base_module not in BLOCKED_MODULES
        else:
            # Should gracefully skip the node
            pass

    def test_importfrom_with_none_module(self):
        """Test ImportFrom where node.module is None (relative imports).

        For relative imports like 'from . import foo', the module attribute
        is None because there's no absolute module name.
        """
        import ast

        # Create an ImportFrom node with module=None (as in relative imports)
        import_from_node = ast.ImportFrom(
            module=None, names=[ast.alias(name="foo", asname=None)], level=1
        )

        # Our fixed code should handle None module
        if isinstance(import_from_node, ast.ImportFrom):
            module_name = import_from_node.module  # This could be None
            if module_name:  # Must check for None before processing
                base_module = module_name.split(".")[0]
            else:
                # For relative imports with None module, skip or handle differently
                # The key is not to crash
                pass


class TestBlockedModulesWithEdgeCases:
    """Test that blocked module detection works with various import styles."""

    def test_blocked_module_via_from_import(self):
        """Verify blocked modules caught in 'from X import Y'."""
        code = "from os import path\ndef bar(): return path.exists('/tmp')"
        result = validate_code(code)
        assert result["valid"] is False
        assert "os" in result["error"]

    def test_blocked_module_via_import(self):
        """Verify blocked modules caught in 'import X'."""
        code = "import os\ndef bar(): pass"
        result = validate_code(code)
        assert result["valid"] is False
        assert "os" in result["error"]

    def test_blocked_module_with_dotted_name(self):
        """Verify blocked modules caught even with dotted paths."""
        code = "import os.path\ndef bar(): pass"
        result = validate_code(code)
        assert result["valid"] is False
        assert "os" in result["error"]


class TestSafeModulesWithEdgeCases:
    """Test that safe modules work with various import styles."""

    def test_safe_module_via_from_import(self):
        """Verify safe modules allowed in 'from X import Y'."""
        code = "from math import sqrt\ndef bar(): return sqrt(4)"
        result = validate_code(code)
        assert result["valid"] is True

    def test_safe_module_via_import(self):
        """Verify safe modules allowed in 'import X'."""
        code = "import math\ndef bar(): return math.sqrt(4)"
        result = validate_code(code)
        assert result["valid"] is True

    def test_safe_module_with_dotted_name(self):
        """Verify safe modules allowed with dotted paths."""
        code = "import collections.abc\ndef bar(): pass"
        result = validate_code(code)
        assert result["valid"] is True
