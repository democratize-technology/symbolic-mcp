# ADR-023: Defense-in-Depth Security Architecture

**Status**: Accepted
**Date**: 2026-02-15
**Decision Maker**: Security Team
**Reviewers**: Architecture Team, Operations
**Related ADRs**: 003 (Import Security), 004 (Resource Limits), 005 (Isolation), 008 (Validation), 011 (Auth), 022 (Builtins)

---

## Executive Summary

The Symbolic MCP server implements a defense-in-depth security architecture with 6 complementary layers: OAuth authentication, import whitelist, dangerous builtins blocking, resource limits, temporary module isolation, and AST validation. Each layer provides independent protection; compromise of one layer does not compromise the system.

---

## 1. Context and Problem Statement

### 1.1 Background

Executing arbitrary user code is inherently risky. No single security measure is sufficient:

- **Authentication**: Doesn't prevent authenticated users from malicious code
- **Import restrictions**: Doesn't prevent built-in function abuse
- **Resource limits**: Doesn't prevent information disclosure
- **Validation**: Doesn't prevent all attack patterns

### 1.2 Problem Statement

Security architecture requires:

- **Multiple layers**: Independent protection mechanisms
- **Fail-safe defaults**: Secure by default, explicitly allow exceptions
- **Compromise containment**: One layer failure doesn't compromise system
- **Auditability**: Each layer documented and testable

### 1.3 Requirements

- **REQ-2301**: Minimum 5 independent security layers
- **REQ-2302**: Each layer documented in separate ADR
- **REQ-2303**: Layers provide overlapping protection
- **REQ-2304**: Layer failure doesn't compromise other layers
- **REQ-2305**: All layers testable independently

### 1.4 Constraints

- Must work on all platforms (macOS, Linux, Windows)
- Must not break CrossHair's internal operations
- Must maintain reasonable performance

---

## 2. Decision

**Implement 6-layer defense-in-depth architecture with independent, overlapping protections.**

### 2.1 Technical Specification

```
┌────────────────────────────────────────────────────────────────┐
│                     Client Request                              │
└───────────────────────────┬────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────┐
│ Layer 1: OAuth 2.1 Authentication (ADR-011)                     │
│ - GitHub OAuth for HTTP transport                               │
│ - Validates bearer tokens                                       │
│ - Prevents unauthorized HTTP access                             │
│ STATUS: Active for HTTP, bypassed for stdio (local dev)         │
└───────────────────────────┬────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────┐
│ Layer 2: Import Whitelist (ADR-003)                             │
│ - 21 allowed modules (whitelist)                                │
│ - 28+ blocked modules (defense list)                            │
│ - Import-time enforcement                                       │
│ STATUS: Always active                                           │
└───────────────────────────┬────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────┐
│ Layer 3: Dangerous Builtins Blocking (ADR-022)                  │
│ - 9 dangerous built-in functions blocked                        │
│ - eval, exec, compile, __import__, open, etc.                   │
│ - AST-based detection                                           │
│ STATUS: Always active                                           │
└───────────────────────────┬────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────┐
│ Layer 4: Resource Limits (ADR-004)                              │
│ - Memory limit: 2048MB default, configurable                    │
│ - Code size limit: 64KB default                                 │
│ - Timeout enforcement                                           │
│ STATUS: Always active (platform-dependent on Windows)           │
└───────────────────────────┬────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────┐
│ Layer 5: Temporary Module Isolation (ADR-005)                   │
│ - UUID-based unique module names                                │
│ - Guaranteed cleanup (file + sys.modules)                       │
│ - Thread-safe module management                                 │
│ STATUS: Always active                                           │
└───────────────────────────┬────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────┐
│ Layer 6: AST-Based Validation (ADR-008)                         │
│ - Pre-execution AST parsing                                     │
│ - 15+ bypass pattern detection                                  │
│ - Comprehensive validation before code execution                │
│ STATUS: Always active                                           │
└───────────────────────────┬────────────────────────────────────┘
                            │
                            ▼
┌────────────────────────────────────────────────────────────────┐
│                   CrossHair Symbolic Execution                  │
└────────────────────────────────────────────────────────────────┘
```

### 2.2 Layer Summary

