# ADR-011: Authentication & Authorization

**Status**: Accepted
**Date**: 2025-02-13
**Related ADRs**: 001 (FastMCP Framework), 003 (Security Model)

---

## Executive Summary

Adopt GitHub OAuth 2.1 for HTTP deployment authentication. All tools remain public (no scope restrictions) because code-level security (ADR-003) provides sufficient protection. OAuth secures the HTTP transport layer for production deployments while maintaining full API functionality for stdio transport (local development).

---

## 1. Context and Problem Statement

### 1.1 Background

The Symbolic Execution MCP Server currently operates with stdio transport only, which is secure for local development but unsuitable for production HTTP deployments. FastMCP 2.0 specification recommends authentication for remote servers, and some LLM clients require authentication for remote servers.

### 1.2 Problem Statement

Without authentication, HTTP deployment of the Symbolic Execution server would:
- Accept arbitrary code execution requests from any client
- Expose attack surface for denial-of-service
- Violate FastMCP security best practices
- Prevent integration with clients requiring authentication

### 1.3 Requirements

- **REQ-AUTH-001**: Support OAuth 2.1 authentication for HTTP transport
- **REQ-AUTH-002**: Maintain stdio transport support for local development
- **REQ-AUTH-003**: Zero code changes when switching between stdio and HTTP
- **REQ-AUTH-004**: All tools remain accessible to authenticated users
- **REQ-AUTH-005**: Security model (ADR-003) provides sufficient protection

### 1.4 Constraints

- **CONST-AUTH-001**: OAuth credentials must not be hardcoded
- **CONST-AUTH-002**: Must not break existing stdio deployment
- **CONST-AUTH-003**: Must be FastMCP 2.0 compliant
- **CONST-AUTH-004**: No tool-level authorization (all tools public)

---

## 2. Decision

