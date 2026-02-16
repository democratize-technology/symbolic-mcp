# ADR-019: Python Version Compatibility Matrix

**Status**: Accepted
**Date**: 2026-02-15
**Decision Maker**: Platform Team
**Reviewers**: Development Team, Operations
**Related ADRs**: 001 (Framework), 012 (Single-File Architecture)

---

## Executive Summary

Supporting Python 3.11, 3.12, and 3.13 with `requires-python = ">=3.11"`. This covers the latest stable releases, provides modern type hint syntax (`X | Y`), and aligns with FastMCP 2.0 requirements. Python 3.10 and earlier are not supported due to missing typing features.

---

## 1. Context and Problem Statement

### 1.1 Background

Python version support affects:

1. **Type hint syntax**: 3.10+ supports `X | Y`, 3.9 requires `Union[X, Y]`
2. **Standard library features**: New modules and improvements
3. **Dependency compatibility**: Some packages require newer Python
4. **User reach**: More versions = more potential users

### 1.2 Problem Statement

Version support involves trade-offs:

- **Reach vs. Features**: Older versions reach more users but lack features
- **Maintenance vs. Compatibility**: More versions = more testing burden
- **Syntax vs. Backport**: Modern syntax vs. typing_extensions

### 1.3 Requirements

- **REQ-1901**: Support Python 3.11, 3.12, 3.13
- **REQ-1902**: Use modern type hint syntax (`X | Y`)
- **REQ-1903**: Single version of code (no version branches)
- **REQ-1904**: Test all supported versions in CI
- **REQ-1905**: Clear deprecation policy

### 1.4 Constraints

- FastMCP 2.0 requires Python 3.10+
- CrossHair supports Python 3.8+ but newer is better
- Modern typing syntax improves readability

---

## 2. Decision

**Support Python 3.11, 3.12, 3.13 with `requires-python = ">=3.11"`.**

### 2.1 Technical Specification

```toml
# pyproject.toml
[project]
requires-python = ">=3.11"

classifiers = [
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
    "Programming Language :: Python :: 3 :: Only",
]

[tool.black]
target-version = ["py311", "py312", "py313"]

[tool.mypy]
python_version = "3.11"

# tox configuration for multi-version testing
[tool.tox]
legacy_tox_ini = """
[tox]
envlist = py311,py312,py313,flake8,mypy,bandit,security
"""
```

### 2.2 Version Support Matrix

| Python Version | Support Status | Type Hints | Tested in CI |
|----------------|----------------|------------|--------------|
| 3.13 | ✅ Full | Modern | Yes |
| 3.12 | ✅ Full | Modern | Yes |
| 3.11 | ✅ Full | Modern | Yes |
| 3.10 | ❌ Not Supported | Modern | No |
| 3.9 | ❌ Not Supported | Legacy | No |
| 3.8 | ❌ Not Supported | Legacy | No |

### 2.3 Modern Type Hint Syntax

```python
# Python 3.10+ syntax (used in project)
def func(x: int | None) -> list[str]:
    ...

# Python 3.9 syntax (NOT used)
from typing import Union, List
def func(x: Union[int, None]) -> List[str]:
    ...
```

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **3.11+** (selected) | Support 3.11, 3.12, 3.13 | Modern syntax, active support | Excludes 3.10 users | 9/10 |
| 3.10+ | Support 3.10, 3.11, 3.12, 3.13 | Wider reach | More test burden | 7/10 |
| 3.9+ | Support 3.9 through 3.13 | Maximum reach | Legacy syntax, typing_extensions | 5/10 |
| 3.12+ | Support 3.12, 3.13 only | Latest features | Excludes many users | 6/10 |

### 3.2 Decision Criteria

| Criterion | Weight | 3.11+ | 3.10+ | 3.9+ | 3.12+ |
|-----------|--------|-------|-------|------|-------|
| Modern Syntax | 30% | 10 | 10 | 4 | 10 |
| User Reach | 25% | 7 | 9 | 10 | 4 |
| Maintenance Burden | 20% | 8 | 6 | 4 | 9 |
| CI Complexity | 15% | 8 | 6 | 4 | 9 |
| EOL Timeline | 10% | 9 | 7 | 4 | 10 |
| **Weighted Score** | **100%** | **8.55** | **7.95** | **5.0** | **8.1** |

### 3.3 Selection Justification

Python 3.11+ achieves the highest score (8.55) due to:

1. **Modern Syntax**: `X | Y` unions, `list[str]` generics
2. **Active Support**: 3.11, 3.12, 3.13 all receive security fixes
3. **Manageable CI**: 3 versions to test (not 5)
4. **Good Reach**: 3.11 released October 2022 (widely available)
5. **Performance**: 3.11+ has significant performance improvements

---

## 4. Alternatives Considered

### 4.1 Alternative 1: Python 3.10+ Support

**Description**: Support Python 3.10, 3.11, 3.12, 3.13.

**Advantages**:
- Wider user reach (3.10 still common)
- Modern syntax still available

**Disadvantages**:
- **More CI burden**: 4 versions to test
- **Edge cases**: 3.10 has subtle differences
- **Declining relevance**: 3.10 EOL October 2026

**Rejection Rationale**: 3.11 is sufficiently available; 3.10 adds maintenance without significant benefit.

### 4.2 Alternative 2: Python 3.9+ Support

