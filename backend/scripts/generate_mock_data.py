"""Generate ~2000-row mock V1 and V2.1 workbooks covering every gap scenario.

Output: <project root>/mockdata/v1_mock.xlsx and v2.1_mock.xlsx
Deterministic (seeded). Does NOT touch the golden fixtures v1.xlsx / v2.1.xlsx.

Scenarios exercised:
  - G1 coverage (IS in V1 not mapped in V2.1), with nullable T/F and parent-root
    min=1 variations to populate the A/B/C funnel
  - G2 occurrence mismatch incl. scalar<->array (unbounded / N>1 roots)
  - G3 data-type mismatch (canonical type differs)
  - G4 mandatory/optional mismatch (Nullable=False => Mandatory convention)
  - G5 reverse-orphan (V2 maps to an IS absent from V1)
  - per-context mappings (Entity / RP IND / RP ORG), incl. single rows that map
    three different V1 IS across the three columns
  - data-quality noise: 'Not APplicable' casing, attribute names with spaces,
    duplicate IS numbers
  - deep, varied Level paths for the Path column / multi-select

Run (from backend/, venv active):  python scripts/generate_mock_data.py
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

from openpyxl import Workbook

random.seed(42)

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "mockdata"
OUT.mkdir(exist_ok=True)

V1_HEADERS = [
    "IS Reference Number", "CC DD Ref No", "Node",
    "Level 1", "Level 2", "Level 3", "Level 4", "Level 5", "Level 6", "Level 7", "Level 8",
    "Attribute", "XSD Field Type", "Nullable", "Min Occurrence", "Max Occurrence",
]
V2_HEADERS = [
    "Schema Name + JSON Path", "CLMT IS Reference Number", "Version Number", "Change Log",
    "Attribute CLM ID", "CCDM Attribute Name", "Source DD#",
    "CC_V1_Mapping Entity", "CC_V1_Mapping RP IND", "CC_V1_Mapping RP ORG",
    "Remarks For Repeating Block", "Node / Element", "Schema Name", "JSON Attribute Name",
    "Data Type", "Min Occurrence", "Max Occurrence", "Mandatory / Optional",
    "Schema + JSON Path + Attribute", "Mapping Remarks",
]

# (V1 XSD type, matching V2 Data Type) — canonical-equivalent pairs
TYPE_PAIRS = [
    ("xs:string", "String"), ("xs:integer", "Integer"), ("xs:decimal", "Decimal"),
    ("xs:boolean", "Boolean"), ("xs:date", "Date"), ("xs:dateTime", "DateTime"),
]
V2_TYPE_BY_CANON = {"xs:string": "String", "xs:integer": "Integer", "xs:decimal": "Decimal",
                    "xs:boolean": "Boolean", "xs:date": "Date", "xs:dateTime": "DateTime"}

FAMILIES = [
    "LegalEntity", "Account", "Party", "Transaction", "Address", "Instrument",
    "Settlement", "Collateral", "Counterparty", "Product", "Trade", "Position",
    "Portfolio", "Reference", "Contact", "Document", "Risk", "Limit", "Fee", "Tax",
    "Currency", "Country", "Identifier", "Classification", "Rating", "Event",
    "Schedule", "Cashflow", "Margin", "Custody",
]
NOUNS = ["Id", "Code", "Name", "Type", "Status", "Date", "Amount", "Rate", "Number",
         "Indicator", "Description", "Category", "Reference", "Sequence", "Value",
         "Flag", "Country", "Currency", "Method", "Level"]

SENTINELS_CLEAN = ["Not Applicable"]
SENTINELS_DQ = ["Not APplicable", "N/A", "", "not applicable"]   # casing/format noise


def sentinel() -> str:
    return random.choice(SENTINELS_DQ) if random.random() < 0.18 else "Not Applicable"


def occ_max():
    return random.choice([1, 1, 1, 5, "unbounded"])


# --- build V1 -----------------------------------------------------------------

v1_rows: list[dict] = []
elements: list[dict] = []   # element metadata for V2 generation
is_n = 1
dd_n = 1

# root metadata per family: top root min/max (the D7 outermost root)
family_roots: dict[str, dict] = {}
containers: list[dict] = []   # {path, family, parent_min, parent_max}

for fam in FAMILIES:
    top_min = random.choice([1, 1, 1, 0])
    top_max = occ_max()
    family_roots[fam] = {"min": top_min, "max": top_max}
    v1_rows.append({"Node": "Root", "Level 1": "Message", "Level 2": fam,
                    "Min Occurrence": top_min, "Max Occurrence": top_max})

    details = fam + "Details"
    contiguous = random.random() < 0.6
    if contiguous:   # nested Root -> exercises the D7 contiguous-chain climb
        v1_rows.append({"Node": "Root", "Level 1": "Message", "Level 2": fam, "Level 3": details,
                        "Min Occurrence": random.choice([1, 0]), "Max Occurrence": occ_max()})

    leaf_paths = [["Message", fam, details]]
    if random.random() < 0.5:   # array/repeating block (Root, unbounded)
        blk = random.choice(["History", "Lines", "Items", "Entries"])
        v1_rows.append({"Node": "Root", "Level 1": "Message", "Level 2": fam, "Level 3": details,
                        "Level 4": blk, "Min Occurrence": 0, "Max Occurrence": "unbounded"})
        leaf_paths.append(["Message", fam, details, blk])
    if random.random() < 0.5:   # deeper non-root container for path variety
        leaf_paths.append(["Message", fam, details, "Sub" + fam, "Item"])

    for lp in leaf_paths:
        containers.append({"path": lp, "family": fam,
                           "parent_min": top_min, "parent_max": top_max})

TARGET_V1 = 2000
n_elements = TARGET_V1 - len(v1_rows)

for i in range(n_elements):
    c = random.choice(containers)
    xsd, v2match = random.choice(TYPE_PAIRS)
    nullable = random.random() < 0.5
    isnum = f"IS{is_n:04d}"
    ddref = f"DD{dd_n:04d}"
    is_n += 1
    dd_n += 1
    noun = random.choice(NOUNS)
    attr = c["family"][0].lower() + c["family"][1:] + noun
    if random.random() < 0.03:        # DQ: attribute name with a space
        attr = attr + " " + random.choice(["X", "v2", "tmp"])
    row = {"IS Reference Number": isnum, "CC DD Ref No": ddref, "Node": "Element",
           "Attribute": attr, "XSD Field Type": xsd, "Nullable": nullable}
    for li, name in enumerate(c["path"], start=1):
        row[f"Level {li}"] = name
    v1_rows.append(row)
    elements.append({"is": isnum, "dd": ddref, "xsd": xsd, "v2match": v2match,
                     "nullable": nullable, "family": c["family"], "attr": attr,
                     "parent_min": c["parent_min"], "parent_max": c["parent_max"]})

# DQ: a couple of duplicate IS numbers
if len(elements) > 5:
    dup = dict(elements[3])
    v1_rows.append({"IS Reference Number": dup["is"], "CC DD Ref No": dup["dd"], "Node": "Element",
                    "Level 1": "Message", "Level 2": dup["family"], "Attribute": dup["attr"] + "Dup",
                    "XSD Field Type": dup["xsd"], "Nullable": dup["nullable"]})


# --- build V2.1 ---------------------------------------------------------------

v2_rows: list[dict] = []
clm_n = 1


def other_v2_type(canon_xsd: str) -> str:
    """Return a V2 Data Type whose canonical differs from the V1 type."""
    choices = [t for x, t in TYPE_PAIRS if x != canon_xsd]
    return random.choice(choices)


def make_v2_element(schema_fam, jsonattr, dd, data_type, vmin, vmax, mo,
                    entity, rp_ind, rp_org, repeating):
    global clm_n
    row = {
        "Schema Name + JSON Path": f"CCDM.{schema_fam}",
        "CLMT IS Reference Number": f"CLMT-IS-Ref-{clm_n:04d}",
        "Version Number": "V1.0",
        "Attribute CLM ID": f"CLM{clm_n:04d}",
        "CCDM Attribute Name": jsonattr,
        "Source DD#": dd,
        "CC_V1_Mapping Entity": entity,
        "CC_V1_Mapping RP IND": rp_ind,
        "CC_V1_Mapping RP ORG": rp_org,
        "Remarks For Repeating Block": "Repeating block" if repeating else sentinel(),
        "Node / Element": "Element",
        "Schema Name": f"CCDM.{schema_fam}",
        "JSON Attribute Name": jsonattr,
        "Data Type": data_type,
        "Min Occurrence": vmin,
        "Max Occurrence": vmax,
        "Mandatory / Optional": mo,
        "Schema + JSON Path + Attribute": f"[CCDM.{schema_fam}].{jsonattr}",
        "Mapping Remarks": "",
    }
    clm_n += 1
    return row


def map_columns(isnum: str, context: str):
    """Place isnum in the chosen context column; sentinels elsewhere."""
    cols = {"Entity": sentinel(), "RP IND": sentinel(), "RP ORG": sentinel()}
    cols[context] = isnum
    return cols["Entity"], cols["RP IND"], cols["RP ORG"]


# Decide each element's fate. ~22% unmapped (G1). Mapped ones get a scenario.
random.shuffle(elements)
unmapped_count = 0
i = 0
while i < len(elements):
    e = elements[i]
    r = random.random()

    # ~10%: pack three consecutive elements into ONE multi-context V2 row
    if r < 0.10 and i + 2 < len(elements):
        e1, e2, e3 = elements[i], elements[i + 1], elements[i + 2]
        # shared row data type/occurrence -> some of the three will mismatch
        dt = random.choice([V2_TYPE_BY_CANON[e1["xsd"]], other_v2_type(e1["xsd"])])
        v2_rows.append(make_v2_element(
            e1["family"], e1["attr"], e1["dd"], dt,
            e1["parent_min"], e1["parent_max"],
            "Mandatory" if not e1["nullable"] else "Optional",
            e1["is"], e2["is"], e3["is"], repeating=False))
        i += 3
        continue

    if r < 0.32:                      # ~22% unmapped -> G1 coverage
        unmapped_count += 1
        i += 1
        continue

    # mapped — choose a mismatch scenario
    scenario = random.choices(
        ["clean", "type", "mo", "occ", "dd"], weights=[32, 18, 18, 18, 14])[0]
    derived_mo = "Mandatory" if not e["nullable"] else "Optional"
    data_type = e["v2match"]
    vmin, vmax = e["parent_min"], e["parent_max"]
    mo = derived_mo
    v2_dd = e["dd"]

    if scenario == "type":
        data_type = other_v2_type(e["xsd"])
    elif scenario == "mo":
        mo = "Optional" if derived_mo == "Mandatory" else "Mandatory"
    elif scenario == "occ":
        # diverge from the parent root occurrence (often scalar<->array -> G2 + G7)
        vmax = 1 if vmax == "unbounded" else "unbounded"
        vmin = 0 if e["parent_min"] == 1 else 1
    elif scenario == "dd":
        v2_dd = f"DDX{random.randint(1000, 9999)}"   # differs from V1 -> G6

    context = random.choice(["Entity", "RP IND", "RP ORG"])
    ent, ind, org = map_columns(e["is"], context)
    v2_rows.append(make_v2_element(
        e["family"], e["attr"], v2_dd, data_type, vmin, vmax, mo,
        ent, ind, org, vmax == "unbounded"))

    # duplicate mapping (G8): ~6% — a 2nd V2 row maps the SAME IS in the SAME context
    if random.random() < 0.06:
        ent2, ind2, org2 = map_columns(e["is"], context)
        v2_rows.append(make_v2_element(
            e["family"], e["attr"] + "Alt", e["dd"], e["v2match"],
            e["parent_min"], e["parent_max"], derived_mo,
            ent2, ind2, org2, e["parent_max"] == "unbounded"))
    i += 1

# reverse orphans (G5): V2 maps to IS not present in V1
for k in range(30):
    fam = random.choice(FAMILIES)
    ctx = random.choice(["Entity", "RP IND", "RP ORG"])
    ent, ind, org = map_columns(f"IS9{k:03d}", ctx)
    v2_rows.append(make_v2_element(
        fam, f"orphanAttr{k}", f"DD9{k:03d}", "String", 1, 1, "Optional",
        ent, ind, org, repeating=False))

# structural Node rows + DQ json-attr spaces, to round out ~2000
while len(v2_rows) < 2000:
    fam = random.choice(FAMILIES)
    if random.random() < 0.5:
        v2_rows.append({
            "Schema Name + JSON Path": f"CCDM.{fam}", "Version Number": "V1.0",
            "Attribute CLM ID": "Not Applicable", "Node / Element": "Node",
            "Schema Name": f"CCDM.{fam}", "Data Type": "Object",
            "Min Occurrence": 1, "Max Occurrence": occ_max(),
            "CC_V1_Mapping Entity": sentinel(), "CC_V1_Mapping RP IND": sentinel(),
            "CC_V1_Mapping RP ORG": sentinel(),
        })
    else:
        ja = f"{fam[0].lower()}{fam[1:]}Extra {random.choice(NOUNS)}"  # space = DQ
        v2_rows.append(make_v2_element(fam, ja, f"DD{dd_n:04d}", "String", 1, 1,
                                       "Optional", sentinel(), sentinel(), sentinel(), False))
        dd_n += 1


# --- write workbooks ----------------------------------------------------------

def write(path: Path, headers: list[str], rows: list[dict]):
    wb = Workbook()
    ws = wb.active
    ws.title = "Sheet 1"
    ws.append(headers)
    for row in rows:
        ws.append([row.get(h) for h in headers])
    wb.save(path)


write(OUT / "v1_mock.xlsx", V1_HEADERS, v1_rows)
write(OUT / "v2.1_mock.xlsx", V2_HEADERS, v2_rows)

print(f"V1 rows: {len(v1_rows)}  (elements={len(elements)}, unmapped~={unmapped_count})")
print(f"V2 rows: {len(v2_rows)}")
print(f"written to {OUT}")

# --- optional: run the analysis to report the gap distribution ---------------
if "--analyze" in sys.argv:
    sys.path.insert(0, str(ROOT / "backend"))
    from app.gaps.typemap import TypeMap            # noqa: E402
    from app.ingestion.service import run_ingestion  # noqa: E402
    from app.services.analysis import analyze        # noqa: E402

    v1, v2, report = run_ingestion(OUT / "v1_mock.xlsx", OUT / "v2.1_mock.xlsx")
    tm = TypeMap.load(ROOT / "backend" / "config" / "type_equivalence.yaml")
    res = analyze(v1, v2, tm, enable_optional=True, dq_findings=report.findings)
    print("\n--- ingestion ---")
    print(f"V1 fields={report.v1_rows}  V2 fields={report.v2_rows}  "
          f"IS={report.v1_is_numbers}  links={report.v2_mapping_links}  DQ={report.by_code}")
    print("--- gaps ---")
    for s in res.summary:
        extra = f"  metrics={s.metrics}" if s.metrics else ""
        print(f"  {s.gap_type:18} total={s.total:4}  sev={dict(s.by_severity)}{extra}")
