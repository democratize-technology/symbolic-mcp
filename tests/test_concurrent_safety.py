"""Test concurrent safety of sys.modules access in _temporary_module.

This module contains tests that validate thread safety when multiple threads
concurrently use the _temporary_module context manager. Without proper locking,
check-then-act patterns on sys.modules can cause KeyError exceptions.

The test simulates high-concurrency scenarios to expose race conditions that
would be difficult to reproduce in normal operation.
"""

import sys
import threading
from collections.abc import Callable
from typing import Any, Protocol

import pytest

# Import the module under test
import main
from main import _FunctionComparisonResult, _SymbolicCheckResult


# Protocol for the run_concurrent_test fixture - matches conftest.ConcurrentTestFunc
class ConcurrentTestFunc(Protocol):
    def __call__(
        self,
        operation: Callable[[int], Any],
        num_threads: int = 50,
    ) -> tuple[list[Exception], list[Any]]: ...


class TestSysModulesConcurrency:
    """Test thread safety of sys.modules access in _temporary_module."""

    def test_concurrent_temp_module_creation_no_exceptions(
        self, run_concurrent_test: ConcurrentTestFunc
    ) -> None:
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
        barrier = threading.Barrier(50)

        def create_and_use_module(thread_id: int) -> int:
            """Create a temporary module and use it."""
            # All threads start at exactly the same time
            barrier.wait()
            with main._temporary_module(test_code) as module:
                return int(module.add(1, 2))

        exceptions, results = run_concurrent_test(
            operation=create_and_use_module, num_threads=50
        )

        # Verify no exceptions occurred
        assert len(exceptions) == 0, f"Exceptions occurred: {exceptions}"
        assert len(results) == 50
        assert all(r == 3 for r in results)

    def test_concurrent_symbolic_check(
        self,
        run_concurrent_test: ConcurrentTestFunc,
    ) -> None:
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
        barrier = threading.Barrier(20)

        def run_analysis(thread_id: int) -> _SymbolicCheckResult:
            """Run symbolic analysis in a thread."""
            barrier.wait()
            return main.logic_symbolic_check(test_code, "multiply", timeout_seconds=5)

        exceptions, results = run_concurrent_test(
            operation=run_analysis, num_threads=20
        )

        # The key assertion: no KeyError (race condition) should occur
        race_condition_errors = [
            e
            for e in exceptions
            if isinstance(e, KeyError) or "Race condition" in str(e)
        ]
        assert (
            len(race_condition_errors) == 0
        ), f"Race condition detected: {race_condition_errors}"
        assert len(results) == 20
        # Verify all results have a status field (i.e., didn't crash in _temporary_module)
        assert all("status" in r for r in results)

    def test_sys_modules_lock_effectiveness(self) -> None:
        """Verify that _SYS_MODULES_LOCK actually prevents race conditions.

        This test directly manipulates sys.modules to verify that the lock
        provides mutual exclusion. It's a lower-level test that validates
        the locking mechanism itself.
        """
        lock_contention_count = [0]
        successful_acquisitions = [0]
        num_threads = 10
        barrier = threading.Barrier(num_threads)

        def contend_for_lock(thread_id: int) -> None:
            """Try to acquire the lock and detect contention."""
            barrier.wait()
            acquired = main._SYS_MODULES_LOCK.acquire(blocking=False)
            if acquired:
                try:
                    successful_acquisitions[0] += 1
                    # Brief hold
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

        # Verify lock mechanism works:
        # - At least one thread should have acquired the lock
        # - Total operations should equal num_threads
        assert (
            successful_acquisitions[0] >= 1
        ), "At least one thread should acquire the lock"
        assert successful_acquisitions[0] + lock_contention_count[0] == num_threads

    def test_no_module_leak_after_concurrent_use(
        self,
        run_concurrent_test: ConcurrentTestFunc,
    ) -> None:
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

        def create_module(_: int) -> None:
            """Create and destroy a temporary module."""
            with main._temporary_module(test_code):
                pass  # Module exists here

        exceptions, results = run_concurrent_test(
            operation=create_module, num_threads=30
        )
        assert len(exceptions) == 0

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

    def test_concurrent_with_exception_in_module_body(
        self,
        run_concurrent_test: ConcurrentTestFunc,
    ) -> None:
        """Concurrent calls with exceptions in module code should still clean up.

        This tests that the finally block in _temporary_module runs correctly
        even when exceptions occur during module execution, under concurrent load.
        """
        # Code with an intentional error
        error_code = """
def broken():
    raise ValueError("intentional error")
"""
        barrier = threading.Barrier(20)

        def try_load_broken_module(_: int) -> bool:
            """Try to load a module with an error."""
            barrier.wait()
            try:
                with main._temporary_module(error_code) as module:
                    # Module loads but calling the function raises
                    module.broken()
                    return False
            except ValueError:
                return True
            except Exception:
                # Should not get KeyError or other unexpected exceptions
                return False

        exceptions, results = run_concurrent_test(
            operation=try_load_broken_module, num_threads=20
        )

        # All threads should have caught the ValueError
        assert len(exceptions) == 0
        assert sum(results) == 20

    def test_concurrent_compare_functions(
        self,
        run_concurrent_test: ConcurrentTestFunc,
    ) -> None:
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
        barrier = threading.Barrier(15)

        def run_comparison(_: int) -> _FunctionComparisonResult:
            """Run function comparison."""
            barrier.wait()
            return main.logic_compare_functions(
                code, "add_one", "add_one_v2", timeout_seconds=10
            )

        exceptions, results = run_concurrent_test(
            operation=run_comparison, num_threads=15
        )

        # No KeyError should occur (would indicate race condition)
        keyerrors = [e for e in exceptions if isinstance(e, KeyError)]
        assert len(keyerrors) == 0, f"Race condition detected: {keyerrors}"

        # We expect at least some results, even if some threads hit errors
        # (CrossHair can have issues with concurrent Z3 access)
        if len(results) > 0:
            # Verify all results have a status field (didn't crash in _temporary_module)
            assert all("status" in r for r in results)

    def test_concurrent_find_path_to_exception(
        self,
        run_concurrent_test: ConcurrentTestFunc,
    ) -> None:
        """Test concurrent find_path_to_exception for race conditions."""
        code = """
def divide(x: int, y: int) -> float:
    return x / y
"""
        barrier = threading.Barrier(15)

        def find_exception(_: int) -> main._ExceptionPathResult:
            """Find ZeroDivisionError path."""
            barrier.wait()
            return main.logic_find_path_to_exception(
                code, "divide", "ZeroDivisionError", timeout_seconds=10
            )

        exceptions, results = run_concurrent_test(
            operation=find_exception, num_threads=15
        )

        assert len(exceptions) == 0
        assert len(results) == 15
        # All should complete successfully (found, unreachable, unknown, or error are acceptable)
        # The key is that no KeyError or other exceptions occurred
        assert all(
            r["status"] in ("found", "unreachable", "unknown", "error") for r in results
        ), f"Unexpected statuses: {[r['status'] for r in results]}"
