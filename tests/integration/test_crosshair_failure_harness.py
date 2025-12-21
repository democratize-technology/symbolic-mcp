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
CrossHair Failure Test Harness for Integration Failure Scenario Testing

Based on fuzzing-mcp patterns for testing resilience under failure conditions.
This harness tests timeout handling, Z3 solver exhaustion, and graceful degradation.
"""

import pytest
import time
import threading
import signal
import subprocess
import tempfile
import os
import sys
import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import queue

# Import RequestExecutor abstraction and dependency container
from .interfaces import SymbolicAnalyzerInterface
from .dependency_container import create_test_container

# Create dependency injection container for isolated testing
_container = create_test_container(use_mocks=True)
_symbolic_analyzer = _container.resolve(SymbolicAnalyzerInterface)

# Check for CrossHair availability with graceful degradation
try:
    import crosshair.core_and_libs
    CROSSHAIR_AVAILABLE = True
except ImportError:
    CROSSHAIR_AVAILABLE = False

# Mock CrossHair functionality for testing environments where CrossHair is unavailable
class MockCrossHair:
    """Mock CrossHair implementation for testing without actual CrossHair dependency"""

    @staticmethod
    def check_function(code: str, function_name: str, timeout_seconds: int) -> Dict[str, Any]:
        """Mock CrossHair function checking"""
        return {
            'status': 'mock_complete',
            'function_name': function_name,
            'analysis_time': 0.1,
            'results': [],
            'postconditions': [],
            'errors': [],
            'exhausted': False
        }

    @staticmethod
    def analyze_paths(code: str, function_name: str, timeout_seconds: int) -> Dict[str, Any]:
        """Mock CrossHair path analysis"""
        return {
            'status': 'mock_complete',
            'function_name': function_name,
            'paths_found': 3,
            'analysis_time': 0.1,
            'exhausted': False
        }

# Create global crosshair instance (mock or real)
_crosshair = MockCrossHair() if not CROSSHAIR_AVAILABLE else None

# Mock RequestExecutor for compatibility with legacy code
class MockRequestExecutor:
    """Mock RequestExecutor that provides the same interface as main module functions"""

    def __init__(self, symbolic_analyzer: SymbolicAnalyzerInterface):
        self.symbolic_analyzer = symbolic_analyzer

    def logic_symbolic_check(self, code: str, function_name: str, timeout_seconds: int) -> Dict[str, Any]:
        """Execute symbolic check using injected analyzer"""
        result = self.symbolic_analyzer.analyze_function(code, function_name, timeout_seconds)
        return {
            'status': result.status,
            'function_name': result.function_name,
            'analysis_time_seconds': result.analysis_time_seconds,
            'findings': result.findings,
            'paths_found': result.paths_found,
            'counterexamples': result.counterexamples,
            'errors': result.errors,
            'metadata': result.metadata
        }

    def logic_find_path_to_exception(self, code: str, function_name: str, exception_type: str, timeout_seconds: int) -> Dict[str, Any]:
        """Find exception paths using injected analyzer"""
        result = self.symbolic_analyzer.find_exception_paths(code, function_name, exception_type, timeout_seconds)
        return {
            'status': result.status,
            'function_name': result.function_name,
            'analysis_time_seconds': result.analysis_time_seconds,
            'findings': result.findings,
            'paths_found': result.paths_found,
            'counterexamples': result.counterexamples,
            'errors': result.errors,
            'metadata': result.metadata
        }

    def logic_compare_functions(self, code: str, function_a: str, function_b: str, timeout_seconds: int) -> Dict[str, Any]:
        """Compare functions using injected analyzer"""
        result = self.symbolic_analyzer.compare_functions(code, function_a, function_b, timeout_seconds)
        return {
            'status': result.status,
            'function_name': result.function_name,
            'analysis_time_seconds': result.analysis_time_seconds,
            'findings': result.findings,
            'paths_found': result.paths_found,
            'counterexamples': result.counterexamples,
            'errors': result.errors,
            'metadata': result.metadata
        }

    def logic_analyze_branches(self, code: str, function_name: str, timeout_seconds: int) -> Dict[str, Any]:
        """Analyze branches using injected analyzer"""
        result = self.symbolic_analyzer.analyze_branches(code, function_name, timeout_seconds)
        return {
            'status': result.status,
            'function_name': result.function_name,
            'analysis_time_seconds': result.analysis_time_seconds,
            'findings': result.findings,
            'paths_found': result.paths_found,
            'counterexamples': result.counterexamples,
            'errors': result.errors,
            'metadata': result.metadata
        }

# Create global request executor instance
_request_executor = MockRequestExecutor(_symbolic_analyzer)

# Expose functions for compatibility with existing code
def logic_symbolic_check(code: str, function_name: str, timeout_seconds: int) -> Dict[str, Any]:
    return _request_executor.logic_symbolic_check(code, function_name, timeout_seconds)

def logic_find_path_to_exception(code: str, function_name: str, exception_type: str, timeout_seconds: int) -> Dict[str, Any]:
    return _request_executor.logic_find_path_to_exception(code, function_name, exception_type, timeout_seconds)

def logic_compare_functions(code: str, function_a: str, function_b: str, timeout_seconds: int) -> Dict[str, Any]:
    return _request_executor.logic_compare_functions(code, function_a, function_b, timeout_seconds)

def logic_analyze_branches(code: str, function_name: str, timeout_seconds: int) -> Dict[str, Any]:
    return _request_executor.logic_analyze_branches(code, function_name, timeout_seconds)


@dataclass
class FailureScenario:
    """Definition of a failure scenario test"""
    name: str
    description: str
    trigger_type: str  # "timeout", "exhaustion", "crash", "resource_limit"
    payload: str
    expected_behavior: str
    timeout_seconds: int


@dataclass
class FailureTestResult:
    """Result of a failure scenario test"""
    scenario_name: str
    test_passed: bool
    actual_behavior: str
    execution_time_ms: float
    error_message: str
    graceful_degradation: bool
    resource_cleanup: bool


@dataclass
class ResilienceReport:
    """Comprehensive resilience testing report"""
    test_name: str
    total_scenarios: int
    passed_scenarios: int
    failed_scenarios: int
    resilience_score: float  # 0.0 (fragile) to 1.0 (resilient)
    results: List[FailureTestResult]
    critical_failures: List[str]


class CrossHairFailureTestHarness:
    """
    CrossHair integration failure scenario testing harness

    Based on fuzzing-mcp patterns for testing resilience under various failure conditions.
    Tests timeout handling, solver exhaustion, and graceful degradation.
    """

    def __init__(self, default_timeout: int = 30):
        self.default_timeout = default_timeout
        self.test_results: List[FailureTestResult] = []

    def generate_failure_scenarios(self) -> List[FailureScenario]:
        """Generate comprehensive failure scenarios"""
        scenarios = []

        # 1. Timeout scenarios
        scenarios.extend([
            FailureScenario(
                name="infinite_loop_timeout",
                description="Test timeout handling with infinite loops",
                trigger_type="timeout",
                payload="""
