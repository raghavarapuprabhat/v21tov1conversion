# Low-Level Design (LLD)
## V2.1 → V1 Schema Conversion — Data Impact & Gap-Analysis Dashboard

| | |
|---|---|
| **Document type** | Low-Level Design (LLD) |
| **Project** | V2.1 → V1 Message Schema Conversion — Data Impact Analysis |
| **Version** | 1.2 (Draft) |
| **Date** | 2026-06-05 |
| **Companion** | `HLD_V2.1_to_V1_Gap_Analysis_Dashboard.md` (v1.2) |
| **Status** | For review / discussion |

> **Grounding note.** Field names, linkage keys, and rules below come **only** from `v1.xlsx` / `v2.1.xlsx` column headers. Sample cell values are dummy; production is ~2,000 rows with **array/repeating nodes** and deeper nesting. Nothing is invented beyond the file contents.

### Revision history
| Ver | Date | Change |
|---|---|---|
| 1.0 | 2026-06-05 | Initial LLD |
| 1.1 | 2026-06-05 | **Per-context linkage** (Entity/RP IND/RP ORG → context-tagged `Linkage`); gaps carry `mapping_context`; G2/G3/G4 iterate per context; G8 redefined as context-aware. **Durable in-memory** via SQLite snapshot. Added status-history/audit, bulk disposition, saved views, comment author, re-ingest merge, gap severity. |
| 1.2 | 2026-06-05 | **`gap_id` made position-independent** (business key, no sheet/row/column) and comments **anchored to the IS Reference Number** (`is_anchor`) so they survive a new Excel upload (§5.7, §8.4). Confirmed author = locally-entered display name (§9.2). |

---

## 1. Component Architecture

```mermaid
flowchart TD
    subgraph FE[Frontend: React + TS]
        R1[LandingPage - Gap Cards]
        R2[GapTablePage - DataGrid + Bulk]
        R3[TreePage - V1 Tree]
        R4[ConversationPanel]
        R5[FetchV2ByDD Modal]
        RQ[TanStack Query client]
    end
    subgraph BE[Backend: FastAPI]
        C[Controllers / Routers]
        S1[IngestionService]
        S2[NormalizationService]
        S3[LinkageResolver - per context]
        S4[TreeBuilder]
        S5[GapEngineRegistry]
        S6[CommentService]
        S7[StatusService + History]
        S8[V2LookupService]
        REPO[(RepositoryInterface)]
    end
    MEM[InMemoryRepository + SQLite snapshot]
    PG[PostgresRepository]

    RQ <--> C
    C --> S1 --> S2 --> S3 --> S4
    S3 --> S5
    C --> S6 & S7 & S8
    S5 --> REPO
    S6 --> REPO
    S7 --> REPO
    REPO --> MEM
    REPO --> PG
```

---

## 2. Canonical Data Model

The ingestion layer maps each source workbook into a **canonical model** so the rest of the system never touches raw spreadsheet quirks. Every canonical record retains a `source_ref` (sheet, row, column) and both `raw` and `normalized` forms of key values.

### 2.1 Source-column → canonical-field mapping

**V1 (`v1.xlsx`)**

| Source column | Canonical field | Type | Notes |
|---|---|---|---|
| `IS Reference Number` | `is_number` | str | Join key; empty on structural rows |
| `CC DD Ref No` | `dd_ref` | str | Secondary key (DD) |
| `Node` | `node_kind` | enum(`Root`,`Element`,…) | Drives tree role |
| `Level 1`…`Level 8` | `path[]` | str[] | Ordered hierarchy path (trailing blanks trimmed) |
| `Attribute` | `attribute` | str | Leaf field name |
| `XSD Field Type` | `xsd_type` | str | e.g. `XS:integer`, `XS:string` |
| `Nullable` | `nullable` | bool | Boolean in source |
| `Min Occurrence` | `min_occurs` | int? | Present on Root rows |
| `Max Occurrence` | `max_occurs` | int? / `UNBOUNDED` | Array detection |

**V2.1 (`v2.1.xlsx`)** — the three mapping columns become **context-tagged** links.

| Source column | Canonical field | Type | Notes |
|---|---|---|---|
| `Schema Name + JSON Path` | `json_path` | str | Hierarchy/path |
| `CLMT IS Reference Number` | `clmt_is_ref` | str | V2.1 own IS ref |
| `Version Number` / `Change Log` | `version` / `change_log` | str | |
| `Attribute CLM ID` | `clm_id` | str | |
| `CCDM Attribute Name` | `attribute_name` | str | |
| `Source DD#` | `dd_ref` | str | Secondary key (DD) |
| `CC_V1_Mapping Entity` | `map_entity` | str | **IS link, context = Entity** |
| `CC_V1_Mapping RP IND` | `map_rp_ind` | str | **IS link, context = RP_IND** |
| `CC_V1_Mapping RP ORG` | `map_rp_org` | str | **IS link, context = RP_ORG** |
| `Remarks For Repeating Block` | `repeat_remarks` | str | Array/repeating hint |
| `Node / Element` | `node_kind` | enum | Tree role |
| `Schema Name` | `schema_name` | str | |
| `JSON Attribute Name` | `json_attr` | str | Leaf field name |
| `Data Type` | `data_type` | str | e.g. `String`, `Object` |
| `Min Occurrence` / `Max Occurrence` | `min_occurs` / `max_occurs` | int? / `UNBOUNDED` | |
| `Mandatory / Optional` | `mandatory_optional` | enum(`Mandatory`,`Optional`) | |
| `Schema + JSON Path + Attribute` | `full_path` | str | Fully-qualified id |
| `Mapping Remarks` | `mapping_remarks` | str | |

