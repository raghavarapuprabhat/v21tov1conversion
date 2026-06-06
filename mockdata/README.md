# Mock data (~2000 rows)

Generated, seeded test data that exercises every gap scenario. These files are
**separate** from the golden fixtures `v1.xlsx` / `v2.1.xlsx` (which the test
suite asserts against) — they are safe to load and regenerate.

| File | Rows |
|---|---|
| `v1_mock.xlsx` | ~2001 (≈1940 elements + structural Root rows, 1941 IS numbers) |
| `v2.1_mock.xlsx` | ~2000 (mapped elements, multi-context rows, reverse-orphans, structural Nodes) |

## What's inside (verified gap distribution)
| Gap | Count | Notes |
|---|---|---|
| G1 Coverage | 372 | funnel: 372 missing · 182 Nullable=False · 115 parent-root Min=1 |
| G2 Occurrence | 465 | incl. scalar↔array (unbounded / N>1 roots) |
| G3 Data type | 565 | canonical type mismatches |
| G4 Mandatory/Optional | 407 | `Nullable=False ⇒ Mandatory` disagreements |
| G5 Reverse orphan | 30 | V2 maps to IS absent from V1 |

Also included: **per-context** mappings (Entity / RP IND / RP ORG, plus single
rows mapping three different IS), **array/repeating** blocks, deep/varied Level
paths (55 distinct), and data-quality noise (`Not APplicable` casing ×418,
attribute names with spaces ×387, duplicate IS ×2).

## Regenerate
```bash
cd backend && . .venv/bin/activate
python scripts/generate_mock_data.py --analyze   # --analyze prints the gap summary
```

## Load it in the app
Point the backend at these files via env vars (paths are relative to `backend/`):
```bash
cd backend && . .venv/bin/activate
V1_PATH=../mockdata/v1_mock.xlsx V2_PATH=../mockdata/v2.1_mock.xlsx \
  ENABLE_OPTIONAL_GAPS=true uvicorn app.main:app --reload --port 8000
```
…or set `V1_PATH` / `V2_PATH` / `ENABLE_OPTIONAL_GAPS=true` in `backend/.env`, then
`make frontend` and open http://localhost:5173. (You can also click **Re-ingest Excel**
on the landing page after changing the configured paths.)
