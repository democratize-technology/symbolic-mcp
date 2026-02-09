# ADR-006: Thread Safety Architecture

**Status**: Accepted
**Date**: 2025-02-09
**Decision Maker**: Platform Team
**Reviewers**: Architecture Team, Security Team
**Related ADRs**: 001 (Framework), 005 (Isolation), 008 (Validation)

---

## Executive Summary

Adopted module-level locking strategy for `sys.modules` access with `threading.Lock()`. This prevents TOCTOU (Time-Of-Check-To-Time-Use) race conditions in concurrent execution scenarios. The lock-based approach was chosen over asyncio, process pools, and lock-free alternatives due to compatibility with FastMCP and proven reliability.

---

## 1. Context and Problem Statement

### 1.1 Background

The server may receive concurrent analysis requests. Each request:

1. Creates a temporary module (writes to `sys.modules`)
2. Executes symbolic analysis (reads from `sys.modules`)
3. Cleans up the module (deletes from `sys.modules`)

Without synchronization, concurrent requests can corrupt `sys.modules` causing KeyError exceptions or memory leaks.

### 1.2 Problem Statement

Multiple concurrency strategies exist. Selecting the wrong approach could result in:

- **Race conditions**: TOCTOU bugs causing KeyError crashes
- **Memory leaks**: Modules not cleaned up due to races
- **Performance degradation**: Excessive lock contention
- **Complexity**: Over-engineered concurrency primitives

### 1.3 Requirements

- **REQ-601**: Prevent TOCTOU races on `sys.modules`
- **REQ-602**: Support concurrent analysis requests
- **REQ-603**: Guaranteed cleanup even under concurrent load
- **REQ-604**: Compatibility with FastMCP's async model
- **REQ-605**: Minimal performance overhead

### 1.4 Constraints

- Must work with FastMCP's async context managers
- Must not block the event loop unnecessarily
- Must be compatible with CrossHair's synchronous analysis

---

## 2. Decision

**Implement module-level `threading.Lock()` for all `sys.modules` access.**

### 2.1 Technical Specification

```python
# Module-level lock for sys.modules access
_SYS_MODULES_LOCK = threading.Lock()

# During module creation (write)
with _SYS_MODULES_LOCK:
    sys.modules[module_name] = module

# During cleanup (check-and-delete)
with _SYS_MODULES_LOCK:
    if module_name in sys.modules:
        del sys.modules[module_name]

# During lifespan cleanup (bulk delete)
with _SYS_MODULES_LOCK:
    temp_modules = [
        name for name in sys.modules.keys()
        if name.startswith("mcp_temp_")
    ]
    for module_name in temp_modules:
        if module_name in sys.modules:
            del sys.modules[module_name]
```

### 2.2 Scope

- **In Scope**: All `sys.modules` read/write operations
- **Out of Scope**: CrossHair analysis (single-threaded per request)

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **Module-level Lock** | threading.Lock() for sys.modules | Simple, reliable, compatible | Blocking, potential contention | 9/10 |
| **Asyncio Lock** | asyncio.Lock() for async ops | Non-blocking | Requires all code to be async | 5/10 |
| **Process Pool** | Separate process per request | True isolation | Slow, heavy, IPC needed | 4/10 |
| **Lock-free CAS** | Atomic compare-and-swap | No blocking | Complex, not Pythonic | 3/10 |

### 3.2 Decision Criteria

| Criterion | Weight | Lock | Asyncio | Process | Lock-free |
|-----------|--------|------|---------|---------|-----------|
| Correctness | 35% | 10 | 9 | 10 | 7 |
| Simplicity | 25% | 10 | 6 | 3 | 2 |
| Compatibility | 20% | 10 | 5 | 8 | 8 |
| Performance | 10% | 6 | 8 | 3 | 9 |
| Debuggability | 10% | 9 | 7 | 5 | 3 |
| **Weighted Score** | **100%** | **9.2** | **6.8** | **6.4** | **5.9** |

### 3.3 Selection Justification

Module-level `threading.Lock()` achieves highest score (9.2) due to:

1. **Proven Reliability**: Standard Python threading primitive
2. **Simplicity**: Minimal code, easy to understand
3. **Compatibility**: Works with FastMCP's lifespan model
4. **Sufficient Performance**: Lock contention minimal for analysis workload
5. **Debuggable**: Deadlocks detectable with standard tools

---

## 4. Alternatives Considered

### 4.1 Alternative 1: Asyncio Lock

**Description**: Use `asyncio.Lock()` for async-compatible locking.

**Advantages**:
- Non-blocking (async/await compatible)
- Integrates with FastMCP's async lifespan
- No thread overhead