### 2.2 Pydantic models (backend)

```python
from enum import Enum
from typing import Optional
from pydantic import BaseModel

class MappingContext(str, Enum):
    ENTITY = "Entity"
    RP_IND = "RP_IND"
    RP_ORG = "RP_ORG"

class SourceRef(BaseModel):
    sheet: str
    row: int            # 1-based Excel row
    column: str         # Excel column letter

class Occurs(BaseModel):
    raw: Optional[str]
    value: Optional[int]      # parsed integer
    unbounded: bool = False   # 'unbounded'/'*'/'n' → True

class V1Field(BaseModel):
    is_number_raw: Optional[str]
    is_number: Optional[str]          # normalized
    dd_ref_raw: Optional[str]
    dd_ref: Optional[str]
    node_kind: str                    # Root / Element / ...
    path: list[str]                   # Level 1..8 trimmed
    attribute: Optional[str]
    xsd_type_raw: Optional[str]
    xsd_type: Optional[str]           # normalized token
    nullable: Optional[bool]
    min_occurs: Optional[int]
    max_occurs: Occurs
    source: SourceRef

class V2Field(BaseModel):
    clmt_is_ref: Optional[str]
    json_path: Optional[str]
    dd_ref_raw: Optional[str]
    dd_ref: Optional[str]
    map_entity: Optional[str]         # raw mapping cell
    map_rp_ind: Optional[str]
    map_rp_org: Optional[str]
    repeat_remarks: Optional[str]
    node_kind: str
    schema_name: Optional[str]
    json_attr: Optional[str]
    data_type_raw: Optional[str]
    data_type: Optional[str]          # normalized token
    min_occurs: Optional[int]
    max_occurs: Occurs
    mandatory_optional: Optional[str]
    full_path: Optional[str]
    source: SourceRef

class Linkage(BaseModel):
    """One context-tagged edge V2.1 row → V1 IS."""
    is_number: str                    # normalized V1 IS this context points to
    context: MappingContext
    v2: V2Field
    v1: Optional[V1Field]             # None if IS not found in V1 (→ G5)
```

### 2.3 Gap, Comment, Status models

```python
class GapType(str, Enum):
    G1_COVERAGE = "G1_COVERAGE"
    G2_OCCURRENCE = "G2_OCCURRENCE"
    G3_DATATYPE = "G3_DATATYPE"
    G4_MANDATORY = "G4_MANDATORY"
    G5_REVERSE_ORPHAN = "G5_REVERSE_ORPHAN"   # optional
    G6_DD_MISMATCH = "G6_DD_MISMATCH"         # optional
    G7_CARDINALITY = "G7_CARDINALITY"         # optional
    G8_DUP_MAPPING = "G8_DUP_MAPPING"         # optional
    G9_DATA_QUALITY = "G9_DATA_QUALITY"       # optional

class GapStatus(str, Enum):
    OPEN = "Open"
    ACCEPTED = "Accepted"
    NOT_APPLICABLE = "Not applicable"

class Severity(str, Enum):
    CRITICAL = "Critical"; HIGH = "High"; MEDIUM = "Medium"; LOW = "Low"

class Gap(BaseModel):
    gap_id: str                       # deterministic hash (see §5.7)
    gap_type: GapType
    is_number: Optional[str]
    mapping_context: Optional[MappingContext]   # NEW: which context produced it
    v1_ref: Optional[SourceRef]
    v2_ref: Optional[SourceRef]
    v1_value: Optional[str]
    v2_value: Optional[str]
    detail: str
    flags: dict
    severity: Severity
    root_node: Optional[str]          # for tree grouping
    dd_ref: Optional[str]             # enables Fetch V2 By DD
    dd_in_v2: bool                    # is dd_ref present in the V2.1 sheet? (filterable)
    status: GapStatus = GapStatus.OPEN

class Comment(BaseModel):
    comment_id: str
    gap_id: str                       # current gap this thread shows under
    is_anchor: Optional[str]          # NEW: the V1 IS Reference Number the comment belongs to
    mapping_context: Optional[MappingContext]  # NEW: context it was raised in (if any)
    parent_comment_id: Optional[str]  # None = root; else reply
    author: str                       # locally-entered display name (no auth) — CONFIRMED
    body: str
    created_at: str                   # ISO-8601

class StatusChange(BaseModel):        # audit trail
    gap_id: str
    old_status: Optional[GapStatus]
    new_status: GapStatus
    author: str
    changed_at: str
    note: Optional[str]
```

---

## 3. Ingestion & Normalization

### 3.1 Excel loading
- `openpyxl.load_workbook(path, data_only=True)`.
- **Header detection:** the sample has a merged "Table 1" title in row 1 and the real headers in row 2. Strategy: scan the first N rows; pick the row maximizing match against the expected header vocabulary; fail loudly (`422`) if below threshold rather than guessing.
- Read subsequent non-empty rows into raw dicts keyed by header.

### 3.2 Normalization rules (deterministic, table-driven)

| Concern | Rule |
|---|---|
| Whitespace | `strip()` + collapse internal space runs |
| Case (matching only) | `casefold()` for comparison keys; **raw preserved for display** |
| Sentinel "no mapping" | `{"", "not applicable", "n/a", "na", "none"}` → empty for linkage |
| IS number | uppercase, trim; store raw too (`is2339`→`IS2339`) |
| Boolean `Nullable` | `{true,1,"true","yes","y"}→True`; `{false,0,"false","no","n"}→False` |
| Occurrence parse | int if numeric; `{"unbounded","*","n","many"}`→`Occurs(unbounded=True)`; blank→`None` |
| Type tokens | mapped via the **type-equivalence table** (§5.4) |

