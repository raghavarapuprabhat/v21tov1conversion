# V2.1 → V1 Schema Conversion — Gap Analysis Dashboard

Local, collaborative workbench for the **data-impact / gap analysis** of converting
messages from the **V2.1** schema to the legacy **V1** schema.

> Design: see [`HLD_V2.1_to_V1_Gap_Analysis_Dashboard.md`](HLD_V2.1_to_V1_Gap_Analysis_Dashboard.md),
> [`LLD_V2.1_to_V1_Gap_Analysis_Dashboard.md`](LLD_V2.1_to_V1_Gap_Analysis_Dashboard.md),
> and the [`IMPLEMENTATION_PLAN`](IMPLEMENTATION_PLAN_V2.1_to_V1_Gap_Analysis_Dashboard.md).

## Status
- **E0 scaffold** ✓ — backend (FastAPI) + frontend (React/Vite, white Tailwind theme) boot and talk via a health check.
- **E1 ingestion & normalization** ✓ — Excel loader with header detection, the normalizer (handles `Not APplicable`, `XS:integer`, boolean Nullable, occurrence/array), canonical `V1Field`/`V2Field` models, and a data-quality report. Exposed at `POST /api/ingest`.
- **E2 per-context linkage** ✓ — `Linkage` edges (Entity/RP_IND/RP_ORG) + `LinkIndex` lookups and coverage/reverse-orphan views.
- **E4 tree builder + parent-root resolver** ✓ — V1 tree from Node+Level with array-node detection, `resolve_parent_root` (outermost logical Root, decision D7), node lookup + gap rollup helper.
- **E3 gap engines + severity** ✓ — mandatory **G1** coverage funnel (A/B/C), **G2** occurrence (per context, arrays), **G3** data type (type-equivalence map), **G4** mandatory/optional; optional **G5** reverse-orphan, **G6** DD mismatch, **G7** cardinality (scalar↔array), **G8** duplicate mapping, **G9** data-quality findings. Position-independent `gap_id`, severity, summary, analysis orchestrator. Optional gaps toggle via `ENABLE_OPTIONAL_GAPS`. Engines can be turned off via `DISABLED_GAPS` (default `G2_OCCURRENCE`, whose logic is under review) — disabled engines produce no gaps but their card still shows in the UI in a **Disabled** state.
- **E5 durable storage** ✓ — `Repository` interface, **SQLite `SnapshotStore`** (statuses/history/comments/views persist across restarts), `InMemoryRepository` (RAM gap indexes + filter/sort/paginate/search), bootstrap + startup ingestion, `POST /api/ingest` populates the repo.
- **E6 collaboration + F13** ✓ — threaded comment assembly (nested replies), IS-anchored retention, re-upload merge (`ReingestSummary` with monotonic `comments_retained`). Comments survive a new Excel upload by IS Reference Number; resolved-gap threads surface as "earlier discussion".
- **E8 REST API** ✓ — `/summary`, `/gaps` (per-column + global filter, sort, paginate), `/gaps/{id}` + `/comments` + `/history`, `PATCH status` & `bulk-status`, `POST comments`, `/tree`, `/v2/by-dd/{dd}`, `/views`, `/export` (CSV), `/sheets/v1` + `/sheets/v2` (raw workbook as-is) + `/sheets/v2/download` (edited .xlsx). 64 tests pass; OpenAPI at `/docs`.
- **E9–E13 React UI** ✓ — white Tailwind theme: landing gap cards (G1 A/B/C funnel), gap data grid with **per-column filters** — **multi-select for IS and Path** (searchable/scrollable, scales to ~800 values via a `/facets` endpoint), dropdowns for Context/Status, text for V1/V2/Detail/DD — plus sort, column show/hide, CSV export, bulk disposition. **Path column** (Level 1–8 joined, truncated with hover tooltip); G1 coverage table adds a **Nullable** column + filter (the V1 `Nullable` flag). Conversation panel (threaded comments, status + history, Fetch-V2-By-DD, "earlier discussion for IS"); V1 tree with gap rollups. Display-name prompt; `?as=` and `?open=` deep links.
- **Sheet viewer tabs** ✓ — **V1 Sheet** (read-only) and **V2.1 Sheet** show the uploaded workbook *as is* (all original columns, raw cell text). Every column has a searchable multi-select filter (Excel-style **(Select All)** + deselect) plus global search, column show/hide, and pagination (scales to ~2,000 rows). The **V2.1 Sheet** lets you **edit any cell inline** (changed cells highlighted, edit counter, reset) and **Download Excel** to get the edited `.xlsx`. The **V1 Sheet** adds a **Gap** column (Yes/No) and highlights rows with gaps (amber = open, green = resolved); **click a flagged row** to open a panel listing that row's gaps, where you can **set status and add comments** (`/api/sheets/v1/gap-index` + `/api/gaps?v1_row=`).
- **Upload & re-ingest** ✓ — the landing **Upload Excel** button opens a dialog to upload a new V1 and/or V2.1 workbook (`POST /api/ingest/upload`). Uploaded files are validated, persisted to the configured paths (so the sheet tabs and a later restart agree), then re-ingested — comments &amp; statuses are retained by IS Reference Number (F13). `POST /api/ingest` still re-reads the configured files without an upload.

**Phase 1 feature-complete.** Run `make dev`, open http://localhost:5173.

## Prerequisites
- Python 3.11+
- Node 20+ / npm

## Quick start
```bash
make install      # backend venv + frontend deps (first time only)
make dev          # backend on :8000, frontend on :5173
```
Then open <http://localhost:5173>. The header shows **API · memory** when connectivity is good.
API docs: <http://localhost:8000/docs>.

Run backend and frontend separately if you prefer:
```bash
make backend      # http://localhost:8000 (uses backend/.env)
make frontend     # http://localhost:5173
make test         # backend smoke tests
```

Switch datasets without editing `backend/.env`:
```bash
make dev-mock     # ~2000-row mock dataset (mockdata/)
make dev-sample   # small sample (v1.xlsx / v2.1.xlsx)
```

## Configuration
Copy `.env.example` → `backend/.env` and adjust (storage mode, workbook paths, gap toggles).
See LLD §12 for every setting.

## Layout
```
backend/   FastAPI app (app/), config, tests, type_equivalence.yaml
frontend/  React + TS (Vite), pages, api client, shared types
v1.xlsx    sample V1 schema (dummy values; real ~2,000 rows)
v2.1.xlsx  sample V2.1 schema
```

## Roadmap (next epics)
E1 ingestion → E2 per-context linkage → E3 gap engines (G1–G4) → E5 durable store →
E6 collaboration + IS-anchored comment retention (F13) → E8 API → E10–E13 UI.
Full task list in the implementation plan.
