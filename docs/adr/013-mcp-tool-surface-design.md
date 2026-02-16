# ADR-013: MCP Tool Surface Design

**Status**: Accepted
**Date**: 2026-02-15
**Decision Maker**: Architecture Team
**Reviewers**: Product Team, Security Team
**Related ADRs**: 001 (Framework), 009 (Error Handling), 010 (Contract Styles)

---

## Executive Summary

Designed a 5-tool MCP surface with focused, composable capabilities: `symbolic_check` (contract verification), `find_path_to_exception` (exception triggering), `compare_functions` (equivalence checking), `analyze_branches` (dead code detection), and `health_check` (server status). Each tool has a single responsibility with consistent parameter and response patterns.

---

## 1. Context and Problem Statement

### 1.1 Background

The Model Context Protocol (MCP) defines tools as the primary interaction mechanism between AI assistants and servers. Tool design directly impacts:

1. **AI Assistant Integration**: How easily can AI assistants discover and use tools?
2. **User Experience**: How intuitive is the API surface?
3. **Composability**: Can tools be combined for complex workflows?

### 1.2 Problem Statement

Designing the MCP tool surface requires balancing:

- **Granularity**: Fine-grained tools vs. monolithic tools
- **Consistency**: Uniform patterns vs. specialized interfaces
- **Discoverability**: Self-documenting vs. minimal parameters

### 1.3 Requirements

- **REQ-1301**: Each tool has single, well-defined responsibility
- **REQ-1302**: Consistent parameter naming across tools
- **REQ-1303**: Consistent response structure across tools
- **REQ-1304**: Tools must be composable for complex workflows
- **REQ-1305**: All tools must include ToolAnnotations for discoverability

### 1.4 Constraints

- FastMCP tool decorator syntax
- MCP JSON-RPC protocol limitations
- CrossHair analysis capabilities

---

## 2. Decision

**Implement 5 focused tools with consistent patterns and comprehensive annotations.**

### 2.1 Technical Specification

```python
# Tool 1: Contract Verification
@mcp.tool(annotations=ToolAnnotations(
    title="Symbolic Contract Verification",
    readOnlyHint=True,
    idempotentHint=True,
    destructiveHint=False,
))
def symbolic_check(code: str, function_name: str,
                   timeout_seconds: int = 30) -> _SymbolicCheckResult:
    """Symbolically verify that a function satisfies its contract."""

# Tool 2: Exception Path Finding
@mcp.tool(annotations=ToolAnnotations(
    title="Find Exception Triggering Inputs",
    readOnlyHint=True,
    idempotentHint=True,
    destructiveHint=False,
))
def find_path_to_exception(code: str, function_name: str,
                          exception_type: str,
                          timeout_seconds: int = 30) -> _ExceptionPathResult:
    """Find concrete inputs that cause a specific exception type."""

# Tool 3: Function Equivalence
@mcp.tool(annotations=ToolAnnotations(
    title="Semantic Function Equivalence Check",
    readOnlyHint=True,
    idempotentHint=True,
    destructiveHint=False,
))
def compare_functions(code: str, function_a: str, function_b: str,
                     timeout_seconds: int = 60) -> _FunctionComparisonResult:
    """Check if two functions are semantically equivalent."""

# Tool 4: Branch Analysis
@mcp.tool(annotations=ToolAnnotations(
    title="Branch Analysis and Complexity",
    readOnlyHint=True,
    idempotentHint=True,
    destructiveHint=False,
))
def analyze_branches(code: str, function_name: str,
                    timeout_seconds: int = 30,
                    symbolic_reachability: bool = False) -> _BranchAnalysisResult:
    """Enumerate branch conditions and report reachability."""

# Tool 5: Health Check
@mcp.tool(annotations=ToolAnnotations(
    title="Server Health Check",
    readOnlyHint=True,
    idempotentHint=True,
    destructiveHint=False,
))
def health_check() -> _HealthCheckResult:
    """Health check for the Symbolic Execution MCP server."""
```

### 2.2 Tool Surface Summary

