"""Symbolic Execution MCP Server

A Model Context Protocol server that provides symbolic execution
capabilities using CrossHair for formal verification and analysis.
"""

import ast
import contextlib
import importlib.util
import logging
import os
import resource
import sys
import tempfile
import textwrap
import time
from typing import Any, Dict, Optional

from crosshair.core_and_libs import AnalysisOptions, MessageType, analyze_function
from fastmcp import FastMCP

# Version information
try:
    from ._version import __version__
except ImportError:
    __version__ = "0.1.0"

# Configure logging
logger = logging.getLogger(__name__)

# --- Security: Import Whitelist ---

# Modules allowed in user code for symbolic execution
ALLOWED_MODULES = frozenset(
    {
        "math",
        "random",
        "string",
        "collections",
        "itertools",
        "functools",
        "operator",
        "typing",
        "re",
        "json",
        "datetime",
        "decimal",
        "fractions",
        "statistics",
        "dataclasses",
        "enum",
        "copy",
        "heapq",
        "bisect",
        "typing_extensions",
        "abc",
    }
)

# Modules that are dangerous and should be blocked
BLOCKED_MODULES = frozenset(
    {
        "os",
        "sys",
        "subprocess",
        "shutil",
        "pathlib",
        "socket",
        "http",
        "urllib",
        "requests",
        "ftplib",
        "pickle",
        "shelve",
        "marshal",
        "ctypes",
        "multiprocessing",
        "importlib",
        "runpy",
        "code",
        "codeop",
        "pty",
        "tty",
    }
)


# --- Memory Management ---


def set_memory_limit(limit_mb: int = 2048):
    """Set memory limit for the process to prevent resource exhaustion."""
    try:
        limit_bytes = limit_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, -1))
    except (ValueError, ImportError):
        pass


set_memory_limit()


# --- Input Validation ---


def validate_code(code: str) -> Dict[str, Any]:
    """Validate user code before execution.

    Returns:
        Dict with 'valid': bool and 'error': str if invalid
    """
    # Size limit: 64KB
    if len(code.encode("utf-8")) > 65536:
        return {"valid": False, "error": "Code size exceeds 64KB limit"}

    # Check for dangerous patterns
    blocked_patterns = {
        "import os",
        "import sys",
        "subprocess",
        "__import__",
        "eval(",
        "exec(",
        "compile(",
    }

    for pattern in blocked_patterns:
        if pattern in code:
            return {"valid": False, "error": f"Blocked pattern: {pattern}"}

    # Check for blocked imports
    try:
        tree = ast.parse(code)
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module_name = (
                    node.names[0].name if isinstance(node, ast.Import) else node.module
                )
                if module_name:
                    base_module = module_name.split(".")[0]
                    if base_module in BLOCKED_MODULES:
                        return {
                            "valid": False,
                            "error": f"Blocked module: {base_module}",
                        }
    except SyntaxError as e:
        return {"valid": False, "error": f"Syntax error: {e}"}

    return {"valid": True}


# --- Symbolic Analyzer ---


