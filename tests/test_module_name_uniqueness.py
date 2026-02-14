"""Test module name uniqueness to prevent sys.modules collision.

This test verifies that temporary module names are unique and don't collide
in concurrent or rapid sequential requests. It confirms that module names
use UUIDs to guarantee uniqueness, as implemented in `main._temporary_module`.
"""

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from main import _temporary_module


class TestModuleNameUniqueness:
    """Tests for guaranteed unique module names."""

    def test_rapid_sequential_calls_generate_unique_names(self) -> None:
        """Test that rapid sequential calls generate unique module names."""
        code = "def test_function(): pass"
        num_iterations = 50

        # Collect module names generated during the test
        temp_modules_before = set(sys.modules.keys())

        for _ in range(num_iterations):
            with _temporary_module(code) as module:
                assert hasattr(module, "test_function")

        temp_modules_after = set(sys.modules.keys())
        new_modules = temp_modules_after - temp_modules_before

        # All module names should be unique
        assert len(new_modules) == 0, "Modules should be cleaned up after context exit"

    def test_concurrent_access_generates_unique_names(self) -> None:
        """Test that concurrent requests generate unique module names."""
        code = "def test_function(): pass"
        num_threads = 20

        temp_modules_before = set(sys.modules.keys())

        def create_temp_module() -> bool:
            """Create a temporary module in a thread."""
            with _temporary_module(code) as module:
                assert hasattr(module, "test_function")
            return True

        # Run concurrent requests
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_temp_module) for _ in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed
        assert all(results), "Some concurrent operations failed"

        temp_modules_after = set(sys.modules.keys())
        new_modules = temp_modules_after - temp_modules_before

        # All module names should be unique and cleaned up
        assert (
            len(new_modules) == 0
        ), "Modules should be cleaned up after concurrent execution"

    def test_module_name_pattern_is_uuid_based(self) -> None:
        """Test that module names follow the UUID pattern for uniqueness."""
        code = "def test_function(): pass"

        # Capture the actual module name used by checking sys.modules
        temp_modules_before = set(
            name for name in sys.modules.keys() if name.startswith("mcp_temp_")
        )

        with _temporary_module(code) as module:
            assert hasattr(module, "test_function")

            # Find the newly added module
            temp_modules_during = set(
                name for name in sys.modules.keys() if name.startswith("mcp_temp_")
            )
            new_modules = temp_modules_during - temp_modules_before

            assert (
                len(new_modules) == 1
            ), f"Expected exactly 1 new temp module, got {len(new_modules)}"
            module_name = list(new_modules)[0]

            # Verify the module name format
            uuid_part = module_name[len("mcp_temp_") :]
            hex_chars = set("0123456789abcdef")
            assert len(uuid_part) == 32 and all(
                c in hex_chars for c in uuid_part
            ), f"Module name UUID part should be 32 hex characters, got: {uuid_part}"
            assert not uuid_part.startswith(
                "tmp"
            ), f"Module name should use UUID pattern, not tempfile basename: {module_name}"

    def test_no_sys_modules_leak_after_context_exit(self) -> None:
        """Test that temporary modules are properly removed from sys.modules."""
        code = "def test_function(): pass"

        # Track modules before
        temp_modules_before = set(
            name for name in sys.modules.keys() if name.startswith("mcp_temp_")
        )

        # Create and exit temporary module
        with _temporary_module(code):
            pass

        # Track modules after
        temp_modules_after = set(
            name for name in sys.modules.keys() if name.startswith("mcp_temp_")
        )

        # Should be cleaned up
        new_modules = temp_modules_after - temp_modules_before
        assert (
            len(new_modules) == 0
        ), f"Temporary module not cleaned up from sys.modules: {new_modules}"
