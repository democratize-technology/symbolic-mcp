# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Symbolic MCP Contributors

"""Symbolic execution analyzer using CrossHair.

This module contains the core symbolic analysis engine, including
the SymbolicAnalyzer class and process execution utilities.
"""

import concurrent.futures
import contextlib
import importlib.util
import inspect
import logging
import math
import os
import sys
import tempfile
import textwrap
import time
import types
import uuid
from typing import Generator, Literal

from crosshair.core import AnalysisOptionSet
from crosshair.core_and_libs import (
    AnalysisKind,
    AnalysisMessage,
    MessageType,
    analyze_function,
    run_checkables,
)

from symbolic_mcp.config import (
    _SYS_MODULES_LOCK,
    COVERAGE_DEGRADATION_FACTOR,
    COVERAGE_EXHAUSTIVE_THRESHOLD,
    DEFAULT_ANALYSIS_TIMEOUT_SECONDS,
    MAX_COVERAGE_SCALE_FACTOR,
    PER_PATH_TIMEOUT_RATIO,
)
from symbolic_mcp.parsing import (
    _CALL_PATTERN,
    _EXC_PATTERN,
    _RESULT_PATTERN,
    _parse_function_args,
)
from symbolic_mcp.security import validate_code
from symbolic_mcp.types import _Counterexample, _SymbolicCheckResult

# Configure logging
logger = logging.getLogger(__name__)


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


__all__ = [
    "_temporary_module",
    "_run_analysis_in_process",
    "SymbolicAnalyzer",
]
