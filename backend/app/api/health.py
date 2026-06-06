"""Liveness endpoint (LLD §7)."""
from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "storage": settings.STORAGE,
        "optional_gaps": settings.ENABLE_OPTIONAL_GAPS,
    }
