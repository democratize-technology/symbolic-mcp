# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Symbolic MCP Contributors

"""Symbolic Execution MCP Server

A Model Context Protocol server that provides symbolic execution
capabilities using CrossHair for formal verification and analysis.
"""

from symbolic_mcp._version import __version__

# Import server components for backward compatibility
from symbolic_mcp.server import main, mcp

# Import tools for direct access
from symbolic_mcp.tools import (
    logic_analyze_branches,
    logic_compare_functions,
    logic_find_path_to_exception,
    logic_symbolic_check,
)

# Import types for public API
from symbolic_mcp.types import (
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
)

__all__ = [
    "__version__",
    # Server
    "main",
    "mcp",
    # Tools
    "logic_symbolic_check",
    "logic_find_path_to_exception",
    "logic_compare_functions",
    "logic_analyze_branches",
    # Types
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
