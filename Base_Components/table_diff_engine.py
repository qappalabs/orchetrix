"""
Pure-logic diff engine for QTableWidget-based resource pages.

Computes the minimal set of insert/remove/modify operations needed to
transition a table from one data state to another.  Zero Qt dependencies
— all inputs and outputs are plain Python dicts, sets, and lists.

This module is designed to be:
  1. Independently unit-testable without a running Qt application.
  2. Executable in a background thread (no GUI calls).
  3. Consumed by BaseResourcePage._apply_watch_update() which translates
     DiffResult operations into surgical QTableWidget mutations on the
     main GUI thread.

Usage:
    old_cache = RowCache()
    old_cache.rebuild(resources, project_fn)

    new_cache = RowCache()
    new_cache.rebuild(new_resources, project_fn)

    diff = compute_diff(old_cache, new_cache)
    # diff.removed  → list of (uid, old_row_index)
    # diff.added    → list of (uid, projected_row_dict)
    # diff.modified → list of (uid, old_row_index, changed_keys)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
)


# Keys in a projected row dict that hold internal metadata and should
# NOT be compared when deciding whether a row has visually changed.
# "uid" is the identity key; "_raw" is the original K8s payload kept
# only for detail-view lookups.
INTERNAL_KEYS: FrozenSet[str] = frozenset({"uid", "_raw"})


@dataclass(frozen=True)
class RemovedRow:
    """A row that existed in the old state but is absent in the new state."""
    uid: str
    old_index: int  # row index in old_uids order


@dataclass(frozen=True)
class AddedRow:
    """A row that exists in the new state but was absent in the old state."""
    uid: str
    data: Dict[str, Any]  # projected row dict


@dataclass(frozen=True)
class ModifiedRow:
    """A row present in both states whose visible data has changed."""
    uid: str
    old_index: int        # row index in old_uids order
    changed_keys: Tuple[str, ...]  # which projected keys mutated
    new_data: Dict[str, Any]       # full new projected row dict


@dataclass
class DiffResult:
    """The computed difference between two RowCache snapshots.

    Operations should be applied in order:
      1. removed  (highest index first to preserve lower indices)
      2. modified (in-place updates, indices still valid after removals
                   are processed top-down)
      3. added    (appended or inserted at the end)

    Attributes:
        removed:      rows to delete, sorted by old_index DESCENDING
        modified:     rows to update in-place
        added:        rows to insert
        is_full_reset: True when the diff is large enough that a full
                       clear-and-rebuild is more efficient
    """
    removed: List[RemovedRow] = field(default_factory=list)
    modified: List[ModifiedRow] = field(default_factory=list)
    added: List[AddedRow] = field(default_factory=list)
    is_full_reset: bool = False

    @property
    def is_empty(self) -> bool:
        return not self.removed and not self.modified and not self.added

    @property
    def total_operations(self) -> int:
        return len(self.removed) + len(self.modified) + len(self.added)


class RowCache:
    """UID-keyed cache of projected row data.

    Maintains two structures:
      - _data:  dict[uid → projected_row_dict]
      - _uids:  list[uid] preserving insertion order (== table row order)

    The cache stores ONLY semantic data (name, status, age, namespace,
    etc).  It NEVER stores visual properties like colors or styles —
    those are resolved at render time by the existing widget/CSS
    infrastructure.
    """

    __slots__ = ("_data", "_uids")

    def __init__(self) -> None:
        self._data: Dict[str, Dict[str, Any]] = {}
        self._uids: List[str] = []

    # ── Public API ──────────────────────────────────────────────────

    def rebuild(
        self,
        resources: Sequence[Dict[str, Any]],
        project_fn: Callable[[Dict[str, Any]], Dict[str, Any]],
    ) -> None:
        """Replace the entire cache by projecting a list of resources.

        Args:
            resources: raw resource dicts from the API/watch.
            project_fn: function that extracts a flat row dict from a
                        raw resource.  MUST include a "uid" key.
        """
        data: Dict[str, Dict[str, Any]] = {}
        uids: List[str] = []
        seen: Set[str] = set()
        for resource in resources or []:
            row = project_fn(resource)
            uid = row.get("uid")
            if uid is None:
                continue  # skip resources without stable identity
            data[uid] = row
            if uid not in seen:
                seen.add(uid)
                uids.append(uid)
            # Handle duplicate UIDs: last-write-wins for data,
            # but don't duplicate in the uid list.
        self._data = data
        self._uids = uids

    @property
    def data(self) -> Dict[str, Dict[str, Any]]:
        return self._data

    @property
    def uids(self) -> List[str]:
        return self._uids

    @property
    def uid_set(self) -> Set[str]:
        return set(self._uids)

    def __len__(self) -> int:
        return len(self._uids)

    def __contains__(self, uid: str) -> bool:
        return uid in self._data

    def get(self, uid: str) -> Optional[Dict[str, Any]]:
        return self._data.get(uid)

    def snapshot(self) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
        """Return a shallow copy of (data_dict, uid_list) for diffing."""
        return dict(self._data), list(self._uids)


def _row_visually_changed(
    old_row: Dict[str, Any],
    new_row: Dict[str, Any],
    ignore_keys: FrozenSet[str] = INTERNAL_KEYS,
) -> Tuple[str, ...]:
    """Compare two projected row dicts, ignoring internal metadata.

    Returns a tuple of key names that differ (empty tuple if identical).
    Only semantic/display keys are compared — visual properties like
    colors are resolved at render time, not cached.
    """
    all_keys = set(old_row.keys()) | set(new_row.keys())
    changed: List[str] = []
    for key in all_keys:
        if key in ignore_keys:
            continue
        if old_row.get(key) != new_row.get(key):
            changed.append(key)
    return tuple(changed)


# ── Volumetric threshold ────────────────────────────────────────────
# When the ratio of structural changes (inserts + deletes) to total
# rows exceeds this fraction, a full table rebuild is more efficient
# than emitting hundreds of individual row operations.  Each individual
# insertRow/removeRow call triggers Qt layout recalculation; beyond
# this threshold the accumulated layout overhead exceeds a single
# clear-and-rebuild.
DIFF_RESET_THRESHOLD: float = 0.5


def compute_diff(
    old_cache: RowCache,
    new_cache: RowCache,
    *,
    reset_threshold: float = DIFF_RESET_THRESHOLD,
) -> DiffResult:
    """Compute the minimal diff between two cache snapshots.

    Args:
        old_cache: the current state of the table.
        new_cache: the incoming state from the watch/API.
        reset_threshold: fraction of structural change above which
                         we flag is_full_reset=True.

    Returns:
        DiffResult with removed/modified/added operations.
    """
    # ── Edge cases ──────────────────────────────────────────────────
    if len(old_cache) == 0:
        # First load: everything is new.  Flag full reset so the
        # consumer uses the fast bulk-render path.
        return DiffResult(
            added=[AddedRow(uid=u, data=new_cache.get(u) or {}) for u in new_cache.uids],
            is_full_reset=True,
        )

    if len(new_cache) == 0:
        # Complete wipe.
        return DiffResult(
            removed=[
                RemovedRow(uid=u, old_index=i)
                for i, u in enumerate(old_cache.uids)
            ],
            is_full_reset=True,
        )

    # ── Set algebra ─────────────────────────────────────────────────
    old_set = old_cache.uid_set
    new_set = new_cache.uid_set

    removed_uids = old_set - new_set
    added_uids = new_set - old_set
    survived_uids = old_set & new_set

    # ── Volumetric guard ────────────────────────────────────────────
    size_basis = max(len(old_cache), len(new_cache))
    structural_change = len(removed_uids) + len(added_uids)
    if size_basis > 0 and (structural_change / size_basis) > reset_threshold:
        return DiffResult(
            added=[AddedRow(uid=u, data=new_cache.get(u) or {}) for u in new_cache.uids],
            is_full_reset=True,
        )

    # ── Order-only change detection ──────────────────────────────────
    # When no UIDs were added or removed but the sequence order differs,
    # signal a full reset so the consumer re-applies the new row order.
    if not removed_uids and not added_uids and old_cache.uids != new_cache.uids:
        return DiffResult(
            added=[AddedRow(uid=u, data=new_cache.get(u) or {}) for u in new_cache.uids],
            is_full_reset=True,
        )

    # ── Build operation lists ───────────────────────────────────────

    # Removals: sorted by old index DESCENDING so higher indices are
    # removed first, preserving the validity of lower indices.
    old_uid_index = {uid: idx for idx, uid in enumerate(old_cache.uids)}
    removed = sorted(
        [RemovedRow(uid=u, old_index=old_uid_index[u]) for u in removed_uids],
        key=lambda r: r.old_index,
        reverse=True,
    )

    # Post-removal index for surviving rows: each removal shifts
    # subsequent survivors up by one position.
    survived_index = {}
    offset = 0
    for idx, uid in enumerate(old_cache.uids):
        if uid in removed_uids:
            offset += 1
        else:
            survived_index[uid] = idx - offset

    # Modifications: compare each surviving row.
    modified: List[ModifiedRow] = []
    for uid in survived_uids:
        old_row = old_cache.get(uid)
        new_row = new_cache.get(uid)
        if old_row is None or new_row is None:
            continue
        changed = _row_visually_changed(old_row, new_row)
        if changed:
            modified.append(ModifiedRow(
                uid=uid,
                old_index=survived_index[uid],
                changed_keys=changed,
                new_data=new_row,
            ))

    # Additions: preserve the order from new_cache.
    added = [
        AddedRow(uid=u, data=new_cache.get(u) or {})
        for u in new_cache.uids
        if u in added_uids
    ]

    return DiffResult(
        removed=removed,
        modified=modified,
        added=added,
        is_full_reset=False,
    )
