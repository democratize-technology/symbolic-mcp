"""
Test for integer parsing vulnerability in main.py.

This test demonstrates the bug where `val.lstrip("-").isdigit()` can be bypassed.
For example, "--123" passes the check (lstrip removes both '-' characters), but
int("--123") raises ValueError.
"""

import pytest


def test_lstrip_vulnerability_demonstration():
    """
    This test demonstrates the vulnerability in the original code.

    The check `val.lstrip("-").isdigit()` returns True for "--123",
    but `int("--123")` raises ValueError.
    """
    # These values pass the lstrip check but fail int() conversion
    vulnerable_values = ["--123", "---42", "--10", "--0"]

    for val in vulnerable_values:
        # This is what the buggy code does
        passes_check = val.lstrip("-").isdigit()
        assert passes_check, f"Expected {val} to pass the lstrip check"

        # But int() conversion fails
        with pytest.raises(ValueError, match="invalid literal for int\\(\\)"):
            int(val)


def test_correct_integer_detection():
    """
    Test the correct way to detect if a string is a valid integer.
    """
    # Valid integers - should be detected
    valid_integers = ["123", "-123", "0", "-0", "42", "-42"]

    for val in valid_integers:
        # Correct approach: try int() and catch ValueError
        try:
            result = int(val)
            # If we get here, it's a valid integer
            assert isinstance(result, int)
        except ValueError:
            pytest.fail(f"{val} should be a valid integer")


def test_invalid_integer_detection():
    """
    Test that invalid integers are properly rejected.
    """
    # Invalid values - should NOT parse as integers
    invalid_values = ["--123", "---42", "--10", "--0", "abc", "12.34", "1e5", ""]

    for val in invalid_values:
        # Should raise ValueError
        with pytest.raises(ValueError):
            int(val)


def test_integer_parsing_with_try_except():
    """
    Test the recommended fix: use try/except directly around int() conversion.
    """

    def safe_parse_int(val: str):
        """Safely parse an integer, returning None if not parseable."""
        try:
            return int(val)
        except ValueError:
            return None

    # Valid integers
    assert safe_parse_int("123") == 123
    assert safe_parse_int("-123") == -123
    assert safe_parse_int("0") == 0
    assert safe_parse_int("-0") == 0
    assert safe_parse_int("42") == 42
    assert safe_parse_int("-42") == -42

    # Invalid values that crash the original code
    assert safe_parse_int("--123") is None
    assert safe_parse_int("---42") is None
    assert safe_parse_int("--10") is None
    assert safe_parse_int("--0") is None

    # Other invalid values
    assert safe_parse_int("abc") is None
    assert safe_parse_int("12.34") is None
    assert safe_parse_int("") is None
    assert safe_parse_int("1e5") is None


def test_integer_parsing_edge_cases():
    """
    Test edge cases for integer parsing.
    """

    def safe_parse_int(val: str):
        """Safely parse an integer, returning None if not parseable."""
        try:
            return int(val)
        except ValueError:
            return None

    # Very large numbers
    large_number = "9" * 100
    assert safe_parse_int(large_number) == int(large_number)

    # Negative with leading zeros (valid in Python)
    assert safe_parse_int("-00042") == -42
    assert safe_parse_int("00042") == 42

    # Whitespace (Python int() handles this)
    assert safe_parse_int("  42  ") == 42
    assert safe_parse_int("  -42  ") == -42

    # But multiple signs are still invalid
    assert safe_parse_int("+-42") is None
    assert safe_parse_int("-+42") is None