> Normalization is **non-destructive**: the raw value is always retained for audit and UI display.

### 3.3 Ingestion report
Returns rows read/accepted/flagged + DQ findings (feeds optional gap G9). Surfaced as a UI banner.

---

## 4. Linkage Resolution (per context)

```python
def resolve_links(v1: list[V1Field], v2: list[V2Field]) -> LinkIndex:
    v1_by_is = {f.is_number: f for f in v1 if f.is_number}
    v1_is_set = set(v1_by_is)

    linkages: list[Linkage] = []
    v2_mapped_is: set[str] = set()
    # Each V2 row yields up to 3 context-tagged links
    COLS = [(MappingContext.ENTITY, lambda r: r.map_entity),
            (MappingContext.RP_IND, lambda r: r.map_rp_ind),
            (MappingContext.RP_ORG, lambda r: r.map_rp_org)]
    for r in v2:
        for ctx, get in COLS:
            isn = normalize_is(get(r))          # None for sentinels/blank
            if not isn:
                continue
            v2_mapped_is.add(isn)
            linkages.append(Linkage(is_number=isn, context=ctx,
                                    v2=r, v1=v1_by_is.get(isn)))

    return LinkIndex(
        v1_by_is=v1_by_is, v1_is_set=v1_is_set,
        linkages=linkages,                      # the per-context edges
        links_by_is=group_by(linkages, key=lambda l: l.is_number),
        v2_mapped_is=v2_mapped_is,
        v2_by_dd=group_by(v2, key=lambda r: r.dd_ref),
        v1_by_dd=group_by(v1, key=lambda r: r.dd_ref),
        root_rows_by_path={tuple(f.path): f for f in v1 if f.node_kind == "Root"},
    )
```

- **Context preserved** on every edge; comparison engines iterate `idx.linkages`.
- **Sentinels** never create a link.
- Three different IS across the three columns of one V2 row → three independent valid edges (**not** a conflict).
- A `Linkage.v1 is None` means the V2 mapping points to an IS absent in V1 → **G5**.

---

## 5. Gap Analysis Engines

All engines are **pure functions**: `(LinkIndex, config) → list[Gap]`. Registered in a `GapEngineRegistry`; optional rules toggle via config. Comparison engines (G2/G3/G4) iterate **per context-tagged linkage**.

### 5.1 G1 — Coverage funnel (mandatory)

```python
def gap_g1(idx: LinkIndex) -> G1Result:
    A = idx.v1_is_set - idx.v2_mapped_is        # in V1, not referenced in ANY context
    gaps, count_B, count_C = [], 0, 0
    for isn in sorted(A):
        f = idx.v1_by_is[isn]
        nullable_false = (f.nullable is False)            # step B
        parent_min_1 = False
        if nullable_false:
            count_B += 1
            parent = resolve_parent_root(f, idx)          # §6
            parent_min_1 = bool(parent and parent.min_occurs == 1)  # step C
            count_C += int(parent_min_1)
        sev = (Severity.CRITICAL if parent_min_1 else
               Severity.HIGH if nullable_false else Severity.MEDIUM)
        gaps.append(Gap(
            gap_type=GapType.G1_COVERAGE, is_number=isn, mapping_context=None,
            v1_ref=f.source, v1_value=f.attribute,
            detail=f"IS {isn} present in V1, absent in all V2.1 mapping contexts",
            flags={"nullable_false": nullable_false,
                   "parent_root_min_occurs_1": parent_min_1},
            severity=sev, root_node=f.path[0] if f.path else None, dd_ref=f.dd_ref))
    return G1Result(items=gaps, total_missing=len(A),
                    nullable_false=count_B, parent_min1=count_C)
```

**G1 card headline metrics:** `|A|` total missing, `|B|` Nullable=False, `|C|` parent Root Min=1. Each drills into rows. *Optional per-context coverage* (open question HLD §15 Q2) is computed the same way but with `A_ctx = v1_is_set − {IS mapped in that context}`.

**Edge cases:** blank/sentinel IS excluded from `v1_is_set`; duplicate IS in V1 → first wins, duplicate raised to G9.

### 5.2 G2 — Node Min/Max occurrence mismatch (mandatory, per context)

```python
def gap_g2(idx: LinkIndex) -> list[Gap]:
    out = []
    for lk in idx.linkages:
        if lk.v1 is None:
            continue                                  # → G5
        parent = resolve_parent_root(lk.v1, idx)
        v1_min = (parent or lk.v1).min_occurs
        v1_max = (parent or lk.v1).max_occurs
        if not occ_equal(v1_min, lk.v2.min_occurs) or not occ_equal(v1_max, lk.v2.max_occurs):
            arr = is_array(v1_max) or is_array(lk.v2.max_occurs)
            out.append(Gap(
                gap_type=GapType.G2_OCCURRENCE, is_number=lk.is_number,
                mapping_context=lk.context,
                v1_ref=(parent or lk.v1).source, v2_ref=lk.v2.source,
                v1_value=f"min={v1_min},max={fmt(v1_max)}",
                v2_value=f"min={lk.v2.min_occurs},max={fmt(lk.v2.max_occurs)}",
                detail="Occurrence mismatch (V1 parent root vs V2 node)",
                flags={"array_v1": is_array(v1_max), "array_v2": is_array(lk.v2.max_occurs)},
                severity=Severity.HIGH if arr else Severity.MEDIUM,
                root_node=lk.v1.path[0] if lk.v1.path else None, dd_ref=lk.v1.dd_ref))
    return out
```

`occ_equal`: `UNBOUNDED==UNBOUNDED` equal; `1!=UNBOUNDED`; `None` (unspecified) compared explicitly and flagged "indeterminate", never silently equal. **Array nodes** are first-class and tagged.

