# ADR-014: Stateless Request Processing Model

**Status**: Accepted
**Date**: 2026-02-15
**Decision Maker**: Architecture Team
**Reviewers**: Operations, Security Team
**Related ADRs**: 001 (Framework), 004 (Resource Limits), 006 (Thread Safety)

---

## Executive Summary

Adopted a stateless request processing model where each MCP tool invocation is completely independent. No session state, no caching between requests, no persistent connections. This simplifies scaling, improves security isolation, and eliminates complex state management bugs.

---

## 1. Context and Problem Statement

### 1.1 Background

Server architectures can be stateful (maintaining session data between requests) or stateless (each request independent). The choice affects:

1. **Scalability**: How easily can the server handle multiple concurrent clients?
2. **Security**: How is data isolated between users?
3. **Reliability**: What happens when requests fail?
4. **Complexity**: How much code is needed for state management?

### 1.2 Problem Statement

For a security-critical symbolic execution server, state management introduces risks:

- **Memory leaks**: Uncollected session data consumes memory
- **Security cross-talk**: One user's data visible to another
- **Timeout handling**: When to clean up abandoned sessions?
- **Concurrency bugs**: Race conditions in state access

### 1.3 Requirements

- **REQ-1401**: Each request is completely independent
- **REQ-1402**: No session state persists between requests
- **REQ-1403**: No caching of analysis results
- **REQ-1404**: Horizontal scaling without session affinity
- **REQ-1405**: Request isolation for security

### 1.4 Constraints

- FastMCP server model
- Symbolic analysis is CPU-bound (no async benefit from caching)
- Security requirements mandate isolation

---

## 2. Decision

**Implement fully stateless request processing with no session management.**

### 2.1 Technical Specification

```python
# Each tool invocation is self-contained
@mcp.tool()
def symbolic_check(code: str, function_name: str,
                   timeout_seconds: int = 30) -> _SymbolicCheckResult:
    # All state is local to this function call
    analyzer = SymbolicAnalyzer(timeout_seconds)  # New instance per request
    return analyzer.analyze(code, function_name)  # No caching

# No global analysis state
# No session storage
# No result caching
# No connection pooling for analysis
```

### 2.2 What IS NOT Stored

| Category | Examples | Rationale |
|----------|----------|-----------|
| Session Data | User preferences, analysis history | Security isolation |
| Analysis Cache | Previous results, path exploration | Correctness (code may change) |
| Module Cache | Loaded user modules | Security (code injection risk) |
| Connection State | Client identification, affinity | Scalability |

### 2.3 What IS Stored (Server-Level)

| Category | Examples | Rationale |
|----------|----------|-----------|
| Configuration | Environment variables, limits | Server-wide settings |
| Memory Limit | Process RLIMIT_AS | Security boundary |
| Module Lock | `_SYS_MODULES_LOCK` | Thread safety for sys.modules |

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **Stateless** (selected) | No session state | Simple, scalable, secure | Repeated work on same code | 9/10 |
| **Session-Based** | Store user sessions | Can cache results, resume work | Complexity, security risks | 5/10 |
| **Hybrid** | Cache results, no sessions | Performance + simplicity | Cache invalidation complexity | 6/10 |

### 3.2 Decision Criteria

| Criterion | Weight | Stateless | Session-Based | Hybrid |
|-----------|--------|-----------|---------------|--------|
| Security Isolation | 35% | 10 | 4 | 6 |
| Scalability | 25% | 10 | 4 | 7 |
| Simplicity | 20% | 10 | 4 | 5 |
| Reliability | 10% | 9 | 5 | 6 |
| Performance | 10% | 5 | 9 | 8 |
| **Weighted Score** | **100%** | **9.0** | **4.6** | **6.3** |

### 3.3 Selection Justification

Stateless achieves the highest score (9.0) due to:

1. **Security Isolation**: No data leakage between users
2. **Scalability**: Any server can handle any request (no session affinity)
3. **Simplicity**: No session lifecycle management code
4. **Reliability**: No corrupted state to recover from
5. **Performance Trade-off**: Symbolic analysis is CPU-bound; caching provides minimal benefit

---

## 4. Alternatives Considered

### 4.1 Alternative 1: Session-Based State

**Description**: Store user sessions with analysis history and preferences.

**Advantages**:
- Can resume interrupted analyses
- Can cache results for repeated requests
- User preferences persist

**Disadvantages**:
- **Security risk**: Session data exposure between users
- **Memory leaks**: Abandoned sessions consume memory
- **Complexity**: Session lifecycle, timeout handling, cleanup
- **Scalability**: Requires session affinity or distributed cache

