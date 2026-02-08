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
E2E Test Harness for Complete MCP Session Lifecycle Testing

Based on fuzzing-mcp patterns for end-to-end testing of Model Context Protocol servers.
This harness validates the complete session lifecycle from initialization to cleanup.
"""

import asyncio  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import queue  # noqa: E402
import sys  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
from dataclasses import asdict, dataclass  # noqa: E402
from typing import Any, AsyncGenerator, Dict, List, Optional  # noqa: E402

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import mock implementations
from .mocks import MockSymbolicAnalyzer  # noqa: E402


@dataclass
class SessionMetrics:
    """Metrics collected during MCP session testing"""

    session_start_time: float
    session_end_time: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    timeouts: int
    avg_response_time: float
    max_response_time: float
    min_response_time: float
    memory_peak_mb: float
    memory_final_mb: float
    errors: List[str]


class E2ETestHarness:
    """
    Complete MCP session lifecycle testing harness

    Uses mock implementations for simplified testing without external dependencies.
    Based on fuzzing-mcp patterns for comprehensive end-to-end validation.
    Tests session initialization, request handling, error recovery, and cleanup.
    """

    def __init__(self, timeout_seconds: int = 30, max_requests: int = 100):
        self.timeout_seconds = timeout_seconds
        self.max_requests = max_requests
        self.session_active = False
        self.request_queue = queue.Queue()
        self.response_queue = queue.Queue()
        self.metrics = None

        # Use mock symbolic analyzer
        self.symbolic_analyzer = MockSymbolicAnalyzer()

    async def initialize_session(self) -> bool:
        """Initialize MCP session and test basic connectivity"""
        try:
            # Test basic function availability using mock symbolic analyzer
            test_code = """
def simple_test(x: int) -> int:
    return x + 1
"""
            result = self.symbolic_analyzer.analyze_function(
                test_code, "simple_test", 5
            )

            # Verify mock returns a valid result
            if result and result.status == "mock_complete":
                self.session_active = True
                return True
            else:
                print("Session initialization failed: invalid mock response")
                return False

        except Exception as e:
            print(f"Session initialization failed: {e}")
            return False

    async def execute_request(self, request_type: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a single MCP request with timing and error tracking.
        Uses mock symbolic analyzer directly for testing.
        """
        if not self.session_active:
            raise RuntimeError("Session not initialized")

        start_time = time.time()

        try:
            # Use mock symbolic analyzer directly
            if request_type == "symbolic_check":
                result = self.symbolic_analyzer.analyze_function(
                    kwargs["code"], kwargs["function_name"], kwargs["timeout_seconds"]
                )
            elif request_type == "find_path_to_exception":
                result = self.symbolic_analyzer.find_exception_paths(
                    kwargs["code"],
                    kwargs["function_name"],
                    kwargs["exception_type"],
                    kwargs["timeout_seconds"],
                )
            elif request_type == "compare_functions":
                result = self.symbolic_analyzer.compare_functions(
                    kwargs["code"],
                    kwargs["function_a"],
                    kwargs["function_b"],
                    kwargs["timeout_seconds"],
                )
            elif request_type == "analyze_branches":
                result = self.symbolic_analyzer.analyze_branches(
                    kwargs["code"], kwargs["function_name"], kwargs["timeout_seconds"]
                )
            else:
                return {
                    "success": False,
                    "error": f"Unknown request type: {request_type}",
                    "response_time": time.time() - start_time,
                    "request_type": request_type,
                    "kwargs": kwargs,
                }

            response_time = time.time() - start_time

            # Convert result to expected format
            return {
                "success": True,
                "result": result.__dict__ if hasattr(result, "__dict__") else result,
                "response_time": response_time,
                "request_type": request_type,
                "kwargs": kwargs,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time,
                "request_type": request_type,
                "kwargs": kwargs,
            }

    async def run_load_test(self, requests: List[Dict[str, Any]]) -> SessionMetrics:
        """Run load test with multiple concurrent requests"""
        if not self.session_active:
            raise RuntimeError("Session not initialized")

        start_time = time.time()
        metrics = SessionMetrics(
            session_start_time=start_time,
            session_end_time=0,
            total_requests=len(requests),
            successful_requests=0,
            failed_requests=0,
            timeouts=0,
            avg_response_time=0,
            max_response_time=0,
            min_response_time=float("inf"),
            memory_peak_mb=0,
            memory_final_mb=0,
            errors=[],
        )

        response_times = []

        # Execute requests
        for request in requests:
            if time.time() - start_time > self.timeout_seconds:
                metrics.timeouts += 1
                metrics.errors.append(f"Timeout for request: {request}")
                continue

            response = await self.execute_request(**request)

            if response["success"]:
                metrics.successful_requests += 1
            else:
                metrics.failed_requests += 1
                metrics.errors.append(f"Request failed: {response['error']}")

            response_times.append(response["response_time"])
            metrics.max_response_time = max(
                metrics.max_response_time, response["response_time"]
            )
            metrics.min_response_time = min(
                metrics.min_response_time, response["response_time"]
            )

        # Calculate final metrics
        metrics.session_end_time = time.time()
        if response_times:
            metrics.avg_response_time = sum(response_times) / len(response_times)
        if metrics.min_response_time == float("inf"):
            metrics.min_response_time = 0

        self.metrics = metrics
        return metrics

    async def cleanup_session(self) -> bool:
        """Cleanup MCP session and resources"""
        try:
            self.session_active = False
            # Clear queues
            while not self.request_queue.empty():
                try:
                    self.request_queue.get_nowait()
                except queue.Empty:
                    break
            while not self.response_queue.empty():
                try:
                    self.response_queue.get_nowait()
                except queue.Empty:
                    break

            return True

        except Exception as e:
            print(f"Session cleanup failed: {e}")
            return False

    @asynccontextmanager
    async def session(self) -> AsyncGenerator["E2ETestHarness", None]:
        """Context manager for session lifecycle"""
        if not await self.initialize_session():
            raise RuntimeError("Failed to initialize session")

        try:
            yield self
        finally:
            await self.cleanup_session()


