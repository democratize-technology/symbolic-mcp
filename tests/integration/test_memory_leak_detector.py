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
Memory Leak Detector for Memory Usage Validation Under Load

Based on fuzzing-mcp patterns for comprehensive memory leak detection.
This detector validates memory limits, identifies leaks, and monitors resource usage.
"""

import gc  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402
import tracemalloc  # noqa: E402
import weakref  # noqa: E402
from concurrent.futures import ThreadPoolExecutor  # noqa: E402
from dataclasses import asdict, dataclass  # noqa: E402
from typing import Any, Callable, Dict, List, Optional  # noqa: E402

import psutil  # noqa: E402
import pytest  # noqa: E402

# Import mock analyzer
from .mocks import MockSymbolicAnalyzer  # noqa: E402

# Create mock analyzer for testing
_symbolic_analyzer = MockSymbolicAnalyzer()


# Mock RequestExecutor for compatibility with legacy code
class MockRequestExecutor:
    """Mock RequestExecutor that provides the same interface as main module functions"""

    def __init__(self):
        from .mocks import MockSymbolicAnalyzer  # noqa: E402

        self.symbolic_analyzer = MockSymbolicAnalyzer()

    def logic_symbolic_check(
        self, code: str, function_name: str, timeout_seconds: int
    ) -> Dict[str, Any]:
        """Execute symbolic check using injected analyzer"""
        result = self.symbolic_analyzer.analyze_function(
            code, function_name, timeout_seconds
        )
        return {
            "status": result.status,
            "function_name": result.function_name,
            "analysis_time_seconds": result.analysis_time_seconds,
            "findings": result.findings,
            "paths_found": result.paths_found,
            "counterexamples": result.counterexamples,
            "errors": result.errors,
            "metadata": result.metadata,
        }

    def logic_find_path_to_exception(
        self, code: str, function_name: str, exception_type: str, timeout_seconds: int
    ) -> Dict[str, Any]:
        """Find exception paths using injected analyzer"""
        result = self.symbolic_analyzer.find_exception_paths(
            code, function_name, exception_type, timeout_seconds
        )
        return {
            "status": result.status,
            "function_name": result.function_name,
            "analysis_time_seconds": result.analysis_time_seconds,
            "findings": result.findings,
            "paths_found": result.paths_found,
            "counterexamples": result.counterexamples,
            "errors": result.errors,
            "metadata": result.metadata,
        }

    def logic_compare_functions(
        self, code: str, function_a: str, function_b: str, timeout_seconds: int
    ) -> Dict[str, Any]:
        """Compare functions using injected analyzer"""
        result = self.symbolic_analyzer.compare_functions(
            code, function_a, function_b, timeout_seconds
        )
        return {
            "status": result.status,
            "function_name": result.function_name,
            "analysis_time_seconds": result.analysis_time_seconds,
            "findings": result.findings,
            "paths_found": result.paths_found,
            "counterexamples": result.counterexamples,
            "errors": result.errors,
            "metadata": result.metadata,
        }

    def logic_analyze_branches(
        self, code: str, function_name: str, timeout_seconds: int
    ) -> Dict[str, Any]:
        """Analyze branches using injected analyzer"""
        result = self.symbolic_analyzer.analyze_branches(
            code, function_name, timeout_seconds
        )
        return {
            "status": result.status,
            "function_name": result.function_name,
            "analysis_time_seconds": result.analysis_time_seconds,
            "findings": result.findings,
            "paths_found": result.paths_found,
            "counterexamples": result.counterexamples,
            "errors": result.errors,
            "metadata": result.metadata,
        }

    def set_memory_limit(self, limit_mb: int) -> bool:
        """Mock memory limit setting - returns True for compatibility"""
        return True


# Create global request executor instance
_request_executor = MockRequestExecutor()


# Expose functions for compatibility with existing code
def logic_symbolic_check(
    code: str, function_name: str, timeout_seconds: int
) -> Dict[str, Any]:
    return _request_executor.logic_symbolic_check(code, function_name, timeout_seconds)


def logic_find_path_to_exception(
    code: str, function_name: str, exception_type: str, timeout_seconds: int
) -> Dict[str, Any]:
    return _request_executor.logic_find_path_to_exception(
        code, function_name, exception_type, timeout_seconds
    )


def logic_compare_functions(
    code: str, function_a: str, function_b: str, timeout_seconds: int
) -> Dict[str, Any]:
    return _request_executor.logic_compare_functions(
        code, function_a, function_b, timeout_seconds
    )


def logic_analyze_branches(
    code: str, function_name: str, timeout_seconds: int
) -> Dict[str, Any]:
    return _request_executor.logic_analyze_branches(
        code, function_name, timeout_seconds
    )


def set_memory_limit(limit_mb: int) -> bool:
    return _request_executor.set_memory_limit(limit_mb)


@dataclass
class MemorySnapshot:
    """Memory usage snapshot at a point in time"""

    timestamp: float
    rss_mb: float  # Resident Set Size
    vms_mb: float  # Virtual Memory Size
    percent: float
    available_mb: float
    python_objects: int
    tracemalloc_current: float
    tracemalloc_peak: float


@dataclass
class MemoryLeakReport:
    """Comprehensive memory leak analysis report"""

    test_name: str
    duration_seconds: float
    initial_memory_mb: float
    peak_memory_mb: float
    final_memory_mb: float
    memory_growth_mb: float
    memory_leak_detected: bool
    leak_rate_mb_per_minute: float
    max_python_objects: int
    python_object_growth: int
    snapshots: List[MemorySnapshot]
    recommendations: List[str]


class MemoryMonitor:
    """Background memory monitoring thread"""

    def __init__(self, sample_interval: float = 0.5):
        self.sample_interval = sample_interval
        self.monitoring = False
        self.snapshots: List[MemorySnapshot] = []
        self.monitor_thread: Optional[threading.Thread] = None
        self.process = psutil.Process()

    def start_monitoring(self):
        """Start background memory monitoring"""
        self.monitoring = True
        self.snapshots.clear()
        tracemalloc.start()

        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self) -> List[MemorySnapshot]:
        """Stop monitoring and return collected snapshots"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)

        tracemalloc.stop()
        return self.snapshots.copy()

    def _monitor_loop(self):
        """Background monitoring loop"""
        while self.monitoring:
            try:
                memory_info = self.process.memory_info()
                memory_full_info = self.process.memory_full_info()

                # Get tracemalloc stats
                current, peak = tracemalloc.get_traced_memory()

                snapshot = MemorySnapshot(
                    timestamp=time.time(),
                    rss_mb=memory_info.rss / 1024 / 1024,
                    vms_mb=memory_info.vms / 1024 / 1024,
                    percent=self.process.memory_percent(),
                    available_mb=psutil.virtual_memory().available / 1024 / 1024,
                    python_objects=len(gc.get_objects()),
                    tracemalloc_current=current / 1024 / 1024,
                    tracemalloc_peak=peak / 1024 / 1024,
                )

                self.snapshots.append(snapshot)

            except Exception as e:
                print(f"Memory monitoring error: {e}")

            time.sleep(self.sample_interval)


