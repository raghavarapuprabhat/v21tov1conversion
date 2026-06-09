"""Gap engine registry + summary (LLD v1.2 §5, Plan T-E3.1)."""
from __future__ import annotations

import re
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
    GapType.G6_DD_MISMATCH: engines.run_g6,
}

# Optional engines that take (idx, typemap). G9 is handled separately because it
# consumes the ingestion data-quality findings rather than the link index.
OPTIONAL = {
    GapType.G5_REVERSE_ORPHAN: engines.run_g5,
    GapType.G7_CARDINALITY: engines.run_g7,
    GapType.G8_DUP_MAPPING: engines.run_g8,
}


def run_all(idx: LinkIndex, typemap: Optional[TypeMap] = None,
            enable_optional: bool = False, dq_findings=None,
            disabled: Optional[set[str]] = None) -> list[Gap]:
    off = disabled or set()
    gaps: list[Gap] = []
    for gt, fn in MANDATORY.items():
        if gt.value in off:
            continue
        gaps.extend(fn(idx, typemap))
    if enable_optional:
        for gt, fn in OPTIONAL.items():
            if gt.value in off:
                continue
            gaps.extend(fn(idx, typemap))
        if GapType.G9_DATA_QUALITY.value not in off:
            gaps.extend(engines.run_g9(dq_findings))   # G9 from ingestion findings
    return gaps


class GapSummary(BaseModel):
    gap_type: str
    total: int
    by_status: dict[str, int] = Field(default_factory=dict)
    by_severity: dict[str, int] = Field(default_factory=dict)
    metrics: Optional[dict[str, int]] = None   # G1 A/B/C funnel
    disabled: bool = False                      # engine turned off (card shown greyed)


def summarize(gaps: list[Gap], disabled: Optional[set[str]] = None) -> list[GapSummary]:
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

    off = disabled or set()
    out: list[GapSummary] = []
    for t, d in by_type.items():
        out.append(GapSummary(
            gap_type=t, total=d["total"],
            by_status=dict(d["status"]), by_severity=dict(d["sev"]),
            metrics=g1 if t == GapType.G1_COVERAGE.value else None,
            disabled=t in off,
        ))
    # keep disabled cards visible even though their engine produced no gaps
    present = {s.gap_type for s in out}
    for t in off:
        if t not in present:
            out.append(GapSummary(gap_type=t, total=0, disabled=True))
    out.sort(key=lambda s: _gap_order(s.gap_type))
    return out


def _gap_order(gap_type: str) -> tuple[int, str]:
    """Numeric by the G<n> code so G10/G11 follow G9 instead of sorting after G1."""
    m = re.match(r"G(\d+)", gap_type)
    return (int(m.group(1)) if m else 999, gap_type)
