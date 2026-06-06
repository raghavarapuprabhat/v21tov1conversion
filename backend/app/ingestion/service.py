"""Ingestion orchestration (Plan E1).

Loads both workbooks into canonical records and builds the data-quality report.
Linkage (E2) and gap engines (E3) consume the returned `(v1, v2)` lists.
"""
from __future__ import annotations

from pathlib import Path

from app.ingestion.excel_loader import load_v1, load_v2
from app.ingestion.validate import IngestionReport, build_report
from app.models.canonical import V1Field, V2Field


def run_ingestion(v1_path: str | Path, v2_path: str | Path
                  ) -> tuple[list[V1Field], list[V2Field], IngestionReport]:
    v1 = load_v1(v1_path)
    v2 = load_v2(v2_path)
    report = build_report(v1, v2, v1_path=str(v1_path), v2_path=str(v2_path))
    return v1, v2, report
