<!-- SPDX-License-Identifier: MIT -->
<!-- Copyright (c) 2025 Symbolic MCP Contributors -->
# Symbolic Execution MCP Server Specification

**Version:** 1.0
**Target Framework:** FastMCP 2.0 (Python)
**Core Library:** CrossHair (`crosshair-tool`)
**Classification:** Empirical Verification / Path-Sensitive Analysis

---

## 1. Executive Summary

This server provides **symbolic execution** capabilities for Python code. Unlike fuzzing (which generates random concrete inputs), symbolic execution treats inputs as symbolic variables and explores all possible execution paths algebraically.

**The Goal:** When fuzzing times out or misses edge cases hidden behind complex conditionals, symbolic execution finds them by solving path constraints. It answers: "Is there ANY input that makes this assertion fail?" rather than "Did my random inputs find a failure?"

**Relationship to Other MCPs:**

| MCP | Technique | Strength |
|-----|-----------|----------|
| Formal Logic | Static theorem proving | Mathematical proofs, consistency checking |
| Fuzzing | Random input generation | Fast coverage, real execution |
| **Symbolic Execution** | Path constraint solving | Exhaustive path exploration, hard-to-reach bugs |

---

## 2. Technical Stack Requirements

- **Language:** Python 3.11+
- **Transport:** Stdio (default), SSE (optional)
- **Key Dependencies:**
  - `fastmcp>=2.0.0` (Server SDK)
  - `crosshair-tool>=0.0.70` (Symbolic execution engine)
  - `z3-solver>=4.12.0` (Constraint solver backend)
  - `typing-extensions>=4.0.0` (Enhanced type hints)

---

## 3. Core Architecture

CrossHair performs symbolic execution by:
1. Intercepting Python operations on symbolic values
2. Building path constraints as execution proceeds
3. Using Z3 to solve for inputs that reach specific paths
4. Reporting counterexamples when contracts are violated

### 3.1 How Symbolic Execution Differs from Fuzzing

```python
def tricky(x: int, y: int) -> int:
    if x == 7 and y == x * 3 + 4:  # y must equal 25
        raise ValueError("Found it!")
    return x + y
```

- **Fuzzing**: Randomly generates `x` and `y`. Probability of hitting `x=7, y=25` is ~1/(2^64). Will likely timeout.
- **Symbolic Execution**: Treats `x` and `y` as symbols, solves `x == 7 ∧ y == x*3+4`, finds `(7, 25)` immediately.

### 3.2 Safety Constraints

- **Requirement:** Production deployment **must** use Docker container.
- **Requirement:** Use the same `RestrictedExecutor` pattern as the Fuzzing MCP for any direct code execution.
- **Note:** CrossHair itself provides some isolation since it doesn't fully execute code—it symbolically interprets it. However, module imports and class definitions still execute.

### 3.3 Restricted Import Handler

CrossHair needs to import the module containing the function under test. We control what that module can access:

```python
import sys
from types import ModuleType
from typing import Any

class RestrictedImporter:
    """
    Controls what modules can be imported during symbolic execution.
    Installs as a meta path finder.
    """

    BLOCKED_MODULES = frozenset({
        'os', 'sys', 'subprocess', 'shutil', 'pathlib',
        'socket', 'http', 'urllib', 'requests', 'ftplib',
        'pickle', 'shelve', 'marshal',
        'ctypes', 'multiprocessing',
        'importlib', 'runpy',
        'code', 'codeop', 'pty', 'tty',
    })

    ALLOWED_MODULES = frozenset({
        'math', 'random', 'string', 'collections', 'itertools',
        'functools', 'operator', 'typing', 're', 'json',
        'datetime', 'decimal', 'fractions', 'statistics',
        'dataclasses', 'enum', 'copy', 'heapq', 'bisect',
        'typing_extensions', 'abc',
    })

    @classmethod
    def install(cls):
        """Install the restricted importer as a meta path finder."""
        sys.meta_path.insert(0, cls())

    @classmethod
    def uninstall(cls):
        """Remove the restricted importer."""
        sys.meta_path = [f for f in sys.meta_path if not isinstance(f, cls)]

    def find_module(self, fullname: str, path=None):
        base_module = fullname.split('.')[0]
        if base_module in self.BLOCKED_MODULES:
            return self  # Return self to handle the import (and block it)
        return None  # Let normal import proceed

    def load_module(self, fullname: str):
        raise ImportError(f"Import of '{fullname}' is blocked in symbolic execution sandbox")
```

