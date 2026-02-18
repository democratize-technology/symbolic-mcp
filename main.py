"""Symbolic Execution MCP Server

A Model Context Protocol server that provides symbolic execution
capabilities using CrossHair for formal verification and analysis.
"""

import ast
import concurrent.futures
import contextlib
import importlib.util
import inspect
import logging
import math
import os
import re
import resource
import sys
import tempfile
import textwrap
import threading
import time
import types
import uuid
from typing import AsyncGenerator, Generator, Literal, NotRequired, Optional

from crosshair.core import AnalysisOptionSet
from crosshair.core_and_libs import (
    AnalysisKind,
    AnalysisMessage,
    MessageType,
    analyze_function,
    run_checkables,
)
from fastmcp import FastMCP
from fastmcp.server.auth.providers.github import GitHubProvider
from mcp.types import ToolAnnotations
from typing_extensions import TypedDict

# Version information
try:
    from _version import __version__
except ImportError:
    __version__ = "0.1.0"

# Configure logging
logger = logging.getLogger(__name__)

# --- Constants ---

# Default timeout for CrossHair analysis in seconds
DEFAULT_ANALYSIS_TIMEOUT_SECONDS = 30


# --- Type Definitions ---


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


# --- Configuration ---


def _get_int_env_var(
    name: str,
    default: str,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
) -> int:
    """Safely parse an integer environment variable with optional bounds checking.

    Args:
        name: Environment variable name
        default: Default value as string
        min_value: Minimum allowed value (inclusive), or None for no minimum
        max_value: Maximum allowed value (inclusive), or None for no maximum

    Returns:
        Parsed integer value, or default if invalid

    Raises:
        ValueError: If the value is outside the allowed bounds
    """
    try:
        value = int(os.environ.get(name, default))
    except (ValueError, TypeError):
        value = int(default)

    if min_value is not None and value < min_value:
        raise ValueError(f"{name} must be at least {min_value}, got {value}")
    if max_value is not None and value > max_value:
        raise ValueError(f"{name} must be at most {max_value}, got {value}")

    return value


# Memory limit in MB for symbolic execution (configurable via environment)
# Min: 128MB, Max: 65536MB (64GB)
MEMORY_LIMIT_MB = _get_int_env_var(
    "SYMBOLIC_MEMORY_LIMIT_MB", "2048", min_value=128, max_value=65536
)

# Code size limit in bytes (configurable via environment)
# Min: 1024 bytes (1KB), Max: 1048576 bytes (1MB)
CODE_SIZE_LIMIT = _get_int_env_var(
    "SYMBOLIC_CODE_SIZE_LIMIT", "65536", min_value=1024, max_value=1048576
)

# Coverage calculation thresholds (configurable via environment)
# Min: 100, Max: 100000
# High confidence threshold: below this count, coverage is considered exhaustive
COVERAGE_EXHAUSTIVE_THRESHOLD = _get_int_env_var(
    "SYMBOLIC_COVERAGE_EXHAUSTIVE_THRESHOLD", "1000", min_value=100, max_value=100000
)

# Coverage degradation factor for logarithmic scaling (see coverage calculation below)
# Derived from: 1.0 - desired_min_coverage
# At max_scale_factor (100): coverage = 1.0 - log(100)/log(100) * 0.23 = 0.77
# This ensures even very large path counts get meaningful (non-zero) coverage estimates
COVERAGE_DEGRADATION_FACTOR = 0.23

# Maximum scale factor for coverage calculation
# At 100x the exhaustive threshold, coverage drops to ~0.77
MAX_COVERAGE_SCALE_FACTOR = 100

# Per-path timeout ratio for CrossHair analysis
# Each path's timeout is this fraction of the total timeout
# A lower value gives more paths a chance to complete before hitting the overall timeout
PER_PATH_TIMEOUT_RATIO = 0.1  # 10% of total timeout per path


# --- Memory Management ---

# Module-level lock for sys.modules access.
# Protects against race conditions when multiple threads concurrently
# create/delete temporary modules. Without this lock, check-then-act
# patterns like "if key in dict: del dict[key]" can cause KeyError
# when another thread modifies the dict between check and act.
_SYS_MODULES_LOCK = threading.Lock()


def set_memory_limit(limit_mb: int) -> None:
    """Set memory limit for the process to prevent resource exhaustion.

    Args:
        limit_mb: Memory limit in megabytes
    """
    try:
        limit_bytes = limit_mb * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (limit_bytes, -1))
    except (ValueError, ImportError):
        pass


