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
        "termios",
        "threading",
        "signal",
        "fcntl",
        "resource",
        "syslog",
        "getpass",
    }
)

# Built-in functions that are dangerous and should be blocked
DANGEROUS_BUILTINS = frozenset(
    {
        "eval",
        "exec",
        "compile",
        "__import__",
        "open",
        "globals",
        "locals",
        "vars",
        "dir",
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


class _DangerousCallVisitor(ast.NodeVisitor):
    """AST visitor that detects dangerous function calls and attribute access.

    This prevents bypasses like:
    - eval (1) - space before parenthesis
    - getattr(__builtins__, "eval") - dynamic access
    - [eval][0]() - list indexing bypass
    - {"f": eval}["f"]() - dict lookup bypass
    - (eval,) - tuple unpacking bypass
    - __builtins__["eval"] - subscript access to __builtins__
    - __builtins__.eval - attribute access to __builtins__
    """

    # Blocked global names that provide access to dangerous functions
    BLOCKED_GLOBALS = frozenset({"__builtins__"})

    def __init__(self) -> None:
        self.dangerous_calls: list[str] = []
        self.dangerous_references: list[str] = []
        self.builtins_access: list[str] = []

    def _is_dangerous_name(self, name: str) -> bool:
        """Check if a name refers to a dangerous builtin."""
        return name in DANGEROUS_BUILTINS

    def _is_blocked_module(self, name: str) -> bool:
        """Check if a name is a blocked module."""
        return name in BLOCKED_MODULES

    def _is_blocked_global(self, name: str) -> bool:
        """Check if a name is a blocked global variable."""
        return name in self.BLOCKED_GLOBALS

    def _check_subscript_for_dangerous(self, node: ast.Subscript) -> None:
        """Check if a subscript accesses a dangerous function.

        Handles: [eval][0](), (eval,)[0](), {"f": eval}["f"]()
        """
        # Check the value being subscripted
        if isinstance(node.value, ast.Name):
            if self._is_dangerous_name(node.value.id):
                self.dangerous_calls.append(node.value.id)
        elif isinstance(node.value, (ast.List, ast.Tuple)):
            self._check_sequence_for_dangerous(node.value)
        elif isinstance(node.value, ast.Dict):
            self._check_dict_for_dangerous(node.value)
        elif isinstance(node.value, ast.Subscript):
            self._check_subscript_for_dangerous(node.value)

    def _check_sequence_for_dangerous(self, node: ast.List | ast.Tuple) -> None:
        """Check a list or tuple literal for dangerous builtin references.

        Handles: [eval], (eval,), [[eval]]
        """
        for elt in node.elts:
            if isinstance(elt, ast.Name) and self._is_dangerous_name(elt.id):
                self.dangerous_calls.append(elt.id)
                self.dangerous_references.append(elt.id)
            elif isinstance(elt, (ast.List, ast.Tuple)):
                self._check_sequence_for_dangerous(elt)

    def _check_dict_for_dangerous(self, node: ast.Dict) -> None:
        """Check a dict literal for dangerous builtin references.

        Handles: {"f": eval}, {"f": [eval]}
        """
        for value in node.values:
            if isinstance(value, ast.Name) and self._is_dangerous_name(value.id):
                self.dangerous_calls.append(value.id)
                self.dangerous_references.append(value.id)
            elif isinstance(value, (ast.List, ast.Tuple)):
                self._check_sequence_for_dangerous(value)
            elif isinstance(value, ast.Dict):
                self._check_dict_for_dangerous(value)

    def visit_List(self, node: ast.List) -> None:
        """Visit list nodes to detect dangerous function references."""
        self._check_sequence_for_dangerous(node)
        self.generic_visit(node)

    def visit_Tuple(self, node: ast.Tuple) -> None:
        """Visit tuple nodes to detect dangerous function references."""
        self._check_sequence_for_dangerous(node)
        self.generic_visit(node)

    def visit_Dict(self, node: ast.Dict) -> None:
        """Visit dict nodes to detect dangerous function references."""
        self._check_dict_for_dangerous(node)
        self.generic_visit(node)

    def visit_Name(self, node: ast.Name) -> None:
        """Track dangerous names that might be called indirectly."""
        # If we see a dangerous name being referenced anywhere in the code,
        # it could be called indirectly
        if self._is_dangerous_name(node.id):
            self.dangerous_references.append(node.id)
        # Check for blocked globals like __builtins__
        if self._is_blocked_global(node.id):
            self.dangerous_references.append(node.id)
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        """Detect dangerous attribute access patterns.

        Handles:
        - __builtins__.eval
        - __builtins__.exec
        - __builtins__.compile
        """
        # Check if this is accessing an attribute of __builtins__
        if isinstance(node.value, ast.Name):
            if node.value.id == "__builtins__":
                # Block any attribute access to __builtins__
                self.dangerous_calls.append(f"__builtins__.{node.attr}")
                self.builtins_access.append(f"__builtins__.{node.attr}")
        # Also check nested attribute access like __builtins__.__dict__
        elif isinstance(node.value, ast.Attribute):
            # Walk down to find the root
            root = node.value
            parts = [node.attr]
            while isinstance(root, ast.Attribute):
                parts.append(root.attr)
                root = root.value
            if isinstance(root, ast.Name) and root.id == "__builtins__":
                parts.append("__builtins__")
                full_chain = ".".join(reversed(parts))
                self.dangerous_calls.append(full_chain)
                self.builtins_access.append(full_chain)
        self.generic_visit(node)

    def visit_Subscript(self, node: ast.Subscript) -> None:
        """Detect dangerous subscript access patterns.

        Handles:
        - __builtins__["eval"]
        - (__builtins__)["eval"]
        - (__builtins__ or {})["eval"]
        """
        # Check if we're subscripting __builtins__
        if isinstance(node.value, ast.Name):
            if node.value.id == "__builtins__":
                self.dangerous_calls.append("__builtins__[...]")
                self.builtins_access.append("__builtins__[...]")
        # Check for subscripted expressions like (__builtins__)["eval"]
        elif isinstance(node.value, (ast.BinOp, ast.BoolOp, ast.Compare)):
            # Check if __builtins__ appears in the expression
            for child in ast.walk(node.value):
                if isinstance(child, ast.Name) and child.id == "__builtins__":
                    self.dangerous_calls.append("__builtins__[...]")
                    self.builtins_access.append("__builtins__[...]")
                    break
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        """Detect dangerous function calls including getattr bypasses.

        Handles:
        - getattr(__builtins__, "eval")
        - getattr(__builtins__, "exec")
        """
        # Check for getattr(__builtins__, "dangerous")
        if isinstance(node.func, ast.Name) and node.func.id == "getattr":
            if len(node.args) >= 2:
                # First arg should be __builtins__
                if (
                    isinstance(node.args[0], ast.Name)
                    and node.args[0].id == "__builtins__"
                ):
                    # Second arg is the attribute name - check if it's a dangerous builtin
                    if isinstance(node.args[1], ast.Constant):
                        attr_name = node.args[1].value
                        if isinstance(attr_name, str) and self._is_dangerous_name(
                            attr_name
                        ):
                            self.dangerous_calls.append(
                                f'getattr(__builtins__, "{attr_name}")'
                            )
                    # Even if we can't determine the attribute name statically,
                    # getattr on __builtins__ is dangerous
                    self.dangerous_calls.append("getattr(__builtins__, ...)")
                    self.builtins_access.append("getattr(__builtins__, ...)")

        # Now check for other dangerous calls (original logic)
        # Direct name call: eval(), exec(), compile()
        if isinstance(node.func, ast.Name):
            if self._is_dangerous_name(node.func.id):
                self.dangerous_calls.append(node.func.id)

        # Attribute access: os.system(), subprocess.run()
        elif isinstance(node.func, ast.Attribute):
            # Check for dangerous attribute chains
            if isinstance(node.func.value, ast.Name):
                # module.dangerous_function()
                attr_chain = f"{node.func.value.id}.{node.func.attr}"
                if self._is_blocked_module(node.func.value.id):
                    self.dangerous_calls.append(attr_chain)
            elif isinstance(node.func.value, ast.Attribute):
                # nested.module.dangerous_function()
                # Walk up to find the root module
                root = node.func.value
                parts = [node.func.attr]
                while isinstance(root, ast.Attribute):
                    parts.append(root.attr)
                    root = root.value
                if isinstance(root, ast.Name):
                    parts.append(root.id)
                    full_name = ".".join(reversed(parts))
                    if any(
                        self._is_blocked_module(part) for part in full_name.split(".")
                    ):
                        self.dangerous_calls.append(full_name)

        # Subscript call: [eval][0]()
        elif isinstance(node.func, ast.Subscript):
            self._check_subscript_for_dangerous(node.func)

        self.generic_visit(node)


def validate_code(code: str) -> Dict[str, Any]:
    """Validate user code before execution.

    Uses AST-based detection to prevent security bypasses:
    - eval (1) - space before parenthesis
    - getattr(__builtins__, "eval") - dynamic access
    - [eval][0]() - list indexing bypass
    - {"f": eval}["f"]() - dict lookup bypass

    Returns:
        Dict with 'valid': bool and 'error': str if invalid
    """
    # Empty string edge case
    if not code or not code.strip():
        return {"valid": True}

    # Size limit: 64KB
    if len(code.encode("utf-8")) > 65536:
        return {"valid": False, "error": "Code size exceeds 64KB limit"}

    # Check for blocked imports and dangerous function calls using AST
    try:
        tree = ast.parse(code)

        # First check for dangerous function calls
        visitor = _DangerousCallVisitor()
        visitor.visit(tree)

        if visitor.dangerous_calls:
            dangerous = ", ".join(set(visitor.dangerous_calls))
            return {"valid": False, "error": f"Blocked function call: {dangerous}"}

        # Check for dangerous function references in data structures
        # These might not be called directly but are still dangerous
        if visitor.dangerous_references:
            # Filter out references that are already in dangerous_calls
            refs = set(visitor.dangerous_references) - set(visitor.dangerous_calls)
            if refs:
                dangerous = ", ".join(refs)
                return {
                    "valid": False,
                    "error": f"Blocked function reference: {dangerous}",
                }

        # Check for blocked imports
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
                except OSError as e:
                    logger.debug(f"Failed to delete temporary file {tmp_path}: {e}")

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
                    analysis_kind=["PEP316"],
                    per_condition_timeout=float(self.timeout),
                    max_iterations=1000,
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


# --- Tool Logic Functions ---


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

    # Find branches by iterating through AST nodes directly
    dedented_code = textwrap.dedent(code)
    branches = []

    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            segment = ast.get_source_segment(dedented_code, node.test)
            if segment:
                branches.append({"line": node.lineno, "condition": segment})
        elif isinstance(node, ast.While):
            segment = ast.get_source_segment(dedented_code, node.test)
            if segment:
                branches.append({"line": node.lineno, "condition": segment})
        elif isinstance(node, ast.For):
            segment = ast.get_source_segment(dedented_code, node.target)
            if segment:
                branches.append(
                    {"line": node.lineno, "condition": f"for {segment} in ..."}
                )

    # Calculate cyclomatic complexity
    complexity = 1  # Base complexity

    for node in ast.walk(tree):
        if isinstance(node, ast.If):
            complexity += 1
            # Count elif branches
            for orelse in node.orelse:
                if isinstance(orelse, ast.If):
                    complexity += 1
        elif isinstance(node, ast.While):
            complexity += 1
        elif isinstance(node, ast.For):
            complexity += 1
        elif isinstance(node, ast.BoolOp):
            complexity += len(node.values) - 1

    return {
        "status": "complete",
        "branches": branches,
        "total_branches": len(branches),
        "reachable_branches": len(branches),
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
    analyzer = SymbolicAnalyzer(timeout_seconds)
    return analyzer.analyze(code, function_name)


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
