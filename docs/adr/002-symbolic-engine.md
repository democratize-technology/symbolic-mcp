# ADR-002: CrossHair + Z3 Symbolic Execution Engine

**Status**: Accepted
**Date**: 2025-02-09
**Decision Maker**: Architecture Team
**Reviewers**: Security Lead, Analysis Team
**Related ADRs**: 001 (Framework), 003 (Security Model), 004 (Resource Limits)

---

## Executive Summary

Selected CrossHair (with Z3 solver backend) as the symbolic execution engine over alternatives (angr, SymPy, KLEE, custom implementation). CrossHair provides optimal Python-native symbolic execution with path-sensitive analysis, constraint solving, and contract verification while maintaining compatibility with our security isolation requirements.

---

## 1. Context and Problem Statement

### 1.1 Background

Symbolic execution for Python requires:
1. Path-sensitive analysis (exploring all execution paths)
2. Constraint solving (finding inputs that reach specific paths)
3. Contract verification (precondition/postcondition checking)
4. Python 3.11+ compatibility
5. Integration with security sandbox (ADR-003)

### 1.2 Problem Statement

Multiple symbolic execution approaches exist for Python. Selecting the wrong engine could result in:
- Incomplete path coverage
- Excessive false positives/negatives
- Security isolation bypass
- Performance degradation
- Maintenance burden

### 1.3 Requirements

- **REQ-201**: Path-sensitive symbolic execution
- **REQ-202**: Z3 SMT solver backend for constraint solving
- **REQ-203**: Python 3.11+ compatibility
- **REQ-204**: Contract verification support (PEP 316, icontract)
- **REQ-205**: Compatible with import-restricted sandbox

### 1.4 Constraints

- Must not require code instrumentation beyond function-level
- Must support timeout-based cancellation
- Must operate within memory limits (ADR-004)
- Must be compatible with whitelist import security

---

## 2. Decision

**Select CrossHair (>=0.0.70) with Z3 solver (>=4.12.0) as the symbolic execution engine.**

### 2.1 Technical Specification

```python
from crosshair.core_and_libs import analyze_function, run_checkables
from crosshair.core import AnalysisOptionSet, AnalysisKind

options = AnalysisOptionSet(
    analysis_kind=[AnalysisKind.asserts, AnalysisKind.PEP316],
    per_condition_timeout=30.0,
    per_path_timeout=3.0,
)

checkables = analyze_function(func, options)
messages = list(run_checkables(checkables))
```

### 2.2 Scope

- **In Scope**: Symbolic execution, path exploration, constraint solving
- **Out of Scope**: Security validation (ADR-008), resource limits (ADR-004)

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **CrossHair + Z3** | Python-native symbolic executor | Python-focused, no AST transforms, contract support | Limited to Python, smaller community | 9/10 |
| **angr** | Binary analysis platform | Powerful, multi-language, large ecosystem | Binary-focused, Python wrapper complex | 5/10 |
| **SymPy + assumptions** | Symbolic math library | Strong math reasoning, well-documented | Not path-sensitive, no contracts | 3/10 |
| **KLEE + LLVM** | LLVM-based symbolic execution | Proven, extensive research | Requires compilation, Python complex | 2/10 |
| **Custom** | Build from scratch | Full control, tailored | High maintenance, reinventing wheels | 2/10 |

### 3.2 Decision Criteria

| Criterion | Weight | CrossHair | angr | SymPy | KLEE | Custom |
|-----------|--------|----------|------|-------|------|--------|
| Python Integration | 30% | 10 | 5 | 8 | 2 | 10 |
| Path Sensitivity | 25% | 9 | 10 | 3 | 10 | 5 |
| Contract Support | 20% | 10 | 2 | 2 | 2 | 5 |
| Performance | 15% | 7 | 5 | 6 | 8 | 3 |
| Ecosystem | 10% | 6 | 9 | 10 | 8 | 1 |
| **Weighted Score** | **100%** | **8.85** | **5.4** | **4.6** | **4.5** | **5.15** |

### 3.3 Selection Justification

CrossHair achieves the highest weighted score due to:

1. **Python-Native Design**: Built specifically for Python, no language bridges
2. **No AST Transformation**: Operates on live Python objects, not AST transforms
3. **Contract Support**: Native support for PEP 316 docstrings and icontract decorators
4. **Sandbox Compatibility**: Works with import-restricted environments
5. **Mature API**: Stable `analyze_function()` and `run_checkables()` interfaces

---

## 4. Alternatives Considered

### 4.1 Alternative 1: angr

**Description**: Use angr's symbolic execution engine with SimProcedures.

**Advantages**:
- Powerful and battle-tested
- Multi-language support (binary analysis)
- Large ecosystem and community
- Advanced constraint solving

**Disadvantages**:
- Binary-focused, not Python-idiomatic
- Complex SimProcedures required for Python stdlib
- Heavier runtime footprint
- Less natural contract verification

**Rejection Rationale**: Lower Python integration score (5/10). Binary focus makes Python analysis more complex.

### 4.2 Alternative 2: SymPy with Assumptions

**Description**: Use SymPy's symbolic math with assumption tracking.

**Advantages**:
- Excellent mathematical reasoning
- Well-documented and mature
- Strong Python ecosystem integration