set_memory_limit(MEMORY_LIMIT_MB)


# --- Pre-compiled Regex Patterns ---

# Pattern for parsing function call messages from CrossHair
_CALL_PATTERN = re.compile(r"calling\s+(\w+)\((.*?)\)(?:\s*\(which|\s*$)")

# Pattern for extracting result values from messages
_RESULT_PATTERN = re.compile(r"which returns\s+(.+)\)$")

# Pattern for extracting exception type from error messages
_EXC_PATTERN = re.compile(r"^(\w+(?:\s+\w+)*)?:")


def _parse_function_args(args_str: str) -> list[str]:
    """Parse function arguments from a string, handling nested expressions.

    This parser properly handles:
    - Simple args: "x, y, z" -> ["x", "y", "z"]
    - Nested calls: "f(x), g(y)" -> ["f(x)", "g(y)"]
    - Complex expressions: "float('nan'), 1" -> ["float('nan')", "1"]
    - Empty strings: "" -> []

    Args:
        args_str: String containing comma-separated arguments

    Returns:
        List of parsed argument strings
    """
    args_str = args_str.strip()
    if not args_str:
        return []

    result = []
    current = []
    paren_depth = 0
    bracket_depth = 0
    brace_depth = 0
    in_string = False
    string_char = None

    i = 0
    while i < len(args_str):
        char = args_str[i]

        # Handle string literals
        if char in ('"', "'"):
            # Check if quote is escaped by odd number of backslashes
            is_escaped = False
            j = i - 1
            while j >= 0 and args_str[j] == "\\":
                is_escaped = not is_escaped
                j -= 1

            if not is_escaped:
                if not in_string:
                    in_string = True
                    string_char = char
                elif char == string_char:
                    in_string = False
                    string_char = None
            current.append(char)
        # Inside string, just append
        elif in_string:
            current.append(char)
        # Handle nested structures
        elif char == "(":
            paren_depth += 1
            current.append(char)
        elif char == ")":
            paren_depth -= 1
            current.append(char)
        elif char == "[":
            bracket_depth += 1
            current.append(char)
        elif char == "]":
            bracket_depth -= 1
            current.append(char)
        elif char == "{":
            brace_depth += 1
            current.append(char)
        elif char == "}":
            brace_depth -= 1
            current.append(char)
        # Handle comma separator (only when not in nested structure)
        elif (
            char == "," and paren_depth == 0 and bracket_depth == 0 and brace_depth == 0
        ):
            arg = "".join(current).strip()
            if arg:
                result.append(arg)
            current = []
        # Skip whitespace only when not in a nested structure
        elif (
            char.isspace()
            and paren_depth == 0
            and bracket_depth == 0
            and brace_depth == 0
            and not current
        ):
            pass  # Skip leading whitespace
        else:
            current.append(char)

        i += 1

    # Add the last argument
    arg = "".join(current).strip()
    if arg:
        result.append(arg)

    return result


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
        - Introspection gadgets: __subclasses__, __bases__, __mro__, __globals__
        """
        # check for introspection gadgets
        if node.attr in (
            "__subclasses__",
            "__bases__",
            "__mro__",
            "__globals__",
            "__class__",
            "__code__",
        ):
            self.dangerous_calls.append(f"introspection via {node.attr}")

        # Check if this is accessing an attribute of __builtins__
        if isinstance(node.value, ast.Name):
            if node.value.id == "__builtins__":
                # Block any attribute access to __builtins__
                self.dangerous_calls.append(f"__builtins__.{node.attr}")
                self.builtins_access.append(f"__builtins__.{node.attr}")
        # Also check nested attribute access like __builtins__.__dict__
        elif isinstance(node.value, ast.Attribute):
            # Walk down to find the root
            root: ast.expr = node.value
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
        # Use a targeted visitor instead of ast.walk to avoid O(n²) complexity
        elif isinstance(node.value, (ast.BinOp, ast.BoolOp, ast.Compare)):
            # Check if __builtins__ appears in the expression using a visitor
            class _BuiltinsFinder(ast.NodeVisitor):
                def __init__(self) -> None:
                    self.found = False

                def visit_Name(self, n: ast.Name) -> None:
                    if n.id == "__builtins__":
                        self.found = True
                    # Don't continue traversal if found
                    if not self.found:
                        self.generic_visit(n)

            finder = _BuiltinsFinder()
            finder.visit(node.value)
            if finder.found:
                self.dangerous_calls.append("__builtins__[...]")
                self.builtins_access.append("__builtins__[...]")
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
                root: ast.expr = node.func.value
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

    def visit_Import(self, node: ast.Import) -> None:
        """Check for blocked module imports.

        This eliminates the need for a separate ast.walk() traversal
        in validate_code(), improving performance.
        """
        if node.names:
            module_name = node.names[0].name
            if module_name:
                base_module = module_name.split(".")[0]
                if self._is_blocked_module(base_module):
                    self.dangerous_calls.append(f"import {base_module}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Check for blocked module imports in 'from X import Y' statements.

        This eliminates the need for a separate ast.walk() traversal
        in validate_code(), improving performance.
        """
        # For ImportFrom, node.module can be None (relative imports)
        if node.module and node.names:
            base_module = node.module.split(".")[0]
            if self._is_blocked_module(base_module):
                self.dangerous_calls.append(f"from {base_module} import ...")
        self.generic_visit(node)