| Layer | ADR | Purpose | Always Active |
|-------|-----|---------|---------------|
| OAuth 2.1 | 011 | Transport authentication | HTTP only |
| Import Whitelist | 003 | Module access control | Yes |
| Builtins Blocking | 022 | Function access control | Yes |
| Resource Limits | 004 | DoS prevention | Yes* |
| Module Isolation | 005 | Cleanup guarantee | Yes |
| AST Validation | 008 | Bypass detection | Yes |

*Resource limits platform-dependent on Windows

### 2.3 Layer Independence

Each layer operates independently:

```python
# Layer 2: Import check (fails immediately if blocked import)
if base_module in BLOCKED_MODULES:
    raise ImportError(f"Module '{module_name}' is blocked")

# Layer 3: Builtin check (separate from import check)
if name in DANGEROUS_BUILTINS:
    return {"valid": False, "error": f"Blocked function: {name}"}

# Layer 4: Resource check (independent of code content)
if code_size > CODE_SIZE_LIMIT:
    return {"valid": False, "error": "Code size exceeds limit"}

# Layer 6: AST check (catches bypasses Layer 2/3 miss)
if visitor.dangerous_calls:
    return {"valid": False, "error": f"Blocked: {dangerous}"}
```

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **6-Layer Defense** (selected) | Multiple independent layers | Maximum protection, containment | More complexity | 9/10 |
| 3-Layer Defense | Auth + Import + Validation | Simpler | Less containment | 6/10 |
| Single-Layer Sandbox | Container-only | Simple isolation | Container escapes exist | 4/10 |
| No Defense-in-Depth | Single security measure | Simple | Single point of failure | 2/10 |

### 3.2 Decision Criteria

| Criterion | Weight | 6-Layer | 3-Layer | Sandbox | Single |
|-----------|--------|---------|---------|---------|--------|
| Security | 40% | 10 | 7 | 6 | 2 |
| Containment | 25% | 10 | 6 | 5 | 1 |
| Complexity | 15% | 5 | 7 | 8 | 9 |
| Auditability | 10% | 9 | 8 | 6 | 5 |
| Maintainability | 10% | 6 | 8 | 7 | 9 |
| **Weighted Score** | **100%** | **8.55** | **7.05** | **5.9** | **3.75** |

### 3.3 Selection Justification

6-Layer Defense achieves the highest score (8.55) due to:

1. **Maximum Security**: Multiple independent layers
2. **Containment**: Layer failure doesn't compromise system
3. **Auditability**: Each layer documented in separate ADR
4. **Overlapping Protection**: Multiple layers catch same attacks
5. **Platform Coverage**: Works across macOS, Linux, Windows

---

## 4. Alternatives Considered

### 4.1 Alternative 1: 3-Layer Defense

**Description**: Only Auth, Import Whitelist, and Validation.

**Advantages**:
- Simpler architecture
- Less code to maintain
- Easier to audit

**Disadvantages**:
- **Less containment**: 3 layers vs 6
- **Resource attacks**: No memory/timeout limits
- **Module leaks**: No isolation cleanup guarantee

**Rejection Rationale**: Insufficient containment for security-critical application.

### 4.2 Alternative 2: Container-Only Sandbox

**Description**: Run all code in Docker containers.

**Advantages**:
- Strong isolation boundary
- Well-understood security model
- Industry standard

**Disadvantages**:
- **Container escapes**: CVEs exist
- **Heavy resource usage**: Container per request
- **Platform-specific**: Doesn't work on all platforms
- **Doesn't replace code-level security**: Defense-in-depth still needed

**Rejection Rationale**: Containers are complementary, not replacement for code-level security.

### 4.3 Alternative 3: Single Security Layer

**Description**: Rely on one comprehensive security layer.

**Advantages**:
- Maximum simplicity
- Single point of control
- Easy to understand

**Disadvantages**:
- **Single point of failure**: One bypass compromises everything
- **No containment**: Failure is catastrophic
- **Insufficient**: No single layer covers all attacks

**Rejection Rationale**: Unacceptable risk for security-critical application.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Layer bypass | Low | Medium | Overlapping layers catch same attacks | Security |
| New attack vector | Medium | High | Continuous security review | Security |
| Layer interaction bugs | Low | Medium | Independent layer design | Dev Team |

### 5.2 Security Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Novel bypass technique | Low | Critical | 6 layers provide containment | Security |
| Zero-day in Python | Low | Critical | Resource limits contain exploitation | Security |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Maximum Security**: 6 independent layers
- **Containment**: Layer failure contained
- **Overlapping Protection**: Same attack blocked by multiple layers
- **Auditability**: Each layer documented separately
- **Platform Coverage**: Works on all platforms

