import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DB_PATH, ensure_directories


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect() -> Any:
    ensure_directories()
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def init_db() -> None:
    """Create the SQLite tables used by the demo website and pipeline."""
    with connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS videos (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                source TEXT NOT NULL,
                original_path TEXT NOT NULL,
                media_file TEXT NOT NULL,
                thumbnail_file TEXT,
                status TEXT NOT NULL,
                risk_score REAL NOT NULL,
                caption TEXT NOT NULL,
                tags TEXT NOT NULL,
                reasons TEXT NOT NULL,
                metrics TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                stage TEXT NOT NULL,
                message TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )


def clear_db() -> None:
    init_db()
    with connect() as connection:
        connection.execute("DELETE FROM events")
        connection.execute("DELETE FROM videos")


def add_event(
    video_id: str | None,
    stage: str,
    message: str,
    payload: dict | None = None,
) -> None:
    init_db()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO events(video_id, stage, message, payload, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (video_id, stage, message, json.dumps(payload or {}, ensure_ascii=False), now_iso()),
        )


def upsert_video(record: dict) -> None:
    init_db()
    created_at = record.get("created_at") or now_iso()
    updated_at = now_iso()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO videos (
                id, title, source, original_path, media_file, thumbnail_file,
                status, risk_score, caption, tags, reasons, metrics, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                title=excluded.title,
                source=excluded.source,
                original_path=excluded.original_path,
                media_file=excluded.media_file,
                thumbnail_file=excluded.thumbnail_file,
                status=excluded.status,
                risk_score=excluded.risk_score,
                caption=excluded.caption,
                tags=excluded.tags,
                reasons=excluded.reasons,
                metrics=excluded.metrics,
                updated_at=excluded.updated_at
            """,
            (
                record["id"],
                record["title"],
                record["source"],
                record["original_path"],
                record["media_file"],
                record.get("thumbnail_file"),
                record["status"],
                float(record["risk_score"]),
                record["caption"],
                json.dumps(record["tags"], ensure_ascii=False),
                json.dumps(record["reasons"], ensure_ascii=False),
                json.dumps(record["metrics"], ensure_ascii=False),
                created_at,
                updated_at,
            ),
        )


def _decode_record(row: sqlite3.Row) -> dict:
    item = dict(row)
    for key in ("tags", "reasons", "metrics"):
        item[key] = json.loads(item[key])
    return item


def list_videos(status: str | None = None) -> list[dict]:
    init_db()
    with connect() as connection:
        if status:
            rows = connection.execute(
                "SELECT * FROM videos WHERE status = ? ORDER BY created_at DESC",
                (status,),
            ).fetchall()
        else:
            rows = connection.execute(
                "SELECT * FROM videos ORDER BY created_at DESC"
            ).fetchall()
    return [_decode_record(row) for row in rows]


def get_video(video_id: str) -> dict | None:
    init_db()
    with connect() as connection:
        row = connection.execute(
            "SELECT * FROM videos WHERE id = ?",
            (video_id,),
        ).fetchone()
    return _decode_record(row) if row else None


def list_events(limit: int = 80) -> list[dict]:
    init_db()
    with connect() as connection:
        rows = connection.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
    events = []
    for row in rows:
        item = dict(row)
        item["payload"] = json.loads(item["payload"])
        events.append(item)
    return events


def stats() -> dict:
    init_db()
    with connect() as connection:
        rows = connection.execute(
            "SELECT status, COUNT(*) AS count FROM videos GROUP BY status"
        ).fetchall()
        total = connection.execute("SELECT COUNT(*) AS count FROM videos").fetchone()["count"]
    by_status = {row["status"]: row["count"] for row in rows}
    return {
        "total": total,
        "published": by_status.get("published", 0),
        "review": by_status.get("review", 0),
        "rejected": by_status.get("rejected", 0),
    }


def database_path() -> Path:
    return DB_PATH


def get_setting(key: str, default: Any = None) -> Any:
    init_db()
    with connect() as connection:
        row = connection.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,),
        ).fetchone()
    if row is None:
        return default
    try:
        return json.loads(row["value"])
    except json.JSONDecodeError:
        return row["value"]


def set_setting(key: str, value: Any) -> None:
    init_db()
    with connect() as connection:
        connection.execute(
            """
            INSERT INTO settings(key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value=excluded.value,
                updated_at=excluded.updated_at
            """,
            (key, json.dumps(value, ensure_ascii=False), now_iso()),
        )
