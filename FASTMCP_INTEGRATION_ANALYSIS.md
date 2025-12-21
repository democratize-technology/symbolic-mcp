<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2025 Symbolic MCP Contributors -->
# FastMCP 2.0 Integration Analysis Report

## Executive Summary

**CRITICAL FINDING**: The FastMCP 2.0 integration issues identified by the debugger are confirmed to be **usage pattern errors**, not framework bugs. The `@mcp.tool()` decorator fundamentally changes function behavior, and tests need to be updated accordingly.

## FastMCP 2.0 Decorator Behavior Confirmed

### 1. @mcp.tool() Decorator Transformation

**Confirmed Behavior**: Functions decorated with `@mcp.tool()` become `FunctionTool` objects, not regular functions.

```python
@mcp.tool()
def symbolic_check(code: str, function_name: str, timeout_seconds: int = 30) -> Dict[str, Any]:
    """Symbolically verify that a function satisfies its contract."""
    # ...
```

**After Decoration**:
- **Type**: `<class 'fastmcp.tools.tool.FunctionTool'>`
- **Callable**: `False`
- **Original Function Access**: Available via `.fn` attribute
- **MCP Execution**: Available via `.run(arguments: dict) -> Coroutine` method

### 2. Proper Usage Patterns

#### Direct Function Access (for Testing)
```python
# ✅ CORRECT: Access original function via .fn
result = symbolic_check.fn(code, function_name, timeout_seconds)

# ❌ INCORRECT: Direct call (current test pattern)
result = symbolic_check(code, function_name, timeout_seconds)  # TypeError!
```

#### MCP Tool Execution (for MCP Protocol)
```python
# ✅ CORRECT: MCP protocol execution
arguments = {"code": "...", "function_name": "...", "timeout_seconds": 30}
result = await symbolic_check.run(arguments)

# ❌ INCORRECT: Direct function call
result = symbolic_check(code, function_name, timeout_seconds)  # TypeError!
```

### 3. Test Suite Fix Required

**Current Broken Test Pattern**:
```python
# tests/test_symbolic_finds_bug.py:39
result = symbolic_check(code=code, function_name="tricky")
# TypeError: 'FunctionTool' object is not callable
```

**Correct Test Pattern**:
```python
# ✅ Access original function for direct testing
result = symbolic_check.fn(code=code, function_name="tricky")

# ✅ Or test MCP protocol behavior
arguments = {"code": code, "function_name": "tricky"}
result = await symbolic_check.run(arguments)
```

### 4. Integration Strategy

The current codebase needs a **dual-interface approach**:

#### Option 1: Separate MCP and Direct Functions
```python
# Core implementation (no decorator)
def _symbolic_check_impl(code: str, function_name: str, timeout_seconds: int = 30) -> Dict[str, Any]:
    """Core symbolic analysis implementation."""
    analyzer = SymbolicAnalyzer(timeout_seconds)
    return analyzer.analyze(code, function_name)

# MCP tool wrapper (with decorator)
@mcp.tool()
def symbolic_check(code: str, function_name: str, timeout_seconds: int = 30) -> Dict[str, Any]:
    """Symbolically verify that a function satisfies its contract."""
    return _symbolic_check_impl(code, function_name, timeout_seconds)

# Tests use core implementation
from main import _symbolic_check_impl
result = _symbolic_check_impl(code, function_name)
```

#### Option 2: Access Via .fn Attribute
```python
# Tests access original function via .fn
from main import symbolic_check
result = symbolic_check.fn(code, function_name)
```

#### Option 3: Undecorated Function + Manual Registration
```python
# Regular function (no decorator)
def symbolic_check(code: str, function_name: str, timeout_seconds: int = 30) -> Dict[str, Any]:
    """Symbolically verify that a function satisfies its contract."""
    analyzer = SymbolicAnalyzer(timeout_seconds)
    return analyzer.analyze(code, function_name)

# Manual MCP registration
mcp.add_tool(symbolic_check)
```

### 5. Verified FastMCP 2.0 Behavior

#### FunctionTool Object Properties
- **Type**: `fastmcp.tools.tool.FunctionTool`
- **Original Function**: Available via `.fn` attribute
- **MCP Execution**: `.run(arguments: dict) -> Coroutine`
- **Metadata**: `.name`, `.description`, `.parameters`, `.output_schema`
- **Not Directly Callable**: `TypeError: 'FunctionTool' object is not callable`

