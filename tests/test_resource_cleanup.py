"""Test resource cleanup for temporary files.

This test verifies that temporary files created during analysis are
properly cleaned up, even on error paths.

Resource leak scenario: If an exception occurs after tempfile is created
with delete=False but before the try block is entered, the file may not
be cleaned up.
"""

import os
import tempfile
from unittest.mock import patch

import pytest

from main import SymbolicAnalyzer, logic_compare_functions, logic_find_path_to_exception


class TestTemporaryFileCleanup:
    """Tests for temporary file cleanup."""

    def test_temporary_module_context_manager_cleanup_on_success(self):
        """Test that _temporary_module cleans up on normal exit."""
        analyzer = SymbolicAnalyzer()

        code = """
def simple_function(x: int) -> int:
    '''post: _ >= x'''
    return x + 1
"""

        # Track created temp files
        temp_files_created = []
        original_named_temporary_file = tempfile.NamedTemporaryFile

        def tracking_named_temporary_file(*args, **kwargs):
            """Track temp file creation."""
            result = original_named_temporary_file(*args, **kwargs)
            temp_files_created.append(result.name)
            return result

        with patch("tempfile.NamedTemporaryFile", tracking_named_temporary_file):
            result = analyzer.analyze(code, "simple_function")

        # Verify analysis succeeded (valid status values per spec)
        assert result["status"] in ("verified", "counterexample", "timeout", "error")

        # Verify all temp files were cleaned up
        for temp_file in temp_files_created:
            if temp_file.endswith(".py"):
                assert not os.path.exists(
                    temp_file
                ), f"Temp file not cleaned up: {temp_file}"

    def test_temporary_module_context_manager_cleanup_on_error(self):
        """Test that _temporary_module cleans up even when module loading fails."""
        analyzer = SymbolicAnalyzer()

        # Invalid code that will fail during import
        code = """
def broken_function():
    this_is_not_a_valid_identifier_!!!
"""

        # Track created temp files
        temp_files_created = []
        original_named_temporary_file = tempfile.NamedTemporaryFile

        def tracking_named_temporary_file(*args, **kwargs):
            """Track temp file creation."""
            result = original_named_temporary_file(*args, **kwargs)
            temp_files_created.append(result.name)
            return result

        with patch("tempfile.NamedTemporaryFile", tracking_named_temporary_file):
            result = analyzer.analyze(code, "broken_function")

        # Verify analysis returned an error
        assert result["status"] == "error"

        # Verify all temp files were cleaned up
        for temp_file in temp_files_created:
            if temp_file.endswith(".py"):
                assert not os.path.exists(
                    temp_file
                ), f"Temp file not cleaned up on error: {temp_file}"

    def test_find_path_to_exception_cleans_up_temp_files(self):
        """Test that logic_find_path_to_exception properly cleans up temp files."""
        code = """
def test_func(x: int) -> int:
    return x
"""

        # Track created temp files
        temp_files_created = []
        original_named_temporary_file = tempfile.NamedTemporaryFile

        def tracking_named_temporary_file(*args, **kwargs):
            """Track temp file creation."""
            result = original_named_temporary_file(*args, **kwargs)
            temp_files_created.append(result.name)
            return result

        with patch("tempfile.NamedTemporaryFile", tracking_named_temporary_file):
            result = logic_find_path_to_exception(code, "test_func", "ValueError", 30)

        # Verify function completed
        assert "status" in result

        # Verify all temp files were cleaned up
        for temp_file in temp_files_created:
            if temp_file.endswith(".py"):
                assert not os.path.exists(
                    temp_file
                ), f"Temp file not cleaned up: {temp_file}"

    def test_find_path_to_exception_cleans_up_on_validation_error(self):
        """Test cleanup when validation fails early."""
        # Invalid code with dangerous function call
        code = """
def test_func():
    eval("print('dangerous')")
"""

        # Track created temp files
        temp_files_created = []
        original_named_temporary_file = tempfile.NamedTemporaryFile

        def tracking_named_temporary_file(*args, **kwargs):
            """Track temp file creation."""
            result = original_named_temporary_file(*args, **kwargs)
            temp_files_created.append(result.name)
            return result

        with patch("tempfile.NamedTemporaryFile", tracking_named_temporary_file):
            result = logic_find_path_to_exception(code, "test_func", "ValueError", 30)

        # Verify validation failed
        assert result["status"] == "error"
        assert "ValidationError" in result.get("error_type", "")

        # Verify no temp files were left behind
        for temp_file in temp_files_created:
            if temp_file.endswith(".py"):
                assert not os.path.exists(
                    temp_file
                ), f"Temp file not cleaned up: {temp_file}"

    def test_compare_functions_cleans_up_temp_files(self):
        """Test that logic_compare_functions properly cleans up temp files."""
        code = """
def func_a(x: int) -> int:
    return x

def func_b(x: int) -> int:
    return x
"""

        # Track created temp files
        temp_files_created = []
        original_named_temporary_file = tempfile.NamedTemporaryFile

        def tracking_named_temporary_file(*args, **kwargs):
            """Track temp file creation."""
            result = original_named_temporary_file(*args, **kwargs)
            temp_files_created.append(result.name)
            return result

        with patch("tempfile.NamedTemporaryFile", tracking_named_temporary_file):
            result = logic_compare_functions(code, "func_a", "func_b", 30)

        # Verify function completed
        assert "status" in result

        # Verify all temp files were cleaned up
        for temp_file in temp_files_created:
            if temp_file.endswith(".py"):
                assert not os.path.exists(
                    temp_file
                ), f"Temp file not cleaned up: {temp_file}"

    def test_compare_functions_cleans_up_on_validation_error(self):
        """Test cleanup when validation fails early in compare_functions."""
        # Invalid code with dangerous function call
        code = """
def func_a():
    eval("dangerous")

def func_b():
    return 1
"""

        # Track created temp files
        temp_files_created = []
        original_named_temporary_file = tempfile.NamedTemporaryFile

        def tracking_named_temporary_file(*args, **kwargs):
            """Track temp file creation."""
            result = original_named_temporary_file(*args, **kwargs)
            temp_files_created.append(result.name)
            return result

        with patch("tempfile.NamedTemporaryFile", tracking_named_temporary_file):
            result = logic_compare_functions(code, "func_a", "func_b", 30)

        # Verify validation failed
        assert result["status"] == "error"
        assert "ValidationError" in result.get("error_type", "")

        # Verify no temp files were left behind
        for temp_file in temp_files_created:
            if temp_file.endswith(".py"):
                assert not os.path.exists(
                    temp_file
                ), f"Temp file not cleaned up: {temp_file}"

    def test_temporary_module_cleanup_on_exception_before_try(self):
        """Test the race condition where exception occurs before try block.

        This simulates the scenario where an exception could occur between
        tempfile creation and entering the try block (e.g., in spec_from_file_location).
        """
        import importlib.util

        analyzer = SymbolicAnalyzer()

        code = """
def simple_function(x: int) -> int:
    return x + 1
"""

        # Track created temp files
        temp_files_created = []
        original_named_temporary_file = tempfile.NamedTemporaryFile

        def tracking_named_temporary_file(*args, **kwargs):
            """Track temp file creation."""
            result = original_named_temporary_file(*args, **kwargs)
            temp_files_created.append(result.name)
            return result

        # Even if spec_from_file_location fails, cleanup should happen
        call_count = [0]

        def failing_spec_from_file_location(*args, **kwargs):
            """Make spec_from_file_location fail on first call."""
            call_count[0] += 1
            if call_count[0] == 1:
                raise RuntimeError("Simulated failure in spec_from_file_location")
            return importlib.util.spec_from_file_location(*args, **kwargs)

        with patch("tempfile.NamedTemporaryFile", tracking_named_temporary_file):
            with patch(
                "importlib.util.spec_from_file_location",
                failing_spec_from_file_location,
            ):
                result = analyzer.analyze(code, "simple_function")

        # Verify analysis returned an error
        assert result["status"] == "error"

        # Verify all temp files were cleaned up (context manager ensures this)
        for temp_file in temp_files_created:
            if temp_file.endswith(".py"):
                assert not os.path.exists(
                    temp_file
                ), f"Temp file not cleaned up on early exception: {temp_file}"
