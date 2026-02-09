# Technical Debt Notes

This document tracks technical debt and cargo cult code identified in the codebase.

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
