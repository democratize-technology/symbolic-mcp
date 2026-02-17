"""
Shared pytest configuration and fixtures for all tests.
"""

import os
from typing import Generator

import pytest
from _pytest.config import Config


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
