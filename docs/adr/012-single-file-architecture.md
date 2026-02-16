# ADR-012: Single-File Monolith Architecture

**Status**: Accepted
**Date**: 2026-02-15
**Decision Maker**: Architecture Team
**Reviewers**: Security Team, Operations
**Related ADRs**: 001 (Framework), 003 (Security Model), 008 (Validation)

---

## Executive Summary

Adopted a single-file architecture where the entire server implementation resides in one `main.py` file (~1,889 lines). This unconventional approach prioritizes security auditability and deployment simplicity over traditional modularity. The entire attack surface is visible in one file, enabling comprehensive security review.

---

## 1. Context and Problem Statement

### 1.1 Background

The Symbolic Execution MCP server executes arbitrary user code, making security the paramount concern. Traditional multi-file project structures, while improving code organization, create several challenges for security-critical applications:

1. **Audit complexity**: Security reviewers must trace code paths across many files
2. **Dependency hiding**: Imports between modules obscure the complete dependency graph
3. **Deployment overhead**: More files increase deployment surface and potential points of failure

### 1.2 Problem Statement

Selecting an architecture for a security-critical MCP server involves trade-offs between:

- **Security auditability**: How easily can the entire codebase be reviewed?
- **Maintainability**: How easy is it to modify and extend the code?
- **Deployment simplicity**: How complex is the deployment process?

### 1.3 Requirements

- **REQ-1201**: Complete security audit must be possible in a single review session
- **REQ-1202**: All security-critical code paths must be traceable without IDE navigation
- **REQ-1203**: Deployment must require minimal file operations
- **REQ-1204**: Import graph must be immediately visible

### 1.4 Constraints

- FastMCP framework expects entry point in single location
- Tool and resource handlers must be in same module as FastMCP instance
- Type definitions must be accessible to all handlers

---

## 2. Decision

**Implement the entire server in a single `main.py` file with clear section boundaries.**

### 2.1 Technical Specification

```
main.py (~1,889 lines)
├── Module Header (lines 1-46)
│   └── Imports, version, logging, constants
├── Type Definitions (lines 53-188)
│   └── TypedDict classes for all responses
├── Security Configuration (lines 190-266)
│   └── ALLOWED_MODULES, BLOCKED_MODULES, DANGEROUS_BUILTINS
├── Environment Configuration (lines 269-338)
│   └── SYMBOLIC_* environment variable parsing
├── Memory Management (lines 340-363)
│   └── Memory limits, module lock
├── Regex Patterns (lines 366-467)
│   └── Pre-compiled patterns for parsing
├── Input Validation (lines 470-789)
│   └── _DangerousCallVisitor, validate_code()
├── Symbolic Analyzer (lines 791-1098)
│   └── _temporary_module, SymbolicAnalyzer class
├── Tool Logic Functions (lines 1100-1505)
│   └── logic_symbolic_check, logic_find_path_to_exception, etc.
├── FastMCP Server (lines 1507-1782)
│   └── Tool handlers, resource handlers, prompt templates
└── Entry Point (lines 1888-1889)
    └── if __name__ == "__main__"
```

### 2.2 Scope

- **In Scope**: All server implementation code
- **Out of Scope**: Test files, documentation, configuration files (pyproject.toml)

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **Single File** | All code in main.py | Security auditability, deployment simplicity | Less code organization | 8/10 |
| **Multi-Module** | Separate modules by concern | Better code organization, standard practice | Audit complexity, import graph hiding | 6/10 |
| **Package Structure** | Full package with submodules | Maximum modularity | Maximum complexity, hidden dependencies | 4/10 |

### 3.2 Decision Criteria

| Criterion | Weight | Single File | Multi-Module | Package |
|-----------|--------|-------------|--------------|---------|
| Security Auditability | 35% | 10 | 5 | 3 |
| Deployment Simplicity | 25% | 10 | 7 | 5 |
| Maintainability | 20% | 5 | 8 | 9 |
| Import Visibility | 20% | 10 | 6 | 3 |
| **Weighted Score** | **100%** | **8.7** | **6.3** | **4.6** |

### 3.3 Selection Justification

Single-file architecture achieves the highest score (8.7) due to:

1. **Complete Visibility**: All 1,889 lines visible in one file
2. **Linear Reading**: Security auditors can read top-to-bottom without file switching
3. **Import Clarity**: All imports at top of file, complete dependency graph visible
4. **Deployment Simplicity**: Single `py-modules = ["main"]` in pyproject.toml
5. **No Hidden Paths**: No `__init__.py` re-exports or relative imports to obscure code flow

---

## 4. Alternatives Considered

### 4.1 Alternative 1: Multi-Module Structure

**Description**: Split code into `security/`, `analysis/`, `types/`, `server/` modules.