| Tool | Purpose | Parameters | Status Values |
|------|---------|------------|---------------|
| `symbolic_check` | Contract verification | code, function_name, timeout | verified, counterexample, timeout, error |
| `find_path_to_exception` | Exception triggering | code, function_name, exception_type, timeout | found, unreachable, error |
| `compare_functions` | Equivalence checking | code, function_a, function_b, timeout | equivalent, different, error |
| `analyze_branches` | Branch analysis | code, function_name, timeout, symbolic_reachability | complete, error |
| `health_check` | Server status | (none) | healthy |

### 2.3 Common Parameters

| Parameter | Type | Default | Purpose |
|-----------|------|---------|---------|
| `code` | str | required | Python source code to analyze |
| `function_name` | str | required | Target function within code |
| `timeout_seconds` | int | 30 (60 for compare) | Analysis timeout |

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **5 Focused Tools** (selected) | Single responsibility per tool | Composable, discoverable | More tools to learn | 9/10 |
| **2 Monolithic Tools** | analyze + health only | Fewer tools | Complex parameters, less composable | 5/10 |
| **10+ Fine-Grained** | Each feature as tool | Maximum flexibility | Overwhelming surface, AI confusion | 4/10 |

### 3.2 Decision Criteria

| Criterion | Weight | 5 Focused | 2 Monolithic | 10+ Fine-Grained |
|-----------|--------|-----------|--------------|------------------|
| Discoverability | 30% | 9 | 6 | 3 |
| Composability | 25% | 9 | 5 | 8 |
| Consistency | 25% | 9 | 7 | 4 |
| AI Integration | 20% | 9 | 6 | 3 |
| **Weighted Score** | **100%** | **9.0** | **5.95** | **4.35** |

### 3.3 Selection Justification

5 focused tools achieve the highest score due to:

1. **Single Responsibility**: Each tool does one thing well
2. **Consistent Patterns**: All analysis tools take `code`, `function_name`, `timeout`
3. **ToolAnnotations**: All tools include `readOnlyHint`, `idempotentHint`, `destructiveHint`
4. **Composability**: Tools can be combined (e.g., analyze_branches then symbolic_check)
5. **AI-Friendly**: Self-documenting tool names and docstrings

---

## 4. Alternatives Considered

### 4.1 Alternative 1: Monolithic `analyze` Tool

**Description**: Single tool with `analysis_type` parameter.

**Advantages**:
- Fewer tools to discover
- Single entry point

**Disadvantages**:
- **Complex parameters**: Different analysis types need different params
- **Inconsistent responses**: Different analysis types return different structures
- **AI confusion**: Harder for AI to understand which parameters to use

**Rejection Rationale**: Violates single responsibility, creates complex parameter handling.

### 4.2 Alternative 2: Fine-Grained 10+ Tools

**Description**: Separate tools for each CrossHair analysis mode, coverage calculation, etc.

**Advantages**:
- Maximum flexibility
- Exposes all CrossHair capabilities

**Disadvantages**:
- **Overwhelming surface**: Too many tools for AI to discover
- **Fragmentation**: Simple workflows require multiple tool calls
- **Maintenance**: More tools to document and maintain

**Rejection Rationale**: Over-engineering for current use cases.

### 4.3 Alternative 3: Pipeline-Based Design

**Description**: Create analysis session, add code, run analysis, get results.

**Advantages**:
- Stateful workflows
- Incremental analysis

**Disadvantages**:
- **State management complexity**: See ADR-014 (Stateless Model)
- **More tool calls**: Simple analysis requires 3+ calls
- **Session lifecycle**: Must manage session creation/destruction

**Rejection Rationale**: Adds unnecessary complexity for stateless analysis needs.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Missing analysis capability | Low | Medium | Can add tools later without breaking changes | Tech Lead |
| Inconsistent response structure | Low | Medium | TypedDict schemas enforce consistency | Tech Lead |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| AI assistant tool confusion | Low | Low | Clear docstrings, ToolAnnotations | Documentation |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Discoverability**: 5 tools easy for AI to understand
- **Consistency**: All tools follow same patterns
- **Composability**: Tools can be combined for complex workflows
- **Documentation**: ToolAnnotations provide machine-readable metadata

### 6.2 Negative Consequences

