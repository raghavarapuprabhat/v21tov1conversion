"""Raw sheet reader — returns the uploaded workbook grid *as is*.

Unlike `excel_loader` (which normalises into canonical `V1Field`/`V2Field`), this
module preserves every original column and the raw cell text. It powers the two
"sheet viewer" tabs (read-only V1, editable + downloadable V2.1). The header row
is located with the same best-match detection used by the canonical loader, then
*all* columns from that row are read verbatim.
"""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any

from openpyxl import Workbook, load_workbook

from app.ingestion.excel_loader import (
    V1_HEADERS,
    V2_HEADERS,
    IngestionError,
    _detect_header_row,
    _MATCH_THRESHOLD,
)

ROW_KEY = "__row"  # source Excel row number, used to target edits


def _cell_text(v: Any) -> str:
    return "" if v is None else str(v)


def _read_grid(path: str | Path, expected: set[str]) -> dict:
    p = Path(path)
    if not p.exists():
        raise IngestionError(f"workbook not found: {p}")
    wb = load_workbook(p, data_only=True)
    ws = wb.active
    hrow, hits, _ = _detect_header_row(ws, expected)
    if hrow is None or hits < len(expected) * _MATCH_THRESHOLD:
        raise IngestionError(
            f"header row not found in {p.name} (matched {hits}/{len(expected)})"
        )

    ncols = ws.max_column or 0
    columns: list[str] = []
    seen: dict[str, int] = {}
    for c in range(1, ncols + 1):
        raw = ws.cell(row=hrow, column=c).value
        label = str(raw).strip() if raw is not None else f"Column {c}"
        if not label:
            label = f"Column {c}"
        if label in seen:
            seen[label] += 1
            label = f"{label} ({seen[label]})"
        else:
            seen[label] = 0
        columns.append(label)

    rows: list[dict] = []
    for r in range(hrow + 1, (ws.max_row or hrow) + 1):
        cells: dict[str, Any] = {}
        blank = True
        for i in range(ncols):
            val = _cell_text(ws.cell(row=r, column=i + 1).value)
            if val.strip():
                blank = False
            cells[columns[i]] = val
        if blank:
            continue
        cells[ROW_KEY] = r
        rows.append(cells)

    return {"sheet": ws.title, "columns": columns, "rows": rows}


def read_v1_grid(path: str | Path) -> dict:
    return _read_grid(path, V1_HEADERS)


def read_v2_grid(path: str | Path) -> dict:
    return _read_grid(path, V2_HEADERS)


def write_grid_xlsx(columns: list[str], rows: list[dict], sheet_title: str = "Sheet1") -> bytes:
    """Serialise an (edited) grid back into an .xlsx workbook."""
    wb = Workbook()
    ws = wb.active
    ws.title = (sheet_title or "Sheet1")[:31]
    ws.append(columns)
    for row in rows:
        ws.append([_cell_text(row.get(c, "")) for c in columns])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
