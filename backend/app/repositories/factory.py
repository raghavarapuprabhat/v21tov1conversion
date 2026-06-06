"""Repository factory — selects the storage backend by config (LLD §8.1)."""
from __future__ import annotations

from app.repositories.base import Repository
from app.repositories.memory import InMemoryRepository


def create_repository(settings) -> Repository:
    if settings.STORAGE == "postgres":
        raise NotImplementedError(
            "PostgreSQL repository lands in Phase 1.5 (E16). Set STORAGE=memory."
        )
    return InMemoryRepository(settings.SNAPSHOT_PATH)