### 5.3 G3 — Data-type mismatch (mandatory, per context)

```python
def gap_g3(idx: LinkIndex, typemap: TypeMap) -> list[Gap]:
    out = []
    for lk in idx.linkages:
        if lk.v1 is None:
            continue
        v1c = typemap.canon_v1(lk.v1.xsd_type)    # XS:integer -> INTEGER
        v2c = typemap.canon_v2(lk.v2.data_type)   # String     -> STRING
        if v1c != v2c:
            mand = (lk.v1.nullable is False)
            out.append(Gap(
                gap_type=GapType.G3_DATATYPE, is_number=lk.is_number,
                mapping_context=lk.context,
                v1_ref=lk.v1.source, v2_ref=lk.v2.source,
                v1_value=lk.v1.xsd_type_raw, v2_value=lk.v2.data_type_raw,
                detail=f"Data type differs: V1 {lk.v1.xsd_type_raw} vs V2 {lk.v2.data_type_raw}",
                flags={"v1_canon": v1c, "v2_canon": v2c, "unmapped": (v1c is None or v2c is None)},
                severity=Severity.HIGH if mand else Severity.MEDIUM,
                root_node=lk.v1.path[0] if lk.v1.path else None, dd_ref=lk.v1.dd_ref))
    return out
```

### 5.4 Type-equivalence table (externalized config — SME-reviewable)

> Seeded only from values **observed** in the files (`XS:integer`, `XS:string`, `String`, `Object`). Extend as production types appear; this is config, not code. Unmapped tokens → DQ flag, never silently "matched".

| Canonical | V1 `XSD Field Type` | V2 `Data Type` |
|---|---|---|
| `STRING` | `xs:string` | `string` |
| `INTEGER` | `xs:integer`, `xs:int` | `integer`, `number` |
| `OBJECT` | (structural) | `object` |
| `DECIMAL` | `xs:decimal` | `number`, `decimal` |
| `BOOLEAN` | `xs:boolean` | `boolean` |
| `DATE` | `xs:date` | `date` |
| `DATETIME` | `xs:datetime` | `datetime`, `date-time` |

### 5.5 G4 — Mandatory/Optional mismatch (mandatory, per context)

```python
def gap_g4(idx: LinkIndex) -> list[Gap]:
    out = []
    for lk in idx.linkages:
        if lk.v1 is None or lk.v1.nullable is None:
            continue
        v1_expected = "Mandatory" if lk.v1.nullable is False else "Optional"  # CONFIRMED
        v2_val = norm_mandatory(lk.v2.mandatory_optional)
        if v2_val and v2_val != v1_expected:
            out.append(Gap(
                gap_type=GapType.G4_MANDATORY, is_number=lk.is_number,
                mapping_context=lk.context,
                v1_ref=lk.v1.source, v2_ref=lk.v2.source,
                v1_value=f"Nullable={lk.v1.nullable} ⇒ {v1_expected}",
                v2_value=lk.v2.mandatory_optional,
                detail="Mandatory/Optional disagreement",
                flags={}, severity=Severity.MEDIUM,
                root_node=lk.v1.path[0] if lk.v1.path else None, dd_ref=lk.v1.dd_ref))
    return out
```

### 5.6 Optional engines (G5–G9)
- **G5 reverse-orphan:** linkages where `lk.v1 is None` (e.g. V2 maps to `IS2339`, absent in V1).
- **G6 DD mismatch:** for a linkage, `lk.v1.dd_ref != lk.v2.dd_ref`.
- **G7 cardinality:** scalar↔array divergence from `max_occurs` per linkage.
- **G8 duplicate/conflicting (context-aware):** group linkages by `(is_number, context)`; flag when **the same** `(IS, context)` is reached from multiple V2 rows with **inconsistent** type/occurrence/M-O. Three different IS across the three columns of *one* row is **not** flagged.
- **G9 data-quality:** the DQ findings collected during ingestion.

### 5.7 Deterministic gap IDs — **position-independent business key**
The `gap_id` must **not** depend on where a row sits in the spreadsheet, otherwise a re-uploaded Excel with reordered/added rows would mint new IDs and orphan existing comments. It is therefore built **only from stable business identity**, never from `SourceRef` (sheet/row/column):

```python
def make_gap_id(gap_type, is_number, context, v2_business_key, dimension) -> str:
    # v2_business_key = V2 'Schema + JSON Path + Attribute' (full_path) or 'Attribute CLM ID'
    #                   — a stable business id, NOT the row position.
    # dimension       = the compared facet (e.g. 'occ', 'type', 'mand', 'coverage')
    key = "|".join(str(x) for x in
                   [gap_type, is_number or "", context or "", v2_business_key or "", dimension])
    return sha1(key.encode()).hexdigest()[:16]
```

| Gap | Business key used |
|---|---|
| G1 coverage | `gap_type · is_number · 'coverage'` (IS-level; no V2 side) |
| G2/G3/G4 | `gap_type · is_number · context · v2_business_key · dimension` |
| G5 reverse-orphan | `gap_type · is_number · context · v2_business_key` |

Because the key is position-independent, re-uploading the **same** business content yields **identical** `gap_id`s, and **comments/statuses/history re-attach automatically** (§8.4). `mapping_context` keeps per-context gaps distinct. `SourceRef` is still stored on the gap for display/audit — it just never feeds the ID.

> **IS-level anchor.** Independently of the gap key, every comment also stores `is_anchor = is_number`. This is the durable hook the requirement calls for: even if a *specific* gap disappears on re-upload (e.g. a type mismatch the new file fixed), the discussion raised for that **IS Reference Number** is retained and surfaced (§8.4).

