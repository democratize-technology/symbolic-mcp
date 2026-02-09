# ADR-009: Error Handling Philosophy

**Status**: Accepted
**Date**: 2026-02-09
**Decision Maker**: Architecture Team
**Reviewers**: Security Lead, Platform Team
**Related ADRs**: 001 (Framework), 003 (Security Model), 008 (Validation)

---

## Executive Summary

Adopted structured error response pattern over exception propagation for all client-facing APIs. All errors are returned as dictionaries with consistent `{status, error_type, message}` structure. This prevents information leakage, provides actionable error messages, and maintains protocol compliance with FastMCP's masked error mode.

---

## 1. Context and Problem Statement

### 1.1 Background

The Symbolic MCP server executes arbitrary user code and performs complex analysis operations. Error scenarios include:
- Syntax errors in user code
- Function signature mismatches
- Security validation failures
- Analysis timeouts
- Unsupported Python constructs

### 1.2 Problem Statement

Multiple error handling approaches exist for MCP servers. Selecting the wrong approach could result in:
- **Information leakage**: Internal details exposed to clients
- **Protocol violations**: Breaking MCP JSON-RPC contract
- **Poor UX**: Cryptic or unactionable error messages
- **Security bypasses**: Errors revealing system information

### 1.3 Requirements

- **REQ-901**: All errors returned as structured dictionaries (never exceptions)
- **REQ-902**: Consistent error response format across all tools
- **REQ-903**: Security errors use "ValidationError" type
- **REQ-904**: FastMCP's `mask_error_details=True` enabled
- **REQ-905**: Actionable error messages with context

### 1.4 Constraints

- Must work with FastMCP's error handling model
- Must not expose internal stack traces to clients
- Must maintain compatibility with MCP JSON-RPC protocol
- Must be consistent across all five tools

---

## 2. Decision

**All tools return structured error dictionaries; exceptions are never propagated to clients.**

### 2.1 Technical Specification

```python
# Standard error response format (all tools)
{
    "status": "error",
    "error_type": "ValueError" | "SyntaxError" | "ValidationError" | ...,
    "message": "Human-readable description",
    # Tool-specific fields (populated even on error)
    "counterexamples": [],
    "paths_explored": 0,
    "time_seconds": 0.0,
    ...
}

# FastMCP configuration
mcp = FastMCP(
    "Symbolic Execution Server",
    lifespan=lifespan,
    mask_error_details=True,  # Hide internal details
)
```

### 2.2 Status Value Taxonomy

| Tool | Success Values | Error Value |
|------|----------------|-------------|
| `symbolic_check` | `verified`, `counterexample` | `error`, `timeout` |
| `find_path_to_exception` | `found`, `unreachable` | `error` |
| `compare_functions` | `equivalent`, `different` | `error` |
| `analyze_branches` | `complete` | `error` |
| `health_check` | `healthy` | N/A |

### 2.3 Error Type Hierarchy

| Error Type | Usage | Examples |
|------------|-------|----------|
| `ValueError` | Invalid input parameters | Function not found, invalid timeout |
| `SyntaxError` | Code parsing failures | Line number included in response |
| `ValidationError` | Security violations | Blocked imports, dangerous calls |
| `ImportError` | Module loading failures | Blocked module access |
| `TimeoutError` | Analysis exceeded time limit | Mapped to `error` status |
| `RuntimeError` | Unexpected errors | Generic fallback |

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **Structured Responses** | Dict with status/error_type/message | Secure, consistent, actionable | More boilerplate | 9/10 |
| **Exception Propagation** | Let exceptions bubble to FastMCP | Less code, Pythonic | Info leakage, protocol issues | 4/10 |
| **Hybrid** | Structured for security, exceptions for UX | Best of both | Inconsistent, complex | 6/10 |

### 3.2 Decision Criteria

| Criterion | Weight | Structured | Exceptions | Hybrid |
|-----------|--------|-----------|------------|--------|
| Security | 35% | 10 | 3 | 7 |
| Consistency | 25% | 10 | 5 | 6 |
| Maintainability | 20% | 7 | 9 | 5 |
| UX | 10% | 8 | 9 | 8 |
| Protocol Compliance | 10% | 10 | 4 | 7 |
| **Weighted Score** | **100%** | **9.05** | **5.0** | **6.45** |

### 3.3 Selection Justification

