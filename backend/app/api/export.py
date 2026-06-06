"""CSV export of the current gap filter (LLD §7, §11.3 T-E11.4 server side)."""
from __future__ import annotations

import csv
import io
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.deps import get_repo
from app.repositories.base import GapQuery, Repository

router = APIRouter(tags=["export"])

_COLUMNS = ["gap_id", "gap_type", "is_number", "v1_path", "mapping_context", "severity",
            "status", "v1_value", "v2_value", "detail", "root_node", "dd_ref", "dd_in_v2"]


@router.get("/export")
def export_gaps(
    type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    context: Optional[str] = Query(None),
    is_number: Optional[str] = Query(None, alias="is"),
    is_in: Optional[list[str]] = Query(None),
    path_in: Optional[list[str]] = Query(None),
    v1: Optional[str] = Query(None),
    v2: Optional[str] = Query(None),
    detail: Optional[str] = Query(None),
    dd: Optional[str] = Query(None),
    dd_in_v2: Optional[bool] = Query(None),
    root: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    sort: Optional[str] = Query(None),
    repo: Repository = Depends(get_repo),
):
    q = GapQuery(gap_type=type, status=status, severity=severity, context=context,
                 is_number=is_number, is_in=is_in, path_in=path_in,
                 v1=v1, v2=v2, detail=detail, dd=dd, dd_in_v2=dd_in_v2,
                 root_node=root, search=search, sort=sort,
                 page=1, page_size=1_000_000)
    rows = repo.query_gaps(q).rows

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(_COLUMNS)
    for g in rows:
        d = g.model_dump()
        d["mapping_context"] = g.mapping_context.value if g.mapping_context else ""
        d["gap_type"] = g.gap_type.value
        d["severity"] = g.severity.value
        d["status"] = g.status.value
        writer.writerow([d.get(c, "") for c in _COLUMNS])

    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=gaps.csv"},
    )