---

## 4. Tool Definitions

### Tool 1: `symbolic_check`

**Description:** Symbolically verify that a function satisfies its contract (preconditions → postconditions). This is the primary tool—it exhaustively checks all paths.

**Inputs:**
- `code` (string): Python code containing the function and its contract. Contracts use CrossHair's `icontract` style or inline assertions.
- `function_name` (string): Name of the function to check.
- `timeout_seconds` (int, optional): Max time for analysis. Default: 30.

**Contract Styles Supported:**

```python
# Style 1: icontract decorators
from icontract import require, ensure

@require(lambda x: x >= 0)
@ensure(lambda result: result >= 0)
def sqrt(x: float) -> float:
    return x ** 0.5

# Style 2: Inline assertions (CrossHair checks these too)
def sqrt(x: float) -> float:
    assert x >= 0, "precondition"
    result = x ** 0.5
    assert result >= 0, "postcondition"
    return result

# Style 3: Type-based contracts (CrossHair infers from types)
def sqrt(x: float) -> float:
    # CrossHair will try to find x where return type is violated
    return x ** 0.5  # Fails for negative x (returns complex)
```

**Behavior:**
1. Parse `code` and extract the function.
2. Install `RestrictedImporter`.
3. Run CrossHair's `analyze_function` with symbolic inputs.
4. Collect any counterexamples (inputs that violate contracts).
5. Uninstall `RestrictedImporter`.

**Output Schema:**

```json
{
  "status": "verified" | "counterexample" | "timeout" | "error",
  "counterexamples": [
    {
      "args": {"x": -1.0},
      "kwargs": {},
      "violation": "postcondition: result >= 0",
      "actual_result": "complex number (nan)",
      "path_condition": "x < 0"
    }
  ],
  "paths_explored": 847,
  "paths_verified": 846,
  "time_seconds": 2.3,
  "coverage_estimate": 0.95
}
```

- `status`:
  - `"verified"` - All explored paths satisfy the contract
  - `"counterexample"` - Found input(s) that violate the contract
  - `"timeout"` - Analysis exceeded time limit (partial results may be present)
  - `"error"` - Syntax error, unsupported construct, or sandbox violation
- `counterexamples`: List of all violations found (may be multiple)
- `paths_explored`: Total execution paths analyzed
- `paths_verified`: Paths that passed all checks
- `time_seconds`: Actual analysis time
- `coverage_estimate`: Estimated fraction of paths explored (1.0 = exhaustive)

---

### Tool 2: `find_path_to_exception`

**Description:** Find concrete inputs that cause a specific exception type to be raised. Useful for security analysis (can an attacker trigger this error?) and bug hunting.

**Inputs:**
- `code` (string): Python function definition.
- `function_name` (string): Function to analyze.
- `exception_type` (string): Exception class name to target (e.g., `"ValueError"`, `"ZeroDivisionError"`, `"IndexError"`).
- `timeout_seconds` (int, optional): Default: 30.

**Behavior:**
1. Symbolically execute the function.
2. At each path, check if `exception_type` is raised.
3. If found, solve constraints to get concrete inputs.
4. Continue searching for additional paths to the same exception.

**Output Schema:**

```json
{
  "status": "found" | "unreachable" | "timeout" | "error",
  "triggering_inputs": [
    {
      "args": {"lst": [], "idx": 0},
      "kwargs": {},
      "path_condition": "len(lst) == 0 and idx >= 0",
      "stack_trace": "IndexError at line 5: list index out of range"
    }
  ],
  "paths_to_exception": 3,
  "total_paths_explored": 156,
  "time_seconds": 1.8
}
```

