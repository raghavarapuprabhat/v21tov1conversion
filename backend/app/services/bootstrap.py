"""Bootstrap — (re)load the configured workbooks into a repository (Plan E5).

Runs ingestion + analysis and hands the result to the repo, which re-applies any
persisted collaboration. Used at startup and by POST /api/ingest.
"""
from __future__ import annotations

from app.gaps.typemap import TypeMap
from app.ingestion.service import run_ingestion
from app.ingestion.validate import IngestionReport
from app.services.analysis import analyze


def reload_repository(repo, settings) -> IngestionReport:
    v1, v2, report = run_ingestion(settings.V1_PATH, settings.V2_PATH)
    typemap = TypeMap.load(settings.TYPE_MAP_PATH)
    result = analyze(v1, v2, typemap, enable_optional=settings.ENABLE_OPTIONAL_GAPS,
                     dq_findings=report.findings, disabled=set(settings.DISABLED_GAPS))
    report.reingest = repo.load(v1, v2, result)   # F13 merge summary
    return report
