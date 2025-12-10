# tests/test_indexing.py
from pathlib import Path

from bot import index_image_from_message, SimpleMessage
from storage import get_image_by_id


def test_index_image_with_user_text_and_ocr(tmp_path: Path, conn, monkeypatch):
    img_path = tmp_path / "img.png"
    img_path.write_bytes(b"fake image data")

    # IMPORTANT: Patch bot.extract_text, not ocr.extract_text!
    monkeypatch.setattr("bot.extract_text", lambda path: "ocr words")

    message = SimpleMessage(
        content="user words",
        author_id=111,
        channel_id=222,
        message_id=333,
    )

    img_id = index_image_from_message(conn, message, str(img_path))

    row = get_image_by_id(conn, img_id)
    assert row["user_text"] == "user words"
    assert row["ocr_text"] == "ocr words"
    assert row["index_text"] == "user words ocr words"


def test_index_image_with_only_ocr(tmp_path: Path, conn, monkeypatch):
    img_path = tmp_path / "img.png"
    img_path.write_bytes(b"fake image data")

    # IMPORTANT: Patch bot.extract_text
    monkeypatch.setattr("bot.extract_text", lambda path: "ocr only")

    message = SimpleMessage(
        content="",  # no user text
        author_id=111,
        channel_id=222,
        message_id=333,
    )

    img_id = index_image_from_message(conn, message, str(img_path))

    row = get_image_by_id(conn, img_id)
    assert row["user_text"] is None
    assert row["ocr_text"] == "ocr only"
    assert row["index_text"] == "ocr only"