### 6.2 Negative Consequences

- **Complexity**: 6 layers to understand and maintain
- **Performance**: Multiple validation passes
- **Documentation**: Must document all layers

### 6.3 Trade-offs Accepted

- **Security > Simplicity**: More layers for better protection
- **Containment > Performance**: Overlapping layers over speed

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] Layer 1: OAuth 2.1 Authentication (ADR-011)
- [x] Layer 2: Import Whitelist (ADR-003)
- [x] Layer 3: Dangerous Builtins (ADR-022)
- [x] Layer 4: Resource Limits (ADR-004)
- [x] Layer 5: Module Isolation (ADR-005)
- [x] Layer 6: AST Validation (ADR-008)

### 7.2 Validation Requirements

- [x] Each layer has dedicated tests
- [x] Layer bypass tests exist
- [x] Integration tests verify layer interaction
- [x] Documentation links to each ADR

### 7.3 Rollout Plan

1. **Completed**: All 6 layers implemented
2. **Completed**: Individual ADRs for each layer
3. **Ongoing**: Security review of new bypass patterns

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **ADR-003**: Import Whitelist
- **ADR-004**: Resource Limits
- **ADR-005**: Module Isolation
- **ADR-008**: AST Validation
- **ADR-011**: OAuth Authentication
- **ADR-022**: Dangerous Builtins

### 8.2 Documentation Dependencies

- Individual ADRs for each layer
- SECURITY.md (if exists)

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | Security Team | Initial ADR documenting defense-in-depth |

---

## 10. References

1. ADR-003: Whitelist-Based Import Security Model
2. ADR-004: Resource Limits Strategy
3. ADR-005: Temporary Module Isolation Strategy
4. ADR-008: AST-Based Security Validation Architecture
5. ADR-011: Authentication & Authorization
6. ADR-022: Dangerous Builtins Restriction Policy
7. NIST Cybersecurity Framework: Defense in Depth
8. OWASP: Layered Security

---

## Appendix A: Attack Scenario Analysis

| Attack Vector | Layer 1 | Layer 2 | Layer 3 | Layer 4 | Layer 5 | Layer 6 | Blocked By |
|--------------|---------|---------|---------|---------|---------|---------|------------|
| Unauthorized HTTP | ✅ | - | - | - | - | - | OAuth |
| `import os` | - | ✅ | - | - | - | - | Whitelist |
| `eval("...")` | - | - | ✅ | - | - | - | Builtins |
| Memory bomb | - | - | - | ✅ | - | - | Limits |
| Module leak | - | - | - | - | ✅ | - | Isolation |
| `getattr(__builtins__, "eval")` | - | - | - | - | - | ✅ | AST |
| Combined attack | - | ✅ | ✅ | - | - | ✅ | Multiple |

---

## Appendix B: Layer Interaction Matrix

| Layer | Independent | Overlaps With | Fallback For |
|-------|-------------|---------------|--------------|
| OAuth | Yes | - | - |
| Import Whitelist | Yes | AST Validation | - |
| Builtins | Yes | AST Validation | Import (for __import__) |
| Resource Limits | Yes | - | All (DoS) |
| Module Isolation | Yes | - | All (cleanup) |
| AST Validation | Yes | Import, Builtins | Import, Builtins |

---

## Appendix C: Security Testing Strategy

```bash
# Test each layer independently
pytest -m security -v

# Test Layer 2: Import whitelist
pytest tests/test_security.py::test_blocked_import -v

# Test Layer 3: Builtin blocking
pytest tests/test_security.py::test_eval_blocked -v

# Test Layer 6: AST bypass detection
pytest tests/test_security.py::test_getattr_bypass -v

# Integration test: All layers
pytest tests/test_security.py -v --cov=main
```

---

## Appendix D: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-2301: 5+ Layers | Compliant | 6 layers implemented |
| REQ-2302: Layer ADRs | Compliant | 6 dedicated ADRs |
| REQ-2303: Overlapping Protection | Compliant | Multiple layers catch same attacks |
| REQ-2304: Layer Independence | Compliant | Each layer operates independently |
| REQ-2305: Independent Testing | Compliant | Each layer has dedicated tests |
