"""Ingestion endpoint (LLD §7).

POST /api/ingest re-loads the **configured** workbooks into the repository.
POST /api/ingest/upload accepts one or both workbooks as file uploads, persists
them to the configured paths, then re-ingests — so the gap analysis and the
sheet-viewer tabs both reflect the freshly uploaded files (and survive restart).
Collaboration (comments/status) is re-applied by IS reference number (F13).
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import settings
from app.deps import get_repo
from app.ingestion.excel_loader import IngestionError, load_v1, load_v2
from app.ingestion.validate import IngestionReport
from app.services.bootstrap import reload_repository

router = APIRouter(tags=["ingestion"])


@router.post("/ingest", response_model=IngestionReport)
def ingest() -> IngestionReport:
    try:
        return reload_repository(get_repo(), settings)
    except IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _stage(upload: UploadFile) -> str:
    """Persist an uploaded workbook to a temp .xlsx and return its path."""
    name = (upload.filename or "").lower()
    if not name.endswith((".xlsx", ".xlsm")):
        raise HTTPException(status_code=415, detail=f"{upload.filename!r} is not an .xlsx file")
    fd, tmp = tempfile.mkstemp(suffix=".xlsx")
    try:
        with os.fdopen(fd, "wb") as out:
            shutil.copyfileobj(upload.file, out)
    finally:
        upload.file.close()
    return tmp


@router.post("/ingest/upload", response_model=IngestionReport)
async def ingest_upload(
    v1: Optional[UploadFile] = File(None),
    v2: Optional[UploadFile] = File(None),
) -> IngestionReport:
    if v1 is None and v2 is None:
        raise HTTPException(status_code=400, detail="Upload at least one workbook (V1 and/or V2.1).")

    staged: list[str] = []
    try:
        v1_tmp = _stage(v1) if v1 is not None else None
        v2_tmp = _stage(v2) if v2 is not None else None
        staged = [p for p in (v1_tmp, v2_tmp) if p]

        # Validate that each uploaded workbook parses *before* overwriting anything.
        # openpyxl raises its own errors (e.g. BadZipFile) for non-xlsx content;
        # normalise everything to a 422 so the existing file is never clobbered.
        try:
            if v1_tmp:
                load_v1(v1_tmp)
            if v2_tmp:
                load_v2(v2_tmp)
        except IngestionError:
            raise
        except Exception as exc:  # noqa: BLE001 - surface as a clean 422
            raise IngestionError(f"Could not read the uploaded workbook: {exc}") from exc

        # Commit to the configured paths so re-ingest + sheet tabs + restart agree.
        if v1_tmp:
            shutil.move(v1_tmp, settings.V1_PATH)
            staged.remove(v1_tmp)
        if v2_tmp:
            shutil.move(v2_tmp, settings.V2_PATH)
            staged.remove(v2_tmp)

        return reload_repository(get_repo(), settings)
    except IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    finally:
        for p in staged:
            Path(p).unlink(missing_ok=True)
