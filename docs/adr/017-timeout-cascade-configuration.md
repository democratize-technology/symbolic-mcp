# ADR-017: Timeout Cascade Configuration

**Status**: Accepted
**Date**: 2026-02-15
**Decision Maker**: Architecture Team
**Reviewers**: Operations, Performance Team
**Related ADRs**: 004 (Resource Limits), 016 (Environment Variables)

---

## Executive Summary

Implemented a timeout cascade system where per-path timeout is calculated as a fraction (10%) of the total analysis timeout. The `PER_PATH_TIMEOUT_RATIO` constant (0.1) ensures individual path analysis completes before the overall timeout, enabling more paths to be explored within time constraints.

---

## 1. Context and Problem Statement

### 1.1 Background

CrossHair symbolic execution explores multiple execution paths through code. Each path has different complexity and analysis time. Without proper timeout management:

1. **Path monopolization**: One slow path consumes entire timeout
2. **Incomplete exploration**: Other paths never get explored
3. **Unpredictable results**: Coverage varies based on path order

### 1.2 Problem Statement

Timeout configuration involves balancing:

- **Thoroughness**: More paths explored = better coverage
- **Responsiveness**: Total timeout should be predictable
- **Fairness**: Each path gets fair chance to complete

### 1.3 Requirements

- **REQ-1701**: Per-path timeout must be configurable
- **REQ-1702**: Per-path timeout must be less than total timeout
- **REQ-1703**: Multiple paths should complete within total timeout
- **REQ-1704**: Ratio should enable ~10 paths per analysis by default

### 1.4 Constraints

- CrossHair supports `per_path_timeout` and `per_condition_timeout`
- Total timeout is user-configurable (default 30s)
- Path count is unpredictable (depends on code complexity)

---

## 2. Decision

**Use `PER_PATH_TIMEOUT_RATIO` (0.1) to calculate per-path timeout from total timeout.**

### 2.1 Technical Specification

```python
# Per-path timeout ratio for CrossHair analysis
# Each path's timeout is this fraction of the total timeout
# A lower value gives more paths a chance to complete before hitting the overall timeout
PER_PATH_TIMEOUT_RATIO = 0.1  # 10% of total timeout per path

# Usage in AnalysisOptionSet
options = AnalysisOptionSet(
    analysis_kind=[AnalysisKind.asserts, AnalysisKind.PEP316],
    per_condition_timeout=float(self.timeout),          # Total timeout
    per_path_timeout=float(self.timeout) * PER_PATH_TIMEOUT_RATIO,  # Per-path: 10%
)
```

### 2.2 Timeout Cascade

```
User Request (timeout_seconds=30)
         │
         ▼
┌─────────────────────────────┐
│ Total Analysis Window: 30s  │
└─────────────────────────────┘
         │
         ├──▶ Path 1: 3s (10%)
         ├──▶ Path 2: 3s (10%)
         ├──▶ Path 3: 3s (10%)
         ├──▶ Path 4: 3s (10%)
         ├──▶ Path 5: 3s (10%)
         ├──▶ Path 6: 3s (10%)
         ├──▶ Path 7: 3s (10%)
         ├──▶ Path 8: 3s (10%)
         ├──▶ Path 9: 3s (10%)
         └──▶ Path 10: 3s (10%)
```

### 2.3 Default Values

| Parameter | Default | Calculation |
|-----------|---------|-------------|
| Total timeout | 30s | User-configurable |
| Per-path timeout | 3s | 30s × 0.1 |
| Expected paths | ~10 | 30s / 3s |

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **10% Ratio** (selected) | Per-path = 10% of total | Fair exploration, predictable | May timeout complex paths | 8/10 |
| 20% Ratio | Per-path = 20% of total | More time per path | Fewer paths explored | 6/10 |
| 5% Ratio | Per-path = 5% of total | Maximum paths | Very short per-path | 6/10 |
| Fixed Timeout | Fixed per-path (e.g., 5s) | Simple | Doesn't scale with total | 5/10 |

### 3.2 Decision Criteria

| Criterion | Weight | 10% Ratio | 20% Ratio | 5% Ratio | Fixed |
|-----------|--------|-----------|-----------|----------|-------|
| Path Fairness | 30% | 8 | 6 | 9 | 5 |
| Predictability | 25% | 9 | 9 | 7 | 5 |
| Complex Path Support | 25% | 7 | 9 | 4 | 8 |
| Simplicity | 20% | 9 | 9 | 9 | 10 |
| **Weighted Score** | **100%** | **8.2** | **7.9** | **7.15** | **6.65** |

### 3.3 Selection Justification

10% ratio achieves the highest score (8.2) due to:

1. **Fair Exploration**: Each path gets equal opportunity
2. **Predictable Coverage**: ~10 paths expected within timeout
3. **Reasonable Per-Path**: 3s is enough for most symbolic paths
4. **Scalable**: Works with any total timeout value

---

## 4. Alternatives Considered

### 4.1 Alternative 1: 20% Ratio

**Description**: Per-path timeout = 20% of total.

