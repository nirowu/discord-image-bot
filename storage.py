# storage.py
import sqlite3
from typing import Optional, Iterable, Dict, Any


SCHEMA = """
CREATE TABLE IF NOT EXISTS images (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    uploader_id       TEXT NOT NULL,
    channel_id        TEXT NOT NULL,
    message_id        TEXT NOT NULL,
    file_path         TEXT NOT NULL,
    user_text         TEXT,
    ocr_text          TEXT,
    index_text        TEXT NOT NULL,
    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.execute(SCHEMA)
    conn.commit()


def save_image_record(
    conn: sqlite3.Connection,
    uploader_id: str,
    channel_id: str,
    message_id: str,
    file_path: str,
    user_text: Optional[str],
    ocr_text: Optional[str],
) -> int:
    """Insert one image row and return its new id."""
    index_text_parts = [t for t in (user_text, ocr_text) if t]
    index_text = " ".join(index_text_parts) if index_text_parts else ""

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO images (
            uploader_id, channel_id, message_id,
            file_path, user_text, ocr_text, index_text
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            uploader_id,
            channel_id,
            message_id,
            file_path,
            user_text,
            ocr_text,
            index_text,
        ),
    )
    conn.commit()
    return cur.lastrowid


def get_image_by_id(conn: sqlite3.Connection, img_id: int) -> Optional[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM images WHERE id = ?", (img_id,))
    row = cur.fetchone()
    if row is None:
        return None
    return _row_to_dict(cur, row)


def insert_image_for_test(
    conn: sqlite3.Connection,
    uploader_id: str,
    channel_id: str,
    message_id: str,
    file_path: str,
    index_text: str,
) -> int:
    """
    Convenience helper for tests: directly insert an image with given index_text.
    """
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO images (
            uploader_id, channel_id, message_id,
            file_path, user_text, ocr_text, index_text
        )
        VALUES (?, ?, ?, ?, NULL, NULL, ?)
        """,
        (uploader_id, channel_id, message_id, file_path, index_text),
    )
    conn.commit()
    return cur.lastrowid


def fetch_all_images(conn: sqlite3.Connection) -> Iterable[Dict[str, Any]]:
    cur = conn.cursor()
    cur.execute("SELECT * FROM images")
    rows = cur.fetchall()
    return [_row_to_dict(cur, row) for row in rows]


def _row_to_dict(cur: sqlite3.Cursor, row: sqlite3.Row) -> Dict[str, Any]:
    col_names = [desc[0] for desc in cur.description]
    return {col: row[idx] for idx, col in enumerate(col_names)}

