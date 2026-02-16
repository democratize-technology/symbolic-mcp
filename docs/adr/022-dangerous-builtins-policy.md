# ADR-022: Dangerous Builtins Restriction Policy

**Status**: Accepted
**Date**: 2026-02-15
**Decision Maker**: Security Team
**Reviewers**: Architecture Team, Operations
**Related ADRs**: 003 (Security Model), 008 (Validation Architecture)

---

## Executive Summary

Established a blocklist of 9 dangerous built-in functions (`eval`, `exec`, `compile`, `__import__`, `open`, `globals`, `locals`, `vars`, `dir`) that complement ADR-003's import whitelist. AST-based validation detects bypass attempts through attribute access, subscripts, and container patterns.

---

## 1. Context and Problem Statement

### 1.1 Background

ADR-003 established a whitelist-based import security model, but Python's built-in functions provide another attack vector. Even with restricted imports, dangerous built-ins can:

1. **Execute arbitrary code**: `eval()`, `exec()`, `compile()`
2. **Access filesystem**: `open()`
3. **Introspect runtime**: `globals()`, `locals()`, `vars()`, `dir()`
4. **Import modules**: `__import__()`

### 1.2 Problem Statement

Built-in function blocking requires:

- **Complete coverage**: All dangerous functions identified
- **Bypass detection**: Detect indirect access patterns
- **Balance**: Block dangerous, allow legitimate

### 1.3 Requirements

- **REQ-2201**: Block code execution built-ins (eval, exec, compile)
- **REQ-2202**: Block filesystem access (open)
- **REQ-2203**: Block introspection that reveals security config
- **REQ-2204**: Detect bypass attempts (getattr, attribute access, subscripts)
- **REQ-2205**: Allow legitimate built-ins (print, len, etc.)

### 1.4 Constraints

- Cannot break CrossHair's internal operations
- Must detect patterns, not just direct calls
- Must provide clear error messages

---

## 2. Decision

**Block 9 dangerous built-in functions with AST-based bypass detection.**

### 2.1 Technical Specification

```python
# Built-in functions that are dangerous and should be blocked
DANGEROUS_BUILTINS = frozenset(
    {
        "eval",       # Arbitrary code execution
        "exec",       # Arbitrary code execution
        "compile",    # Code compilation for later execution
        "__import__", # Dynamic module loading
        "open",       # File system access
        "globals",    # Access to global namespace
        "locals",     # Access to local namespace
        "vars",       # Access to object __dict__
        "dir",        # Object introspection
    }
)
```

### 2.2 Blocked Functions Rationale

| Function | Category | Risk | Block Reason |
|----------|----------|------|--------------|
| `eval` | Code Execution | Critical | Execute arbitrary strings as code |
| `exec` | Code Execution | Critical | Execute arbitrary strings as code |
| `compile` | Code Execution | Critical | Compile strings to code objects |
| `__import__` | Import | Critical | Bypass import restrictions |
| `open` | Filesystem | High | Read/write arbitrary files |
| `globals` | Introspection | Medium | Access global namespace dict |
| `locals` | Introspection | Medium | Access local namespace dict |
| `vars` | Introspection | Medium | Access object's __dict__ |
| `dir` | Introspection | Low | Enumerate object attributes |

### 2.3 Bypass Detection Patterns

```python
# All of these are detected and blocked

# Pattern 1: Direct call
eval("...")

# Pattern 2: Space before parenthesis
eval ("...")

# Pattern 3: getattr bypass
getattr(__builtins__, "eval")("...")

# Pattern 4: Attribute access
__builtins__.eval("...")

# Pattern 5: Subscript access
__builtins__["eval"]("...")

# Pattern 6: List indexing bypass
[eval][0]("...")

# Pattern 7: Dict lookup bypass
{"f": eval}["f"]("...")

# Pattern 8: Tuple unpacking bypass
(eval,)[0]("...")

# Pattern 9: Nested access
(__builtins__ or {})["eval"]("...")
```

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **Block 9 + AST Detection** (selected) | Comprehensive blocklist with bypass detection | Secure, comprehensive | More complex | 9/10 |
| Block 5 Only | Only code execution built-ins | Simpler | Less secure | 5/10 |
| Block All Built-ins | Block all except allowlist | Maximum security | Breaks legitimate code | 4/10 |
| No Blocking | Rely on import restrictions only | Simple | Security gap | 2/10 |

