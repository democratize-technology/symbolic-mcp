# API Reference

Complete reference for all tools provided by the Symbolic MCP server.

## Overview

The Symbolic MCP server provides five core tools for symbolic execution analysis:

1. **symbolic_check** - Verify function contracts
2. **find_path_to_exception** - Find inputs causing exceptions
3. **compare_functions** - Check semantic equivalence
4. **analyze_branches** - Enumerate branch conditions
5. **health_check** - Server health monitoring

---

## Tools

### symbolic_check

Symbolically verify that a function satisfies its contract using preconditions and postconditions.

**Signature:**
```python
symbolic_check(
    code: str,
    function_name: str,
    timeout_seconds: int = 30
) -> Dict[str, Any]
```

**Parameters:**
- `code` (str): Python source code containing the function to verify
- `function_name` (str): Name of the function to analyze
- `timeout_seconds` (int, optional): Maximum execution time in seconds (default: 30)

**Returns:**
Dictionary containing:
- `status` (str): "verified", "counterexample", "timeout", or "error"
- `counterexamples` (list): List of counterexamples if contract violations found
- `paths_explored` (int): Total execution paths analyzed
- `paths_verified` (int): Paths that passed all checks
- `time_seconds` (float): Time taken for analysis
- `coverage_estimate` (float): Estimated fraction of paths explored (0.0-1.0)

**Example:**
```python
result = symbolic_check("""
def divide(x: int, y: int) -> float:
    '''
    pre: y != 0
    post: __return__ == x / y
    '''
    return x / y
""", "divide", 30)
```

**Raises:**
- `ValueError`: Invalid Python code or missing function
- `TimeoutError`: Execution exceeds timeout_seconds

---

### find_path_to_exception

Find concrete inputs that cause a specific exception type to be raised.

**Signature:**
```python
find_path_to_exception(
    code: str,
    function_name: str,
    exception_type: str,
    timeout_seconds: int = 30
) -> Dict[str, Any]
```

**Parameters:**
- `code` (str): Python source code containing the function
- `function_name` (str): Name of the function to analyze
- `exception_type` (str): Full exception class name (e.g., "ValueError", "ZeroDivisionError")
- `timeout_seconds` (int, optional): Maximum execution time in seconds (default: 30)

**Returns:**
Dictionary containing:
- `status` (str): "found", "unreachable", or "error"
- `triggering_inputs` (list): List of counterexamples causing the exception (if found)
- `paths_to_exception` (int): Number of paths that trigger the exception
- `total_paths_explored` (int): Total execution paths analyzed
- `time_seconds` (float): Time taken for analysis

**Example:**
```python
result = find_path_to_exception("""
def parse_int(s: str) -> int:
    return int(s)
""", "parse_int", "ValueError", 30)
# Returns counterexample like: {"s": "not_a_number"}
```

**Raises:**
- `ValueError`: Invalid exception type or missing function
- `TimeoutError`: Execution exceeds timeout_seconds

---

### compare_functions

Check if two functions are semantically equivalent for all possible inputs.

**Signature:**
```python
compare_functions(
    code: str,
    function_a: str,
    function_b: str,
    timeout_seconds: int = 60
) -> Dict[str, Any]
```

**Parameters:**
- `code` (str): Python source code containing both functions
- `function_a` (str): Name of the first function
- `function_b` (str): Name of the second function
- `timeout_seconds` (int, optional): Maximum execution time in seconds (default: 60)

**Returns:**
Dictionary containing:
- `status` (str): "equivalent", "different", or "error"
- `distinguishing_input` (dict): Input where functions differ (if different)
- `paths_compared` (int): Number of paths analyzed for equivalence
- `confidence` (str): "proven", "high", or "partial"
- `error_type` (str): Error type if status is "error"
- `message` (str): Human-readable comparison result

**Example:**
```python
result = compare_functions("""
def add_v1(x: int, y: int) -> int:
    return x + y

def add_v2(x: int, y: int) -> int:
    return y + x
""", "add_v1", "add_v2", 60)
# Returns: {"status": "equivalent", "confidence": "proven"}
```

**Raises:**
- `ValueError`: Missing function or incompatible signatures
- `TimeoutError`: Execution exceeds timeout_seconds

---

### analyze_branches

