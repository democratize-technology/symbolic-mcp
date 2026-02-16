# ADR-021: Prompt Template Design for AI Workflows

**Status**: Accepted
**Date**: 2026-02-15
**Decision Maker**: UX Team
**Reviewers**: AI Integration Team, Documentation
**Related ADRs**: 013 (Tool Surface), 020 (Resource Endpoints)

---

## Executive Summary

Implemented 4 prompt templates for common AI assistant workflows: `symbolic_check_template`, `find_exception_path_template`, `compare_functions_template`, and `analyze_branches_template`. Each template provides structured guidance for AI assistants to use MCP tools effectively, reducing friction in human-AI collaboration.

---

## 1. Context and Problem Statement

### 1.1 Background

MCP prompts are pre-defined templates that AI assistants can use to guide user interactions. They serve as:

1. **Workflow guides**: Step-by-step instructions for common tasks
2. **Tool discovery**: Helping AI understand available tools
3. **User onboarding**: Reducing learning curve for new users
4. **Consistency**: Standardizing AI responses

### 1.2 Problem Statement

Prompt design involves balancing:

- **Guidance vs. Flexibility**: Prescriptive templates vs. open-ended
- **Completeness vs. Brevity**: Detailed instructions vs. concise prompts
- **Tool Coupling**: Template per tool vs. workflow-based

### 1.3 Requirements

- **REQ-2101**: Prompts for each analysis tool
- **REQ-2102**: Clear parameter guidance ({{parameter}} syntax)
- **REQ-2103**: Consistent structure across prompts
- **REQ-2104**: Guidance on result interpretation
- **REQ-2105**: FastMCP `@mcp.prompt()` decorator usage

### 1.4 Constraints

- FastMCP prompt decorator syntax
- MCP protocol prompt format
- Template variable syntax ({{variable}})

---

## 2. Decision

**Implement 4 prompt templates, one per analysis tool, with consistent structure.**

### 2.1 Technical Specification

```python
# Prompt 1: Symbolic Check
@mcp.prompt
def symbolic_check_template() -> str:
    """Template for analyzing function contracts with symbolic execution.

    Use this prompt when you want to verify that a function satisfies
    its contract using formal symbolic execution.
    """
    return """
Please analyze this Python function using symbolic execution:

```python
{{code}}
```

Function to analyze: `{{function_name}}`

Report on:
1. Contract violations found (if any)
2. Counterexamples with concrete inputs
3. Number of paths explored and verified
4. Estimated code coverage

Use the `symbolic_check` tool with appropriate timeout.
"""

# Prompt 2: Find Exception Path
@mcp.prompt
def find_exception_path_template() -> str:
    """Template for finding paths to exceptions.

    Use this prompt when you want to find concrete inputs that cause
    a specific exception type to be raised.
    """
    return """
Please find concrete inputs that cause this function to raise an exception:

```python
{{code}}
```

Function to analyze: `{{function_name}}`
Target exception type: `{{exception_type}}`

Report on:
1. Concrete inputs that trigger the exception
2. Path conditions that lead to the exception
3. Whether the exception is reachable

Use the `find_path_to_exception` tool with appropriate timeout.
"""

# Prompt 3: Compare Functions
@mcp.prompt
def compare_functions_template() -> str:
    """Template for comparing function equivalence.

    Use this prompt when you want to check if two functions are
    semantically equivalent.
    """
    return """
Please compare these two functions for semantic equivalence:

```python
{{code}}
```

Function A: `{{function_a}}`
Function B: `{{function_b}}`

Report on:
1. Whether the functions are semantically equivalent
2. Any behavioral differences found
3. Concrete inputs demonstrating differences (if any)

Use the `compare_functions` tool with appropriate timeout.
"""

# Prompt 4: Analyze Branches
@mcp.prompt
def analyze_branches_template() -> str:
    """Template for branch analysis.

    Use this prompt when you want to analyze branch conditions
    and code complexity.
    """
    return """
Please analyze the branch structure and complexity of this function:

```python
{{code}}
```

Function to analyze: `{{function_name}}`

Report on:
1. All branch conditions found
2. Cyclomatic complexity
3. Potential dead code (unreachable branches)
4. Static vs symbolic reachability (if requested)

Use the `analyze_branches` tool with appropriate timeout.
"""
```

### 2.2 Prompt Summary

| Prompt | Tool | Parameters | Use Case |
|--------|------|------------|----------|
| `symbolic_check_template` | `symbolic_check` | code, function_name | Contract verification |
| `find_exception_path_template` | `find_path_to_exception` | code, function_name, exception_type | Exception triggering |
| `compare_functions_template` | `compare_functions` | code, function_a, function_b | Equivalence checking |
| `analyze_branches_template` | `analyze_branches` | code, function_name | Branch analysis |

### 2.3 Common Structure

```
1. Request: What to analyze
2. Code Block: {{code}} placeholder
3. Parameters: {{parameter_name}} placeholders
4. Report Guidance: What to report
5. Tool Hint: Which tool to use
```

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **4 Tool-Aligned Prompts** (selected) | One per analysis tool | Clear mapping, complete coverage | More prompts | 9/10 |
| Workflow Prompts | Multi-tool workflows | Guides complex tasks | Less flexible | 6/10 |
| Single Generic Prompt | One template for all | Simple | Vague guidance | 4/10 |

### 3.2 Decision Criteria