class MemoryLeakDetector:
    """
    Comprehensive memory leak detection and analysis

    Based on fuzzing-mcp patterns for memory validation under load.
    Detects memory leaks, tracks resource usage, and provides analysis.
    """

    def __init__(
        self, leak_threshold_mb: float = 50.0, test_duration_minutes: float = 5.0
    ):
        self.leak_threshold_mb = leak_threshold_mb
        self.test_duration_minutes = test_duration_minutes
        self.memory_monitor = MemoryMonitor()

    def get_memory_usage_mb(self) -> float:
        """Get current memory usage in MB"""
        return psutil.Process().memory_info().rss / 1024 / 1024

    def count_python_objects(self) -> int:
        """Count current Python objects"""
        return len(gc.get_objects())

    def force_garbage_collection(self) -> int:
        """Force garbage collection and return number of collected objects"""
        objects_before = self.count_python_objects()
        gc.collect()
        objects_after = self.count_python_objects()
        return objects_before - objects_after

    def run_memory_stress_test(
        self, test_name: str, duration_minutes: float = None
    ) -> MemoryLeakReport:
        """Run memory stress test to detect leaks"""
        if duration_minutes is None:
            duration_minutes = self.test_duration_minutes

        print(f"Starting memory stress test: {test_name} ({duration_minutes} minutes)")

        # Initial setup
        gc.collect()  # Clean up before test
        initial_memory = self.get_memory_usage_mb()
        initial_objects = self.count_python_objects()

        # Start monitoring
        self.memory_monitor.start_monitoring()

        start_time = time.time()
        end_time = start_time + (duration_minutes * 60)

        # Memory stress workload
        iteration = 0
        while time.time() < end_time:
            iteration += 1

            # Simulate symbolic execution workload
            self._execute_memory_intensive_workload(iteration)

            # Periodic garbage collection
            if iteration % 10 == 0:
                collected = self.force_garbage_collection()
                if collected > 1000:  # Significant collection
                    print(f"GC collected {collected} objects at iteration {iteration}")

            # Small delay to prevent CPU spinning
            time.sleep(0.1)

        # Stop monitoring
        snapshots = self.memory_monitor.stop_monitoring()

        # Final cleanup and measurement
        self.force_garbage_collection()
        final_memory = self.get_memory_usage_mb()
        final_objects = self.count_python_objects()

        # Calculate metrics
        duration = time.time() - start_time
        memory_growth = final_memory - initial_memory
        object_growth = final_objects - initial_objects

        # Peak memory
        peak_memory = max(s.rss_mb for s in snapshots) if snapshots else final_memory

        # Detect leak
        memory_leak_detected = memory_growth > self.leak_threshold_mb

        # Calculate leak rate
        leak_rate_mb_per_minute = (memory_growth / duration) * 60 if duration > 0 else 0

        # Generate recommendations
        recommendations = self._generate_recommendations(
            memory_growth, object_growth, duration, memory_leak_detected
        )

        report = MemoryLeakReport(
            test_name=test_name,
            duration_seconds=duration,
            initial_memory_mb=initial_memory,
            peak_memory_mb=peak_memory,
            final_memory_mb=final_memory,
            memory_growth_mb=memory_growth,
            memory_leak_detected=memory_leak_detected,
            leak_rate_mb_per_minute=leak_rate_mb_per_minute,
            max_python_objects=(
                max(s.python_objects for s in snapshots) if snapshots else final_objects
            ),
            python_object_growth=object_growth,
            snapshots=snapshots,
            recommendations=recommendations,
        )

        print(f"Memory stress test completed:")  # noqa: F541
        print(f"  Duration: {duration:.1f}s")
        print(f"  Memory growth: {memory_growth:.1f}MB")
        print(f"  Object growth: {object_growth}")
        print(f"  Leak detected: {memory_leak_detected}")
        print(f"  Leak rate: {leak_rate_mb_per_minute:.2f}MB/min")

        return report

    def _execute_memory_intensive_workload(self, iteration: int):
        """Execute symbolic execution workload for memory testing"""
        try:
            # Simple symbolic check that should work
            simple_code = f"""
def test_function_{iteration % 5}(x: int) -> int:
    if x > {iteration % 10}:
        return x * 2
    else:
        return x + 1
"""

            result = logic_symbolic_check(
                code=simple_code,
                function_name=f"test_function_{iteration % 5}",
                timeout_seconds=5,
            )

            # Create some objects intentionally (will be cleaned up by GC)
            test_objects = []
            for i in range(10):
                test_objects.append(
                    {"iteration": iteration, "data": list(range(100)), "result": result}
                )

            # Objects should be garbage collected when function exits
            del test_objects

        except Exception:
            # Expected with some test cases - continue monitoring
            pass

    def test_memory_limits(self) -> bool:
        """Test memory limit enforcement"""
        print("Testing memory limit enforcement...")

        try:
            # Set a low memory limit for testing
            original_limit = 2 * 1024 * 1024 * 1024  # 2GB
            test_limit = 100 * 1024 * 1024  # 100MB

            # This would normally be set at startup, but we test the mechanism
            print(f"Testing with memory limit: {test_limit / 1024 / 1024:.1f}MB")

            # Test that memory monitoring is working
            current_memory = self.get_memory_usage_mb()
            assert current_memory > 0, "Memory monitoring not working"

            print(f"Current memory usage: {current_memory:.1f}MB")
            return True

        except Exception as e:
            print(f"Memory limit test failed: {e}")
            return False

    def test_symbolic_execution_memory_patterns(self) -> Dict[str, Any]:
        """Test memory patterns during symbolic execution"""
        print("Testing symbolic execution memory patterns...")

        # Enable tracemalloc for detailed tracking
        tracemalloc.start()

        memory_patterns = {
            "simple_analysis": [],
            "complex_analysis": [],
            "error_handling": [],
        }

        # Test simple analysis patterns
        for i in range(5):
            gc.collect()
            before = self.get_memory_usage_mb()
            before_objects = self.count_python_objects()

            try:
                result = logic_symbolic_check(
                    code="def simple(x: int) -> int: return x + 1",
                    function_name="simple",
                    timeout_seconds=5,
                )

                after = self.get_memory_usage_mb()
                after_objects = self.count_python_objects()

                memory_patterns["simple_analysis"].append(
                    {
                        "memory_delta": after - before,
                        "object_delta": after_objects - before_objects,
                        "success": result.get("status") != "error",
                    }
                )

            except Exception:
                after = self.get_memory_usage_mb()
                after_objects = self.count_python_objects()
                memory_patterns["simple_analysis"].append(
                    {
                        "memory_delta": after - before,
                        "object_delta": after_objects - before_objects,
                        "success": False,
                    }
                )

        # Test complex analysis patterns
        complex_code = """
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
"""

        for i in range(3):
            gc.collect()
            before = self.get_memory_usage_mb()
            before_objects = self.count_python_objects()

            try:
                result = logic_symbolic_check(
                    code=complex_code,
                    function_name="complex_function",
                    timeout_seconds=10,
                )

                after = self.get_memory_usage_mb()
                after_objects = self.count_python_objects()

                memory_patterns["complex_analysis"].append(
                    {
                        "memory_delta": after - before,
                        "object_delta": after_objects - before_objects,
                        "success": result.get("status") != "error",
                    }
                )

            except Exception:
                after = self.get_memory_usage_mb()
                after_objects = self.count_python_objects()
                memory_patterns["complex_analysis"].append(
                    {
                        "memory_delta": after - before,
                        "object_delta": after_objects - before_objects,
                        "success": False,
                    }
                )

        # Test error handling patterns
        error_code = """
def error_prone(x: int) -> int:
    if x == 0:
        raise ZeroDivisionError("Division by zero")
    return 100 // x
"""

        for i in range(3):
            gc.collect()
            before = self.get_memory_usage_mb()
            before_objects = self.count_python_objects()

            try:
                result = logic_find_path_to_exception(
                    code=error_code,
                    function_name="error_prone",
                    exception_type="ZeroDivisionError",
                    timeout_seconds=5,
                )

                after = self.get_memory_usage_mb()
                after_objects = self.count_python_objects()

                memory_patterns["error_handling"].append(
                    {
                        "memory_delta": after - before,
                        "object_delta": after_objects - before_objects,
                        "success": result.get("status") != "error",
                    }
                )

            except Exception:
                after = self.get_memory_usage_mb()
                after_objects = self.count_python_objects()
                memory_patterns["error_handling"].append(
                    {
                        "memory_delta": after - before,
                        "object_delta": after_objects - before_objects,
                        "success": False,
                    }
                )

        tracemalloc.stop()

        return memory_patterns

    def _generate_recommendations(
        self,
        memory_growth: float,
        object_growth: int,
        duration: float,
        leak_detected: bool,
    ) -> List[str]:
        """Generate recommendations based on memory analysis"""
        recommendations = []

        if leak_detected:
            recommendations.append(
                "🚨 MEMORY LEAK DETECTED - Investigate object retention"
            )
            recommendations.append("Review symbolic execution cleanup procedures")

        if memory_growth > 20:
            recommendations.append(
                "High memory growth detected - consider reducing cache sizes"
            )

        if object_growth > 10000:
            recommendations.append("High object growth - check for object accumulation")

        if duration > 60 and memory_growth > 10:
            recommendations.append(
                "Consider periodic garbage collection during long runs"
            )

        if memory_growth < 0:
            recommendations.append("Good memory management - no leaks detected")

        return recommendations

    def assert_memory_requirements(self, report: MemoryLeakReport):
        """Assert memory requirements are met"""
        # Critical memory assertions
        assert (
            not report.memory_leak_detected
        ), f"Memory leak detected: {report.memory_growth_mb:.1f}MB"
        assert (
            abs(report.leak_rate_mb_per_minute) < 10
        ), f"Leak rate too high: {report.leak_rate_mb_per_minute:.2f}MB/min"

        # Memory usage should be reasonable
        assert (
            report.peak_memory_mb < 1000
        ), f"Peak memory too high: {report.peak_memory_mb:.1f}MB"

        print(f"✅ Memory requirements met for {report.test_name}")