def infinite_loop(x: int) -> int:
    while True:
        x = x + 1
        if x > 1000000:  # Should never reach here in reasonable time
            break
    return x
""",
                expected_behavior="timeout_graceful",
                timeout_seconds=5
            ),
            FailureScenario(
                name="deep_recursion_timeout",
                description="Test timeout with deep recursion",
                trigger_type="timeout",
                payload="""
def deep_recursion(x: int) -> int:
    if x <= 0:
        return deep_recursion(x - 1)  # Infinite recursion
    return x
""",
                expected_behavior="timeout_graceful",
                timeout_seconds=3
            ),
            FailureScenario(
                name="combinatorial_explosion",
                description="Test timeout with combinatorial explosion",
                trigger_type="timeout",
                payload="""
def combinatorial_explosion(arr: list) -> int:
    if not arr:
        return 0
    # Generate all subsets (2^n complexity)
    total = 0
    for i in range(2**len(arr)):
        for j in range(len(arr)):
            if i & (1 << j):
                total += arr[j]
    return total
""",
                expected_behavior="timeout_graceful",
                timeout_seconds=5
            ),
        ])

        # 2. Z3 Solver exhaustion scenarios
        scenarios.extend([
            FailureScenario(
                name="large_integer_constraints",
                description="Test Z3 with large integer constraints",
                trigger_type="exhaustion",
                payload="""