- `status`:
  - `"found"` - At least one path triggers the exception
  - `"unreachable"` - No path can trigger this exception (proven)
  - `"timeout"` - Could not complete analysis
  - `"error"` - Invalid exception type or code error

---

### Tool 3: `compare_functions`

**Description:** Check if two functions are semantically equivalent (produce the same output for all inputs). Essential for refactoring validation.

**Inputs:**
- `code` (string): Python code containing both functions.
- `function_a` (string): Name of first function.
- `function_b` (string): Name of second function.
- `timeout_seconds` (int, optional): Default: 60 (equivalence checking is expensive).

**Behavior:**
1. Symbolically execute both functions with the same symbolic inputs.
2. Check if outputs are always equal.
3. If not, find a distinguishing input.

**Output Schema:**

```json
{
  "status": "equivalent" | "different" | "timeout" | "error",
  "distinguishing_input": {
    "args": {"x": 0},
    "function_a_result": 0,
    "function_b_result": 1,
    "explanation": "Functions differ when x == 0"
  },
  "paths_compared": 234,
  "time_seconds": 15.2,
  "confidence": "proven" | "high" | "partial"
}
```

- `status`:
  - `"equivalent"` - All explored paths produce identical results
  - `"different"` - Found input where outputs differ
  - `"timeout"` / `"error"` - Analysis incomplete
- `confidence`:
  - `"proven"` - Exhaustively checked all paths
  - `"high"` - Checked many paths, no differences found
  - `"partial"` - Timed out, only partial coverage

---

### Tool 4: `analyze_branches`

**Description:** Enumerate all branch conditions in a function and report which are reachable. Helps understand code complexity and identify dead code.

**Inputs:**
- `code` (string): Python function definition.
- `function_name` (string): Function to analyze.
- `timeout_seconds` (int, optional): Default: 30.

**Output Schema:**

```json
{
  "status": "complete" | "partial" | "error",
  "branches": [
    {
      "line": 5,
      "condition": "x > 0",
      "true_reachable": true,
      "false_reachable": true,
      "true_example": {"x": 1},
      "false_example": {"x": -1}
    },
    {
      "line": 8,
      "condition": "x > 0 and x < 0",
      "true_reachable": false,
      "false_reachable": true,
      "true_example": null,
      "false_example": {"x": 0},
      "note": "Dead code: condition is unsatisfiable"
    }
  ],
  "total_branches": 5,
  "reachable_branches": 4,
  "dead_code_lines": [9, 10],
  "cyclomatic_complexity": 6,
  "time_seconds": 3.1
}
```

---

## 5. Implementation Guidelines

### 5.1 CrossHair Integration