**Use GitHub OAuth 2.1 (via FastMCP's GitHubProvider) for HTTP deployment authentication with environment-based configuration.**

### 2.1 Technical Specification

```python
# main.py - Import GitHubProvider
from fastmcp.server.auth.providers.github import GitHubProvider

# main.py - Helper function
def _get_github_auth() -> Optional[GitHubProvider]:
    """Get GitHub OAuth provider if configured for HTTP deployment.

    Returns GitHubProvider if GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET
    environment variables are set. Otherwise returns None for stdio transport.

    Environment Variables:
        GITHUB_CLIENT_ID: GitHub OAuth App client ID
        GITHUB_CLIENT_SECRET: GitHub OAuth App client secret

    Returns:
        GitHubProvider if configured, None for stdio (local development)
    """
    client_id = os.environ.get("GITHUB_CLIENT_ID")
    client_secret = os.environ.get("GITHUB_CLIENT_SECRET")

    if client_id and client_secret:
        logger.info("GitHub OAuth authentication configured for HTTP deployment")
        return GitHubProvider(
            client_id=client_id,
            client_secret=client_secret,
        )

    logger.info("No OAuth credentials found, using stdio transport (local development)")
    return None

# main.py - FastMCP initialization
auth = _get_github_auth()
mcp = FastMCP(
    "Symbolic Execution Server",
    auth=auth,  # OAuth for HTTP, None for stdio
    lifespan=lifespan,
    mask_error_details=True,
)
```

### 2.2 Scope

- **In Scope**:
  - GitHub OAuth 2.1 authentication for HTTP transport
  - Environment-based credential configuration
  - Automatic transport selection (stdio vs HTTP) based on credentials
  - All 5 tools: `symbolic_check`, `find_path_to_exception`, `compare_functions`, `analyze_branches`, `health_check`

- **Out of Scope**:
  - Tool-level authorization (all tools remain public)
  - OAuth providers other than GitHub
  - Custom authorization logic
  - User role/permission management

---

## 3. Rationale

### 3.1 Analysis of Options

| Option | Description | Pros | Cons | Score |
|--------|-------------|------|------|-------|
| **GitHub OAuth** (selected) | FastMCP native GitHubProvider | Widely understood, reliable, zero code changes with env var config | Requires GitHub account | 9/10 |
| Google OAuth | FastMCP native GoogleProvider | More users have Google accounts | More complex setup | 7/10 |
| JWTVerifier only | FastMCP native JWTVerifier | No external provider | Requires separate token issuance system | 5/10 |
| No OAuth (current) | No authentication | Zero setup | Critical security risk for HTTP | 1/10 |

### 3.2 Decision Criteria

| Criterion | Weight | GitHub OAuth | Google OAuth | JWT Only | No OAuth |
|-----------|--------|-------------|--------------|-----------|----------|
| Security | 35% | 9 | 9 | 5 | 1 |
| Simplicity | 30% | 9 | 7 | 5 | 10 |
| Ecosystem | 20% | 9 | 10 | 5 | 1 |
| Reliability | 15% | 9 | 9 | 7 | 1 |
| **Weighted Score** | **100%** | **9.0** | **8.3** | **5.2** | **2.6** |

### 3.3 Selection Justification

GitHub OAuth provides the best balance of security, simplicity, and reliability. The environment-based configuration means zero code changes when switching between stdio and HTTP deployments. FastMCP's native GitHubProvider handles all OAuth protocol details automatically.

**Tool Authorization Strategy**: All tools remain public (no scope restrictions). This is correct because:
1. ADR-003 whitelist blocks all dangerous modules regardless of user identity
2. AST validation prevents code execution escapes
3. OAuth provides transport-layer security (prevents unauthorized HTTP access)
4. Additional tool-level scopes would require use case justification

---

## 4. Alternatives Considered

### 4.1 Alternative 1: No OAuth (Current State)

**Description**: Continue with stdio transport only, no HTTP deployment.

**Analysis**:
- **Advantages**: Zero setup, no external dependencies
- **Disadvantages**: Cannot deploy via HTTP, limited to local development
- **Rejection Rationale**: Unacceptable for production use cases. HTTP deployment is a core MCP capability.

### 4.2 Alternative 2: Tool-Level Authorization

**Description**: Add `@mcp.tool(auth=auth.require_scopes("admin"))` decorators to sensitive tools.

**Analysis**:
- **Advantages**: Fine-grained access control
- **Disadvantages**: Increased complexity, no clear scope requirements, ADR-003 already protects
- **Rejection Rationale**: Over-engineering. Code-level security (ADR-003) is sufficient.

### 4.3 Alternative 3: Multiple OAuth Providers

**Description**: Support GitHub, Google, and custom OAuth providers simultaneously.

**Analysis**:
- **Advantages**: Maximum user flexibility
- **Disadvantages**: Increased configuration complexity, more maintenance surface
- **Rejection Rationale**: GitHub OAuth is sufficient for current use cases. Can add later if needed.

---

## 5. Risk Assessment

### 5.1 Technical Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| GitHub OAuth downtime | Low | Medium | FastMCP handles token refresh automatically | FastMCP |
| Client doesn't support OAuth | Low | High | Document OAuth requirement for HTTP deployments | Documentation |
| Secret leakage (repo/env) | Low | Critical | Use environment variables, never commit secrets | Operations |

### 5.2 Operational Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Callback URL mismatch | Low | Medium | Document exact callback URL in README | Documentation |
| Token refresh failure | Low | Medium | FastMCP handles automatically | FastMCP |

### 5.3 Security Risks

| Risk | Probability | Severity | Mitigation | Owner |
|------|-------------|----------|------------|-------|
| Compromised GitHub account | Low | Critical | Use 2FA, monitor OAuth app usage | User |
| Stolen OAuth token | Low | High | Tokens have limited lifetime, auto-refresh | FastMCP |

---

## 6. Consequences

### 6.1 Positive Consequences

- **Production HTTP Deployment**: Server can be safely deployed via HTTP with OAuth
- **Zero Code Changes**: Switching between stdio and HTTP requires only environment variables
- **FastMCP Compliance**: Fully compliant with FastMCP 2.0 authentication recommendations
- **Security**: OAuth prevents unauthorized HTTP access while ADR-003 prevents code execution escapes

### 6.2 Negative Consequences

- **GitHub Account Required**: Users must have GitHub account for HTTP deployment
- **OAuth App Setup**: One-time OAuth app creation required before HTTP deployment

### 6.3 Trade-offs Accepted

- **Simplicity over Flexibility**: Only GitHub OAuth supported (not Google, etc.)
  - **Rationale**: GitHub OAuth is sufficient for current use cases
  - **Future**: Can add additional providers if needed

---

## 7. Implementation Plan

### 7.1 Implementation Status

- [x] Phase 1: Add `GitHubProvider` import to `main.py`
- [x] Phase 2: Create `_get_github_auth()` helper function
- [x] Phase 3: Update `FastMCP` initialization with `auth` parameter
- [x] Phase 4: Add OAuth configuration tests (`test_oauth_configuration.py`)
- [x] Phase 5: Create ADR-011 documentation

### 7.2 Validation Requirements

- [x] Local stdio deployment still works (no OAuth env vars)
- [x] Helper function returns `None` without env vars
- [x] Helper function returns `GitHubProvider` with both env vars
- [x] Helper function returns `None` with only one env var set
- [x] FastMCP server accepts both `auth=None` and `auth=GitHubProvider`
- [ ] HTTP deployment rejects unauthenticated requests (requires manual testing)
- [ ] Authorized clients can successfully call all 5 tools (requires manual testing)

### 7.3 Rollout Plan

1. **Step 1**: Create GitHub OAuth App
   - Navigate to: https://github.com/settings/developers
   - "OAuth Apps" → "New OAuth App"
   - Application name: `Symbolic MCP Server [Your Environment]`
   - Homepage URL: `https://your-server-domain.com`
   - Authorization callback URL: `https://your-server-domain.com/auth/callback/github`
   - Save Client ID and Client Secret as environment variables

2. **Step 2**: Set Environment Variables (for HTTP deployment)
   ```bash
   export GITHUB_CLIENT_ID="Ov23li..."
   export GITHUB_CLIENT_SECRET="github_pat_..."
   ```

3. **Step 3**: Deploy with gunicorn/uvicorn
   ```bash
   gunicorn -w uvicorn.workers.UvicornWorker main:mcp
   ```

4. **Step 4**: Update Documentation
   - Add OAuth setup instructions to README.md
   - Document HTTP deployment requirements

---

## 8. Dependencies

### 8.1 Technical Dependencies

- **fastmcp.server.auth.providers.github**: Provides `GitHubProvider` class
  - **Impact**: Zero. FastMCP already installed as dependency
  - **Version**: FastMCP 2.0+

### 8.2 Documentation Dependencies

- **FastMCP Authentication Spec**: https://gofastmcp.com/servers/auth/authentication.md
- **Related ADR**:
  - ADR-001: FastMCP Framework Selection
  - ADR-003: Security Model (Whitelist-Based Import Security)

### 8.3 External Dependencies

- **GitHub OAuth**: https://github.com/settings/developers
- **Python stdlib**: `os` module for environment variable access

---

## 9. Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2025-02-13 | Implementation | Initial draft |
| 1.0 | 2025-02-13 | Implementation | Accepted, implementation complete |

---

## 10. References

1. FastMCP Authentication: https://gofastmcp.com/servers/auth/authentication.md
2. FastMCP HTTP Deployment: https://gofastmcp.com/deployment/http.md
3. GitHub OAuth Apps: https://github.com/settings/developers
4. ADR-003: Security Model (Whitelist-Based Import Security)
5. FastMCP GitHubProvider: fastmcp.server.auth.providers.github module

---

## Appendix A: Technical Analysis

### Environment Variable Behavior

| GITHUB_CLIENT_ID | GITHUB_CLIENT_SECRET | Result |
|------------------|----------------------|---------|
| Not set | Not set | `auth=None` (stdio transport) |
| Set | Set | `auth=GitHubProvider` (HTTP transport) |
| Set | Not set | `auth=None` (stdio transport) |
| Not set | Set | `auth=None` (stdio transport) |

### Security Model Layering

```
┌─────────────────────────────────────────────────────────┐
│                   Client Request                       │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 1: OAuth 2.1 (Transport Layer Security)      │
│ - Valid bearer token required                           │
│ - Prevents unauthorized HTTP access                      │
│ - Managed by FastMCP + GitHub OAuth                   │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 2: ADR-003 Whitelist (Code Level Security)     │
│ - 21 allowed modules (whitelist)                       │
│ - 28+ blocked modules (blacklist)                      │
│ - 11 dangerous built-ins blocked                        │
│ - AST bypass detection for 15+ patterns                 │
└────────────────────┬────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────┐
│ Layer 3: CrossHair Symbolic Execution (Core Logic)     │
│ - Formal verification of contracts                      │
│ - Counterexample generation                            │
│ - Path exploration                                    │
└─────────────────────────────────────────────────────────┘
```

**Rationale**: Defense-in-depth approach. Even if OAuth fails, ADR-003 prevents malicious code execution. Even if ADR-003 bypass is discovered, OAuth limits exposure to authenticated users.

---

## Appendix B: Stakeholder Feedback

| Stakeholder | Position | Feedback | Resolution |
|-------------|----------|-----------|------------|
| N/A | N/A | No external stakeholders for this decision | N/A |

---

## Appendix C: Compliance Matrix

| Standard/Requirement | Compliance Status | Notes |
|---------------------|-------------------|-------|
| FastMCP 2.0 Authentication | ✅ Compliant | Uses native GitHubProvider |
| FastMCP 2.0 HTTP Deployment | ✅ Compliant | OAuth ready for HTTP transport |
| FastMCP 2.0 Security Best Practices | ✅ Compliant | Authentication "highly recommended" |
| ADR-003 Security Model | ✅ Compliant | Layered security maintained |
| OAuth 2.1 Specification | ✅ Compliant | Delegated to GitHubProvider |
| Zero Code Changes (stdio ↔ HTTP) | ✅ Compliant | Environment-based configuration |
