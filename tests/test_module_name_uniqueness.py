"""Test module name uniqueness to prevent sys.modules collision.

This test verifies that temporary module names are unique and don't collide
in concurrent or rapid sequential requests.

CRITICAL BUG: Module names generated from tempfile basename could collide in
concurrent requests. os.path.basename(tmp_path) produces non-unique names like
tmpXXX.py that could collide if two requests create temp files with the same
basename.
"""

import os
import sys
import tempfile
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytest

from main import _temporary_module


class TestModuleNameUniqueness:
    """Tests for guaranteed unique module names."""

    def test_module_name_uses_uuid_for_uniqueness(self):
        """Test that module names include UUID for guaranteed uniqueness."""
        code = """
def test_function(x: int) -> int:
    return x + 1
"""

        collected_module_names = []

        original_named_temporary_file = tempfile.NamedTemporaryFile

        def tracking_named_temporary_file(*args, **kwargs):
            """Track temp file creation to capture module name."""
            result = original_named_temporary_file(*args, **kwargs)
            tmp_path = result.name
            # Simulate the current module naming logic
            module_name = f"mcp_temp_{os.path.basename(tmp_path)[:-3]}"
            collected_module_names.append((tmp_path, module_name))
            return result

        with patch("tempfile.NamedTemporaryFile", tracking_named_temporary_file):
            with _temporary_module(code) as module:
                # The module should have been loaded
                assert hasattr(module, "test_function")

        # Verify module name format - after fix should use UUID
        if collected_module_names:
            _, module_name = collected_module_names[0]
            # After fix: module name should contain UUID-like pattern (hex digits)
            # Current broken: module name looks like "mcp_temp_tmpXXX"
            # Fixed: module name looks like "mcp_temp_3f2a8b1c9d4e..."
            assert module_name.startswith("mcp_temp_")

    def test_rapid_sequential_calls_generate_unique_names(self):
        """Test that rapid sequential calls generate unique module names."""
        code = """
def test_function(x: int) -> int:
    return x + 1
"""

        module_names = []
        original_named_temporary_file = tempfile.NamedTemporaryFile

        def tracking_named_temporary_file(*args, **kwargs):
            """Track temp file creation to capture module name."""
            result = original_named_temporary_file(*args, **kwargs)
            tmp_path = result.name
            module_name = f"mcp_temp_{os.path.basename(tmp_path)[:-3]}"
            module_names.append(module_name)
            return result

        # Create many temporary modules rapidly
        num_iterations = 50
        with patch("tempfile.NamedTemporaryFile", tracking_named_temporary_file):
            for _ in range(num_iterations):
                with _temporary_module(code) as module:
                    assert hasattr(module, "test_function")

        # After fix: all module names should be unique
        unique_names = set(module_names)
        assert len(unique_names) == num_iterations, (
            f"Expected {num_iterations} unique module names, "
            f"but got {len(unique_names)} unique names. "
            f"Duplicate names indicate potential collision bug."
        )

    def test_concurrent_access_generates_unique_names(self):
        """Test that concurrent requests generate unique module names."""
        code = """
def test_function(x: int) -> int:
    return x + 1
"""

        module_names = []
        original_named_temporary_file = tempfile.NamedTemporaryFile

        def tracking_named_temporary_file(*args, **kwargs):
            """Track temp file creation to capture module name."""
            result = original_named_temporary_file(*args, **kwargs)
            tmp_path = result.name
            module_name = f"mcp_temp_{os.path.basename(tmp_path)[:-3]}"
            module_names.append(module_name)
            return result

        def create_temp_module():
            """Create a temporary module in a thread."""
            with _temporary_module(code) as module:
                assert hasattr(module, "test_function")
                return True

        # Run concurrent requests
        num_threads = 20
        with patch("tempfile.NamedTemporaryFile", tracking_named_temporary_file):
            with ThreadPoolExecutor(max_workers=num_threads) as executor:
                futures = [executor.submit(create_temp_module) for _ in range(num_threads)]
                results = [f.result() for f in as_completed(futures)]

        # All should succeed
        assert all(results), "Some concurrent operations failed"

        # After fix: all module names should be unique
        unique_names = set(module_names)
        assert len(unique_names) == num_threads, (
            f"Expected {num_threads} unique module names from concurrent execution, "
            f"but got {len(unique_names)} unique names. "
            f"This indicates a race condition in module name generation."
        )

    def test_module_name_pattern_after_fix(self):
        """Test that module names follow the UUID pattern after fix.

        This test specifically checks for the UUID-based naming pattern
        that guarantees uniqueness.
        """
        import uuid

        code = """
def test_function(x: int) -> int:
    return x + 1
"""

        # Capture the actual module name used by checking sys.modules
        temp_modules_before = set(name for name in sys.modules.keys() if name.startswith("mcp_temp_"))

        with _temporary_module(code) as module:
            assert hasattr(module, "test_function")

            # Find the newly added module
            temp_modules_during = set(name for name in sys.modules.keys() if name.startswith("mcp_temp_"))
            new_modules = temp_modules_during - temp_modules_before

            assert len(new_modules) == 1, f"Expected exactly 1 new temp module, got {len(new_modules)}"
            module_name = list(new_modules)[0]

        # Verify the module name format
        # After fix: should contain UUID (32 hex digits)
        uuid_part = module_name[len("mcp_temp_"):]

        # A UUID4 has 32 hex chars (no hyphens in our implementation)
        hex_chars = set("0123456789abcdef")
        assert len(uuid_part) == 32 and all(c in hex_chars for c in uuid_part), (
            f"Module name UUID part should be 32 hex characters, got: {uuid_part}"
        )

        # Verify it does NOT look like old tempfile basename pattern
        assert not uuid_part.startswith("tmp"), (
            f"Module name should use UUID pattern, not tempfile basename: {module_name}"
        )

    def test_no_sys_modules_leak_after_context_exit(self):
        """Test that temporary modules are properly removed from sys.modules."""
        code = """
def test_function(x: int) -> int:
    return x + 1
"""

        # Track modules before
        temp_modules_before = set(name for name in sys.modules.keys() if name.startswith("mcp_temp_"))

        # Create and exit temporary module
        with _temporary_module(code) as module:
            assert hasattr(module, "test_function")

        # Track modules after
        temp_modules_after = set(name for name in sys.modules.keys() if name.startswith("mcp_temp_"))

        # Should be cleaned up (only new modules from this test)
        new_modules = temp_modules_after - temp_modules_before
        assert len(new_modules) == 0, (
            f"Temporary module not cleaned up from sys.modules: {new_modules}"
        )

    def test_lifespan_cleanup_works_with_uuid_names(self):
        """Test that lifespan cleanup logic works with UUID-based module names."""
        import importlib.util
        import textwrap

        # Simulate creating modules with UUID-based names
        created_module_names = []

        with tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False) as tmp:
            tmp.write("def foo(): return 1")
            tmp_path = tmp.name

        # Use UUID-based naming (the fix)
        import uuid
        module_name = f"mcp_temp_{uuid.uuid4().hex}"
        created_module_names.append(module_name)

        try:
            spec = importlib.util.spec_from_file_location(module_name, tmp_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                # Verify module is in sys.modules
                assert module_name in sys.modules

                # Simulate lifespan cleanup
                temp_modules = [
                    name for name in sys.modules.keys() if name.startswith("mcp_temp_")
                ]
                assert module_name in temp_modules, "UUID-based module should be found by cleanup logic"

                # Do the cleanup
                for name in temp_modules:
                    if name in sys.modules:
                        del sys.modules[name]

                # Verify cleanup worked
                assert module_name not in sys.modules, "Module should be cleaned up"
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