```python
import crosshair
from crosshair.core_and_libs import analyze_function, AnalysisOptions, MessageType
from crosshair.fnutil import resolve_signature
import ast
import textwrap
from typing import Any

class SymbolicAnalyzer:
    """Wraps CrossHair for MCP tool usage."""

    def __init__(self, timeout_seconds: int = 30):
        self.timeout = timeout_seconds

    def check_function(
        self,
        code: str,
        function_name: str
    ) -> dict[str, Any]:
        """
        Symbolically check a function against its contracts.

        Returns structured results compatible with MCP tool output.
        """
        # Parse and compile the code
        try:
            tree = ast.parse(textwrap.dedent(code))
        except SyntaxError as e:
            return {
                "status": "error",
                "error_type": "SyntaxError",
                "message": str(e),
                "line": e.lineno
            }

        # Create a module namespace and execute the code
        namespace: dict[str, Any] = {}
        try:
            RestrictedImporter.install()
            exec(compile(tree, "<mcp-input>", "exec"), namespace)
        except ImportError as e:
            return {
                "status": "error",
                "error_type": "SandboxViolation",
                "message": str(e)
            }
        except Exception as e:
            return {
                "status": "error",
                "error_type": type(e).__name__,
                "message": str(e)
            }
        finally:
            RestrictedImporter.uninstall()

        # Get the function
        if function_name not in namespace:
            return {
                "status": "error",
                "error_type": "NameError",
                "message": f"Function '{function_name}' not found in code"
            }

        func = namespace[function_name]

        # Configure CrossHair analysis
        options = AnalysisOptions(
            max_iterations=1000,
            per_condition_timeout=self.timeout,
            per_path_timeout=self.timeout / 10,
        )

        # Run analysis
        counterexamples = []
        paths_explored = 0
        paths_verified = 0

        try:
            for message in analyze_function(func, options):
                paths_explored += 1
                if message.state == MessageType.CONFIRMED:
                    paths_verified += 1
                elif message.state == MessageType.COUNTEREXAMPLE:
                    counterexamples.append({
                        "args": message.args,
                        "kwargs": message.kwargs or {},
                        "violation": message.message,
                        "path_condition": str(message.condition) if hasattr(message, 'condition') else None
                    })
        except TimeoutError:
            return {
                "status": "timeout",
                "counterexamples": counterexamples,
                "paths_explored": paths_explored,
                "paths_verified": paths_verified,
                "coverage_estimate": min(paths_explored / 1000, 0.99)
            }

        return {
            "status": "counterexample" if counterexamples else "verified",
            "counterexamples": counterexamples,
            "paths_explored": paths_explored,
            "paths_verified": paths_verified,
            "coverage_estimate": 1.0 if paths_explored < 1000 else 0.99
        }
```

### 5.2 Error Handling

- **Unsupported Constructs:** CrossHair doesn't support all Python features (e.g., generators with complex state, some metaclasses). Return:
  ```json
  {
    "status": "error",
    "error_type": "UnsupportedConstruct",
    "message": "Generator expressions are not fully supported",
    "suggestion": "Try rewriting as a list comprehension or explicit loop"
  }
  ```

- **Solver Timeout:** Z3 can hang on complex constraints. Use per-path timeouts:
  ```python
  options = AnalysisOptions(
      per_path_timeout=timeout_seconds / 10,  # Each path gets 1/10 of total
      per_condition_timeout=timeout_seconds,
  )
  ```

- **Memory Limits:** Symbolic state can explode. Set a cap:
  ```python
  import resource
  resource.setrlimit(resource.RLIMIT_AS, (2 * 1024 * 1024 * 1024, -1))  # 2GB
  ```

### 5.3 Test Requirements

Create `tests/` directory with **pytest**:

1. **`test_symbolic_finds_bug.py`** - Find a bug that fuzzing would miss:
   ```python
   def test_finds_needle_in_haystack():
       """Symbolic execution finds input that random testing would miss."""
       code = '''
   def tricky(x: int, y: int) -> int:
       if x == 12345 and y == x * 7 + 3:
           raise ValueError("Found the needle")
       return x + y
   '''
       result = symbolic_check(code=code, function_name="tricky")
       assert result["status"] == "counterexample"
       ce = result["counterexamples"][0]
       assert ce["args"]["x"] == 12345
       assert ce["args"]["y"] == 12345 * 7 + 3
   ```

2. **`test_equivalence_check.py`** - Verify two implementations are equivalent:
   ```python
   def test_detects_difference():
       code = '''
   def impl_a(x: int) -> int:
       return x * 2

   def impl_b(x: int) -> int:
       return x + x if x != 0 else 1  # Bug: wrong for x=0
   '''
       result = compare_functions(code=code, function_a="impl_a", function_b="impl_b")
       assert result["status"] == "different"
       assert result["distinguishing_input"]["args"]["x"] == 0
   ```

3. **`test_unreachable_exception.py`** - Prove an exception cannot occur:
   ```python
   def test_proves_safe():
       code = '''
   def safe_div(a: int, b: int) -> float:
       if b == 0:
           return 0.0
       return a / b
   '''
       result = find_path_to_exception(
           code=code,
           function_name="safe_div",
           exception_type="ZeroDivisionError"
       )
       assert result["status"] == "unreachable"
   ```

