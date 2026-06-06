"""Shared dependencies — the process-wide repository singleton."""
from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.repositories.base import Repository
from app.repositories.factory import create_repository


@lru_cache(maxsize=1)
def get_repo() -> Repository:
    return create_repository(settings)
