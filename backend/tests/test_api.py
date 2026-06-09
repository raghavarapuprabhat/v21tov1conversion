"""API integration tests (LLD §7) — full stack over HTTP against the sample.

Uses a temp snapshot and enables optional gaps so G5 appears. The TestClient
context manager triggers startup ingestion into a fresh repo.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.deps import get_repo
from app.main import app

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(
    not ((ROOT / "v1.xlsx").exists() and (ROOT / "v2.1.xlsx").exists()),
    reason="sample workbooks not present",
)


@pytest.fixture
def client(tmp_path, monkeypatch):
    # Pin the sample workbooks so a local backend/.env (e.g. pointing at mockdata)
    # never leaks into the tests.
    monkeypatch.setattr(settings, "V1_PATH", str(ROOT / "v1.xlsx"))
    monkeypatch.setattr(settings, "V2_PATH", str(ROOT / "v2.1.xlsx"))
    monkeypatch.setattr(settings, "SNAPSHOT_PATH", str(tmp_path / "s.sqlite"))
    monkeypatch.setattr(settings, "ENABLE_OPTIONAL_GAPS", True)
    get_repo.cache_clear()
    with TestClient(app) as c:
        yield c
    get_repo.cache_clear()


def _first_g1_id(client) -> str:
    r = client.get("/api/gaps", params={"type": "G1_COVERAGE"})
    return r.json()["rows"][0]["gap_id"]


def test_summary(client):
    data = client.get("/api/summary").json()
    by_type = {s["gap_type"]: s for s in data}
    assert by_type["G1_COVERAGE"]["total"] == 4
    assert by_type["G1_COVERAGE"]["metrics"] == {
        "total_missing": 4, "nullable_false": 3, "parent_min1": 3}
    assert by_type["G5_REVERSE_ORPHAN"]["total"] == 1


def test_list_and_filter_gaps(client):
    assert client.get("/api/gaps", params={"type": "G1_COVERAGE"}).json()["total"] == 4
    crit = client.get("/api/gaps", params={"type": "G1_COVERAGE", "severity": "Critical"})
    assert crit.json()["total"] == 3
    search = client.get("/api/gaps", params={"search": "IS2339"}).json()
    assert search["total"] == 1 and search["rows"][0]["gap_type"] == "G5_REVERSE_ORPHAN"


def test_column_filters(client):
    # contains filter on IS
    r = client.get("/api/gaps", params={"is": "IS2"})
    isns = {row["is_number"] for row in r.json()["rows"]}
    assert isns and all("IS2" in (i or "") for i in isns)
    # contains filter on V1 value (attribute) — only IS4 is 'existingId'
    r2 = client.get("/api/gaps", params={"type": "G1_COVERAGE", "v1": "existing"})
    assert r2.json()["total"] == 1
    assert r2.json()["rows"][0]["is_number"] == "IS4"
    # exact severity column filter
    r3 = client.get("/api/gaps", params={"type": "G1_COVERAGE", "severity": "Medium"})
    assert r3.json()["total"] == 1


def test_g1_nullable_field_and_filter(client):
    rows = client.get("/api/gaps", params={"type": "G1_COVERAGE"}).json()["rows"]
    # every G1 coverage gap carries the V1 Nullable value
    assert all("nullable" in r for r in rows)
    # 3 of 4 are Nullable=False (matches the funnel's nullable_false metric)
    not_null = client.get("/api/gaps", params={"type": "G1_COVERAGE", "nullable": "false"})
    assert not_null.json()["total"] == 3
    assert all(r["nullable"] is False for r in not_null.json()["rows"])
    nullable = client.get("/api/gaps", params={"type": "G1_COVERAGE", "nullable": "true"})
    assert nullable.json()["total"] == 1
    assert nullable.json()["rows"][0]["is_number"] == "IS4"


def test_g2_disabled_card_present_but_empty(client):
    by_type = {s["gap_type"]: s for s in client.get("/api/summary").json()}
    # the G2 card is still listed, flagged disabled, with no gaps
    assert "G2_OCCURRENCE" in by_type
    assert by_type["G2_OCCURRENCE"]["disabled"] is True
    assert by_type["G2_OCCURRENCE"]["total"] == 0
    # and the engine produced nothing
    assert client.get("/api/gaps", params={"type": "G2_OCCURRENCE"}).json()["total"] == 0
    # other cards are not disabled
    assert by_type["G1_COVERAGE"]["disabled"] is False


def test_facets(client):
    f = client.get("/api/facets", params={"type": "G1_COVERAGE"}).json()
    assert set(f["is_numbers"]) == {"IS1", "IS2", "IS3", "IS4"}
    # all four elements share the same V1 path on the sample
    assert f["paths"] == ["Message > LegalEntity > LEDetails"]


def test_multiselect_is_in(client):
    r = client.get("/api/gaps", params=[("type", "G1_COVERAGE"), ("is_in", "IS1"), ("is_in", "IS3")])
    isns = {row["is_number"] for row in r.json()["rows"]}
    assert isns == {"IS1", "IS3"}


def test_multiselect_is_not_in(client):
    # "Select All" minus IS2/IS4 -> exclusion list keeps IS1/IS3
    r = client.get("/api/gaps", params=[("type", "G1_COVERAGE"), ("is_not_in", "IS2"), ("is_not_in", "IS4")])
    isns = {row["is_number"] for row in r.json()["rows"]}
    assert isns == {"IS1", "IS3"}


def test_multiselect_path_in(client):
    p = "Message > LegalEntity > LEDetails"
    r = client.get("/api/gaps", params=[("type", "G1_COVERAGE"), ("path_in", p)])
    assert r.json()["total"] == 4
    assert all(row["v1_path"] == p for row in r.json()["rows"])


def test_dd_in_v2_flag_and_filter(client):
    # On the sample, V1's DD1490 (IS4) also appears in V2.1 -> flag True for that gap;
    # DD1/DD2/DD3 are V1-only -> flag False.
    rows = client.get("/api/gaps", params={"type": "G1_COVERAGE"}).json()["rows"]
    by_is = {r["is_number"]: r for r in rows}
    assert by_is["IS4"]["dd_in_v2"] is True
    assert by_is["IS1"]["dd_in_v2"] is False
    # filter: only DD-in-V2 coverage gaps
    only = client.get("/api/gaps", params={"type": "G1_COVERAGE", "dd_in_v2": "true"}).json()
    assert {r["is_number"] for r in only["rows"]} == {"IS4"}
    none = client.get("/api/gaps", params={"type": "G1_COVERAGE", "dd_in_v2": "false"}).json()
    assert none["total"] == 3


def test_get_gap_404(client):
    assert client.get("/api/gaps/does-not-exist").status_code == 404


def test_status_and_history_flow(client):
    gid = _first_g1_id(client)
    r = client.patch(f"/api/gaps/{gid}/status",
                     json={"status": "Accepted", "author": "alice", "note": "ok"})
    assert r.status_code == 200 and r.json()["status"] == "Accepted"
    hist = client.get(f"/api/gaps/{gid}/history").json()
    assert len(hist) == 1 and hist[0]["new_status"] == "Accepted"


def test_bulk_status(client):
    ids = [g["gap_id"] for g in client.get(
        "/api/gaps", params={"type": "G1_COVERAGE"}).json()["rows"][:2]]
    r = client.patch("/api/gaps/bulk-status",
                     json={"gap_ids": ids, "status": "Not applicable", "author": "bob"})
    assert r.json() == {"updated": 2}


def test_comment_thread_flow(client):
    gid = _first_g1_id(client)
    c1 = client.post(f"/api/gaps/{gid}/comments",
                     json={"author": "alice", "body": "root"}).json()
    client.post(f"/api/gaps/{gid}/comments",
                json={"author": "bob", "body": "reply", "parent_comment_id": c1["comment_id"]})
    conv = client.get(f"/api/gaps/{gid}/comments").json()
    assert len(conv["thread"]) == 1
    assert conv["thread"][0]["body"] == "root"
    assert conv["thread"][0]["replies"][0]["body"] == "reply"


def test_tree(client):
    tree = client.get("/api/tree").json()
    assert any(c["name"] == "Message" for c in tree["children"])


def test_v2_by_dd(client):
    rows = client.get("/api/v2/by-dd/DD1490").json()
    assert len(rows) == 1 and rows[0]["map_entity"] == "IS2339"


def test_export_csv(client):
    r = client.get("/api/export", params={"type": "G1_COVERAGE"})
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "IS1" in r.text and "gap_id" in r.text


def test_saved_views(client):
    created = client.post("/api/views",
                          json={"name": "Critical only", "spec": {"severity": "Critical"}}).json()
    assert created["view_id"]
    views = client.get("/api/views").json()
    assert any(v["name"] == "Critical only" for v in views)