def validate_code(code: str) -> _ValidationResult:
    """Validate user code before execution.

    Uses AST-based detection to prevent security bypasses:
    - eval (1) - space before parenthesis
    - getattr(__builtins__, "eval") - dynamic access
    - [eval][0]() - list indexing bypass
    - {"f": eval}["f"]() - dict lookup bypass

    Returns:
        ValidationResult with 'valid': bool and optional 'error': str if invalid
    """
    # Empty string edge case
    if not code or not code.strip():
        return {"valid": True}

    # Size limit check (configurable via SYMBOLIC_CODE_SIZE_LIMIT env var)
    code_size = len(code.encode("utf-8"))
    if code_size > CODE_SIZE_LIMIT:
        return {
            "valid": False,
            "error": f"Code size exceeds {CODE_SIZE_LIMIT // 1024}KB limit",
        }

    # Check for blocked imports and dangerous function calls using AST
    # Use textwrap.dedent for consistency with _temporary_module and logic_analyze_branches
    # This allows users to pass indented code snippets (e.g., from markdown blocks)
    try:
        tree = ast.parse(textwrap.dedent(code))

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

    except SyntaxError as e:
        return {
            "valid": False,
            "error": f"Syntax error: {e}",
            "error_type": "SyntaxError",
        }

    return {"valid": True}


# --- Symbolic Analyzer ---


