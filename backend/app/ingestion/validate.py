"""Validation & data-quality report (LLD v1.2 §3.3, Plan T-E1.4).

Produces an ingestion report with data-quality findings. Checks are grounded in
anomalies actually present in the sample data (sentinel casing like
'Not APplicable', attribute names containing spaces, duplicate IS numbers).
Findings are surfaced to the user and later feed optional gap engine G9 — they
never block ingestion.
"""
from __future__ import annotations

from collections import Counter
from typing import Optional

from pydantic import BaseModel, Field

from app.ingestion import normalize as N
from app.models.canonical import V1Field, V2Field
from app.models.collab import ReingestSummary

# A sentinel written exactly like this is considered "clean"; other casings flag.
ACCEPTED_SENTINEL_FORMS = {"Not Applicable", "N/A"}


class DQFinding(BaseModel):
    code: str
    severity: str                  # low | medium | high
    sheet: str
    row: Optional[int] = None
    column: Optional[str] = None
    message: str
    raw: Optional[str] = None


class IngestionReport(BaseModel):
    v1_path: str
    v2_path: str
    v1_rows: int                   # canonical fields loaded from V1
    v2_rows: int                   # canonical fields loaded from V2.1
    v1_is_numbers: int             # rows carrying an IS Reference Number
    v2_mapping_links: int          # non-sentinel links across the 3 context columns
    findings_count: int = 0
    by_code: dict[str, int] = Field(default_factory=dict)
    findings: list[DQFinding] = Field(default_factory=list)
    reingest: Optional[ReingestSummary] = None   # set by bootstrap after repo.load (F13)


def _check_v1(v1: list[V1Field]) -> list[DQFinding]:
    out: list[DQFinding] = []
    seen: Counter[str] = Counter(f.is_number for f in v1 if f.is_number)
    dupes = {k for k, n in seen.items() if n > 1}
    for f in v1:
        if f.node_kind and f.node_kind.casefold() == "element" and not f.is_number:
            out.append(DQFinding(
                code="MISSING_IS_ON_ELEMENT", severity="medium",
                sheet=f.source.sheet, row=f.source.row,
                message="Element row has no IS Reference Number",
                raw=f.attribute,
            ))
        if f.is_number in dupes:
            out.append(DQFinding(
                code="DUPLICATE_IS", severity="high",
                sheet=f.source.sheet, row=f.source.row,
                message=f"IS Reference Number '{f.is_number}' appears more than once",
                raw=f.is_number_raw,
            ))
        if f.max_occurs.raw and f.max_occurs.value is None and not f.max_occurs.unbounded:
            out.append(DQFinding(
                code="UNPARSEABLE_MAX_OCCURS", severity="low",
                sheet=f.source.sheet, row=f.source.row,
                message="Max Occurrence is neither a number nor 'unbounded'",
                raw=f.max_occurs.raw,
            ))
    return out


def _check_v2(v2: list[V2Field]) -> list[DQFinding]:
    out: list[DQFinding] = []
    for f in v2:
        for raw in (f.map_entity_raw, f.map_rp_ind_raw, f.map_rp_org_raw):
            if raw and N.is_sentinel(raw) and raw not in ACCEPTED_SENTINEL_FORMS:
                out.append(DQFinding(
                    code="SENTINEL_CASING", severity="low",
                    sheet=f.source.sheet, row=f.source.row,
                    message=f"Non-standard 'not applicable' token: '{raw}'",
                    raw=raw,
                ))
        if f.json_attr and " " in f.json_attr:
            out.append(DQFinding(
                code="JSON_ATTR_HAS_SPACE", severity="low",
                sheet=f.source.sheet, row=f.source.row,
                message=f"JSON attribute name contains a space: '{f.json_attr}'",
                raw=f.json_attr,
            ))
    return out


def build_report(v1: list[V1Field], v2: list[V2Field],
                 v1_path: str = "", v2_path: str = "") -> IngestionReport:
    findings = _check_v1(v1) + _check_v2(v2)
    by_code = dict(Counter(f.code for f in findings))
    links = sum(len(f.mapped_is()) for f in v2)
    return IngestionReport(
        v1_path=v1_path, v2_path=v2_path,
        v1_rows=len(v1), v2_rows=len(v2),
        v1_is_numbers=sum(1 for f in v1 if f.is_number),
        v2_mapping_links=links,
        findings_count=len(findings),
        by_code=by_code,
        findings=findings,
    )
