"""SQLite snapshot store (LLD v1.2 §8.2/§8.3, Plan T-E5.2).

Persists the *collaboration* layer (statuses, status history, comments, saved
views) to a local SQLite file so it survives restarts. Gaps/fields/tree are
recomputed from Excel each start and re-joined to this by deterministic gap_id.
Uses the stdlib `sqlite3` — no external service. (PostgreSQL is the Phase-1.5
alternative implementation.)
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

_DDL = """
CREATE TABLE IF NOT EXISTS gap_status (
    gap_id     TEXT PRIMARY KEY,
    status     TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS status_history (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    gap_id     TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT NOT NULL,
    author     TEXT NOT NULL,
    note       TEXT,
    changed_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS comment (
    comment_id        TEXT PRIMARY KEY,
    gap_id            TEXT,
    is_anchor         TEXT,
    mapping_context   TEXT,
    parent_comment_id TEXT,
    author            TEXT NOT NULL,
    body              TEXT NOT NULL,
    created_at        TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS saved_view (
    view_id TEXT PRIMARY KEY,
    name    TEXT NOT NULL,
    owner   TEXT,
    spec    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_comment_gap ON comment(gap_id);
CREATE INDEX IF NOT EXISTS idx_comment_anchor ON comment(is_anchor);
CREATE INDEX IF NOT EXISTS idx_hist_gap ON status_history(gap_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SnapshotStore:
    def __init__(self, path: str | Path):
        self.path = str(path)
        # allow use across FastAPI threads; we commit on every write
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(_DDL)
        self._conn.commit()

    # --- statuses -------------------------------------------------------------
    def set_status(self, gap_id: str, status: str) -> None:
        self._conn.execute(
            "INSERT INTO gap_status(gap_id, status, updated_at) VALUES(?,?,?) "
            "ON CONFLICT(gap_id) DO UPDATE SET status=excluded.status, updated_at=excluded.updated_at",
            (gap_id, status, _now()),
        )
        self._conn.commit()

    def all_statuses(self) -> dict[str, str]:
        cur = self._conn.execute("SELECT gap_id, status FROM gap_status")
        return {r["gap_id"]: r["status"] for r in cur.fetchall()}

    # --- status history -------------------------------------------------------
    def add_history(self, gap_id: str, old: Optional[str], new: str,
                    author: str, note: Optional[str]) -> None:
        self._conn.execute(
            "INSERT INTO status_history(gap_id, old_status, new_status, author, note, changed_at) "
            "VALUES(?,?,?,?,?,?)",
            (gap_id, old, new, author, note, _now()),
        )
        self._conn.commit()

    def history(self, gap_id: str) -> list[dict]:
        cur = self._conn.execute(
            "SELECT gap_id, old_status, new_status, author, note, changed_at "
            "FROM status_history WHERE gap_id=? ORDER BY id", (gap_id,),
        )
        return [dict(r) for r in cur.fetchall()]

    # --- comments -------------------------------------------------------------
    def add_comment(self, c: dict) -> None:
        self._conn.execute(
            "INSERT INTO comment(comment_id, gap_id, is_anchor, mapping_context, "
            "parent_comment_id, author, body, created_at) VALUES(?,?,?,?,?,?,?,?)",
            (c["comment_id"], c.get("gap_id"), c.get("is_anchor"),
             c.get("mapping_context"), c.get("parent_comment_id"),
             c["author"], c["body"], c["created_at"]),
        )
        self._conn.commit()

    def comments_for_gap(self, gap_id: str) -> list[dict]:
        cur = self._conn.execute(
            "SELECT * FROM comment WHERE gap_id=? ORDER BY created_at", (gap_id,))
        return [dict(r) for r in cur.fetchall()]

    def comments_for_anchor(self, is_anchor: str) -> list[dict]:
        cur = self._conn.execute(
            "SELECT * FROM comment WHERE is_anchor=? ORDER BY created_at", (is_anchor,))
        return [dict(r) for r in cur.fetchall()]

    def detach_gap(self, gap_id: str) -> None:
        """Used by F13 (E6): keep the thread but clear its (now absent) gap link."""
        self._conn.execute("UPDATE comment SET gap_id=NULL WHERE gap_id=?", (gap_id,))
        self._conn.commit()

    def count_comments(self) -> int:
        return self._conn.execute("SELECT COUNT(*) FROM comment").fetchone()[0]

    # --- saved views ----------------------------------------------------------
    def save_view(self, view_id: str, name: str, owner: Optional[str], spec: dict) -> None:
        self._conn.execute(
            "INSERT INTO saved_view(view_id, name, owner, spec) VALUES(?,?,?,?) "
            "ON CONFLICT(view_id) DO UPDATE SET name=excluded.name, owner=excluded.owner, spec=excluded.spec",
            (view_id, name, owner, json.dumps(spec)),
        )
        self._conn.commit()

    def list_views(self) -> list[dict]:
        cur = self._conn.execute("SELECT view_id, name, owner, spec FROM saved_view ORDER BY name")
        return [{**dict(r), "spec": json.loads(r["spec"])} for r in cur.fetchall()]

    def close(self) -> None:
        self._conn.close()
