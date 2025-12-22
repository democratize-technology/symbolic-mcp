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
- `status` (str): "success", "violation_found", or "error"
- `violations` (list): Contract violations if found
- `message` (str): Human-readable result description
- `execution_time` (float): Time taken for analysis

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
- `status` (str): "found", "not_found", or "error"
- `counterexample` (dict): Input values causing the exception (if found)
- `exception_message` (str): The exception message that would be raised
- `execution_time` (float): Time taken for analysis

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
- `status` (str): "equivalent", "not_equivalent", or "error"
- `counterexample` (dict): Input where functions differ (if not equivalent)
- `outputs` (dict): Different outputs for the counterexample
- `message` (str): Human-readable comparison result
- `execution_time` (float): Time taken for analysis

**Example:**
```python
result = compare_functions("""
def add_v1(x: int, y: int) -> int:
    return x + y

def add_v2(x: int, y: int) -> int:
    return y + x
""", "add_v1", "add_v2", 60)
# Returns: {"status": "equivalent", "message": "Functions are semantically equivalent"}
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
    timeout_seconds: int = 30
) -> Dict[str, Any]
```

**Parameters:**
- `code` (str): Python source code containing the function
- `function_name` (str): Name of the function to analyze
- `timeout_seconds` (int, optional): Maximum execution time in seconds (default: 30)

**Returns:**
Dictionary containing:
- `status` (str): "success" or "error"
- `branches` (list): List of branch conditions found
- `reachability` (dict): Reachability status for each branch
- `dead_code` (list): Unreachable code locations (if any)
- `execution_time` (float): Time taken for analysis

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
- `status` (str): Overall health status ("healthy", "degraded", "unhealthy")
- `timestamp` (float): Current Unix timestamp
- `uptime_seconds` (float): Server uptime in seconds
- `version` (str): FastMCP version
- `resource_usage` (dict): Memory and CPU utilization
- `crosshair_status` (dict): CrossHair integration health
- `security_status` (dict): Security validation results
- `performance_metrics` (dict): Response time statistics

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
  "error_message": "Detailed error description",
  "execution_time": 0.123
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

**Resource Limits (Section 5.2 Compliance):**
- Maximum memory: 512 MB per operation
- Maximum execution time: 60 seconds (configurable)
- Concurrent requests: 10 (configurable via `FASTMCP_MAX_CONCURRENT_REQUESTS`)

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
**Python Requirement:** >= 3.10
**CrossHair Requirement:** >= 0.0.72

---

## Further Reading

- [Complete Specification](../spec/Symbolic%20Execution%20MCP%20Specification.md)
- [Usage Examples](examples.md)
- [Security Documentation](../SECURITY.md)
- [Contributing Guidelines](../CONTRIBUTING.md)
