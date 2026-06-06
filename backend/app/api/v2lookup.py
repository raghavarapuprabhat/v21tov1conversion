"""Fetch V2 By DD route (LLD §7, §10) — reads the loaded v2.1 workbook."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import get_repo
from app.models.canonical import V2Field
from app.repositories.base import Repository

router = APIRouter(tags=["v2"])


@router.get("/v2/by-dd/{dd}", response_model=list[V2Field])
def v2_by_dd(dd: str, repo: Repository = Depends(get_repo)):
    return repo.v2_by_dd(dd)