Enumerate all branch conditions in a function and report static reachability analysis.

**Signature:**
```python
analyze_branches(
    code: str,
    function_name: str,
    timeout_seconds: int = 30,
    symbolic_reachability: bool = False
) -> Dict[str, Any]
```

**Parameters:**
- `code` (str): Python source code containing the function
- `function_name` (str): Name of the function to analyze
- `timeout_seconds` (int, optional): Maximum execution time in seconds (default: 30)
- `symbolic_reachability` (bool, optional): Use symbolic execution to prove reachability (default: False)

**Returns:**
Dictionary containing:
- `status` (str): "complete" or "error"
- `branches` (list): List of branch conditions with line numbers and reachability
- `total_branches` (int): Total number of conditional branches found
- `reachable_branches` (int): Number of reachable branches
- `dead_code_lines` (list): Line numbers of unreachable code
- `cyclomatic_complexity` (int): McCabe complexity score
- `time_seconds` (float): Time taken for analysis
- `analysis_mode` (str): "static" or "symbolic"

**Example:**
```python
result = analyze_branches("""
def classify(x: int) -> str:
    if x > 0:
        return "positive"
    elif x < 0:
        return "negative"
    else:
        return "zero"
""", "classify", 30)
```

**Raises:**
- `ValueError`: Invalid code or missing function
- `TimeoutError`: Execution exceeds timeout_seconds

---

### health_check

Production monitoring and health check for the Symbolic Execution MCP server.

**Signature:**
```python
health_check() -> Dict[str, Any]
```

**Parameters:**
None

**Returns:**
Dictionary containing comprehensive server health information:
- `status` (str): Overall health status ("healthy")
- `version` (str): Symbolic MCP server version
- `python_version` (str): Python interpreter version
- `crosshair_version` (str): CrossHair library version
- `z3_version` (str): Z3 solver version
- `platform` (str): Operating system and architecture
- `memory_usage_mb` (float): Current memory consumption in MB

**Example:**
```python
result = health_check()
# Returns comprehensive health report
```

**Use Cases:**
- Production monitoring and alerting
- Pre-deployment health verification
- Performance regression detection
- Resource utilization tracking

---

## Error Handling

All tools follow a consistent error handling pattern:

### Standard Error Response
```json
{
  "status": "error",
  "error_type": "ValueError",
  "message": "Detailed error description"
}
```

### Common Error Types
- `ValueError`: Invalid input parameters
- `TimeoutError`: Execution time exceeded
- `ImportError`: Missing dependencies
- `RuntimeError`: Internal execution errors
- `SecurityError`: Sandbox security violations (Section 5.1 compliance)

---

## Rate Limits and Timeouts

**Default Timeouts:**
- `symbolic_check`: 30 seconds
- `find_path_to_exception`: 30 seconds
- `compare_functions`: 60 seconds (longer due to complexity)
- `analyze_branches`: 30 seconds
- `health_check`: 5 seconds (fast diagnostic)

**Resource Limits:**
- Maximum memory: 2048 MB per operation (configurable via `SYMBOLIC_MEMORY_LIMIT_MB`)
- Maximum code size: 64 KB (configurable via `SYMBOLIC_CODE_SIZE_LIMIT`)
- Maximum execution time: Configurable per tool (default 30-60 seconds)
- Per-path timeout: 10% of total timeout for path exploration

---

## Security Considerations

All code execution happens in a restricted sandbox (Section 5.1 compliance):

- **Restricted Imports**: Only whitelisted modules allowed
- **No File I/O**: Filesystem access blocked
- **No Network**: Network operations disabled
- **Memory Limits**: Hard memory caps enforced
- **Time Limits**: Execution timeouts prevent infinite loops

See [SECURITY.md](../SECURITY.md) for detailed security architecture.

---

## Version Compatibility

**Current Version:** 0.1.0
**FastMCP Compatibility:** >= 2.0.0
**Python Requirement:** >= 3.11
**CrossHair Requirement:** >= 0.0.70
**Z3 Requirement:** >= 4.12.0

---

## Further Reading

- [Complete Specification](../spec/Symbolic%20Execution%20MCP%20Specification.md)
- [Usage Examples](examples.md)
- [Security Documentation](../SECURITY.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
