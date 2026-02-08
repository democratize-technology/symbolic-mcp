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
Simplified Mock Implementations for Integration Testing

This module provides concrete mock implementations for testing without
abstract base class or protocol overhead.
"""

from dataclasses import dataclass  # noqa: E402
from enum import Enum  # noqa: E402
from typing import Any, Dict, List, Optional  # noqa: E402


class ImportSecurityLevel(Enum):
    """Security level for import operations"""

    ALLOWED = "allowed"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"


@dataclass
class ImportResult:
    """Result of an import operation"""

    module_name: str
    security_level: ImportSecurityLevel
    success: bool
    error_message: Optional[str] = None
    execution_time_ms: float = 0.0


@dataclass
class SymbolicAnalysisResult:
    """Result of symbolic analysis operations"""

    status: str
    function_name: str
    analysis_time_seconds: float
    findings: List[str]
    paths_found: int
    counterexamples: List[Dict[str, Any]]
    errors: List[str]
    metadata: Dict[str, Any]


class MockSecurityValidator:
    """Mock security validator for testing"""

    def __init__(self, allowed_modules: List[str] = None):
        self.allowed_modules = allowed_modules or ["math", "json", "datetime", "typing"]

    def validate_import(self, module_name: str) -> ImportResult:
        is_allowed = module_name in self.allowed_modules
        return ImportResult(
            module_name=module_name,
            security_level=(
                ImportSecurityLevel.ALLOWED
                if is_allowed
                else ImportSecurityLevel.BLOCKED
            ),
            success=is_allowed,
            error_message=None if is_allowed else f"Module '{module_name}' not allowed",
        )

    def is_module_allowed(self, module_name: str) -> bool:
        return module_name in self.allowed_modules

    def get_allowed_modules(self) -> List[str]:
        return self.allowed_modules.copy()

    def check_code_security(self, code: str) -> List[str]:
        # Simple mock security check
        dangerous_patterns = ["import os", "import sys", "subprocess", "__import__"]
        issues = []
        for pattern in dangerous_patterns:
            if pattern in code:
                issues.append(f"Dangerous pattern detected: {pattern}")
        return issues


class MockRestrictedImporter:
    """Mock restricted importer for testing"""

    def __init__(self, security_validator: MockSecurityValidator = None):
        self.security_validator = security_validator or MockSecurityValidator()
        self.access_attempts = []

    def validate_module_access(self, module_name: str) -> bool:
        self.access_attempts.append(module_name)
        return self.security_validator.is_module_allowed(module_name)

    def create_restricted_importer(self):
        return self

    def monitor_module_access(self) -> Dict[str, Any]:
        return {
            "access_attempts": self.access_attempts.copy(),
            "blocked_attempts": [
                m
                for m in self.access_attempts
                if not self.security_validator.is_module_allowed(m)
            ],
            "total_attempts": len(self.access_attempts),
        }


class MockSymbolicAnalyzer:
    """Mock symbolic analyzer for testing"""

    def analyze_function(
        self, code: str, function_name: str, timeout_seconds: int
    ) -> SymbolicAnalysisResult:
        return SymbolicAnalysisResult(
            status="mock_complete",
            function_name=function_name,
            analysis_time_seconds=0.1,
            findings=[f"Mock analysis of {function_name}"],
            paths_found=3,
            counterexamples=[{"input": "mock_input", "result": "mock_result"}],
            errors=[],
            metadata={"mock": True, "timeout": timeout_seconds},
        )

    def find_exception_paths(
        self, code: str, function_name: str, exception_type: str, timeout_seconds: int
    ) -> SymbolicAnalysisResult:
        return SymbolicAnalysisResult(
            status="mock_complete",
            function_name=function_name,
            analysis_time_seconds=0.1,
            findings=[f"Mock exception analysis for {exception_type}"],
            paths_found=2,
            counterexamples=[{"input": "mock_input", "exception": exception_type}],
            errors=[],
            metadata={"mock": True, "exception_type": exception_type},
        )

    def compare_functions(
        self, code: str, function_a: str, function_b: str, timeout_seconds: int
    ) -> SymbolicAnalysisResult:
        return SymbolicAnalysisResult(
            status="mock_equal",
            function_name=function_a,
            analysis_time_seconds=0.1,
            findings=[f"Mock comparison of {function_a} and {function_b}"],
            paths_found=1,
            counterexamples=[],
            errors=[],
            metadata={
                "mock": True,
                "functions": [function_a, function_b],
                "equivalent": True,
            },
        )

    def analyze_branches(
        self, code: str, function_name: str, timeout_seconds: int
    ) -> SymbolicAnalysisResult:
        return SymbolicAnalysisResult(
            status="mock_complete",
            function_name=function_name,
            analysis_time_seconds=0.1,
            findings=[f"Mock branch analysis of {function_name}"],
            paths_found=4,
            counterexamples=[],
            errors=[],
            metadata={"mock": True, "branches": ["if", "else", "elif"]},
        )


class MockMemoryManager:
    """Mock memory manager for testing"""

    def __init__(self):
        self.memory_limit_mb = 2048
        self.current_usage_mb = 512.0

    def set_memory_limit(self, limit_mb: int) -> bool:
        self.memory_limit_mb = limit_mb
        return True

    def get_memory_usage(self) -> Dict[str, float]:
        return {
            "current_usage_mb": self.current_usage_mb,
            "limit_mb": self.memory_limit_mb,
            "usage_percent": (self.current_usage_mb / self.memory_limit_mb) * 100,
        }

    def check_memory_limit_exceeded(self) -> bool:
        return self.current_usage_mb > self.memory_limit_mb

    def cleanup_memory(self) -> bool:
        # Simulate memory cleanup
        self.current_usage_mb *= 0.8
        return True


class MockProcessIsolation:
    """Mock process isolation for testing"""

    def __init__(self):
        self.created_processes = {}
        self.next_process_id = 1000

    def create_isolated_process(
        self, code: str, timeout_seconds: int
    ) -> Dict[str, Any]:
        process_id = self.next_process_id
        self.next_process_id += 1

        self.created_processes[process_id] = {
            "code": code,
            "timeout": timeout_seconds,
            "status": "mock_completed",
            "output": "mock_output",
        }

        return {
            "process_id": process_id,
            "status": "completed",
            "execution_time": 0.1,
            "output": "mock_output",
        }

    def monitor_process_resources(self, process_id: int) -> Dict[str, Any]:
        if process_id in self.created_processes:
            return {
                "process_id": process_id,
                "cpu_percent": 25.0,
                "memory_mb": 128.0,
                "status": self.created_processes[process_id]["status"],
            }
        return {"error": "Process not found"}

    def terminate_process(self, process_id: int, force: bool = False) -> bool:
        if process_id in self.created_processes:
            self.created_processes[process_id]["status"] = "terminated"
            return True
        return False

    def cleanup_isolated_resources(self) -> bool:
        self.created_processes.clear()
        return True