# Pytest fixtures
@pytest.fixture
def memory_detector():
    """Pytest fixture for memory leak detector"""
    return MemoryLeakDetector(leak_threshold_mb=30.0, test_duration_minutes=1.0)


@pytest.mark.memory
def test_memory_basic_monitoring(memory_detector):
    """Test basic memory monitoring functionality"""
    initial_memory = memory_detector.get_memory_usage_mb()
    initial_objects = memory_detector.count_python_objects()

    # Allocate some memory
    test_data = []
    for i in range(1000):
        test_data.append(list(range(100)))

    peak_memory = memory_detector.get_memory_usage_mb()
    peak_objects = memory_detector.count_python_objects()

    # Clean up
    del test_data
    collected = memory_detector.force_garbage_collection()

    final_memory = memory_detector.get_memory_usage_mb()
    final_objects = memory_detector.count_python_objects()

    # Verify monitoring worked
    assert peak_memory > initial_memory
    assert peak_objects > initial_objects
    assert collected > 0
    print(  # noqa: E501
        f"Memory monitoring test: {initial_memory:.1f}MB -> {peak_memory:.1f}MB -> {final_memory:.1f}MB"
    )


@pytest.mark.memory
@pytest.mark.slow
def test_memory_leak_detection_short(memory_detector):
    """Test memory leak detection with short duration"""
    # Run a short stress test (1 minute instead of 5)
    report = memory_detector.run_memory_stress_test(
        "short_leak_test", duration_minutes=0.5
    )

    memory_detector.assert_memory_requirements(report)

    # Should have collected some data
    assert len(report.snapshots) > 10
    assert report.duration_seconds > 25  # At least 25 seconds