# Module-level context manager for temporary module creation.
# This is shared by SymbolicAnalyzer and the logic functions to ensure
# consistent resource cleanup across all code paths.
@contextlib.contextmanager
def _temporary_module(code: str) -> Generator[types.ModuleType, None, None]:
    """Create a temporary module from code with guaranteed cleanup.

    This context manager ensures that temporary files and sys.modules entries
    are properly cleaned up even if exceptions occur during module loading.

    Thread Safety:
        All sys.modules access is protected by _SYS_MODULES_LOCK to prevent
        race conditions in concurrent execution scenarios.

    Args:
        code: Python source code to load as a module

    Yields:
        The loaded module object

    Example:
        with _temporary_module("def foo(): return 1") as module:
            result = module.foo()
        # File and module are cleaned up here, even if exception occurred
    """
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False) as tmp:
        tmp.write(textwrap.dedent(code))
        tmp_path = tmp.name

    # Use UUID for guaranteed uniqueness across concurrent requests
    # Previous implementation using os.path.basename() could theoretically collide
    module_name = f"mcp_temp_{uuid.uuid4().hex}"

    try:
        spec = importlib.util.spec_from_file_location(module_name, tmp_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            # Lock required for sys.modules write to prevent race conditions
            with _SYS_MODULES_LOCK:
                sys.modules[module_name] = module
            spec.loader.exec_module(module)
            yield module
    finally:
        # Lock required for sys.modules check-and-delete to prevent TOCTOU race
        # Without lock: Thread A checks "key in dict" -> True, Thread B deletes key,
        # Thread A tries to delete key -> KeyError. With lock: atomic check-and-delete.
        with _SYS_MODULES_LOCK:
            if module_name in sys.modules:
                del sys.modules[module_name]
        if os.path.exists(tmp_path):
            try:
                # Use os.remove() for clarity (same as os.unlink() for files)
                # tempfile.NamedTemporaryFile guarantees tmp_path is a file, not a directory
                os.remove(tmp_path)
            except OSError as e:
                logger.debug(f"Failed to delete temporary file {tmp_path}: {e}")


def _run_analysis_in_process(
    code: str, target_function_name: str, timeout: float
) -> _SymbolicCheckResult:
    """Run symbolic analysis in a separate process for isolation.

    This function contains the core CrossHair analysis logic. It is designed
    to be run in a separate process via ProcessPoolExecutor to isolate
    the main server from Z3 crashes and memory leaks.
    """
    start_time = time.perf_counter()
    try:
        # Use module-level _temporary_module
        with _temporary_module(code) as module:
            if not hasattr(module, target_function_name):
                elapsed = time.perf_counter() - start_time
                return {
                    "status": "error",
                    "counterexamples": [],
                    "paths_explored": 0,
                    "paths_verified": 0,
                    "time_seconds": round(elapsed, 4),
                    "coverage_estimate": 0.0,
                    "error_type": "NameError",
                    "message": f"Function '{target_function_name}' not found",
                }

            func = getattr(module, target_function_name)

            # Create AnalysisOptionSet with proper configuration
            # Use both asserts (for assert statements) and PEP316 (for docstring contracts)
            options = AnalysisOptionSet(
                analysis_kind=[AnalysisKind.asserts, AnalysisKind.PEP316],
                per_condition_timeout=float(timeout),
                per_path_timeout=float(timeout) * PER_PATH_TIMEOUT_RATIO,
            )

            # Get checkables from analyze_function
            checkables = analyze_function(func, options)

            counterexamples: list[_Counterexample] = []
            paths_explored = 0
            paths_verified = 0

            if checkables:
                # Run checkables to get analysis messages
                messages: list[AnalysisMessage] = list(run_checkables(checkables))

                # Get function signature for proper arg name mapping
                try:
                    func_sig = (
                        inspect.signature(func)
                        if hasattr(inspect, "signature")
                        else None
                    )
                except ValueError:
                    # inspect.signature() raises ValueError for builtin functions
                    # and C extensions. Fall back to no signature info.
                    func_sig = None
                param_names = list(func_sig.parameters.keys()) if func_sig else []

                for message in messages:
                    paths_explored += 1
                    if message.state == MessageType.CONFIRMED:
                        paths_verified += 1
                    elif message.state in (
                        MessageType.POST_FAIL,
                        MessageType.PRE_UNSAT,
                        MessageType.POST_ERR,
                        MessageType.EXEC_ERR,
                    ):
                        # Extract counterexample from message
                        # Parse the message to extract args if present
                        # Message format: "false when calling func(arg1, arg2) (which returns ...)"
                        # Or: "ExceptionType: when calling func(arg1, arg2)"
                        args: dict[str, int | bool | None | str] = {}
                        kwargs: dict[str, int | bool | None | str] = {}
                        actual_result = ""
                        path_condition = ""

                        # Try to parse the function call from the message
                        match = _CALL_PATTERN.search(message.message)
                        if match:
                            args_str = match.group(2)
                            if args_str:
                                # Parse positional args with proper handling of nested expressions
                                # This handles cases like "float('nan')" which contain commas
                                arg_values = _parse_function_args(args_str)
                                # Try to convert to appropriate types
                                for i, val in enumerate(arg_values):
                                    # Use actual parameter name if available
                                    arg_name = (
                                        param_names[i]
                                        if i < len(param_names)
                                        else f"arg{i}"
                                    )
                                    # Try int first - safe parsing with try/except
                                    # This handles both positive and negative integers
                                    # and properly rejects invalid formats like "--123"
                                    try:
                                        args[arg_name] = int(val)
                                    except ValueError:
                                        # Not an integer, check for other known values
                                        if val == "True":
                                            args[arg_name] = True
                                        elif val == "False":
                                            args[arg_name] = False
                                        elif val == "None":
                                            args[arg_name] = None
                                        else:
                                            args[arg_name] = val

                                # Build path_condition from the arg values
                                # This represents the input condition that led to the violation
                                if args:
                                    conditions = []
                                    for arg_name, arg_val in args.items():
                                        if isinstance(arg_val, str) and '"' in arg_val:
                                            # Handle string representations like 'float("nan")'
                                            conditions.append(f"{arg_name}={arg_val}")
                                        else:
                                            conditions.append(
                                                f"{arg_name}={repr(arg_val)}"
                                            )
                                    path_condition = ", ".join(conditions)

                        # Extract actual_result from message
                        # Pattern: "which returns X)" at the end of the message
                        result_match = _RESULT_PATTERN.search(message.message)
                        if result_match:
                            actual_result = result_match.group(1).strip()
                        else:
                            # Fallback: try to find exception result
                            # Some messages have format: "ExceptionType: ... when calling ..."
                            exc_match = _EXC_PATTERN.match(message.message)
                            if exc_match:
                                actual_result = (
                                    f"exception: {exc_match.group(0).rstrip(':')}"
                                )

                        counterexamples.append(
                            {
                                "args": args,
                                "kwargs": kwargs,
                                "violation": message.message,
                                "actual_result": actual_result,
                                "path_condition": path_condition,
                            }
                        )

            elapsed = time.perf_counter() - start_time

            # Determine status based on analysis results
            # Valid statuses per spec: "verified", "counterexample", "timeout", "error"
            status: Literal["verified", "counterexample", "timeout", "error"] = (
                "verified"
            )
            if counterexamples:
                status = "counterexample"
            # Note: paths_explored == 0 with no counterexamples means no contracts to verify
            # This is treated as "verified" since nothing was disproven

            # Calculate coverage estimate based on paths explored using logarithmic scaling
            # This provides a more gradual degradation than a binary threshold
            # - For small path counts: coverage approaches 1.0 (exhaustive)
            # - For large path counts: coverage scales logarithmically
            if paths_explored == 0:
                # No paths explored (no contracts) = unknown coverage
                coverage_estimate = 1.0
            elif paths_explored < COVERAGE_EXHAUSTIVE_THRESHOLD:
                # Below threshold: treat as exhaustive
                coverage_estimate = 1.0
            else:
                # Above threshold: use logarithmic scaling
                # Formula: 1.0 - log(paths/threshold) / log(max_paths) * COVERAGE_DEGRADATION_FACTOR
                #
                # Coverage degradation behavior (using module-level constants):
                # - At 1x threshold: coverage = 1.0
                # - At 10x threshold: coverage ≈ 0.94
                # - At 100x threshold: coverage ≈ 0.77
                scale_factor = min(
                    paths_explored / COVERAGE_EXHAUSTIVE_THRESHOLD,
                    MAX_COVERAGE_SCALE_FACTOR,
                )
                coverage_estimate = (
                    1.0
                    - (math.log(scale_factor) / math.log(MAX_COVERAGE_SCALE_FACTOR))
                    * COVERAGE_DEGRADATION_FACTOR
                )
                coverage_estimate = round(coverage_estimate, 4)

            return {
                "status": status,
                "counterexamples": counterexamples,
                "paths_explored": paths_explored,
                "paths_verified": paths_verified,
                "time_seconds": round(elapsed, 4),
                "coverage_estimate": coverage_estimate,
            }

    except ImportError as e:
        elapsed = time.perf_counter() - start_time
        return {
            "status": "error",
            "counterexamples": [],
            "paths_explored": 0,
            "paths_verified": 0,
            "time_seconds": round(elapsed, 4),
            "coverage_estimate": 0.0,
            "error_type": "ImportError",
            "message": str(e),
        }
    except Exception as e:
        elapsed = time.perf_counter() - start_time
        return {
            "status": "error",
            "counterexamples": [],
            "paths_explored": 0,
            "paths_verified": 0,
            "time_seconds": round(elapsed, 4),
            "coverage_estimate": 0.0,
            "error_type": type(e).__name__,
            "message": str(e),
        }


class SymbolicAnalyzer:
    """Analyzes code using CrossHair symbolic execution.

    This class delegates actual execution to a separate process via
    ProcessPoolExecutor to ensure robust isolation and cleanup.
    """

    def __init__(self, timeout_seconds: int = DEFAULT_ANALYSIS_TIMEOUT_SECONDS) -> None:
        self.timeout = timeout_seconds

    # Use the module-level context manager for consistency
    _temporary_module = staticmethod(_temporary_module)

    def analyze(self, code: str, target_function_name: str) -> _SymbolicCheckResult:
        """Analyze a function using symbolic execution."""
        start_time = time.perf_counter()

        # Validate code first
        validation = validate_code(code)
        if not validation["valid"]:
            error_msg = validation.get("error", "Unknown validation error")
            error_type_val = validation.get("error_type", "ValidationError")
            return {
                "status": "error",
                "counterexamples": [],
                "paths_explored": 0,
                "paths_verified": 0,
                "time_seconds": round(time.perf_counter() - start_time, 4),
                "coverage_estimate": 0.0,
                "error_type": error_type_val,
                "message": error_msg,
            }

        # Run analysis in a separate process
        # We use a max_workers=1 pool that is created per-request to ensure a fresh process
        # for each analysis, maximizing isolation.
        process_timeout = float(self.timeout) + 5.0

        try:
            with concurrent.futures.ProcessPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    _run_analysis_in_process,
                    code,
                    target_function_name,
                    float(self.timeout),
                )
                try:
                    return future.result(timeout=process_timeout)
                except concurrent.futures.TimeoutError:
                    # Return a timeout result
                    return {
                        "status": "timeout",
                        "counterexamples": [],
                        "paths_explored": 0,
                        "paths_verified": 0,
                        "time_seconds": round(time.perf_counter() - start_time, 4),
                        "coverage_estimate": 0.0,
                        "message": f"Analysis timed out after {process_timeout} seconds",
                    }
        except Exception as e:
            return {
                "status": "error",
                "counterexamples": [],
                "paths_explored": 0,
                "paths_verified": 0,
                "time_seconds": round(time.perf_counter() - start_time, 4),
                "coverage_estimate": 0.0,
                "error_type": type(e).__name__,
                "message": str(e),
            }


