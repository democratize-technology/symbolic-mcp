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
Load Test Harness with psutil Integration for Performance Monitoring

Based on fuzzing-mcp patterns for comprehensive performance testing.
This harness validates resource usage, throughput, and scalability under load.

Uses mock implementations for simplified testing without external dependencies.
"""

import asyncio  # noqa: E402
import gc  # noqa: E402
import json  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402
from dataclasses import asdict, dataclass  # noqa: E402
from typing import Any, Callable, Dict, List, Optional  # noqa: E402

import psutil  # noqa: E402
import pytest  # noqa: E402

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# Import mock implementations
from .mocks import MockSymbolicAnalyzer  # noqa: E402


@dataclass
class ResourceMetrics:
    """Resource usage metrics collected during load testing"""

    timestamp: float
    cpu_percent: float
    memory_mb: float
    memory_percent: float
    open_files: int
    threads: int
    disk_io_read_mb: float
    disk_io_write_mb: float
    network_io_recv_mb: float
    network_io_sent_mb: float


@dataclass
class LoadTestResults:
    """Comprehensive load test results"""

    test_name: str
    duration_seconds: float
    total_requests: int
    successful_requests: int
    failed_requests: int
    requests_per_second: float
    avg_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    max_response_time: float
    min_response_time: float
    initial_memory_mb: float
    peak_memory_mb: float
    final_memory_mb: float
    memory_leak_mb: float
    avg_cpu_percent: float
    peak_cpu_percent: float
    resource_samples: List[ResourceMetrics]
    errors: List[str]


class ResourceMonitor:
    """Background resource monitoring using psutil"""

    def __init__(self, sample_interval: float = 0.5):
        self.sample_interval = sample_interval
        self.monitoring = False
        self.samples: List[ResourceMetrics] = []
        self.monitor_thread: Optional[threading.Thread] = None
        self.process = psutil.Process()

        # Track initial disk and network I/O (platform-dependent)
        try:
            self.initial_io_counters = self.process.io_counters()
        except (AttributeError, psutil.AccessDenied, psutil.NoSuchProcess):
            self.initial_io_counters = None

        try:
            self.initial_net_io = psutil.net_io_counters()
        except (AttributeError, psutil.AccessDenied):
            self.initial_net_io = None

    def start_monitoring(self):
        """Start background resource monitoring"""
        self.monitoring = True
        self.samples.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self) -> List[ResourceMetrics]:
        """Stop monitoring and return collected samples"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        return self.samples.copy()

    def _monitor_loop(self):  # noqa: C901
        """Background monitoring loop"""
        while self.monitoring:
            try:
                # Get memory info
                memory_info = self.process.memory_info()
                memory_mb = memory_info.rss / 1024 / 1024

                # Get CPU usage (non-blocking)
                cpu_percent = self.process.cpu_percent()

                # Get file and thread count
                try:
                    open_files = len(self.process.open_files())
                except (psutil.AccessDenied, psutil.NoSuchProcess):
                    open_files = 0

                threads = self.process.num_threads()

                # Get I/O counters (platform-dependent)
                disk_read_mb = 0
                disk_write_mb = 0
                try:
                    if self.initial_io_counters:
                        io_counters = self.process.io_counters()
                        disk_read_mb = (
                            (
                                io_counters.read_bytes
                                - self.initial_io_counters.read_bytes
                            )
                            / 1024
                            / 1024
                        )
                        disk_write_mb = (
                            (
                                io_counters.write_bytes
                                - self.initial_io_counters.write_bytes
                            )
                            / 1024
                            / 1024
                        )
                except (AttributeError, psutil.AccessDenied, psutil.NoSuchProcess):
                    disk_read_mb = 0
                    disk_write_mb = 0

                # Get network I/O (platform-dependent)
                net_recv_mb = 0
                net_sent_mb = 0
                try:
                    if self.initial_net_io:
                        net_io = psutil.net_io_counters()
                        net_recv_mb = (
                            (net_io.bytes_recv - self.initial_net_io.bytes_recv)
                            / 1024
                            / 1024
                        )
                        net_sent_mb = (
                            (net_io.bytes_sent - self.initial_net_io.bytes_sent)
                            / 1024
                            / 1024
                        )
                except (AttributeError, psutil.AccessDenied):
                    net_recv_mb = 0
                    net_sent_mb = 0

                sample = ResourceMetrics(
                    timestamp=time.time(),
                    cpu_percent=cpu_percent,
                    memory_mb=memory_mb,
                    memory_percent=self.process.memory_percent(),
                    open_files=open_files,
                    threads=threads,
                    disk_io_read_mb=disk_read_mb,
                    disk_io_write_mb=disk_write_mb,
                    network_io_recv_mb=net_recv_mb,
                    network_io_sent_mb=net_sent_mb,
                )

                self.samples.append(sample)

            except Exception as e:
                print(f"Resource monitoring error: {e}")

            time.sleep(self.sample_interval)


