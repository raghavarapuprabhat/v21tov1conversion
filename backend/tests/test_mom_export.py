"""MoM (Minutes of Meeting) export — date-ranged decisions + comments."""
import datetime
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
TODAY = datetime.date.today().isoformat()


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "V1_PATH", str(ROOT / "v1.xlsx"))
    monkeypatch.setattr(settings, "V2_PATH", str(ROOT / "v2.1.xlsx"))
    monkeypatch.setattr(settings, "SNAPSHOT_PATH", str(tmp_path / "s.sqlite"))
    monkeypatch.setattr(settings, "ENABLE_OPTIONAL_GAPS", True)
    get_repo.cache_clear()
    with TestClient(app) as c:
        yield c
    get_repo.cache_clear()


def _seed(client):
    gid = client.get("/api/gaps", params={"type": "G1_COVERAGE"}).json()["rows"][0]["gap_id"]
    client.post(f"/api/gaps/{gid}/comments", json={"author": "Alice", "body": "Keep mandatory"})
    client.patch(f"/api/gaps/{gid}/status", json={"status": "Accepted", "author": "Bob", "note": "Agreed"})
    return gid


def test_mom_preview_counts(client):
    _seed(client)
    r = client.get("/api/export/mom.json", params={"from": TODAY, "to": TODAY}).json()
    assert r["totals"] == {"decisions": 1, "comments": 1, "attributes": 1, "participants": 2}
    assert r["participants"] == ["Alice", "Bob"]
    assert r["attributes"][0]["is_number"] == "IS1"


def test_mom_html_download(client):
    _seed(client)
    r = client.get("/api/export/mom", params={"from": TODAY, "to": TODAY, "format": "html"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/html")
    assert f"MoM_{TODAY}_to_{TODAY}.html" in r.headers["content-disposition"]
    assert "Minutes of Meeting" in r.text and "Accepted" in r.text and "Keep mandatory" in r.text


def test_mom_csv_and_md(client):
    _seed(client)
    csv_r = client.get("/api/export/mom", params={"from": TODAY, "to": TODAY, "format": "csv"})
    assert "comment_or_note" in csv_r.text and "Keep mandatory" in csv_r.text
    md_r = client.get("/api/export/mom", params={"from": TODAY, "to": TODAY, "format": "md"})
    assert md_r.text.startswith("# Minutes of Meeting") and "| IS1 |" in md_r.text


def test_mom_empty_range(client):
    _seed(client)
    r = client.get("/api/export/mom.json", params={"from": "2000-01-01", "to": "2000-01-02"}).json()
    assert r["totals"]["decisions"] == 0 and r["events"] == []


def test_mom_bad_range_400(client):
    assert client.get("/api/export/mom", params={"from": TODAY, "to": "2000-01-01"}).status_code == 400


def test_mom_invalid_format_422(client):
    assert client.get("/api/export/mom", params={"from": TODAY, "to": TODAY, "format": "pdf"}).status_code == 422
