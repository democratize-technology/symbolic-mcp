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
Pytest configuration for integration tests

This file provides pytest configuration, markers, and shared fixtures
for the comprehensive integration test suite.
"""

import asyncio
import os
import shutil
import sys
import tempfile
from typing import Any, Dict, Generator

import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "integration: Mark test as integration test")
    config.addinivalue_line("markers", "load: Mark test as load/performance test")
    config.addinivalue_line("markers", "security: Mark test as security test")
    config.addinivalue_line("markers", "memory: Mark test as memory leak test")
    config.addinivalue_line(
        "markers", "resilience: Mark test as resilience/failure test"
    )
    config.addinivalue_line(
        "markers",
        "failing: Mark test as expected to fail (demonstrates current issues)",
    )
    config.addinivalue_line(
        "markers", "slow: Mark test as slow running (takes > 30 seconds)"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers and handle slow tests"""
    # Add integration marker to all tests in this directory
    for item in items:
        if "tests/integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)

        # Mark async tests appropriately
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)


@pytest.fixture(scope="session")
def temp_project_dir() -> Generator[str, None, None]:
    """Create a temporary project directory for testing"""
    temp_dir = tempfile.mkdtemp(prefix="symbolic_mcp_test_")

    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture(scope="session")
def test_code_samples() -> Dict[str, str]:
    """Provide common code samples for testing"""
    return {
        "simple_function": """
def simple_function(x: int) -> int:
    return x + 1
""",
        "conditional_function": """
def conditional_function(x: int, y: int) -> int:
    if x > y:
        return x - y
    else:
        return y - x
""",
        "error_function": """
def error_function(x: int) -> int:
    if x == 0:
        raise ValueError("Division by zero")
    return 100 // x
""",
        "complex_function": """
def complex_function(x: int, y: int, z: int) -> int:
    result = x * y
    if result > 100:
        result = result + z * 2
    elif result < 50:
        result = result - z
    else:
        result = result // (z + 1)

    if x == y and y == z:
        raise ValueError("All equal")

    return result
""",
        "loop_function": """
def loop_function(n: int) -> int:
    total = 0
    for i in range(n):
        for j in range(n):
            total += i * j
    return total
""",
        "recursive_function": """
def recursive_function(n: int) -> int:
    if n <= 0:
        return 1
    return n * recursive_function(n - 1)
""",
    }


@pytest.fixture
def sample_requests(test_code_samples):
    """Generate sample requests for testing"""
    return [
        {
            "request_type": "symbolic_check",
            "code": test_code_samples["simple_function"],
            "function_name": "simple_function",
            "timeout_seconds": 10,
        },
        {
            "request_type": "symbolic_check",
            "code": test_code_samples["conditional_function"],
            "function_name": "conditional_function",
            "timeout_seconds": 10,
        },
        {
            "request_type": "find_path_to_exception",
            "code": test_code_samples["error_function"],
            "function_name": "error_function",
            "exception_type": "ValueError",
            "timeout_seconds": 10,
        },
        {
            "request_type": "symbolic_check",
            "code": test_code_samples["complex_function"],
            "function_name": "complex_function",
            "timeout_seconds": 15,
        },
    ]


# Performance baselines and expectations
@pytest.fixture(scope="session")
def performance_baselines():
    """Define performance baselines for testing"""
    return {
        "max_response_time_ms": {
            "simple": 5000,  # 5 seconds for simple functions
            "complex": 15000,  # 15 seconds for complex functions
            "timeout": 30000,  # 30 seconds for timeout scenarios
        },
        "min_requests_per_second": {
            "light_load": 0.5,  # At least 0.5 req/s under light load
            "medium_load": 0.2,  # At least 0.2 req/s under medium load
            "heavy_load": 0.1,  # At least 0.1 req/s under heavy load
        },
        "memory_limits": {
            "max_growth_mb": 100,  # Max 100MB growth during tests
            "max_peak_mb": 500,  # Max 500MB peak usage
            "leak_threshold_mb": 50,  # Consider >50MB as potential leak
        },
        "security_expectations": {
            "min_block_rate": 0.95,  # At least 95% of attacks should be blocked
            "max_bypasses": 0,  # Zero security bypasses allowed
            "response_time_ms": 1000,  # Security checks should be fast
        },
    }


# Test environment validation
@pytest.fixture(scope="session", autouse=True)
def validate_test_environment():
    """Validate that the test environment is properly set up"""
    print("\n" + "=" * 60)
    print("SYMBOLIC EXECUTION MCP INTEGRATION TEST SUITE")
    print("=" * 60)

    # Check critical dependencies
    try:
        import psutil

        print(f"✅ psutil available: {psutil.__version__}")
    except ImportError:
        pytest.skip(
            "psutil not available - required for integration tests",
            allow_module_level=True,
        )

    try:
        import crosshair

        print(f"✅ CrossHair available: {getattr(crosshair, '__version__', 'unknown')}")
    except ImportError:
        print("⚠️  CrossHair not available - testing graceful degradation")

    print(f"✅ Python version: {sys.version}")
    print("✅ Test environment validated")
    print("=" * 60 + "\n")


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_test_state():
    """Clean up test state before and after each test"""
    # Pre-test cleanup
    yield

    # Post-test cleanup
    import gc

    gc.collect()  # Force garbage collection


# Skip conditions
def pytest_runtest_setup(item):
    """Set up test run with appropriate skip conditions"""
    # Skip slow tests unless explicitly requested
    if item.get_closest_marker("slow") and not item.config.getoption("--run-slow"):
        pytest.skip("Slow test - use --run-slow to include")

    # Skip memory tests unless explicitly requested
    if item.get_closest_marker("memory") and not item.config.getoption("--run-memory"):
        pytest.skip("Memory test - use --run-memory to include")


def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--run-slow", action="store_true", default=False, help="Run slow tests"
    )
    parser.addoption(
        "--run-memory",
        action="store_true",
        default=False,
        help="Run memory-intensive tests",
    )
    parser.addoption(
        "--performance-report",
        action="store_true",
        default=False,
        help="Generate detailed performance report",
    )
    parser.addoption(
        "--security-report",
        action="store_true",
        default=False,
        help="Generate detailed security report",
    )
