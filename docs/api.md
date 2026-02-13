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

---

## Resources

The Symbolic MCP server provides configuration and informational resources using FastMCP's `@mcp.resource()` decorator.

### config://security

Current security configuration settings including allowed modules, blocked modules, and memory limits.

**URI:** `config://security`

**Returns:**
- `allowed_modules` (list): Whitelisted modules for symbolic execution
- `blocked_modules` (list): Blocked modules for security
- `dangerous_builtins` (list): Blocked built-in functions
- `memory_limit_mb` (int): Memory limit in MB
- `code_size_bytes` (int): Maximum code size in bytes
- `coverage_threshold` (int): Coverage threshold for exhaustive analysis

### config://server

Current server configuration settings including version and timeouts.

**URI:** `config://server`

**Returns:**
- `version` (str): Symbolic MCP server version
- `default_timeout_seconds` (int): Default analysis timeout
- `mask_error_details` (bool): Whether error details are masked
- `transport` (str): Transport type ("oauth" or "stdio")

### info://capabilities

Server capabilities and available tools.

**URI:** `info://capabilities`

**Returns:**
- `tools` (list): Available tools with names and descriptions
- `resources` (list): Available resources with URIs and descriptions

---

## Resource Templates

FastMCP 2.0 supports **RFC 6570 URI Template** syntax for dynamic resources. This allows resources to accept parameters in their URIs, similar to how URL routing works in web frameworks.

### Static vs. Template Resources

**Static resources** (like those above) have fixed URIs:
```python
@mcp.resource("config://security")
def get_security_config() -> dict[str, object]:
    return {"allowed_modules": [...]}
```

**Template resources** use variable placeholders:
```python
@mcp.resource("file://code/{function_name}.py")
def get_function_code(function_name: str) -> str:
    return f"def {function_name}(): ..."
```

### RFC 6570 URI Template Syntax

#### Path Parameters

Use `{variable}` for single path segments and `{variable*}` for wildcard matching:

```python
# Single segment: matches "file://code/foo.py"
@mcp.resource("file://code/{filename}.py")
def get_code_file(filename: str) -> str:
    return f"# {filename}"

# Wildcard: matches "file://code/a/b/c.py"
@mcp.resource("file://code/{filepath*}.py")
def get_nested_file(filepath: str) -> str:
    return f"# {filepath}"
```

**Path parameter examples:**
- `{function_name}` - Single path segment (e.g., "symbolic_check")
- `{filepath*}` - Wildcard matching multiple segments (e.g., "utils/helpers")
- `{module}/{function}` - Multiple path segments

#### Query Parameters

Use `{?query}` or `{?query*}` for optional query parameters:

```python
# Single query parameter: "file://code/foo.py?format=raw"
@mcp.resource("file://code/{filename}.py{?format}")
def get_code_with_format(filename: str, format: str | None = None) -> str:
    if format == "raw":
        return get_raw_code(filename)
    return get_highlighted_code(filename)

# Multiple query parameters: "file://code/foo.py?format=raw&limit=100"
@mcp.resource("file://code/{filename}.py{?format*}")
def get_code_with_options(filename: str, format: str | None = None, limit: int | None = None) -> str:
    return fetch_code(filename, format=format, limit=limit)
```

**Query parameter examples:**
- `{?format}` - Optional single parameter
- `{?format,limit}` - Optional multiple parameters
- `{?options*}` - Wildcard for multiple parameters

#### Combining Path and Query Parameters

```python
@mcp.resource("analysis/{function_name}{?timeout,depth}")
def get_analysis_result(function_name: str, timeout: int | None = None, depth: int | None = None) -> dict:
    return perform_analysis(function_name, timeout, depth)
```

**URI examples:**
- `analysis/symbolic_check` - No query params
- `analysis/symbolic_check?timeout=60` - With timeout
- `analysis/symbolic_check?timeout=60&depth=5` - Both params

### Resource Template vs. Static Resource

| Aspect | Static Resource | Template Resource |
|--------|---------------|------------------|
| URI | Fixed string | Contains `{variable}` placeholders |
| Parameters | None | Extracted from URI path/query |
| Use case | Configuration, global info | File access, dynamic content |
| Example | `config://security` | `file://code/{filepath*}` |

### Best Practices

1. **Use specific names**: `{function_name}` is clearer than `{name}`
2. **Document wildcards**: Explain what `{filepath*}` can contain
3. **Validate inputs**: Template parameters should be validated in resource functions
4. **Provide defaults**: Query parameters should have sensible defaults
5. **Consider security**: Wildcard paths like `{filepath*}` need careful validation to prevent directory traversal

---

## Tool Visibility & Annotations

FastMCP 2.0 provides tools with visibility control, annotations, and notification capabilities.

### Tool Annotations

Tools can include **ToolAnnotations** to provide LLM hints about behavior:

```python
from mcp.types import ToolAnnotations

@mcp.tool(
    annotations=ToolAnnotations(
        title="Descriptive Tool Title",  # Shown to LLMs
        readOnlyHint=True,     # Read-only operation
        idempotentHint=True,   # Same result on repeated calls
        destructiveHint=False,    # Doesn't modify data
        openWorldHint=False,    # No external interactions
    )
)
def my_tool() -> dict:
    return {"result": "value"}
```

