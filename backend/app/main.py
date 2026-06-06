"""FastAPI application entrypoint.

Run from the `backend/` directory:
    uvicorn app.main:app --reload --port 8000

On startup the configured workbooks are ingested + analysed into the repository
(in-memory + SQLite snapshot). Ingestion can be re-triggered via POST /api/ingest.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import export, gaps, health, ingest, tree, v2lookup, views
from app.config import settings
from app.deps import get_repo
from app.services.bootstrap import reload_repository


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        report = reload_repository(get_repo(), settings)
        print(f"[startup] ingested v1={report.v1_rows} v2={report.v2_rows} rows")
    except Exception as exc:  # noqa: BLE001 - app still starts; retry via /api/ingest
        print(f"[startup] ingestion skipped: {exc}")
    yield


app = FastAPI(
    title="V2.1 -> V1 Schema Conversion — Gap Analysis Dashboard",
    version=__version__,
    summary="Data-impact / gap-analysis workbench (local).",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(ingest.router, prefix="/api")
app.include_router(gaps.router, prefix="/api")
app.include_router(tree.router, prefix="/api")
app.include_router(v2lookup.router, prefix="/api")
app.include_router(views.router, prefix="/api")
app.include_router(export.router, prefix="/api")


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "name": "V2.1->V1 Gap Analysis Dashboard",
        "version": __version__,
        "docs": "/docs",
        "health": "/api/health",
    }
