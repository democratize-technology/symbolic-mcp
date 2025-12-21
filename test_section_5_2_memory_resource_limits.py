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
COMPREHENSIVE TEST SUITE - Section 5.2 Memory and Resource Limits

CRITICAL REQUIREMENTS FROM SECTION 5.2:
1. Memory limit: 2GB for Z3 solver via resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, -1))
2. CPU time limits for analysis
3. Path exploration limits to prevent infinite loops
4. Proper cleanup and resource management

CURRENT IMPLEMENTATION ISSUES:
- Missing memory limits for Z3 solver
- Missing resource.setrlimit calls as specified in Section 5.2
- No resource management for symbolic execution
- Missing protection against resource exhaustion attacks

TEST STRATEGY: Write failing tests first, then implement to pass tests
"""

import pytest
import resource
import threading
import time
import tempfile
import os
import signal
from unittest.mock import patch, MagicMock
import subprocess
import sys

# Import the functions we need to test
from main import (
    logic_symbolic_check,
    logic_find_path_to_exception,
    logic_analyze_branches,
    logic_compare_functions,
    set_memory_limit
)


class TestSection52MemoryLimits:
    """Test EXACT Section 5.2 specification requirements for memory limits"""

    def test_memory_limit_setrlimit_exact_specification(self):
        """
        CRITICAL TEST: Verify exact Section 5.2 specification
        resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, -1))  # 2GB

        This test FAILS until the exact specification is implemented.
        """
        # Mock the system to avoid platform-specific limitations
        with patch('resource.getrlimit') as mock_getrlimit, \
             patch('resource.setrlimit') as mock_setrlimit:

            # Mock current limits as unlimited (common on macOS)
            mock_getrlimit.return_value = (9223372036854775807, 9223372036854775807)

            # Set memory limit using current implementation
            set_memory_limit()

            # EXACT SPECIFICATION: Should call with 2GB soft limit, unlimited hard limit
            expected_call = ((resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, -1)),)

            # FAILING TEST: Should call setrlimit with exact Section 5.2 parameters
            assert mock_setrlimit.called, "resource.setrlimit must be called"
            assert mock_setrlimit.call_args == expected_call, \
                f"Expected call with 2GB limit and unlimited hard limit, got: {mock_setrlimit.call_args}"

    def test_memory_limit_called_during_symbolic_execution(self):
        """
        Test that resource.setrlimit is called during symbolic execution
        This test FAILS until memory limits are properly integrated
        """
        with patch('resource.setrlimit') as mock_setrlimit:
            # Execute symbolic analysis
            code = """
def test_func(x: int) -> int:
    if x > 1000:
        return x
    return 0
"""
            result = logic_symbolic_check(code=code, function_name="test_func", timeout_seconds=5)

            # FAILING TEST: resource.setrlimit should be called with exact Section 5.2 parameters
            expected_call_args = [
                ((resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, -1)),)
            ]

            # Verify setrlimit was called with correct parameters
            assert mock_setrlimit.called, "resource.setrlimit must be called during symbolic execution"
            assert mock_setrlimit.call_args_list == expected_call_args, \
                f"Expected call with 2GB limit, got: {mock_setrlimit.call_args_list}"

    def test_memory_limit_enforcement_z3_solver(self):
        """
        Test that Z3 solver memory usage is limited to 2GB
        This test FAILS until Z3 memory limits are implemented
        """
        # Code that would cause Z3 to use excessive memory if unlimited
        memory_intensive_code = """
def memory_intensive(data):
    # Create complex conditions that could cause Z3 memory explosion
    result = []
    for i in range(100):
        if data[i] > 0 and data[i] < 1000 and data[i] % 2 == 0 and data[i] % 3 == 0:
            if data[i] % 5 == 0 and data[i] % 7 == 0 and data[i] % 11 == 0:
                if data[i] % 13 == 0 and data[i] % 17 == 0 and data[i] % 19 == 0:
                    if data[i] % 23 == 0 and data[i] % 29 == 0 and data[i] % 31 == 0:
                        result.append(data[i])
    return result