**Annotation hints:**
- `title`: Human-readable title for LLMs
- `readOnlyHint=True`: Tool doesn't modify state (like GET requests)
- `idempotentHint=True`: Same inputs always produce same results
- `destructiveHint=True`: Tool modifies or deletes data
- `openWorldHint=True`: Tool interacts with external systems

### Tool Visibility Control

Tools can be dynamically enabled or disabled:

```python
# Disable a tool programmatically
mcp.disable(key="my_tool")

# Re-enable the tool
mcp.enable(key="my_tool")

# Disable all tools with specific tags
mcp.disable(tags=["experimental"])

# Enable only specific tools
mcp.enable(keys=["safe_tool_1", "safe_tool_2"])
```

**Use cases:**
- **Feature flags**: Gradually roll out new functionality
- **A/B testing**: Compare different tool implementations
- **Maintenance**: Temporarily disable problematic tools
- **Client permissions**: Show different tools based on authentication

### Notifications

FastMCP automatically broadcasts `notifications/tools/list_changed` when tools are enabled/disabled. Clients can handle this notification to update their available tools list dynamically.

**When notifications are sent:**
- Within a request context (immediate dispatch)
- During initialization (startup event)
- When `mcp.disable()` or `mcp.enable()` is called

### Lifecycle Management

FastMCP servers support lifespan events for startup/shutdown:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan():
    # Startup: Initialize resources
    print("Server starting...")
    yield
    # Shutdown: Clean up resources
    print("Server shutting down...")

mcp = FastMCP("My Server", lifespan=lifespan)
```

**Lifespan events:**
- `startup`: Run before server starts accepting requests
- `shutdown`: Run after server stops handling requests
- Async context managers supported for resource cleanup

---

## Context Object

FastMCP 2.0 provides a **Context** object for tools that need access to MCP capabilities like logging, progress reporting, and resource access.

### Using Context in Tools

Add a `ctx: Context` parameter to access MCP capabilities:

```python
from fastmcp import Context

@mcp.tool
def analyze_with_progress(code: str, ctx: Context) -> dict:
    """Analyze code with progress reporting."""
    # Log at different levels
    ctx.info("Starting analysis")
    ctx.warning("This may take a while")
    ctx.error("Critical: Analysis failed")

    # Report progress (0-100 scale)
    for i in range(100):
        ctx.report_progress(i + 1, 100, f"Processing step {i}")

    # Read resources from the same server
    security_config = ctx.read_resource("config://security")

    # Get request metadata
    request_id = ctx.request_id
    client_id = ctx.client_id

    return {"status": "complete", "request_id": request_id}
```

### Context Capabilities

| Method | Description | Use Case |
|--------|-------------|----------|
| `ctx.info(msg)` | Log info message | General logging |
| `ctx.warning(msg)` | Log warning message | Non-critical issues |
| `ctx.error(msg)` | Log error message | Error conditions |
| `ctx.report_progress(progress, total, message?)` | Report progress | Long-running operations |
| `ctx.read_resource(uri)` | Read server resource | Access config/data |
| `ctx.request_id` | Current request ID | Tracking, debugging |
| `ctx.client_id` | Client identifier | Per-client behavior |

### Best Practices

1. **Optional parameter**: Only add `ctx: Context` if your tool needs it
2. **Type annotation**: Use `Context` from `fastmcp` for proper hints
3. **Progress granularity**: Report progress at appropriate intervals (not every iteration)
4. **Resource access**: Use `ctx.read_resource()` for accessing server's own resources
5. **Logging preference**: Use Context logging over `print()` for better client integration

---

## Output Schema Control

FastMCP 2.0 provides two ways to structure tool outputs: **ToolResult** for rich responses, and **output_schema** for validation.

### ToolResult with Structured Content

Use `ToolResult` to provide both human-readable content and structured data:

```python
from mcp.types import ToolResult

@mcp.tool
def get_weather(city: str) -> ToolResult:
    """Get weather for a city with structured output."""
    return ToolResult(
        content=f"Weather for {city} is 72°F and sunny",
        structured_content={
            "city": city,
            "temperature_f": 72,
            "conditions": "sunny",
            "forecast": ["sunny", "clear"]
        },
        meta={
            "execution_time_ms": 150,
            "data_source": "weather_api"
        }
    )
```

### output_schema Parameter

For automatic structured output, use `output_schema` to define validation:

```python
from pydantic import BaseModel

@mcp.tool(output_schema=WeatherResult)
def get_weather_schema(city: str) -> WeatherResult:
    """Get weather with Pydantic schema validation."""
    return WeatherResult(
        city=city,
        temperature_f=72,
        conditions="sunny"
    )

class WeatherResult(BaseModel):
    city: str
    temperature_f: int
    conditions: str
```

### ToolResult vs output_schema

| Aspect | ToolResult | output_schema |
|--------|-----------|---------------|
| Control | Full control over content/structure | Automatic from type hints |
| Flexibility | Can vary structure per call | Consistent structure |
| Validation | Manual | Automatic Pydantic validation |
| Metadata | Built-in `meta` field | Add as separate field |
| Use case | Complex/variable responses | Consistent data structures |

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