**Advantages**:
- Industry-standard organization
- Better IDE support for navigation
- Clearer separation of concerns

**Disadvantages**:
- **Audit complexity**: Security reviewer must trace paths across files
- **Hidden imports**: `from .security import *` obscures dependencies
- **Deployment overhead**: More files to manage in deployment

**Rejection Rationale**: Security auditability is more critical than code organization for this project.

### 4.2 Alternative 2: Full Package Structure

**Description**: Create `symbolic_mcp/` package with `__init__.py`, submodules, and proper package structure.

**Advantages**:
- Maximum modularity
- Publishable to PyPI as installable package
- Supports plugins and extensions

**Disadvantages**:
- **Maximum complexity**: Many files, many import paths
- **Hidden dependencies**: Re-exports in `__init__.py` obscure actual imports
- **Over-engineering**: Current scope doesn't require package structure

**Rejection Rationale**: Over-engineering for current requirements. Can migrate later if needed.

### 4.3 Alternative 3: Hybrid Approach

**Description**: Keep core in main.py, extract types to separate module.

**Advantages**:
- Balances auditability and organization
- Types can be imported by tests cleanly

**Disadvantages**:
- **Partial complexity**: Still some file switching required
- **Inconsistent**: Some code in main.py, some in modules

**Rejection Rationale**: Doesn't achieve full auditability benefit of single-file approach.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| File becomes unmaintainably large | Low | Medium | Use section comments, consider split at 3,000 lines | Tech Lead |
| Merge conflicts in team development | Medium | Low | Clear section boundaries, review before merge | Dev Team |
| IDE performance on large file | Low | Low | Modern IDEs handle 2,000+ lines well | Dev Team |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Longer code reviews | Medium | Low | Use line-based comments, focused reviews | Reviewers |
| Harder to find specific code | Low | Low | Use section headers, grep works well | Dev Team |

### 5.3 Security Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| None (improves security auditability) | N/A | N/A | N/A | N/A |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Security Auditability**: Complete codebase visible in single review
- **Deployment Simplicity**: Single file deployment
- **Import Transparency**: All dependencies visible at file header
- **No Circular Imports**: Single-file structure prevents circular dependencies

### 6.2 Negative Consequences

- **Code Organization**: Less natural separation of concerns
- **Navigation**: No file-based code navigation
- **Team Conflicts**: More potential for merge conflicts

### 6.3 Trade-offs Accepted

- **Security > Organization**: Prioritizing auditability over traditional modularity
- **Simplicity > Scalability**: Single file works well up to ~3,000 lines

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] Phase 1: All code consolidated in main.py
- [x] Phase 2: Section headers added for navigation
- [x] Phase 3: pyproject.toml configured for single module

### 7.2 Validation Requirements

- [x] All functionality in single file
- [x] Clear section boundaries with comments
- [x] All imports at file header
- [x] No relative imports or re-exports

### 7.3 Rollout Plan

1. **Completed**: Initial single-file implementation
2. **Completed**: Section header organization
3. **Ongoing**: Monitor file size, consider split if approaching 3,000 lines

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **FastMCP**: Requires entry point in single location
- **pyproject.toml**: `py-modules = ["main"]` configuration

### 8.2 Documentation Dependencies

- ADR-003: Security Model (validation code in same file)
- ADR-008: Validation Architecture (AST visitor in same file)

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | Architecture Team | Initial ADR documenting single-file architecture |

---

## 10. References

1. Project `main.py`: Complete implementation
2. Project `pyproject.toml`: Line 145 (`py-modules = ["main"]`)
3. The Pragmatic Programmer: "Good enough software" philosophy

---

## Appendix A: Section Header Pattern

```python
# --- Constants ---

# --- Type Definitions ---

# --- Security: Import Whitelist ---

# --- Configuration ---

# --- Memory Management ---

# --- Pre-compiled Regex Patterns ---

# --- Input Validation ---

# --- Symbolic Analyzer ---

# --- Tool Logic Functions (exposed for testing) ---

# --- FastMCP Server ---

# --- Entry Point ---
```

This pattern enables rapid navigation via Ctrl+F for section names.

---

## Appendix B: Size Thresholds

| Lines | Status | Action |
|-------|--------|--------|
| < 2,000 | Optimal | No action needed |
| 2,000 - 2,500 | Acceptable | Monitor growth |
| 2,500 - 3,000 | Warning | Consider split |
| > 3,000 | Critical | Split into modules |

---

## Appendix C: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-1201: Security Audit | Compliant | Single file reviewable |
| REQ-1202: Traceable Paths | Compliant | No file switching needed |
| REQ-1203: Deployment Simplicity | Compliant | Single py-module |
| REQ-1204: Import Visibility | Compliant | All imports at header |