"""

        # Track memory usage before and after analysis
        initial_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        # Execute symbolic analysis
        result = logic_symbolic_check(code=memory_intensive_code, function_name="memory_intensive", timeout_seconds=10)

        # Check memory usage after analysis
        final_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        memory_used = final_memory - initial_memory

        # FAILING TEST: Memory usage should be limited (2GB = 2,147,483,648 bytes)
        # In practice, we should see much less usage if limits are working
        max_allowed_memory = 2 * 1024 * 1024 * 1024  # 2GB

        # Note: ru_maxrss is in KB on macOS, bytes on Linux
        if sys.platform == "darwin":
            max_allowed_memory = max_allowed_memory / 1024  # Convert to KB for macOS

        assert memory_used < max_allowed_memory, \
            f"Memory usage ({memory_used}) exceeds 2GB limit ({max_allowed_memory})"

    def test_memory_usage_monitoring_and_reporting(self):
        """
        Test that memory usage is monitored and reported during analysis
        This test FAILS until memory monitoring is implemented
        """
        code = """
def simple_func(x: int) -> int:
    return x * 2
"""

        result = logic_symbolic_check(code=code, function_name="simple_func", timeout_seconds=5)

        # FAILING TEST: Result should include memory usage information
        assert "memory_usage_mb" in result, "Result should include memory_usage_mb field"
        assert "memory_limit_mb" in result, "Result should include memory_limit_mb field"
        assert isinstance(result["memory_usage_mb"], (int, float)), "memory_usage_mb should be numeric"
        assert result["memory_limit_mb"] == 2048, "Memory limit should be 2048MB (2GB)"

    def test_memory_limit_error_handling(self):
        """
        Test proper error handling when memory limits are exceeded
        This test FAILS until proper error handling is implemented
        """
        # Create code that might exceed memory limits
        large_search_code = """
def large_search(data):
    for i in range(len(data)):
        for j in range(len(data)):
            if i != j and data[i] == data[j] and data[i] > 1000000:
                return i, j
    return None
"""

        result = logic_symbolic_check(code=large_search_code, function_name="large_search", timeout_seconds=5)

        # FAILING TEST: Should handle memory limit exceeded gracefully
        assert result["status"] in ["memory_limit_exceeded", "timeout", "analysis_complete"], \
            f"Should handle memory limits gracefully, got status: {result['status']}"

        if result["status"] == "memory_limit_exceeded":
            assert "error" in result, "Should include error message for memory limit exceeded"


class TestSection52ResourceManagement:
    """Test Section 5.2 resource management requirements"""

    def test_cpu_time_limits(self):
        """
        Test CPU time limits for analysis
        This test FAILS until CPU time limits are implemented
        """
        with patch('resource.setrlimit') as mock_setrlimit:
            code = """
def endless_loop():
    x = 1
    while True:
        x = x + 1
"""

            result = logic_symbolic_check(code=code, function_name="endless_loop", timeout_seconds=2)

            # FAILING TEST: Should set CPU time limits
            cpu_limit_calls = [call for call in mock_setrlimit.call_args_list
                             if call[0][0] == resource.RLIMIT_CPU]

            assert len(cpu_limit_calls) > 0, "Should set CPU time limits"
            # Should limit to slightly more than timeout to allow cleanup
            cpu_limit = cpu_limit_calls[0][0][1][0]  # Get soft limit
            assert cpu_limit <= 5, f"CPU limit should be reasonable, got {cpu_limit}"

    def test_path_exploration_limits(self):
        """
        Test path exploration limits to prevent infinite loops
        This test FAILS until path limits are implemented
        """
        # Code with many possible paths
        path_intensive_code = """
def many_paths(x):
    if x > 0:
        if x > 10:
            if x > 20:
                if x > 30:
                    if x > 40:
                        return "high"
                    else:
                        return "mid_high"
                else:
                    return "mid"
            else:
                return "low_mid"
        else:
            return "low"
    else:
        return "negative"
"""

        result = logic_analyze_branches(code=code, function_name="many_paths", timeout_seconds=5)

        # FAILING TEST: Should limit path exploration
        assert "paths_explored" in result, "Should report number of paths explored"
        assert "max_paths_limit" in result, "Should report maximum paths limit"
        assert result["paths_explored"] <= result["max_paths_limit"], \
            f"Paths explored ({result['paths_explored']}) should not exceed limit ({result['max_paths_limit']})"

    def test_resource_cleanup_after_analysis(self):
        """
        Test proper resource cleanup after analysis completion
        This test FAILS until cleanup is implemented
        """
        # Track resource usage before analysis
        initial_fds = len(os.listdir("/proc/self/fd")) if os.path.exists("/proc/self/fd") else 0
        initial_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        code = """