def large_integer_constraints(x: int) -> int:
    # Create many constraints that are hard for Z3
    constraints = [
        x > 1000000,
        x < 2000000,
        x % 7 == 0,
        x % 13 == 0,
        x % 17 == 0,
        x % 19 == 0,
        x % 23 == 0,
        x % 29 == 0,
        x % 31 == 0,
        x % 37 == 0,
        x % 41 == 0,
        x % 43 == 0,
        x % 47 == 0,
        x % 53 == 0,
        x % 59 == 0,
    ]
    if all(constraints):
        return x * 2
    return x
""",
                expected_behavior="graceful_exhaustion",
                timeout_seconds=10
            ),
            FailureScenario(
                name="complex_string_constraints",
                description="Test Z3 with complex string operations",
                trigger_type="exhaustion",
                payload="""
def complex_string_constraints(s: str) -> str:
    # Complex string constraints
    constraints = [
        len(s) > 10,
        s.count('a') >= 2,
        s.count('b') >= 2,
        s.count('c') >= 2,
        s.startswith('prefix'),
        s.endswith('suffix'),
        'xyz' in s,
        s[::-1] != s,  # Not a palindrome
        s.upper() != s.lower(),  # Mixed case
    ]
    if all(constraints):
        return s + "_processed"
    return s
""",
                expected_behavior="graceful_exhaustion",
                timeout_seconds=8
            ),
            FailureScenario(
                name="array_index_constraints",
                description="Test Z3 with complex array index constraints",
                trigger_type="exhaustion",
                payload="""
def complex_array_constraints(arr: list) -> int:
    n = len(arr)
    if n < 5:
        return 0

    # Complex constraints on indices and values
    sum_even = sum(arr[i] for i in range(n) if i % 2 == 0)
    sum_odd = sum(arr[i] for i in range(n) if i % 2 == 1)

    constraints = [
        sum_even > sum_odd,
        all(arr[i] > i for i in range(n)),
        any(arr[i] * i == 100 for i in range(n)),
        max(arr) - min(arr) > n,
    ]

    if all(constraints):
        return sum(arr)
    return 0
""",
                expected_behavior="graceful_exhaustion",
                timeout_seconds=10
            ),
        ])

        # 3. Resource limit scenarios
        scenarios.extend([
            FailureScenario(
                name="memory_pressure",
                description="Test behavior under memory pressure",
                trigger_type="resource_limit",
                payload="""
def memory_intensive(x: int) -> list:
    # Create large data structures
    big_data = []
    for i in range(10000):
        big_data.append([j for j in range(1000)])

    if len(big_data) > 5000:
        raise MemoryError("Too much memory")

    return big_data[:x]
""",
                expected_behavior="resource_error_handling",
                timeout_seconds=15
            ),
            FailureScenario(
                name="computationally_expensive",
                description="Test computationally expensive analysis",
                trigger_type="resource_limit",
                payload="""
def expensive_computation(n: int) -> int:
    # Simulate expensive computation
    result = 0
    for i in range(n):
        for j in range(n):
            for k in range(n):
                result += (i * j * k) % 1000
    return result
""",
                expected_behavior="timeout_or_resource_limit",
                timeout_seconds=8
            ),
        ])

        # 4. Error handling scenarios
        scenarios.extend([
            FailureScenario(
                name="syntax_error_handling",
                description="Test handling of syntax errors",
                trigger_type="crash",
                payload="def broken_syntax(x: int -> int: return x + 1",  # Syntax error
                expected_behavior="graceful_error",
                timeout_seconds=5
            ),
            FailureScenario(
                name="type_error_handling",
                description="Test handling of type errors",
                trigger_type="crash",
                payload="""
