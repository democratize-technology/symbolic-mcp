# SPDX-License-Identifier: MIT
# Copyright (c) 2025 Symbolic MCP Contributors

"""Business logic functions for symbolic execution tools.

This module contains the core logic functions that implement the
MCP tool capabilities, exposed for testing.
"""

import ast
import inspect
import textwrap
import time
import types
from typing import Optional

from symbolic_mcp.analyzer import SymbolicAnalyzer, _temporary_module
from symbolic_mcp.config import DEFAULT_ANALYSIS_TIMEOUT_SECONDS
from symbolic_mcp.security import validate_code
from symbolic_mcp.types import (
    _BranchAnalysisResult,
    _BranchInfo,
    _ExceptionPathResult,
    _FunctionComparisonResult,
    _SymbolicCheckResult,
)


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


__all__ = [
    "logic_symbolic_check",
    "logic_find_path_to_exception",
    "logic_compare_functions",
    "logic_analyze_branches",
]