**Description**: Support Python 3.9 through 3.13.

**Advantages**:
- Maximum user reach
- Debian 11 ships with 3.9

**Disadvantages**:
- **Legacy syntax**: Must use `Union[X, Y]` or typing_extensions
- **Heavy typing_extensions**: More backports needed
- **More CI burden**: 5 versions to test
- **3.9 EOL**: October 2025 (ended)

**Rejection Rationale**: Legacy syntax hurts readability; 3.9 EOL has passed.

### 4.3 Alternative 3: Python 3.12+ Only

**Description**: Support only Python 3.12 and 3.13.

**Advantages**:
- Latest features (GIL improvements in 3.13)
- Minimal CI matrix
- Forward-looking

**Disadvantages**:
- **Excludes many users**: 3.12 released October 2023
- **Premature**: Many users still on 3.11

**Rejection Rationale**: Too restrictive for current user base.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Version-specific bugs | Low | Medium | Multi-version CI testing | Dev Team |
| Dependency incompatibility | Low | Medium | Pin dependencies, test matrix | Dev Team |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| User can't install | Low | Low | Clear version requirement in docs | Documentation |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Modern Syntax**: Clean, readable type hints
- **Performance**: 3.11+ is significantly faster
- **Active Support**: All versions receive security updates
- **Manageable CI**: 3 versions to test

### 6.2 Negative Consequences

- **Excluded Users**: Users on Python 3.10 and earlier cannot use
- **Dependency Constraints**: Some packages may require 3.12+

### 6.3 Trade-offs Accepted

- **Modernity > Reach**: Modern syntax over maximum compatibility
- **Manageability > Coverage**: Fewer versions over wider testing

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] Phase 1: `requires-python = ">=3.11"` in pyproject.toml
- [x] Phase 2: Classifiers for 3.11, 3.12, 3.13
- [x] Phase 3: tox configuration for multi-version testing
- [x] Phase 4: Modern type hint syntax throughout

### 7.2 Validation Requirements

- [x] All supported versions tested in CI
- [x] mypy configured for Python 3.11
- [x] Black targets 3.11, 3.12, 3.13
- [x] No typing backports needed

### 7.3 Rollout Plan

1. **Completed**: Initial version configuration
2. **Completed**: CI matrix for all versions
3. **Ongoing**: Add Python 3.14 when released

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **FastMCP 2.0**: Requires Python 3.10+
- **CrossHair**: Supports 3.8+ (we require 3.11+)
- **tox**: Multi-version testing

### 8.2 Documentation Dependencies

- README.md: Installation requirements
- pyproject.toml: Version constraints

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | Platform Team | Initial ADR documenting version support |

---

## 10. References

1. Project `pyproject.toml`: Lines 32-48 (classifiers), Line 49 (requires-python)
2. Python Release Schedule: https://devguide.python.org/versions/
3. PEP 604: Union syntax (`X | Y`)
4. PEP 585: Generic syntax (`list[str]`)

---

## Appendix A: Python Version Timeline

| Version | Release Date | EOL Date | Status |
|---------|--------------|----------|--------|
| 3.8 | Oct 2020 | Oct 2024 | ❌ EOL |
| 3.9 | Oct 2020 | Oct 2025 | ❌ EOL |
| 3.10 | Oct 2021 | Oct 2026 | ⚠️ Approaching EOL |
| 3.11 | Oct 2022 | Oct 2027 | ✅ Supported |
| 3.12 | Oct 2023 | Oct 2028 | ✅ Supported |
| 3.13 | Oct 2024 | Oct 2029 | ✅ Supported |

---

## Appendix B: Modern Type Hint Features

```python
# Python 3.10+ features used in project

# Union syntax (PEP 604)
x: int | None  # Instead of Union[int, None]

# Generic syntax (PEP 585)
items: list[str]  # Instead of List[str]
mapping: dict[str, int]  # Instead of Dict[str, int]

# TypeGuard (PEP 647) - 3.10+
from typing import TypeGuard
def is_string_list(val: list[object]) -> TypeGuard[list[str]]:
    return all(isinstance(x, str) for x in val)

# ParamSpec (PEP 612) - 3.10+
from typing import ParamSpec, Callable
P = ParamSpec('P')
def decorator(f: Callable[P, int]) -> Callable[P, str]:
    ...
```

---

## Appendix C: CI Matrix Configuration

```yaml
# .github/workflows/test.yml
jobs:
  test:
    strategy:
      matrix:
        python-version: ['3.11', '3.12', '3.13']
    runs-on: ubuntu-latest
    steps:
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - run: pytest --cov=main
```

---

## Appendix D: Deprecation Policy

| Action | Timing | Process |
|--------|--------|---------|
| Add new Python version | At release | Add to matrix, classifiers |
| Drop oldest version | At EOL | Remove from matrix, update requires-python |
| Announce deprecation | 6 months before EOL | Update README, release notes |

---

## Appendix E: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-1901: Support 3.11-3.13 | Compliant | All tested in CI |
| REQ-1902: Modern Syntax | Compliant | `X | Y` unions |
| REQ-1903: Single Codebase | Compliant | No version branches |
| REQ-1904: Multi-Version CI | Compliant | tox + GitHub matrix |
| REQ-1905: Deprecation Policy | Compliant | Documented in appendix |