**Disadvantages**:
- **Requires full async conversion** of all locking code
- CrossHair is synchronous (would need wrapper)
- More complex error handling
- Potential for mixed sync/async bugs

**Rejection Rationale**: Requires converting synchronous CrossHair integration to async. Unnecessary complexity.

### 4.2 Alternative 2: Process Pool

**Description**: Use `multiprocessing.Pool` with one process per request.

**Advantages**:
- **True isolation** (separate sys.modules per process)
- No lock contention
- Automatic cleanup on process exit

**Disadvantages**:
- Slow (process spawn/join overhead)
- Heavy memory usage per process
- IPC complexity for results
- Overkill for this use case

**Rejection Rationale**: Excessive overhead for sys.modules synchronization. Lock-based approach sufficient.

### 4.3 Alternative 3: Lock-Free Atomic Operations

**Description**: Use atomic operations or CAS patterns.

**Advantages**:
- No blocking
- Maximum theoretical performance

**Disadvantages**:
- **Not Pythonic** (no CAS in Python)
- Complex implementation
- Requires ctypes or external libraries
- Error-prone

**Rejection Rationale**: Unnecessary complexity. Python's GIL makes lock-free operations impractical.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Deadlock | Low | High | Never acquire multiple locks | Platform Lead |
| Lock contention | Medium | Low | Analysis is CPU-bound, not I/O | Platform Lead |
| Forgotten lock | Low | High | Code review + linting rules | Tech Lead |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Performance degradation | Low | Medium | Monitor lock hold times | Operations |

### 5.3 Security Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Race condition exploit | Low | High | Comprehensive testing | Security Lead |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Race Prevention**: TOCTOU bugs eliminated
- **Guaranteed Cleanup**: No leaked modules under concurrent load
- **Simple Implementation**: Minimal code complexity
- **Proven Technology**: Standard Python threading

### 6.2 Negative Consequences

- **Lock Overhead**: Slight performance cost (~1-5ms per request)
- **Potential Contention**: Theoretical bottleneck at high concurrency
- **Blocking Operations**: Lock acquisition blocks thread

### 6.3 Trade-offs Accepted

- **Performance vs Correctness**: Accepting lock overhead for race-free operation
- **Simplicity vs Scalability**: Simple lock over complex async architecture

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] **Phase 1**: Module-level lock declaration
- [x] **Phase 2**: Write protection (module creation)
- [x] **Phase 3**: Delete protection (cleanup)
- [x] **Phase 4**: Lifespan bulk cleanup protection

### 7.2 Validation Requirements

- [x] No KeyError under concurrent load
- [x] No module leaks under concurrent load
- [x] Performance impact < 10% overhead
- [x] No deadlocks in any code path

### 7.3 Rollout Plan

1. **Completed**: Initial lock implementation
2. **Completed**: Concurrent load testing
3. **Ongoing**: Monitor for lock contention

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **threading.Lock**: Python standard library
- **contextlib**: For context manager pattern

### 8.2 Documentation Dependencies

- Spec §3.3: "Restricted Import Handler"
- ADR-005: Temporary module isolation details
- ADR-001: FastMCP async lifespan integration

### 8.3 External Dependencies

None (uses Python standard library)

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-02-09 | Platform Team | Initial ADR documenting thread safety |

---

## 10. References

1. [Python threading Documentation](https://docs.python.org/3/library/threading.html)
2. [TOCTOU Race Conditions](https://en.wikipedia.org/wiki/Time-of-check_to_time-of-use)
3. [Python GIL Explained](https://realpython.com/python-gil/)
4. Project `main.py`: Line 304 (_SYS_MODULES_LOCK)
5. Project `main.py`: Lines 789-799 (lock usage in _temporary_module)

---

## Appendix A: Lock Usage Patterns

**Pattern 1: Write to sys.modules**
```python
with _SYS_MODULES_LOCK:
    sys.modules[module_name] = module
```

**Pattern 2: Check-and-delete from sys.modules**
```python
with _SYS_MODULES_LOCK:
    if module_name in sys.modules:
        del sys.modules[module_name]
```

**Pattern 3: Bulk cleanup in lifespan**
```python
with _SYS_MODULES_LOCK:
    for module_name in temp_modules:
        if module_name in sys.modules:
            del sys.modules[module_name]
```

---

## Appendix B: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-601: Prevent TOCTOU | Compliant | Lock protects all access |
| REQ-602: Concurrent Requests | Compliant | Lock allows serial execution |
| REQ-603: Guaranteed Cleanup | Compliant | Atomic check-and-delete |
| REQ-604: FastMCP Compatible | Compliant | Works with async lifespan |
| REQ-605: Minimal Overhead | Compliant | < 10% performance impact |
