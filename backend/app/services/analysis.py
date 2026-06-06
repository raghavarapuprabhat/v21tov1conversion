"""Analysis orchestration (Plan E3): ingestion output -> gaps + tree + summary.

Pure/deterministic; persistence (E5) and the API (E8) build on top of this.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.domain.linkage import LinkIndex, resolve_links
from app.domain.tree import TreeNode, aggregate_gaps, build_v1_tree
from app.gaps.registry import GapSummary, run_all, summarize
from app.gaps.typemap import TypeMap
from app.models.canonical import V1Field, V2Field
from app.models.gap import Gap


@dataclass
class AnalysisResult:
    idx: LinkIndex
    gaps: list[Gap]
    tree: TreeNode
    summary: list[GapSummary]


def analyze(v1: list[V1Field], v2: list[V2Field], typemap: TypeMap | None = None,
            enable_optional: bool = False) -> AnalysisResult:
    idx = resolve_links(v1, v2)
    gaps = run_all(idx, typemap, enable_optional=enable_optional)
    tree = build_v1_tree(v1)
    aggregate_gaps(tree, gaps)
    return AnalysisResult(idx=idx, gaps=gaps, tree=tree, summary=summarize(gaps))