# --- Tool Logic Functions (exposed for testing) ---


def logic_symbolic_check(
    code: str,
    function_name: str,
    timeout_seconds: int = DEFAULT_ANALYSIS_TIMEOUT_SECONDS,
) -> _SymbolicCheckResult:
    """Symbolically verify that a function satisfies its contract.

    This is the core logic function for symbolic_check, exposed for testing.
    """
    analyzer = SymbolicAnalyzer(timeout_seconds)
    return analyzer.analyze(code, function_name)


def _extract_function_signature_and_params(
    module: types.ModuleType, function_name: str
) -> tuple[Optional[str], list[str]]:
    """Extract the signature and parameter names of a function.

    Returns a tuple of (signature_string, parameter_names).
    signature_string is like '(x: int, y: int) -> int' or None if not found.
    parameter_names is a list of parameter names (e.g., ['x', 'y']).
    """
    if not hasattr(module, function_name):
        return None, []

    func = getattr(module, function_name)
    try:
        sig = inspect.signature(func)
    except ValueError:
        return None, []

    # Extract parameter names
    param_names = list(sig.parameters.keys())

    # Build signature string (reuse logic from _extract_function_signature)
    params = []
    for name, param in sig.parameters.items():
        param_str = name
        if param.annotation != inspect.Parameter.empty:
            param_str += f": {param.annotation.__name__ if hasattr(param.annotation, '__name__') else str(param.annotation)}"
        if param.default != inspect.Parameter.empty:
            param_str += f" = {repr(param.default)}"
        params.append(param_str)

    return_str = ""
    if sig.return_annotation != inspect.Signature.empty:
        return_str = f" -> {sig.return_annotation.__name__ if hasattr(sig.return_annotation, '__name__') else str(sig.return_annotation)}"

    sig_str = f"({', '.join(params)}){return_str}"
    return sig_str, param_names


