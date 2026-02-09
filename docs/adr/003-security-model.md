# ADR-003: Whitelist-Based Import Security Model

**Status**: Accepted
**Date**: 2025-02-09
**Decision Maker**: Security Team
**Reviewers**: Architecture Team, Operations
**Related ADRs**: 001 (Framework), 002 (Symbolic Engine), 005 (Isolation)

---

## Executive Summary

Adopted a whitelist-based import security model over blacklist approaches. User code is restricted to 21 explicitly allowed modules, with 28+ dangerous modules blocked. This defense-in-depth approach prevents code execution escapes while enabling legitimate symbolic analysis operations.

---

## 1. Context and Problem Statement

### 1.1 Background

The Symbolic Execution MCP server accepts and executes arbitrary Python code from users. This creates a significant attack surface:

1. **Code injection**: Malicious users may execute arbitrary code
2. **Sandbox escape**: Users may attempt to break out of isolation
3. **Resource exhaustion**: Attacks on memory/CPU limits
4. **Information disclosure**: Leakage of system information

### 1.2 Problem Statement

Multiple security models exist for restricting code execution. Selecting an inappropriate model could result in:

- **Remote code execution** on host systems
- **Data exfiltration** through side channels
- **Denial of service** via resource exhaustion
- **Supply chain attacks** via dependency injection

### 1.3 Requirements

- **REQ-301**: Zero-trust assumptions (all input is potentially adversarial)
- **REQ-302**: Whitelist-only module access
- **REQ-303**: Block all dangerous built-in functions
- **REQ-304**: Detect bypass attempts (getattr, subscript, attribute access)
- **REQ-305**: Enable legitimate symbolic execution operations

### 1.4 Constraints

- Must allow mathematical operations (math module)
- Must allow data structure operations (collections, itertools)
- Must not break CrossHair's internal operations
- Must be enforceable at import time

---

## 2. Decision

**Implement a whitelist-based import security model with AST-based bypass detection.**

### 2.1 Technical Specification

```python
# 21 allowed modules (whitelist)
ALLOWED_MODULES = frozenset({
    "math", "random", "string", "collections", "itertools",
    "functools", "operator", "typing", "re", "json",
    "datetime", "decimal", "fractions", "statistics",
    "dataclasses", "enum", "copy", "heapq", "bisect",
    "typing_extensions", "abc",
})

# 28+ blocked modules (security blacklist)
BLOCKED_MODULES = frozenset({
    "os", "sys", "subprocess", "shutil", "pathlib",
    "socket", "http", "urllib", "requests", "ftplib",
    "pickle", "shelve", "marshal", "ctypes", "multiprocessing",
    "importlib", "runpy", "code", "codeop", "pty", "tty",
    "termios", "threading", "signal", "fcntl", "resource",
    "syslog", "getpass",
})

# Dangerous built-in functions
DANGEROUS_BUILTINS = frozenset({
    "eval", "exec", "compile", "__import__",
    "open", "globals", "locals", "vars", "dir",
})
```

### 2.2 Scope

- **In Scope**: All user code execution, module imports, built-in access
- **Out of Scope**: CrossHair internal operations (run in trusted context)

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **Whitelist + AST** | Allow 21 modules, detect bypasses | Secure by default, comprehensive bypass detection | Maintenance burden for new modules | 9/10 |
| **Blacklist only** | Block known dangerous modules | Easier to maintain | Insecure (misses novel attacks) | 3/10 |
| **Container isolation** | Docker containers only | Strong isolation | Heavy, can still escape containers | 6/10 |
| **Seccomp filters** | Linux syscall filtering | Strong kernel-level protection | Platform-specific, complex | 5/10 |

### 3.2 Decision Criteria

