# Technical Debt Notes

This document tracks technical debt and cargo cult code identified in the codebase.

## Test Infrastructure Over-Engineering

### Location
- `tests/integration/interfaces.py` (390 lines)
- `tests/integration/dependency_container.py` (354 lines)
- `tests/integration/request_executor.py` (283 lines)

### Issue
The integration tests use a custom dependency injection system with:
- Abstract interfaces for all main module dependencies
- A DI container with resolver patterns
- Request executor abstraction

This is over-engineered for what the tests need. Standard pytest fixtures with `unittest.mock` would be simpler and more maintainable.

### Impact
- Three files totaling ~1000 lines of complex DI infrastructure
- 9 test files depend on this system
- Makes tests harder to understand and modify
- Non-standard pattern that differs from typical pytest usage

### Resolution Path
1. **Future work**: Replace DI container with simple pytest fixtures
2. Use `unittest.mock.patch` for mocking dependencies
3. Use `@pytest.fixture` for shared test state
4. Pattern to follow:
   ```python
   @pytest.fixture
   def mock_symbolic_analyzer():
       with patch('main.SymbolicAnalyzer') as mock:
           mock.return_value = {"status": "complete", ...}
           yield mock
   ```

### Tests Using DI System
- `test_architectural_improvements.py`
- `test_crosshair_failure_harness.py`
- `test_failing_integration_tests.py`
- `test_load_harness.py`
- `test_e2e_harness.py`
- `test_memory_leak_detector.py`
- `test_security_harness.py`
- `test_runner.py`
- `conftest.py` (partial)

### Status
Documented for future refactoring. Not critical to fix immediately as the system works, but adds maintenance burden.

## Completed Cleanup (v0.1.1)

### Phase 1: Security Fixes ✅
- Added logging to silent exception blocks (7 locations)
- All security validators now log warnings instead of silently passing

### Phase 2: Dead Code Removal ✅
- Removed unused `DANGEROUS_AST_NODES` constant
- Removed dead debug code (`if hasattr(node, "lineno"): pass`)
- Removed unused `main()` function

### Phase 3: Import Fixes ✅
- Removed duplicate `from contextlib import asynccontextmanager`
- Changed to use `contextlib.asynccontextmanager` directly

### Phase 5: Vaporware Tests ✅
- Moved `tests/test_critical_vulnerability_demonstration.py` to `tests/demos/vulnerabilities.py`
- Renamed test methods to demo methods (won't be collected by pytest)
- Added README to explain these are demonstrations, not tests
- Deleted `tests/test_crosshair_section_5_1_compliance.py` (vaporware compliance test)
- Created `COMPLIANCE_NOTES.md` to track non-compliance items

### Phase 6: Orphaned Scripts ✅
- Deleted `scripts/verify-dependabot-config.py` (vaporware - checked for non-existent workflows)
- Created `scripts/README.md` to document remaining scripts

### Phase 7: Pointless Cleanup ✅
- Removed meaningless `finally` block that just did `analyzer = None`
- Python's GC handles this automatically

### Phase 8: Unused Variable Removal ✅ (2026-02-09)
- **TD-SYM-002**: Removed unused `start_time` variable in `logic_find_path_to_exception()`
- Variable was assigned but never used; timing comes from analyzer result instead
- Location: main.py:1115 (removed)

### Phase 9: Dead Code Removal ✅ (2026-02-09)
- **TD-SYM-001**: Removed `_extract_function_signature()` function (39 lines)
- Function was replaced by more efficient `_extract_function_signature_and_params()`
- Removed stale docstring reference in `_extract_function_signature_and_params()`
- Total: ~40 lines removed