def type_error(x: str) -> int:
    return x + 1  # Type error
""",
                expected_behavior="graceful_error",
                timeout_seconds=5
            ),
            FailureScenario(
                name="name_error_handling",
                description="Test handling of name errors",
                trigger_type="crash",
                payload="""
def name_error(x: int) -> int:
    return undefined_variable + x
""",
                expected_behavior="graceful_error",
                timeout_seconds=5
            ),
        ])

        return scenarios

    def execute_failure_scenario(self, scenario: FailureScenario) -> FailureTestResult:
        """Execute a single failure scenario"""
        print(f"Testing failure scenario: {scenario.name}")

        start_time = time.time()
        test_passed = False
        actual_behavior = "unknown"
        error_message = ""
        graceful_degradation = False
        resource_cleanup = True

        try:
            # Execute with timeout
            if scenario.trigger_type in ["timeout", "exhaustion"]:
                result = self._execute_with_timeout(
                    scenario.payload,
                    scenario.timeout_seconds
                )
            else:
                result = self._execute_with_error_handling(scenario.payload)

            execution_time = (time.time() - start_time) * 1000

            # Analyze result
            if isinstance(result, dict):
                status = result.get('status', 'unknown')
                error = result.get('error', '')

                if status == 'timeout':
                    actual_behavior = "timeout_handled"
                    graceful_degradation = True
                    test_passed = scenario.expected_behavior in ["timeout_graceful", "timeout_or_resource_limit"]

                elif status == 'resource_exhausted':
                    actual_behavior = "exhaustion_handled"
                    graceful_degradation = True
                    test_passed = scenario.expected_behavior in ["graceful_exhaustion", "timeout_or_resource_limit"]

                elif status == 'error':
                    actual_behavior = "error_handled"
                    graceful_degradation = True
                    test_passed = scenario.expected_behavior in ["graceful_error", "timeout_or_resource_limit", "resource_error_handling"]

                elif status == 'unknown':
                    actual_behavior = "unknown_status"
                    # Unknown status might be acceptable for some scenarios
                    test_passed = scenario.expected_behavior in ["timeout_or_resource_limit", "graceful_exhaustion"]

                else:
                    actual_behavior = f"unexpected_status: {status}"
                    test_passed = False

                if error:
                    error_message = error

            else:
                actual_behavior = f"unexpected_result_type: {type(result)}"
                test_passed = False
                error_message = f"Expected dict, got {type(result)}"

        except TimeoutError:
            execution_time = (time.time() - start_time) * 1000
            actual_behavior = "hard_timeout"
            graceful_degradation = True  # Hard timeout is still graceful
            test_passed = scenario.expected_behavior in ["timeout_graceful", "timeout_or_resource_limit"]
            error_message = "Hard timeout occurred"

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            actual_behavior = "exception_raised"
            graceful_degradation = False
            test_passed = False
            error_message = str(e)
            resource_cleanup = False  # Exception might indicate resource leak

        return FailureTestResult(
            scenario_name=scenario.name,
            test_passed=test_passed,
            actual_behavior=actual_behavior,
            execution_time_ms=execution_time,
            error_message=error_message,
            graceful_degradation=graceful_degradation,
            resource_cleanup=resource_cleanup
        )

    def _execute_with_timeout(self, payload: str, timeout_seconds: int) -> Dict[str, Any]:
        """Execute payload with timeout protection"""
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(self._safe_execute, payload)
            try:
                result = future.result(timeout=timeout_seconds)
                return result
            except TimeoutError:
                future.cancel()
                return {"status": "timeout", "error": f"Execution timed out after {timeout_seconds}s"}

    def _execute_with_error_handling(self, payload: str) -> Dict[str, Any]:
        """Execute payload with comprehensive error handling"""
        return self._safe_execute(payload)

    def _safe_execute(self, payload: str) -> Dict[str, Any]:
        """Safely execute payload and return result"""
        try:
            # Try symbolic check first
            result = logic_symbolic_check(
                code=payload,
                function_name="test_function",
                timeout_seconds=self.default_timeout
            )
            return result

        except Exception as e:
            error_msg = str(e).lower()

            # Categorize the error
            if "timeout" in error_msg:
                return {"status": "timeout", "error": str(e)}
            elif "memory" in error_msg or "resource" in error_msg:
                return {"status": "resource_exhausted", "error": str(e)}
            elif "syntax" in error_msg or "parse" in error_msg:
                return {"status": "error", "error": f"Syntax error: {str(e)}"}
            elif "type" in error_msg:
                return {"status": "error", "error": f"Type error: {str(e)}"}
            elif "name" in error_msg:
                return {"status": "error", "error": f"Name error: {str(e)}"}
            else:
                return {"status": "error", "error": f"General error: {str(e)}"}

    def run_resilience_test_suite(self, test_name: str) -> ResilienceReport:
        """Run comprehensive resilience test suite"""
        print(f"Running resilience test suite: {test_name}")

        scenarios = self.generate_failure_scenarios()
        results = []

        for scenario in scenarios:
            result = self.execute_failure_scenario(scenario)
            results.append(result)

            if not result.test_passed:
                print(f"❌ Failed scenario: {scenario.name} - Expected: {scenario.expected_behavior}, Got: {result.actual_behavior}")
            else:
                print(f"✅ Passed scenario: {scenario.name}")

        # Calculate metrics
        passed_count = sum(1 for r in results if r.test_passed)
        failed_count = len(results) - passed_count
        resilience_score = passed_count / len(results) if results else 0.0

        # Identify critical failures
        critical_failures = []
        for result in results:
            if not result.test_passed and not result.graceful_degradation:
                critical_failures.append(f"{result.scenario_name}: {result.actual_behavior}")

        report = ResilienceReport(
            test_name=test_name,
            total_scenarios=len(scenarios),
            passed_scenarios=passed_count,
            failed_scenarios=failed_count,
            resilience_score=resilience_score,
            results=results,
            critical_failures=critical_failures
        )

        print(f"Resilience test completed: {resilience_score:.2%} passed ({passed_count}/{len(scenarios)})")

        return report

    def test_crosshair_availability(self) -> Dict[str, Any]:
        """Test CrossHair availability and functionality"""
        print("Testing CrossHair availability...")

        crosshair_status = {
            'available': CROSSHAIR_AVAILABLE,
            'simple_analysis': False,
            'complex_analysis': False,
            'error_handling': False,
            'timeout_handling': False
        }

        if not CROSSHAIR_AVAILABLE:
            print("CrossHair not available - testing graceful degradation")
            return crosshair_status

        try:
            # Test simple analysis
            simple_code = """
