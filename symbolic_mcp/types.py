# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Symbolic MCP Contributors

"""Type definitions for symbolic execution results.

This module contains all TypedDict definitions used throughout
the symbolic execution server for structured result types.
"""

from typing import Literal, NotRequired, Optional

from typing_extensions import TypedDict


class _Counterexample(TypedDict):
    """A counterexample found during symbolic execution."""

    args: dict[str, int | bool | None | str]
    kwargs: dict[str, int | bool | None | str]
    violation: str
    actual_result: str
    path_condition: str


class _SymbolicCheckResult(TypedDict):
    """Result of symbolic execution analysis."""

    status: Literal["verified", "counterexample", "timeout", "error"]
    counterexamples: list[_Counterexample]
    paths_explored: int
    paths_verified: int
    time_seconds: float
    coverage_estimate: float
    error_type: NotRequired[str]
    message: NotRequired[str]


class _ValidationResult(TypedDict):
    """Result of code validation."""

    valid: bool
    error: NotRequired[str]
    error_type: NotRequired[str]


class _ExceptionPathResult(TypedDict):
    """Result of finding a path to an exception."""

    status: Literal["found", "unreachable", "error"]
    triggering_inputs: NotRequired[list[_Counterexample]]
    paths_to_exception: NotRequired[int]
    total_paths_explored: NotRequired[int]
    time_seconds: NotRequired[float]
    error_type: NotRequired[str]
    message: NotRequired[str]


class _FunctionComparisonResult(TypedDict):
    """Result of comparing two functions."""

    status: Literal["equivalent", "different", "error"]
    distinguishing_input: NotRequired[Optional[_Counterexample]]
    paths_compared: NotRequired[int]
    confidence: NotRequired[str]
    error_type: NotRequired[str]
    message: NotRequired[str]


class _BranchInfo(TypedDict):
    """Information about a branch."""

    line: int
    condition: str
    true_reachable: Optional[bool]
    false_reachable: Optional[bool]
    true_example: Optional[str]
    false_example: Optional[str]


class _BranchAnalysisResult(TypedDict):
    """Result of branch analysis."""

    status: Literal["complete", "error"]
    branches: NotRequired[list[_BranchInfo]]
    total_branches: NotRequired[int]
    reachable_branches: NotRequired[int]
    dead_code_lines: NotRequired[list[int]]
    cyclomatic_complexity: NotRequired[int]
    time_seconds: NotRequired[float]
    analysis_mode: NotRequired[Literal["static", "symbolic"]]
    error_type: NotRequired[str]
    message: NotRequired[str]
    line: NotRequired[int]


class _HealthCheckResult(TypedDict):
    """Result of health check."""

    status: Literal["healthy"]
    version: str
    python_version: str
    crosshair_version: Optional[str]
    z3_version: Optional[str]
    platform: str
    memory_usage_mb: float


class _ToolDescription(TypedDict):
    """Description of an MCP tool."""

    name: str
    description: str


class _ResourceDescription(TypedDict):
    """Description of an MCP resource."""

    uri: str
    description: str


class _SecurityConfigResult(TypedDict):
    """Result of security configuration resource."""

    allowed_modules: list[str]
    blocked_modules: list[str]
    dangerous_builtins: list[str]
    memory_limit_mb: int
    code_size_bytes: int
    coverage_threshold: int


class _ServerConfigResult(TypedDict):
    """Result of server configuration resource."""

    version: str
    default_timeout_seconds: int
    mask_error_details: bool
    transport: Literal["oauth", "stdio"]


class _CapabilitiesResult(TypedDict):
    """Result of capabilities resource."""

    tools: list[_ToolDescription]
    resources: list[_ResourceDescription]


# Public type aliases for cleaner imports
Counterexample = _Counterexample
SymbolicCheckResult = _SymbolicCheckResult
ValidationResult = _ValidationResult
ExceptionPathResult = _ExceptionPathResult
FunctionComparisonResult = _FunctionComparisonResult
BranchInfo = _BranchInfo
BranchAnalysisResult = _BranchAnalysisResult
HealthCheckResult = _HealthCheckResult
ToolDescription = _ToolDescription
ResourceDescription = _ResourceDescription
SecurityConfigResult = _SecurityConfigResult
ServerConfigResult = _ServerConfigResult
CapabilitiesResult = _CapabilitiesResult

__all__ = [
    "_Counterexample",
    "_SymbolicCheckResult",
    "_ValidationResult",
    "_ExceptionPathResult",
    "_FunctionComparisonResult",
    "_BranchInfo",
    "_BranchAnalysisResult",
    "_HealthCheckResult",
    "_ToolDescription",
    "_ResourceDescription",
    "_SecurityConfigResult",
    "_ServerConfigResult",
    "_CapabilitiesResult",
    # Public aliases
    "Counterexample",
    "SymbolicCheckResult",
    "ValidationResult",
    "ExceptionPathResult",
    "FunctionComparisonResult",
    "BranchInfo",
    "BranchAnalysisResult",
    "HealthCheckResult",
    "ToolDescription",
    "ResourceDescription",
    "SecurityConfigResult",
    "ServerConfigResult",
    "CapabilitiesResult",
]
