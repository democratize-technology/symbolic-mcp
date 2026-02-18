"""Shared type definitions for test fixtures.

This module contains Protocol and TypeVar definitions used across test files.
Centralizing these definitions prevents duplication and F401/F811 linting issues.
"""

from collections.abc import Callable
from typing import Protocol, TypeVar

# TypeVar for the result type of concurrent test operations
T = TypeVar("T")


class ConcurrentTestFunc(Protocol):
    """Protocol for the concurrent test runner function.

    This protocol defines the interface for the run_concurrent_test fixture
    that executes operations across multiple threads to test for race conditions.

    Usage:
        def test_something(run_concurrent_test: ConcurrentTestFunc) -> None:
            def worker(thread_id: int) -> int:
                return thread_id * 2

            exceptions, results = run_concurrent_test(operation=worker, num_threads=50)
            assert len(exceptions) == 0
    """

    def __call__(
        self,
        operation: Callable[[int], T],
        num_threads: int = 50,
    ) -> tuple[list[Exception], list[T]]: ...
