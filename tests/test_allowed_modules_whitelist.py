"""
SPDX-License-Identifier: MIT
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

"""
TEST: ALLOWED_MODULES Whitelist Implementation (Specification Section 3.3)

This test verifies that the ALLOWED_MODULES whitelist is implemented correctly
according to the exact specification requirements.

SPECIFICATION REQUIREMENT:
The whitelist must contain exactly these 22 modules:
- math, random, string, collections, itertools
- functools, operator, typing, re, json
- datetime, decimal, fractions, statistics
- dataclasses, enum, copy, heapq, bisect
- typing_extensions, abc

SECURITY ARCHITECTURE:
- BLOCKED_MODULES = absolute deny list (existing)
- ALLOWED_MODULES = explicit allow list (to be implemented)
- Default behavior = deny everything else (defense-in-depth)
"""
import sys
import pytest
import tempfile
import importlib.util
import os

# Import from main.py to test the actual implementation
from main import RestrictedImporter, SymbolicAnalyzer


class TestAllowedModulesWhitelist:
    """
    Comprehensive test suite for ALLOWED_MODULES whitelist implementation.
    Tests both the whitelist functionality and defense-in-depth security.
    """

    # Specification requirement: exact whitelist content
    SPECIFICATION_ALLOWED_MODULES = frozenset({
        'math', 'random', 'string', 'collections', 'itertools',
        'functools', 'operator', 'typing', 're', 'json',
        'datetime', 'decimal', 'fractions', 'statistics',
        'dataclasses', 'enum', 'copy', 'heapq', 'bisect',
        'typing_extensions', 'abc',
    })

    def test_specification_allowed_modules_constant_exists(self):
        """
        CRITICAL: The ALLOWED_MODULES frozenset must exist and match specification exactly.
        """
        # Test that the constant exists
        assert hasattr(RestrictedImporter, 'ALLOWED_MODULES'), "ALLOWED_MODULES constant must exist"

        # Test that it's a frozenset
        assert isinstance(RestrictedImporter.ALLOWED_MODULES, frozenset), "ALLOWED_MODULES must be a frozenset"

        # Test that it matches specification exactly
        assert RestrictedImporter.ALLOWED_MODULES == self.SPECIFICATION_ALLOWED_MODULES, \
            f"ALLOWED_MODULES must match specification exactly. Expected: {self.SPECIFICATION_ALLOWED_MODULES}, Got: {RestrictedImporter.ALLOWED_MODULES}"

    def test_whitelist_allows_specification_modules(self):
        """
        Test that all modules in the specification whitelist can be imported.
        """
        RestrictedImporter.install()

        try:
            for module_name in self.SPECIFICATION_ALLOWED_MODULES:
                # Skip typing_extensions as it might not be installed in test environment
                if module_name == 'typing_extensions':
                    continue

                try:
                    __import__(module_name)
                    print(f"✓ Allowed module '{module_name}' imported successfully")
                except ImportError as e:
                    # Some modules might not be available, but they shouldn't be blocked by our importer
                    assert "blocked in symbolic execution sandbox" not in str(e), \
                        f"Module '{module_name}' should not be blocked by RestrictedImporter: {e}"
        finally:
            RestrictedImporter.uninstall()

    def test_whitelist_blocks_non_allowed_modules(self):
        """
        Test that modules not in whitelist are blocked (defense-in-depth).
        """
        RestrictedImporter.install()

        try:
            # Test modules that are commonly available but not in whitelist
            non_allowed_modules = [
                'os', 'sys', 'subprocess', 'socket', 'http',
                'urllib', 'requests', 'pathlib', 'pickle', 'shelve'
            ]

            for module_name in non_allowed_modules:
                if module_name in sys.modules:  # Skip if already loaded
                    continue

                with pytest.raises(ImportError, match=f"Import of '{module_name}' is blocked"):
                    __import__(module_name)
                print(f"✓ Non-allowed module '{module_name}' correctly blocked")

        finally:
            RestrictedImporter.uninstall()

    def test_whitelist_blocks_even_standard_library_modules(self):
        """
        CRITICAL: Test that even standard library modules not in whitelist are blocked.
        This verifies defense-in-depth - default behavior is deny.
        """
        RestrictedImporter.install()

        try:
            # These are standard library modules NOT in the whitelist
            standard_lib_not_whitelisted = [
                'sqlite3', 'csv', 'xml', 'html', 'email',
                'mimetypes', 'base64', 'uuid', 'hashlib'
            ]

            for module_name in standard_lib_not_whitelisted:
                if module_name in sys.modules:  # Skip if already loaded
                    continue

                with pytest.raises(ImportError, match=f"Import of '{module_name}' is blocked"):
                    __import__(module_name)
                print(f"✓ Standard library module '{module_name}' correctly blocked (not in whitelist)")

        finally:
            RestrictedImporter.uninstall()

    def test_symbolic_execution_respects_whitelist(self):
        """
        Test that symbolic execution properly respects the whitelist.
        """
        RestrictedImporter.install()

        try:
            analyzer = SymbolicAnalyzer(timeout_seconds=5)

            # Test 1: Symbolic code with allowed modules should work
            allowed_module_code = """
import math
import collections
def compute_stats(numbers: list) -> dict:
    return {
        'sum': math.fsum(numbers),
        'count': len(numbers),
        'min': min(numbers),
        'max': max(numbers)
    }
