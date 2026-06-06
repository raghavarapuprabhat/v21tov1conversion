"""Comment threading + conversation assembly (LLD v1.2 §9.1, §8.4, Plan E6).

`assemble_thread` turns a flat comment list into a nested reply tree.
`build_conversation` returns a gap's own thread plus the IS-anchored "earlier
discussion" retained from any now-resolved gap for the same IS (F13).
"""
from __future__ import annotations

from collections import defaultdict

from app.models.collab import Comment, CommentNode, GapConversation


def assemble_thread(flat: list[Comment]) -> list[CommentNode]:
    by_parent: dict[str | None, list[Comment]] = defaultdict(list)
    for c in sorted(flat, key=lambda x: x.created_at):
        by_parent[c.parent_comment_id].append(c)

    def build(parent_id: str | None) -> list[CommentNode]:
        return [
            CommentNode(**c.model_dump(), replies=build(c.comment_id))
            for c in by_parent.get(parent_id, [])
        ]

    return build(None)


def build_conversation(repo, gap_id: str) -> GapConversation:
    exact, earlier = repo.conversation_parts(gap_id)
    gap = repo.get_gap(gap_id)
    return GapConversation(
        gap_id=gap_id,
        is_number=gap.is_number if gap else None,
        thread=assemble_thread(exact),
        earlier_for_is=assemble_thread(earlier),
    )