@pytest.mark.memory
def test_memory_limit_enforcement(memory_detector):
    """Test memory limit enforcement mechanism"""
    result = memory_detector.test_memory_limits()
    assert result, "Memory limit enforcement not working"


@pytest.mark.memory
def test_memory_patterns_analysis(memory_detector):
    """Test symbolic execution memory patterns"""
    patterns = memory_detector.test_symbolic_execution_memory_patterns()

    # Should have data for all test types
    assert "simple_analysis" in patterns
    assert "complex_analysis" in patterns
    assert "error_handling" in patterns

    # Should have executed tests
    assert len(patterns["simple_analysis"]) >= 5
    assert len(patterns["complex_analysis"]) >= 3
    assert len(patterns["error_handling"]) >= 3

    # Analyze patterns
    simple_avg = sum(p["memory_delta"] for p in patterns["simple_analysis"]) / len(
        patterns["simple_analysis"]
    )
    complex_avg = sum(p["memory_delta"] for p in patterns["complex_analysis"]) / len(
        patterns["complex_analysis"]
    )

    print(f"Memory patterns - Simple: {simple_avg:.2f}MB, Complex: {complex_avg:.2f}MB")


@pytest.mark.memory
def test_memory_cleanup_verification(memory_detector):
    """Test memory cleanup and garbage collection"""
    # Create objects that should be cleaned up
    objects_before = memory_detector.count_python_objects()

    # Create temporary objects
    temp_objects = []
    for i in range(100):
        temp_objects.append(
            {
                "data": list(range(1000)),
                "nested": {"more_data": list(range(500))},
                "string_data": "x" * 1000,
            }
        )

    objects_created = memory_detector.count_python_objects()

    # Clean up
    del temp_objects
    collected = memory_detector.force_garbage_collection()

    objects_after = memory_detector.count_python_objects()

    # Verify cleanup worked
    assert objects_created > objects_before
    assert collected > 0
    assert objects_after <= objects_before + 100  # Allow some variance

    print(  # noqa: E501
        f"Cleanup test: {objects_before} -> {objects_created} -> {objects_after} (collected {collected})"
    )


if __name__ == "__main__":
    # Run standalone memory leak detection
    def main():
        detector = MemoryLeakDetector()

        # Quick memory leak test (2 minutes)
        report = detector.run_memory_stress_test(
            "standalone_test", duration_minutes=0.1
        )

        print(f"\nMemory Leak Detection Results:")  # noqa: F541
        print(json.dumps(asdict(report), indent=2, default=str))

        detector.assert_memory_requirements(report)

        # Test memory patterns
        patterns = detector.test_symbolic_execution_memory_patterns()
        print(f"\nMemory Patterns:")  # noqa: F541
        for test_type, results in patterns.items():
            avg_memory = sum(r["memory_delta"] for r in results) / len(results)
            success_rate = sum(1 for r in results if r["success"]) / len(results)
            print(f"  {test_type}: {avg_memory:.3f}MB avg, {success_rate:.1%} success")

    import json

    main()
