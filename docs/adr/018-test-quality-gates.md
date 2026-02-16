# ADR-018: Test Quality Gates and Coverage Strategy

**Status**: Accepted
**Date**: 2026-02-15
**Decision Maker**: Quality Team
**Reviewers**: Development Team, Security Team
**Related ADRs**: 003 (Security Model), 008 (Validation Architecture)

---

## Executive Summary

Established 85% minimum test coverage threshold with specialized test markers (unit, integration, security, slow, mocked) and strict environment isolation. Tests are organized by category with pytest markers, and coverage reports exclude standard boilerplate patterns.

---

## 1. Context and Problem Statement

### 1.1 Background

Test quality for a security-critical symbolic execution server requires:

1. **High coverage**: Most code paths tested
2. **Categorized tests**: Fast unit tests, slower integration tests
3. **Environment isolation**: Tests don't affect each other
4. **Security focus**: Dedicated security test suite

### 1.2 Problem Statement

Test strategy involves trade-offs:

- **Coverage vs. Speed**: Higher coverage = slower test suite
- **Isolation vs. Complexity**: Better isolation = more setup code
- **Categories vs. Simplicity**: More categories = more complex CI

### 1.3 Requirements

- **REQ-1801**: Minimum 85% code coverage enforced
- **REQ-1802**: Test markers for categorization
- **REQ-1803**: Environment isolation between tests
- **REQ-1804**: Security test suite with dedicated marker
- **REQ-1805**: Coverage excludes boilerplate patterns

### 1.4 Constraints

- pytest as testing framework
- pytest-cov for coverage measurement
- CI/CD pipeline time constraints

---

## 2. Decision

**Implement 85% coverage threshold with 5 test markers and environment isolation via conftest.py.**

### 2.1 Technical Specification

```toml
# pyproject.toml - pytest configuration
[tool.pytest.ini_options]
minversion = "7.0"
addopts = [
    "--strict-markers",
    "--strict-config",
    "--verbose",
    "--cov=main",
    "--cov-report=term-missing",
    "--cov-report=html",
    "--cov-report=xml"
]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "integration: marks tests as integration tests using real CrossHair",
    "security: marks tests as security-related tests",
    "unit: marks tests as unit tests",
    "mocked: marks tests using CrossHair mocks instead of real execution"
]
```

### 2.2 Test Markers

| Marker | Purpose | Typical Duration | Example |
|--------|---------|------------------|---------|
| `unit` | Fast, isolated tests | < 100ms | Input validation |
| `integration` | Real CrossHair execution | 1-10s | Symbolic analysis |
| `security` | Security boundary tests | 100ms-1s | Bypass attempts |
| `slow` | Long-running tests | > 10s | Complex analysis |
| `mocked` | Mocked CrossHair | < 100ms | Error handling |

### 2.3 Coverage Configuration

```toml
# pyproject.toml - coverage configuration
[tool.coverage.run]
source = ["main"]
omit = [
    "*/tests/*",
    "*/test_*",
    "setup.py"
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if self.debug:",
    "if settings.DEBUG",
    "raise AssertionError",
    "raise NotImplementedError",
    "if 0:",
    "if __name__ == .__main__.:",
    "class .*\\bProtocol\\):",
    "@(abc\\.)?abstractmethod"
]
show_missing = true
precision = 2
```

### 2.4 Environment Isolation

```python
# tests/conftest.py
def pytest_configure(config: Config) -> None:
    """Clear SYMBOLIC_* environment variables before pytest imports."""
    for key in list(os.environ.keys()):
        if key.startswith("SYMBOLIC_"):
            del os.environ[key]

@pytest.fixture(autouse=True)
def clean_symbolic_env_per_test() -> Generator[None, None, None]:
    """Clear SYMBOLIC_* environment variables before each test."""
    keys_to_clear = [k for k in os.environ if k.startswith("SYMBOLIC_")]
    for key in keys_to_clear:
        del os.environ[key]
    yield
    keys_to_clear = [k for k in os.environ if k.startswith("SYMBOLIC_")]
    for key in keys_to_clear:
        del os.environ[key]
```

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **85% + Markers + Isolation** (selected) | Full strategy | Comprehensive, organized | More setup | 9/10 |
| 90% Coverage Only | Higher threshold | Better coverage | Slow, diminishing returns | 6/10 |
| 70% + Fast CI | Lower threshold | Faster CI | Less confidence | 5/10 |
| No Markers | Simple config | Simpler | No categorization | 4/10 |

### 3.2 Decision Criteria

| Criterion | Weight | 85%+Markers | 90% Only | 70%+Fast | No Markers |
|-----------|--------|-------------|----------|----------|------------|
| Coverage Quality | 30% | 8 | 9 | 5 | 7 |
| CI Speed | 25% | 8 | 5 | 9 | 8 |
| Test Organization | 20% | 9 | 4 | 4 | 2 |
| Isolation Quality | 15% | 9 | 7 | 6 | 5 |
| Maintainability | 10% | 7 | 8 | 7 | 9 |
| **Weighted Score** | **100%** | **8.05** | **6.7** | **5.95** | **5.65** |

### 3.3 Selection Justification

85% + Markers + Isolation achieves the highest score (8.05) due to:

