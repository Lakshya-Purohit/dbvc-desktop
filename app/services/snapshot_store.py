"""
Local SQLite store for connection profiles, schema snapshots, and apply history.
"""

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Optional

from app.config import DB_PATH
from app.logger import get_logger

log = get_logger("snapshot_store")

# ── Schema ───────────────────────────────────────────────────────────────
_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS connections (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    db_type TEXT NOT NULL,
    host TEXT NOT NULL,
    port TEXT,
    database_name TEXT NOT NULL,
    username TEXT NOT NULL,
    password_encrypted TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS snapshots (
    id TEXT PRIMARY KEY,
    connection_id TEXT NOT NULL REFERENCES connections(id),
    label TEXT,
    message TEXT,
    schema_data TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS apply_history (
    id TEXT PRIMARY KEY,
    snapshot_id TEXT,
    target_connection_id TEXT,
    sql_executed TEXT,
    obj_type TEXT,
    obj_name TEXT,
    status TEXT,
    error_message TEXT,
    applied_at TEXT DEFAULT (datetime('now'))
);
"""


class SnapshotStore:
    """Manages the local SQLite database for DBVC."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    def _init_db(self):
        log.info("Initializing local database at: %s", self.db_path)
        with self._get_conn() as conn:
            conn.executescript(_SCHEMA_SQL)
        log.info("Local database ready ✓")

    # ── Connections ──────────────────────────────────────────────────────

    def save_connection(
        self,
        name: str,
        db_type: str,
        host: str,
        port: str,
        database_name: str,
        username: str,
        password_encrypted: str = "",
        conn_id: Optional[str] = None,
    ) -> str:
        """Insert or update a connection profile. Returns the connection ID."""
        cid = conn_id or str(uuid.uuid4())
        now = datetime.now().isoformat()

        with self._get_conn() as conn:
            if conn_id:
                conn.execute(
                    """UPDATE connections
                       SET name=?, db_type=?, host=?, port=?, database_name=?,
                           username=?, password_encrypted=?, updated_at=?
                       WHERE id=?""",
                    (name, db_type, host, port, database_name, username, password_encrypted, now, cid),
                )
                log.info("Updated connection profile: %s (%s)", name, cid)
            else:
                conn.execute(
                    """INSERT INTO connections
                       (id, name, db_type, host, port, database_name, username, password_encrypted, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (cid, name, db_type, host, port, database_name, username, password_encrypted, now, now),
                )
                log.info("Saved new connection profile: %s (%s)", name, cid)

        return cid

    def get_connections(self) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute("SELECT * FROM connections ORDER BY name").fetchall()
        result = [dict(r) for r in rows]
        log.debug("Loaded %d connection profiles", len(result))
        return result

    def get_connection(self, conn_id: str) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM connections WHERE id=?", (conn_id,)).fetchone()
        return dict(row) if row else None

    def delete_connection(self, conn_id: str):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM snapshots WHERE connection_id=?", (conn_id,))
            conn.execute("DELETE FROM connections WHERE id=?", (conn_id,))
        log.info("Deleted connection profile: %s", conn_id)

    # ── Snapshots ────────────────────────────────────────────────────────

    def save_snapshot(
        self,
        connection_id: str,
        schema_data: dict,
        label: str = "",
        message: str = "",
    ) -> str:
        """Save a schema snapshot. Returns snapshot ID."""
        sid = str(uuid.uuid4())
        data_json = json.dumps(schema_data, indent=2, default=str)

        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO snapshots (id, connection_id, label, message, schema_data, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (sid, connection_id, label, message, data_json, datetime.now().isoformat()),
            )

        log.info("Snapshot saved: %s (label=%s, connection=%s)", sid[:8], label, connection_id[:8])
        return sid

    def get_snapshots(self, connection_id: Optional[str] = None) -> list[dict]:
        with self._get_conn() as conn:
            if connection_id:
                rows = conn.execute(
                    """SELECT s.*, c.name as connection_name
                       FROM snapshots s
                       JOIN connections c ON s.connection_id = c.id
                       WHERE s.connection_id=?
                       ORDER BY s.created_at DESC""",
                    (connection_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT s.*, c.name as connection_name
                       FROM snapshots s
                       JOIN connections c ON s.connection_id = c.id
                       ORDER BY s.created_at DESC"""
                ).fetchall()

        result = [dict(r) for r in rows]
        log.debug("Loaded %d snapshots", len(result))
        return result

    def get_snapshot(self, snap_id: str) -> Optional[dict]:
        with self._get_conn() as conn:
            row = conn.execute(
                """SELECT s.*, c.name as connection_name
                   FROM snapshots s
                   JOIN connections c ON s.connection_id = c.id
                   WHERE s.id=?""",
                (snap_id,),
            ).fetchone()
        if row:
            d = dict(row)
            d["schema_data"] = json.loads(d["schema_data"])
            return d
        return None

    def delete_snapshot(self, snap_id: str):
        with self._get_conn() as conn:
            conn.execute("DELETE FROM snapshots WHERE id=?", (snap_id,))
        log.info("Deleted snapshot: %s", snap_id)

    # ── Apply History ────────────────────────────────────────────────────

    def save_apply_record(
        self,
        target_connection_id: str,
        sql_executed: str,
        obj_type: str,
        obj_name: str,
        status: str,
        error_message: str = "",
        snapshot_id: str = "",
    ) -> str:
        rid = str(uuid.uuid4())
        with self._get_conn() as conn:
            conn.execute(
                """INSERT INTO apply_history
                   (id, snapshot_id, target_connection_id, sql_executed, obj_type, obj_name, status, error_message, applied_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (rid, snapshot_id, target_connection_id, sql_executed, obj_type, obj_name, status, error_message, datetime.now().isoformat()),
            )
        log.info("Apply record saved: %s %s → %s", obj_type, obj_name, status)
        return rid

    def get_apply_history(self, limit: int = 100) -> list[dict]:
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM apply_history ORDER BY applied_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]