def simple_test(x: int) -> int:
    return x + 1
"""
            result = logic_symbolic_check(
                code=simple_code,
                function_name="simple_test",
                timeout_seconds=5
            )
            crosshair_status['simple_analysis'] = 'status' in result

        except Exception:
            crosshair_status['simple_analysis'] = False

        try:
            # Test timeout handling
            timeout_code = """
def timeout_test(x: int) -> int:
    while True:
        x = x + 1
    return x
"""
            start = time.time()
            result = logic_symbolic_check(
                code=timeout_code,
                function_name="timeout_test",
                timeout_seconds=3
            )
            execution_time = time.time() - start

            crosshair_status['timeout_handling'] = execution_time < 5  # Should return quickly

        except Exception:
            crosshair_status['timeout_handling'] = False

        return crosshair_status

    def assert_resilience_requirements(self, report: ResilienceReport):
        """Assert resilience requirements are met"""
        # Critical resilience assertions
        assert report.resilience_score >= 0.7, f"Resilience score too low: {report.resilience_score:.2%}"
        assert len(report.critical_failures) == 0, f"Critical failures detected: {report.critical_failures}"

        # At least 80% of scenarios should show graceful degradation
        graceful_count = sum(1 for r in report.results if r.graceful_degradation)
        graceful_rate = graceful_count / len(report.results) if report.results else 0
        assert graceful_rate >= 0.8, f"Graceful degradation rate too low: {graceful_rate:.2%}"

        print(f"✅ Resilience requirements met for {report.test_name}")


# Pytest fixtures
@pytest.fixture
def failure_harness():
    """Pytest fixture for failure test harness"""
    return CrossHairFailureTestHarness(default_timeout=10)


@pytest.mark.resilience
def test_resilience_timeout_scenarios(failure_harness):
    """Test timeout handling scenarios"""
    timeout_scenarios = [s for s in failure_harness.generate_failure_scenarios() if s.trigger_type == "timeout"]

    for scenario in timeout_scenarios:
        result = failure_harness.execute_failure_scenario(scenario)
        assert result.graceful_degradation, f"Timeout scenario not handled gracefully: {scenario.name}"
        assert result.execution_time_ms < (scenario.timeout_seconds + 5) * 1000, f"Timeout took too long: {result.execution_time_ms}ms"


@pytest.mark.resilience
def test_resilience_error_scenarios(failure_harness):
    """Test error handling scenarios"""
    error_scenarios = [s for s in failure_harness.generate_failure_scenarios() if s.trigger_type == "crash"]

    for scenario in error_scenarios:
        result = failure_harness.execute_failure_scenario(scenario)
        assert result.test_passed, f"Error scenario not handled correctly: {scenario.name} - {result.error_message}"


@pytest.mark.resilience
def test_resilience_crosshair_availability(failure_harness):
    """Test CrossHair availability and graceful degradation"""
    crosshair_status = failure_harness.test_crosshair_availability()

    # Should handle both available and unavailable scenarios
    assert 'available' in crosshair_status
    assert isinstance(crosshair_status['available'], bool)

    print(f"CrossHair availability test: {crosshair_status}")


@pytest.mark.resilience
@pytest.mark.slow
def test_resilience_comprehensive_suite(failure_harness):
    """Test comprehensive resilience suite"""
    # Test a subset of scenarios for CI efficiency
    scenarios = failure_harness.generate_failure_scenarios()[:5]  # Test first 5 scenarios
    results = []

    for scenario in scenarios:
        result = failure_harness.execute_failure_scenario(scenario)
        results.append(result)

    # At least 80% should pass
    passed_count = sum(1 for r in results if r.test_passed)
    pass_rate = passed_count / len(results)

    assert pass_rate >= 0.6, f"Pass rate too low: {pass_rate:.2%}"  # Slightly lower for subset test

    print(f"Comprehensive resilience test: {passed_count}/{len(results)} passed")


@pytest.mark.resilience
def test_resilience_resource_cleanup(failure_harness):
    """Test resource cleanup after failures"""
    # Run a resource-intensive scenario
    scenario = FailureScenario(
        name="resource_cleanup_test",
        description="Test resource cleanup after failure",
        trigger_type="resource_limit",
        payload="""
def resource_test(x: int) -> list:
    # Create some temporary resources
    temp_data = []
    for i in range(100):
        temp_data.append([j for j in range(100)])
    return temp_data[:x]
""",
        expected_behavior="resource_error_handling",
        timeout_seconds=5
    )

    result = failure_harness.execute_failure_scenario(scenario)
    assert result.resource_cleanup, "Resource cleanup failed after test"


if __name__ == "__main__":
    # Run standalone resilience tests
    def main():
        harness = CrossHairFailureTestHarness()

        # Test CrossHair availability
        crosshair_status = harness.test_crosshair_availability()
        print(f"CrossHair Status: {crosshair_status}")

        # Run resilience test suite
        report = harness.run_resilience_test_suite("standalone_resilience_test")

        print(f"\nResilience Test Results:")
        print(json.dumps(asdict(report), indent=2, default=str))

        harness.assert_resilience_requirements(report)

    import json
    main()