Structured responses achieve the highest score due to:
1. **Security**: No stack traces or internal details leaked
2. **Consistency**: All tools follow same pattern
3. **Protocol Compliance**: Works correctly with FastMCP's error masking
4. **Actionability**: Error types guide client handling

---

## 4. Alternatives Considered

### 4.1 Alternative 1: Exception Propagation

**Description**: Allow Python exceptions to propagate to FastMCP.

**Advantages**:
- Less boilerplate code
- Pythonic patterns
- FastMCP handles serialization

**Disadvantages**:
- **Information leakage**: Stack traces exposed if `mask_error_details=False`
- **Inconsistent format**: Different exceptions serialize differently
- **Less control**: Cannot customize error messages

**Rejection Rationale**: Fails REQ-904 (security). Exceptions risk exposing internal details.

### 4.2 Alternative 2: Hybrid Approach

**Description**: Use structured responses for security errors, exceptions for others.

**Advantages**:
- Reduced boilerplate for non-critical errors
- Security where it matters

**Disadvantages**:
- **Inconsistent**: Clients must handle two patterns
- **Complex**: More code paths to test
- **Error-prone**: Easy to forget structured pattern

**Rejection Rationale**: Fails REQ-902 (consistency). Hybrid is confusing for API consumers.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Boilerplate bloat | Medium | Low | Helper functions for common patterns | Tech Lead |
| Inconsistent fields | Low | Medium | TypedDict schemas with validation | Tech Lead |

### 5.2 Security Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Info in messages | Low | Medium | Review all error strings | Security Lead |
| mask_error_details bypass | Low | High | Keep FastMCP updated | Security Lead |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Security**: No internal details leaked
- **Consistency**: Predictable error handling
- **Client UX**: Actionable error messages
- **Protocol Compliant**: Works with MCP tool spec

### 6.2 Negative Consequences

- **Boilerplate**: Each tool needs error handling code
- **Maintenance**: New fields must be added to error responses

### 6.3 Trade-offs Accepted

- **Code verbosity vs Security**: Accepting more code for secure error handling
- **Consistency vs Convenience**: Structured responses over exception propagation

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] **Phase 1**: Standard error response format defined
- [x] **Phase 2**: All tools use structured responses
- [x] **Phase 3**: FastMCP configured with mask_error_details=True
- [x] **Phase 4**: TypedDict schemas for each tool

### 7.2 Validation Requirements

- [x] No exceptions propagate to clients
- [x] All error responses include status="error"
- [x] error_type is one of defined types
- [x] Security errors use ValidationError

### 7.3 Rollout Plan

1. **Completed**: Initial implementation
2. **Completed**: Documentation in ADR
3. **Ongoing**: Review error messages for clarity

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **FastMCP >= 2.0.0**: mask_error_details support
- **TypedDict schemas**: Type safety for responses

### 8.2 Documentation Dependencies

- Spec §5.2: Error handling requirements
- ADR-001: FastMCP framework
- ADR-003: Security model

---

## 9. References

1. Project `main.py`: Lines 827-836 (standard error format)
2. Project `main.py`: Line 1471 (mask_error_details configuration)
3. Project `main.py`: Lines 822-836 (ValidationError handling)

---

## Appendix A: Error Response Examples

### Security Error
```json
{
  "status": "error",
  "error_type": "ValidationError",
  "message": "Blocked function call: eval",
  "counterexamples": [],
  "paths_explored": 0,
  "paths_verified": 0,
  "time_seconds": 0.0015,
  "coverage_estimate": 0.0
}
```

### Syntax Error
```json
{
  "status": "error",
  "error_type": "SyntaxError",
  "message": "Syntax error: invalid syntax (unknown_line, line 5)",
  "counterexamples": [],
  "paths_explored": 0,
  "paths_verified": 0,
  "time_seconds": 0.0023,
  "coverage_estimate": 0.0
}
```

### Function Not Found
```json
{
  "status": "error",
  "error_type": "ValueError",
  "message": "Function 'missing_func' not found in code",
  "counterexamples": [],
  "paths_explored": 0,
  "paths_verified": 0,
  "time_seconds": 0.0045,
  "coverage_estimate": 0.0
}
```

---

## Appendix B: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-901: Structured Responses | Compliant | All tools use dict format |
| REQ-902: Consistent Format | Compliant | {status, error_type, message} |
| REQ-903: ValidationError Type | Compliant | Security violations use this |
| REQ-904: Masked Details | Compliant | mask_error_details=True |
| REQ-905: Actionable Messages | Compliant | Context in all messages |