4. **`test_branch_analysis.py`** - Identify dead code:
   ```python
   def test_finds_dead_code():
       code = '''
   def dead_branch(x: int) -> int:
       if x > 0 and x < 0:  # Impossible
           return 999
       return x
   '''
       result = analyze_branches(code=code, function_name="dead_branch")
       assert 999 in str(result["dead_code_lines"]) or len(result["dead_code_lines"]) > 0
   ```

---

## 6. Dockerfile Specification

```dockerfile
FROM python:3.11-slim

# Z3 solver requires build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Security: run as non-root user
RUN useradd --create-home --shell /bin/bash mcp

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY --chown=mcp:mcp . .

USER mcp

ENV PYTHONUNBUFFERED=1
ENV MCP_TRANSPORT=stdio

# Memory limit for Z3 solver
ENV Z3_MEMORY_LIMIT=2048

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import crosshair; print('ok')" || exit 1

ENTRYPOINT ["python", "main.py"]
```

**requirements.txt:**
```
fastmcp>=2.0.0
crosshair-tool>=0.0.70
z3-solver>=4.12.0
icontract>=2.6.0
typing-extensions>=4.0.0
```

---

## 7. Development Prompt for Claude Code

Copy and paste this instruction:

> I need you to build the **'Symbolic Execution MCP'** based on this specification.
>
> **Constraints:**
>
> 1. **No Placeholders:** Write the complete `main.py` with FastMCP instantiation and all four tools.
> 2. **RestrictedImporter:** Implement exactly as specified in section 3.3.
> 3. **SymbolicAnalyzer:** Implement the CrossHair wrapper as specified in section 5.1, adapting as needed for the actual CrossHair API.
> 4. **Output Schemas:** All tools must return JSON matching the exact schemas in section 4.
> 5. **Testing:** Create `tests/` directory with pytest tests covering all four required test cases in section 5.3.
> 6. **Output Files:** Provide `main.py`, `requirements.txt`, `Dockerfile`, and all test files.
>
> **Important Notes:**
> - CrossHair's API may have evolved. Use `crosshair --help` and the CrossHair documentation to adapt the integration code.
> - The `analyze_function` API shown is illustrative. You may need to use CrossHair's CLI wrapper or find the current internal API.
> - If CrossHair doesn't expose a clean Python API, wrap the CLI: `subprocess.run(["crosshair", "check", module_path])` and parse output.

---

## 8. Verification Tests

### Test 1: Needle in Haystack

**Input:**
```python
def tricky(x: int, y: int) -> int:
    if x == 7 and y == 25:
        raise ValueError("Boom")
    return x + y
```

**Expected:** Finds `x=7, y=25` within seconds.

### Test 2: Refactoring Safety

**Input:**
```python
# Original
def original(items: list[int]) -> int:
    total = 0
    for item in items:
        total += item
    return total

# Refactored
def refactored(items: list[int]) -> int:
    return sum(items)
```

**Expected:** `status: "equivalent"` with `confidence: "proven"`.

### Test 3: Prove Exception Unreachable

**Input:**
```python
def validated_sqrt(x: float) -> float:
    if x < 0:
        return 0.0  # Safe fallback
    return x ** 0.5
```

**Target:** `ValueError` or `ZeroDivisionError`

**Expected:** `status: "unreachable"` - these exceptions cannot occur.

---

## 9. Integration with Fuzzing MCP

The Symbolic Execution MCP complements the Fuzzing MCP. Recommended workflow:

1. **Start with Fuzzing** - Fast, finds common bugs quickly.
2. **If fuzzing passes** - Run symbolic execution to check harder paths.
3. **If fuzzing times out without finding bugs** - Use symbolic execution to either find the bug or prove safety.

Example orchestration (future Orchestrator MCP):
```
IF fuzz_function.status == "passed" AND confidence_needed == "high":
    symbolic_check(same_function)
ELIF fuzz_function.status == "timeout":
    symbolic_check(same_function)  # Pick up where fuzzing left off
```

---

## Changelog

- **v1.0** - Initial specification.
