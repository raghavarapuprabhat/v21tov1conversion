"""Repository tests (LLD §8): query/filter/sort/paginate + SQLite durability.

The headline test proves collaboration (status + history) survives a simulated
restart — a second repository instance over the same snapshot file recovers it.
"""
from pathlib import Path

import pytest

from app.gaps.typemap import TypeMap
from app.ingestion.service import run_ingestion
from app.models.collab import Comment
from app.repositories.base import GapQuery
from app.repositories.memory import InMemoryRepository
from app.services.analysis import analyze

ROOT = Path(__file__).resolve().parents[2]
BACKEND = Path(__file__).resolve().parents[1]
V1 = ROOT / "v1.xlsx"
V2 = ROOT / "v2.1.xlsx"
TYPEMAP = BACKEND / "config" / "type_equivalence.yaml"

pytestmark = pytest.mark.skipif(
    not (V1.exists() and V2.exists()), reason="sample workbooks not present"
)


def _load(repo):
    v1, v2, _report = run_ingestion(V1, V2)
    repo.load(v1, v2, analyze(v1, v2, TypeMap.load(TYPEMAP), enable_optional=True))
    return repo


@pytest.fixture
def repo(tmp_path):
    r = _load(InMemoryRepository(str(tmp_path / "snap.sqlite")))
    yield r
    r.close()


def test_query_by_type(repo):
    page = repo.query_gaps(GapQuery(gap_type="G1_COVERAGE"))
    assert page.total == 4
    assert {g.is_number for g in page.rows} == {"IS1", "IS2", "IS3", "IS4"}


def test_filter_by_severity(repo):
    page = repo.query_gaps(GapQuery(gap_type="G1_COVERAGE", severity="Critical"))
    assert page.total == 3                      # IS1/IS2/IS3


def test_sort_and_paginate(repo):
    page = repo.query_gaps(GapQuery(sort="severity", page=1, page_size=2))
    assert page.page_size == 2
    assert len(page.rows) == 2
    assert page.rows[0].severity.value == "Critical"   # most severe first


def test_search(repo):
    page = repo.query_gaps(GapQuery(search="IS2339"))
    assert page.total == 1
    assert page.rows[0].gap_type.value == "G5_REVERSE_ORPHAN"


def test_v2_by_dd(repo):
    rows = repo.v2_by_dd("DD1490")
    assert len(rows) == 1
    assert rows[0].map_entity == "IS2339"


def test_status_and_history(repo):
    gid = repo.query_gaps(GapQuery(gap_type="G1_COVERAGE")).rows[0].gap_id
    repo.set_status(gid, "Accepted", "alice", "agreed in review")
    assert repo.get_gap(gid).status.value == "Accepted"
    hist = repo.status_history(gid)
    assert len(hist) == 1
    assert hist[0].old_status.value == "Open"
    assert hist[0].new_status.value == "Accepted"
    assert hist[0].author == "alice"


def test_summary_reflects_status(repo):
    gid = repo.query_gaps(GapQuery(gap_type="G1_COVERAGE")).rows[0].gap_id
    repo.set_status(gid, "Not applicable", "bob")
    g1 = next(s for s in repo.summary() if s.gap_type == "G1_COVERAGE")
    assert g1.by_status.get("Not applicable") == 1
    assert g1.by_status.get("Open") == 3


def test_durability_across_restart(tmp_path):
    path = str(tmp_path / "snap.sqlite")
    r1 = _load(InMemoryRepository(path))
    gid = r1.query_gaps(GapQuery(gap_type="G1_COVERAGE")).rows[0].gap_id
    r1.set_status(gid, "Accepted", "alice", "ok")
    r1.add_comment(Comment(comment_id="", gap_id=gid, author="alice", body="looks fine"))
    r1.close()

    # Simulate restart: brand-new repo instance over the same snapshot file
    r2 = _load(InMemoryRepository(path))
    assert r2.get_gap(gid).status.value == "Accepted"        # status survived
    assert len(r2.status_history(gid)) == 1                   # history survived
    comments = r2.list_comments(gid)
    assert len(comments) == 1 and comments[0].body == "looks fine"
    assert comments[0].is_anchor == r2.get_gap(gid).is_number  # IS anchor defaulted
    r2.close()