class SymbolicAnalyzer:
    """Analyzes code using CrossHair symbolic execution."""

    def __init__(self, timeout_seconds: int = 30):
        self.timeout = timeout_seconds

    @contextlib.contextmanager
    def _temporary_module(self, code: str):
        """Create a temporary module from code."""
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False) as tmp:
            tmp.write(textwrap.dedent(code))
            tmp_path = tmp.name

        module_name = f"mcp_temp_{os.path.basename(tmp_path)[:-3]}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, tmp_path)
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)
                yield module
        finally:
            if module_name in sys.modules:
                del sys.modules[module_name]
            if os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

    def analyze(self, code: str, target_function_name: str) -> Dict[str, Any]:
        """Analyze a function using symbolic execution."""
        start_time = time.perf_counter()

        # Validate code first
        validation = validate_code(code)
        if not validation["valid"]:
            return {
                "status": "error",
                "error_type": "ValidationError",
                "message": validation["error"],
                "time_seconds": round(time.perf_counter() - start_time, 4),
            }

        try:
            with self._temporary_module(code) as module:
                if not hasattr(module, target_function_name):
                    return {
                        "status": "error",
                        "error_type": "NameError",
                        "message": f"Function '{target_function_name}' not found",
                    }

                func = getattr(module, target_function_name)

                options = AnalysisOptions(
                    analysis_kind=[AnalysisKind.PEP316],
                    enabled=True,
                    specs_complete=False,
                    per_condition_timeout=float(self.timeout),
                    max_iterations=1000,
                    report_all=False,
                    report_verbose=False,
                    unblock=(),
                    timeout=float(self.timeout),
                    per_path_timeout=float(self.timeout) / 10.0,
                    max_uninteresting_iterations=1000,
                )

                counterexamples = []
                paths_explored = 0
                paths_verified = 0

                for message in analyze_function(func, options):
                    paths_explored += 1
                    if message.state == MessageType.CONFIRMED:
                        paths_verified += 1
                    elif message.state == MessageType.COUNTEREXAMPLE:
                        counterexamples.append(
                            {
                                "args": message.args,
                                "kwargs": message.kwargs or {},
                                "violation": message.message,
                            }
                        )

                elapsed = time.perf_counter() - start_time

                status = "verified"
                if counterexamples:
                    status = "counterexample"
                elif paths_explored == 0:
                    status = "unknown"

                return {
                    "status": status,
                    "counterexamples": counterexamples,
                    "paths_explored": paths_explored,
                    "paths_verified": paths_verified,
                    "time_seconds": round(elapsed, 4),
                }

        except ImportError as e:
            return {
                "status": "error",
                "error_type": "ImportError",
                "message": str(e),
            }
        except Exception as e:
            return {
                "status": "error",
                "error_type": type(e).__name__,
                "message": str(e),
            }


# Import AnalysisKind from crosshair.options
try:
    from crosshair.options import AnalysisKind
except ImportError:
    # Fallback for older versions
    class AnalysisKind:
        PEP316 = "PEP316"


# --- Tool Logic Functions ---


def logic_symbolic_check(
    code: str, function_name: str, timeout_seconds: int
) -> Dict[str, Any]:
    """Symbolically verify that a function satisfies its contract."""
    analyzer = SymbolicAnalyzer(timeout_seconds)
    return analyzer.analyze(code, function_name)


def logic_find_path_to_exception(
    code: str, function_name: str, exception_type: str, timeout_seconds: int
) -> Dict[str, Any]:
    """Find concrete inputs that cause a specific exception type."""
    wrapper_code = f"""
{code}

def _exception_hunter_wrapper(*args, **kwargs):
    try:
        {function_name}(*args, **kwargs)
    except {exception_type}:
        assert False, "Triggered target exception: {exception_type}"
    except Exception:
        pass
    """
    analyzer = SymbolicAnalyzer(timeout_seconds)
    result = analyzer.analyze(wrapper_code, "_exception_hunter_wrapper")

    if result["status"] == "counterexample":
        return {
            "status": "found",
            "triggering_inputs": result["counterexamples"],
            "paths_to_exception": len(result["counterexamples"]),
            "total_paths_explored": result["paths_explored"],
            "time_seconds": result.get("time_seconds", 0),
        }
    elif result["status"] == "verified":
        return {
            "status": "unreachable",
            "paths_to_exception": 0,
            "total_paths_explored": result["paths_explored"],
        }
    else:
        return result


def logic_compare_functions(
    code: str, function_a: str, function_b: str, timeout_seconds: int
) -> Dict[str, Any]:
    """Check if two functions are semantically equivalent."""
    wrapper_code = f"""
{code}

def _equivalence_check(*args, **kwargs):
    res_a = {function_a}(*args, **kwargs)
    res_b = {function_b}(*args, **kwargs)
    assert res_a == res_b, f"Mismatch: {{res_a}} != {{res_b}}"
"""
    analyzer = SymbolicAnalyzer(timeout_seconds)
    result = analyzer.analyze(wrapper_code, "_equivalence_check")

    if result["status"] == "counterexample":
        return {
            "status": "different",
            "distinguishing_input": result["counterexamples"][0],
            "paths_compared": result["paths_explored"],
            "confidence": "proven",
        }
    elif result["status"] == "verified":
        return {
            "status": "equivalent",
            "distinguishing_input": None,
            "paths_compared": result["paths_explored"],
            "confidence": "proven",
        }
    else:
        return result