### 3.2 Decision Criteria

| Criterion | Weight | Block 9 + AST | Block 5 Only | Block All | No Blocking |
|-----------|--------|---------------|--------------|-----------|-------------|
| Security | 40% | 10 | 6 | 9 | 1 |
| Functionality | 30% | 8 | 9 | 3 | 10 |
| Simplicity | 15% | 6 | 8 | 5 | 9 |
| Maintainability | 15% | 7 | 8 | 4 | 9 |
| **Weighted Score** | **100%** | **8.3** | **7.4** | **5.4** | **5.95** |

### 3.3 Selection Justification

Block 9 + AST Detection achieves the highest score (8.3) due to:

1. **Security**: Blocks all dangerous built-ins
2. **Functionality**: Legitimate built-ins still work
3. **Bypass Detection**: AST catches indirect access
4. **Clear Scope**: 9 functions is manageable

---

## 4. Alternatives Considered

### 4.1 Alternative 1: Block Only Code Execution Built-ins

**Description**: Block only `eval`, `exec`, `compile`, `__import__`, `open`.

**Advantages**:
- Simpler implementation
- Blocks most critical functions

**Disadvantages**:
- **Security gap**: Introspection can reveal security config
- **Bypass potential**: `globals()['__builtins__']['eval']`
- **Incomplete**: Doesn't address all attack vectors

**Rejection Rationale**: Insufficient for security-critical application.

### 4.2 Alternative 2: Allowlist Built-ins

**Description**: Block all built-ins except an explicit allowlist.

**Advantages**:
- Maximum security
- Explicit control

**Disadvantages**:
- **Breaks functionality**: Many legitimate uses blocked
- **Maintenance burden**: Must add to allowlist constantly
- **User friction**: Unexpected blocks

**Rejection Rationale**: Overly restrictive; breaks legitimate code.

### 4.3 Alternative 3: No Built-in Blocking

**Description**: Rely entirely on import restrictions.

**Advantages**:
- Simpler security model
- Less code

**Disadvantages**:
- **Major security gap**: `eval()` works without imports
- **Insufficient protection**: Built-ins bypass import restrictions

**Rejection Rationale**: Unacceptable security gap.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| New bypass pattern | Medium | High | Continuous AST improvement | Security |
| False positive | Low | Medium | Clear error messages | Dev Team |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| User confusion | Low | Low | Documentation on blocked functions | Docs |

### 5.3 Security Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Novel bypass | Low | Critical | AST detection patterns, security review | Security |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Code Execution Prevention**: eval/exec blocked
- **Filesystem Protection**: open blocked
- **Introspection Control**: globals/locals blocked
- **Bypass Detection**: AST catches indirect access
- **Clear Error Messages**: Users understand what's blocked

### 6.2 Negative Consequences

- **Some Introspection Blocked**: dir blocked (may affect some legitimate uses)
- **False Positives**: May block some safe patterns

### 6.3 Trade-offs Accepted

- **Security > Convenience**: Blocking dir even though low risk
- **Detection > Prevention**: AST detection over sandboxing

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] Phase 1: DANGEROUS_BUILTINS frozenset defined
- [x] Phase 2: _DangerousCallVisitor detects direct calls
- [x] Phase 3: Bypass detection (getattr, attribute, subscript)
- [x] Phase 4: Container pattern detection (list, dict, tuple)

### 7.2 Validation Requirements

- [x] All 9 functions blocked
- [x] Bypass patterns detected
- [x] Clear error messages
- [x] Tests for all patterns

