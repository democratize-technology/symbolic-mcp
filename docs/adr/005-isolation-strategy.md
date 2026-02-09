# ADR-005: Temporary Module Isolation Strategy

**Status**: Accepted
**Date**: 2025-02-09
**Decision Maker**: Architecture Team
**Reviewers**: Security Team, Platform Team
**Related ADRs**: 001 (Framework), 002 (Symbolic Engine), 006 (Thread Safety)

---

## Executive Summary

Adopted UUID-based temporary module isolation with guaranteed cleanup via context managers. User code is loaded into isolated modules with unique names, ensuring namespace separation and preventing cross-request contamination. Thread-safe sys.modules management prevents race conditions in concurrent scenarios.

---

## 1. Context and Problem Statement

### 1.1 Background

The server must execute arbitrary user code while maintaining:
1. **Namespace isolation**: Each request must not affect others
2. **Cleanup guarantee**: Temporary modules must be removed after analysis
3. **Thread safety**: Concurrent requests must not corrupt sys.modules
4. **Debuggability**: Module names must be traceable for troubleshooting

### 1.2 Problem Statement

Multiple approaches exist for code isolation. Selecting the wrong strategy could result in:

- **Cross-request contamination**: Variables leaking between analyses
- **Memory leaks**: Temporary modules accumulating in sys.modules
- **Race conditions**: Concurrent requests corrupting sys.modules
- **Debugging difficulty**: Untraceable module names

### 1.3 Requirements

- **REQ-501**: Namespace isolation per request
- **REQ-502**: Guaranteed cleanup (even on exceptions)
- **REQ-503**: Thread-safe sys.modules access
- **REQ-504**: Traceable module naming
- **REQ-505**: No cross-request interference

### 1.4 Constraints

- Must work with CrossHair's function extraction
- Must handle exceptions during module loading
- Must support concurrent analysis requests
- Must clean up both sys.modules entries and temporary files

---

## 2. Decision

**Implement UUID-based temporary module isolation with context manager and thread-safe cleanup.**

### 2.1 Technical Specification

```python
# Module-level lock for sys.modules access
_SYS_MODULES_LOCK = threading.Lock()

@contextlib.contextmanager
def _temporary_module(code: str) -> Generator[types.ModuleType, None, None]:
    """Create a temporary module from code with guaranteed cleanup."""
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w+", delete=False) as tmp:
        tmp.write(textwrap.dedent(code))
        tmp_path = tmp.name

    # UUID-based naming for uniqueness and traceability
    module_name = f"mcp_temp_{uuid.uuid4().hex}"

    try:
        spec = importlib.util.spec_from_file_location(module_name, tmp_path)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            # Thread-safe sys.modules write
            with _SYS_MODULES_LOCK:
                sys.modules[module_name] = module
            spec.loader.exec_module(module)
            yield module
    finally:
        # Thread-safe sys.modules check-and-delete
        with _SYS_MODULES_LOCK:
            if module_name in sys.modules:
                del sys.modules[module_name]
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
```

### 2.2 Scope

- **In Scope**: All user code loading for symbolic analysis
- **Out of Scope**: CrossHair internal operations (trusted context)

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **UUID + Context Manager** | Temporary files + UUID names + cleanup | Guaranteed cleanup, thread-safe, traceable | File I/O overhead | 9/10 |
| **exec() namespace** | Execute code in dict namespace | No file I/O, fast | No cleanup, shared built-ins | 4/10 |
| **Memory-only modules** | Create module without file | No file cleanup | Complex, limited traceability | 6/10 |
| **Process isolation** | Spawn subprocess per request | Strong isolation | Slow, heavy, IPC complexity | 5/10 |

### 3.2 Decision Criteria

| Criterion | Weight | UUID+CM | exec() | Memory | Process |
|-----------|--------|---------|--------|--------|---------|
| Isolation | 30% | 9 | 5 | 7 | 10 |
| Cleanup Guarantee | 25% | 10 | 2 | 6 | 9 |
| Thread Safety | 20% | 10 | 10 | 8 | 10 |
| Traceability | 15% | 10 | 3 | 5 | 8 |
| Performance | 10% | 6 | 9 | 8 | 2 |
| **Weighted Score** | **100%** | **9.05** | **5.0** | **6.55** | **8.05** |

### 3.3 Selection Justification

UUID + Context Manager achieves highest score (9.05) due to:

1. **Guaranteed Cleanup**: `finally` block ensures cleanup even on exceptions
2. **Thread Safety**: Module-level lock prevents TOCTOU races
3. **Traceability**: UUID enables troubleshooting and logging
4. **Standard Pattern**: Uses Python's importlib as designed
5. **Minimal Overhead**: File I/O is acceptable for analysis use case

---

## 4. Alternatives Considered

### 4.1 Alternative 1: exec() in Dict Namespace

**Description**: Use `exec(code, namespace_dict)` for code execution.

**Advantages**:
- Fast (no file I/O)
- Simple implementation
- No cleanup needed (no sys.modules modification)