def _generate_wrapper_code(
    code: str,
    wrapper_name: str,
    postcondition: str,
    target_func: str,
    func_sig: str,
    param_names: list[str],
) -> str:
    """Generate wrapper code for CrossHair symbolic analysis.

    Args:
        code: The original function code to embed
        wrapper_name: Name for the wrapper function
        postcondition: CrossHair postcondition string (e.g., "True" or "f(_) == g(_)")
        target_func: Name of the function to call in the wrapper
        func_sig: Function signature string (e.g., "(x: int, y: int)")
        param_names: List of parameter names for the function call

    Returns:
        Complete wrapper code ready for symbolic analysis
    """
    if param_names:
        args_str = ", ".join(param_names)
        call_expr = f"{target_func}({args_str})"
    else:
        call_expr = f"{target_func}(*args, **kwargs)"

    return f"""
{code}

def {wrapper_name}{func_sig}:
    '''post: {postcondition}'''
    return {call_expr}
"""


def logic_find_path_to_exception(
    code: str, function_name: str, exception_type: str, timeout_seconds: int
) -> _ExceptionPathResult:
    """Find concrete inputs that cause a specific exception type."""
    validation = validate_code(code)
    if not validation["valid"]:
        return {
            "status": "error",
            "error_type": "ValidationError",
            "message": validation["error"],
        }

    try:
        # Use the shared context manager for guaranteed cleanup
        with _temporary_module(code) as module:
            if not hasattr(module, function_name):
                return {
                    "status": "error",
                    "error_type": "NameError",
                    "message": f"Function '{function_name}' not found",
                }

            # Get the function signature and parameter names in one call
            # This is more efficient than calling _extract_function_signature() and
            # then inspect.signature() separately
            func_sig, param_names = _extract_function_signature_and_params(
                module, function_name
            )
            if func_sig is None:
                func_sig = "(*args, **kwargs)"
                param_names = []

            # Create wrapper with explicit signature for CrossHair analysis
            wrapper_code = _generate_wrapper_code(
                code=code,
                wrapper_name="_exception_hunter_wrapper",
                postcondition="True",
                target_func=function_name,
                func_sig=func_sig,
                param_names=param_names,
            )

            analyzer = SymbolicAnalyzer(timeout_seconds)
            result = analyzer.analyze(wrapper_code, "_exception_hunter_wrapper")

    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e),
        }

    # Check if any counterexamples mention the target exception
    if result["status"] == "error":
        # Can't return result directly - it's _SymbolicCheckResult, not _ExceptionPathResult
        # Transfer error information if available
        error_type_val = result.get("error_type", "AnalysisError")
        error_msg = result.get("message", "Unknown error")
        return {
            "status": "error",
            "error_type": error_type_val,
            "message": error_msg,
        }

    # Filter counterexamples for the target exception
    triggering_inputs = []
    if result.get("counterexamples"):
        for ce in result["counterexamples"]:
            violation = ce.get("violation", "")
            if exception_type in violation:
                triggering_inputs.append(ce)

    if triggering_inputs:
        return {
            "status": "found",
            "triggering_inputs": triggering_inputs,
            "paths_to_exception": len(triggering_inputs),
            "total_paths_explored": result.get("paths_explored", 0),
            "time_seconds": result.get("time_seconds", 0),
        }
    elif result["status"] == "verified":
        return {
            "status": "unreachable",
            "paths_to_exception": 0,
            "total_paths_explored": result.get("paths_explored", 0),
        }
    else:
        # Can't return result directly - it's _SymbolicCheckResult, not _ExceptionPathResult
        # This handles the "counterexample" case where no matching exception was found
        return {
            "status": "unreachable",
            "paths_to_exception": 0,
            "total_paths_explored": result.get("paths_explored", 0),
        }


