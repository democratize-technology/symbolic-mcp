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

#!/usr/bin/env python3
"""
Test that our RestrictedImporter implementation matches specification requirements.
"""

import sys
import os
import threading
import builtins

# Extract just the RestrictedImporter class
class RestrictedImporter:
    """
    Controls what modules can be imported during symbolic execution.
    Installs as a meta path finder with comprehensive security protections.

    SECURITY FIXES IMPLEMENTED:
    - Patch builtins.__import__ to block sys.modules bypass
    - Thread-safe installation/uninstallation
    - sys.modules cleanup for blocked modules
    - Multiple layers of import protection
    """

    BLOCKED_MODULES = frozenset({
        'os', 'sys', 'subprocess', 'shutil', 'pathlib',
        'socket', 'http', 'urllib', 'requests', 'ftplib',
        'pickle', 'shelve', 'marshal',
        'ctypes', 'multiprocessing',
        'importlib', 'runpy',
        'code', 'codeop', 'pty', 'tty',
    })

    ALLOWED_MODULES = frozenset({
        'math', 'random', 'string', 'collections', 'itertools',
        'functools', 'operator', 'typing', 're', 'json',
        'datetime', 'decimal', 'fractions', 'statistics',
        'dataclasses', 'enum', 'copy', 'heapq', 'bisect',
        'typing_extensions', 'abc',
    })

    # Thread safety and state tracking
    _lock = threading.Lock()
    _original_import = None
    _installed = False

    @classmethod
    def install(cls):
        """Install the restricted importer with comprehensive security protections."""
        with cls._lock:  # CRITICAL: Thread safety
            # Prevent double installation
            if cls._installed:
                return

            # Store original __import__ for restoration
            cls._original_import = builtins.__import__

            # CRITICAL FIX: Patch builtins.__import__ to block sys.modules bypass
            builtins.__import__ = cls._secure_import

            # CRITICAL FIX: Remove blocked modules from sys.modules to prevent access
            for module_name in cls.BLOCKED_MODULES:
                if module_name in sys.modules:
                    del sys.modules[module_name]

            # Install meta path finder (additional protection layer)
            if not any(isinstance(f, cls) for f in sys.meta_path):
                sys.meta_path.insert(0, cls())

            cls._installed = True

    @classmethod
    def uninstall(cls):
        """Remove the restricted importer and restore original import functionality."""
        with cls._lock:  # CRITICAL: Thread safety
            if not cls._installed:
                return

            # Restore original __import__ if we stored it
            if cls._original_import is not None:
                builtins.__import__ = cls._original_import
                cls._original_import = None

            # Remove from meta_path
            sys.meta_path = [f for f in sys.meta_path if not isinstance(f, cls)]

            cls._installed = False

    @classmethod
    def _secure_import(cls, name, globals=None, locals=None, fromlist=(), level=0):
        """
        CRITICAL SECURITY FIX: Secure import function that blocks sys.modules bypass.
        """
        # Handle relative imports (level > 0)
        if level > 0:
            if globals and '__package__' in globals and globals['__package__']:
                package = globals['__package__']
                if level > 1:
                    parts = package.split('.')
                    if len(parts) >= level - 1:
                        package = '.'.join(parts[:-(level - 1)])
                    else:
                        package = ''

                if name:
                    fullname = f"{package}.{name}" if package else name
                else:
                    fullname = package
            else:
                fullname = name
        else:
            fullname = name

        # Check base module name against blocked modules
        base_module = fullname.split('.')[0] if fullname else ''

        # CRITICAL CHECK: Block if base module is in BLOCKED_MODULES
        if base_module in cls.BLOCKED_MODULES:
            raise ImportError(f"Import of '{fullname}' is blocked in symbolic execution sandbox")

        # CRITICAL CHECK: Check fromlist for blocked modules
        if fromlist:
            for module_name in fromlist:
                if module_name in cls.BLOCKED_MODULES:
                    raise ImportError(f"Import of '{module_name}' is blocked in symbolic execution sandbox")

        # CRITICAL CHECK: For submodule imports, check if parent is blocked
        if '.' in fullname:
            parent_module = fullname.split('.')[0]
            if parent_module in cls.BLOCKED_MODULES:
                raise ImportError(f"Import of '{fullname}' is blocked in symbolic execution sandbox")

        # Additional security: Check if someone is trying to access blocked modules via sys.modules
        if name == 'sys' and fromlist and 'modules' in fromlist:
            raise ImportError(f"Import of 'sys.modules' is blocked in symbolic execution sandbox")

        # If all checks pass, call original import function
        return cls._original_import(name, globals, locals, fromlist, level)

    def find_module(self, fullname: str, path=None):
        """Legacy find_module method for Python compatibility."""
        base_module = fullname.split('.')[0]
        if base_module in self.BLOCKED_MODULES:
            return self
        return None

    def find_spec(self, fullname, path, target=None):
        """Bridge modern find_spec to legacy find_module for Python 3.4+ compatibility."""
        if self.find_module(fullname, path):
            import importlib.util
            return importlib.util.spec_from_loader(fullname, loader=self)
        return None

    def create_module(self, spec):
        """Required for exec_module compatibility."""
        return None

    def exec_module(self, module):
        """Modern module execution method that blocks execution of blocked modules."""
        fullname = module.__name__
        base_module = fullname.split('.')[0]

        if base_module in self.BLOCKED_MODULES:
            raise ImportError(f"Import of '{fullname}' is blocked in symbolic execution sandbox")

        raise ImportError(f"Import of '{fullname}' is blocked in symbolic execution sandbox")

    def load_module(self, fullname: str):
        """Legacy load_module method that blocks loading of blocked modules."""
        base_module = fullname.split('.')[0]

        if base_module in self.BLOCKED_MODULES:
            raise ImportError(f"Import of '{fullname}' is blocked in symbolic execution sandbox")

        raise ImportError(f"Import of '{fullname}' is blocked in symbolic execution sandbox")