### 7.3 Rollout Plan

1. **Completed**: Initial blocklist
2. **Completed**: Bypass detection
3. **Ongoing**: Monitor for new bypass patterns

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **Python ast module**: AST parsing
- **_DangerousCallVisitor**: AST visitor class (ADR-008)

### 8.2 Documentation Dependencies

- ADR-003: Whitelist-Based Import Security Model
- ADR-008: AST-Based Security Validation Architecture

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | Security Team | Initial ADR documenting builtins policy |

---

## 10. References

1. Project `main.py`: Lines 254-266 (DANGEROUS_BUILTINS)
2. Project `main.py`: Lines 473-728 (_DangerousCallVisitor)
3. ADR-003: Whitelist-Based Import Security Model
4. ADR-008: AST-Based Security Validation Architecture

---

## Appendix A: Blocked Functions Detail

```python
DANGEROUS_BUILTINS = frozenset({
    # Code Execution (Critical Risk)
    "eval",       # Evaluate expression string
    "exec",       # Execute statement string
    "compile",    # Compile string to code object
    "__import__", # Dynamic module import

    # Filesystem Access (High Risk)
    "open",       # Open file (read/write)

    # Introspection (Medium Risk)
    "globals",    # Return global namespace dict
    "locals",     # Return local namespace dict
    "vars",       # Return object's __dict__
    "dir",        # Return object's attribute names
})
```

---

## Appendix B: Allowed Built-ins

These built-ins are **allowed** (not exhaustive):

```python
# Safe built-ins that are allowed
len, print, range, enumerate, zip, map, filter, sorted, reversed
min, max, sum, any, all, abs, round, int, float, str, bool, list, dict, set, tuple
type, isinstance, issubclass, hasattr, callable, id, hash, repr
chr, ord, hex, oct, bin, pow, divmod
iter, next, slice, object, staticmethod, classmethod, property
# ... and many more
```

---

## Appendix C: AST Detection Implementation

```python
class _DangerousCallVisitor(ast.NodeVisitor):
    def _is_dangerous_name(self, name: str) -> bool:
        """Check if a name refers to a dangerous builtin."""
        return name in DANGEROUS_BUILTINS

    def visit_Call(self, node: ast.Call) -> None:
        # Direct call: eval(), exec()
        if isinstance(node.func, ast.Name):
            if self._is_dangerous_name(node.func.id):
                self.dangerous_calls.append(node.func.id)

        # Attribute access: __builtins__.eval
        elif isinstance(node.func, ast.Attribute):
            # ... detect __builtins__ access

        # Subscript call: [eval][0]()
        elif isinstance(node.func, ast.Subscript):
            # ... detect container bypass
```

---

## Appendix D: Test Cases

```python
# tests/test_security.py

def test_eval_blocked():
    code = "eval('1+1')"
    result = validate_code(code)
    assert not result["valid"]
    assert "eval" in result["error"]

def test_getattr_bypass_blocked():
    code = "getattr(__builtins__, 'eval')('1+1')"
    result = validate_code(code)
    assert not result["valid"]

def test_subscript_bypass_blocked():
    code = "__builtins__['eval']('1+1')"
    result = validate_code(code)
    assert not result["valid"]

def test_list_bypass_blocked():
    code = "[eval][0]('1+1')"
    result = validate_code(code)
    assert not result["valid"]

def test_dict_bypass_blocked():
    code = '{"f": eval}["f"]("1+1")'
    result = validate_code(code)
    assert not result["valid"]
```

---

## Appendix E: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-2201: Code Execution Blocked | Compliant | eval, exec, compile blocked |
| REQ-2202: Filesystem Blocked | Compliant | open blocked |
| REQ-2203: Introspection Blocked | Compliant | globals, locals, vars, dir blocked |
| REQ-2204: Bypass Detection | Compliant | AST detects 9+ patterns |
| REQ-2205: Legitimate Allowed | Compliant | Most built-ins allowed |
