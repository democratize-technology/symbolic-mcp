# ADR-015: TypedDict for Structured Responses

**Status**: Accepted
**Date**: 2026-02-15
**Decision Maker**: Architecture Team
**Reviewers**: Type Safety Team, API Team
**Related ADRs**: 009 (Error Handling), 013 (Tool Surface)

---

## Executive Summary

Adopted `TypedDict` from `typing_extensions` for all structured response types instead of Pydantic models or dataclasses. This provides type safety without runtime validation overhead, works naturally with JSON serialization, and maintains compatibility with FastMCP's dictionary-based return values.

---

## 1. Context and Problem Statement

### 1.1 Background

MCP tool responses must be JSON-serializable dictionaries. Python offers several approaches for structured data:

1. **TypedDict**: Type hints for dictionaries, no runtime validation
2. **Pydantic models**: Runtime validation, JSON serialization built-in
3. **dataclasses**: Python objects, require explicit serialization
4. **Plain dicts**: No type safety, no validation

### 1.2 Problem Statement

Choosing a response type strategy involves trade-offs:

- **Type Safety**: Static type checking vs. runtime validation
- **Performance**: Validation overhead vs. type hint overhead
- **Serialization**: Automatic vs. manual JSON conversion
- **FastMCP Compatibility**: Native support vs. adapter needed

### 1.3 Requirements

- **REQ-1501**: All tool responses must be type-checked by mypy
- **REQ-1502**: Responses must be JSON-serializable without adapters
- **REQ-1503**: No runtime validation overhead for normal responses
- **REQ-1504**: Support optional fields (NotRequired pattern)
- **REQ-1505**: Work with FastMCP's dictionary return values

### 1.4 Constraints

- FastMCP returns dictionaries, not objects
- MCP protocol requires JSON-serializable responses
- mypy strict mode enabled

---

## 2. Decision

**Use TypedDict for all structured response types with NotRequired for optional fields.**

### 2.1 Technical Specification

```python
from typing_extensions import TypedDict
from typing import Literal, NotRequired, Optional

class _Counterexample(TypedDict):
    """A counterexample found during symbolic execution."""
    args: dict[str, int | bool | None | str]
    kwargs: dict[str, int | bool | None | str]
    violation: str
    actual_result: str
    path_condition: str

class _SymbolicCheckResult(TypedDict):
    """Result of symbolic execution analysis."""
    status: Literal["verified", "counterexample", "timeout", "error"]
    counterexamples: list[_Counterexample]
    paths_explored: int
    paths_verified: int
    time_seconds: float
    coverage_estimate: float
    error_type: NotRequired[str]  # Optional field
    message: NotRequired[str]     # Optional field
```

### 2.2 TypedDict Patterns Used

| Pattern | Purpose | Example |
|---------|---------|---------|
| Required fields | Always present | `status: Literal["verified", ...]` |
| `NotRequired[T]` | Optional fields (error cases) | `error_type: NotRequired[str]` |
| `Literal[...]` | Enum-like constraints | `status: Literal["verified", ...]` |
| Nested TypedDict | Complex structures | `counterexamples: list[_Counterexample]` |
| Union types | Polymorphic fields | `int | bool | None | str` |

### 2.3 Response Type Hierarchy

```
_ToolDescription (resource)
_ResourceDescription (resource)
_SecurityConfigResult (resource)
_ServerConfigResult (resource)
_CapabilitiesResult (resource)
_Counterexample (shared)
_ValidationResult (internal)
_SymbolicCheckResult (symbolic_check)
_ExceptionPathResult (find_path_to_exception)
_FunctionComparisonResult (compare_functions)
_BranchInfo (analyze_branches)
_BranchAnalysisResult (analyze_branches)
_HealthCheckResult (health_check)
```

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **TypedDict** (selected) | Type hints for dicts | Type safety, zero runtime overhead, JSON-native | No runtime validation | 9/10 |
| Pydantic | Runtime models | Validation, JSON schema generation | Runtime overhead, adapter needed | 7/10 |
| dataclasses | Python objects | Clean syntax, type hints | Serialization overhead | 5/10 |
| Plain dicts | No structure | Zero overhead | No type safety | 2/10 |

### 3.2 Decision Criteria

| Criterion | Weight | TypedDict | Pydantic | dataclasses | Plain dicts |
|-----------|--------|-----------|----------|-------------|-------------|
| Type Safety | 30% | 9 | 9 | 9 | 1 |
| JSON Serialization | 25% | 10 | 9 | 5 | 10 |
| Performance | 20% | 10 | 5 | 7 | 10 |
| FastMCP Compatibility | 15% | 10 | 7 | 5 | 10 |
| Optional Fields | 10% | 9 | 10 | 8 | 1 |
| **Weighted Score** | **100%** | **9.4** | **7.85** | **6.85** | **5.05** |

### 3.3 Selection Justification

TypedDict achieves the highest score (9.4) due to:

1. **Type Safety**: Full mypy support with strict mode
2. **JSON Native**: TypedDict IS a dict, no serialization needed
3. **Zero Runtime Overhead**: No validation, no conversion
4. **FastMCP Native**: Works directly with FastMCP's dict returns
5. **NotRequired**: Clean syntax for optional fields (PEP 655)

---

## 4. Alternatives Considered