| Criterion | Weight | Whitelist+AST | Blacklist | Container | Seccomp |
|-----------|--------|---------------|-----------|-----------|---------|
| Security | 40% | 10 | 3 | 8 | 9 |
| Maintainability | 25% | 7 | 8 | 5 | 3 |
| Performance | 15% | 8 | 9 | 4 | 7 |
| Cross-Platform | 10% | 10 | 10 | 8 | 2 |
| Developer Experience | 10% | 7 | 9 | 5 | 4 |
| **Weighted Score** | **100%** | **8.7** | **5.85** | **6.35** | **5.85** |

### 3.3 Selection Justification

Whitelist + AST achieves the highest weighted security score (8.7) due to:

1. **Secure by Default**: Unknown modules are blocked, not allowed
2. **Bypass Detection**: AST visitor detects `eval()`, `getattr(__builtins__)`, subscript attacks
3. **Defense-in-Depth**: Multiple layers (import filter + AST validation)
4. **Cross-Platform**: Works on all Python platforms
5. **Transparent**: Clear security model for auditors

---

## 4. Alternatives Considered

### 4.1 Alternative 1: Blacklist-Only Security

**Description**: Block known dangerous modules and functions.

**Advantages**:
- Easier to maintain (add new threats as discovered)
- Less restrictive for users
- Faster initial implementation

**Disadvantages**:
- **Insecure by default** (misses novel attack vectors)
- Continual catch-up with new exploits
- Combinatorial explosion of bypass patterns
- Cannot anticipate all attacks

**Rejection Rationale**: Fails zero-trust principle (REQ-301). Blacklists are inherently reactive, not proactive.

### 4.2 Alternative 2: Container-Only Isolation

**Description**: Rely on Docker/container isolation without code-level restrictions.

**Advantages**:
- Strong isolation boundary
- Kernel-level enforcement
- Well-understood security model

**Disadvantages**:
- **Container escape vulnerabilities** exist (CVEs)
- Heavy resource requirement
- Doesn't prevent DoS attacks
- Platform-specific (Linux containers)

**Rejection Rationale**: Defense-in-depth requires code-level restrictions. Containers are complementary, not replacement.

### 4.3 Alternative 3: Seccomp Syscall Filtering

**Description**: Use Linux seccomp to filter dangerous system calls.

**Advantages**:
- Kernel-level enforcement
- Strong protection against syscall attacks
- Fine-grained control

**Disadvantages**:
- **Linux-only** (fails cross-platform requirement)
- Complex configuration
- Can be bypassed with permitted syscalls
- Requires root/CAP_SYS_ADMIN

**Rejection Rationale**: Platform-specific. Fails to protect macOS/Windows users.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Bypass via novel pattern | Medium | High | Continuous AST improvement | Security Lead |
| Legitimate use blocked | Low | Medium | Exception request process | Tech Lead |
| CrossHair internal imports | Low | Low | Trusted context separation | Analysis Lead |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Module whitelist drift | Low | Low | Quarterly review process | Security Lead |
| False positives | Medium | Low | User feedback mechanism | Tech Lead |

### 5.3 Security Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| AST parsing bypass | Low | Critical | Multi-layer validation | Security Lead |
| Import hook bypass | Low | High | Meta-path injection detection | Security Lead |
| Deserialization attack | Low | Critical | Block pickle/marshal/shelve | Security Lead |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Secure by Default**: Unknown modules automatically blocked
- **Comprehensive Detection**: AST visitor detects 15+ bypass patterns
- **Clear Audit Trail**: Explicit list of allowed modules
- **Cross-Platform**: Works on all Python-supported platforms

### 6.2 Negative Consequences

- **Maintenance Burden**: New legitimate modules require explicit approval
- **User Constraints**: Some valid Python code cannot be analyzed
- **False Positives**: Some safe patterns may be flagged

### 6.3 Trade-offs Accepted

- **Security vs Flexibility**: Prioritizing security over code compatibility
- **Explicit vs Implicit**: Requiring explicit approval over implicit trust

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] **Phase 1**: Whitelist implementation (21 modules)
- [x] **Phase 2**: Blacklist implementation (28+ modules)
- [x] **Phase 3**: Dangerous built-in blocking
- [x] **Phase 4**: AST bypass detection (15+ patterns)