---

## 6. Tree Builder & "Immediate Parent Root" Resolution

### 6.1 Build the V1 tree
```python
def build_v1_tree(v1: list[V1Field]) -> TreeNode:
    root = TreeNode(name="(root)", children={})
    for f in v1:
        cur = root
        for level in f.path:                 # trimmed, no trailing blanks
            cur = cur.children.setdefault(level, TreeNode(name=level, children={}))
            cur.node_kind = cur.node_kind or f.node_kind
        cur.fields.append(f)                  # leaf (Element) attaches here
    return root
```
- **Array/repeating nodes** marked when any contributing row has `max_occurs.unbounded`/`>1`, or a non-empty `repeat_remarks` on the V2 side; tree page badges them `[]`.
- Each node aggregates gaps whose `root_node`/path fall under it ("gaps under each root").

### 6.2 Resolve logical parent Root (G1 step C and G2) — **Decision D7**
A field may be enclosed by a **chain of nested Root nodes**. The "immediate parent root" is resolved as the **outermost Root of the contiguous chain** that begins at the field's nearest Root ancestor and climbs while each successive ancestor is also a Root. This yields the logical entity root rather than an inner structural wrapper.

```python
def resolve_parent_root(field: V1Field, idx: LinkIndex) -> Optional[V1Field]:
    roots_by_depth = {}
    for depth in range(len(field.path)):
        cand = idx.root_rows_by_path.get(tuple(field.path[:depth + 1]))
        if cand and (cand.node_kind or "").casefold() == "root":
            roots_by_depth[depth] = cand
    if not roots_by_depth:
        return None
    top = max(roots_by_depth)                 # immediate parent Root
    while (top - 1) in roots_by_depth:         # climb the contiguous Root chain
        top -= 1
    return roots_by_depth[top]                 # outermost (logical) Root
```

`root_rows_by_path` indexes `Node=Root` rows by full path tuple → deterministic, unit-testable. On the sample, an element under `LEDetails`(Root) whose parent `LegalEntity` is also Root resolves to **LegalEntity** (Min=1), so **G1 step C = 3** (IS1/IS2/IS3 are Nullable=False; IS4 is nullable).

---

## 7. REST API Contract

Base URL `http://localhost:8000/api`. JSON; OpenAPI at `/docs`.

| Method | Path | Purpose | Key response |
|---|---|---|---|
| `POST` | `/ingest` | (Re)load v1/v2.1 (configured paths or upload); merge collaboration | ingestion report |
| `GET` | `/summary` | Gap counts per type + severity (landing cards) | summary[] |
| `GET` | `/gaps` | List; query `type,status,severity,context,is,root,search,sort,page,page_size` | paginated rows |
| `GET` | `/gaps/{gap_id}` | Single gap + comments + status history | gap detail |
| `PATCH` | `/gaps/{gap_id}/status` | Set status (records history) | updated gap |
| `PATCH` | `/gaps/status/bulk` | **Bulk** set status over an id list / current filter | count updated |
| `GET` | `/gaps/{gap_id}/comments` | Threaded comments | nested tree |
| `POST` | `/gaps/{gap_id}/comments` | Add comment/reply (`parent_comment_id?`, `author`) | created comment |
| `GET` | `/tree` | V1 tree + gap aggregates per node | tree JSON |
| `GET` | `/v2/by-dd/{dd}` | **Fetch V2 By DD** from loaded workbook | V2Field[] |
| `GET` | `/export` | Export current filter (CSV / multi-sheet XLSX) | file stream |
| `GET`/`POST` | `/views` | List/save **saved views** (filter+columns+sort) | view[] |
| `GET` | `/health` | Liveness | `{status:"ok"}` |

### 7.1 Representative payloads

`GET /summary`
```json
[
  {"gap_type":"G1_COVERAGE","total":12,
   "metrics":{"total_missing":12,"nullable_false":7,"parent_min1":4},
   "by_status":{"Open":12,"Accepted":0,"Not applicable":0},
   "by_severity":{"Critical":4,"High":3,"Medium":5}},
  {"gap_type":"G3_DATATYPE","total":9,"by_status":{"Open":9}}
]
```

`GET /gaps?type=G3_DATATYPE&context=RP_ORG`
```json
{"page":1,"page_size":50,"total":3,
 "rows":[
   {"gap_id":"9f3a...","gap_type":"G3_DATATYPE","is_number":"IS4",
    "mapping_context":"RP_ORG","v1_value":"XS:string","v2_value":"String",
    "severity":"Medium","status":"Open","dd_ref":"DD1490",
    "root_node":"Message","comment_count":2}]}
```

`PATCH /gaps/status/bulk`
```json
// request
{"gap_ids":["9f3a...","b21c..."],"status":"Not applicable","author":"jdoe","note":"Out of scope for RP ORG"}
// response
{"updated":2}
```

---

## 8. Storage Abstraction (durable in BOTH modes)

### 8.1 Repository interface
```python
class Repository(Protocol):
    def replace_dataset(self, v1, v2, gaps, *, merge_collab: bool = True) -> None: ...
    def summary(self) -> list[GapSummary]: ...
    def query_gaps(self, q: GapQuery) -> Page[Gap]: ...
    def get_gap(self, gap_id: str) -> Gap | None: ...
    def set_status(self, gap_id, status, author, note=None) -> Gap: ...
    def bulk_status(self, gap_ids, status, author, note=None) -> int: ...
    def status_history(self, gap_id: str) -> list[StatusChange]: ...
    def list_comments(self, gap_id: str) -> list[Comment]: ...
    def add_comment(self, c: Comment) -> Comment: ...
    def tree(self) -> TreeNode: ...
    def v2_by_dd(self, dd: str) -> list[V2Field]: ...
    def list_views(self) -> list[SavedView]: ...
    def save_view(self, v: SavedView) -> SavedView: ...
```
Selected at startup:
```python
REPO = (InMemoryRepository(snapshot=settings.SNAPSHOT_PATH)
        if settings.STORAGE == "memory"
        else PostgresRepository(settings.DATABASE_URL))
```

