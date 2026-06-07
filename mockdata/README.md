# Mock data (~2000 rows)

Generated, seeded test data that exercises every gap scenario. These files are
**separate** from the golden fixtures `v1.xlsx` / `v2.1.xlsx` (which the test
suite asserts against) — they are safe to load and regenerate.

| File | Rows |
|---|---|
| `v1_mock.xlsx` | ~2001 (≈1940 elements + structural Root rows, 1941 IS numbers) |
| `v2.1_mock.xlsx` | ~2000 (mapped elements, multi-context rows, reverse-orphans, structural Nodes) |

## What's inside (verified gap distribution, all 9 engines enabled)
| Gap | Count | Notes |
|---|---|---|
| G1 Coverage | 395 | funnel: 395 missing · 192 Nullable=False · 107 parent-root Min=1 |
| G2 Occurrence | 460 | min/max mismatch incl. scalar↔array |
| G3 Data type | 536 | canonical type mismatches |
| G4 Mandatory/Optional | 354 | `Nullable=False ⇒ Mandatory` disagreements |
| G5 Reverse orphan | 30 | V2 maps to IS absent from V1 |
| G6 DD mismatch | 452 | V2 `Source DD#` differs from V1 `CC DD Ref No` |
| G7 Cardinality | 337 | scalar ↔ array divergence |
| G8 Duplicate mapping | 47 | >1 V2 row maps the same IS in the same context |
| G9 Data quality | 743 | ingestion findings (casing/spaces/dupes) surfaced as gaps |

Also included: **per-context** mappings (Entity / RP IND / RP ORG, plus single
rows mapping three different IS), **array/repeating** blocks, deep/varied Level
paths (55 distinct), and data-quality noise (`Not APplicable` casing, attribute
names with spaces, duplicate IS). Optional gaps (G5–G9) require
`ENABLE_OPTIONAL_GAPS=true` (already set in `backend/.env`).

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
`make frontend` and open http://localhost:5173. (You can also click **Upload Excel**
on the landing page to push a new workbook directly, no path change needed.)
