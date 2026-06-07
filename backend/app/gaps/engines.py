"""Gap engines (LLD v1.2 §5). Pure functions: (LinkIndex, TypeMap) -> list[Gap].

Comparison engines (G2/G3/G4) iterate per context-tagged linkage and tag each
gap with its mapping_context. G1 is IS-level coverage; G5 is the reverse-orphan.
"""
from __future__ import annotations

from typing import Optional

from app.domain.linkage import LinkIndex
from app.domain.tree import resolve_parent_root
from app.gaps import severity as sev
from app.gaps.gap_id import make_gap_id, v2_business_key
from app.gaps.typemap import TypeMap
from app.ingestion import normalize as N
from app.models.canonical import Occurs, SourceRef
from app.models.gap import Gap, GapType, Severity


# --- helpers ------------------------------------------------------------------

def _fmt_max(o: Occurs) -> str:
    return "unbounded" if o.unbounded else ("" if o.value is None else str(o.value))


def _min_equal(a: Optional[int], b: Optional[int]) -> bool:
    return a == b


def _max_equal(a: Occurs, b: Occurs) -> bool:
    if a.unbounded or b.unbounded:
        return a.unbounded and b.unbounded
    return a.value == b.value


def _join_path(path: list[str]) -> Optional[str]:
    return " > ".join(path) if path else None


def _norm_mandatory(value) -> Optional[str]:
    s = N.clean(value)
    if not s:
        return None
    low = s.casefold()
    if low.startswith("mandat") or low in {"m", "required", "req", "mand"}:
        return "Mandatory"
    if low.startswith("option") or low in {"o", "opt"}:
        return "Optional"
    return s  # unknown -> returned as-is, will compare unequal


# --- G1: coverage funnel ------------------------------------------------------

def run_g1(idx: LinkIndex, _typemap: TypeMap | None = None) -> list[Gap]:
    v2_dds = set(idx.v2_by_dd)
    gaps: list[Gap] = []
    for isn in sorted(idx.missing_in_v2()):
        f = idx.v1_by_is[isn]
        nullable_false = f.nullable is False
        parent_min_1 = False
        if nullable_false:
            parent = resolve_parent_root(f, idx)
            parent_min_1 = bool(parent and parent.min_occurs == 1)
        gaps.append(Gap(
            gap_id=make_gap_id(GapType.G1_COVERAGE, isn, None, "", "coverage"),
            gap_type=GapType.G1_COVERAGE, is_number=isn, mapping_context=None,
            v1_path=_join_path(f.path), v1_ref=f.source, v1_value=f.attribute,
            detail=f"IS {isn} present in V1, absent in all V2.1 mapping contexts",
            flags={"nullable_false": nullable_false,
                   "parent_root_min_occurs_1": parent_min_1},
            severity=sev.coverage_severity(nullable_false, parent_min_1),
            root_node=f.path[0] if f.path else None, dd_ref=f.dd_ref,
            dd_in_v2=bool(f.dd_ref and f.dd_ref in v2_dds),
        ))
    return gaps


# --- G2: occurrence mismatch (per context) ------------------------------------

def run_g2(idx: LinkIndex, _typemap: TypeMap | None = None) -> list[Gap]:
    v2_dds = set(idx.v2_by_dd)
    gaps: list[Gap] = []
    for lk in idx.resolved_links():
        parent = resolve_parent_root(lk.v1, idx) or lk.v1
        v1_min, v1_max = parent.min_occurs, parent.max_occurs
        if _min_equal(v1_min, lk.v2.min_occurs) and _max_equal(v1_max, lk.v2.max_occurs):
            continue
        arr = v1_max.is_array or lk.v2.max_occurs.is_array
        gaps.append(Gap(
            gap_id=make_gap_id(GapType.G2_OCCURRENCE, lk.is_number, lk.context,
                               v2_business_key(lk.v2), "occ"),
            gap_type=GapType.G2_OCCURRENCE, is_number=lk.is_number,
            mapping_context=lk.context, v1_path=_join_path(lk.v1.path),
            v1_ref=parent.source, v2_ref=lk.v2.source,
            v1_value=f"min={v1_min},max={_fmt_max(v1_max)}",
            v2_value=f"min={lk.v2.min_occurs},max={_fmt_max(lk.v2.max_occurs)}",
            detail="Occurrence mismatch (V1 parent root vs V2 node)",
            flags={"array_v1": v1_max.is_array, "array_v2": lk.v2.max_occurs.is_array},
            severity=sev.occurrence_severity(arr),
            root_node=lk.v1.path[0] if lk.v1.path else None, dd_ref=lk.v1.dd_ref,
            dd_in_v2=bool(lk.v1.dd_ref and lk.v1.dd_ref in v2_dds),
        ))
    return gaps


# --- G3: data-type mismatch (per context) -------------------------------------

