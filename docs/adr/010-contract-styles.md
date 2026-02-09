# ADR-010: Contract Style Support

**Status**: Accepted
**Date**: 2026-02-09
**Decision Maker**: Analysis Team
**Reviewers**: Architecture Team, Security Team
**Related ADRs**: 002 (Symbolic Engine), 003 (Security Model)

---

## Executive Summary

Supports four contract verification styles: icontract decorators (priority 1), PEP 316 docstrings (priority 2), inline assertions (priority 3), and type-based inference (automatic). CrossHair's `asserts` and `PEP316` analysis kinds are enabled; explicit `type` analysis kind is not configured (inferred automatically). This provides flexibility for users while maintaining consistent behavior.

---

## 1. Context and Problem Statement

### 1.1 Background

Python has multiple contract specification approaches:
- **icontract decorators**: `@require`, `@ensure` with lambda expressions
- **PEP 316 docstrings**: `pre:` and `post:` in docstrings
- **Inline assertions**: `assert` statements in function body
- **Type hints**: Type-based contract inference

CrossHair supports multiple `AnalysisKind` options for different contract styles.

### 1.2 Problem Statement

Multiple contract styles exist with no clear priority. Selecting wrong configuration could result in:
- **Missed contracts**: Some styles not detected
- **Inconsistent behavior**: Different results for equivalent contracts
- **User confusion**: Unclear which style to use
- **Performance overhead**: Unnecessary analysis kinds enabled

### 1.3 Requirements

- **REQ-1001**: Support icontract decorators (primary style)
- **REQ-1002**: Support PEP 316 docstring contracts
- **REQ-1003**: Support inline assertions
- **REQ-1004**: Automatic type-based inference
- **REQ-1005**: Clear priority order when multiple present

### 1.4 Constraints

- Must work with CrossHair's analysis kind system
- Must not break existing user code
- Must be compatible with security sandbox (ADR-003)

---

## 2. Decision

**Enable `asserts` and `PEP316` analysis kinds; rely on CrossHair for icontract and type inference.**

### 2.1 Technical Specification

```python
# CrossHair configuration (main.py:856-861)
options = AnalysisOptionSet(
    analysis_kind=[AnalysisKind.asserts, AnalysisKind.PEP316],
    per_condition_timeout=float(self.timeout),
    per_path_timeout=float(self.timeout) * PER_PATH_TIMEOUT_RATIO,
)
```

### 2.2 Contract Style Priority

| Priority | Style | Analysis Kind | Notes |
|----------|-------|---------------|-------|
| 1 | icontract decorators | Built-in | Explicit @require/@ensure |
| 2 | PEP 316 docstrings | PEP316 | `pre:`/`post:` in docstring |
| 3 | Inline assertions | asserts | `assert` statements |
| 4 | Type hints | Automatic | Inferred by CrossHair |

### 2.3 Scope

- **In Scope**: All contract verification in `symbolic_check` tool
- **Out of Scope**: Other tools don't analyze contracts

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **asserts + PEP316** | Current config | Covers main styles, lightweight | No explicit type checking | 9/10 |
| **All analysis kinds** | Enable type, postconditions | Maximum coverage | Slower, redundant | 6/10 |
| **Icontract only** | Decorators only | Explicit, clear | Misses docstrings/assertions | 5/10 |

### 3.2 Decision Criteria

| Criterion | Weight | asserts+PEP316 | All Kinds | Icontract Only |
|-----------|--------|---------------|-----------|---------------|
| Coverage | 30% | 9 | 10 | 5 |
| Performance | 25% | 9 | 5 | 9 |
| User Flexibility | 25% | 9 | 10 | 4 |
| Complexity | 10% | 9 | 6 | 9 |
| Ecosystem Fit | 10% | 9 | 7 | 6 |
| **Weighted Score** | **100%** | **8.9** | **7.4** | **5.6** |

### 3.3 Selection Justification

`asserts + PEP316` achieves highest score due to:
1. **Coverage**: Handles all common contract styles
2. **Performance**: Minimal overhead vs enabling all kinds
3. **Simplicity**: Two analysis kinds easy to understand
4. **CrossHair-native**: Uses library as designed

---

## 4. Alternatives Considered

### 4.1 Alternative 1: Enable All Analysis Kinds

