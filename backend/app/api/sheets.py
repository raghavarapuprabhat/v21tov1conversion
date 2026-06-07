"""Raw sheet viewer endpoints (LLD: uploaded-workbook tabs).

`GET /api/sheets/v1` and `/api/sheets/v2` return the workbook *as is* (all
original columns + raw cell text). `POST /api/sheets/v2/download` serialises an
edited V2.1 grid back into a downloadable .xlsx.
"""
from __future__ import annotations

import io
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import settings
from app.ingestion.excel_loader import IngestionError
from app.ingestion.raw_sheet import read_v1_grid, read_v2_grid, write_grid_xlsx

router = APIRouter(tags=["sheets"])

_XLSX_MEDIA = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@router.get("/sheets/v1")
def sheet_v1() -> dict:
    try:
        return read_v1_grid(settings.V1_PATH)
    except IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@router.get("/sheets/v2")
def sheet_v2() -> dict:
    try:
        return read_v2_grid(settings.V2_PATH)
    except IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


class GridPayload(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    filename: Optional[str] = None
    sheet: Optional[str] = None


@router.post("/sheets/v2/download")
def download_v2(payload: GridPayload) -> StreamingResponse:
    data = write_grid_xlsx(payload.columns, payload.rows, payload.sheet or "V2.1")
    name = payload.filename or "v2.1_edited.xlsx"
    if not name.lower().endswith(".xlsx"):
        name += ".xlsx"
    return StreamingResponse(
        io.BytesIO(data),
        media_type=_XLSX_MEDIA,
        headers={"Content-Disposition": f"attachment; filename={name}"},
    )
