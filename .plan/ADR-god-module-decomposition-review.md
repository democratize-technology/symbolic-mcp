# ADR: God Module Decomposition Review

**Status**: APPROVED with observations
**Date**: 2026-02-23
**Decision Type**: Architecture Review
**Stakes**: Medium (affects maintainability and future extensibility)

## Summary

Reviewed the decomposition of a 1,975-line `main.py` God Module into a proper Python package structure with 9 modules totaling 2,234 lines.

## Pass/Fail Assessment

| Criterion | Status | Score | Notes |
|-----------|--------|-------|-------|
| Architectural Debt | PASS | 8.5/10 | Clean decomposition, minimal new debt |
| Integration Points | PASS | 9.0/10 | Well-defined module boundaries |
| Side Effects | PASS | 8.0/10 | Some observations below |
| Extensibility | PASS | 8.5/10 | Good foundation for future work |
| Test Coverage | PASS | 8.0/10 | 83.85% coverage, all 107 tests pass |

**Overall**: PASS - Ready for production use

## Detailed Analysis

### 1. Architectural Debt Assessment

**Score**: 8.5/10

**Positives**:
- No circular dependencies detected in import chain
- Clean layering: types -> config -> parsing/security -> analyzer -> tools -> server
- TypedDict definitions properly isolated with public aliases
- PEP 561 marker (`py.typed`) present for type consumers
- No TODO/FIXME/HACK comments left in codebase

