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
Simple test for the security fixes without importing full main module
"""

import sys
import os
import threading
import time
import concurrent.futures

# Import just the RestrictedImporter class by exec-ing the file
with open('main.py', 'r') as f:
    content = f.read()

# Create a sandbox to execute just the RestrictedImporter class
restricted_globals = {}
exec(content, restricted_globals)
RestrictedImporter = restricted_globals['RestrictedImporter']

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
    print("Testing security fixes...")

    test1 = test_recursion_fix()
    test2 = test_thread_safety()
    test3 = test_reference_counting()

    if test1 and test2 and test3:
        print("\n🎉 ALL TESTS PASSED - SECURITY FIXES ARE WORKING!")
        exit(0)
    else:
        print("\n❌ SOME TESTS FAILED")
        exit(1)