class LoadTestHarness:
    """
    Comprehensive load testing harness with resource monitoring

    Uses mock implementations for simplified testing without external dependencies.
    Based on fuzzing-mcp patterns for performance validation under various load conditions.  # noqa: E501
    """

    def __init__(self, max_concurrent_requests: int = 10, timeout_seconds: int = 30):
        self.max_concurrent_requests = max_concurrent_requests
        self.timeout_seconds = timeout_seconds
        self.resource_monitor = ResourceMonitor()
        # Use mock symbolic analyzer
        self.symbolic_analyzer = MockSymbolicAnalyzer()

    async def execute_request(self, request_type: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a single request with timing.
        Uses mock symbolic analyzer directly for testing.
        """
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
                }

            response_time = time.time() - start_time

            # Convert result to expected format
            return {
                "success": True,
                "result": result.__dict__ if hasattr(result, "__dict__") else result,
                "response_time": response_time,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "response_time": time.time() - start_time,
            }

    async def run_load_test(
        self, test_name: str, requests: List[Dict[str, Any]], concurrency: int = None
    ) -> LoadTestResults:
        """Run load test with specified concurrency"""
        if concurrency is None:
            concurrency = self.max_concurrent_requests

        print(  # noqa: E501
            f"Starting load test: {test_name} with {len(requests)} requests, concurrency={concurrency}"
        )

        # Start resource monitoring
        initial_memory_mb = psutil.Process().memory_info().rss / 1024 / 1024
        self.resource_monitor.start_monitoring()

        start_time = time.time()
        response_times = []
        successful_requests = 0
        failed_requests = 0
        errors = []

        # Execute requests with semaphore for concurrency control
        semaphore = asyncio.Semaphore(concurrency)

        async def bounded_request(request_data):
            async with semaphore:
                return await self.execute_request(**request_data)

        # Run all requests
        tasks = [bounded_request(req) for req in requests]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        # Process responses
        for response in responses:
            if isinstance(response, Exception):
                failed_requests += 1
                errors.append(str(response))
            elif response["success"]:
                successful_requests += 1
                response_times.append(response["response_time"])
            else:
                failed_requests += 1
                errors.append(response["error"])

        end_time = time.time()
        duration = end_time - start_time

        # Stop resource monitoring
        resource_samples = self.resource_monitor.stop_monitoring()
        final_memory_mb = psutil.Process().memory_info().rss / 1024 / 1024

        # Calculate metrics
        if response_times:
            response_times.sort()
            avg_response_time = sum(response_times) / len(response_times)
            p50_response_time = response_times[len(response_times) // 2]
            p95_response_time = response_times[int(len(response_times) * 0.95)]
            p99_response_time = response_times[int(len(response_times) * 0.99)]
            max_response_time = max(response_times)
            min_response_time = min(response_times)
        else:
            avg_response_time = p50_response_time = p95_response_time = 0
            p99_response_time = max_response_time = min_response_time = 0

        # Calculate resource metrics
        if resource_samples:
            cpu_values = [s.cpu_percent for s in resource_samples]
            memory_values = [s.memory_mb for s in resource_samples]
            avg_cpu_percent = sum(cpu_values) / len(cpu_values)
            peak_cpu_percent = max(cpu_values)
            peak_memory_mb = max(memory_values)
        else:
            avg_cpu_percent = peak_cpu_percent = peak_memory_mb = 0

        results = LoadTestResults(
            test_name=test_name,
            duration_seconds=duration,
            total_requests=len(requests),
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            requests_per_second=successful_requests / duration if duration > 0 else 0,
            avg_response_time=avg_response_time,
            p50_response_time=p50_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            max_response_time=max_response_time,
            min_response_time=min_response_time,
            initial_memory_mb=initial_memory_mb,
            peak_memory_mb=peak_memory_mb,
            final_memory_mb=final_memory_mb,
            memory_leak_mb=final_memory_mb - initial_memory_mb,
            avg_cpu_percent=avg_cpu_percent,
            peak_cpu_percent=peak_cpu_percent,
            resource_samples=resource_samples,
            errors=errors[:10],  # Keep only first 10 errors
        )

        print(  # noqa: E501
            f"Load test completed: {successful_requests}/{len(requests)} successful, "
            f"{results.requests_per_second:.2f} req/s, {results.avg_response_time:.3f}s avg"
        )

        return results

    def assert_performance_requirements(self, results: LoadTestResults):
        """Assert performance requirements are met"""
        # Basic performance assertions - these should be adjusted based on requirements
        assert results.successful_requests > 0, "No successful requests"
        assert (
            results.requests_per_second > 0.1
        ), f"Too slow: {results.requests_per_second} req/s"
        assert (
            results.avg_response_time < 10.0
        ), f"Response time too high: {results.avg_response_time}s"
        assert (
            results.memory_leak_mb < 100
        ), f"Memory leak detected: {results.memory_leak_mb}MB"
        assert (
            results.peak_cpu_percent < 95
        ), f"CPU usage too high: {results.peak_cpu_percent}%"

        print(f"✅ Performance requirements met for {results.test_name}")


# Test generators
def generate_symbolic_load_requests(count: int = 100) -> List[Dict[str, Any]]:
    """Generate symbolic check requests for load testing"""
    requests = []

    templates = [
        {
            "code": "def simple_math(x: int, y: int) -> int: return x + y",
            "function_name": "simple_math",
        },
        {
            "code": """
def conditional_logic(x: int, y: int) -> int:
    if x > y:
        return x - y
    else:
        return y - x
""",
            "function_name": "conditional_logic",
        },
        {
            "code": """
def complex_calculation(x: int, y: int, z: int) -> int:
    result = x * y
    if result > 100:
        result = result + z
    else:
        result = result - z
    return result
""",
            "function_name": "complex_calculation",
        },
        {
            "code": """
def potentially_error_prone(x: int) -> int:
    if x == 0:
        return 0
    elif x < 0:
        raise ValueError("Negative value")
    else:
        return 100 // x
""",
            "function_name": "potentially_error_prone",
        },
    ]

    for i in range(count):
        template = templates[i % len(templates)]
        requests.append(
            {
                "request_type": "symbolic_check",
                "code": template["code"],
                "function_name": template["function_name"],
                "timeout_seconds": 15,
            }
        )

    return requests


def generate_mixed_load_requests(count: int = 100) -> List[Dict[str, Any]]:
    """Generate mixed request types for comprehensive load testing"""
    requests = []

    # Mix of different request types
    symbolic_requests = generate_symbolic_load_requests(count // 2)

    # Add exception path requests
    exception_requests = []
    for i in range(count // 4):
        exception_requests.append(
            {
                "request_type": "find_path_to_exception",
                "code": """
def exception_path(x: int):
    if x == 42:
        raise ValueError("The answer")
    return x
""",
                "function_name": "exception_path",
                "exception_type": "ValueError",
                "timeout_seconds": 15,
            }
        )

    requests.extend(symbolic_requests)
    requests.extend(exception_requests)

    return requests


# Pytest fixtures
@pytest.fixture
def load_harness():
    """Pytest fixture for load test harness with mock analyzer"""
    return LoadTestHarness(max_concurrent_requests=10, timeout_seconds=30)


@pytest.fixture
def load_harness_mock():  # noqa: E501
    """Pytest fixture for load test harness with mock analyzer (alias for consistency)"""
    return LoadTestHarness(max_concurrent_requests=10, timeout_seconds=30)


@pytest.mark.asyncio
@pytest.mark.load
async def test_load_basic_performance(load_harness):
    """Test basic performance under light load"""
    requests = generate_symbolic_load_requests(20)
    results = await load_harness.run_load_test(
        "basic_performance", requests, concurrency=3
    )

    load_harness.assert_performance_requirements(results)
    assert results.successful_requests >= 15  # At least 75% success rate


@pytest.mark.asyncio
@pytest.mark.load
async def test_load_high_concurrency(load_harness):
    """Test performance under high concurrency"""
    requests = generate_symbolic_load_requests(50)
    results = await load_harness.run_load_test(
        "high_concurrency", requests, concurrency=10
    )

    load_harness.assert_performance_requirements(results)
    assert results.requests_per_second > 0.5  # At least 0.5 req/s under load


@pytest.mark.asyncio
@pytest.mark.load
async def test_load_mixed_workload(load_harness):
    """Test performance with mixed request types"""
    requests = generate_mixed_load_requests(40)
    results = await load_harness.run_load_test(
        "mixed_workload", requests, concurrency=5
    )

    load_harness.assert_performance_requirements(results)

    # Verify we have different response time patterns
    assert results.p95_response_time > results.p50_response_time


@pytest.mark.asyncio
@pytest.mark.load
async def test_load_memory_stability(load_harness):
    """Test memory usage stability over extended run"""
    # Force garbage collection before test
    gc.collect()

    # Run multiple sequential load tests
    all_results = []
    for i in range(3):
        requests = generate_symbolic_load_requests(30)
        results = await load_harness.run_load_test(
            f"memory_stability_{i}", requests, concurrency=5
        )
        all_results.append(results)

        # Small delay between tests
        await asyncio.sleep(1)

    # Check memory doesn't grow excessively
    memory_growth = all_results[-1].peak_memory_mb - all_results[0].peak_memory_mb
    assert memory_growth < 50, f"Memory grew too much: {memory_growth}MB"

    print(f"Memory stability test passed: {memory_growth:.1f}MB growth across 3 tests")


if __name__ == "__main__":
    # Run standalone load tests
    async def main():
        harness = LoadTestHarness()

        # Basic performance test
        requests = generate_symbolic_load_requests(50)
        results = await harness.run_load_test("standalone_test", requests)

        print(f"Load test results:")  # noqa: F541
        print(json.dumps(asdict(results), indent=2, default=str))

        harness.assert_performance_requirements(results)

    asyncio.run(main())
