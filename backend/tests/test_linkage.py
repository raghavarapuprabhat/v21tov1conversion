"""Per-context linkage tests (LLD §4) against the real sample workbooks.

On the sample, the only real mapping is Entity -> IS2339, and IS2339 is NOT in
V1 — so every V1 IS is unmapped (G1 set A) and IS2339 is a reverse-orphan (G5).
"""
from pathlib import Path

import pytest

from app.domain.linkage import resolve_links
from app.ingestion.service import run_ingestion
from app.models.canonical import MappingContext

ROOT = Path(__file__).resolve().parents[2]
V1 = ROOT / "v1.xlsx"
V2 = ROOT / "v2.1.xlsx"

pytestmark = pytest.mark.skipif(
    not (V1.exists() and V2.exists()), reason="sample workbooks not present"
)


@pytest.fixture(scope="module")
def idx():
    v1, v2, _report = run_ingestion(V1, V2)
    return resolve_links(v1, v2)


def test_v1_is_set(idx):
    assert idx.v1_is_set == {"IS1", "IS2", "IS3", "IS4"}


def test_single_context_linkage(idx):
    assert len(idx.linkages) == 1
    lk = idx.linkages[0]
    assert lk.is_number == "IS2339"
    assert lk.context == MappingContext.ENTITY
    assert lk.is_orphan is True            # IS2339 absent in V1
    assert idx.v2_mapped_is == {"IS2339"}


def test_coverage_and_reverse_orphans(idx):
    # All V1 IS are unmapped -> G1 set A is the full set
    assert idx.missing_in_v2() == {"IS1", "IS2", "IS3", "IS4"}
    # IS2339 is referenced by V2 but missing from V1 -> G5
    assert idx.reverse_orphans() == {"IS2339"}
    assert [lk.is_number for lk in idx.orphan_links()] == ["IS2339"]
    assert idx.resolved_links() == []


def test_dd_indexes(idx):
    # DD1490 appears on both sides (V1 IS4 and the V2 element row)
    assert "DD1490" in idx.v1_by_dd
    assert "DD1490" in idx.v2_by_dd
    assert idx.v1_by_dd["DD1490"][0].is_number == "IS4"


def test_root_rows_by_path(idx):
    keys = set(idx.root_rows_by_path)
    assert ("Message", "LegalEntity") in keys
    assert ("Message", "LegalEntity", "LEDetails") in keys
    assert idx.root_rows_by_path[("Message", "LegalEntity")].min_occurs == 1