- **Multiple Tools**: Users must understand which tool to use
- **No Single Entry Point**: No "analyze everything" tool

### 6.3 Trade-offs Accepted

- **Focus vs. Convenience**: Focused tools over convenience single entry point
- **Stability vs. Extensibility**: Fixed 5 tools over plugin architecture

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] Phase 1: Core 5 tools implemented
- [x] Phase 2: ToolAnnotations added to all tools
- [x] Phase 3: TypedDict response schemas defined
- [x] Phase 4: Consistent error handling (ADR-009)

### 7.2 Validation Requirements

- [x] All tools have ToolAnnotations
- [x] All tools have consistent parameter patterns
- [x] All tools have TypedDict response types
- [x] All tools have clear docstrings

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **FastMCP**: `@mcp.tool()` decorator, `ToolAnnotations` class
- **CrossHair**: Analysis capabilities backing each tool

### 8.2 Documentation Dependencies

- ADR-009: Error Handling Philosophy
- ADR-010: Contract Style Support
- ADR-015: TypedDict Return Types

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | Architecture Team | Initial ADR documenting tool surface |

---

## 10. References

1. Project `main.py`: Lines 1573-1709 (tool definitions)
2. MCP Specification: Tool definition format
3. FastMCP Documentation: ToolAnnotations
4. ADR-009: Error Handling Philosophy

---

## Appendix A: Tool Response Schemas

```python
class _SymbolicCheckResult(TypedDict):
    status: Literal["verified", "counterexample", "timeout", "error"]
    counterexamples: list[_Counterexample]
    paths_explored: int
    paths_verified: int
    time_seconds: float
    coverage_estimate: float
    error_type: NotRequired[str]
    message: NotRequired[str]

class _ExceptionPathResult(TypedDict):
    status: Literal["found", "unreachable", "error"]
    triggering_inputs: NotRequired[list[_Counterexample]]
    paths_to_exception: NotRequired[int]
    total_paths_explored: NotRequired[int]
    time_seconds: NotRequired[float]
    error_type: NotRequired[str]
    message: NotRequired[str]

class _FunctionComparisonResult(TypedDict):
    status: Literal["equivalent", "different", "error"]
    distinguishing_input: NotRequired[Optional[_Counterexample]]
    paths_compared: NotRequired[int]
    confidence: NotRequired[str]
    error_type: NotRequired[str]
    message: NotRequired[str]

class _BranchAnalysisResult(TypedDict):
    status: Literal["complete", "error"]
    branches: NotRequired[list[_BranchInfo]]
    total_branches: NotRequired[int]
    reachable_branches: NotRequired[int]
    dead_code_lines: NotRequired[list[int]]
    cyclomatic_complexity: NotRequired[int]
    time_seconds: NotRequired[float]
    analysis_mode: NotRequired[Literal["static", "symbolic"]]
    error_type: NotRequired[str]
    message: NotRequired[str]

class _HealthCheckResult(TypedDict):
    status: Literal["healthy"]
    version: str
    python_version: str
    crosshair_version: Optional[str]
    z3_version: Optional[str]
    platform: str
    memory_usage_mb: float
```

---

## Appendix B: Composability Examples

```python
# Example 1: Analyze then verify
branches = analyze_branches(code, "process")
if branches["total_branches"] > 10:
    result = symbolic_check(code, "process", timeout_seconds=60)
else:
    result = symbolic_check(code, "process")

# Example 2: Compare functions, find difference
compare = compare_functions(code, "old_impl", "new_impl")
if compare["status"] == "different":
    exc_path = find_path_to_exception(code, "new_impl", "ValueError")

# Example 3: Health check before analysis
health = health_check()
if health["status"] == "healthy":
    result = symbolic_check(code, "target")
```

---

## Appendix C: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-1301: Single Responsibility | Compliant | Each tool has one purpose |
| REQ-1302: Consistent Parameters | Compliant | code, function_name, timeout pattern |
| REQ-1303: Consistent Responses | Compliant | All use TypedDict with status field |
| REQ-1304: Composability | Compliant | Tools can be combined |
| REQ-1305: ToolAnnotations | Compliant | All tools have annotations |