"""

            result = analyzer.analyze(allowed_module_code, "compute_stats")
            # Should not fail due to import restrictions
            assert result.get("error_type") not in ["ImportError", "SandboxViolation"], \
                f"Allowed modules should work in symbolic execution: {result}"
            print("✓ Symbolic execution allows whitelisted modules")

            # Test 2: Symbolic code with non-allowed modules should be blocked
            non_allowed_module_code = """
import os  # Should be blocked by whitelist
def read_file(filename: str) -> str:
    with open(filename, 'r') as f:
        return f.read()
"""

            result = analyzer.analyze(non_allowed_module_code, "read_file")
            assert result["status"] == "error", f"Expected error for non-allowed import, got {result['status']}"
            assert result.get("error_type") in ["ImportError", "SandboxViolation"], \
                f"Expected import error, got {result.get('error_type')}: {result}"
            print("✓ Symbolic execution blocks non-whitelisted modules")

        finally:
            RestrictedImporter.uninstall()

    def test_whitelist_blocks_submodules_of_non_allowed_modules(self):
        """
        Test that submodules of non-allowed modules are also blocked.
        """
        RestrictedImporter.install()

        try:
            # These should be blocked because their parent modules are not whitelisted
            blocked_submodules = [
                'os.path',        # os is not whitelisted
                'sys.exit',       # sys is not whitelisted
                'json.decoder',   # json is whitelisted, so this should work
            ]

            # Test blocked submodules
            with pytest.raises(ImportError, match="Import of 'os.path' is blocked"):
                __import__('os.path')
            print("✓ Non-allowed submodule 'os.path' blocked")

            # Test that submodules of whitelisted modules work
            try:
                import json.decoder  # json is in whitelist
                print("✓ Whitelisted submodule 'json.decoder' allowed")
            except ImportError as e:
                assert "blocked in symbolic execution sandbox" not in str(e), \
                    f"Whitelisted submodule should not be blocked: {e}"

        finally:
            RestrictedImporter.uninstall()

    def test_comprehensive_security_architecture(self):
        """
        Test the complete security architecture: BLOCKED + ALLOWED + default deny.
        """
        RestrictedImporter.install()

        try:
            # Layer 1: BLOCKED_MODULES should still work
            assert hasattr(RestrictedImporter, 'BLOCKED_MODULES'), "BLOCKED_MODULES must still exist"
            assert len(RestrictedImporter.BLOCKED_MODULES) > 0, "BLOCKED_MODULES should not be empty"
            print("✓ BLOCKED_MODULES still present")

            # Layer 2: ALLOWED_MODULES should be defined
            assert hasattr(RestrictedImporter, 'ALLOWED_MODULES'), "ALLOWED_MODULES must exist"
            assert len(RestrictedImporter.ALLOWED_MODULES) == 21, "ALLOWED_MODULES should have 21 modules"
            print("✓ ALLOWED_MODULES present with correct size")

            # Layer 3: No overlap between blocked and allowed
            overlap = RestrictedImporter.BLOCKED_MODULES.intersection(RestrictedImporter.ALLOWED_MODULES)
            assert len(overlap) == 0, f"BLOCKED and ALLOWED modules should not overlap: {overlap}"
            print("✓ No overlap between BLOCKED and ALLOWED modules")

            # Layer 4: Defense-in-depth - default deny behavior
            with pytest.raises(ImportError, match="Import of 'some_nonexistent_module_12345' is blocked"):
                __import__('some_nonexistent_module_12345')
            print("✓ Default deny behavior working")

        finally:
            RestrictedImporter.uninstall()

    def test_installation_maintains_security_properties(self):
        """
        Test that installing/uninstalling maintains all security properties.
        """
        original_meta_path = sys.meta_path.copy()

        # Test installation
        RestrictedImporter.install()
        assert any(isinstance(f, RestrictedImporter) for f in sys.meta_path), \
            "RestrictedImporter should be in meta_path after installation"

        # Test that whitelist is active
        with pytest.raises(ImportError, match="Import of 'os' is blocked"):
            __import__('os')

        # Test uninstallation
        RestrictedImporter.uninstall()
        assert not any(isinstance(f, RestrictedImporter) for f in sys.meta_path), \
            "RestrictedImporter should be removed from meta_path after uninstallation"

        # Test that restrictions are lifted
        try:
            __import__('os')  # Should work after uninstallation
            print("✓ Installation/uninstallation cycle works correctly")
        except ImportError:
            pytest.fail("Module import should work after uninstallation")


if __name__ == "__main__":
    print("=== ALLOWED_MODULES WHITELIST IMPLEMENTATION TEST ===")
    print("Testing Specification Section 3.3 Compliance")
    print()

    # Run tests
    test_instance = TestAllowedModulesWhitelist()

    try:
        test_instance.test_specification_allowed_modules_constant_exists()
        print("✅ ALLOWED_MODULES constant exists and matches specification")
    except AssertionError as e:
        print(f"❌ FAILED: {e}")

    try:
        test_instance.test_whitelist_allows_specification_modules()
        print("✅ Whitelist allows specification modules")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    try:
        test_instance.test_whitelist_blocks_non_allowed_modules()
        print("✅ Whitelist blocks non-allowed modules")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    try:
        test_instance.test_comprehensive_security_architecture()
        print("✅ Comprehensive security architecture working")
    except Exception as e:
        print(f"❌ FAILED: {e}")

    print()
    print("=== WHITELIST TEST COMPLETE ===")