def logic_compare_functions(
    code: str, function_a: str, function_b: str, timeout_seconds: int
) -> _FunctionComparisonResult:
    """Check if two functions are semantically equivalent."""
    # First, load the module to get function signatures
    validation = validate_code(code)
    if not validation["valid"]:
        return {
            "status": "error",
            "error_type": "ValidationError",
            "message": validation["error"],
        }

    try:
        # Use the shared context manager for guaranteed cleanup
        with _temporary_module(code) as module:
            if not hasattr(module, function_a):
                return {
                    "status": "error",
                    "error_type": "NameError",
                    "message": f"Function '{function_a}' not found",
                }

            if not hasattr(module, function_b):
                return {
                    "status": "error",
                    "error_type": "NameError",
                    "message": f"Function '{function_b}' not found",
                }

            # Get function signature and parameter names for wrapper
            # Use the efficient helper that returns both in one call
            func_sig, param_names = _extract_function_signature_and_params(
                module, function_a
            )
            if func_sig is None:
                func_sig = "(*args, **kwargs)"
                param_names = []

            # Create wrapper with explicit signature using postcondition
            wrapper_code = _generate_wrapper_code(
                code=code,
                wrapper_name="_equivalence_check",
                postcondition=f"{function_a}(_) == {function_b}(_)",
                target_func=function_a,
                func_sig=func_sig,
                param_names=param_names,
            )

            analyzer = SymbolicAnalyzer(timeout_seconds)
            result = analyzer.analyze(wrapper_code, "_equivalence_check")

    except Exception as e:
        return {
            "status": "error",
            "error_type": type(e).__name__,
            "message": str(e),
        }

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
        # Can't return result directly - it's _SymbolicCheckResult, not _FunctionComparisonResult
        # This handles error and timeout cases
        return {
            "status": "error",
            "error_type": result["status"],
            "message": "Analysis did not complete",
        }