def run_g3(idx: LinkIndex, typemap: TypeMap | None = None) -> list[Gap]:
    if typemap is None:
        return []
    v2_dds = set(idx.v2_by_dd)
    gaps: list[Gap] = []
    for lk in idx.resolved_links():
        v1c = typemap.canon_v1(lk.v1.xsd_type)
        v2c = typemap.canon_v2(lk.v2.data_type)
        unmapped = v1c is None or v2c is None
        if not unmapped and v1c == v2c:
            continue
        mandatory = lk.v1.nullable is False
        gaps.append(Gap(
            gap_id=make_gap_id(GapType.G3_DATATYPE, lk.is_number, lk.context,
                               v2_business_key(lk.v2), "type"),
            gap_type=GapType.G3_DATATYPE, is_number=lk.is_number,
            mapping_context=lk.context, v1_path=_join_path(lk.v1.path),
            v1_ref=lk.v1.source, v2_ref=lk.v2.source,
            v1_value=lk.v1.xsd_type_raw, v2_value=lk.v2.data_type_raw,
            detail=("Data type indeterminate (token not in equivalence map)"
                    if unmapped else
                    f"Data type differs: V1 {lk.v1.xsd_type_raw} vs V2 {lk.v2.data_type_raw}"),
            flags={"v1_canon": v1c, "v2_canon": v2c, "unmapped": unmapped},
            severity=sev.datatype_severity(mandatory),
            root_node=lk.v1.path[0] if lk.v1.path else None, dd_ref=lk.v1.dd_ref,
            dd_in_v2=bool(lk.v1.dd_ref and lk.v1.dd_ref in v2_dds),
        ))
    return gaps


# --- G4: mandatory/optional mismatch (per context) ----------------------------

def run_g4(idx: LinkIndex, _typemap: TypeMap | None = None) -> list[Gap]:
    v2_dds = set(idx.v2_by_dd)
    gaps: list[Gap] = []
    for lk in idx.resolved_links():
        if lk.v1.nullable is None:
            continue
        v1_expected = "Mandatory" if lk.v1.nullable is False else "Optional"  # D2
        v2_val = _norm_mandatory(lk.v2.mandatory_optional)
        if not v2_val or v2_val.casefold() == v1_expected.casefold():
            continue
        gaps.append(Gap(
            gap_id=make_gap_id(GapType.G4_MANDATORY, lk.is_number, lk.context,
                               v2_business_key(lk.v2), "mand"),
            gap_type=GapType.G4_MANDATORY, is_number=lk.is_number,
            mapping_context=lk.context, v1_path=_join_path(lk.v1.path),
            v1_ref=lk.v1.source, v2_ref=lk.v2.source,
            v1_value=f"Nullable={lk.v1.nullable} => {v1_expected}",
            v2_value=lk.v2.mandatory_optional,
            detail="Mandatory/Optional disagreement",
            severity=sev.datatype_severity(lk.v1.nullable is False),
            root_node=lk.v1.path[0] if lk.v1.path else None, dd_ref=lk.v1.dd_ref,
            dd_in_v2=bool(lk.v1.dd_ref and lk.v1.dd_ref in v2_dds),
        ))
    return gaps


# --- G5: reverse-orphan mapping (optional) ------------------------------------

def run_g5(idx: LinkIndex, _typemap: TypeMap | None = None) -> list[Gap]:
    gaps: list[Gap] = []
    for lk in idx.orphan_links():
        gaps.append(Gap(
            gap_id=make_gap_id(GapType.G5_REVERSE_ORPHAN, lk.is_number, lk.context,
                               v2_business_key(lk.v2), "reverse_orphan"),
            gap_type=GapType.G5_REVERSE_ORPHAN, is_number=lk.is_number,
            mapping_context=lk.context, v2_ref=lk.v2.source,
            v1_value=None, v2_value=lk.is_number,
            detail=f"V2.1 maps to IS {lk.is_number} ({lk.context.value}) which is absent in V1",
            flags={}, severity=Severity.HIGH,
            root_node=None, dd_ref=lk.v2.dd_ref,
            dd_in_v2=bool(lk.v2.dd_ref),     # DD comes from the V2.1 row itself
        ))
    return gaps


# --- G6: DD reference mismatch (optional) -------------------------------------