# Test data generators
def generate_symbolic_check_requests(count: int = 10) -> List[Dict[str, Any]]:
    """Generate symbolic check requests for testing"""
    requests = []

    test_cases = [
        {
            "code": """
def simple_add(x: int, y: int) -> int:
    return x + y
""",
            "function_name": "simple_add",
        },
        {
            "code": """
def conditional(x: int) -> int:
    if x > 10:
        return x * 2
    else:
        return x + 5
""",
            "function_name": "conditional",
        },
        {
            "code": """
def might_crash(x: int, y: int) -> int:
    if y == 0:
        raise ValueError("Division by zero")
    return x // y
""",
            "function_name": "might_crash",
        },
    ]

    for i in range(count):
        test_case = test_cases[i % len(test_cases)]
        requests.append(
            {
                "request_type": "symbolic_check",
                "code": test_case["code"],
                "function_name": test_case["function_name"],
                "timeout_seconds": 10,
            }
        )

    return requests


def generate_exception_path_requests(count: int = 5) -> List[Dict[str, Any]]:
    """Generate exception path requests for testing"""
    requests = []

    test_cases = [
        {
            "code": """
def index_error(x: int):
    if x < 0:
        raise IndexError("Negative index")
    return x
""",
            "function_name": "index_error",
            "exception_type": "IndexError",
        },
        {
            "code": """
def value_error(s: str):
    if not s.isdigit():
        raise ValueError("Not a number")
    return int(s)
""",
            "function_name": "value_error",
            "exception_type": "ValueError",
        },
    ]

    for i in range(count):
        test_case = test_cases[i % len(test_cases)]
        requests.append(
            {
                "request_type": "find_path_to_exception",
                "code": test_case["code"],
                "function_name": test_case["function_name"],
                "exception_type": test_case["exception_type"],
                "timeout_seconds": 10,
            }
        )

    return requests


# Pytest integration
@pytest_asyncio.fixture
async def e2e_harness():
    """Pytest fixture for E2E test harness with mock analyzer"""
    harness = E2ETestHarness(timeout_seconds=30, max_requests=50)
    async with harness.session():
        yield harness


@pytest_asyncio.fixture
async def e2e_harness_mock():
    """Pytest fixture for E2E test harness with mock analyzer (alias for consistency)"""
    harness = E2ETestHarness(timeout_seconds=30, max_requests=50)
    async with harness.session():
        yield harness


@pytest.mark.asyncio
@pytest.mark.integration
async def test_e2e_session_lifecycle(e2e_harness):
    """Test complete session lifecycle"""
    # Verify session is active
    assert e2e_harness.session_active

    # Execute a simple request
    response = await e2e_harness.execute_request(
        request_type="symbolic_check",
        code="def test(x: int) -> int: return x + 1",
        function_name="test",
        timeout_seconds=5,
    )

    # Verify response structure
    assert "success" in response
    assert "response_time" in response
    assert response["response_time"] > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_e2e_load_testing(e2e_harness):
    """Test load handling capabilities"""
    requests = generate_symbolic_check_requests(20)
    metrics = await e2e_harness.run_load_test(requests)

    # Verify metrics were collected
    assert metrics.total_requests == 20
    assert metrics.session_end_time > metrics.session_start_time
    assert (
        metrics.successful_requests + metrics.failed_requests <= metrics.total_requests
    )

    # Print metrics for debugging
    print(f"Load test metrics: {asdict(metrics)}")


@pytest.mark.asyncio
@pytest.mark.integration
async def test_e2e_mixed_requests(e2e_harness):
    """Test handling of mixed request types"""
    requests = []
    requests.extend(generate_symbolic_check_requests(5))
    requests.extend(generate_exception_path_requests(3))

    metrics = await e2e_harness.run_load_test(requests)

    # Verify all requests were processed
    assert metrics.total_requests == 8
    assert metrics.avg_response_time > 0


@pytest.mark.asyncio
@pytest.mark.integration
async def test_e2e_error_handling(e2e_harness):
    """Test error handling and recovery"""
    # Test with unknown request type - this will fail
    response = await e2e_harness.execute_request(
        request_type="unknown_request_type",
        code="def test(x): return x",
        function_name="test",
        timeout_seconds=5,
    )

    # Should handle error gracefully for unknown request type
    assert not response["success"]
    assert "error" in response
    assert "Unknown request type" in response["error"]
    assert response["response_time"] >= 0


if __name__ == "__main__":
    # Run standalone tests
    async def main():
        async with E2ETestHarness().session() as harness:
            requests = generate_symbolic_check_requests(10)
            metrics = await harness.run_load_test(requests)
            print(f"Test completed: {asdict(metrics)}")

    asyncio.run(main())