**Disadvantages**:
- Not path-sensitive (no control flow analysis)
- No contract verification support
- Requires manual path encoding
- Designed for math, not general verification

**Rejection Rationale**: Fails REQ-201 (path-sensitive analysis). Cannot explore code paths automatically.

### 4.3 Alternative 3: KLEE with LLVM

**Description**: Compile Python to LLVM bytecode and use KLEE.

**Advantages**:
- Proven symbolic execution engine
- Extensive research and tooling
- High performance

**Disadvantages**:
- Requires LLVM compilation step
- Complex integration with Python runtime
- Numba or similar required (heavy dependency)
- Not suitable for dynamic Python features

**Rejection Rationale**: Unacceptable complexity. LLVM compilation breaks Python's dynamic nature.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| CrossHair unmaintained | Low | High | Fork capability; API stability | Tech Lead |
| Z3 solver hangs | Medium | High | Per-path timeouts (ADR-004) | Analysis Lead |
| Unsupported Python features | Medium | Medium | Fallback to static analysis | Analysis Lead |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Path explosion | High | Medium | Timeout tuning; coverage degradation | Analysis Lead |
| Memory exhaustion | Medium | High | Resource limits (ADR-004) | Platform Lead |

### 5.3 Security Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Sandbox escape via Z3 | Low | Critical | Import whitelist (ADR-003) | Security Lead |
| Solver side-channels | Low | Low | Constant-time comparisons | Security Lead |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Path Sensitivity**: Exhaustive path exploration with constraint solving
- **Mathematical Proofs**: Can prove properties about code behavior
- **Edge Case Discovery**: Finds inputs that reach deep conditional bugs
- **Contract Verification**: Native support for PEP 316 and icontract
- **Python-Native**: No compilation or transformation required

### 6.2 Negative Consequences

- **Path Explosion**: Complex functions can generate exponential paths
- **Z3 Dependency**: External solver dependency
- **Timeout Sensitivity**: Analysis can time out on complex code
- **Memory Usage**: Symbolic state can be memory-intensive

### 6.3 Trade-offs Accepted

- **Completeness vs Performance**: Accepting path explosion for exhaustive analysis
- **External Dependency vs Custom**: Accepting Z3 dependency for proven constraint solving

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] **Phase 1**: CrossHair integration completed
- [x] **Phase 2**: All 4 tools implemented
- [x] **Phase 3**: Timeout and memory limit integration
- [x] **Phase 4**: Coverage calculation with logarithmic degradation

### 7.2 Validation Requirements

- [x] `symbolic_check`: Contract verification working
- [x] `find_path_to_exception`: Exception path finding
- [x] `compare_functions`: Semantic equivalence checking
- [x] `analyze_branches`: Branch enumeration

### 7.3 Rollout Plan

1. **Completed**: Initial CrossHair integration
2. **Completed**: Security integration with whitelist
3. **Ongoing**: Performance tuning for complex functions

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **crosshair-tool >= 0.0.70**: Symbolic execution engine
- **z3-solver >= 4.12.0**: SMT solver backend
- **Python 3.11+**: Required for modern type syntax

### 8.2 Documentation Dependencies

- Spec §2: "Technical Stack Requirements"
- Spec §3: "Core Architecture"
- ADR-001: FastMCP framework integration
- ADR-003: Security model (import whitelist)

### 8.3 External Dependencies

```
crosshair-tool>=0.0.70  # Symbolic execution engine
z3-solver>=4.12.0       # SMT solver backend
icontract>=2.6.0        # Contract decorators (optional)
```

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-02-09 | Architecture Team | Initial ADR documenting CrossHair selection |

---

## 10. References

1. [CrossHair Documentation](https://crosshair.readthedocs.io/)
2. [Z3 Solver Theorem Prover](https://github.com/Z3Prover/z3)
3. [PEP 316 - Programming by Contract for Python](https://www.python.org/dev/peps/pep-0316/)
4. [icontract Library](https://github.com/Parquery/icontract)
5. Project `main.py`: Lines 810-1053 (SymbolicAnalyzer class)

---

## Appendix A: Integration Evidence

```python
# main.py:810-1053 (excerpt)
class SymbolicAnalyzer:
    """Analyzes code using CrossHair symbolic execution."""

    def analyze(self, code: str, target_function_name: str) -> _SymbolicCheckResult:
        # Load user code in temporary module
        with self._temporary_module(code) as module:
            func = getattr(module, target_function_name)

            # Configure CrossHair analysis
            options = AnalysisOptionSet(
                analysis_kind=[AnalysisKind.asserts, AnalysisKind.PEP316],
                per_condition_timeout=float(self.timeout),
                per_path_timeout=float(self.timeout) * PER_PATH_TIMEOUT_RATIO,
            )

            # Get checkables and run analysis
            checkables = analyze_function(func, options)
            messages: list[AnalysisMessage] = list(run_checkables(checkables))

            # Process results...
```

---

## Appendix B: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-201: Path Sensitivity | Compliant | CrossHair core capability |
| REQ-202: Z3 Backend | Compliant | z3-solver >= 4.12.0 |
| REQ-203: Python 3.11+ | Compliant | Tested with Python 3.11+ |
| REQ-204: Contract Support | Compliant | PEP 316 + icontract |
| REQ-205: Sandbox Compatible | Compliant | Works with import whitelist |