**Rejection Rationale**: Security risks and complexity outweigh benefits.

### 4.2 Alternative 2: Result Caching

**Description**: Cache analysis results by code hash.

**Advantages**:
- Faster repeated requests
- Less CPU usage

**Disadvantages**:
- **Cache invalidation**: Code changes invalidate cache
- **Memory usage**: Cached results consume memory
- **Correctness risk**: Stale results if cache key insufficient
- **Hash collisions**: Different code with same hash

**Rejection Rationale**: Correctness risk from stale cache. Symbolic analysis is deterministic; client can cache if needed.

### 4.3 Alternative 3: Connection Pooling

**Description**: Maintain persistent connections with state.

**Advantages**:
- Reduced connection overhead
- Can maintain per-connection state

**Disadvantages**:
- **State complexity**: Connection state management
- **Timeout handling**: When to close idle connections?
- **Load balancing**: Connection affinity required

**Rejection Rationale**: MCP protocol doesn't benefit from connection pooling; each request is independent.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Repeated work on same code | High | Low | Client-side caching if needed | Client |
| No resume capability | Medium | Low | By design; accept trade-off | Architecture |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| None (stateless improves reliability) | N/A | N/A | N/A | N/A |

### 5.3 Security Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| None (stateless improves security) | N/A | N/A | N/A | N/A |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Horizontal Scaling**: Any server instance can handle any request
- **Security Isolation**: No data leakage between requests
- **Simplicity**: No session management code
- **Reliability**: No corrupted state to recover
- **Debugging**: Each request is self-contained

### 6.2 Negative Consequences

- **Repeated Work**: Same code analyzed multiple times
- **No Resume**: Long analyses cannot be paused/resumed
- **No History**: No record of previous analyses

### 6.3 Trade-offs Accepted

- **Simplicity > Performance**: Stateless simplicity over caching performance
- **Security > Convenience**: Security isolation over session convenience

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] Phase 1: All tools are stateless functions
- [x] Phase 2: No global analysis state
- [x] Phase 3: No session management code
- [x] Phase 4: New analyzer instance per request

### 7.2 Validation Requirements

- [x] No session state between requests
- [x] No caching of analysis results
- [x] Each request creates new analyzer instance
- [x] No persistent connections

### 7.3 Rollout Plan

1. **Completed**: Stateless implementation
2. **Completed**: Testing for request isolation
3. **Ongoing**: Monitor for accidental state introduction

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **FastMCP**: Stateless request handling
- **Thread Safety**: ADR-006 for concurrent stateless requests

### 8.2 Documentation Dependencies

- ADR-004: Resource Limits (per-request limits)
- ADR-006: Thread Safety Architecture

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | Architecture Team | Initial ADR documenting stateless model |

---

## 10. References

1. Project `main.py`: All tool functions are stateless
2. REST API Design: Stateless constraint (Roy Fielding)
3. ADR-006: Thread Safety Architecture

---

## Appendix A: Stateless vs Stateful Comparison

```
Stateless (Selected):
┌─────────┐     ┌─────────────┐     ┌──────────┐
│ Client  │────▶│ MCP Server  │────▶│ Analysis │
└─────────┘     └─────────────┘     └──────────┘
   Request         No State           Result
                     │
                     └─▶ Each request independent

Stateful (Rejected):
┌─────────┐     ┌─────────────┐     ┌──────────┐
│ Client  │────▶│ MCP Server  │────▶│ Analysis │
└─────────┘     └─────────────┘     └──────────┘
   Request      │ Session Store │    Result
                 │ Cache Layer   │
                 │ State Manager │
                     │
                     └─▶ State persists between requests
                         (complexity, security risks)
```

---

## Appendix B: Client-Side Caching Pattern

Clients who need caching can implement it:

```python
# Client-side caching example
_cache = {}

def cached_symbolic_check(code: str, function_name: str, timeout: int = 30):
    cache_key = hashlib.sha256(f"{code}:{function_name}:{timeout}".encode()).hexdigest()
    if cache_key in _cache:
        return _cache[cache_key]

    result = mcp.symbolic_check(code, function_name, timeout)
    _cache[cache_key] = result
    return result
```

This keeps the server simple while allowing clients to optimize.

---

## Appendix C: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-1401: Request Independence | Compliant | No shared state |
| REQ-1402: No Session State | Compliant | No session storage |
| REQ-1403: No Result Caching | Compliant | Each request re-analyzes |
| REQ-1404: Horizontal Scaling | Compliant | No session affinity needed |
| REQ-1405: Request Isolation | Compliant | Security boundary per request |
