"""CSV export of the current gap filter + MoM export (LLD §7, §11.3 T-E11.4)."""
from __future__ import annotations

import csv
import io
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse

from app.deps import get_repo
from app.repositories.base import GapQuery, Repository
from app.services import mom as mom_svc

router = APIRouter(tags=["export"])

_COLUMNS = ["gap_id", "gap_type", "is_number", "v1_path", "mapping_context",
            "status", "v1_value", "v2_value", "detail", "root_node", "dd_ref",
            "nullable", "dd_in_v2"]


@router.get("/export")
def export_gaps(
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    context: Optional[str] = Query(None),
    is_number: Optional[str] = Query(None, alias="is"),
    is_in: Optional[list[str]] = Query(None),
    path_in: Optional[list[str]] = Query(None),
    is_not_in: Optional[list[str]] = Query(None),
    path_not_in: Optional[list[str]] = Query(None),
    v1: Optional[str] = Query(None),
    v2: Optional[str] = Query(None),
    detail: Optional[str] = Query(None),
    dd: Optional[str] = Query(None),
    dd_in_v2: Optional[bool] = Query(None),
    nullable: Optional[bool] = Query(None),
    root: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    repo: Repository = Depends(get_repo),
):
    q = GapQuery(gap_type=type, status=status, severity=severity, context=context,
                 is_number=is_number, is_in=is_in, path_in=path_in,
                 is_not_in=is_not_in, path_not_in=path_not_in,
                 v1=v1, v2=v2, detail=detail, dd=dd, dd_in_v2=dd_in_v2,
                 nullable=nullable, root_node=root, search=search, sort=sort,
                 page=1, page_size=1_000_000)
    rows = repo.query_gaps(q).rows

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_COLUMNS)
    for g in rows:
        d = g.model_dump()
        d["mapping_context"] = g.mapping_context.value if g.mapping_context else ""
        d["gap_type"] = g.gap_type.value
        d["status"] = g.status.value
        d["nullable"] = "" if g.nullable is None else ("Yes" if g.nullable else "No")
        writer.writerow([d.get(c, "") for c in _COLUMNS])

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=gaps.csv"},
    )


# --- MoM (Minutes of Meeting) export -----------------------------------------

def _mom_range(d_from: date, d_to: date) -> tuple[date, date]:
    if d_from > d_to:
        raise HTTPException(status_code=400, detail="'from' date must be on or before 'to' date")
    return d_from, d_to


@router.get("/export/mom.json")
def mom_preview(
    from_: date = Query(..., alias="from"),
    to: date = Query(...),
    repo: Repository = Depends(get_repo),
):
    """Structured MoM activity for the date range — drives the export preview."""
    d_from, d_to = _mom_range(from_, to)
    return mom_svc.collect(repo, d_from, d_to)


_MOM_MEDIA = {"html": "text/html", "md": "text/markdown", "csv": "text/csv"}


@router.get("/export/mom")
def mom_export(
    from_: date = Query(..., alias="from"),
    to: date = Query(...),
    format: str = Query("html", pattern="^(html|md|csv)$"),
    repo: Repository = Depends(get_repo),
):
    """Download the MoM document (HTML / Markdown / CSV) for the date range."""
    d_from, d_to = _mom_range(from_, to)
    report = mom_svc.collect(repo, d_from, d_to)
    body = {
        "html": mom_svc.render_html,
        "md": mom_svc.render_markdown,
        "csv": mom_svc.render_csv,
    }[format](report)
    name = mom_svc.filename(report, format)
    return Response(
        content=body,
        media_type=_MOM_MEDIA[format],
        headers={"Content-Disposition": f"attachment; filename={name}"},
    )