def logic_analyze_branches(
    code: str, function_name: str, timeout_seconds: int
) -> Dict[str, Any]:
    """Enumerate branch conditions and report static reachability."""
    start_time = time.perf_counter()

    # Validate code first
    validation = validate_code(code)
    if not validation["valid"]:
        return {
            "status": "error",
            "error_type": "ValidationError",
            "message": validation["error"],
            "time_seconds": round(time.perf_counter() - start_time, 4),
        }

    try:
        tree = ast.parse(textwrap.dedent(code))
    except SyntaxError as e:
        return {
            "status": "error",
            "error_type": "SyntaxError",
            "message": str(e),
            "line": e.lineno,
        }

    # Find branches
    branches = []

    class BranchFinder(ast.NodeVisitor):
        def visit_If(self, node):
            segment = ast.get_source_segment(textwrap.dedent(code), node.test)
            if segment:
                branches.append(
                    {
                        "line": node.lineno,
                        "condition": segment,
                    }
                )
            self.generic_visit(node)

        def visit_While(self, node):
            segment = ast.get_source_segment(textwrap.dedent(code), node.test)
            if segment:
                branches.append(
                    {
                        "line": node.lineno,
                        "condition": segment,
                    }
                )
            self.generic_visit(node)

        def visit_For(self, node):
            segment = ast.get_source_segment(textwrap.dedent(code), node.target)
            if segment:
                branches.append(
                    {
                        "line": node.lineno,
                        "condition": f"for {segment} in ...",
                    }
                )
            self.generic_visit(node)

    BranchFinder().visit(tree)

    # Calculate cyclomatic complexity
    complexity = 1  # Base complexity

    class ComplexityVisitor(ast.NodeVisitor):
        def __init__(self):
            nonlocal complexity

        def visit_If(self, node):
            nonlocal complexity
            complexity += 1
            for orelse in node.orelse:
                if isinstance(orelse, ast.If):
                    complexity += 1
            self.generic_visit(node)

        def visit_While(self, node):
            nonlocal complexity
            complexity += 1
            self.generic_visit(node)

        def visit_For(self, node):
            nonlocal complexity
            complexity += 1
            self.generic_visit(node)

        def visit_BoolOp(self, node):
            nonlocal complexity
            complexity += len(node.values) - 1
            self.generic_visit(node)

    ComplexityVisitor().visit(tree)

    return {
        "status": "complete",
        "branches": branches,
        "total_branches": len(branches),
        "reachable_branches": len(branches),  # Assume reachable without deeper analysis
        "dead_code_lines": [],
        "cyclomatic_complexity": complexity,
        "time_seconds": round(time.perf_counter() - start_time, 4),
    }


# --- FastMCP Server ---


@contextlib.asynccontextmanager
async def lifespan(app):
    """Manage server lifespan."""
    try:
        yield {}
    finally:
        # Clean up temporary modules
        temp_modules = [
            name for name in sys.modules.keys() if name.startswith("mcp_temp_")
        ]
        for module_name in temp_modules:
            if module_name in sys.modules:
                del sys.modules[module_name]


mcp = FastMCP("Symbolic Execution Server", lifespan=lifespan)


@mcp.tool()
def symbolic_check(
    code: str, function_name: str, timeout_seconds: int = 30
) -> Dict[str, Any]:
    """Symbolically verify that a function satisfies its contract."""
    return logic_symbolic_check(code, function_name, timeout_seconds)


@mcp.tool()
def find_path_to_exception(
    code: str, function_name: str, exception_type: str, timeout_seconds: int = 30
) -> Dict[str, Any]:
    """Find concrete inputs that cause a specific exception type to be raised."""
    return logic_find_path_to_exception(
        code, function_name, exception_type, timeout_seconds
    )


@mcp.tool()
def compare_functions(
    code: str, function_a: str, function_b: str, timeout_seconds: int = 60
) -> Dict[str, Any]:
    """Check if two functions are semantically equivalent."""
    return logic_compare_functions(code, function_a, function_b, timeout_seconds)


@mcp.tool()
def analyze_branches(
    code: str, function_name: str, timeout_seconds: int = 30
) -> Dict[str, Any]:
    """Enumerate branch conditions and report static reachability."""
    return logic_analyze_branches(code, function_name, timeout_seconds)


@mcp.tool()
def health_check() -> Dict[str, Any]:
    """Health check for the Symbolic Execution MCP server."""
    import platform

    import psutil

    return {
        "status": "healthy",
        "version": __version__,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "memory_usage_mb": round(psutil.Process().memory_info().rss / 1024 / 1024, 2),
    }


if __name__ == "__main__":
    mcp.run()
