"""
Shared pytest configuration and fixtures for all tests.
"""

import os
import sys
from collections.abc import Callable
from typing import Any, Generator, Protocol

import pytest
from _pytest.config import Config


# Type alias for the run_concurrent_test fixture return value
class ConcurrentTestFunc(Protocol):
    """Protocol for the concurrent test runner function."""

    def __call__(
        self,
        operation: Callable[[int], Any],
        num_threads: int = 50,
    ) -> tuple[list[Exception], list[Any]]: ...


# Test constants
CONCURRENT_TEST_THREAD_COUNT = 50  # Enough to expose race conditions
QUICK_ANALYSIS_TIMEOUT = 5
STANDARD_ANALYSIS_TIMEOUT = 10


def pytest_configure(config: Config) -> None:
    """Clear SYMBOLIC_* environment variables before pytest imports any test modules.

    This hook runs before test collection and imports, ensuring that the main module
    is imported with default configuration values rather than values from the
    environment that may have been set by other processes.

    This is critical because configuration variables like MEMORY_LIMIT_MB,
    CODE_SIZE_LIMIT, and COVERAGE_EXHAUSTIVE_THRESHOLD are read at import time,
    not at runtime.
    """
    for key in list(os.environ.keys()):
        if key.startswith("SYMBOLIC_"):
            del os.environ[key]

    # Register custom test markers
    config.addinivalue_line(
        "markers", "integration: Tests using real CrossHair symbolic execution"
    )
    config.addinivalue_line("markers", "mocked: Tests using CrossHair mocks")


@pytest.fixture(autouse=True)
def clean_symbolic_env_per_test() -> Generator[None, None, None]:
    """Clear SYMBOLIC_* environment variables before each test.

    This prevents tests from polluting each other's environment.
    """
    # Clear before test
    keys_to_clear = [k for k in os.environ if k.startswith("SYMBOLIC_")]
    for key in keys_to_clear:
        del os.environ[key]
    yield
    # Clear after test
    keys_to_clear = [k for k in os.environ if k.startswith("SYMBOLIC_")]
    for key in keys_to_clear:
        del os.environ[key]


@pytest.fixture(autouse=True)
def clean_sys_modules_snapshot() -> Generator[None, None, None]:
    """Snapshot and restore sys.modules to prevent test pollution.

    This fixture removes any mcp_temp_* modules that tests may have added
    to sys.modules, ensuring tests don't pollute each other.
    """
    snapshot = dict(sys.modules)
    yield
    # Clean up any mcp_temp modules added during the test
    current = set(sys.modules.keys())
    original = set(snapshot.keys())
    for module_name in current - original:
        if module_name.startswith("mcp_temp_"):
            del sys.modules[module_name]


@pytest.fixture
def run_concurrent_test() -> ConcurrentTestFunc:
    """Fixture providing standardized concurrent test execution.

    Returns:
        A function that runs an operation concurrently across multiple threads
        and returns any exceptions and results.

    Usage:
        def test_something(run_concurrent_test):
            def worker(thread_id):
                # do work
                return result

            exceptions, results = run_concurrent_test(
                operation=worker,
                num_threads=50
            )
            assert len(exceptions) == 0
    """
    from concurrent.futures import ThreadPoolExecutor, wait

    def _run(
        operation: Callable[[int], Any],
        num_threads: int = CONCURRENT_TEST_THREAD_COUNT,
    ) -> tuple[list[Exception], list[Any]]:
        exceptions: list[Exception] = []
        results: list[Any] = []

        def worker(thread_id: int) -> None:
            try:
                results.append(operation(thread_id))
            except Exception as e:
                exceptions.append(e)

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(worker, i) for i in range(num_threads)]
            wait(futures)

        return exceptions, results

    return _run
