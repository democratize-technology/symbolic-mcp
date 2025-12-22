# Usage Examples

Comprehensive examples demonstrating the Symbolic MCP server capabilities.

## Table of Contents

1. [Basic Contract Verification](#basic-contract-verification)
2. [Finding Exception Paths](#finding-exception-paths)
3. [Function Equivalence](#function-equivalence)
4. [Branch Analysis](#branch-analysis)
5. [Real-World Use Cases](#real-world-use-cases)

---

## Basic Contract Verification

### Example 1: Safe Division

Verify that division handles the zero-denominator case correctly:

```python
from mcp import symbolic_check

code = """
def safe_divide(x: int, y: int) -> float:
    '''
    Divide two numbers safely.

    pre: y != 0
    post: __return__ == x / y
    '''
    if y == 0:
        raise ValueError("Division by zero")
    return x / y
"""

result = symbolic_check(code, "safe_divide", timeout_seconds=30)

# Expected result:
# {
#   "status": "success",
#   "message": "No contract violations found",
#   "execution_time": 1.234
# }
```

### Example 2: Detecting Contract Violations

```python
code = """
def buggy_abs(x: int) -> int:
    '''
    Return absolute value.

    post: __return__ >= 0
    '''
    return x  # Bug: doesn't actually compute abs!
"""

result = symbolic_check(code, "buggy_abs", timeout_seconds=30)

# Expected result:
# {
#   "status": "violation_found",
#   "violations": [
#     {
#       "condition": "__return__ >= 0",
#       "counterexample": {"x": -5},
#       "actual_return": -5
#     }
#   ],
#   "execution_time": 0.523
# }
```

---

## Finding Exception Paths

### Example 3: Invalid Input Discovery

Find inputs that cause parsing errors:

```python
from mcp import find_path_to_exception

code = """
def parse_positive_int(s: str) -> int:
    '''Parse a string as a positive integer.'''
    value = int(s)
    if value <= 0:
        raise ValueError("Must be positive")
    return value
"""

# Find ValueError path
result = find_path_to_exception(
    code,
    "parse_positive_int",
    "ValueError",
    timeout_seconds=30
)

# Expected result:
# {
#   "status": "found",
#   "counterexample": {"s": "0"},
#   "exception_message": "Must be positive",
#   "execution_time": 0.842
# }
```

### Example 4: Multiple Exception Types

```python
code = """
def divide_and_sqrt(x: float, y: float) -> float:
    '''Divide x by y and take square root.'''
    result = x / y
    if result < 0:
        raise ValueError("Cannot sqrt negative")
    return result ** 0.5
"""

# Find ZeroDivisionError
zero_div_result = find_path_to_exception(
    code,
    "divide_and_sqrt",
    "ZeroDivisionError",
    timeout_seconds=30
)
# Returns: {"counterexample": {"x": 1.0, "y": 0.0}}

# Find ValueError
value_error_result = find_path_to_exception(
    code,
    "divide_and_sqrt",
    "ValueError",
    timeout_seconds=30
)
# Returns: {"counterexample": {"x": -1.0, "y": 1.0}}
```

---

## Function Equivalence

### Example 5: Refactoring Validation

Verify that refactored code maintains semantics:

```python
from mcp import compare_functions

code = """
def original_sum(numbers: list) -> int:
    '''Sum a list of integers.'''
    total = 0
    for n in numbers:
        total += n
    return total

def refactored_sum(numbers: list) -> int:
    '''Sum using built-in sum().'''
    return sum(numbers)
"""

result = compare_functions(
    code,
    "original_sum",
    "refactored_sum",
    timeout_seconds=60
)

# Expected result:
# {
#   "status": "equivalent",
#   "message": "Functions are semantically equivalent",
#   "execution_time": 2.145
# }
```

### Example 6: Finding Differences

```python
code = """
def ceil_divide_v1(x: int, y: int) -> int:
    '''Ceiling division.'''
    return (x + y - 1) // y

def ceil_divide_v2(x: int, y: int) -> int:
    '''Ceiling division - buggy version.'''
    return x // y + 1
"""

result = compare_functions(
    code,
    "ceil_divide_v1",
    "ceil_divide_v2",
    timeout_seconds=60
)

# Expected result:
# {
#   "status": "not_equivalent",
#   "counterexample": {"x": 10, "y": 5},
#   "outputs": {
#     "ceil_divide_v1": 2,
#     "ceil_divide_v2": 3
#   },
#   "message": "Functions produce different outputs",
#   "execution_time": 1.823
# }
```

---

## Branch Analysis

### Example 7: Dead Code Detection

Find unreachable code branches:

```python
from mcp import analyze_branches

code = """
def classify_number(x: int) -> str:
    '''Classify integer as positive, negative, or zero.'''
    if x > 0:
        return "positive"
    elif x < 0:
        return "negative"
    elif x == 0:  # Always reachable
        return "zero"
    else:  # Dead code - x must be positive, negative, or zero
        return "impossible"
"""

result = analyze_branches(code, "classify_number", timeout_seconds=30)

# Expected result:
# {
#   "status": "success",
#   "branches": [
#     {"condition": "x > 0", "line": 3},
#     {"condition": "x < 0", "line": 5},
#     {"condition": "x == 0", "line": 7}
#   ],
#   "reachability": {
#     "x > 0": "reachable",
#     "x < 0": "reachable",
#     "x == 0": "reachable",
#     "else": "unreachable"
#   },
#   "dead_code": [{"line": 9, "reason": "Condition always false"}],
#   "execution_time": 0.634
# }
```

### Example 8: Complex Conditions

```python
code = """
def process_data(value: int, flag: bool) -> str:
    '''Process data with multiple conditions.'''
    if value > 100 and flag:
        return "high_priority"
    elif value > 50 and not flag:
        return "medium"
    elif value > 0:
        return "low"
    else:
        return "invalid"
"""

result = analyze_branches(code, "process_data", timeout_seconds=30)

# Returns branch coverage analysis showing all condition combinations
```

---

## Real-World Use Cases

### Example 9: API Input Validation

Verify API endpoint handles all input cases:

```python
code = """
def create_user(username: str, age: int, email: str) -> dict:
    '''
    Create user account.

    pre: len(username) >= 3
    pre: 13 <= age <= 120
    pre: '@' in email
    post: __return__['success'] == True
    '''
    if len(username) < 3:
        raise ValueError("Username too short")
    if not (13 <= age <= 120):
        raise ValueError("Invalid age")
    if '@' not in email:
        raise ValueError("Invalid email")

    return {
        'success': True,
        'user': {
            'username': username,
            'age': age,
            'email': email
        }
    }
"""

# Verify all validation works
contract_result = symbolic_check(code, "create_user", 30)

# Find edge cases that fail validation
invalid_username = find_path_to_exception(code, "create_user", "ValueError", 30)
# Returns: {"username": "ab", "age": 25, "email": "test@example.com"}
```

### Example 10: Encryption Function Equivalence

Verify encryption implementation matches specification:

```python
code = """
def encrypt_spec(data: bytes, key: int) -> bytes:
    '''Reference encryption implementation.'''
    return bytes((b ^ key) & 0xFF for b in data)

def encrypt_impl(data: bytes, key: int) -> bytes:
    '''Optimized encryption implementation.'''
    key_byte = key & 0xFF
    return bytes(b ^ key_byte for b in data)
"""

result = compare_functions(code, "encrypt_spec", "encrypt_impl", 60)
# Verify optimization preserves correctness
```

### Example 11: Safety-Critical Code Verification

Verify control systems meet safety requirements:

```python
code = """
def emergency_brake(speed: float, obstacle_distance: float) -> bool:
    '''
    Determine if emergency braking is needed.

    pre: speed >= 0
    pre: obstacle_distance >= 0
    post: (__return__ == True) implies (obstacle_distance < speed * 2)
    '''
    # Emergency brake if collision imminent
    stopping_distance = speed * 2  # Simplified physics
    return obstacle_distance < stopping_distance
"""

result = symbolic_check(code, "emergency_brake", 30)
# Verify safety contract is never violated
```

---

## Health Monitoring

### Example 12: Production Health Check

```python
from mcp import health_check

# Periodic health monitoring
result = health_check()

print(f"Status: {result['status']}")
print(f"Uptime: {result['uptime_seconds']}s")
print(f"Memory: {result['resource_usage']['memory_mb']}MB")
print(f"CrossHair: {result['crosshair_status']['available']}")

# Example output:
# Status: healthy
# Uptime: 86400s
# Memory: 234.5MB
# CrossHair: True
```

---

## Error Handling Examples

### Example 13: Handling Timeouts

```python
code = """
def infinite_loop(x: int) -> int:
    '''This will timeout.'''
    while True:
        x += 1
    return x
"""

try:
    result = symbolic_check(code, "infinite_loop", timeout_seconds=5)
except TimeoutError as e:
    print(f"Analysis timed out: {e}")
    # Expected: Timeout after 5 seconds
```

### Example 14: Invalid Code Handling

```python
code = """
def broken_syntax(x: int) -> int
    return x + 1  # Missing colon
"""

result = symbolic_check(code, "broken_syntax", 30)
# Returns:
# {
#   "status": "error",
#   "error_type": "SyntaxError",
#   "error_message": "invalid syntax",
#   "execution_time": 0.012
# }
```

---

## Best Practices

### Timeout Selection

- **Simple functions:** 10-30 seconds
- **Complex logic:** 30-60 seconds
- **Function comparison:** 60-120 seconds (more computation needed)

### Contract Writing

Use clear, verifiable conditions:

```python
# Good: Specific and verifiable
'''
pre: 0 <= index < len(array)
post: __return__ == array[index]
'''

# Bad: Vague and hard to verify
'''
pre: index is valid
post: returns the right value
'''
```

### Exception Testing

Test all exception paths explicitly:

```python
# Test each exception type separately
exceptions = ["ValueError", "TypeError", "IndexError"]
for exc_type in exceptions:
    result = find_path_to_exception(code, func_name, exc_type, 30)
    if result["status"] == "found":
        print(f"{exc_type}: {result['counterexample']}")
```

---

## Further Reading

- [API Reference](api.md) - Complete tool documentation
- [Specification](../spec/Symbolic%20Execution%20MCP%20Specification.md) - Technical details
- [Security](../SECURITY.md) - Security architecture and threat model
- [Contributing](../CONTRIBUTING.md) - Development guidelines
