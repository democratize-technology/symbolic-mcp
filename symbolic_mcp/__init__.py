# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Symbolic MCP Contributors

"""Symbolic Execution MCP Server

A Model Context Protocol server that provides symbolic execution
capabilities using CrossHair for formal verification and analysis.
"""

from symbolic_mcp._version import __version__

# Import analyzer
from symbolic_mcp.analyzer import SymbolicAnalyzer, _temporary_module

# Import config
from symbolic_mcp.config import (
    _SYS_MODULES_LOCK,
    CODE_SIZE_LIMIT,
    COVERAGE_DEGRADATION_FACTOR,
    COVERAGE_EXHAUSTIVE_THRESHOLD,
    DEFAULT_ANALYSIS_TIMEOUT_SECONDS,
    MAX_COVERAGE_SCALE_FACTOR,
    MEMORY_LIMIT_MB,
    PER_PATH_TIMEOUT_RATIO,
    set_memory_limit,
)

# Import parsing
from symbolic_mcp.parsing import (
    _CALL_PATTERN,
    _EXC_PATTERN,
    _RESULT_PATTERN,
    _parse_function_args,
)

# Import security
from symbolic_mcp.security import (
    ALLOWED_MODULES,
    BLOCKED_MODULES,
    DANGEROUS_BUILTINS,
    _DangerousCallVisitor,
    validate_code,
)

# Import server
from symbolic_mcp.server import _get_github_auth, logic_health_check, main, mcp

# Import tools
from symbolic_mcp.tools import (
    logic_analyze_branches,
    logic_compare_functions,
    logic_find_path_to_exception,
    logic_symbolic_check,
)

# Import types (both public and private for testing)
from symbolic_mcp.types import (  # Public aliases
    BranchAnalysisResult,
    BranchInfo,
    CapabilitiesResult,
    Counterexample,
    ExceptionPathResult,
    FunctionComparisonResult,
    HealthCheckResult,
    ResourceDescription,
    SecurityConfigResult,
    ServerConfigResult,
    SymbolicCheckResult,
    ToolDescription,
    ValidationResult,
    _BranchAnalysisResult,
    _BranchInfo,
    _CapabilitiesResult,
    _Counterexample,
    _ExceptionPathResult,
    _FunctionComparisonResult,
    _HealthCheckResult,
    _ResourceDescription,
    _SecurityConfigResult,
    _ServerConfigResult,
    _SymbolicCheckResult,
    _ToolDescription,
    _ValidationResult,
)

__all__ = [
    "__version__",
    # Server
    "main",
    "mcp",
    "_get_github_auth",
    "logic_health_check",
    # Tools
    "logic_symbolic_check",
    "logic_find_path_to_exception",
    "logic_compare_functions",
    "logic_analyze_branches",
    # Analyzer
    "SymbolicAnalyzer",
    "_temporary_module",
    # Parsing
    "_parse_function_args",
    "_CALL_PATTERN",
    "_RESULT_PATTERN",
    "_EXC_PATTERN",
    # Security
    "validate_code",
    "ALLOWED_MODULES",
    "BLOCKED_MODULES",
    "DANGEROUS_BUILTINS",
    "_DangerousCallVisitor",
    # Config
    "DEFAULT_ANALYSIS_TIMEOUT_SECONDS",
    "MEMORY_LIMIT_MB",
    "CODE_SIZE_LIMIT",
    "COVERAGE_EXHAUSTIVE_THRESHOLD",
    "COVERAGE_DEGRADATION_FACTOR",
    "MAX_COVERAGE_SCALE_FACTOR",
    "PER_PATH_TIMEOUT_RATIO",
    "_SYS_MODULES_LOCK",
    "set_memory_limit",
    # Types (private for testing)
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
    # Types (public)
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
