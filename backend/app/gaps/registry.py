"""Gap engine registry + summary (LLD v1.2 §5, Plan T-E3.1)."""
from __future__ import annotations

from collections import defaultdict
from typing import Optional

from pydantic import BaseModel, Field

from app.domain.linkage import LinkIndex
from app.gaps import engines
from app.gaps.typemap import TypeMap
from app.models.gap import Gap, GapType

MANDATORY = {
    GapType.G1_COVERAGE: engines.run_g1,
    GapType.G2_OCCURRENCE: engines.run_g2,
    GapType.G3_DATATYPE: engines.run_g3,
    GapType.G4_MANDATORY: engines.run_g4,
}

OPTIONAL = {
    GapType.G5_REVERSE_ORPHAN: engines.run_g5,
    # G6..G9 land in Phase 1.5
}


def run_all(idx: LinkIndex, typemap: Optional[TypeMap] = None,
            enable_optional: bool = False) -> list[Gap]:
    funcs = list(MANDATORY.values())
    if enable_optional:
        funcs += list(OPTIONAL.values())
    gaps: list[Gap] = []
    for fn in funcs:
        gaps.extend(fn(idx, typemap))
    return gaps


class GapSummary(BaseModel):
    gap_type: str
    total: int
    by_status: dict[str, int] = Field(default_factory=dict)
    by_severity: dict[str, int] = Field(default_factory=dict)
    metrics: Optional[dict[str, int]] = None   # G1 A/B/C funnel


def summarize(gaps: list[Gap]) -> list[GapSummary]:
    by_type: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "status": defaultdict(int), "sev": defaultdict(int)}
    )
    g1 = {"total_missing": 0, "nullable_false": 0, "parent_min1": 0}
    for g in gaps:
        t = by_type[g.gap_type.value]
        t["total"] += 1
        t["status"][g.status.value] += 1
        t["sev"][g.severity.value] += 1
        if g.gap_type == GapType.G1_COVERAGE:
            g1["total_missing"] += 1
            g1["nullable_false"] += int(bool(g.flags.get("nullable_false")))
            g1["parent_min1"] += int(bool(g.flags.get("parent_root_min_occurs_1")))

    out: list[GapSummary] = []
    for t, d in by_type.items():
        out.append(GapSummary(
            gap_type=t, total=d["total"],
            by_status=dict(d["status"]), by_severity=dict(d["sev"]),
            metrics=g1 if t == GapType.G1_COVERAGE.value else None,
        ))
    out.sort(key=lambda s: s.gap_type)
    return out