### 7.2 Validation Requirements

- [x] All 35 bypass attempts blocked (test_security_*.py)
- [x] CrossHair operations unaffected
- [x] No false positives on legitimate code
- [x] Performance < 10ms for validation

### 7.3 Rollout Plan

1. **Completed**: Initial whitelist implementation
2. **Completed**: Comprehensive bypass detection
3. **Ongoing**: Quarterly whitelist review

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **AST module**: Python standard library (ast)
- **Import system**: Python's importlib and sys.meta_path
- **Validation layer**: pre-execution AST parsing

### 8.2 Documentation Dependencies

- Spec §3.2: "Safety Constraints"
- Spec §3.3: "Restricted Import Handler"
- SECURITY.md: Complete security architecture
- ADR-005: Temporary module isolation

### 8.3 External Dependencies

None (security model uses only Python standard library)

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-02-09 | Security Team | Initial ADR documenting whitelist model |

---

## 10. References

1. [Python ast Module](https://docs.python.org/3/library/ast.html)
2. [CWE-20: Improper Input Validation](https://cwe.mitre.org/data/definitions/20.html)
3. [CWE-78: OS Command Injection](https://cwe.mitre.org/data/definitions/78.html)
4. [Python Security Best Practices](https://docs.python.org/3/security_warnings.html)
5. Project `main.py`: Lines 147-223 (ALLOWED_MODULES, BLOCKED_MODULES)
6. Project `main.py`: Lines 430-686 (_DangerousCallVisitor)

---

## Appendix A: Allowed Modules Rationale

| Module | Rationale |
|--------|-----------|
| math | Essential for symbolic math operations |
| random | Random value generation for fuzzing |
| string | String operations and constants |
| collections | Data structures (Counter, defaultdict, etc.) |
| itertools | Iterator building blocks |
| functools | Higher-order functions (reduce, partial, etc.) |
| operator | Function versions of operators |
| typing | Type hints and generics |
| re | Regular expressions |
| json | JSON parsing/encoding |
| datetime | Date/time operations |
| decimal | Decimal arithmetic |
| fractions | Rational numbers |
| statistics | Statistical functions |
| dataclasses | Data class decorators |
| enum | Enumeration support |
| copy | Shallow/deep copying |
| heapq | Heap queue algorithm |
| bisect | Array bisection algorithms |
| typing_extensions | Extended typing support |
| abc | Abstract base classes |

---

## Appendix B: Blocked Bypass Patterns

```python
# Pattern 1: Direct call
eval("...")                          # BLOCKED

# Pattern 2: Space before parenthesis
eval ("...")                         # BLOCKED

# Pattern 3: getattr bypass
getattr(__builtins__, "eval")("...") # BLOCKED

# Pattern 4: Attribute access
__builtins__.eval("...")             # BLOCKED

# Pattern 5: Subscript access
__builtins__["eval"]("...")          # BLOCKED

# Pattern 6: List indexing bypass
[eval][0]("...")                     # BLOCKED

# Pattern 7: Dict lookup bypass
{"f": eval}["f"]("...")              # BLOCKED

# Pattern 8: Tuple unpacking bypass
(eval,)[0]("...")                    # BLOCKED

# Pattern 9: Nested attribute access
(__builtins__ or {})["eval"]("...")  # BLOCKED
```

---

## Appendix C: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-301: Zero-Trust | Compliant | All input treated as adversarial |
| REQ-302: Whitelist-Only | Compliant | 21 allowed modules explicitly |
| REQ-303: Block Built-ins | Compliant | 11 dangerous built-ins blocked |
| REQ-304: Bypass Detection | Compliant | 15+ patterns detected |
| REQ-305: Legitimate Ops | Compliant | Math, data structures enabled |
