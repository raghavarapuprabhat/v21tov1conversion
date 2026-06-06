"""Ingestion tests against the real sample workbooks (golden fixture, T-E14.1).

Asserts the canonical model matches the actual content of v1.xlsx / v2.1.xlsx.
Values are dummy but the structure is the contract; these assertions lock it in.
"""
from pathlib import Path

import pytest

from app.ingestion.service import run_ingestion
from app.models.canonical import MappingContext

ROOT = Path(__file__).resolve().parents[2]   # project root holding the xlsx files
V1 = ROOT / "v1.xlsx"
V2 = ROOT / "v2.1.xlsx"

pytestmark = pytest.mark.skipif(
    not (V1.exists() and V2.exists()),
    reason="sample workbooks not present",
)


@pytest.fixture(scope="module")
def ingested():
    return run_ingestion(V1, V2)


def test_v1_counts_and_is_numbers(ingested):
    v1, _v2, _report = ingested
    by_is = {f.is_number: f for f in v1 if f.is_number}
    assert set(by_is) == {"IS1", "IS2", "IS3", "IS4"}
    # two structural Root rows carry no IS
    assert sum(1 for f in v1 if (f.node_kind or "").lower() == "root") == 2


def test_v1_leaf_attributes_types_nullable(ingested):
    v1, _v2, _report = ingested
    by_is = {f.is_number: f for f in v1 if f.is_number}

    is1 = by_is["IS1"]
    assert is1.attribute == "LegalEntityID"
    assert is1.xsd_type == "xs:integer"
    assert is1.xsd_type_raw == "XS:integer"     # raw preserved
    assert is1.nullable is False
    assert is1.dd_ref == "DD1"
    assert is1.path == ["Message", "LegalEntity", "LEDetails"]

    is4 = by_is["IS4"]
    assert is4.xsd_type == "xs:string"
    assert is4.nullable is True
    assert is4.dd_ref == "DD1490"


def test_v1_root_occurrence(ingested):
    v1, _v2, _report = ingested
    roots = [f for f in v1 if (f.node_kind or "").lower() == "root"]
    # The Message/LegalEntity root carries Min=1, Max=1
    top = next(f for f in roots if f.path == ["Message", "LegalEntity"])
    assert top.min_occurs == 1
    assert top.max_occurs.value == 1


def test_v2_counts_and_mapping(ingested):
    _v1, v2, _report = ingested
    assert len(v2) == 2                          # one Node row + one Element row

    element = next(f for f in v2 if (f.node_kind or "").lower() == "element")
    # Entity context maps to IS2339 (absent in V1 -> reverse orphan in E3/G5)
    assert element.mapped_is() == {MappingContext.ENTITY: "IS2339"}
    assert element.map_rp_ind is None            # 'Not APplicable' -> sentinel
    assert element.map_rp_org is None            # 'Not Applicable' -> sentinel
    assert element.data_type == "string"
    assert element.mandatory_optional == "Optional"
    assert element.dd_ref == "DD1490"

    node = next(f for f in v2 if (f.node_kind or "").lower() == "node")
    assert node.data_type == "object"
    assert node.min_occurs == 1
    assert node.max_occurs.value == 1


def test_dq_report_flags_observed_anomalies(ingested):
    _v1, _v2, report = ingested
    assert report.v1_rows == 6                   # 2 Root + 4 Element
    assert report.v2_rows == 2
    assert report.v1_is_numbers == 4
    assert report.v2_mapping_links == 1          # only Entity->IS2339 is real
    # 'Not APplicable' odd casing + 'availabilityOfExistig D' space are flagged
    assert report.by_code.get("SENTINEL_CASING", 0) >= 1
    assert report.by_code.get("JSON_ATTR_HAS_SPACE", 0) >= 1