def cleanup_test(x):
    return x + 1
"""

        # Execute multiple analyses to test cleanup
        for i in range(5):
            result = logic_symbolic_check(code=code, function_name="cleanup_test", timeout_seconds=2)

        # Check resource usage after analyses
        final_fds = len(os.listdir("/proc/self/fd")) if os.path.exists("/proc/self/fd") else 0
        final_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss

        # FAILING TEST: Should properly clean up resources
        fd_leak = final_fds - initial_fds
        memory_growth = final_memory - initial_memory

        assert fd_leak <= 2, f"Should not leak file descriptors, leaked: {fd_leak}"
        assert memory_growth < 100 * 1024, f"Should not have excessive memory growth: {memory_growth}KB"

    def test_timeout_protection_with_resource_limits(self):
        """
        Test that timeouts work properly with resource limits
        This test FAILS until timeout + resource limit integration is implemented
        """
        # Code that might hang or use excessive resources
        hanging_code = """
def potential_hang():
    import time
    # This could cause infinite symbolic exploration
    data = list(range(1000))
    for i in range(len(data)):
        for j in range(len(data)):
            if data[i] == data[j] and i != j:
                return True
    return False
"""

        start_time = time.time()
        result = logic_symbolic_check(code=hanging_code, function_name="potential_hang", timeout_seconds=3)
        elapsed_time = time.time() - start_time

        # FAILING TEST: Should respect timeout even with resource limits
        assert elapsed_time < 10, f"Should complete within reasonable time, took {elapsed_time:.2f}s"
        assert result["status"] in ["timeout", "analysis_complete", "resource_limited"], \
            f"Should handle timeout gracefully, got: {result['status']}"


class TestSection52ComplianceOverall:
    """Test overall Section 5.2 compliance"""

    def test_exact_section_52_implementation(self):
        """
        Overall test for EXACT Section 5.2 specification compliance

        EXACT SPECIFICATION REQUIREMENTS:
        1. Memory limit: 2GB for Z3 solver
        2. resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, -1))
        3. CPU time limits for analysis
        4. Path exploration limits to prevent infinite loops
        5. Proper cleanup and resource management

        This test FAILS until all requirements are exactly implemented.
        """
        with patch('resource.setrlimit') as mock_setrlimit:
            with patch('resource.getrusage') as mock_getrusage:
                # Mock memory usage reporting
                mock_getrusage.return_value.ru_maxrss = 50000  # 50MB

                code = """
def section_52_test(x: int) -> int:
    if x > 100:
        return x * 2
    return x
"""

                result = logic_symbolic_check(code=code, function_name="section_52_test", timeout_seconds=5)

                # EXACT SPECIFICATION: Memory limit must be 2GB with unlimited hard limit
                expected_memory_call = ((resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, -1)),)

                # FAILING TEST: Must implement exact Section 5.2 specification
                assert expected_memory_call in mock_setrlimit.call_args_list, \
                    f"Must call resource.setrlimit with exact 2GB limit: {expected_memory_call}"

                # Must include memory monitoring
                assert "memory_usage_mb" in result, "Must monitor and report memory usage"
                assert "memory_limit_mb" in result, "Must report memory limit"

                # Must include resource management
                assert result.get("memory_limit_mb") == 2048, "Memory limit should be 2048MB (2GB)"

    def test_backward_compatibility_with_resource_limits(self):
        """
        Test that resource limits don't break existing functionality
        This test FAILS until resource limits are properly integrated
        """
        code = """
def compatible_function(x: int, y: int) -> int:
    if x > 0 and y > 0:
        return x + y
    return 0
"""

        # Should still find counterexamples with resource limits
        result = logic_find_path_to_exception(
            code=code,
            function_name="compatible_function",
            exception_type="ValueError",
            timeout_seconds=5
        )

        # FAILING TEST: Existing functionality should work with resource limits
        assert result["status"] in ["found", "unreachable", "analysis_complete"], \
            f"Should maintain compatibility, got status: {result['status']}"

        if "memory_usage_mb" in result:
            assert result["memory_usage_mb"] >= 0, "Memory usage should be non-negative"
            assert result["memory_limit_mb"] == 2048, "Should have 2GB limit"


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "--tb=short"])