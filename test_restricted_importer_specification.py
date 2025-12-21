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
Tests for RestrictedImporter implementation based on Section 3.3 specification.

These tests verify that the RestrictedImporter implementation matches the specification EXACTLY.
"""
import sys
import pytest
from types import ModuleType
from typing import Any

# Import the RestrictedImporter that we need to implement
# This will fail initially since we haven't implemented it yet
try:
    from main import RestrictedImporter
except ImportError:
    RestrictedImporter = None


class TestRestrictedImporterSpecification:
    """Test suite for RestrictedImporter based on Section 3.3 specification."""

    def test_blocked_modules_frozenset_matches_specification(self):
        """Test that BLOCKED_MODULES frozenset matches specification exactly."""
        expected_blocked = frozenset({
            'os', 'sys', 'subprocess', 'shutil', 'pathlib',
            'socket', 'http', 'urllib', 'requests', 'ftplib',
            'pickle', 'shelve', 'marshal',
            'ctypes', 'multiprocessing',
            'importlib', 'runpy',
            'code', 'codeop', 'pty', 'tty',
        })

        assert RestrictedImporter.BLOCKED_MODULES == expected_blocked
        assert isinstance(RestrictedImporter.BLOCKED_MODULES, frozenset)

    def test_allowed_modules_frozenset_matches_specification(self):
        """Test that ALLOWED_MODULES frozenset matches specification exactly."""
        expected_allowed = frozenset({
            'math', 'random', 'string', 'collections', 'itertools',
            'functools', 'operator', 'typing', 're', 'json',
            'datetime', 'decimal', 'fractions', 'statistics',
            'dataclasses', 'enum', 'copy', 'heapq', 'bisect',
            'typing_extensions', 'abc',
        })

        assert RestrictedImporter.ALLOWED_MODULES == expected_allowed
        assert isinstance(RestrictedImporter.ALLOWED_MODULES, frozenset)

    def test_install_adds_to_meta_path_at_position_0(self):
        """Test that install() adds the importer at position 0 in sys.meta_path."""
        # Remove any existing instances
        RestrictedImporter.uninstall()

        # Get initial count
        initial_count = len([f for f in sys.meta_path if isinstance(f, RestrictedImporter)])

        # Install
        RestrictedImporter.install()

        # Check it's at position 0
        assert isinstance(sys.meta_path[0], RestrictedImporter)
        assert len([f for f in sys.meta_path if isinstance(f, RestrictedImporter)]) == initial_count + 1

    def test_uninstall_removes_importer(self):
        """Test that uninstall() removes the importer from sys.meta_path."""
        # Ensure it's installed first
        RestrictedImporter.install()

        # Uninstall
        RestrictedImporter.uninstall()

        # Check it's removed
        assert not any(isinstance(f, RestrictedImporter) for f in sys.meta_path)

    def test_find_module_returns_self_for_blocked_modules(self):
        """Test that find_module returns self for blocked modules."""
        importer = RestrictedImporter()

        for blocked_module in RestrictedImporter.BLOCKED_MODULES:
            result = importer.find_module(blocked_module)
            assert result is importer

        # Test submodules
        result = importer.find_module('os.path')
        assert result is importer

        result = importer.find_module('subprocess.Popen')
        assert result is importer

    def test_find_module_returns_none_for_allowed_modules(self):
        """Test that find_module returns None for allowed modules."""
        importer = RestrictedImporter()

        for allowed_module in RestrictedImporter.ALLOWED_MODULES:
            result = importer.find_module(allowed_module)
            assert result is None

    def test_find_module_returns_none_for_unlisted_modules(self):
        """Test that find_module returns None for modules not in either list."""
        importer = RestrictedImporter()

        # Test some common modules not in either list
        unlisted_modules = ['logging', 'unittest', 'json']  # json is in allowed, testing error case

        for module in unlisted_modules:
            if module not in RestrictedImporter.BLOCKED_MODULES and module not in RestrictedImporter.ALLOWED_MODULES:
                result = importer.find_module(module)
                assert result is None

    def test_load_module_raises_importerror_with_correct_message(self):
        """Test that load_module raises ImportError with correct message."""
        importer = RestrictedImporter()

        test_modules = ['os', 'sys', 'subprocess']

        for module_name in test_modules:
            with pytest.raises(ImportError, match=f"Import of '{module_name}' is blocked in symbolic execution sandbox"):
                importer.load_module(module_name)

    def test_import_blocks_blocked_modules(self):
        """Test that actual import statements raise ImportError for blocked modules."""
        # Install the importer
        RestrictedImporter.install()

        try:
            # Test importing blocked modules
            for blocked_module in ['os', 'sys', 'subprocess']:
                with pytest.raises(ImportError, match=f"Import of '{blocked_module}' is blocked in symbolic execution sandbox"):
                    __import__(blocked_module)
        finally:
            # Clean up
            RestrictedImporter.uninstall()

    def test_import_allows_allowed_modules(self):
        """Test that allowed modules can be imported successfully."""
        # Install the importer
        RestrictedImporter.install()

        try:
            # Test importing allowed modules
            for allowed_module in ['math', 'random', 'string']:
                try:
                    __import__(allowed_module)
                    assert allowed_module in sys.modules
                except ImportError:
                    pytest.fail(f"Allowed module '{allowed_module}' was blocked")
        finally:
            # Clean up
            RestrictedImporter.uninstall()

    def test_class_docstring_matches_specification(self):
        """Test that the class docstring matches the specification."""
        expected_docstring = """
        Controls what modules can be imported during symbolic execution.
        Installs as a meta path finder.
        """

        assert RestrictedImporter.__doc__ == expected_docstring

    def test_class_has_no_additional_attributes(self):
        """Test that class only has the expected class attributes."""
        expected_attributes = {'BLOCKED_MODULES', 'ALLOWED_MODULES', '__doc__', '__module__'}

        # Get all class attributes (excluding methods and special attributes)
        actual_attributes = set()
        for name in dir(RestrictedImporter):
            if not name.startswith('_') or name in ['__doc__', '__module__']:
                if not callable(getattr(RestrictedImporter, name)):
                    actual_attributes.add(name)

        # Should only have the expected attributes
        assert actual_attributes == expected_attributes

    def test_class_has_expected_methods(self):
        """Test that class has exactly the expected methods."""
        expected_methods = {'install', 'uninstall', 'find_module', 'load_module'}

        # Get all instance methods
        actual_methods = set()
        for name in dir(RestrictedImporter):
            if callable(getattr(RestrictedImporter, name)) and not name.startswith('_'):
                actual_methods.add(name)

        assert actual_methods == expected_methods

    def test_install_and_uninstall_are_classmethods(self):
        """Test that install and uninstall are class methods."""
        assert isinstance(RestrictedImporter.__dict__['install'], classmethod)
        assert isinstance(RestrictedImporter.__dict__['uninstall'], classmethod)

    def test_install_uninstall_idempotency(self):
        """Test that install and uninstall can be called multiple times safely."""
        # Multiple installs should not create duplicates
        RestrictedImporter.uninstall()  # Clean start

        RestrictedImporter.install()
        count_after_first = len([f for f in sys.meta_path if isinstance(f, RestrictedImporter)])

        RestrictedImporter.install()  # Second install
        count_after_second = len([f for f in sys.meta_path if isinstance(f, RestrictedImporter)])

        assert count_after_first == count_after_second == 1

        # Multiple uninstalls should not raise errors
        RestrictedImporter.uninstall()
        RestrictedImporter.uninstall()  # Second uninstall should not error

        assert not any(isinstance(f, RestrictedImporter) for f in sys.meta_path)


@pytest.fixture
def clean_meta_path():
    """Fixture to ensure clean meta_path before and after tests."""
    # Store original state
    original_meta_path = sys.meta_path.copy()

    # Clean up any existing RestrictedImporter instances
    if RestrictedImporter:
        RestrictedImporter.uninstall()

    yield

    # Restore original state
    sys.meta_path = original_meta_path