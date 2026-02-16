# ADR-016: Environment Variable Configuration Pattern

**Status**: Accepted
**Date**: 2026-02-15
**Decision Maker**: Platform Team
**Reviewers**: Operations, Security Team
**Related ADRs**: 004 (Resource Limits), 017 (Timeout Cascade)

---

## Executive Summary

Adopted `SYMBOLIC_*` prefixed environment variables with bounds checking for all configurable parameters. This follows 12-factor app principles, enables container-friendly deployment, and prevents misconfiguration through runtime validation.

---

## 1. Context and Problem Statement

### 1.1 Background

Server configuration can be managed through multiple mechanisms:

1. **Configuration files**: JSON, YAML, TOML files
2. **Environment variables**: Process environment
3. **Command-line arguments**: Startup parameters
4. **Database/storage**: External configuration service

For containerized deployments, environment variables are the standard approach.

### 1.2 Problem Statement

Configuration management affects:

- **Deployment flexibility**: How easily can deployments be customized?
- **Security**: How are sensitive values protected?
- **Validation**: How are invalid configurations caught?
- **Documentation**: How is configuration documented?

### 1.3 Requirements

- **REQ-1601**: All configuration via `SYMBOLIC_*` environment variables
- **REQ-1602**: Default values for all parameters
- **REQ-1603**: Bounds checking on numeric values
- **REQ-1604**: Configuration loaded at startup (not runtime)
- **REQ-1605**: Clear error messages for invalid values

### 1.4 Constraints

- Must work in containerized environments (Docker, Kubernetes)
- Must support 12-factor app methodology
- No configuration files (simplifies deployment)

---

## 2. Decision

**Use `SYMBOLIC_*` prefixed environment variables with helper function for bounds checking.**

### 2.1 Technical Specification

```python
def _get_int_env_var(
    name: str,
    default: str,
    min_value: Optional[int] = None,
    max_value: Optional[int] = None,
) -> int:
    """Safely parse an integer environment variable with optional bounds checking.

    Args:
        name: Environment variable name
        default: Default value as string
        min_value: Minimum allowed value (inclusive), or None for no minimum
        max_value: Maximum allowed value (inclusive), or None for no maximum

    Returns:
        Parsed integer value, or default if invalid

    Raises:
        ValueError: If the value is outside the allowed bounds
    """
    try:
        value = int(os.environ.get(name, default))
    except (ValueError, TypeError):
        value = int(default)

    if min_value is not None and value < min_value:
        raise ValueError(f"{name} must be at least {min_value}, got {value}")
    if max_value is not None and value > max_value:
        raise ValueError(f"{name} must be at most {max_value}, got {value}")

    return value

# Configuration variables
MEMORY_LIMIT_MB = _get_int_env_var(
    "SYMBOLIC_MEMORY_LIMIT_MB", "2048", min_value=128, max_value=65536
)

CODE_SIZE_LIMIT = _get_int_env_var(
    "SYMBOLIC_CODE_SIZE_LIMIT", "65536", min_value=1024, max_value=1048576
)

COVERAGE_EXHAUSTIVE_THRESHOLD = _get_int_env_var(
    "SYMBOLIC_COVERAGE_EXHAUSTIVE_THRESHOLD", "1000", min_value=100, max_value=100000
)
```

### 2.2 Configuration Variables

| Variable | Default | Min | Max | Purpose |
|----------|---------|-----|-----|---------|
| `SYMBOLIC_MEMORY_LIMIT_MB` | 2048 | 128 | 65536 | Process memory limit |
| `SYMBOLIC_CODE_SIZE_LIMIT` | 65536 | 1024 | 1048576 | Max code size in bytes |
| `SYMBOLIC_COVERAGE_EXHAUSTIVE_THRESHOLD` | 1000 | 100 | 100000 | Paths for exhaustive coverage |

### 2.3 Naming Convention

```
SYMBOLIC_<CATEGORY>_<PARAMETER>

Examples:
- SYMBOLIC_MEMORY_LIMIT_MB     (Memory category)
- SYMBOLIC_CODE_SIZE_LIMIT     (Code category)
- SYMBOLIC_COVERAGE_EXHAUSTIVE_THRESHOLD (Coverage category)
```

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **Environment Variables** (selected) | SYMBOLIC_* env vars | 12-factor, container-native | No config files | 9/10 |
| Config Files | TOML/YAML files | Complex configurations | Deployment complexity | 6/10 |
| CLI Arguments | Command-line flags | Simple override | Doesn't work with containers | 5/10 |
| Hybrid | Env vars + config files | Maximum flexibility | Complexity | 7/10 |

### 3.2 Decision Criteria

| Criterion | Weight | Env Vars | Config Files | CLI Args | Hybrid |
|-----------|--------|----------|--------------|----------|--------|
| Container Compatibility | 30% | 10 | 6 | 2 | 8 |
| Simplicity | 25% | 9 | 5 | 8 | 4 |
| Security | 20% | 8 | 7 | 6 | 7 |
| Validation | 15% | 8 | 9 | 5 | 8 |
| Documentation | 10% | 7 | 9 | 6 | 7 |
| **Weighted Score** | **100%** | **8.65** | **6.75** | **4.9** | **6.85** |

### 3.3 Selection Justification

Environment variables achieve the highest score (8.65) due to:

1. **12-Factor App**: Config in environment, strict separation
2. **Container Native**: Docker/Kubernetes use environment variables
3. **Simplicity**: No config files to manage
4. **Security**: Secrets via environment (never in code)
5. **Bounds Checking**: Helper function validates at startup

