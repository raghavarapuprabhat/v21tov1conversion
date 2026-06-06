"""Application settings (LLD v1.2 §12).

All values are overridable via environment variables or a local `.env` file.
"""
from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Storage — both modes are durable (LLD §8)
    STORAGE: str = "memory"                      # memory | postgres
    SNAPSHOT_PATH: str = "./.gapdb.sqlite"       # durable snapshot for in-memory mode
    DATABASE_URL: str = "postgresql+psycopg://user:pass@localhost:5432/gapdb"

    # Source workbooks
    V1_PATH: str = "../v1.xlsx"
    V2_PATH: str = "../v2.1.xlsx"

    # Gap analysis
    ENABLE_OPTIONAL_GAPS: bool = False           # toggles G5..G9
    TYPE_MAP_PATH: str = "./config/type_equivalence.yaml"
    MANDATORY_CONVENTION: str = "nullable_false_is_mandatory"  # CONFIRMED (D2)
    G1_COVERAGE_SCOPE: str = "any_context"       # any_context | per_context

    # Frontend dev origin for CORS
    CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]


settings = Settings()
