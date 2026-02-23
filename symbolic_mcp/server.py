# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Symbolic MCP Contributors

"""FastMCP server for symbolic execution.

This module contains the FastMCP server setup, tool decorators,
resources, prompts, and entry point.
"""

import contextlib
import logging
import os
import platform
from typing import AsyncGenerator

import psutil
from fastmcp import FastMCP
from fastmcp.server.auth.providers.github import GitHubProvider
from mcp.types import ToolAnnotations

from symbolic_mcp._version import __version__
from symbolic_mcp.config import (
    _SYS_MODULES_LOCK,
    CODE_SIZE_LIMIT,
    COVERAGE_EXHAUSTIVE_THRESHOLD,
    DEFAULT_ANALYSIS_TIMEOUT_SECONDS,
    MEMORY_LIMIT_MB,
)
from symbolic_mcp.security import ALLOWED_MODULES, BLOCKED_MODULES, DANGEROUS_BUILTINS
from symbolic_mcp.tools import (
    logic_analyze_branches,
    logic_compare_functions,
    logic_find_path_to_exception,
    logic_symbolic_check,
)
from symbolic_mcp.types import (
    _BranchAnalysisResult,
    _CapabilitiesResult,
    _ExceptionPathResult,
    _FunctionComparisonResult,
    _HealthCheckResult,
    _SecurityConfigResult,
    _ServerConfigResult,
    _SymbolicCheckResult,
)

# Configure logging
logger = logging.getLogger(__name__)


def _get_github_auth() -> GitHubProvider | None:
    """Get GitHub OAuth provider if configured for HTTP deployment.

    Returns GitHubProvider if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET
    environment variables are set. Otherwise returns None for stdio transport.

    Environment Variables:
        GITHUB_CLIENT_ID: GitHub OAuth App client ID
        GITHUB_CLIENT_SECRET: GitHub OAuth App client secret

    Returns:
        GitHubProvider if configured, None for stdio (local development)
    """
    client_id = os.environ.get("GITHUB_CLIENT_ID")
    client_secret = os.environ.get("GITHUB_CLIENT_SECRET")

    if client_id and client_secret:
        logger.info("GitHub OAuth authentication configured for HTTP deployment")
        return GitHubProvider(
            client_id=client_id,
            client_secret=client_secret,
            base_url="https://github.com",
        )

    logger.info("No OAuth credentials found, using stdio transport (local development)")
    return None


@contextlib.asynccontextmanager
async def lifespan(app: object) -> AsyncGenerator[dict[str, object], None]:
    """Manage server lifespan.

    Note: The app parameter type is 'object' to match FastMCP's expected
    lifespan context manager signature. The return type uses dict[str, object]
    as the state dictionary can contain arbitrary values.
    """
    try:
        yield {}
    finally:
        # Clean up temporary modules
        # Lock required to prevent race conditions with concurrent _temporary_module calls
        import sys

        with _SYS_MODULES_LOCK:
            temp_modules = [
                name for name in sys.modules.keys() if name.startswith("mcp_temp_")
            ]
            for module_name in temp_modules:
                if module_name in sys.modules:
                    del sys.modules[module_name]


# Configure authentication (if provided)
# For HTTP deployment with OAuth, set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET
# For stdio transport (local development), leave environment variables unset
auth = _get_github_auth()

mcp = FastMCP(
    "Symbolic Execution Server",
    auth=auth,  # OAuth for HTTP, None for stdio
    lifespan=lifespan,
    mask_error_details=True,  # Security: Hide internal error details from clients
)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Symbolic Contract Verification",
        readOnlyHint=True,  # Analysis doesn't modify code
        idempotentHint=True,  # Same code produces same results
        destructiveHint=False,
    )
)
def symbolic_check(
    code: str,
    function_name: str,
    timeout_seconds: int = DEFAULT_ANALYSIS_TIMEOUT_SECONDS,
) -> _SymbolicCheckResult:
    """Symbolically verify that a function satisfies its contract.

    Args:
        code: Python function definition with contracts
        function_name: Name of function to analyze
        timeout_seconds: Analysis timeout in seconds (default: DEFAULT_ANALYSIS_TIMEOUT_SECONDS)

    Returns:
        SymbolicCheckResult with status, counterexamples, paths explored, etc.
    """
    return logic_symbolic_check(code, function_name, timeout_seconds)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Find Exception Triggering Inputs",
        readOnlyHint=True,  # Analysis doesn't modify code
        idempotentHint=True,  # Same inputs produce same results
        destructiveHint=False,
    )
)
def find_path_to_exception(
    code: str,
    function_name: str,
    exception_type: str,
    timeout_seconds: int = DEFAULT_ANALYSIS_TIMEOUT_SECONDS,
) -> _ExceptionPathResult:
    """Find concrete inputs that cause a specific exception type to be raised."""
    return logic_find_path_to_exception(
        code, function_name, exception_type, timeout_seconds
    )


