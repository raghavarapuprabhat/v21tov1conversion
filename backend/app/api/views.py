"""Saved views routes (LLD §7, §11.3)."""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.deps import get_repo
from app.models.collab import SavedView
from app.repositories.base import Repository

router = APIRouter(tags=["views"])


class ViewCreate(BaseModel):
    name: str
    owner: Optional[str] = None
    spec: dict[str, Any] = Field(default_factory=dict)


@router.get("/views", response_model=list[SavedView])
def list_views(repo: Repository = Depends(get_repo)):
    return repo.list_views()


@router.post("/views", response_model=SavedView)
def save_view(payload: ViewCreate, repo: Repository = Depends(get_repo)):
    return repo.save_view(SavedView(view_id="", name=payload.name,
                                    owner=payload.owner, spec=payload.spec))