| Criterion | Weight | 4 Tool-Aligned | Workflow | Single |
|-----------|--------|----------------|----------|--------|
| Tool Discovery | 30% | 9 | 7 | 3 |
| Guidance Quality | 25% | 9 | 8 | 4 |
| Simplicity | 20% | 7 | 5 | 9 |
| Completeness | 15% | 9 | 7 | 3 |
| Consistency | 10% | 9 | 6 | 10 |
| **Weighted Score** | **100%** | **8.6** | **6.75** | **5.0** |

### 3.3 Selection Justification

4 tool-aligned prompts achieve the highest score (8.6) due to:

1. **Tool Discovery**: Each prompt introduces a tool
2. **Clear Guidance**: Specific instructions per tool
3. **Complete Coverage**: All analysis tools covered
4. **Consistent Structure**: Same format for all prompts
5. **Parameter Placeholders**: Clear variable syntax

---

## 4. Alternatives Considered

### 4.1 Alternative 1: Workflow-Based Prompts

**Description**: Multi-step prompts combining multiple tools.

**Advantages**:
- Guides complex workflows
- Real-world use case alignment

**Disadvantages**:
- **Less flexible**: Locked into specific workflow
- **More complex**: Harder to understand
- **Tool mixing**: Unclear which tool to use when

**Rejection Rationale**: Tool-aligned prompts are more discoverable and flexible.

### 4.2 Alternative 2: Single Generic Prompt

**Description**: One template for all analysis types.

**Advantages**:
- Maximum simplicity
- One prompt to maintain

**Disadvantages**:
- **Vague guidance**: Doesn't help AI understand tools
- **No tool discovery**: Doesn't introduce capabilities
- **Poor UX**: Users must know what to ask

**Rejection Rationale**: Doesn't provide meaningful guidance.

### 4.3 Alternative 3: No Prompts

**Description**: Rely on tool descriptions only.

**Advantages**:
- Simpler API surface
- Less documentation

**Disadvantages**:
- **Poor onboarding**: No guidance for new users
- **Inconsistent AI responses**: No structure
- **MCP non-compliance**: Prompts are part of MCP spec

**Rejection Rationale**: Prompts improve AI assistant integration.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Outdated guidance | Low | Low | Review prompts with tool changes | Dev Team |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| None significant | N/A | N/A | N/A | N/A |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Tool Discovery**: Prompts introduce available tools
- **Consistent Structure**: Same format across prompts
- **Parameter Guidance**: Clear placeholders for variables
- **Improved UX**: Better AI assistant integration
- **MCP Compliance**: Standard prompt pattern

### 6.2 Negative Consequences

- **Maintenance**: 4 prompts to keep updated
- **Documentation**: Must document each prompt

### 6.3 Trade-offs Accepted

- **Completeness > Simplicity**: More prompts for better guidance
- **Tool Alignment > Workflow**: Per-tool prompts over workflow guides

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] Phase 1: `symbolic_check_template` prompt
- [x] Phase 2: `find_exception_path_template` prompt
- [x] Phase 3: `compare_functions_template` prompt
- [x] Phase 4: `analyze_branches_template` prompt

### 7.2 Validation Requirements

- [x] All analysis tools have corresponding prompt
- [x] Consistent structure across prompts
- [x] Parameter placeholders use {{syntax}}
- [x] Tool hints included

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **FastMCP**: `@mcp.prompt` decorator
- **ADR-013**: Tool Surface Design

### 8.2 Documentation Dependencies

- ADR-013: MCP Tool Surface Design
- FastMCP Documentation: Prompt decorator

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | UX Team | Initial ADR documenting prompt templates |

---

## 10. References

1. Project `main.py`: Lines 1784-1885 (prompt definitions)
2. MCP Specification: Prompts
3. FastMCP Documentation: Prompt decorator
4. ADR-013: MCP Tool Surface Design

---

## Appendix A: Prompt Template Structure

```
┌─────────────────────────────────────────┐
│ @mcp.prompt                              │
│ def prompt_name() -> str:               │
│     """Docstring (shown to AI)"""       │
│     return """                          │
│                                         │
│     [Request: What to do]               │
│                                         │
│     ```python                           │
│     {{code}}                            │
│     ```                                 │
│                                         │
│     [Parameters: {{param1}}, {{param2}}]│
│                                         │
│     [Report on:                         │
│      1. Item 1                          │
│      2. Item 2                          │
│      ...]                               │
│                                         │
│     [Tool hint: Use `tool_name`]        │
│     """                                 │
└─────────────────────────────────────────┘
```

---

## Appendix B: Client Usage

```python
# AI assistant using prompt
user: "Check this function for bugs"
code = "def foo(x): ..."

# AI retrieves prompt template
prompt = await client.get_prompt("symbolic_check_template")

# AI fills in template
filled_prompt = prompt.format(code=code, function_name="foo")

# AI uses prompt guidance to call tool
result = await client.call_tool("symbolic_check", {
    "code": code,
    "function_name": "foo"
})

# AI reports results following prompt guidance
```

---

## Appendix C: Prompt vs Tool Comparison

| Aspect | Prompts | Tools |
|--------|---------|-------|
| Purpose | Guide AI behavior | Execute actions |
| Returns | Text template | Structured result |
| Called by | AI assistant | AI assistant |
| Parameters | {{placeholder}} | JSON arguments |
| Documentation | Docstring | Type hints |

---

## Appendix D: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-2101: Prompts per Tool | Compliant | 4 prompts for 4 analysis tools |
| REQ-2102: Parameter Syntax | Compliant | {{parameter}} syntax |
| REQ-2103: Consistent Structure | Compliant | Same format all prompts |
| REQ-2104: Result Guidance | Compliant | "Report on:" sections |
| REQ-2105: FastMCP Decorator | Compliant | @mcp.prompt used |