### 8.2 In-memory implementation — **durable via SQLite snapshot**
- **Fast path (RAM):** gaps/fields/tree held in dicts + secondary indexes (`by_type`, `by_status`, `by_severity`, `by_context`, `by_dd`) for query speed.
- **Durable path (disk):** collaboration tables — `comment`, `gap_status`, `status_history`, `saved_view` — persisted to a local **SQLite file** (`SNAPSHOT_PATH`, default `./.gapdb.sqlite`). Gaps/fields are **recomputed** from Excel on each start (cheap, deterministic) and re-joined to persisted collaboration by `gap_id`.
- Net effect: **comments/statuses/history/views survive restarts** with zero external services — satisfying the "in-memory must persist" requirement, while keeping fast in-RAM querying.

### 8.3 PostgreSQL schema (DDL)
```sql
CREATE TABLE gap (
    gap_id        VARCHAR(32) PRIMARY KEY,
    gap_type      VARCHAR(32) NOT NULL,
    is_number     VARCHAR(64),
    mapping_context VARCHAR(16),         -- Entity / RP_IND / RP_ORG / NULL
    v1_value      TEXT,
    v2_value      TEXT,
    detail        TEXT,
    flags         JSONB DEFAULT '{}'::jsonb,
    severity      VARCHAR(12) NOT NULL DEFAULT 'Medium',
    root_node     VARCHAR(255),
    dd_ref        VARCHAR(64),
    v1_ref        JSONB,
    v2_ref        JSONB,
    status        VARCHAR(20) NOT NULL DEFAULT 'Open'
);
CREATE INDEX idx_gap_type ON gap(gap_type);
CREATE INDEX idx_gap_status ON gap(status);
CREATE INDEX idx_gap_sev ON gap(severity);
CREATE INDEX idx_gap_ctx ON gap(mapping_context);
CREATE INDEX idx_gap_dd ON gap(dd_ref);
CREATE INDEX idx_gap_root ON gap(root_node);

CREATE TABLE comment (
    comment_id        VARCHAR(40) PRIMARY KEY,
    gap_id            VARCHAR(32),                       -- nullable: may be NULL if gap resolved
    is_anchor         VARCHAR(64),                       -- IS Reference Number (durable hook)
    mapping_context   VARCHAR(16),                       -- context it was raised in
    parent_comment_id VARCHAR(40) REFERENCES comment(comment_id) ON DELETE CASCADE,
    author            VARCHAR(255) NOT NULL,
    body              TEXT NOT NULL,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_comment_gap ON comment(gap_id);
CREATE INDEX idx_comment_anchor ON comment(is_anchor);   -- retain-by-IS lookups
CREATE INDEX idx_comment_parent ON comment(parent_comment_id);
-- NOTE: gap_id FK is intentionally soft (no hard CASCADE) so a comment outlives a
-- gap that disappears on re-upload; it stays reachable via is_anchor.

CREATE TABLE status_history (
    id          BIGSERIAL PRIMARY KEY,
    gap_id      VARCHAR(32) NOT NULL REFERENCES gap(gap_id) ON DELETE CASCADE,
    old_status  VARCHAR(20),
    new_status  VARCHAR(20) NOT NULL,
    author      VARCHAR(255) NOT NULL,
    note        TEXT,
    changed_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_hist_gap ON status_history(gap_id);

CREATE TABLE saved_view (
    view_id   VARCHAR(40) PRIMARY KEY,
    name      VARCHAR(255) NOT NULL,
    owner     VARCHAR(255),
    spec      JSONB NOT NULL         -- {filters, columns, sort}
);

-- Raw canonical rows retained for "Fetch V2 By DD" and audit
CREATE TABLE v2_field (id BIGSERIAL PRIMARY KEY, dd_ref VARCHAR(64), payload JSONB NOT NULL);
CREATE INDEX idx_v2_dd ON v2_field(dd_ref);
CREATE TABLE v1_field (id BIGSERIAL PRIMARY KEY, is_number VARCHAR(64), dd_ref VARCHAR(64), payload JSONB NOT NULL);
CREATE INDEX idx_v1_is ON v1_field(is_number);
```
- Threaded comments use the **adjacency list** `parent_comment_id`; the API assembles the tree (or `WITH RECURSIVE`).
- The same logical tables exist in the SQLite snapshot for in-memory mode.

### 8.4 Re-upload merge — comment retention by IS Reference Number (F13)
This is the explicit requirement: **uploading a new Excel must retain the comments raised against the old IS Reference Numbers.** Because `gap_id` is now position-independent (§5.7) and comments carry `is_anchor`, retention is two-tier and lossless:

```python
def reingest(new_v1, new_v2):
    new_gaps = run_all_engines(resolve_links(new_v1, new_v2))   # fresh gaps
    new_ids   = {g.gap_id for g in new_gaps}
    old_ids   = repo.all_gap_ids()

    repo.upsert_gaps(new_gaps)            # gaps replaced by business identity, not row

    # Tier 1 — exact gap match: comments/status/history already point at the same
    # gap_id (same IS + context + business key) → they re-attach automatically. No-op.

    # Tier 2 — gap resolved/removed by the new file:
    for cid in old_ids - new_ids:
        comments = repo.comments_for_gap(cid)        # keyed on is_anchor too
        for c in comments:
            # keep the thread; detach from the now-absent gap, keep IS anchor
            repo.update_comment(c.comment_id, gap_id=None)   # stays reachable via is_anchor
        repo.mark_gap(cid, stale=True)               # hidden by default, never deleted

    # Tier 3 — same IS reappears under a *new* gap on re-upload:
    #   the IS-anchored thread is surfaced on that IS's gaps (see retrieval below).
    summary = {"new": len(new_ids - old_ids),
               "unchanged": len(new_ids & old_ids),
               "resolved_retained": len(old_ids - new_ids),
               "comments_retained": repo.count_comments()}     # never decreases
    return summary
```

**Retrieval contract.** When the UI opens a gap, `GET /gaps/{gap_id}/comments` returns:
1. comments whose `gap_id` matches (exact), **plus**
2. comments with the same `is_anchor` (+ context) whose original gap is now `stale` — rendered under a **"Earlier discussion for IS &lt;x&gt;"** divider.

So a reviewer always sees the full conversation history for that IS Reference Number, regardless of how rows shifted between uploads. The ingestion summary banner reports `new / unchanged / resolved-retained / comments-retained`, and `comments_retained` is asserted **non-decreasing** across uploads in tests (§14).

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant ENG as Gap Engines
    participant DB as Store
    U->>API: POST /ingest (new v2.1.xlsx)
    API->>ENG: recompute gaps (position-independent ids)
    ENG-->>API: new gaps
    API->>DB: upsert gaps by business key
    API->>DB: re-link comments by gap_id (exact) + is_anchor (fallback)
    API->>DB: mark vanished gaps stale (keep threads)
    API-->>U: summary {new, unchanged, resolved_retained, comments_retained}
```

---

## 9. Collaboration: Comments, Threads, Status, Audit

### 9.1 Threaded comment assembly
```python
def assemble_thread(flat: list[Comment]) -> list[CommentNode]:
    by_parent = defaultdict(list)
    for c in sorted(flat, key=lambda x: x.created_at):
        by_parent[c.parent_comment_id].append(c)
    def build(pid):
        return [CommentNode(**c.dict(), replies=build(c.comment_id))
                for c in by_parent.get(pid, [])]
    return build(None)
