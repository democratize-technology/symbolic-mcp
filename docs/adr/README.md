# Architecture Decision Records (ADRs)

**Documentation Standard**: NASA-style Engineering Documentation
**Version Control**: Git-tracked, immutable after approval
**Review Process**: Technical review required for status changes

## Directory Structure

```
docs/adr/
├── README.md                    # This file
├── 000-template.md              # ADR template (use this for new ADRs)
├── 001-framework-selection.md   # FastMCP 2.0 framework decision
├── 002-symbolic-engine.md       # CrossHair + Z3 solver selection
├── 003-security-model.md        # Whitelist-based import control
├── 004-resource-limits.md       # Memory and timeout strategies
├── 005-isolation-strategy.md    # Temporary module isolation
├── 006-thread-safety.md         # Concurrency control approach
├── 007-coverage-calculation.md  # Path explosion handling
├── 008-validation-architecture.md # AST-based security validation
├── 009-error-handling.md        # Structured error response pattern
├── 010-contract-styles.md       # Contract verification style support
└── accepted/                    # Historical/superseded ADRs
```

## ADR Lifecycle

| Status | Description | Required Actions |
|--------|-------------|------------------|
| **Proposed** | Draft under review | Technical review, risk assessment |
| **Accepted** | Approved and implemented | Implementation complete, tested |
| **Deprecated** | Superseded but in use | Migration path defined |
| **Superseded** | Replaced by new ADR | Reference new ADR, archive old |
| **Rejected** | Not pursued | Rationale documented |

## ADR Format Requirements

Each ADR MUST contain:

1. **Metadata Section**
   - Unique ID (sequential, zero-padded)
   - Title (descriptive, technology-neutral)
   - Status (Proposed/Accepted/Deprecated/Superseded/Rejected)
   - Date (YYYY-MM-DD)
   - Author/Decision Maker
   - Related ADRs (dependencies)

2. **Decision Section**
   - Context (problem statement)
   - Decision (concise statement)
   - Rationale (justification with trade-offs)
   - Alternatives Considered (with analysis)
   - Consequences (positive/negative)
   - Risk Assessment (NASA-style: Severity/Probability)
   - Implementation Status
   - References

## NASA Documentation Principles Applied

1. **Traceability**: Every decision references requirements and constraints
2. **Reproducibility**: Sufficient detail for future engineers to understand context
3. **Risk-Based**: Explicit risk assessment with mitigation strategies
4. **Alternatives Analysis**: Multiple options evaluated with selection criteria
5. **Iterative Review**: Decisions revisited as new information emerges

## Quick Reference

| ADR | Topic | Status | Date |
|-----|-------|--------|------|
| 001 | FastMCP 2.0 Framework | Accepted | 2025-02-09 |
| 002 | CrossHair + Z3 Solver | Accepted | 2025-02-09 |
| 003 | Whitelist Security Model | Accepted | 2025-02-09 |
| 004 | Resource Limits Strategy | Accepted | 2025-02-09 |
| 005 | Temporary Module Isolation | Accepted | 2025-02-09 |
| 006 | Thread Safety Architecture | Accepted | 2025-02-09 |
| 007 | Coverage Calculation Method | Accepted | 2025-02-09 |
| 008 | AST-Based Security Validation | Accepted | 2025-02-09 |
| 009 | Error Handling Philosophy | Accepted | 2026-02-09 |
| 010 | Contract Style Support | Accepted | 2026-02-09 |

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-02-09 | Initial ADR system establishment | System |
| 1.1 | 2026-02-09 | Added ADR-009, ADR-010 (Error Handling, Contract Styles) | System |