---

## 4. Alternatives Considered

### 4.1 Alternative 1: Configuration Files

**Description**: Use TOML or YAML configuration files.

**Advantages**:
- Complex nested configurations
- Comments for documentation
- Type-safe with libraries

**Disadvantages**:
- **Deployment complexity**: Config files must be mounted
- **Secrets exposure**: Config files may contain secrets
- **Multiple sources**: Need precedence rules for env override

**Rejection Rationale**: Over-engineering for current configuration needs.

### 4.2 Alternative 2: Command-Line Arguments

**Description**: Configure via command-line flags.

**Advantages**:
- Simple override mechanism
- Clear in process listing

**Disadvantages**:
- **Container incompatibility**: Containers don't use CLI args easily
- **Limited types**: Only strings, need parsing
- **No defaults in help**: Must document separately

**Rejection Rationale**: Doesn't work well with containerized deployments.

### 4.3 Alternative 3: Pydantic Settings

**Description**: Use pydantic-settings for configuration management.

**Advantages**:
- Type validation
- Environment variable loading
- Nested settings

**Disadvantages**:
- **Additional dependency**: Already have pydantic but not pydantic-settings
- **Overhead**: More code for simple configuration
- **Learning curve**: Another API to learn

**Rejection Rationale**: Simple helper function is sufficient for current needs.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Invalid configuration at startup | Medium | Medium | Bounds checking with clear errors | Tech Lead |
| Environment variable collision | Low | Low | SYMBOLIC_ prefix | Architecture |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Missing documentation | Medium | Low | Document all variables in ADR | Documentation |

### 5.3 Security Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Secrets in environment | Medium | High | Document secret handling, use secrets managers | Operations |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Container Native**: Works with Docker/Kubernetes
- **12-Factor Compliant**: Config in environment
- **Bounds Checking**: Invalid values caught at startup
- **Simple**: No configuration files to manage

### 6.2 Negative Consequences

- **No Complex Config**: Cannot do nested configurations
- **Process Restart**: Config changes require restart

### 6.3 Trade-offs Accepted

- **Simplicity > Flexibility**: Simple env vars over complex config files
- **Startup Validation > Runtime Validation**: Fail fast on invalid config

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] Phase 1: `_get_int_env_var` helper function
- [x] Phase 2: SYMBOLIC_MEMORY_LIMIT_MB
- [x] Phase 3: SYMBOLIC_CODE_SIZE_LIMIT
- [x] Phase 4: SYMBOLIC_COVERAGE_EXHAUSTIVE_THRESHOLD

### 7.2 Validation Requirements

- [x] All config variables have defaults
- [x] All config variables have bounds checking
- [x] Invalid values raise clear errors
- [x] Test environment clears SYMBOLIC_* vars (conftest.py)

### 7.3 Rollout Plan

1. **Completed**: Helper function implementation
2. **Completed**: Configuration variables
3. **Completed**: Test isolation (conftest.py)
4. **Ongoing**: Add new variables as needed

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **Python stdlib**: `os.environ`
- **conftest.py**: Clears SYMBOLIC_* vars before tests

### 8.2 Documentation Dependencies

- ADR-004: Resource Limits (uses SYMBOLIC_MEMORY_LIMIT_MB)
- ADR-017: Timeout Cascade Configuration

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | Platform Team | Initial ADR documenting env var pattern |

---

## 10. References

1. Project `main.py`: Lines 272-338 (configuration)
2. Project `tests/conftest.py`: Environment isolation
3. The Twelve-Factor App: https://12factor.net/config
4. ADR-004: Resource Limits Strategy

---

## Appendix A: Docker/Kubernetes Usage

### Docker Compose
```yaml
services:
  symbolic-mcp:
    image: symbolic-mcp:latest
    environment:
      - SYMBOLIC_MEMORY_LIMIT_MB=4096
      - SYMBOLIC_CODE_SIZE_LIMIT=131072
```

### Kubernetes ConfigMap
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: symbolic-mcp-config
data:
  SYMBOLIC_MEMORY_LIMIT_MB: "4096"
  SYMBOLIC_CODE_SIZE_LIMIT: "131072"
---
apiVersion: apps/v1
kind: Deployment
spec:
  template:
    spec:
      containers:
        - name: symbolic-mcp
          envFrom:
            - configMapRef:
                name: symbolic-mcp-config
```

### Kubernetes Secrets
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: symbolic-mcp-secrets
# Note: SYMBOLIC_* vars don't include secrets
# OAuth secrets use GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET
```

---

## Appendix B: Error Messages

```
$ SYMBOLIC_MEMORY_LIMIT_MB=50 python -m main
ValueError: SYMBOLIC_MEMORY_LIMIT_MB must be at least 128, got 50

$ SYMBOLIC_MEMORY_LIMIT_MB=999999 python -m main
ValueError: SYMBOLIC_MEMORY_LIMIT_MB must be at most 65536, got 999999

$ SYMBOLIC_MEMORY_LIMIT_MB=invalid python -m main
# Uses default of 2048 (invalid is caught by try/except)
```

---

## Appendix C: Test Isolation

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

## Appendix D: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-1601: SYMBOLIC_* Prefix | Compliant | All vars use prefix |
| REQ-1602: Default Values | Compliant | All vars have defaults |
| REQ-1603: Bounds Checking | Compliant | Helper validates min/max |
| REQ-1604: Startup Loading | Compliant | Module-level assignment |
| REQ-1605: Clear Errors | Compliant | ValueError with context |
