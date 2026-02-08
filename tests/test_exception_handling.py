"""Tests for exception handling in main.py.

This module tests exception handling for edge cases like builtin functions
that don't support inspect.signature().
"""

import pytest

from main import _extract_function_signature


class TestExtractFunctionSignature:
    """Test exception handling in _extract_function_signature."""

    def test_builtin_function_returns_fallback(self):
        """Test that builtin functions return None (triggering fallback).

        Builtin functions like max, min, str don't have inspectable signatures
        and raise ValueError when calling inspect.signature(). This test ensures
        the function handles this gracefully.

        Note: In Python 3.14+, some builtins like len, print, abs now have
        inspectable signatures, but others like max, min, str, int still
        raise ValueError.
        """
        import builtins

        # Test builtin functions that are known to raise ValueError
        # These are the ones that actually fail in Python 3.14
        value_error_builtins = ["max", "min", "str", "int"]

        for func_name in value_error_builtins:
            result = _extract_function_signature(builtins, func_name)
            # Should return None to trigger fallback to "(*args, **kwargs)"
            assert result is None, f"Expected None for builtin {func_name}, got {result}"

        # Verify that builtins with valid signatures still work
        # This ensures the fix doesn't break normal function handling
        valid_sig_builtins = ["len", "abs", "ord", "chr"]
        for func_name in valid_sig_builtins:
            result = _extract_function_signature(builtins, func_name)
            # These should return a signature string
            assert result is not None, f"Expected signature for builtin {func_name}, got None"
            assert isinstance(result, str), f"Expected str for builtin {func_name}, got {type(result)}"

    def test_normal_function_returns_signature(self):
        """Test that normal Python functions return their signature."""
        import types

        # Create a simple module with a normal function
        module = types.ModuleType("test_module")

        def normal_func(x: int, y: str) -> bool:
            return True

        module.normal_func = normal_func

        result = _extract_function_signature(module, "normal_func")
        # Should return a proper signature string
        assert result is not None
        assert "x: int" in result
        assert "y: str" in result
        assert "-> bool" in result

    def test_function_with_defaults(self):
        """Test that functions with default values work correctly."""
        import types

        module = types.ModuleType("test_module")

        def func_with_defaults(a: int, b: int = 10) -> int:
            return a + b

        module.func_with_defaults = func_with_defaults

        result = _extract_function_signature(module, "func_with_defaults")
        assert result is not None
        assert "a: int" in result
        assert "b: int = 10" in result

    def test_function_without_annotations(self):
        """Test that functions without type annotations work correctly."""
        import types

        module = types.ModuleType("test_module")

        def func_no_annotations(x, y):
            return x + y

        module.func_no_annotations = func_no_annotations

        result = _extract_function_signature(module, "func_no_annotations")
        assert result is not None
        # Should have parameter names even without annotations
        assert "x" in result
        assert "y" in result

    def test_nonexistent_function_returns_none(self):
        """Test that requesting a nonexistent function returns None."""
        import types

        module = types.ModuleType("test_module")

        result = _extract_function_signature(module, "nonexistent_func")
        assert result is None

    def test_c_extension_function_handling(self):
        """Test that C extension functions are handled gracefully.

        C extension functions (like those from builtins or compiled modules)
        also raise ValueError for inspect.signature(). This test targets
        specific builtins that are known to raise ValueError.
        """
        import builtins

        # Test specific C builtin types/functions that raise ValueError
        # These are the ones that actually fail with ValueError in Python 3.14+
        value_error_builtins = ["max", "min", "str", "int"]

        for func_name in value_error_builtins:
            if hasattr(builtins, func_name):
                result = _extract_function_signature(builtins, func_name)
                # These should return None since inspect.signature raises ValueError
                assert result is None, f"Expected None for C builtin {func_name}, got {result}"
