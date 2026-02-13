# ADR-001: Unused Search Index Module

**Status:** Accepted (Decision: Retain for now with documentation)

**Date:** 2026-01-15

---

## Problem

The file `Utils/search_index.py` (349 lines) implements an inverted-index search system for fast resource lookup. However:

- **Not imported or used anywhere** in the codebase (verified via grep)
- Already marked "UNUSED" in the module docstring
- Was created as an optimization for large dataset search
- Current application uses simpler direct filtering in UI components instead
- Original author is no longer on the team

This creates potential confusion: "Is this code active? Should I maintain it?"

---

## Context

The `ResourceSearchIndex` class was designed to provide:
- Efficient full-text search with relevance scoring
- O(1) lookups via inverted index
- Thread-safe operations

However, the application evolved to use simpler, direct filtering that meets current performance needs. The code was retained as "potential future integration" if advanced search becomes necessary.

---

## Decision

**Keep the file for now** with explicit documentation via this ADR and existing comments.

### Rationale

1. **Low cost to keep**: One unused file is minimal maintenance burden
2. **Code preservation**: Git history preserves it; deletion is reversible but requires recovery effort
3. **Future optionality**: If advanced search is needed, this is a solid reference implementation
4. **Clear marking**: The file is already marked UNUSED in its docstring; this ADR makes the decision explicit

---

## Security Considerations

The unused `search_index.py` module relies solely on Python standard library modules (`threading`, `re`, `dataclasses`, `logging`) and presents minimal supply-chain risk. However, unused code can increase attack surface if external dependencies are introduced during future modifications. The module should be monitored for any additions that might introduce third-party libraries.

---

## Alternatives Considered

1. **Delete immediately**: Removes dead code but requires re-implementing if search needs evolve
2. **Archive to separate branch**: Adds process overhead but explicitly separates active from historical code
3. **Keep (chosen)**: Minimal overhead, preserves optionality, explicit documentation prevents confusion

---

## Action Items

- [x] Document in ADR (this file)
- [x] Verify no imports (completed)
- [ ] **Future**: If advanced search is needed, reference this module and `ResourceSearchIndex` class
  - **Owner**: Engineering Team Lead
  - **Timeline**: Ongoing, review during feature planning
- [ ] **Future**: If unused after 12+ months, delete and reference this ADR in commit message
  - **Owner**: Engineering Manager
  - **Timeline**: Review date: 2027-01-15 (12 months from ADR date)

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

- File: `Utils/search_index.py` (lines 1-8 contain UNUSED note)
- Application search: Uses direct filtering in UI components
- Git history: Full implementation preserved if needed
