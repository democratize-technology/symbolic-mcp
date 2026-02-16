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
├── 011-authentication-authorization.md # OAuth 2.1 authentication
├── 012-single-file-architecture.md # Single-file monolith architecture
├── 013-mcp-tool-surface-design.md # MCP tool API design
├── 014-stateless-request-model.md # Stateless request processing
├── 015-typeddict-return-types.md # TypedDict response strategy
├── 016-environment-variable-configuration.md # Environment variable pattern
├── 017-timeout-cascade-configuration.md # Timeout cascade strategy
├── 018-test-quality-gates.md    # Test coverage and quality gates
├── 019-python-version-compatibility.md # Python version support
├── 020-mcp-resource-endpoints.md # MCP resource endpoint strategy
├── 021-prompt-template-design.md # Prompt template design
├── 022-dangerous-builtins-policy.md # Dangerous builtins blocking
├── 023-defense-in-depth-security.md # Defense-in-depth architecture
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

### Framework & Engine (001-002)

| ADR | Topic | Status | Date |
|-----|-------|--------|------|
| 001 | FastMCP 2.0 Framework | Accepted | 2025-02-09 |
| 002 | CrossHair + Z3 Solver | Accepted | 2025-02-09 |

### Security (003-008, 011, 022-023)

| ADR | Topic | Status | Date |
|-----|-------|--------|------|
| 003 | Whitelist Security Model | Accepted | 2025-02-09 |
| 004 | Resource Limits Strategy | Accepted | 2025-02-09 |
| 005 | Temporary Module Isolation | Accepted | 2025-02-09 |
| 008 | AST-Based Security Validation | Accepted | 2025-02-09 |
| 011 | Authentication & Authorization | Accepted | 2025-02-13 |
| 022 | Dangerous Builtins Policy | Accepted | 2026-02-15 |
| 023 | Defense-in-Depth Security | Accepted | 2026-02-15 |

### Concurrency & Performance (006-007)

| ADR | Topic | Status | Date |
|-----|-------|--------|------|
| 006 | Thread Safety Architecture | Accepted | 2025-02-09 |
| 007 | Coverage Calculation Method | Accepted | 2025-02-09 |

### API Design (009-010, 013, 015, 020-021)

| ADR | Topic | Status | Date |
|-----|-------|--------|------|
| 009 | Error Handling Philosophy | Accepted | 2026-02-09 |
| 010 | Contract Style Support | Accepted | 2026-02-09 |
| 013 | MCP Tool Surface Design | Accepted | 2026-02-15 |
| 015 | TypedDict Return Types | Accepted | 2026-02-15 |
| 020 | MCP Resource Endpoints | Accepted | 2026-02-15 |
| 021 | Prompt Template Design | Accepted | 2026-02-15 |

### Architecture (012, 014)

| ADR | Topic | Status | Date |
|-----|-------|--------|------|
| 012 | Single-File Architecture | Accepted | 2026-02-15 |
| 014 | Stateless Request Model | Accepted | 2026-02-15 |

### Operations (016-019)

| ADR | Topic | Status | Date |
|-----|-------|--------|------|
| 016 | Environment Variable Configuration | Accepted | 2026-02-15 |
| 017 | Timeout Cascade Configuration | Accepted | 2026-02-15 |
| 018 | Test Quality Gates | Accepted | 2026-02-15 |
| 019 | Python Version Compatibility | Accepted | 2026-02-15 |

## ADR Index by Number

| ADR | Title | Category | Date |
|-----|-------|----------|------|
| 001 | FastMCP 2.0 Framework Selection | Framework | 2025-02-09 |
| 002 | CrossHair + Z3 Symbolic Execution Engine | Engine | 2025-02-09 |
| 003 | Whitelist-Based Import Security Model | Security | 2025-02-09 |
| 004 | Resource Limits Strategy | Security | 2025-02-09 |
| 005 | Temporary Module Isolation Strategy | Security | 2025-02-09 |
| 006 | Thread Safety Architecture | Concurrency | 2025-02-09 |
| 007 | Coverage Calculation with Logarithmic Degradation | Algorithm | 2025-02-09 |
| 008 | AST-Based Security Validation Architecture | Security | 2025-02-09 |
| 009 | Error Handling Philosophy | API Design | 2026-02-09 |
| 010 | Contract Style Support | Features | 2026-02-09 |
| 011 | Authentication & Authorization (OAuth 2.1) | Security | 2025-02-13 |
| 012 | Single-File Monolith Architecture | Architecture | 2026-02-15 |
| 013 | MCP Tool Surface Design | API Design | 2026-02-15 |
| 014 | Stateless Request Processing Model | Architecture | 2026-02-15 |
| 015 | TypedDict for Structured Responses | API Design | 2026-02-15 |
| 016 | Environment Variable Configuration Pattern | Operations | 2026-02-15 |
| 017 | Timeout Cascade Configuration | Operations | 2026-02-15 |
| 018 | Test Quality Gates and Coverage Strategy | Operations | 2026-02-15 |
| 019 | Python Version Compatibility Matrix | Operations | 2026-02-15 |
| 020 | MCP Resource Endpoint Strategy | API Design | 2026-02-15 |
| 021 | Prompt Template Design for AI Workflows | API Design | 2026-02-15 |
| 022 | Dangerous Builtins Restriction Policy | Security | 2026-02-15 |
| 023 | Defense-in-Depth Security Architecture | Security | 2026-02-15 |

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-02-09 | Initial ADR system establishment | System |
| 1.1 | 2026-02-09 | Added ADR-009, ADR-010 (Error Handling, Contract Styles) | System |
| 1.2 | 2025-02-13 | Added ADR-011 (Authentication & Authorization) | System |
| 1.3 | 2026-02-15 | Added ADR-012 through ADR-023 (Gap Analysis Remediation) | System |
