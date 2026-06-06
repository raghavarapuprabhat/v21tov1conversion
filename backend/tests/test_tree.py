"""V1 tree + parent-root resolver tests (LLD §6) against the real sample.

Sample hierarchy: Message > LegalEntity (Root, min=1/max=1) > LEDetails (Root,
no occurrence) > {LegalEntityID, SequenceNumber, LegalEntityType, existingId}.
"""
from pathlib import Path

import pytest

from app.domain.linkage import resolve_links
from app.domain.tree import build_v1_tree, find_node, resolve_parent_root
from app.ingestion.service import run_ingestion

ROOT = Path(__file__).resolve().parents[2]
V1 = ROOT / "v1.xlsx"
V2 = ROOT / "v2.1.xlsx"

pytestmark = pytest.mark.skipif(
    not (V1.exists() and V2.exists()), reason="sample workbooks not present"
)


@pytest.fixture(scope="module")
def ctx():
    v1, v2, _report = run_ingestion(V1, V2)
    return v1, resolve_links(v1, v2), build_v1_tree(v1)


def test_tree_shape_and_leaves(ctx):
    _v1, _idx, tree = ctx
    le = find_node(tree, ["Message", "LegalEntity"])
    assert le is not None
    assert le.node_kind.lower() == "root"
    assert le.min_occurs == 1
    assert le.max_occurs.value == 1

    ledetails = find_node(tree, ["Message", "LegalEntity", "LEDetails"])
    assert ledetails is not None
    attrs = {leaf.attribute for leaf in ledetails.leaves}
    assert attrs == {"LegalEntityID", "SequenceNumber", "LegalEntityType", "existingId"}
    assert {leaf.is_number for leaf in ledetails.leaves} == {"IS1", "IS2", "IS3", "IS4"}


def test_no_spurious_array_flag(ctx):
    _v1, _idx, tree = ctx
    le = find_node(tree, ["Message", "LegalEntity"])
    assert le.is_array is False        # max=1 is not an array


def test_parent_root_is_logical_outermost_root(ctx):
    v1, idx, _tree = ctx
    is1 = next(f for f in v1 if f.is_number == "IS1")
    parent = resolve_parent_root(is1, idx)
    # Decision D7: climb the contiguous Root chain (LEDetails -> LegalEntity) and
    # take the outermost logical Root, which carries Min=1.
    assert parent is not None
    assert parent.path == ["Message", "LegalEntity"]
    assert parent.min_occurs == 1
    # IS4 is nullable -> excluded from G1 step B; IS1/IS2/IS3 (Nullable=False)
    # all resolve to this Min=1 root, so G1-C = 3 on this sample.
    for isn in ("IS2", "IS3", "IS4"):
        f = next(x for x in v1 if x.is_number == isn)
        assert resolve_parent_root(f, idx).path == ["Message", "LegalEntity"]