@mcp.tool(
    annotations=ToolAnnotations(
        title="Semantic Function Equivalence Check",
        readOnlyHint=True,  # Analysis doesn't modify code
        idempotentHint=True,  # Same inputs produce same results
        destructiveHint=False,
    )
)
def compare_functions(
    code: str,
    function_a: str,
    function_b: str,
    timeout_seconds: int = DEFAULT_ANALYSIS_TIMEOUT_SECONDS,
) -> _FunctionComparisonResult:
    """Check if two functions are semantically equivalent."""
    return logic_compare_functions(code, function_a, function_b, timeout_seconds)


@mcp.tool(
    annotations=ToolAnnotations(
        title="Branch Analysis and Complexity",
        readOnlyHint=True,  # Analysis doesn't modify code
        idempotentHint=True,  # Same inputs produce same results
        destructiveHint=False,
    )
)
def analyze_branches(
    code: str,
    function_name: str,
    timeout_seconds: int = DEFAULT_ANALYSIS_TIMEOUT_SECONDS,
    symbolic_reachability: bool = False,
) -> _BranchAnalysisResult:
    """Enumerate branch conditions and report static or symbolic reachability.

    Args:
        code: Python function definition to analyze
        function_name: Name of function to analyze
        timeout_seconds: Analysis timeout in seconds (default: DEFAULT_ANALYSIS_TIMEOUT_SECONDS)
        symbolic_reachability: If True, use symbolic execution to prove reachability (default: False)

    Returns:
        BranchAnalysisResult with branch information, complexity, and dead code detection.
    """
    return logic_analyze_branches(
        code, function_name, timeout_seconds, symbolic_reachability
    )


def logic_health_check() -> _HealthCheckResult:
    """Health check for the Symbolic Execution MCP server logic.

    Returns server status, version information, and resource usage.
    """
    # Get CrossHair version
    crosshair_version = None
    try:
        import crosshair

        crosshair_version = getattr(crosshair, "__version__", "unknown")
    except Exception:
        crosshair_version = None

    # Get Z3 version
    z3_version = None
    try:
        import z3

        version_tuple = z3.get_version()
        # z3.get_version() returns a tuple like (4, 13, 0, 0)
        z3_version = ".".join(map(str, version_tuple)) if version_tuple else "unknown"
    except Exception:
        z3_version = None

    return {
        "status": "healthy",
        "version": __version__,
        "python_version": platform.python_version(),
        "crosshair_version": crosshair_version,
        "z3_version": z3_version,
        "platform": platform.platform(),
        "memory_usage_mb": round(psutil.Process().memory_info().rss / 1024 / 1024, 2),
    }


@mcp.tool(
    annotations=ToolAnnotations(
        title="Server Health Check",
        readOnlyHint=True,  # Read-only server status
        idempotentHint=True,  # Same results on repeated calls
        destructiveHint=False,
    )
)
def health_check() -> _HealthCheckResult:
    """Health check for the Symbolic Execution MCP server.

    Returns server status, version information, and resource usage.
    """
    return logic_health_check()