1. **Practical Coverage**: 85% catches most bugs without diminishing returns
2. **Test Categories**: Markers enable selective test runs
3. **Environment Isolation**: conftest.py prevents test pollution
4. **Security Focus**: Dedicated security marker ensures coverage
5. **CI Optimization**: Can skip slow tests for quick feedback

---

## 4. Alternatives Considered

### 4.1 Alternative 1: 90% Coverage Only

**Description**: Higher coverage threshold without markers.

**Advantages**:
- Better coverage
- Simpler configuration

**Disadvantages**:
- **Slower CI**: More tests, longer runs
- **Diminishing returns**: 90%→95% is expensive
- **No categorization**: Can't skip slow tests

**Rejection Rationale**: 85% is sufficient; 90% has diminishing returns.

### 4.2 Alternative 2: 70% Coverage with Fast CI

**Description**: Lower threshold prioritizing CI speed.

**Advantages**:
- Faster CI
- Simpler test maintenance

**Disadvantages**:
- **Lower confidence**: 30% of code untested
- **Security risk**: Critical paths may be missed
- **False security**: Coverage number without quality

**Rejection Rationale**: Unacceptable for security-critical code.

### 4.3 Alternative 3: No Test Markers

**Description**: All tests treated equally without categorization.

**Advantages**:
- Simpler configuration
- No marker maintenance

**Disadvantages**:
- **No selective runs**: Can't skip slow tests
- **Poor organization**: Tests not categorized
- **CI inefficiency**: Always run all tests

**Rejection Rationale**: Markers provide essential CI optimization.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Coverage drops below 85% | Medium | Medium | CI failure on coverage drop | CI |
| Slow test suite | Medium | Low | Use markers to skip slow | Dev Team |
| Test pollution | Low | Medium | conftest.py isolation | QA |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| CI timeout | Low | Medium | Skip slow tests in PR checks | DevOps |

---

## 6. Consequences

### 6.1 Positive Consequences

- **85% Coverage**: High confidence in code quality
- **Test Categories**: Selective test runs via markers
- **Environment Isolation**: No test pollution
- **Security Focus**: Dedicated security tests
- **CI Optimization**: Skip slow tests for quick feedback

### 6.2 Negative Consequences

- **Test Maintenance**: More test infrastructure to maintain
- **Slower CI**: Full test suite takes longer
- **Marker Overhead**: Must apply markers correctly

### 6.3 Trade-offs Accepted

- **85% vs 90%**: Practical coverage over maximum
- **Markers vs Simplicity**: Organization over simplicity

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] Phase 1: pytest configuration in pyproject.toml
- [x] Phase 2: conftest.py environment isolation
- [x] Phase 3: Test markers defined
- [x] Phase 4: Coverage exclusion patterns

### 7.2 Validation Requirements

- [x] Coverage threshold enforced in CI
- [x] All markers registered
- [x] Environment isolation working
- [x] Coverage excludes boilerplate

### 7.3 Rollout Plan

1. **Completed**: Initial test infrastructure
2. **Completed**: Security test suite
3. **Ongoing**: Maintain coverage above 85%

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **pytest >= 7.0**: Test framework
- **pytest-cov >= 4.0**: Coverage measurement
- **pytest-mock >= 3.10**: Mocking support

### 8.2 Documentation Dependencies

- ADR-003: Security Model (security tests)
- ADR-008: Validation Architecture (validation tests)

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | Quality Team | Initial ADR documenting test strategy |

---

## 10. References

1. Project `pyproject.toml`: Lines 195-243 (pytest/coverage config)
2. Project `tests/conftest.py`: Environment isolation
3. pytest documentation: Markers
4. Coverage.py: Configuration

---

## Appendix A: Running Tests by Category

```bash
# Run all tests
pytest

# Run only unit tests (fast)
pytest -m unit

# Run only security tests
pytest -m security

# Skip slow tests
pytest -m "not slow"

# Run integration tests with real CrossHair
pytest -m integration

# Run mocked tests only
pytest -m mocked

# Coverage report
pytest --cov=main --cov-report=html
```

---

## Appendix B: CI Configuration Example

```yaml
# .github/workflows/test.yml
jobs:
  test-fast:
    runs-on: ubuntu-latest
    steps:
      - name: Run fast tests
        run: pytest -m "not slow" --cov=main --cov-fail-under=85

  test-full:
    runs-on: ubuntu-latest
    needs: test-fast
    steps:
      - name: Run all tests
        run: pytest --cov=main --cov-fail-under=85
```

---

## Appendix C: Test File Organization

```
tests/
├── conftest.py              # Shared fixtures, environment isolation
├── test_security.py         # @pytest.mark.security
├── test_validation.py       # @pytest.mark.unit
├── test_symbolic_check.py   # @pytest.mark.integration
├── test_equivalence.py      # @pytest.mark.integration
├── test_branches.py         # @pytest.mark.integration
├── test_resources.py        # @pytest.mark.unit
├── test_error_handling.py   # @pytest.mark.mocked
└── test_slow_analysis.py    # @pytest.mark.slow
```

---

## Appendix D: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-1801: 85% Coverage | Compliant | Enforced in CI |
| REQ-1802: Test Markers | Compliant | 5 markers defined |
| REQ-1803: Environment Isolation | Compliant | conftest.py clears env |
| REQ-1804: Security Marker | Compliant | security marker |
| REQ-1805: Coverage Exclusions | Compliant | Standard patterns excluded |
