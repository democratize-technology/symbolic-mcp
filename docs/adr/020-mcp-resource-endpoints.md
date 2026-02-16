# ADR-020: MCP Resource Endpoint Strategy

**Status**: Accepted
**Date**: 2026-02-15
**Decision Maker**: API Team
**Reviewers**: Architecture Team, Documentation
**Related ADRs**: 001 (Framework), 003 (Security Model), 013 (Tool Surface)

---

## Executive Summary

Implemented 3 MCP resource endpoints (`config://security`, `config://server`, `info://capabilities`) following URI-based namespacing patterns. Resources provide read-only configuration and capability information, enabling clients to discover server features without executing analysis tools.

---

## 1. Context and Problem Statement

### 1.1 Background

MCP resources are read-only data sources that clients can query for information. Unlike tools (which perform actions), resources provide static or dynamically-generated data. Common patterns include:

1. **Configuration exposure**: Showing server settings
2. **Capability discovery**: Listing available features
3. **Status information**: Runtime state

### 1.2 Problem Statement

Resource design involves decisions:

- **Naming**: URI scheme for resources
- **Content**: What information to expose
- **Security**: What is safe to expose
- **Consistency**: Uniform response format

### 1.3 Requirements

- **REQ-2001**: Resources use consistent URI scheme
- **REQ-2002**: Resources expose only non-sensitive configuration
- **REQ-2003**: Resources enable capability discovery
- **REQ-2004**: Resources use TypedDict response types
- **REQ-2005**: Resources are read-only (no mutations)

### 1.4 Constraints

- FastMCP `@mcp.resource()` decorator syntax
- MCP protocol resource format
- Security considerations for exposed data

---

## 2. Decision

**Implement 3 namespaced resource endpoints: `config://security`, `config://server`, `info://capabilities`.**

### 2.1 Technical Specification

```python
# Resource 1: Security Configuration
@mcp.resource("config://security")
def get_security_config() -> _SecurityConfigResult:
    """Current security configuration settings.

    Returns the whitelist of allowed modules, blocked modules, and
    other security-related configuration from ADR-003.
    """
    return {
        "allowed_modules": list(ALLOWED_MODULES),
        "blocked_modules": list(BLOCKED_MODULES),
        "dangerous_builtins": list(DANGEROUS_BUILTINS),
        "memory_limit_mb": MEMORY_LIMIT_MB,
        "code_size_bytes": CODE_SIZE_LIMIT,
        "coverage_threshold": COVERAGE_EXHAUSTIVE_THRESHOLD,
    }

# Resource 2: Server Configuration
@mcp.resource("config://server")
def get_server_config() -> _ServerConfigResult:
    """Current server configuration settings.

    Returns version, timeout settings, and other server-related
    configuration.
    """
    return {
        "version": __version__,
        "default_timeout_seconds": DEFAULT_ANALYSIS_TIMEOUT_SECONDS,
        "mask_error_details": True,  # Always True for production
        "transport": "oauth" if _get_github_auth() else "stdio",
    }

# Resource 3: Capabilities
@mcp.resource("info://capabilities")
def get_capabilities() -> _CapabilitiesResult:
    """Server capabilities and available tools.

    Returns a list of available tools and their descriptions.
    """
    return {
        "tools": [
            {"name": "symbolic_check", "description": "..."},
            {"name": "find_path_to_exception", "description": "..."},
            {"name": "compare_functions", "description": "..."},
            {"name": "analyze_branches", "description": "..."},
            {"name": "health_check", "description": "..."},
        ],
        "resources": [
            {"uri": "config://security", "description": "..."},
            {"uri": "config://server", "description": "..."},
            {"uri": "info://capabilities", "description": "..."},
        ],
    }
```

### 2.2 Resource Summary

| URI | Category | Purpose | Response Type |
|-----|----------|---------|---------------|
| `config://security` | Configuration | Security settings | `_SecurityConfigResult` |
| `config://server` | Configuration | Server settings | `_ServerConfigResult` |
| `info://capabilities` | Discovery | Tools and resources | `_CapabilitiesResult` |

### 2.3 URI Scheme

```
{category}://{name}

Categories:
- config://  Server configuration
- info://    Discovery information
```

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **3 Namespaced Resources** (selected) | config://, info:// prefixes | Clear organization, discoverable | More endpoints | 9/10 |
| Single Config Resource | One resource for all config | Simpler | Less organized | 6/10 |
| 5+ Granular Resources | One per setting | Maximum granularity | Overwhelming | 4/10 |

### 3.2 Decision Criteria

| Criterion | Weight | 3 Namespaced | Single | 5+ Granular |
|-----------|--------|--------------|--------|-------------|
| Organization | 30% | 9 | 5 | 3 |
| Discoverability | 25% | 9 | 7 | 5 |
| Security | 25% | 8 | 6 | 4 |
| Simplicity | 20% | 8 | 9 | 3 |
| **Weighted Score** | **100%** | **8.55** | **6.55** | **3.75** |

### 3.3 Selection Justification

3 namespaced resources achieve the highest score (8.55) due to:

1. **Clear Categories**: `config://` for settings, `info://` for discovery
2. **Discoverability**: Clients can enumerate resources
3. **Security Isolation**: Security config separate from general config
4. **Appropriate Granularity**: 3 resources is manageable but organized

---

## 4. Alternatives Considered

### 4.1 Alternative 1: Single Configuration Resource

**Description**: One `config://all` resource with all settings.

**Advantages**:
- Simpler implementation
- One call for all config

**Disadvantages**:
- **No organization**: Security and server config mixed
- **Security exposure**: May expose unnecessary info
- **Large response**: More data than needed

**Rejection Rationale**: Separate resources improve organization and security.

### 4.2 Alternative 2: Granular Per-Setting Resources

**Description**: Resources like `config://memory_limit`, `config://allowed_modules`, etc.

**Advantages**:
- Maximum granularity
- Precise queries

**Disadvantages**:
- **Overwhelming**: Too many resources
- **Chatty**: Multiple requests needed
- **Maintenance**: More endpoints to maintain

**Rejection Rationale**: Over-engineering; grouped resources are more practical.

### 4.3 Alternative 3: No Resources (Tools Only)

**Description**: Expose all information via tools instead of resources.

**Advantages**:
- Simpler API surface
- Only one concept

**Disadvantages**:
- **Semantic mismatch**: Resources are for data, tools for actions
- **MCP non-compliance**: Resources are part of MCP spec
- **Client confusion**: Expected pattern not followed

**Rejection Rationale**: Resources are the MCP pattern for read-only data.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Sensitive data exposure | Low | High | Review exposed data, no secrets | Security |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| None significant | N/A | N/A | N/A | N/A |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Discoverability**: Clients can enumerate capabilities
- **Organization**: Clear URI scheme
- **Type Safety**: TypedDict responses
- **MCP Compliance**: Standard resource pattern

### 6.2 Negative Consequences

- **More Endpoints**: 3 resources to maintain
- **Documentation**: Must document each resource

### 6.3 Trade-offs Accepted

- **Organization > Simplicity**: Named resources over single endpoint
- **Standard > Custom**: MCP patterns over custom API

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] Phase 1: `config://security` resource
- [x] Phase 2: `config://server` resource
- [x] Phase 3: `info://capabilities` resource
- [x] Phase 4: TypedDict response types

### 7.2 Validation Requirements

- [x] All resources use TypedDict
- [x] No sensitive data exposed
- [x] Consistent URI scheme
- [x] Read-only access

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **FastMCP**: `@mcp.resource()` decorator
- **ADR-003**: Security model (allowed_modules, blocked_modules)

### 8.2 Documentation Dependencies

- ADR-003: Security Model
- ADR-013: Tool Surface Design
- ADR-015: TypedDict Return Types

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-02-15 | API Team | Initial ADR documenting resource endpoints |

---

## 10. References

1. Project `main.py`: Lines 1712-1781 (resource definitions)
2. MCP Specification: Resources
3. FastMCP Documentation: Resource decorator
4. ADR-003: Whitelist-Based Import Security Model

---

## Appendix A: Response Schemas

```python
class _SecurityConfigResult(TypedDict):
    """Result of security configuration resource."""
    allowed_modules: list[str]
    blocked_modules: list[str]
    dangerous_builtins: list[str]
    memory_limit_mb: int
    code_size_bytes: int
    coverage_threshold: int

class _ServerConfigResult(TypedDict):
    """Result of server configuration resource."""
    version: str
    default_timeout_seconds: int
    mask_error_details: bool
    transport: Literal["oauth", "stdio"]

class _CapabilitiesResult(TypedDict):
    """Result of capabilities resource."""
    tools: list[_ToolDescription]
    resources: list[_ResourceDescription]

class _ToolDescription(TypedDict):
    """Description of an MCP tool."""
    name: str
    description: str

class _ResourceDescription(TypedDict):
    """Description of an MCP resource."""
    uri: str
    description: str
```

---

## Appendix B: Client Usage Examples

```python
# MCP Client usage
security_config = await client.read_resource("config://security")
print(f"Allowed modules: {security_config['allowed_modules']}")

server_config = await client.read_resource("config://server")
print(f"Server version: {server_config['version']}")

capabilities = await client.read_resource("info://capabilities")
print(f"Available tools: {[t['name'] for t in capabilities['tools']]}")
```

---

## Appendix C: Security Considerations

| Data | Exposed? | Rationale |
|------|----------|-----------|
| Memory limit | Yes | Non-sensitive, useful for clients |
| Code size limit | Yes | Non-sensitive, useful for clients |
| Allowed modules | Yes | Required for client understanding |
| Blocked modules | Yes | Required for error messages |
| OAuth client ID | No | Sensitive, not exposed |
| OAuth client secret | No | Sensitive, not exposed |
| Environment variables | No | Not exposed directly |

---

## Appendix D: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| REQ-2001: URI Scheme | Compliant | config://, info:// prefixes |
| REQ-2002: Non-Sensitive Only | Compliant | No secrets exposed |
| REQ-2003: Capability Discovery | Compliant | info://capabilities |
| REQ-2004: TypedDict Responses | Compliant | All resources use TypedDict |
| REQ-2005: Read-Only | Compliant | No mutations |
