"""V1 schema tree + parent-root resolution (LLD v1.2 §6, Plan E4).

The V1 hierarchy is the ordered `Level 1..8` path plus the `Node` role. Structural
`Root` rows carry occurrence and define container nodes; `Element` rows attach as
leaves under their container. Array/repeating nodes are flagged from a structural
node whose Max Occurrence is >1 or unbounded.

`resolve_parent_root` returns the nearest ancestor `Root` row for a field — used
by G1 step C ("immediate parent root Min Occurrence = 1") and by G2.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from app.domain.linkage import LinkIndex
from app.models.canonical import Occurs, V1Field


class TreeNode(BaseModel):
    name: str
    node_kind: Optional[str] = None
    min_occurs: Optional[int] = None
    max_occurs: Occurs = Field(default_factory=Occurs)
    is_array: bool = False
    children: list["TreeNode"] = Field(default_factory=list)
    leaves: list[V1Field] = Field(default_factory=list)
    # Gap rollup — populated by aggregate_gaps() once gaps exist (E3/E8).
    gap_count: int = 0
    gaps_by_type: dict[str, int] = Field(default_factory=dict)


TreeNode.model_rebuild()


def build_v1_tree(v1: list[V1Field]) -> TreeNode:
    root = TreeNode(name="(root)")
    index: dict[tuple[str, ...], TreeNode] = {(): root}

    for f in v1:
        cur = root
        prefix: tuple[str, ...] = ()
        for level in f.path:
            prefix = prefix + (level,)
            nxt = index.get(prefix)
            if nxt is None:
                nxt = TreeNode(name=level)
                cur.children.append(nxt)
                index[prefix] = nxt
            cur = nxt

        if (f.node_kind or "").casefold() == "element":
            cur.leaves.append(f)
        else:
            # Structural node: carry kind + occurrence + array flag
            cur.node_kind = f.node_kind or cur.node_kind
            if f.min_occurs is not None:
                cur.min_occurs = f.min_occurs
            if f.max_occurs.value is not None or f.max_occurs.unbounded:
                cur.max_occurs = f.max_occurs
            if f.max_occurs.is_array:
                cur.is_array = True
    return root


def resolve_parent_root(field: V1Field, idx: LinkIndex) -> Optional[V1Field]:
    """Logical parent Root for a field (LLD §6.2, confirmed decision D7).

    A field may be enclosed by a *chain* of nested Root nodes. We take the
    **outermost Root of the contiguous chain** that starts at the field's
    immediate parent Root and climbs while each ancestor is also a Root. This
    resolves to the logical entity root (e.g. an element under LEDetails(Root)
    whose parent LegalEntity is also Root -> LegalEntity)."""
    roots_by_depth: dict[int, V1Field] = {}
    for depth in range(len(field.path)):
        cand = idx.root_rows_by_path.get(tuple(field.path[: depth + 1]))
        if cand and (cand.node_kind or "").casefold() == "root":
            roots_by_depth[depth] = cand
    if not roots_by_depth:
        return None
    top = max(roots_by_depth)                    # immediate parent Root depth
    while (top - 1) in roots_by_depth:           # climb the contiguous Root chain
        top -= 1
    return roots_by_depth[top]                    # outermost (logical) Root


def find_node(root: TreeNode, path: list[str]) -> Optional[TreeNode]:
    """Walk the tree by Level path; None if any segment is missing."""
    cur = root
    for level in path:
        nxt = next((c for c in cur.children if c.name == level), None)
        if nxt is None:
            return None
        cur = nxt
    return cur


def aggregate_gaps(root: TreeNode, gaps) -> TreeNode:
    """Roll gap counts up the tree (T-E4.3). Each gap carries a root_node and,
    where available, the V1 source path. Counts accumulate on the owning node and
    every ancestor so a collapsed parent reflects its subtree. Called from E8 once
    gap records exist; tolerant of gaps that only know their root_node."""
    def bump(node: TreeNode, gap_type: str) -> None:
        node.gap_count += 1
        node.gaps_by_type[gap_type] = node.gaps_by_type.get(gap_type, 0) + 1

    for g in gaps:
        gap_type = getattr(g, "gap_type", None) or getattr(g, "type", "UNKNOWN")
        gap_type = str(getattr(gap_type, "value", gap_type))
        # Walk from the root along the gap's root_node (top Level) if present.
        rn = getattr(g, "root_node", None)
        bump(root, gap_type)
        if rn:
            child = next((c for c in root.children if c.name == rn), None)
            if child:
                bump(child, gap_type)
    return root
