# ADR-002: Unused Performance Configuration Module

**Status:** Accepted (Decision: Retain for now with documentation)

**Date:** 2026-01-15

---

## Problem

The file `Utils/performance_config.py` (120+ lines) implements centralized performance settings for UI responsiveness, memory management, and data loading optimizations. However:

- **Not imported or used anywhere** in the codebase (verified via grep)
- Already marked "UNUSED" in the module docstring (lines 3-7)
- Was created as an attempt to centralize performance settings
- Current application uses direct constants in individual files instead (e.g., BATCH_SIZE in base_resource_page.py)
- Approach was abandoned in favor of simpler, directly-defined constants

This creates potential confusion: "Is this code active? Should I maintain it?"

---

## Context

The `performance_config.py` module was designed to provide:
- Centralized performance configuration with multiple profiles (high_performance, balanced, responsive)
- Adaptive optimization based on system resources (CPU, memory)
- Constants for table rendering, data loading, graph updates, memory management, UI responsiveness, and thread management

However, the application evolved to use simpler, direct constants defined in individual files that meet current performance needs. The code was retained as "potential future integration" if centralized performance management becomes necessary.

---

## Decision

**Keep the file for now** with explicit documentation via this ADR and existing comments.

### Rationale

1. **Low cost to keep**: One unused file is minimal maintenance burden
2. **Code preservation**: Git history preserves it; deletion is reversible but requires recovery effort
3. **Future optionality**: If centralized performance config is needed, this is a solid reference implementation
4. **Clear marking**: The file is already marked UNUSED in its docstring; this ADR makes the decision explicit

---

## Alternatives Considered

1. **Delete immediately**: Removes dead code but requires re-implementing if performance config needs evolve
2. **Archive to separate branch**: Adds process overhead but explicitly separates active from historical code
3. **Keep (chosen)**: Minimal overhead, preserves optionality, explicit documentation prevents confusion

---

## Action Items

- [x] Document in ADR (this file)
- [x] Verify no imports (completed - 0 references found)
- [x] Make psutil an optional dependency with graceful fallback (implemented 2026-01-15)
- [ ] **Future**: If centralized performance config is needed, reference this module and functions
- [ ] **Future**: If unused after 12+ months, delete and reference this ADR in commit message

## Dependency Management

**psutil Handling Strategy (2026-01-15):**
- Made psutil an optional dependency in `performance_config.py`
- Added graceful fallback in `apply_performance_optimizations()` function when psutil is not available
- Commented out psutil in requirements.txt with explanation
- Reduces install bloat while preserving functionality for users who install psutil
- No breaking changes - existing installations continue to work

---

## Consequences

**Positive:**
- Zero deletion risk
- Preserves code if direction changes
- ADR provides context for future developers

**Negative:**
- Unused code remains in repository
- Must remain documented to avoid confusion

---

## Related References

- File: `Utils/performance_config.py` (lines 1-8 contain UNUSED note)
- Application performance: Uses direct constants in individual components
- Git history: Full implementation preserved if needed
- ADR-001: Similar decision for unused search index module