### 4.1 Alternative 1: Pydantic Models

**Description**: Use Pydantic BaseModel for all response types.

**Advantages**:
- Runtime validation
- JSON schema generation
- Rich ecosystem (validators, serializers)

**Disadvantages**:
- **Runtime overhead**: Validation on every response
- **Conversion needed**: Must call `.model_dump()` for FastMCP
- **Over-engineering**: Validation not needed for server-generated responses

**Rejection Rationale**: Server controls response generation; validation is redundant.

### 4.2 Alternative 2: dataclasses

**Description**: Use @dataclass decorator for response types.

**Advantages**:
- Clean syntax
- Type hints
- Standard library

**Disadvantages**:
- **Serialization**: Must convert to dict for JSON
- **Not JSON-native**: dataclass objects aren't dicts
- **FastMCP mismatch**: FastMCP expects dict returns

**Rejection Rationale**: Requires serialization layer; TypedDict is JSON-native.

### 4.3 Alternative 3: Plain Dicts with Comments

**Description**: Use plain dicts with type comments.

**Advantages**:
- Maximum simplicity
- Zero overhead

**Disadvantages**:
- **No type safety**: mypy cannot verify structure
- **No IDE support**: Autocomplete unavailable
- **Documentation burden**: Types only in comments

**Rejection Rationale**: Unacceptable for production code; violates type safety requirements.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Missing runtime validation | Medium | Low | Server controls response generation | Tech Lead |
| TypedDict syntax confusion | Low | Low | Clear documentation and examples | Dev Team |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| None significant | N/A | N/A | N/A | N/A |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Type Safety**: Full mypy strict mode compliance
- **JSON Native**: No serialization layer needed
- **Zero Overhead**: No runtime validation cost
- **IDE Support**: Autocomplete for TypedDict fields
- **NotRequired**: Clean optional field syntax

### 6.2 Negative Consequences

- **No Runtime Validation**: Malformed responses possible if code is buggy
- **Syntax Learning Curve**: TypedDict syntax less familiar than dataclasses

### 6.3 Trade-offs Accepted

- **Static vs Runtime**: Static type checking over runtime validation
- **Simplicity vs Validation**: Zero-overhead simplicity over validation safety net

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] Phase 1: All response types defined as TypedDict
- [x] Phase 2: NotRequired used for optional fields
- [x] Phase 3: Literal types for status enums
- [x] Phase 4: Nested TypedDict for complex structures

### 7.2 Validation Requirements

- [x] All tool return types are TypedDict
- [x] All TypedDict have complete type annotations
- [x] Optional fields use NotRequired
- [x] mypy --strict passes

### 7.3 Rollout Plan

1. **Completed**: TypedDict implementation
2. **Completed**: NotRequired for error fields
3. **Completed**: mypy strict mode compliance

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **typing_extensions**: TypedDict, NotRequired (PEP 655)
- **mypy >= 1.5**: TypedDict type checking
- **Python >= 3.11**: Type union syntax (`X | Y`)

### 8.2 Documentation Dependencies

- ADR-009: Error Handling Philosophy (uses NotRequired)
- ADR-013: Tool Surface Design (defines response types)

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | Architecture Team | Initial ADR documenting TypedDict strategy |

---

## 10. References

1. Project `main.py`: Lines 53-188 (TypedDict definitions)
2. PEP 655: NotRequired and Required
3. typing_extensions documentation
4. ADR-009: Error Handling Philosophy

---

## Appendix A: TypedDict Examples

```python
# Required fields only
class _HealthCheckResult(TypedDict):
    status: Literal["healthy"]
    version: str
    python_version: str
    crosshair_version: Optional[str]
    z3_version: Optional[str]
    platform: str
    memory_usage_mb: float

# Required + Optional fields
class _SymbolicCheckResult(TypedDict):
    # Always present
    status: Literal["verified", "counterexample", "timeout", "error"]
    counterexamples: list[_Counterexample]
    paths_explored: int
    paths_verified: int
    time_seconds: float
    coverage_estimate: float
    # Only present on error
    error_type: NotRequired[str]
    message: NotRequired[str]

# Nested TypedDict
class _BranchAnalysisResult(TypedDict):
    status: Literal["complete", "error"]
    branches: NotRequired[list[_BranchInfo]]  # List of nested TypedDict
    total_branches: NotRequired[int]
    # ...
```

---

## Appendix B: FastMCP Integration

```python
# TypedDict works directly with FastMCP
@mcp.tool()
def symbolic_check(code: str, function_name: str,
                   timeout_seconds: int = 30) -> _SymbolicCheckResult:
    # Return dict directly - it IS a _SymbolicCheckResult
    return {
        "status": "verified",
        "counterexamples": [],
        "paths_explored": 10,
        "paths_verified": 10,
        "time_seconds": 1.23,
        "coverage_estimate": 1.0,
    }

# No .model_dump() or .to_dict() needed!
```

---

## Appendix C: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-1501: Type Safety | Compliant | Full mypy support |
| REQ-1502: JSON Serialization | Compliant | TypedDict is dict |
| REQ-1503: No Runtime Overhead | Compliant | No validation |
| REQ-1504: Optional Fields | Compliant | NotRequired pattern |
| REQ-1505: FastMCP Compatible | Compliant | Native dict return |
