"""Ingestion endpoint (LLD §7).

POST /api/ingest re-loads the configured workbooks into the repository
(recompute gaps, re-apply persisted collaboration) and returns the DQ report.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.config import settings
from app.deps import get_repo
from app.ingestion.excel_loader import IngestionError
from app.ingestion.validate import IngestionReport
from app.services.bootstrap import reload_repository

router = APIRouter(tags=["ingestion"])


@router.post("/ingest", response_model=IngestionReport)
def ingest() -> IngestionReport:
    try:
        return reload_repository(get_repo(), settings)
    except IngestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
