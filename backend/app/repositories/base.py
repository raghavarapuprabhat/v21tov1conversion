"""Repository interface + query/page types (LLD v1.2 §8.1)."""
from __future__ import annotations

from typing import Optional, Protocol

from pydantic import BaseModel

from app.domain.tree import TreeNode
from app.gaps.registry import GapSummary
from app.models.canonical import V2Field
from app.models.collab import Comment, ReingestSummary, SavedView, StatusChange
from app.models.gap import Gap


class GapQuery(BaseModel):
    gap_type: Optional[str] = None       # exact (column filter: Type)
    status: Optional[str] = None         # exact (column filter: Status)
    severity: Optional[str] = None       # exact (column filter: Severity)
    context: Optional[str] = None        # exact (column filter: Context)
    is_number: Optional[str] = None      # contains (legacy single IS)
    is_in: Optional[list[str]] = None    # any-of (multi-select column filter: IS)
    path_in: Optional[list[str]] = None  # any-of (multi-select column filter: Path)
    is_not_in: Optional[list[str]] = None    # none-of (Select-All minus a few: IS)
    path_not_in: Optional[list[str]] = None  # none-of (Select-All minus a few: Path)
    v1: Optional[str] = None             # contains (column filter: V1)
    v2: Optional[str] = None             # contains (column filter: V2.1)
    detail: Optional[str] = None         # contains (column filter: Detail)
    dd: Optional[str] = None             # contains (column filter: DD)
    dd_in_v2: Optional[bool] = None      # exact (column filter: DD in V2)
    nullable: Optional[bool] = None      # exact (column filter: Nullable, G1)
    v1_row: Optional[int] = None         # exact (gaps anchored to a V1 sheet row)
    root_node: Optional[str] = None
    search: Optional[str] = None         # global contains across fields
    sort: Optional[str] = None           # field name, '-' prefix = descending
    page: int = 1
    page_size: int = 50


class GapPage(BaseModel):
    page: int
    page_size: int
    total: int
    rows: list[Gap]


class Repository(Protocol):
    def load(self, v1, v2, result) -> ReingestSummary: ...
    def summary(self) -> list[GapSummary]: ...
    def query_gaps(self, q: GapQuery) -> GapPage: ...
    def facets(self, gap_type: Optional[str]) -> dict: ...
    def v1_gap_index(self) -> dict: ...
    def get_gap(self, gap_id: str) -> Optional[Gap]: ...
    def set_status(self, gap_id: str, status: str, author: str,
                   note: Optional[str] = None) -> Gap: ...
    def bulk_status(self, gap_ids: list[str], status: str, author: str,
                    note: Optional[str] = None) -> int: ...
    def status_history(self, gap_id: str) -> list[StatusChange]: ...
    def add_comment(self, c: Comment) -> Comment: ...
    def list_comments(self, gap_id: str) -> list[Comment]: ...
    def conversation_parts(self, gap_id: str) -> tuple[list[Comment], list[Comment]]: ...
    def tree(self) -> TreeNode: ...
    def v2_by_dd(self, dd: str) -> list[V2Field]: ...
    def list_views(self) -> list[SavedView]: ...
    def save_view(self, v: SavedView) -> SavedView: ...
    def close(self) -> None: ...
