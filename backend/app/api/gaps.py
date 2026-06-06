"""Gap, status, and comment routes (LLD v1.2 §7)."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from app.deps import get_repo
from app.gaps.registry import GapSummary
from app.models.collab import Comment, GapConversation, StatusChange
from app.models.gap import Gap, GapStatus
from app.repositories.base import GapPage, GapQuery, Repository
from app.services.comments import build_conversation

router = APIRouter(tags=["gaps"])


# --- request bodies -----------------------------------------------------------

class StatusUpdate(BaseModel):
    status: GapStatus
    author: str
    note: Optional[str] = None


class BulkStatusUpdate(BaseModel):
    gap_ids: list[str]
    status: GapStatus
    author: str
    note: Optional[str] = None


class CommentCreate(BaseModel):
    author: str
    body: str
    parent_comment_id: Optional[str] = None


# --- reads --------------------------------------------------------------------

@router.get("/summary", response_model=list[GapSummary])
def get_summary(repo: Repository = Depends(get_repo)):
    return repo.summary()


@router.get("/facets")
def get_facets(type: Optional[str] = Query(None), repo: Repository = Depends(get_repo)):
    """Distinct IS numbers + paths for multi-select column filters."""
    return repo.facets(type)


@router.get("/gaps", response_model=GapPage)
def list_gaps(
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
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=1000),
    repo: Repository = Depends(get_repo),
):
    q = GapQuery(gap_type=type, status=status, severity=severity, context=context,
                 is_number=is_number, is_in=is_in, path_in=path_in,
                 v1=v1, v2=v2, detail=detail, dd=dd, dd_in_v2=dd_in_v2,
                 root_node=root, search=search, sort=sort,
                 page=page, page_size=page_size)
    return repo.query_gaps(q)


@router.get("/gaps/{gap_id}", response_model=Gap)
def get_gap(gap_id: str, repo: Repository = Depends(get_repo)):
    g = repo.get_gap(gap_id)
    if g is None:
        raise HTTPException(status_code=404, detail="gap not found")
    return g


@router.get("/gaps/{gap_id}/comments", response_model=GapConversation)
def get_comments(gap_id: str, repo: Repository = Depends(get_repo)):
    if repo.get_gap(gap_id) is None:
        raise HTTPException(status_code=404, detail="gap not found")
    return build_conversation(repo, gap_id)


@router.get("/gaps/{gap_id}/history", response_model=list[StatusChange])
def get_history(gap_id: str, repo: Repository = Depends(get_repo)):
    return repo.status_history(gap_id)


# --- writes -------------------------------------------------------------------

@router.patch("/gaps/bulk-status")
def patch_bulk_status(payload: BulkStatusUpdate, repo: Repository = Depends(get_repo)):
    n = repo.bulk_status(payload.gap_ids, payload.status.value, payload.author, payload.note)
    return {"updated": n}


@router.patch("/gaps/{gap_id}/status", response_model=Gap)
def patch_status(gap_id: str, payload: StatusUpdate, repo: Repository = Depends(get_repo)):
    try:
        return repo.set_status(gap_id, payload.status.value, payload.author, payload.note)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="gap not found") from exc


@router.post("/gaps/{gap_id}/comments", response_model=Comment)
def post_comment(gap_id: str, payload: CommentCreate, repo: Repository = Depends(get_repo)):
    if repo.get_gap(gap_id) is None:
        raise HTTPException(status_code=404, detail="gap not found")
    return repo.add_comment(Comment(
        gap_id=gap_id, author=payload.author, body=payload.body,
        parent_comment_id=payload.parent_comment_id,
    ))
