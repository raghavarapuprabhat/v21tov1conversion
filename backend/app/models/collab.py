"""Collaboration models — comments, status history, saved views (LLD §2.3, §8.3)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field

from app.models.canonical import MappingContext
from app.models.gap import GapStatus


class Comment(BaseModel):
    comment_id: str = ""                       # repo generates when empty
    gap_id: Optional[str] = None              # may be None if the gap is resolved (F13)
    is_anchor: Optional[str] = None           # IS Reference Number — durable retention hook
    mapping_context: Optional[MappingContext] = None
    parent_comment_id: Optional[str] = None   # None = root thread; else a reply
    author: str
    body: str
    created_at: str = ""                        # ISO-8601; repo sets when empty


class StatusChange(BaseModel):
    gap_id: str
    old_status: Optional[GapStatus] = None
    new_status: GapStatus
    author: str
    note: Optional[str] = None
    changed_at: str


class SavedView(BaseModel):
    view_id: str
    name: str
    owner: Optional[str] = None
    spec: dict[str, Any] = Field(default_factory=dict)   # {filters, columns, sort}


class CommentNode(Comment):
    """A comment with its nested replies (Facebook-style thread, LLD §9.1)."""
    replies: list["CommentNode"] = Field(default_factory=list)


CommentNode.model_rebuild()


class GapConversation(BaseModel):
    """A gap's discussion: its own thread plus any earlier discussion retained
    for the same IS Reference Number from a now-resolved gap (F13, LLD §8.4)."""
    gap_id: str
    is_number: Optional[str] = None
    thread: list[CommentNode] = Field(default_factory=list)
    earlier_for_is: list[CommentNode] = Field(default_factory=list)


class ReingestSummary(BaseModel):
    """Reported after a (re)load — how the new dataset relates to the prior one."""
    new: int = 0
    unchanged: int = 0
    resolved_retained: int = 0       # gaps that vanished; their discussion is kept
    comments_retained: int = 0       # total comments on disk (never decreases)