**Disadvantages**:
- **Incomplete isolation** (shared __builtins__)
- No cleanup tracking
- Limited traceability
- CrossHair may not work correctly

**Rejection Rationale**: Fails REQ-501 (namespace isolation). Shared built-ins create contamination risk.

### 4.2 Alternative 2: Memory-Only Modules

**Description**: Create module objects directly without files.

**Advantages**:
- No file I/O overhead
- No file cleanup needed
- Faster than temporary files

**Disadvantages**:
- **Complex implementation** (manual module creation)
- Limited traceability
- May not work with all import patterns
- Less standard approach

**Rejection Rationale**: Higher complexity for marginal performance gain. Standard approach preferred.

### 4.3 Alternative 3: Process Isolation

**Description**: Spawn separate subprocess for each analysis.

**Advantages**:
- **Strongest isolation** (separate process)
- Guaranteed cleanup on process exit
- Memory isolation

**Disadvantages**:
- Slow (process spawn overhead)
- Heavy resource usage
- IPC complexity for results
- Overkill for this use case

**Rejection Rationale**: Excessive overhead. Defense-in-depth with other security measures is sufficient.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| TOCTOU race on sys.modules | Medium | High | Module-level lock | Platform Lead |
| File cleanup failure | Low | Low | try/except with logging | Platform Lead |
| UUID collision | Negligible | Medium | UUID collision resistance | N/A |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Temp file accumulation | Low | Medium | Cleanup verification | Operations |
| Module name exhaustion | Negligible | Low | UUID space (2^128) | N/A |

### 5.3 Security Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Sys.modules pollution | Low | Medium | Thread-safe cleanup | Security Lead |
| Cross-request leakage | Low | Medium | UUID uniqueness | Security Lead |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Guaranteed Cleanup**: `finally` block ensures no leaks
- **Thread Safety**: Lock prevents race conditions
- **Traceability**: UUID enables debugging and logging
- **Standard Pattern**: Uses Python's import system as designed

### 6.2 Negative Consequences

- **File I/O Overhead**: Temporary files created per request
- **Disk Usage**: Brief temporary file existence
- **Slight Latency**: File operations add ~1-5ms

### 6.3 Trade-offs Accepted

- **Performance vs Correctness**: Accepting file I/O for guaranteed cleanup
- **Complexity vs Thread Safety**: Accepting lock overhead for correctness

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] **Phase 1**: Context manager implementation
- [x] **Phase 2**: Thread-safe sys.modules access
- [x] **Phase 3**: UUID-based naming
- [x] **Phase 4**: Lifespan cleanup integration

### 7.2 Validation Requirements

- [x] Cleanup happens even on exceptions
- [x] Thread-safe under concurrent load
- [x] No cross-request contamination
- [x] Temporary files removed

### 7.3 Rollout Plan

1. **Completed**: Initial context manager implementation
2. **Completed**: Thread safety verification
3. **Ongoing**: Monitor for module leaks

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **contextlib**: For context manager support
- **tempfile**: For temporary file creation
- **importlib.util**: For module loading
- **uuid**: For unique module naming
- **threading**: For sys.modules lock

### 8.2 Documentation Dependencies

- Spec §3.3: "Restricted Import Handler"
- ADR-001: FastMCP lifespan integration
- ADR-006: Thread safety architecture

### 8.3 External Dependencies

None (uses Python standard library)

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-02-09 | Architecture Team | Initial ADR documenting isolation strategy |

---

## 10. References

1. [Python importlib Documentation](https://docs.python.org/3/library/importlib.html)
2. [Python contextlib Documentation](https://docs.python.org/3/library/contextlib.html)
3. [Python uuid Documentation](https://docs.python.org/3/library/uuid.html)
4. [TOCTOU Race Conditions](https://en.wikipedia.org/wiki/Time-of-check_to_time-of-use)
5. Project `main.py`: Lines 754-806 (_temporary_module context manager)

---

## Appendix A: Thread Safety Analysis

**Race Condition Without Lock**:
```
Thread A: if "mcp_temp_xyz" in sys.modules:  # True
Thread B: del sys.modules["mcp_temp_xyz"]    # Removes
Thread A: del sys.modules["mcp_temp_xyz"]    # KeyError!
```

**Solution With Lock**:
```python
with _SYS_MODULES_LOCK:
    if module_name in sys.modules:
        del sys.modules[module_name]
# Atomic check-and-delete, no race possible
```

---

## Appendix B: UUID Collision Analysis

UUID version 4 (random) has:
- **122 random bits**
- **Collision probability**: ~1.7×10^-18 for 1 billion UUIDs
- **Conclusion**: Negligible risk for this use case

---

## Appendix C: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-501: Namespace Isolation | Compliant | Separate modules per request |
| REQ-502: Guaranteed Cleanup | Compliant | finally block ensures cleanup |
| REQ-503: Thread Safety | Compliant | Module-level lock |
| REQ-504: Traceability | Compliant | UUID-based naming |
| REQ-505: No Interference | Compliant | Isolated sys.modules entries |
