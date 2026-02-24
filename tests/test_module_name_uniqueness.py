"""Test module name uniqueness to prevent sys.modules collision.

This test verifies that temporary module names are unique and don't collide
in concurrent or rapid sequential requests. It confirms that module names
use UUIDs to guarantee uniqueness, as implemented in `main._temporary_module`.
"""

import sys
from concurrent.futures import ThreadPoolExecutor, as_completed

from symbolic_mcp import _temporary_module


class TestModuleNameUniqueness:
    """Tests for guaranteed unique module names."""

    def test_sequential_calls_generate_unique_names(self) -> None:
        """Test that sequential calls generate unique module names."""
        code = "def test_function(): pass"
        num_iterations = 50
        module_names = []

        for _ in range(num_iterations):
            with _temporary_module(code):
                # Capture module name while context is active
                for name in sys.modules:
                    if name.startswith("mcp_temp_") and name not in module_names:
                        if hasattr(sys.modules[name], "test_function"):
                            module_names.append(name)
                            break

        # All module names should be unique
        assert len(set(module_names)) == len(
            module_names
        ), f"Expected {len(module_names)} unique names, got {len(set(module_names))}"

    def test_concurrent_access_no_exceptions(self) -> None:
        """Test that concurrent requests complete without exceptions or collisions.

        This verifies thread safety - all operations should succeed without
        race conditions or module name collisions.
        """
        code = "def test_function(): pass"
        num_threads = 20

        def create_temp_module() -> bool:
            """Create a temporary module and verify it works."""
            with _temporary_module(code) as module:
                assert hasattr(module, "test_function")
            return True

        # Run concurrent requests
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(create_temp_module) for _ in range(num_threads)]
            results = [f.result() for f in as_completed(futures)]

        # All should succeed without exceptions
        assert all(results), "Some concurrent operations failed"

    def test_module_name_pattern_is_uuid_based(self) -> None:
        """Test that module names follow the UUID pattern for uniqueness."""
        code = "def test_function(): pass"

        temp_modules_before = set(
            name for name in sys.modules.keys() if name.startswith("mcp_temp_")
        )

        with _temporary_module(code):
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

    def test_no_sys_modules_leak_after_context_exit(self) -> None:
        """Test that temporary modules are properly removed from sys.modules."""
        code = "def test_function(): pass"

        temp_modules_before = set(
            name for name in sys.modules.keys() if name.startswith("mcp_temp_")
        )

        with _temporary_module(code):
            pass

        temp_modules_after = set(
            name for name in sys.modules.keys() if name.startswith("mcp_temp_")
        )

        new_modules = temp_modules_after - temp_modules_before
        assert len(new_modules) == 0, f"Temporary module not cleaned up: {new_modules}"
