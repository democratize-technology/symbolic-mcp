"""Edge case tests for AST pattern matching in validate_code().

These tests verify that validate_code handles edge cases in import statements
without crashing. The main issue is that node.names[0] could raise IndexError
and node.module could be None for relative imports.

NOTE: These tests do NOT require CrossHair mocking. The validate_code function
and BLOCKED_MODULES constant have no CrossHair dependencies.
"""

import pytest

from symbolic_mcp import validate_code


class TestImportEdgeCases:
    """Tests for edge cases in import statement parsing."""

    def test_relative_import_from_current_package(self) -> None:
        """Test that relative imports like 'from . import foo' are handled."""
        # This is valid Python and node.module could be None for relative imports
        # Relative imports are allowed since they reference local package modules
        code = "from . import foo\ndef bar(): return foo"
        result = validate_code(code)
        assert result["valid"] is True

    def test_relative_import_from_parent_package(self) -> None:
        """Test that relative imports like 'from .. import foo' are handled."""
        # Relative imports are allowed since they reference local package modules
        code = "from .. import foo\ndef bar(): return foo"
        result = validate_code(code)
        assert result["valid"] is True

    def test_relative_import_with_submodule(self) -> None:
        """Test 'from .submodule import something'."""
        # Relative imports are allowed since they reference local package modules
        code = "from .utils import helper\ndef bar(): return helper()"
        result = validate_code(code)
        assert result["valid"] is True

    def test_import_star(self) -> None:
        """Test 'from module import *' statement."""
        # math is a safe module, so star import is valid
        code = "from math import *\ndef bar(): return sqrt(4)"
        result = validate_code(code)
        assert result["valid"] is True

    def test_import_multiple_names(self) -> None:
        """Test importing multiple names from a module."""
        code = "from math import sin, cos, tan\ndef bar(): return sin(0)"
        result = validate_code(code)
        # math is allowed, so should be valid
        assert result["valid"] is True

    def test_import_with_as_clause(self) -> None:
        """Test import with aliasing."""
        code = "import math as m\ndef bar(): return m.sqrt(4)"
        result = validate_code(code)
        assert result["valid"] is True

    def test_from_import_with_as_clause(self) -> None:
        """Test from import with aliasing."""
        code = "from math import sqrt as square_root\ndef bar(): return square_root(4)"
        result = validate_code(code)
        assert result["valid"] is True


class TestMalformedImportStatements:
    """Tests for edge cases that could have empty or unusual AST structures."""

    def test_bare_import(self) -> None:
        """Test a simple bare import statement."""
        code = "import math\ndef bar(): return math.sqrt(4)"
        result = validate_code(code)
        assert result["valid"] is True

    def test_semicolon_separated_imports(self) -> None:
        """Test multiple imports on one line separated by semicolons."""
        code = "import math; import random\ndef bar(): return math.sqrt(4)"
        result = validate_code(code)
        assert result["valid"] is True

    def test_escaped_newline_in_import(self) -> None:
        """Test import with escaped newline."""
        code = "from math \\\n    import sqrt\ndef bar(): return sqrt(4)"
        result = validate_code(code)
        assert result["valid"] is True


class TestBlockedModulesWithEdgeCases:
    """Test that blocked module detection works with various import styles."""

    @pytest.mark.parametrize(
        "code,expected_error_module",
        [
            ("from os import path\ndef bar(): return path.exists('/tmp')", "os"),
            ("import os\ndef bar(): pass", "os"),
            ("import os.path\ndef bar(): pass", "os"),
        ],
        ids=["from_import", "bare_import", "dotted_name"],
    )
    def test_blocked_module_detection(
        self, code: str, expected_error_module: str
    ) -> None:
        """Verify blocked modules are caught regardless of import style."""
        result = validate_code(code)
        assert result["valid"] is False
        assert expected_error_module in result["error"]


class TestSafeModulesWithEdgeCases:
    """Test that safe modules work with various import styles."""

    @pytest.mark.parametrize(
        "code",
        [
            "from math import sqrt\ndef bar(): return sqrt(4)",
            "import math\ndef bar(): return math.sqrt(4)",
            "import collections.abc\ndef bar(): pass",
        ],
        ids=["from_import", "bare_import", "dotted_name"],
    )
    def test_safe_module_validation(self, code: str) -> None:
        """Verify safe modules are allowed regardless of import style."""
        result = validate_code(code)
        assert result["valid"] is True
