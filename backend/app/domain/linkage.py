"""Per-context linkage resolver (LLD v1.2 §4, Plan T-E2.2/T-E2.3).

Each V2.1 row contributes up to three context-tagged edges (Entity / RP_IND /
RP_ORG), each pointing at a possibly different V1 IS Reference Number. Three
different IS across one row's three columns is expected, not a conflict.

`LinkIndex` precomputes the lookups the gap engines (E3) consume.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field

from app.models.canonical import Linkage, V1Field, V2Field


@dataclass
class LinkIndex:
    v1_by_is: dict[str, V1Field] = field(default_factory=dict)
    v1_is_set: set[str] = field(default_factory=set)
    linkages: list[Linkage] = field(default_factory=list)
    links_by_is: dict[str, list[Linkage]] = field(default_factory=dict)
    v2_mapped_is: set[str] = field(default_factory=set)
    v2_by_dd: dict[str, list[V2Field]] = field(default_factory=dict)
    v1_by_dd: dict[str, list[V1Field]] = field(default_factory=dict)
    # Root rows keyed by their full Level path tuple (used by the E4 parent-root
    # resolver and G1/G2). Built here because it is a pure index over V1 rows.
    root_rows_by_path: dict[tuple[str, ...], V1Field] = field(default_factory=dict)

    # --- convenience views the gap engines build on -------------------------
    def missing_in_v2(self) -> set[str]:
        """G1 set A: IS in V1 not referenced by any V2 mapping context."""
        return self.v1_is_set - self.v2_mapped_is

    def reverse_orphans(self) -> set[str]:
        """G5: IS referenced by V2 mappings but absent from V1 (e.g. IS2339)."""
        return self.v2_mapped_is - self.v1_is_set

    def orphan_links(self) -> list[Linkage]:
        return [lk for lk in self.linkages if lk.is_orphan]

    def resolved_links(self) -> list[Linkage]:
        return [lk for lk in self.linkages if not lk.is_orphan]


def resolve_links(v1: list[V1Field], v2: list[V2Field]) -> LinkIndex:
    # V1 index by IS (first occurrence wins; duplicates are flagged in DQ/G9)
    v1_by_is: dict[str, V1Field] = {}
    for f in v1:
        if f.is_number and f.is_number not in v1_by_is:
            v1_by_is[f.is_number] = f

    linkages: list[Linkage] = []
    links_by_is: dict[str, list[Linkage]] = defaultdict(list)
    v2_mapped_is: set[str] = set()
    for row in v2:
        for context, isn in row.mapped_is().items():
            v2_mapped_is.add(isn)
            lk = Linkage(is_number=isn, context=context, v2=row, v1=v1_by_is.get(isn))
            linkages.append(lk)
            links_by_is[isn].append(lk)

    v2_by_dd: dict[str, list[V2Field]] = defaultdict(list)
    for row in v2:
        if row.dd_ref:
            v2_by_dd[row.dd_ref].append(row)

    v1_by_dd: dict[str, list[V1Field]] = defaultdict(list)
    for f in v1:
        if f.dd_ref:
            v1_by_dd[f.dd_ref].append(f)

    root_rows_by_path: dict[tuple[str, ...], V1Field] = {}
    for f in v1:
        if (f.node_kind or "").casefold() == "root":
            root_rows_by_path[tuple(f.path)] = f

    return LinkIndex(
        v1_by_is=v1_by_is,
        v1_is_set=set(v1_by_is),
        linkages=linkages,
        links_by_is=dict(links_by_is),
        v2_mapped_is=v2_mapped_is,
        v2_by_dd=dict(v2_by_dd),
        v1_by_dd=dict(v1_by_dd),
        root_rows_by_path=root_rows_by_path,
    )
