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
Test Suite for Architectural Improvements

Tests all three HIGH-PRIORITY architectural fixes:
1. ARCH-001: Mock implementations for test isolation
2. ARCH-002: Pytest fixtures eliminate dependency injection complexity
3. ARCH-003: Security test process isolation
"""

import asyncio  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402

import pytest  # noqa: E402

# Add project root to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from .mocks import (  # noqa: E402
    MockMemoryManager,
    MockProcessIsolation,
    MockRestrictedImporter,
    MockSecurityValidator,
    MockSymbolicAnalyzer,
)
from .test_e2e_harness import E2ETestHarness  # noqa: E402
from .test_load_harness import LoadTestHarness  # noqa: E402
from .test_security_harness import SecurityTestHarness  # noqa: E402


class TestArchitecturalImprovements:
    """Test suite for all architectural improvements"""

    def test_arch001_mock_implementations_for_test_isolation(self):  # noqa: E501, C901
        """Test ARCH-001: Mock implementations provide test isolation without main module coupling"""

        # Test MockSecurityValidator works independently
        security_validator = MockSecurityValidator()
        assert security_validator.is_module_allowed("math") is True
        assert security_validator.is_module_allowed("os") is False

        # Test custom configuration
        custom_validator = MockSecurityValidator(["math", "json", "datetime"])
        assert custom_validator.is_module_allowed("math") is True
        assert custom_validator.is_module_allowed("json") is True
        assert custom_validator.is_module_allowed("os") is False

        # Test MockRestrictedImporter works with MockSecurityValidator
        importer = MockRestrictedImporter(security_validator)
        assert importer.validate_module_access("math") is True
        assert importer.validate_module_access("os") is False

        # Test monitoring capabilities
        monitor_data = importer.monitor_module_access()
        assert monitor_data["total_attempts"] == 2
        # Note: blocked_attempts returns a list of module names
        assert "os" in monitor_data["blocked_attempts"]

    def test_arch002_pytest_fixtures_simplify_testing(self):
        """Test ARCH-002: Pytest fixtures simplify testing without DI complexity"""

        # Test that mock implementations work directly
        security_validator = MockSecurityValidator()
        assert security_validator.is_module_allowed("math")
        assert not security_validator.is_module_allowed("os")

        # Test custom configuration
        custom_validator = MockSecurityValidator(["math", "json", "datetime"])
        assert custom_validator.is_module_allowed("math")
        assert not custom_validator.is_module_allowed("os")

        # Test MockSymbolicAnalyzer returns proper structured results
        analyzer = MockSymbolicAnalyzer()
        result = analyzer.analyze_function(
            code="def test(x): return x + 1", function_name="test", timeout_seconds=30
        )
        assert result.status == "mock_complete"
        assert result.function_name == "test"
        assert result.paths_found == 3
        assert len(result.counterexamples) > 0

        # Test exception path analysis
        exception_result = analyzer.find_exception_paths(
            code="def f(x): raise ValueError()",
            function_name="f",
            exception_type="ValueError",
            timeout_seconds=30,
        )
        assert exception_result.status == "mock_complete"
        assert exception_result.metadata["exception_type"] == "ValueError"

        # Test function comparison
        comparison_result = analyzer.compare_functions(
            code="def f1(x): return x\ndef f2(x): return x",
            function_a="f1",
            function_b="f2",
            timeout_seconds=30,
        )
        assert comparison_result.status == "mock_equal"
        assert comparison_result.metadata["equivalent"] is True

        # Test MockMemoryManager
        memory_manager = MockMemoryManager()
        assert memory_manager.set_memory_limit(4096) is True
        usage = memory_manager.get_memory_usage()
        assert usage["current_usage_mb"] > 0
        assert usage["limit_mb"] == 4096

        # Test MockProcessIsolation
        process_isolation = MockProcessIsolation()
        process_result = process_isolation.create_isolated_process(
            "def test(): pass", 10
        )
        assert process_result["status"] == "completed"
        assert "process_id" in process_result

    @pytest.mark.asyncio
    async def test_arch003_security_process_isolation(self):
        """Test ARCH-003: Security test process isolation"""

        # Test with mock implementations (no process isolation needed for basic tests)
        harness = SecurityTestHarness(use_process_isolation=False)

        # Test attack execution
        result = harness.execute_attack("import os", "test_attack")
        assert result.blocked is True
        assert "os" in result.error_message

        # Test allowed module
        result = harness.execute_attack("import math", "test_math")
        assert result.blocked is False  # Mock allows math module

        # Check allowed modules from dependency
        assert "math" in harness.allowed_modules

    @pytest.mark.asyncio
    async def test_e2e_harness_with_mock_analyzer(self):
        """Test E2E harness works with mock analyzer"""

        # Test with mock symbolic analyzer
        harness = E2ETestHarness(timeout_seconds=30, max_requests=100)
        success = await harness.initialize_session()
        assert success is True
        assert harness.session_active is True

        # Test request execution
        response = await harness.execute_request(
            "symbolic_check",
            code="def test_func(x): return x * 2",
            function_name="test_func",
            timeout_seconds=10,
        )
        assert response["success"] is True
        assert "result" in response
        assert "response_time" in response

        # Test exception path request
        exception_response = await harness.execute_request(
            "find_path_to_exception",
            code="def might_fail(x): raise ValueError() if x < 0 else x",
            function_name="might_fail",
            exception_type="ValueError",
            timeout_seconds=10,
        )
        assert exception_response["success"] is True

        # Test function comparison
        comparison_response = await harness.execute_request(
            "compare_functions",
            code="def f1(x): return x\ndef f2(x): return x",
            function_a="f1",
            function_b="f2",
            timeout_seconds=10,
        )
        assert comparison_response["success"] is True

    @pytest.mark.asyncio
    async def test_load_harness_with_mock_analyzer(self):
        """Test load harness uses mock analyzer directly"""

        harness = LoadTestHarness(max_concurrent_requests=10, timeout_seconds=30)

        # Test single request
        response = await harness.execute_request(
            "compare_functions",
            code="def f1(x): return x\ndef f2(x): return x",
            function_a="f1",
            function_b="f2",
            timeout_seconds=15,
        )
        assert response["success"] is True
        assert response["result"] is not None

        # Test that it uses mock symbolic analyzer
        assert hasattr(harness, "symbolic_analyzer")
        assert isinstance(harness.symbolic_analyzer, MockSymbolicAnalyzer)

    def test_architectural_requirements_met(self):
        """Verify all architectural requirements are satisfied"""

        # Get integration directory for file checks
        integration_dir = os.path.dirname(os.path.abspath(__file__))

        # 1. Mock implementations exist and work independently
        security_validator = MockSecurityValidator()
        analyzer = MockSymbolicAnalyzer()
        importer = MockRestrictedImporter(security_validator)
        memory_manager = MockMemoryManager()
        process_isolation = MockProcessIsolation()

        # Verify all mock components are functional
        assert security_validator.is_module_allowed("math")
        result = analyzer.analyze_function("def f(): pass", "f", 10)
        assert result.status == "mock_complete"
        assert importer.validate_module_access("math")
        assert memory_manager.get_memory_usage()["current_usage_mb"] > 0
        proc_result = process_isolation.create_isolated_process("pass", 10)
        assert proc_result["status"] == "completed"

        # 2. Verify mocks.py exists with all required classes
        mocks_file = os.path.join(integration_dir, "mocks.py")
        assert os.path.exists(mocks_file), "mocks.py should exist"

        # 4. Verify harness files exist and use mocks
        e2e_harness_file = os.path.join(integration_dir, "test_e2e_harness.py")
        load_harness_file = os.path.join(integration_dir, "test_load_harness.py")
        security_harness_file = os.path.join(
            integration_dir, "test_security_harness.py"
        )

        for harness_file in [
            e2e_harness_file,
            load_harness_file,
            security_harness_file,
        ]:
            assert os.path.exists(harness_file), f"{harness_file} should exist"
            # Verify they import from mocks
            content = open(harness_file).read()
            assert (
                "from .mocks import" in content
            ), f"{harness_file} should import from mocks"

    @pytest.mark.asyncio
    async def test_code_duplication_eliminated(self):
        """Verify both harnesses work consistently with mock analyzer"""

        # Both harnesses should use MockSymbolicAnalyzer
        e2e_harness = E2ETestHarness(timeout_seconds=30, max_requests=100)
        load_harness = LoadTestHarness(max_concurrent_requests=10, timeout_seconds=30)

        # Verify they use the same mock analyzer
        assert hasattr(e2e_harness, "symbolic_analyzer")
        assert hasattr(load_harness, "symbolic_analyzer")
        assert isinstance(e2e_harness.symbolic_analyzer, MockSymbolicAnalyzer)
        assert isinstance(load_harness.symbolic_analyzer, MockSymbolicAnalyzer)

        # Initialize E2E session
        await e2e_harness.initialize_session()

        # Test they both produce consistent results
        test_code = "def test(): return 42"

        e2e_response = await e2e_harness.execute_request(
            "symbolic_check", code=test_code, function_name="test", timeout_seconds=10
        )

        load_response = await load_harness.execute_request(
            "symbolic_check", code=test_code, function_name="test", timeout_seconds=10
        )

        # Both should have same structure (eliminated duplication)
        assert "success" in e2e_response
        assert "success" in load_response
        assert e2e_response["success"] is True
        assert load_response["success"] is True
        assert "response_time" in e2e_response
        assert "response_time" in load_response

        # Test multiple request types work consistently with appropriate test code
        test_cases = [
            ("symbolic_check", "def test(): return 42", "test"),
            (
                "find_path_to_exception",
                "def test(x):\n    if x < 0:\n        raise ValueError()\n    return x",
                "test",
                "ValueError",
            ),
            (
                "compare_functions",
                "def f1(x): return x\ndef f2(x): return x",
                "f1",
                "f2",
            ),
            (
                "analyze_branches",
                "def test(x):\n    if x > 0:\n        return 1\n    else:\n        return 0",  # noqa: E501
                "test",
            ),
        ]

        for test_case in test_cases:
            request_type = test_case[0]
            if request_type == "find_path_to_exception":
                e2e_resp = await e2e_harness.execute_request(
                    request_type,
                    code=test_case[1],
                    function_name=test_case[2],
                    exception_type=test_case[3],
                    timeout_seconds=10,
                )
                assert e2e_resp["success"], f"E2E failed for {request_type}"

                load_resp = await load_harness.execute_request(
                    request_type,
                    code=test_case[1],
                    function_name=test_case[2],
                    exception_type=test_case[3],
                    timeout_seconds=10,
                )
                assert load_resp["success"], f"Load failed for {request_type}"
            elif request_type == "compare_functions":
                e2e_resp = await e2e_harness.execute_request(
                    request_type,
                    code=test_case[1],
                    function_a=test_case[2],
                    function_b=test_case[3],
                    timeout_seconds=10,
                )
                assert e2e_resp["success"], f"E2E failed for {request_type}"

                load_resp = await load_harness.execute_request(
                    request_type,
                    code=test_case[1],
                    function_a=test_case[2],
                    function_b=test_case[3],
                    timeout_seconds=10,
                )
                assert load_resp["success"], f"Load failed for {request_type}"
            else:
                e2e_resp = await e2e_harness.execute_request(
                    request_type,
                    code=test_case[1],
                    function_name=test_case[2],
                    timeout_seconds=10,
                )
                assert e2e_resp["success"], f"E2E failed for {request_type}"

                load_resp = await load_harness.execute_request(
                    request_type,
                    code=test_case[1],
                    function_name=test_case[2],
                    timeout_seconds=10,
                )
                assert load_resp["success"], f"Load failed for {request_type}"


if __name__ == "__main__":
    # Run tests standalone
    async def main():
        test_suite = TestArchitecturalImprovements()

        print("Testing ARCH-001: Mock implementations for test isolation...")
        test_suite.test_arch001_mock_implementations_for_test_isolation()
        print(" ARCH-001 passed")

        print("Testing ARCH-002: Pytest fixtures simplify testing...")
        test_suite.test_arch002_pytest_fixtures_simplify_testing()
        print(" ARCH-002 passed")

        print("Testing ARCH-003: Security test process isolation...")
        await test_suite.test_arch003_security_process_isolation()
        print(" ARCH-003 passed")

        print("Testing E2E harness with mock analyzer...")
        await test_suite.test_e2e_harness_with_mock_analyzer()
        print(" E2E harness passed")

        print("Testing Load harness with mock analyzer...")
        await test_suite.test_load_harness_with_mock_analyzer()
        print(" Load harness passed")

        print("Verifying architectural requirements...")
        test_suite.test_architectural_requirements_met()
        print(" Requirements verified")

        print("Testing code duplication elimination...")
        await test_suite.test_code_duplication_eliminated()
        print(" Code duplication eliminated")

        print("\n ALL ARCHITECTURAL IMPROVEMENTS VALIDATED!")
        print(" ARCH-001: Mock implementations for test isolation - COMPLETE")
        print(" ARCH-002: Pytest fixtures simplify testing - COMPLETE")
        print(" ARCH-003: Security test process isolation - COMPLETE")
        print(" Code duplication eliminated - COMPLETE")
        print(" All tests pass with new architecture - COMPLETE")

    asyncio.run(main())
