"""File-upload re-ingestion — POST /api/ingest/upload.

Paths are pinned to *temp copies* so the golden fixtures are never overwritten.
"""
import shutil
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
    # Pin configured paths to disposable copies — the upload commits onto these.
    v1 = tmp_path / "v1.xlsx"
    v2 = tmp_path / "v2.1.xlsx"
    shutil.copy(ROOT / "v1.xlsx", v1)
    shutil.copy(ROOT / "v2.1.xlsx", v2)
    monkeypatch.setattr(settings, "V1_PATH", str(v1))
    monkeypatch.setattr(settings, "V2_PATH", str(v2))
    monkeypatch.setattr(settings, "SNAPSHOT_PATH", str(tmp_path / "s.sqlite"))
    monkeypatch.setattr(settings, "ENABLE_OPTIONAL_GAPS", True)
    get_repo.cache_clear()
    with TestClient(app) as c:
        yield c
    get_repo.cache_clear()


def test_upload_v2_reingests_and_persists(client):
    target = Path(settings.V2_PATH)
    target.write_bytes(b"")  # clobber so we can prove the upload restored it
    with open(ROOT / "v2.1.xlsx", "rb") as fh:
        r = client.post("/api/ingest/upload", files={"v2": ("v2.1.xlsx", fh, "application/octet-stream")})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["v2_rows"] > 0
    assert target.stat().st_size > 0          # committed to the configured path
    # the sheet tab now serves the uploaded file
    assert client.get("/api/sheets/v2").json()["rows"]


def test_upload_both(client):
    with open(ROOT / "v1.xlsx", "rb") as f1, open(ROOT / "v2.1.xlsx", "rb") as f2:
        r = client.post(
            "/api/ingest/upload",
            files={
                "v1": ("v1.xlsx", f1, "application/octet-stream"),
                "v2": ("v2.1.xlsx", f2, "application/octet-stream"),
            },
        )
    assert r.status_code == 200, r.text
    assert r.json()["v1_rows"] > 0 and r.json()["v2_rows"] > 0


def test_upload_nothing_is_400(client):
    assert client.post("/api/ingest/upload").status_code == 400


def test_upload_wrong_type_is_415(client):
    r = client.post("/api/ingest/upload", files={"v2": ("notes.txt", b"hello", "text/plain")})
    assert r.status_code == 415


def test_bad_workbook_does_not_clobber_configured(client):
    """A garbage .xlsx fails validation and the existing file is left intact."""
    before = Path(settings.V2_PATH).read_bytes()
    r = client.post("/api/ingest/upload", files={"v2": ("bad.xlsx", b"not a zip", "application/octet-stream")})
    assert r.status_code == 422
    assert Path(settings.V2_PATH).read_bytes() == before