```
UI renders nested replies (Facebook-style): root → indented replies → reply box per node.

### 9.2 Author identity (no-auth phase) — **CONFIRMED: locally-entered display name**
No login this phase. On first use the UI captures a **display name** (`DisplayNamePrompt`, stored in `localStorage`) and sends it as `author` on comments/status changes; the backend records it verbatim. This is **attribution data, not a security control**. (Decision D5, HLD §15.)

### 9.3 Status workflow + history
`Open` (default) → `Accepted` / `Not applicable`; any→any allowed. Every change writes a `status_history` row (`old`, `new`, `author`, `note`, `changed_at`). Status is a filterable/sortable chip; bulk disposition writes one history row per affected gap.

---

## 10. "Fetch V2 By DD"
Every gap carries `dd_ref`. The link calls `GET /api/v2/by-dd/{dd}`; the service looks up the DD in the **loaded v2.1 workbook** (`v2_by_dd` index/table) and returns the full row(s) with all 20 columns (raw values preserved). Absent DD → `[]` and UI shows "No V2.1 record for DD <x>". No external system is contacted this phase.

---

## 11. Frontend Design (React + TypeScript)

### 11.1 Component tree
```
App
├─ Router
│  ├─ /            LandingPage
│  │   └─ GapCard[]            (per gap type; G1 shows A/B/C funnel; severity counts)
│  ├─ /gaps/:type GapTablePage
│  │   ├─ DataGrid             (TanStack Table)
│  │   │   ├─ Toolbar (search, status/severity/context filters, column-visibility, export, saved views)
│  │   │   ├─ BulkBar (select → set status / comment)
│  │   │   └─ Row → expand → ConversationPanel + FetchV2ByDD button + status history
│  │   └─ Pagination
│  └─ /tree       TreePage
│      ├─ V1TreeView (virtualized; array nodes badged [])
│      └─ NodeGapsPanel  (gaps under selected node)
├─ ConversationPanel   (threaded comments + reply boxes)
├─ FetchV2ByDDModal
├─ DisplayNamePrompt    (sets author once)
└─ StatusChip / SeverityChip / ContextChip / GapTypeBadge (shared)
```

### 11.2 Landing page (cards → table)
- One `GapCard` per gap type. The **G1 card** shows the three funnel numbers (`total_missing`, `nullable_false`, `parent_min1`); all cards show status + severity breakdown.
- Click a card → `/gaps/:type` table.

### 11.3 Data grid features (F7, F10, F11)
| Feature | Implementation |
|---|---|
| **Sorting** | TanStack `getSortedRowModel` per column |
| **Filtering** | Column filters + global search; **context** & **severity** filters; server-side via `/gaps` query for large sets |
| **Column show/hide** | TanStack column-visibility menu, persisted in `localStorage` and saved views |
| **Export** | Client export of current view (CSV/XLSX); `/export` for full filtered set; multi-sheet workbook (one sheet per gap type) |
| **Bulk disposition** | Row selection → `PATCH /gaps/status/bulk` |
| **Saved views** | Named filter+column+sort presets via `/views` |
| **Scale** | Server pagination + row virtualization for ~2,000 rows |

### 11.4 Tree page (F6)
Built from `GET /tree`; each node shows a gap-count badge; selecting a node lists its gaps (reusing grid + conversation). Array/repeating nodes badged.

### 11.5 State & data
TanStack Query for server state; mutations (comment, status, bulk) optimistic, then invalidate `/gaps` & `/summary`.

---

## 12. Configuration

`.env` / `settings.py`:
```
STORAGE=memory               # memory | postgres   (both durable)
SNAPSHOT_PATH=./.gapdb.sqlite # used when STORAGE=memory
DATABASE_URL=postgresql+psycopg://user:pass@localhost:5432/gapdb
V1_PATH=./v1.xlsx
V2_PATH=./v2.1.xlsx
ENABLE_OPTIONAL_GAPS=false   # toggles G5–G9
TYPE_MAP_PATH=./config/type_equivalence.yaml
MANDATORY_CONVENTION=nullable_false_is_mandatory   # CONFIRMED
G1_COVERAGE_SCOPE=any_context # any_context | per_context  (open question)
```
Switching storage requires no code change — only `STORAGE` (+ `DATABASE_URL` for postgres).

---

## 13. Error Handling & Validation
- **Ingestion errors** (header not found, unreadable file) → `422` + actionable message; UI banner.
- **Type token not in equivalence map** → not fatal; DQ flag; engine marks "indeterminate type" (styled distinctly, never silently matched).
- **Indeterminate comparisons** (missing occurrence/type) → flagged, never assumed equal.
- **Idempotency**: re-ingest preserves comments/status/history via deterministic `gap_id` + merge (§8.4).
- All raw source values preserved → **no fabricated data** ever reaches the UI.

---

## 14. Test Strategy

| Level | Coverage |
|---|---|
| **Unit** | normalization (casing/sentinel/typo from sample), occurrence parsing (unbounded/array), type-equivalence, `resolve_parent_root`, each gap engine incl. **per-context** fan-out, G1 funnel counts, G8 context-awareness |
| **Fixture** | provided `v1.xlsx`/`v2.1.xlsx` as golden sample with asserted gap counts per context |
| **Integration** | `/ingest → /summary → /gaps → /comments → /status → /status/bulk` on both stores |
| **Durability** | restart in memory mode → comments/status/history/views survive (snapshot) |
| **Store parity** | identical results from In-Memory(+snapshot) and PostgreSQL |
| **Re-ingest merge** | changed dataset keeps collaboration; stale gaps flagged not deleted |
| **Re-upload retention (F13)** | upload a new Excel with the **same IS on a different row** → comment re-attaches (position-independent `gap_id`); resolve a gap in the new file → its thread retained via `is_anchor` and shown as "Earlier discussion for IS"; assert `comments_retained` never decreases |
| **Scale** | synthetic ~2,000-row set with array nodes + 3-context mappings → perf + correctness |
| **Frontend** | grid sort/filter/column/export/bulk; threaded-comment render; tree gap aggregation; context/severity filters |

---

## 15. Proposed Repository Layout
```
V2.1toV1Schema_Conversion/
├─ backend/
│  ├─ app/
│  │  ├─ main.py                 # FastAPI app + routers
│  │  ├─ config.py
│  │  ├─ models/                 # canonical, linkage(context), gap/comment/status
│  │  ├─ ingestion/              # excel_loader.py, normalize.py, validate.py
│  │  ├─ domain/                 # linkage.py (per-context), tree.py
│  │  ├─ gaps/                   # registry.py, g1..g9.py, typemap.py, severity.py
│  │  ├─ repositories/           # base.py, memory.py (+sqlite snapshot), postgres.py
│  │  ├─ services/               # comment, status(+history), v2_lookup, views
│  │  └─ api/                    # routers
│  ├─ config/type_equivalence.yaml
│  └─ tests/
└─ frontend/
   ├─ src/
   │  ├─ pages/ (LandingPage, GapTablePage, TreePage)
   │  ├─ components/ (DataGrid, BulkBar, ConversationPanel, FetchV2ByDDModal,
   │  │              GapCard, V1TreeView, DisplayNamePrompt, chips)
   │  ├─ api/ (client, queries)
   │  └─ types/
   └─ index.html
```

---

## 16. Traceability — requirement → design element

| Requirement | HLD | LLD |
|---|---|---|
| IS-number linkage, **3 contexts** (Entity/RP IND/RP ORG) | §2.3 | §2.2, §4 |
| G1 coverage funnel (A→B→C counts) | §7 G1 | §5.1, §6.2 |
| G2 occurrence comparison (per context, arrays) | §7 G2 | §5.2 |
| G3 data-type comparison (per context) | §7 G3 | §5.3–5.4 |
| G4 mandatory/optional (`Nullable=False⇒Mandatory`) | §7 G4 | §5.5 |
| Comments + threaded replies | §10 F1–F2 | §2.3, §8.3, §9.1 |
| Status Open/Accepted/Not applicable (+ history) | §10 F3 | §9.3, §8.3 |
| Fetch V2 By DD (loaded file) | §10 F4 | §7, §10 |
| Landing cards → table | §10 F5 | §11.1–11.2 |
| V1 tree with gaps per root | §10 F6 | §6, §11.4 |
| Table sort/filter/column/export | §10 F7 | §11.3 |
| Bulk disposition / saved views / audit | §10 F10–F12 | §7, §9, §11.3 |
| **Comment retention on Excel re-upload (by IS Ref No)** | §10 F13 | §5.7, §8.4 |
| Durable in-memory + PostgreSQL | §11 | §8 |
| Python + React, local | §11 | §11, §15 |
| Scale ~2,000 + array nodes | §12 | §5.2, §6.1, §14 |
| Severity ranking | §8 | §2.3, §5 |
| No hallucinated data | §2.4 | §3.2, §13 |

---
*End of LLD.*
