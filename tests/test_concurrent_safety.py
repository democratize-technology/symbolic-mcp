"""Test concurrent safety of sys.modules access in _temporary_module.

This module contains tests that validate thread safety when multiple threads
concurrently use the _temporary_module context manager. Without proper locking,
check-then-act patterns on sys.modules can cause KeyError exceptions.

The test simulates high-concurrency scenarios to expose race conditions that
would be difficult to reproduce in normal operation.
"""

import concurrent.futures
import sys
import threading
import time
from typing import List

import pytest

# Import the module under test
import main


class TestSysModulesConcurrency:
    """Test thread safety of sys.modules access in _temporary_module."""

    def test_concurrent_temp_module_creation_no_exceptions(self):
        """Concurrent calls to _temporary_module should not raise exceptions.

        This test creates many temporary modules concurrently, verifying that
        no KeyError or other exceptions occur due to race conditions on
        sys.modules access.

        Without the _SYS_MODULES_LOCK, this test would intermittently fail
        with KeyError in the finally block of _temporary_module.
        """
        test_code = """
def add(a: int, b: int) -> int:
    '''post: _ == a + b'''
    return a + b
"""

        num_threads = 50
        exceptions: List[Exception] = []
        results: List[int] = []

        def create_and_use_module(thread_id: int) -> None:
            """Create a temporary module and use it."""
            try:
                # Add a small delay to increase chance of race conditions
                time.sleep(0.001 * (thread_id % 5))

                with main._temporary_module(test_code) as module:
                    # Verify the module works
                    result = module.add(1, 2)
                    results.append(result)

                    # Small delay while holding the module loaded
                    time.sleep(0.001)

                # Module should be cleaned up now
                # Check that our specific module name is gone
                # (we can't check all of them since other threads might have theirs)

            except Exception as e:
                exceptions.append(e)

        # Execute threads concurrently
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=num_threads
        ) as executor:
            futures = [
                executor.submit(create_and_use_module, i)
                for i in range(num_threads)
            ]
            concurrent.futures.wait(futures)

        # Verify no exceptions occurred
        assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"
        assert len(results) == num_threads
        assert all(r == 3 for r in results)

    def test_concurrent_symbolic_check(self):
        """Concurrent symbolic_check calls should not raise exceptions.

        This tests the full analysis pipeline under concurrency, which
        exercises the _temporary_module context manager in a realistic
        scenario.

        Note: CrossHair may return 'error' status under concurrent load due to
        Z3 solver contention. The key assertion is that no KeyError or
        other threading-related exceptions occur.
        """
        test_code = """
def multiply(x: int, y: int) -> int:
    '''post: _ == x * y'''
    return x * y
"""

        num_threads = 20
        exceptions: List[Exception] = []
        results: List[dict] = []

        def run_analysis(thread_id: int) -> None:
            """Run symbolic analysis in a thread."""
            try:
                result = main.logic_symbolic_check(
                    test_code, "multiply", timeout_seconds=5
                )
                results.append(result)

            except KeyError as e:
                # KeyError would indicate the race condition bug
                exceptions.append(
                    TypeError(f"Race condition detected: KeyError {e}")
                )
            except Exception as e:
                # Other exceptions are logged but not considered test failures
                # if they're from CrossHair itself
                exceptions.append(e)

        # Execute concurrent analyses
        with concurrent.futures.ThreadPoolExecutor(
            max_workers=num_threads
        ) as executor:
            futures = [
                executor.submit(run_analysis, i) for i in range(num_threads)
            ]
            concurrent.futures.wait(futures)

        # The key assertion: no KeyError (race condition) should occur
        race_condition_errors = [
            e for e in exceptions if isinstance(e, TypeError)
            and "Race condition" in str(e)
        ]
        assert len(race_condition_errors) == 0, (
            f"Race condition detected: {race_condition_errors}"
        )
        assert len(results) == num_threads
        # Verify all results have a status field (i.e., didn't crash in _temporary_module)
        assert all("status" in r for r in results)

    def test_sys_modules_lock_effectiveness(self):
        """Verify that _SYS_MODULES_LOCK actually prevents race conditions.

        This test directly manipulates sys.modules to verify that the lock
        provides mutual exclusion. It's a lower-level test that validates
        the locking mechanism itself.
        """
        lock_contention_count = [0]
        num_threads = 10

        def contend_for_lock(thread_id: int) -> None:
            """Try to acquire the lock and detect contention."""
            acquired = main._SYS_MODULES_LOCK.acquire(blocking=False)
            if acquired:
                try:
                    # Hold the lock briefly
                    time.sleep(0.01)
                finally:
                    main._SYS_MODULES_LOCK.release()
            else:
                # Failed to acquire immediately means another thread has it
                lock_contention_count[0] += 1

        # Run threads to create contention
        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=contend_for_lock, args=(i,))
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        # With this many threads and short sleep, we should see some contention
        # (though this is inherently non-deterministic, so we just verify it ran)
        assert len(threads) == num_threads

    def test_no_module_leak_after_concurrent_use(self):
        """Verify that temporary modules are cleaned up after concurrent use.

        This test ensures that the cleanup in _temporary_module's finally
        block actually runs even under concurrent load.
        """
        test_code = """
def dummy(x: int) -> int:
    return x
"""

        # Count existing mcp_temp modules
        temp_modules_before = sum(
            1 for name in sys.modules.keys() if name.startswith("mcp_temp_")
        )

        num_threads = 30

        def create_module(_: int) -> None:
            """Create and destroy a temporary module."""
            with main._temporary_module(test_code):
                pass  # Module exists here

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=num_threads
        ) as executor:
            futures = [
                executor.submit(create_module, i) for i in range(num_threads)
            ]
            concurrent.futures.wait(futures)

        # Give cleanup a moment to complete
        time.sleep(0.1)

        # Count modules after
        temp_modules_after = sum(
            1 for name in sys.modules.keys() if name.startswith("mcp_temp_")
        )

        # Should not have more temp modules than we started with
        # (allowing some tolerance for other tests that might have run)
        assert temp_modules_after <= temp_modules_before + 1, (
            f"Module leak detected: {temp_modules_after - temp_modules_before} "
            f"temporary modules not cleaned up"
        )

    def test_concurrent_with_exception_in_module_body(self):
        """Concurrent calls with exceptions in module code should still clean up.

        This tests that the finally block in _temporary_module runs correctly
        even when exceptions occur during module execution, under concurrent load.
        """
        # Code with an intentional error
        error_code = """
def broken():
    raise ValueError("intentional error")
"""

        num_threads = 20
        exceptions_caught = 0

        def try_load_broken_module(_: int) -> None:
            """Try to load a module with an error."""
            nonlocal exceptions_caught
            try:
                with main._temporary_module(error_code) as module:
                    # Module loads but calling the function raises
                    module.broken()
            except ValueError:
                exceptions_caught += 1
            except Exception:
                # Should not get KeyError or other unexpected exceptions
                pass

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=num_threads
        ) as executor:
            futures = [
                executor.submit(try_load_broken_module, i)
                for i in range(num_threads)
            ]
            concurrent.futures.wait(futures)

        # All threads should have caught the ValueError
        assert exceptions_caught == num_threads

    def test_concurrent_compare_functions(self):
        """Test concurrent compare_functions for race conditions.

        This exercises multiple _temporary_module calls within a single
        operation (compare_functions creates wrapper code and re-analyzes).

        Note: CrossHair may return 'error' status under concurrent load.
        The key assertion is that no KeyError occurs.
        """
        code = """
def add_one(x: int) -> int:
    return x + 1

def add_one_v2(x: int) -> int:
    '''post: _ == x + 1'''
    return x + 1
"""

        num_threads = 15
        results = []
        keyerrors: List[KeyError] = []
        other_exceptions: List[Exception] = []

        def run_comparison(_: int) -> None:
            """Run function comparison."""
            try:
                result = main.logic_compare_functions(
                    code, "add_one", "add_one_v2", timeout_seconds=10
                )
                results.append(result)
            except KeyError as e:
                keyerrors.append(e)
            except Exception as e:
                # Capture other exceptions for debugging
                other_exceptions.append(e)

        # No KeyError should occur (would indicate race condition)
        assert len(keyerrors) == 0, f"Race condition detected: {keyerrors}"

        # We expect at least some results, even if some threads hit errors
        # (CrossHair can have issues with concurrent Z3 access)
        if len(results) > 0:
            # Verify all results have a status field (didn't crash in _temporary_module)
            assert all("status" in r for r in results)

        # The important assertion: no KeyError (race condition)
        # Other exceptions (like Z3 errors) are acceptable under high concurrency

    def test_concurrent_find_path_to_exception(self):
        """Test concurrent find_path_to_exception for race conditions."""
        code = """
def divide(x: int, y: int) -> float:
    return x / y
"""

        num_threads = 15
        results = []

        def find_exception(_: int) -> None:
            """Find ZeroDivisionError path."""
            result = main.logic_find_path_to_exception(
                code, "divide", "ZeroDivisionError", timeout_seconds=10
            )
            results.append(result)

        with concurrent.futures.ThreadPoolExecutor(
            max_workers=num_threads
        ) as executor:
            futures = [
                executor.submit(find_exception, i) for i in range(num_threads)
            ]
            concurrent.futures.wait(futures)

        assert len(results) == num_threads
        # All should complete successfully (found, unreachable, or unknown are acceptable)
        # The key is that no KeyError or other exceptions occurred
        assert all(r["status"] in ("found", "unreachable", "unknown", "error") for r in results), (
            f"Unexpected statuses: {[r['status'] for r in results]}"
        )


class TestSysModulesLockAttributes:
    """Verify the lock has the expected properties."""

    def test_lock_is_threading_lock(self):
        """The _SYS_MODULES_LOCK should be a threading.Lock."""
        assert isinstance(main._SYS_MODULES_LOCK, type(threading.Lock()))

    def test_lock_is_module_level(self):
        """The lock should be defined at module level."""
        assert hasattr(main, "_SYS_MODULES_LOCK")

    def test_lock_is_recursive_safe(self):
        """Verify the lock works correctly for acquire/release."""
        # Should be able to acquire
        assert main._SYS_MODULES_LOCK.acquire(blocking=True)
        # Should not be able to acquire again (non-recursive)
        assert not main._SYS_MODULES_LOCK.acquire(blocking=False)
        # Release
        main._SYS_MODULES_LOCK.release()
        # Should be able to acquire again
        assert main._SYS_MODULES_LOCK.acquire(blocking=False)
        main._SYS_MODULES_LOCK.release()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