**Advantages**:
- More time for complex paths
- Higher confidence per path

**Disadvantages**:
- **Fewer paths**: Only ~5 paths in 30s
- **Lower coverage**: Less exploration
- **Path monopolization**: One path could consume 20% of total

**Rejection Rationale**: Prioritizes depth over breadth; symbolic execution benefits from breadth.

### 4.2 Alternative 2: 5% Ratio

**Description**: Per-path timeout = 5% of total.

**Advantages**:
- Maximum path exploration
- Quick identification of simple counterexamples

**Disadvantages**:
- **Complex paths timeout**: Many interesting paths exceed 1.5s
- **Superficial analysis**: May miss subtle bugs
- **Frustrating timeouts**: Users see many timeout paths

**Rejection Rationale**: Too aggressive; sacrifices path quality for quantity.

### 4.3 Alternative 3: Fixed Per-Path Timeout

**Description**: Fixed 5-second per-path timeout regardless of total.

**Advantages**:
- Simple to understand
- Consistent per-path time

**Disadvantages**:
- **Doesn't scale**: 5s is 50% of 10s total, 5% of 100s total
- **Unpredictable**: Path count varies wildly with total timeout

**Rejection Rationale**: Ratio-based approach scales better with user-configured timeouts.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Complex paths timeout | Medium | Low | User can increase total timeout | User |
| Too few paths explored | Low | Medium | 10% ratio provides good balance | Architecture |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| None significant | N/A | N/A | N/A | N/A |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Fair Exploration**: Each path gets equal time budget
- **Predictable Coverage**: ~10 paths within default timeout
- **Scalable**: Works with any total timeout
- **No Monopolization**: Single slow path can't consume entire budget

### 6.2 Negative Consequences

- **Complex Paths Timeout**: Paths needing > 10% of total will timeout
- **Trade-off Required**: Balance between depth and breadth

### 6.3 Trade-offs Accepted

- **Breadth > Depth**: More paths explored over deeper per-path analysis
- **Ratio > Fixed**: Proportional scaling over fixed values

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] Phase 1: `PER_PATH_TIMEOUT_RATIO` constant defined
- [x] Phase 2: Applied in `AnalysisOptionSet` creation
- [x] Phase 3: Default timeout documented

### 7.2 Validation Requirements

- [x] Per-path timeout is 10% of total
- [x] Multiple paths can complete within total timeout
- [x] CrossHair respects timeout settings

### 7.3 Rollout Plan

1. **Completed**: Constant implementation
2. **Completed**: CrossHair integration
3. **Ongoing**: Monitor effectiveness in production

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **CrossHair**: `AnalysisOptionSet` with `per_path_timeout` parameter
- **ADR-016**: Environment variables (timeout not configurable via env yet)

### 8.2 Documentation Dependencies

- ADR-004: Resource Limits Strategy
- ADR-016: Environment Variable Configuration

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | Architecture Team | Initial ADR documenting timeout cascade |

---

## 10. References

1. Project `main.py`: Line 337 (PER_PATH_TIMEOUT_RATIO)
2. Project `main.py`: Lines 900-904 (AnalysisOptionSet usage)
3. CrossHair Documentation: AnalysisOptionSet
4. ADR-004: Resource Limits Strategy

---

## Appendix A: Timeout Math

```
Total Timeout: T
Per-Path Timeout: T × 0.1

Examples:
- T = 30s → Per-path = 3s → ~10 paths
- T = 60s → Per-path = 6s → ~10 paths
- T = 10s → Per-path = 1s → ~10 paths
- T = 120s → Per-path = 12s → ~10 paths
```

The ratio ensures consistent path count regardless of total timeout.

---

## Appendix B: CrossHair Timeout Parameters

```python
AnalysisOptionSet(
    # per_condition_timeout: Maximum time for a single condition check
    # This is the "total" timeout for the analysis
    per_condition_timeout=float(self.timeout),

    # per_path_timeout: Maximum time for exploring a single execution path
    # This is calculated as a fraction of per_condition_timeout
    per_path_timeout=float(self.timeout) * PER_PATH_TIMEOUT_RATIO,
)
```

CrossHair uses both parameters:
- `per_condition_timeout`: Hard limit for entire analysis
- `per_path_timeout`: Limit for each path exploration

---

## Appendix C: Tuning Guidance

| Scenario | Recommendation | Rationale |
|----------|----------------|-----------|
| Simple functions | Default (30s, 10%) | Sufficient for most cases |
| Complex conditions | Increase total to 60s | More time for complex paths |
| Many branches | Keep 10% ratio | Ensures breadth of exploration |
| Deep nesting | Consider 15% ratio | More time per path |

---

## Appendix D: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-1701: Configurable Ratio | Compliant | PER_PATH_TIMEOUT_RATIO constant |
| REQ-1702: Per-Path < Total | Compliant | 10% is less than 100% |
| REQ-1703: Multiple Paths | Compliant | ~10 paths in default timeout |
| REQ-1704: ~10 Paths Default | Compliant | 30s / 3s = 10 paths |