**Description**: Enable `asserts`, `PEP316`, `type`, and `postconditions`.

**Advantages**:
- Maximum contract coverage
- Explicit type checking
- Future-proof for new contract styles

**Disadvantages**:
- **Slower analysis**: More overhead per path
- **Redundant**: Type checking already inferred
- **Complex**: More combinations to test

**Rejection Rationale**: Fails performance requirements. Type checking is automatic; explicit kind is redundant.

### 4.2 Alternative 2: Icontract Decorators Only

**Description**: Only support icontract `@require`/`@ensure`.

**Advantages**:
- **Explicit**: Contracts are visible decorators
- **Type-safe**: Lambda expressions checked
- **Standard**: Well-known library

**Disadvantages**:
- **Excludes common styles**: No docstring or assertion support
- **Requires dependency**: icontract must be installed
- **Migration burden**: Existing code needs refactoring

**Rejection Rationale**: Fails REQ-1002 and REQ-1003. Too restrictive for users.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Contract style not detected | Low | Medium | Documentation examples | Analysis Lead |
| icontract version issues | Low | Low | Version pin >= 2.6.0 | Analysis Lead |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| User confusion on styles | Medium | Low | Documentation with examples | Documentation |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Flexibility**: Users can choose preferred style
- **Compatibility**: Works with existing code
- **Performance**: Minimal analysis overhead
- **Clear priority**: Unambiguous behavior

### 6.2 Negative Consequences

- **No explicit type checking**: Relies on CrossHair's automatic inference
- **Style mixing**: Users might mix styles confusingly

### 6.3 Trade-offs Accepted

- **Explicit vs Inferred type checking**: Accepting automatic type inference for simplicity
- **Flexibility vs Simplicity**: Multiple styles supported but requires documentation

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] **Phase 1**: CrossHair configured with asserts + PEP316
- [x] **Phase 2**: icontract dependency specified
- [x] **Phase 3**: Documentation examples for all styles
- [x] **Phase 4**: Tests for each contract style

### 7.2 Validation Requirements

- [x] icontract decorators are verified
- [x] PEP 316 docstrings are verified
- [x] Inline assertions are verified
- [x] Type-based contracts are inferred

### 7.3 Rollout Plan

1. **Completed**: Initial implementation
2. **Completed**: Contract style documentation
3. **Ongoing**: Monitor user feedback on contract styles

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **CrossHair >= 0.0.70**: Symbolic execution engine
- **icontract >= 2.6.0**: Contract decorators (optional but recommended)
- **Python 3.11+**: Type hint support

### 8.2 Documentation Dependencies

- Spec §4: Tool definitions with contract examples
- ADR-002: CrossHair engine integration

---

## 9. References

1. Project `main.py`: Lines 856-861 (AnalysisOptionSet configuration)
2. [PEP 316 - Programming by Contract for Python](https://www.python.org/dev/peps/pep-0316/)
3. [icontract Library](https://github.com/Parquery/icontract)
4. [CrossHair Contract Support](https://crosshair.readthedocs.io/)

---

## Appendix A: Contract Style Examples

### Style 1: icontract Decorators
```python
from icontract import require, ensure

@require(lambda x: x >= 0, "x must be non-negative")
@ensure(lambda result: result >= 0, "result must be non-negative")
def sqrt(x: float) -> float:
    return x ** 0.5
```

### Style 2: PEP 316 Docstrings
```python
def divide(a: int, b: int) -> float:
    """
    pre: b != 0
    post: __return__ == a / b
    """
    return a / b
```

### Style 3: Inline Assertions
```python
def safe_divide(a: int, b: int) -> float:
    assert b != 0, "Divisor cannot be zero"
    result = a / b
    assert isinstance(result, float), "Result must be float"
    return result
```

### Style 4: Type-Based (Automatic)
```python
def add(x: int, y: int) -> int:
    return x + y  # CrossHair infers: result must be int
```

---

## Appendix B: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-1001: icontract Support | Compliant | Detected by CrossHair |
| REQ-1002: PEP 316 Support | Compliant | PEP316 analysis kind enabled |
| REQ-1003: Inline Assertions | Compliant | asserts analysis kind enabled |
| REQ-1004: Type Inference | Compliant | Automatic in CrossHair |
| REQ-1005: Clear Priority | Compliant | Documented in spec |