def run_g6(idx: LinkIndex, _typemap: TypeMap | None = None) -> list[Gap]:
    v2_dds = set(idx.v2_by_dd)
    gaps: list[Gap] = []
    for lk in idx.resolved_links():
        if lk.v1.dd_ref and lk.v2.dd_ref and lk.v1.dd_ref != lk.v2.dd_ref:
            gaps.append(Gap(
                gap_id=make_gap_id(GapType.G6_DD_MISMATCH, lk.is_number, lk.context,
                                   v2_business_key(lk.v2), "dd"),
                gap_type=GapType.G6_DD_MISMATCH, is_number=lk.is_number,
                mapping_context=lk.context, v1_path=_join_path(lk.v1.path),
                v1_ref=lk.v1.source, v2_ref=lk.v2.source,
                v1_value=lk.v1.dd_ref, v2_value=lk.v2.dd_ref,
                detail=f"DD reference differs: V1 {lk.v1.dd_ref} vs V2 {lk.v2.dd_ref}",
                severity=Severity.LOW,
                root_node=lk.v1.path[0] if lk.v1.path else None, dd_ref=lk.v1.dd_ref,
                dd_in_v2=bool(lk.v1.dd_ref in v2_dds)))
    return gaps


# --- G7: cardinality / scalar<->array divergence (optional) -------------------

def run_g7(idx: LinkIndex, _typemap: TypeMap | None = None) -> list[Gap]:
    v2_dds = set(idx.v2_by_dd)
    gaps: list[Gap] = []
    for lk in idx.resolved_links():
        parent = resolve_parent_root(lk.v1, idx) or lk.v1
        v1_arr = parent.max_occurs.is_array
        v2_arr = lk.v2.max_occurs.is_array
        if v1_arr != v2_arr:
            gaps.append(Gap(
                gap_id=make_gap_id(GapType.G7_CARDINALITY, lk.is_number, lk.context,
                                   v2_business_key(lk.v2), "card"),
                gap_type=GapType.G7_CARDINALITY, is_number=lk.is_number,
                mapping_context=lk.context, v1_path=_join_path(lk.v1.path),
                v1_ref=parent.source, v2_ref=lk.v2.source,
                v1_value=f"{'array' if v1_arr else 'scalar'} (max={_fmt_max(parent.max_occurs)})",
                v2_value=f"{'array' if v2_arr else 'scalar'} (max={_fmt_max(lk.v2.max_occurs)})",
                detail="Cardinality divergence (scalar ↔ array)",
                flags={"array_v1": v1_arr, "array_v2": v2_arr}, severity=Severity.HIGH,
                root_node=lk.v1.path[0] if lk.v1.path else None, dd_ref=lk.v1.dd_ref,
                dd_in_v2=bool(lk.v1.dd_ref and lk.v1.dd_ref in v2_dds)))
    return gaps


# --- G8: conflicting / duplicate mapping, context-aware (optional) ------------

def run_g8(idx: LinkIndex, _typemap: TypeMap | None = None) -> list[Gap]:
    from collections import defaultdict
    v2_dds = set(idx.v2_by_dd)
    groups: dict[tuple, list] = defaultdict(list)
    for lk in idx.resolved_links():
        groups[(lk.is_number, lk.context)].append(lk)
    gaps: list[Gap] = []
    for (isn, ctx), lks in groups.items():
        if len(lks) > 1:                      # same IS+context mapped by >1 V2 row
            v1 = lks[0].v1
            gaps.append(Gap(
                gap_id=make_gap_id(GapType.G8_DUP_MAPPING, isn, ctx, "", "dup"),
                gap_type=GapType.G8_DUP_MAPPING, is_number=isn, mapping_context=ctx,
                v1_path=_join_path(v1.path) if v1 else None,
                v1_ref=v1.source if v1 else None, v2_ref=lks[0].v2.source,
                v1_value=isn,
                v2_value=f"{len(lks)} V2.1 rows map this IS in context {ctx.value}",
                detail="Multiple V2.1 rows map to the same IS in the same context",
                flags={"count": len(lks)}, severity=Severity.MEDIUM,
                root_node=v1.path[0] if (v1 and v1.path) else None,
                dd_ref=v1.dd_ref if v1 else None,
                dd_in_v2=bool(v1 and v1.dd_ref and v1.dd_ref in v2_dds)))
    return gaps


# --- G9: data-quality findings from ingestion (optional) ----------------------

_DQ_SEV = {"low": Severity.LOW, "medium": Severity.MEDIUM, "high": Severity.HIGH}


def run_g9(dq_findings) -> list[Gap]:
    gaps: list[Gap] = []
    for i, f in enumerate(dq_findings or []):
        ref = SourceRef(sheet=f.sheet, row=f.row) if f.row else None
        gaps.append(Gap(
            gap_id=make_gap_id(GapType.G9_DATA_QUALITY, f.raw or "", None,
                               f.code, f"{f.sheet}:{f.row}:{i}"),
            gap_type=GapType.G9_DATA_QUALITY,
            is_number=f.raw if f.code == "DUPLICATE_IS" else None,
            mapping_context=None, v1_ref=ref, v1_value=f.raw,
            detail=f"[{f.code}] {f.message}", flags={"code": f.code},
            severity=_DQ_SEV.get(f.severity, Severity.LOW),
            root_node=None, dd_ref=None, dd_in_v2=False))
    return gaps