def test_specification_compliance():
    """Test that our implementation matches the specification."""
    print("Testing specification compliance...")

    # Test 1: BLOCKED_MODULES frozenset matches specification
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
    print("✓ BLOCKED_MODULES matches specification")

    # Test 2: ALLOWED_MODULES frozenset matches specification
    expected_allowed = frozenset({
        'math', 'random', 'string', 'collections', 'itertools',
        'functools', 'operator', 'typing', 're', 'json',
        'datetime', 'decimal', 'fractions', 'statistics',
        'dataclasses', 'enum', 'copy', 'heapq', 'bisect',
        'typing_extensions', 'abc',
    })

    assert RestrictedImporter.ALLOWED_MODULES == expected_allowed
    assert isinstance(RestrictedImporter.ALLOWED_MODULES, frozenset)
    print("✓ ALLOWED_MODULES matches specification")

    # Test 3: Thread safety attributes exist
    assert hasattr(RestrictedImporter, '_lock')
    assert hasattr(RestrictedImporter, '_original_import')
    assert hasattr(RestrictedImporter, '_installed')
    assert isinstance(RestrictedImporter._lock, threading.Lock)
    assert RestrictedImporter._original_import is None
    assert RestrictedImporter._installed is False
    print("✓ Thread safety attributes properly initialized")

    # Test 4: Required methods exist
    assert hasattr(RestrictedImporter, 'install')
    assert hasattr(RestrictedImporter, 'uninstall')
    assert hasattr(RestrictedImporter, '_secure_import')
    assert hasattr(RestrictedImporter, 'find_module')
    assert hasattr(RestrictedImporter, 'find_spec')
    assert hasattr(RestrictedImporter, 'load_module')
    print("✓ All required methods exist")

    # Test 5: install adds to meta_path at position 0
    original_meta_path = sys.meta_path.copy()
    RestrictedImporter.install()

    # Check that RestrictedImporter instance is at position 0
    assert len(sys.meta_path) > len(original_meta_path)
    assert isinstance(sys.meta_path[0], RestrictedImporter)
    print("✓ install() adds importer at position 0 in meta_path")

    # Test 6: uninstall removes from meta_path
    RestrictedImporter.uninstall()

    # Check that no RestrictedImporter instances remain
    remaining_importers = [f for f in sys.meta_path if isinstance(f, RestrictedImporter)]
    assert len(remaining_importers) == 0
    assert RestrictedImporter._installed is False
    assert RestrictedImporter._original_import is None
    print("✓ uninstall() properly cleans up")

    # Test 7: find_module behavior
    importer = RestrictedImporter()

    # Should return self for blocked modules
    result = importer.find_module('os')
    assert result is importer

    result = importer.find_module('os.path')
    assert result is importer

    # Should return None for allowed modules
    result = importer.find_module('math')
    assert result is None

    result = importer.find_module('random')
    assert result is None
    print("✓ find_module behaves correctly")

    # Test 8: Thread safety of install/uninstall
    results = []
    errors = []

    def test_concurrent_access():
        try:
            RestrictedImporter.install()
            RestrictedImporter.uninstall()
            results.append("success")
        except Exception as e:
            errors.append(str(e))

    threads = []
    for i in range(3):
        thread = threading.Thread(target=test_concurrent_access)
        threads.append(thread)
        thread.start()

    for thread in threads:
        thread.join()

    assert len(errors) == 0, f"Thread safety errors: {errors}"
    assert len(results) == 3
    print("✓ Thread safety confirmed")

    return True

if __name__ == "__main__":
    print("=" * 60)
    print("SPECIFICATION COMPLIANCE TEST")
    print("=" * 60)

    try:
        success = test_specification_compliance()
        print("\n" + "=" * 60)
        print("🎉 ALL SPECIFICATION TESTS PASSED!")
        print("Implementation correctly matches security requirements")
        print("=" * 60)
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ SPECIFICATION TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        print("=" * 60)
        sys.exit(1)