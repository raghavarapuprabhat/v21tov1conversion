"""V1 tree route (LLD §7)."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import get_repo
from app.domain.tree import TreeNode
from app.repositories.base import Repository

router = APIRouter(tags=["tree"])


@router.get("/tree", response_model=TreeNode)
def get_tree(repo: Repository = Depends(get_repo)):
    return repo.tree()
