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
import threading

# Import the isolated RestrictedImporter
exec(open('test_restricted_importer_isolated.py').read())

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
    assert RestrictedImporter._original_import is None  # Should be None initially
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
        print("=" * 60)
        sys.exit(1)