"""Gap engine tests (LLD §5) against the real sample, with the D7 parent-root rule.

Expected on the sample:
  G1: A=4 (IS1..IS4 all unmapped), B=3 (Nullable=False), C=3 (parent root Min=1)
      severities: IS1/IS2/IS3 Critical, IS4 Medium
  G2/G3/G4: 0 (the only linkage IS2339 is an orphan with no V1 side)
  G5: 1 (IS2339 reverse-orphan, Entity context, High)
"""
from pathlib import Path

import pytest

from app.gaps.gap_id import make_gap_id
from app.gaps.typemap import TypeMap
from app.ingestion.service import run_ingestion
from app.models.gap import GapType, Severity
from app.services.analysis import analyze

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
V1 = ROOT / "v1.xlsx"
V2 = ROOT / "v2.1.xlsx"
TYPEMAP = BACKEND / "config" / "type_equivalence.yaml"

pytestmark = pytest.mark.skipif(
    not (V1.exists() and V2.exists()), reason="sample workbooks not present"
)


@pytest.fixture(scope="module")
def result():
    v1, v2, _report = run_ingestion(V1, V2)
    return analyze(v1, v2, TypeMap.load(TYPEMAP), enable_optional=True)


def _by_type(gaps, t):
    return [g for g in gaps if g.gap_type == t]


def test_g1_funnel_counts(result):
    g1 = _by_type(result.gaps, GapType.G1_COVERAGE)
    assert {g.is_number for g in g1} == {"IS1", "IS2", "IS3", "IS4"}
    assert sum(g.flags["nullable_false"] for g in g1) == 3
    assert sum(g.flags["parent_root_min_occurs_1"] for g in g1) == 3


def test_g1_severities(result):
    g1 = {g.is_number: g for g in _by_type(result.gaps, GapType.G1_COVERAGE)}
    assert g1["IS1"].severity == Severity.CRITICAL
    assert g1["IS2"].severity == Severity.CRITICAL
    assert g1["IS3"].severity == Severity.CRITICAL
    assert g1["IS4"].severity == Severity.MEDIUM     # IS4 is nullable -> not B/C


def test_no_comparison_gaps_on_orphan_only_sample(result):
    assert _by_type(result.gaps, GapType.G2_OCCURRENCE) == []
    assert _by_type(result.gaps, GapType.G3_DATATYPE) == []
    assert _by_type(result.gaps, GapType.G4_MANDATORY) == []


def test_g5_reverse_orphan(result):
    g5 = _by_type(result.gaps, GapType.G5_REVERSE_ORPHAN)
    assert len(g5) == 1
    assert g5[0].is_number == "IS2339"
    assert g5[0].mapping_context.value == "Entity"
    assert g5[0].severity == Severity.HIGH


def test_summary_has_g1_metrics(result):
    by_type = {s.gap_type: s for s in result.summary}
    g1 = by_type["G1_COVERAGE"]
    assert g1.total == 4
    assert g1.metrics == {"total_missing": 4, "nullable_false": 3, "parent_min1": 3}
    assert by_type["G5_REVERSE_ORPHAN"].total == 1


def test_tree_gap_rollup(result):
    # G1 gaps carry root_node 'Message'; rollup bumps the Message node.
    msg = next(c for c in result.tree.children if c.name == "Message")
    assert msg.gap_count >= 4


def test_gap_ids_deterministic_and_position_independent(result):
    # Re-running analysis yields identical ids (no source-position in the key).
    v1, v2, _r = run_ingestion(V1, V2)
    again = analyze(v1, v2, TypeMap.load(TYPEMAP), enable_optional=True)
    assert {g.gap_id for g in result.gaps} == {g.gap_id for g in again.gaps}
    # G1 id depends only on type+IS+dimension
    expected = make_gap_id(GapType.G1_COVERAGE, "IS1", None, "", "coverage")
    assert any(g.gap_id == expected for g in result.gaps)