@mcp.resource("config://security")
def get_security_config() -> _SecurityConfigResult:
    """Current security configuration settings.

    Returns the whitelist of allowed modules, blocked modules, and
    other security-related configuration from ADR-003.
    """
    return {
        "allowed_modules": list(ALLOWED_MODULES),
        "blocked_modules": list(BLOCKED_MODULES),
        "dangerous_builtins": list(DANGEROUS_BUILTINS),
        "memory_limit_mb": MEMORY_LIMIT_MB,
        "code_size_bytes": CODE_SIZE_LIMIT,
        "coverage_threshold": COVERAGE_EXHAUSTIVE_THRESHOLD,
    }


@mcp.resource("config://server")
def get_server_config() -> _ServerConfigResult:
    """Current server configuration settings.

    Returns version, timeout settings, and other server-related
    configuration.
    """
    return {
        "version": __version__,
        "default_timeout_seconds": DEFAULT_ANALYSIS_TIMEOUT_SECONDS,
        "mask_error_details": True,  # Always True for production
        "transport": "oauth" if _get_github_auth() else "stdio",
    }


@mcp.resource("info://capabilities")
def get_capabilities() -> _CapabilitiesResult:
    """Server capabilities and available tools.

    Returns a list of available tools and their descriptions.
    """
    return {
        "tools": [
            {
                "name": "symbolic_check",
                "description": "Symbolically verify that a function satisfies its contract.",
            },
            {
                "name": "find_path_to_exception",
                "description": "Find concrete inputs that cause a specific exception type.",
            },
            {
                "name": "compare_functions",
                "description": "Check if two functions are semantically equivalent.",
            },
            {
                "name": "analyze_branches",
                "description": "Enumerate branch conditions and report reachability.",
            },
            {
                "name": "health_check",
                "description": "Health check for the Symbolic Execution MCP server.",
            },
        ],
        "resources": [
            {
                "uri": "config://security",
                "description": "Security configuration settings",
            },
            {"uri": "config://server", "description": "Server configuration settings"},
            {"uri": "info://capabilities", "description": "Server capabilities"},
        ],
    }


@mcp.prompt
def symbolic_check_template() -> str:
    """Template for analyzing function contracts with symbolic execution.

    Use this prompt when you want to verify that a function satisfies
    its contract using formal symbolic execution.
    """
    return """
Please analyze this Python function using symbolic execution:

```python
{{code}}
```

Function to analyze: `{{function_name}}`

Report on:
1. Contract violations found (if any)
2. Counterexamples with concrete inputs
3. Number of paths explored and verified
4. Estimated code coverage

Use the `symbolic_check` tool with appropriate timeout.
"""


@mcp.prompt
def find_exception_path_template() -> str:
    """Template for finding paths to exceptions.

    Use this prompt when you want to find concrete inputs that cause
    a specific exception type to be raised.
    """
    return """
Please find concrete inputs that cause this function to raise an exception:

```python
{{code}}
```

Function to analyze: `{{function_name}}`
Target exception type: `{{exception_type}}`

Report on:
1. Concrete inputs that trigger the exception
2. Path conditions that lead to the exception
3. Whether the exception is reachable

Use the `find_path_to_exception` tool with appropriate timeout.
"""


@mcp.prompt
def compare_functions_template() -> str:
    """Template for comparing function equivalence.

    Use this prompt when you want to check if two functions are
    semantically equivalent.
    """
    return """
Please compare these two functions for semantic equivalence:

```python
{{code}}
```

Function A: `{{function_a}}`
Function B: `{{function_b}}`

Report on:
1. Whether the functions are semantically equivalent
2. Any behavioral differences found
3. Concrete inputs demonstrating differences (if any)

Use the `compare_functions` tool with appropriate timeout.
"""


@mcp.prompt
def analyze_branches_template() -> str:
    """Template for branch analysis.

    Use this prompt when you want to analyze branch conditions
    and code complexity.
    """
    return """
Please analyze the branch structure and complexity of this function:

```python
{{code}}
```

Function to analyze: `{{function_name}}`

Report on:
1. All branch conditions found
2. Cyclomatic complexity
3. Potential dead code (unreachable branches)
4. Static vs symbolic reachability (if requested)

Use the `analyze_branches` tool with appropriate timeout.
"""


def main() -> None:
    """Entry point for the symbolic-mcp CLI command."""
    mcp.run()


if __name__ == "__main__":
    main()
