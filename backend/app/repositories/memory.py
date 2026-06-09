"""In-memory repository with durable SQLite snapshot (LLD v1.2 §8.2, Plan E5).

Gaps/fields/tree live in RAM (recomputed from Excel each load); statuses,
history, comments and saved views persist via `SnapshotStore`. On load, persisted
statuses are re-applied onto the freshly computed gaps by `gap_id`.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from app.domain.tree import TreeNode
from app.gaps.registry import GapSummary, summarize
from app.ingestion import normalize as N
from app.models.canonical import V2Field
from app.models.collab import Comment, ReingestSummary, SavedView, StatusChange
from app.models.gap import Gap, GapStatus
from app.repositories.base import GapPage, GapQuery
from app.repositories.snapshot import SnapshotStore

_SEVERITY_RANK = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}


class InMemoryRepository:
    def __init__(self, snapshot_path: str):
        self.snap = SnapshotStore(snapshot_path)
        self._gaps: dict[str, Gap] = {}
        self._order: list[str] = []
        self._summary: list[GapSummary] = []
        self._tree: TreeNode = TreeNode(name="(root)")
        self._v2_by_dd: dict[str, list[V2Field]] = {}
        self._v1: list = []
        self._v2: list = []
        self._disabled: set[str] = set()

    # --- dataset --------------------------------------------------------------
    def load(self, v1, v2, result) -> ReingestSummary:
        old_ids = set(self._gaps)               # previously loaded gaps (F13)
        self._v1, self._v2 = v1, v2
        self._gaps = {g.gap_id: g for g in result.gaps}
        self._order = [g.gap_id for g in result.gaps]
        self._tree = result.tree
        self._v2_by_dd = result.idx.v2_by_dd
        self._disabled = set(getattr(result, "disabled", set()) or set())
        # Re-apply persisted statuses onto the freshly computed gaps (by gap_id)
        for gid, status in self.snap.all_statuses().items():
            g = self._gaps.get(gid)
            if g:
                g.status = GapStatus(status)
        self._refresh_summary()

        new_ids = set(self._gaps)
        summary = ReingestSummary(
            new=len(new_ids - old_ids),
            unchanged=len(new_ids & old_ids),
            resolved_retained=len(old_ids - new_ids),   # vanished; discussion kept
            comments_retained=self.snap.count_comments(),
        )
        self._last_reingest = summary
        return summary

    def _refresh_summary(self) -> None:
        self._summary = summarize(list(self._gaps.values()), self._disabled)

    # --- queries --------------------------------------------------------------
    def summary(self) -> list[GapSummary]:
        return self._summary

    def get_gap(self, gap_id: str) -> Optional[Gap]:
        return self._gaps.get(gap_id)

    def tree(self) -> TreeNode:
        return self._tree

    def v2_by_dd(self, dd: str) -> list[V2Field]:
        return self._v2_by_dd.get(N.norm_code(dd) or "", [])

    def query_gaps(self, q: GapQuery) -> GapPage:
        rows = [self._gaps[gid] for gid in self._order]
        rows = [g for g in rows if self._match(g, q)]
        if q.sort:
            rows = self._sort(rows, q.sort)
        total = len(rows)
        start = max(0, (q.page - 1) * q.page_size)
        return GapPage(page=q.page, page_size=q.page_size, total=total,
                       rows=rows[start:start + q.page_size])

    def facets(self, gap_type: Optional[str]) -> dict:
        """Distinct IS numbers and paths (optionally scoped to a gap type) for the
        multi-select column filters. Cheap at ~700-800 rows."""
        iss: set[str] = set()
        paths: set[str] = set()
        for g in self._gaps.values():
            if gap_type and g.gap_type.value != gap_type:
                continue
            if g.is_number:
                iss.add(g.is_number)
            if g.v1_path:
                paths.add(g.v1_path)
        return {"is_numbers": sorted(iss), "paths": sorted(paths)}

    def v1_gap_index(self) -> dict:
        """Map each V1 source row -> {count, open} for the V1 sheet's Gap column
        and row highlighting. One pass over the gaps."""
        idx: dict[str, dict] = {}
        for g in self._gaps.values():
            if g.v1_ref is None or g.v1_ref.row is None:
                continue
            e = idx.setdefault(str(g.v1_ref.row), {"count": 0, "open": 0})
            e["count"] += 1
            if g.status == GapStatus.OPEN:
                e["open"] += 1
        return idx

    @staticmethod
    def _match(g: Gap, q: GapQuery) -> bool:
        ctx = g.mapping_context.value if g.mapping_context else None

        def contains(needle: Optional[str], hay: Optional[str]) -> bool:
            return not needle or needle.casefold() in (hay or "").casefold()

        # exact-match column filters
        if q.gap_type and g.gap_type.value != q.gap_type:
            return False
        if q.status and g.status.value != q.status:
            return False
        if q.severity and g.severity.value != q.severity:
            return False
        if q.context and ctx != q.context:
            return False
        if q.dd_in_v2 is not None and g.dd_in_v2 != q.dd_in_v2:
            return False
        if q.nullable is not None and g.nullable != q.nullable:
            return False
        if q.v1_row is not None and (g.v1_ref is None or g.v1_ref.row != q.v1_row):
            return False
        if q.root_node and g.root_node != q.root_node:
            return False
        # multi-select (any-of) column filters
        if q.is_in and g.is_number not in q.is_in:
            return False
        if q.path_in and g.v1_path not in q.path_in:
            return False
        # multi-select (none-of) — Select-All with a few deselected
        if q.is_not_in and g.is_number in q.is_not_in:
            return False
        if q.path_not_in and g.v1_path in q.path_not_in:
            return False
        # contains column filters
        if not contains(q.is_number, g.is_number):
            return False
        if not contains(q.v1, g.v1_value):
            return False
        if not contains(q.v2, g.v2_value):
            return False
        if not contains(q.detail, g.detail):
            return False
        if not contains(q.dd, g.dd_ref):
            return False
        # global search
        if q.search:
            hay = " ".join(filter(None, [
                g.is_number, g.detail, g.v1_value, g.v2_value, g.dd_ref,
            ])).casefold()
            if q.search.casefold() not in hay:
                return False
        return True

    @staticmethod
    def _sort(rows: list[Gap], sort: str) -> list[Gap]:
        desc = sort.startswith("-")
        field = sort[1:] if desc else sort

        def key(g: Gap):
            if field == "severity":
                return _SEVERITY_RANK.get(g.severity.value, 99)
            return str(getattr(g, field, "") or "")

        return sorted(rows, key=key, reverse=desc)

    # --- status (persisted) ---------------------------------------------------
    def set_status(self, gap_id: str, status: str, author: str,
                   note: Optional[str] = None) -> Gap:
        g = self._gaps.get(gap_id)
        if g is None:
            raise KeyError(gap_id)
        new = GapStatus(status)
        old = g.status
        g.status = new
        self.snap.set_status(gap_id, new.value)
        self.snap.add_history(gap_id, old.value, new.value, author, note)
        self._refresh_summary()
        return g

    def bulk_status(self, gap_ids: list[str], status: str, author: str,
                    note: Optional[str] = None) -> int:
        n = 0
        for gid in gap_ids:
            if gid in self._gaps:
                self.set_status(gid, status, author, note)
                n += 1
        return n

    def status_history(self, gap_id: str) -> list[StatusChange]:
        return [
            StatusChange(
                gap_id=r["gap_id"], old_status=r["old_status"], new_status=r["new_status"],
                author=r["author"], note=r["note"], changed_at=r["changed_at"],
            )
            for r in self.snap.history(gap_id)
        ]

    # --- comments (basic persistence; threading + F13 retrieval in E6) --------
    def add_comment(self, c: Comment) -> Comment:
        if not c.comment_id:
            c = c.model_copy(update={"comment_id": "c_" + uuid.uuid4().hex[:12]})
        if not c.created_at:
            c = c.model_copy(update={"created_at": datetime.now(timezone.utc).isoformat()})
        # default the durable IS anchor from the gap when not supplied
        if c.is_anchor is None and c.gap_id and c.gap_id in self._gaps:
            c = c.model_copy(update={"is_anchor": self._gaps[c.gap_id].is_number})
        self.snap.add_comment({
            "comment_id": c.comment_id, "gap_id": c.gap_id, "is_anchor": c.is_anchor,
            "mapping_context": c.mapping_context.value if c.mapping_context else None,
            "parent_comment_id": c.parent_comment_id, "author": c.author,
            "body": c.body, "created_at": c.created_at,
        })
        return c

    def list_comments(self, gap_id: str) -> list[Comment]:
        return [Comment(**r) for r in self.snap.comments_for_gap(gap_id)]

    def conversation_parts(self, gap_id: str) -> tuple[list[Comment], list[Comment]]:
        """(thread, earlier_for_is) — F13 retention retrieval (LLD §8.4).

        `thread` = comments on this exact gap. `earlier_for_is` = comments sharing
        this gap's IS Reference Number whose own gap is no longer current (a gap
        resolved/removed by a re-upload), surfaced as "Earlier discussion for IS".
        """
        exact = [Comment(**r) for r in self.snap.comments_for_gap(gap_id)]
        earlier: list[Comment] = []
        gap = self._gaps.get(gap_id)
        if gap and gap.is_number:
            for r in self.snap.comments_for_anchor(gap.is_number):
                if r["gap_id"] != gap_id and r["gap_id"] not in self._gaps:
                    earlier.append(Comment(**r))
        return exact, earlier

    def last_reingest(self) -> Optional[ReingestSummary]:
        return getattr(self, "_last_reingest", None)

    # --- saved views ----------------------------------------------------------
    def save_view(self, v: SavedView) -> SavedView:
        if not v.view_id:
            v = v.model_copy(update={"view_id": "v_" + uuid.uuid4().hex[:12]})
        self.snap.save_view(v.view_id, v.name, v.owner, v.spec)
        return v

    def list_views(self) -> list[SavedView]:
        return [SavedView(**r) for r in self.snap.list_views()]

    def close(self) -> None:
        self.snap.close()