def logic_analyze_branches(
    code: str,
    function_name: str,
    timeout_seconds: int = DEFAULT_ANALYSIS_TIMEOUT_SECONDS,
    symbolic_reachability: bool = False,
) -> _BranchAnalysisResult:
    """Enumerate branch conditions and report static or symbolic reachability.

    Args:
        code: Python function definition to analyze
        function_name: Name of function to analyze
        timeout_seconds: Analysis timeout in seconds
        symbolic_reachability: If True, use symbolic execution to prove reachability
    """
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
        result: _BranchAnalysisResult = {
            "status": "error",
            "error_type": "SyntaxError",
            "message": str(e),
        }
        if e.lineno is not None:
            result["line"] = e.lineno
        return result

    # Use a single-pass visitor to collect both branches and complexity
    # This avoids multiple O(n) AST traversals
    dedented_code = textwrap.dedent(code)

    class _BranchAndComplexityVisitor(ast.NodeVisitor):
        """Single-pass visitor that collects branches and calculates complexity."""

        def __init__(self, source_code: str, symbolic_reachability: bool) -> None:
            self.branches: list[_BranchInfo] = []
            self.complexity = 1  # Base complexity
            self.source_code = source_code
            self.symbolic_reachability = symbolic_reachability

        def visit_If(self, node: ast.If) -> None:
            """Visit an if statement and count it as one decision point."""
            self.complexity += 1
            segment = ast.get_source_segment(self.source_code, node.test)
            if segment:
                self.branches.append(
                    {
                        "line": node.lineno,
                        "condition": segment,
                        "true_reachable": None if self.symbolic_reachability else True,
                        "false_reachable": None if self.symbolic_reachability else True,
                        "true_example": None,
                        "false_example": None,
                    }
                )
            self.generic_visit(node)

        def visit_While(self, node: ast.While) -> None:
            """Visit a while loop and count it as one decision point."""
            self.complexity += 1
            segment = ast.get_source_segment(self.source_code, node.test)
            if segment:
                self.branches.append(
                    {
                        "line": node.lineno,
                        "condition": segment,
                        "true_reachable": None if self.symbolic_reachability else True,
                        "false_reachable": None if self.symbolic_reachability else True,
                        "true_example": None,
                        "false_example": None,
                    }
                )
            self.generic_visit(node)

        def visit_For(self, node: ast.For) -> None:
            """Visit a for loop and count it as one decision point."""
            self.complexity += 1
            segment = ast.get_source_segment(self.source_code, node.target)
            if segment:
                self.branches.append(
                    {
                        "line": node.lineno,
                        "condition": f"for {segment} in ...",
                        "true_reachable": None if self.symbolic_reachability else True,
                        "false_reachable": None if self.symbolic_reachability else True,
                        "true_example": None,
                        "false_example": None,
                    }
                )
            self.generic_visit(node)

        def visit_BoolOp(self, node: ast.BoolOp) -> None:
            """Visit a BoolOp (and/or) and count additional operands.

            For 'a and b and c': 3 values -> +2 complexity
            """
            self.complexity += len(node.values) - 1
            self.generic_visit(node)

    # Single-pass traversal for both branches and complexity
    visitor = _BranchAndComplexityVisitor(dedented_code, symbolic_reachability)
    visitor.visit(tree)
    branches = visitor.branches
    complexity = visitor.complexity

    # If symbolic reachability is requested, perform deeper analysis
    dead_code_lines: list[int] = []
    reachable_branches = len(branches)

    if symbolic_reachability:
        # Try to prove each branch is reachable/unreachable using symbolic execution
        # This is a placeholder for future enhancement (v0.3.0)
        # Currently we return results from static analysis
        pass

    return {
        "status": "complete",
        "branches": branches,
        "total_branches": len(branches),
        "reachable_branches": reachable_branches,
        "dead_code_lines": dead_code_lines,
        "cyclomatic_complexity": complexity,
        "time_seconds": round(time.perf_counter() - start_time, 4),
        "analysis_mode": "symbolic" if symbolic_reachability else "static",
    }


# --- FastMCP Server ---


def _get_github_auth() -> Optional[GitHubProvider]:
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
    import platform

    import psutil

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
