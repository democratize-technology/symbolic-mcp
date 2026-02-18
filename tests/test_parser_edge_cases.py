"""Edge case tests for the internal function argument parser.

This module provides unit tests for the _parse_function_args function and the
health_check tool to improve code coverage.
"""

import pytest

from main import _parse_function_args, logic_health_check


class TestFunctionArgsParser:
    """Tests for the _parse_function_args internal helper."""

    def test_parse_simple_args(self) -> None:
        """Test parsing simple comma-separated arguments."""
        assert _parse_function_args("1, 2, 3") == ["1", "2", "3"]
        assert _parse_function_args("True, False, None") == ["True", "False", "None"]
        assert _parse_function_args("'a', 'b', 'c'") == ["'a'", "'b'", "'c'"]

    def test_parse_nested_parentheses(self) -> None:
        """Test parsing arguments with nested parentheses."""
        assert _parse_function_args("f(1, 2), g(3)") == ["f(1, 2)", "g(3)"]
        assert _parse_function_args("((1, 2), 3)") == ["((1, 2), 3)"]

    def test_parse_nested_brackets(self) -> None:
        """Test parsing arguments with nested square brackets (lists)."""
        assert _parse_function_args("[1, 2], [3, 4]") == ["[1, 2]", "[3, 4]"]
        assert _parse_function_args("f([1, 2]), 3") == ["f([1, 2])", "3"]

    def test_parse_nested_braces(self) -> None:
        """Test parsing arguments with nested curly braces (dicts/sets)."""
        assert _parse_function_args("{'a': 1, 'b': 2}, {'c': 3}") == [
            "{'a': 1, 'b': 2}",
            "{'c': 3}",
        ]
        assert _parse_function_args("f({'a': 1}), 2") == ["f({'a': 1})", "2"]

    def test_parse_complex_nesting(self) -> None:
        """Test parsing arguments with complex mixed nesting."""
        args_str = "[1, (2, 3)], {'a': [4, 5]}, f(g(6), 7)"
        expected = ["[1, (2, 3)]", "{'a': [4, 5]}", "f(g(6), 7)"]
        assert _parse_function_args(args_str) == expected

    def test_parse_strings_with_commas(self) -> None:
        """Test that commas inside strings are not treated as separators."""
        assert _parse_function_args("'a,b', \"c,d\"") == ["'a,b'", '"c,d"']
        assert _parse_function_args("'f(a,b)', 1") == ["'f(a,b)'", "1"]

    def test_parse_empty_and_whitespace(self) -> None:
        """Test parsing empty strings and various whitespace."""
        assert _parse_function_args("") == []
        assert _parse_function_args("   ") == []
        assert _parse_function_args(" 1 ,  2  ") == ["1", "2"]

    def test_parse_escaped_backslash_before_quote(self) -> None:
        """Test that escaped backslashes before quotes are handled correctly.

        Note: The current implementation might fail on this as it only checks
        if the previous character is a backslash.
        """
        # "a\\" is a string ending with a backslash
        # The quote after it should be a separator or part of next arg
        assert _parse_function_args("'a\\\\', 'b'") == ["'a\\\\'", "'b'"]

    def test_parse_escaped_quotes(self) -> None:
        """Test that escaped quotes are handled correctly."""
        assert _parse_function_args("'a\\'b', 'c'") == ["'a\\'b'", "'c'"]


class TestHealthCheck:
    """Tests for the health_check tool."""

    def test_health_check_returns_valid_structure(self) -> None:
        """Verify that health_check returns the expected dictionary structure."""
        result = logic_health_check()
        assert result["status"] == "healthy"
        assert "version" in result
        assert "python_version" in result
        assert "crosshair_version" in result
        assert "z3_version" in result
        assert "platform" in result
        assert isinstance(result["memory_usage_mb"], float)
        assert result["memory_usage_mb"] > 0
