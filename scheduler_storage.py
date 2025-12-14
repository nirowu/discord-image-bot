import sqlite3
from typing import Any, Dict, Iterable, List, Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS scheduled_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id  TEXT NOT NULL,
    kind        TEXT NOT NULL DEFAULT 'text', -- text | image_search
    content     TEXT NOT NULL,
    run_at      INTEGER NOT NULL, -- unix epoch seconds
    repeat_interval TEXT, -- NULL | minute | hour | day
    created_by  TEXT,
    status      TEXT NOT NULL DEFAULT 'pending', -- pending | sending | sent | canceled | failed
    error       TEXT,
    created_at  INTEGER NOT NULL DEFAULT (CAST(strftime('%s','now') AS INTEGER)),
    sent_at     INTEGER
);

CREATE INDEX IF NOT EXISTS idx_scheduled_messages_status_run_at
    ON scheduled_messages(status, run_at);
"""


def init_scheduler_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)
    _ensure_column(conn, table="scheduled_messages", column="kind", ddl="TEXT NOT NULL DEFAULT 'text'")
    _ensure_column(conn, table="scheduled_messages", column="repeat_interval", ddl="TEXT")
    conn.commit()


def create_scheduled_message(
    conn: sqlite3.Connection,
    *,
    channel_id: str,
    kind: str = "text",
    content: str,
    run_at: int,
    repeat_interval: Optional[str] = None,
    created_by: Optional[str],
) -> int:
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO scheduled_messages (channel_id, kind, content, run_at, repeat_interval, created_by)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (channel_id, kind, content, run_at, repeat_interval, created_by),
    )
    conn.commit()
    return int(cur.lastrowid)


def list_scheduled_messages(
    conn: sqlite3.Connection,
    *,
    channel_id: Optional[str] = None,
    created_by: Optional[str] = None,
    include_non_pending: bool = False,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    where = []
    params: List[Any] = []

    if channel_id is not None:
        where.append("channel_id = ?")
        params.append(channel_id)
    if created_by is not None:
        where.append("created_by = ?")
        params.append(created_by)
    if not include_non_pending:
        where.append("status = 'pending'")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT id, channel_id, kind, content, run_at, repeat_interval, created_by, status, error, created_at, sent_at
        FROM scheduled_messages
        {where_sql}
        ORDER BY run_at ASC
        LIMIT ?
        """,
        (*params, limit),
    )
    rows = cur.fetchall()
    return [_row_to_dict(cur, row) for row in rows]


def cancel_scheduled_message(
    conn: sqlite3.Connection,
    *,
    schedule_id: int,
    requester_id: Optional[str] = None,
) -> bool:
    """
    Cancel a scheduled message if it's still pending.
    If requester_id is provided, only cancel if created_by matches.
    """
    cur = conn.cursor()
    if requester_id is None:
        cur.execute(
            """
            UPDATE scheduled_messages
            SET status = 'canceled'
            WHERE id = ? AND status = 'pending'
            """,
            (schedule_id,),
        )
    else:
        cur.execute(
            """
            UPDATE scheduled_messages
            SET status = 'canceled'
            WHERE id = ? AND status = 'pending' AND created_by = ?
            """,
            (schedule_id, requester_id),
        )
    conn.commit()
    return cur.rowcount > 0


def claim_due_messages(
    conn: sqlite3.Connection,
    *,
    now: int,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Atomically claim due messages by moving them from 'pending' -> 'sending'.
    Returns the claimed rows.
    """
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")
    cur.execute(
        """
        SELECT id
        FROM scheduled_messages
        WHERE status = 'pending' AND run_at <= ?
        ORDER BY run_at ASC
        LIMIT ?
        """,
        (now, limit),
    )
    ids = [int(r[0]) for r in cur.fetchall()]
    if not ids:
        conn.commit()
        return []

    placeholders = ",".join("?" for _ in ids)
    cur.execute(
        f"""
        UPDATE scheduled_messages
        SET status = 'sending'
        WHERE id IN ({placeholders}) AND status = 'pending'
        """,
        ids,
    )

    cur.execute(
        f"""
        SELECT id, channel_id, kind, content, run_at, repeat_interval, created_by, status, error, created_at, sent_at
        FROM scheduled_messages
        WHERE id IN ({placeholders})
        ORDER BY run_at ASC
        """,
        ids,
    )
    rows = cur.fetchall()
    conn.commit()
    return [_row_to_dict(cur, row) for row in rows]


def mark_sent(conn: sqlite3.Connection, schedule_id: int, *, sent_at: int) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE scheduled_messages
        SET status = 'sent', sent_at = ?
        WHERE id = ? AND status = 'sending'
        """,
        (sent_at, schedule_id),
    )
    conn.commit()


def reschedule_repeat(
    conn: sqlite3.Connection,
    schedule_id: int,
    *,
    sent_at: int,
    next_run_at: int,
) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE scheduled_messages
        SET status = 'pending', run_at = ?, sent_at = ?, error = NULL
        WHERE id = ? AND status = 'sending'
        """,
        (next_run_at, sent_at, schedule_id),
    )
    conn.commit()


def mark_failed(conn: sqlite3.Connection, schedule_id: int, *, error: str) -> None:
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE scheduled_messages
        SET status = 'failed', error = ?
        WHERE id = ? AND status = 'sending'
        """,
        (error, schedule_id),
    )
    conn.commit()


def _row_to_dict(cur: sqlite3.Cursor, row: Iterable[Any]) -> Dict[str, Any]:
    col_names = [desc[0] for desc in cur.description]
    return {col: row[idx] for idx, col in enumerate(col_names)}


def _ensure_column(conn: sqlite3.Connection, *, table: str, column: str, ddl: str) -> None:
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    existing = {r[1] for r in cur.fetchall()}
    if column in existing:
        return
    cur.execute(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")