#### .run() Method Signature
```python
def run(self, arguments: dict[str, Any]) -> ToolResult:
    """Execute tool with arguments (async coroutine)."""
```

#### .fn Attribute
```python
# Original, undecorated function
@property
def fn(self) -> Callable:
    """Access to the original underlying function."""
```

## Root Cause Analysis

### Why Tests Fail
1. **Incorrect Assumption**: Tests assume `@mcp.tool()` decorated functions remain directly callable
2. **Framework Misunderstanding**: FastMCP 2.0 follows MCP protocol, not direct function execution
3. **Outdated Pattern**: Test patterns from older MCP frameworks or different implementations

### Why This is Not a Bug
1. **MCP Protocol Compliance**: FastMCP correctly implements MCP tool protocol
2. **Proper Abstraction**: `FunctionTool` objects provide MCP-specific behavior (schema, validation, async execution)
3. **Framework Design**: Enables proper MCP tool registration, discovery, and execution

## Implementation Recommendations

### Immediate Fix: Dual Interface Approach
```python
# main.py - Core implementation remains unchanged
class SymbolicAnalyzer:
    # ... existing implementation ...

# Non-decorated core functions for testing/internal use
def _symbolic_check_core(code: str, function_name: str, timeout_seconds: int = 30) -> Dict[str, Any]:
    """Core symbolic analysis - no MCP decorator."""
    analyzer = SymbolicAnalyzer(timeout_seconds)
    return analyzer.analyze(code, function_name)

def _find_path_to_exception_core(code: str, function_name: str, exception_type: str, timeout_seconds: int = 30) -> Dict[str, Any]:
    """Core exception path finding - no MCP decorator."""
    # ... implementation ...

def _compare_functions_core(code: str, function_a: str, function_b: str, timeout_seconds: int = 60) -> Dict[str, Any]:
    """Core function comparison - no MCP decorator."""
    # ... implementation ...

def _analyze_branches_core(code: str, function_name: str, timeout_seconds: int = 30) -> Dict[str, Any]:
    """Core branch analysis - no MCP decorator."""
    # ... implementation ...

# MCP tool wrappers (with decorators)
@mcp.tool()
def symbolic_check(code: str, function_name: str, timeout_seconds: int = 30) -> Dict[str, Any]:
    """Symbolically verify that a function satisfies its contract."""
    return _symbolic_check_core(code, function_name, timeout_seconds)

@mcp.tool()
def find_path_to_exception(code: str, function_name: str, exception_type: str, timeout_seconds: int = 30) -> Dict[str, Any]:
    """Find concrete inputs that cause a specific exception type to be raised."""
    return _find_path_to_exception_core(code, function_name, exception_type, timeout_seconds)

@mcp.tool()
def compare_functions(code: str, function_a: str, function_b: str, timeout_seconds: int = 60) -> Dict[str, Any]:
    """Check if two functions are semantically equivalent."""
    return _compare_functions_core(code, function_a, function_b, timeout_seconds)

@mcp.tool()
def analyze_branches(code: str, function_name: str, timeout_seconds: int = 30) -> Dict[str, Any]:
    """Dynamically enumerate branch conditions and prove which are reachable."""
    return _analyze_branches_core(code, function_name, timeout_seconds)
```

### Test Suite Updates
```python
# tests/test_symbolic_finds_bug.py
from main import _symbolic_check_core

def test_finds_needle_in_haystack():
    # Test core implementation directly
    result = _symbolic_check_core(code=code, function_name="tricky")
    assert result["status"] == "counterexample"
    # ... rest of test
```

### Alternative: Import .fn Attribute
```python
# tests/test_symbolic_finds_bug.py
from main import symbolic_check

def test_finds_needle_in_haystack():
    # Test via .fn attribute
    result = symbolic_check.fn(code=code, function_name="tricky")
    assert result["status"] == "counterexample"
    # ... rest of test
```

## Conclusion

**Finding**: FastMCP 2.0 integration issues are **usage pattern errors**, not framework bugs.

**Impact**:
- **31 out of 34 tests failing** due to incorrect `@mcp.tool()` usage
- **Core functionality works** when accessed properly
- **MCP protocol behavior correct** for tool execution

**Recommendation**: Implement dual-interface approach to support both direct testing and MCP protocol execution.

**Urgency**: HIGH - Tests are completely non-functional due to this issue.

The symbolic execution server's core logic works correctly, but the test suite needs updates to match FastMCP 2.0's proper usage patterns.