**Minor Debt Introduced**:
- **Observation**: The stated dependency graph shows `parsing.py` depending on `types.py` and `config.py`, but actual implementation has zero internal dependencies. This is documented but slightly misleading.
- **Observation**: `_temporary_module` is exported from both `analyzer.py` (where it's defined) and implicitly via `SymbolicAnalyzer._temporary_module` as a static method. This pattern works but is unconventional.

**Recommendation**: Update the stated dependency graph to reflect reality:
```
types.py      <- (no dependencies)
config.py     <- (no dependencies, uses stdlib only)
parsing.py    <- (no dependencies)
security.py   <- types.py, config.py
analyzer.py   <- types.py, config.py, parsing.py, security.py
tools.py      <- types.py, config.py, security.py, analyzer.py
server.py     <- ALL modules (orchestrates everything)
__init__.py   <- server.py, tools.py, types.py, _version.py
```

### 2. Integration Points

**Score**: 9.0/10

**Module Boundaries**:
| Module | Responsibility | Exports | Coupling |
|--------|---------------|---------|----------|
| `types.py` | Type definitions | 13 TypedDicts + aliases | Zero (leaf) |
| `config.py` | Configuration, env vars, memory | Constants, `set_memory_limit()` | Zero (leaf) |
| `parsing.py` | Regex patterns, arg parsing | 3 patterns, 1 function | Zero (leaf) |
| `security.py` | AST validation, security constants | Constants, `validate_code()`, visitor | Low |
| `analyzer.py` | CrossHair integration, process isolation | `SymbolicAnalyzer`, `_temporary_module` | Medium |
| `tools.py` | Business logic for MCP tools | 4 `logic_*` functions | Medium |
| `server.py` | FastMCP setup, entry point | `mcp`, `main()`, tools, resources | High (expected) |

**Strengths**:
- Clear separation between business logic (`tools.py`) and MCP protocol (`server.py`)
- Security validation isolated in dedicated module
- Process isolation logic properly encapsulated in `analyzer.py`

**Single Point of Failure**: `server.py` has high coupling, but this is intentional and appropriate for an orchestrator module.

### 3. Side Effects Analysis

**Score**: 8.0/10

**Identified Side Effects**:

1. **Memory Limit on Import** (config.py:107)
   - `set_memory_limit(MEMORY_LIMIT_MB)` runs at module import time
   - Affects entire process, not just symbolic execution
   - **Risk**: Could interfere with host application if imported as library
   - **Mitigation**: Documented as expected behavior; appropriate for MCP server context

2. **sys.modules Lock** (config.py:90)
   - Global lock created at import time
   - Shared across all threads using `_temporary_module`
   - **Risk**: Potential contention under high concurrency
   - **Mitigation**: Lock scope is minimal (check-and-delete operations)

3. **Backward Compatibility Shim** (main.py)
   - Imports all internal symbols for test compatibility
   - Creates coupling between shim and all internal modules
   - **Risk**: Shim must be updated when internal exports change
   - **Mitigation**: Clear deprecation path documented

**No unintended consequences detected** in the decomposition itself.

### 4. Extensibility Assessment

**Score**: 8.5/10

**Easy to Extend**:
- Adding new MCP tools: Create `logic_*` function in `tools.py`, wrap in `server.py`
- Adding new TypedDicts: Add to `types.py` with public alias
- Adding new validation rules: Extend `_DangerousCallVisitor` in `security.py`
- Adding new analysis modes: Extend `SymbolicAnalyzer` in `analyzer.py`

**Potential Friction Points**:
- `_temporary_module` sharing between analyzer and tools requires awareness
- CrossHair integration is tightly coupled to `analyzer.py` design
- Symbolic execution timeout handling is distributed across multiple layers

**Recommended Future Improvements**:
1. Extract `_temporary_module` to a dedicated `sandbox.py` module
2. Consider protocol/interface for analyzer abstraction
3. Add factory pattern for creating analyzers with different configurations

### 5. Test Coverage Assessment

**Score**: 8.0/10

**Coverage by Module**:
| Module | Coverage | Missing Lines |
|--------|----------|---------------|
| `__init__.py` | 100% | - |
| `_version.py` | 100% | - |
| `types.py` | 100% | - |
| `parsing.py` | 100% | - |
| `config.py` | 86.21% | Error handling paths |
| `analyzer.py` | 81.82% | Edge cases, error paths |
| `tools.py` | 82.31% | Error handling, edge cases |
| `security.py` | 79.04% | Complex visitor paths |
| `server.py` | 79.55% | Lifespan, error paths |

**Overall**: 83.85% (107 tests pass)

**Observations**:
- Tests still use `from main import ...` pattern via compatibility shim
- Tests exercise actual functionality, not just mocks
- Missing coverage primarily in error handling and edge cases
- No tests specifically for new module boundaries

**Recommendation**: Add integration tests that verify module boundary integrity (e.g., ensure `parsing.py` can be imported without `types.py`).

## Key Decisions Validated

1. **Kept `_temporary_module` in analyzer.py** - APPROVED
   - Rationale: Primarily used by analyzer, tools only needs it for direct module access
   - Alternative considered: Extract to `sandbox.py` module
   - Decision: Acceptable for current scope; document for future refactoring

2. **Created backward compatibility shim at root main.py** - APPROVED
   - Rationale: Maintains existing test suite without modification
   - Risk: Tests don't exercise new import paths
   - Recommendation: Migrate tests to `from symbolic_mcp import ...` in future

3. **Public type aliases alongside private TypedDict names** - APPROVED
   - Pattern: `_Counterexample` (private) vs `Counterexample` (public alias)
   - Benefit: Allows internal refactoring without breaking public API
   - Consistency: Applied across all 13 TypedDicts

4. **Entry point changed to `symbolic_mcp.server:main`** - APPROVED
   - pyproject.toml correctly configured
   - Backward compatibility maintained via main.py shim

## Risks and Monitoring

### What Could Go Wrong

1. **Memory limit affects host process** (Low risk)
   - Detection: Host application OOM errors when importing symbolic_mcp
   - Mitigation: Document limitation; consider lazy initialization

2. **Lock contention under load** (Low risk)
   - Detection: Slowdown in concurrent analysis scenarios
   - Mitigation: Monitor lock hold times; consider lock-free patterns

3. **Shim drift from internals** (Medium risk)
   - Detection: Import errors when using old import paths
   - Mitigation: Add CI check that shim exports match internal exports

### Monitoring Recommendations

- Add metrics for `_SYS_MODULES_LOCK` contention
- Track temporary file cleanup success rate
- Monitor analysis process spawn/failure rates

## Conclusion

The God Module decomposition is well-executed with clean module boundaries, proper separation of concerns, and no circular dependencies. The architecture is appropriate for an MCP server providing symbolic execution capabilities.

**Recommendation**: APPROVE for production use with minor documentation updates.

## Action Items

1. [ ] Update dependency graph documentation to match actual implementation
2. [ ] Add integration test verifying module boundary integrity
3. [ ] Document memory limit side effect in README
4. [ ] Consider future extraction of `_temporary_module` to dedicated module
5. [ ] Plan gradual migration of tests from shim imports to package imports
