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
Test just the core RestrictedImporter without external dependencies
"""

import sys
import os
import threading
import time
import concurrent.futures
import importlib.util

# Define just the RestrictedImporter class with our fixes
class RestrictedImporter:
    """
    Secure importer that blocks access to dangerous modules and functions.

    SECURITY FIXES:
    1. Thread-safe installation with lock and reference counting
    2. Patch builtins.__import__ to block sys.modules bypass
    3. Remove blocked modules from sys.modules
    4. Fix recursion bug in find_spec method
    """

    BLOCKED_MODULES = frozenset({
        'os', 'sys', 'subprocess', 'shutil', 'pathlib',
        'socket', 'http', 'urllib', 'requests', 'ftplib',
        'pickle', 'shelve', 'marshal',
        'ctypes', 'multiprocessing',
        'importlib', 'runpy',
        'code', 'codeop', 'pty', 'tty',
    })

    # Thread safety and state tracking
    _lock = threading.Lock()
    _original_import = None
    _installed = False
    _install_count = 0  # Reference counting for nested installs

    @classmethod
    def install(cls):
        """
        Install the restricted importer with comprehensive security protections.

        SECURITY FIXES:
        1. Thread-safe installation with lock
        2. Patch builtins.__import__ to block sys.modules bypass
        3. Remove blocked modules from sys.modules
        4. Install meta path finder
        """
        import builtins

        with cls._lock:  # CRITICAL: Thread safety
            # Reference counting for nested installs
            cls._install_count += 1
            if cls._installed:
                return  # Already installed, just increment count

            # Store original __import__ for restoration
            cls._original_import = builtins.__import__

            # CRITICAL FIX: Patch builtins.__import__ to block sys.modules bypass
            builtins.__import__ = cls._secure_import

            # CRITICAL FIX: Remove blocked modules from sys.modules to prevent access
            # Create a snapshot first to avoid race conditions during iteration
            modules_to_remove = [
                module_name for module_name in cls.BLOCKED_MODULES
                if module_name in sys.modules
            ]
            for module_name in modules_to_remove:
                del sys.modules[module_name]

            # Install meta path finder (additional protection layer)
            # Use atomic check-and-insert to avoid race conditions
            meta_path_instance = cls()
            if not any(isinstance(f, cls) for f in sys.meta_path):
                sys.meta_path.insert(0, meta_path_instance)

            cls._installed = True

    @classmethod
    def uninstall(cls):
        """
        Remove the restricted importer and restore original import functionality.

        SECURITY FIXES:
        1. Thread-safe uninstallation with lock
        2. Restore original __import__
        3. Remove from meta_path
        4. Reset installation state
        """
        import builtins

        with cls._lock:  # CRITICAL: Thread safety
            if cls._install_count == 0:
                return  # Not installed

            # Reference counting for nested uninstalls
            cls._install_count -= 1
            if cls._install_count > 0:
                return  # Still other active installations

            # Restore original __import__ if we stored it
            if cls._original_import is not None:
                builtins.__import__ = cls._original_import
                cls._original_import = None

            # Remove from meta_path - use list comprehension for atomic operation
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

        # Additional security: Check if someone is trying to access blocked modules via sys.modules
        if name == 'sys' and fromlist and 'modules' in fromlist:
            raise ImportError(f"Import of 'sys.modules' is blocked in symbolic execution sandbox")

        # If all checks pass, call original import function
        return cls._original_import(name, globals, locals, fromlist, level)

    def find_module(self, fullname: str, path=None):
        """Legacy find_module method for Python compatibility."""
        base_module = fullname.split('.')[0]
        if base_module in self.BLOCKED_MODULES:
            return self  # Return self to handle the import (and block it)
        return None  # Let normal import proceed

    def find_spec(self, fullname, path, target=None):
        """Bridge modern find_spec to legacy find_module for Python 3.4+ compatibility."""
        if self.find_module(fullname, path):
            # Note: importlib.util is already imported at module level (line 20)
            # This avoids recursion since importlib is BLOCKED
            return importlib.util.spec_from_loader(fullname, loader=self)
        return None

    def create_module(self, spec):
        """Required for exec_module compatibility."""
        return None  # Use default module creation

    def exec_module(self, module):
        """Modern module execution method that blocks execution of blocked modules."""
        base_module = module.__name__.split('.')[0]
        if base_module in self.BLOCKED_MODULES:
            raise ImportError(f"Execution of '{module.__name__}' is blocked in symbolic execution sandbox")


def test_recursion_fix():
    """Test that the recursion bug is fixed"""
    print("=== Testing Recursion Bug Fix ===")

    try:
        RestrictedImporter.install()

        # This should not cause infinite recursion
        try:
            import os.path
            print("❌ FAILED: os.path import should have been blocked")
            return False
        except ImportError as e:
            print("✅ SUCCESS: os.path import blocked correctly")
        except RecursionError as e:
            print("❌ FAILED: Recursion bug still exists")
            return False
        finally:
            RestrictedImporter.uninstall()

    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False

    return True

def test_thread_safety():
    """Test thread safety with reference counting"""
    print("\n=== Testing Thread Safety with Reference Counting ===")

    def install_and_test(thread_id):
        """Function to run in threads"""
        try:
            RestrictedImporter.install()
            time.sleep(0.1)  # Simulate some work

            # Test that it's working
            try:
                import os
                return f"Thread {thread_id}: FAILED - os import allowed"
            except ImportError:
                return f"Thread {thread_id}: SUCCESS - os import blocked"
        except Exception as e:
            return f"Thread {thread_id}: ERROR - {e}"
        finally:
            RestrictedImporter.uninstall()

    # Run multiple threads concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(install_and_test, i) for i in range(10)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    success_count = sum(1 for result in results if "SUCCESS" in result)
    print(f"Thread safety test: {success_count}/10 threads successful")

    if success_count == 10:
        print("✅ PASS: Thread safety test passed")
        return True
    else:
        print("❌ FAILED: Thread safety test failed")
        print("Results:", results)
        return False

def test_reference_counting():
    """Test that reference counting works correctly"""
    print("\n=== Testing Reference Counting ===")

    try:
        # Install twice
        RestrictedImporter.install()
        RestrictedImporter.install()

        # Should still work
        try:
            import os
            print("❌ FAILED: os import should have been blocked after double install")
            return False
        except ImportError:
            print("✅ SUCCESS: os import blocked after double install")
        finally:
            # Uninstall once, should still be blocked
            RestrictedImporter.uninstall()

        try:
            import os
            print("❌ FAILED: os import should still be blocked after one uninstall")
            return False
        except ImportError:
            print("✅ SUCCESS: os import still blocked after one uninstall")
        finally:
            # Uninstall second time, should be unblocked
            RestrictedImporter.uninstall()

        # Now should work
        try:
            import os
            print("✅ SUCCESS: os import works after full uninstall")
            return True
        except ImportError:
            print("❌ FAILED: os import should work after full uninstall")
            return False

    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False

if __name__ == "__main__":
    print("Testing core security fixes...")

    test1 = test_recursion_fix()
    test2 = test_thread_safety()
    test3 = test_reference_counting()

    if test1 and test2 and test3:
        print("\n🎉 ALL TESTS PASSED - SECURITY FIXES ARE WORKING!")
        exit(0)
    else:
        print("\n❌ SOME TESTS FAILED")
        exit(1)