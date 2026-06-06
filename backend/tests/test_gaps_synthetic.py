"""Synthetic gap tests — a *resolved* per-context linkage with real mismatches,
proving G2/G3/G4 fire (the sample workbook only has an orphan linkage).

V1 element IS100: xs:integer, Nullable=False, parent root Min=1/Max=1.
V2 maps Entity->IS100 with data_type=string, Min=0/Max=unbounded, Optional.
=> expect one G2 (occurrence, array), one G3 (type), one G4 (mandatory).
"""
from pathlib import Path

import pytest

from app.gaps.typemap import TypeMap
from app.models.canonical import Occurs, SourceRef, V1Field, V2Field
from app.models.gap import GapType, Severity
from app.services.analysis import analyze

BACKEND = Path(__file__).resolve().parents[1]
TYPEMAP = BACKEND / "config" / "type_equivalence.yaml"


@pytest.fixture(scope="module")
def result():
    v1 = [
        V1Field(node_kind="Root", path=["Root1"], min_occurs=1,
                max_occurs=Occurs(raw="1", value=1), source=SourceRef(sheet="t", row=1)),
        V1Field(is_number="IS100", is_number_raw="IS100", node_kind="Element",
                path=["Root1"], attribute="Foo",
                xsd_type="xs:integer", xsd_type_raw="XS:integer",
                nullable=False, source=SourceRef(sheet="t", row=2)),
    ]
    v2 = [
        V2Field(map_entity="IS100", map_entity_raw="IS100", node_kind="Element",
                data_type="string", data_type_raw="String",
                min_occurs=0, max_occurs=Occurs(raw="unbounded", unbounded=True),
                mandatory_optional="Optional", full_path="[X].foo", dd_ref="DD9",
                source=SourceRef(sheet="t", row=2)),
    ]
    return analyze(v1, v2, TypeMap.load(TYPEMAP), enable_optional=True)


def _one(gaps, t):
    found = [g for g in gaps if g.gap_type == t]
    assert len(found) == 1, f"expected exactly one {t}, got {len(found)}"
    return found[0]


def test_no_coverage_gap_when_mapped(result):
    assert [g for g in result.gaps if g.gap_type == GapType.G1_COVERAGE] == []
    assert [g for g in result.gaps if g.gap_type == GapType.G5_REVERSE_ORPHAN] == []


def test_g2_occurrence_array(result):
    g = _one(result.gaps, GapType.G2_OCCURRENCE)
    assert g.is_number == "IS100"
    assert g.mapping_context.value == "Entity"
    assert g.flags["array_v2"] is True
    assert g.severity == Severity.HIGH          # crosses scalar->array
    assert "min=1,max=1" in g.v1_value
    assert "unbounded" in g.v2_value


def test_g3_type_mismatch(result):
    g = _one(result.gaps, GapType.G3_DATATYPE)
    assert g.v1_value == "XS:integer" and g.v2_value == "String"
    assert g.flags["v1_canon"] == "INTEGER" and g.flags["v2_canon"] == "STRING"
    assert g.flags["unmapped"] is False
    assert g.severity == Severity.HIGH          # mandatory field


def test_g4_mandatory_mismatch(result):
    g = _one(result.gaps, GapType.G4_MANDATORY)
    assert "Mandatory" in g.v1_value            # Nullable=False => Mandatory
    assert g.v2_value == "Optional"
    assert g.mapping_context.value == "Entity"
