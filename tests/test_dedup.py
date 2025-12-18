from pathlib import Path

from bot import index_image_from_message, SimpleMessage
from storage import get_image_by_id, fetch_all_images


def test_index_image_deduplication_removes_duplicate_file(
    tmp_path: Path, conn, monkeypatch
):
    """
    When the same image hash is seen twice:
    - first image is indexed normally
    - second image is detected as duplicate
    - duplicate file is removed
    - no new DB row is created
    """

    # Always return the same hash
    monkeypatch.setattr("bot.compute_image_hash", lambda path: "same_hash")

    # Avoid real OCR
    monkeypatch.setattr("bot.extract_text", lambda path: "ocr text")

    # First image
    img1 = tmp_path / "img1.png"
    img1.write_bytes(b"fake image data 1")

    msg1 = SimpleMessage(
        content="hello",
        author_id=1,
        channel_id=10,
        message_id=100,
    )

    id1 = index_image_from_message(conn, msg1, str(img1))

    assert id1 > 0
    assert img1.exists()

    # Second (duplicate) image
    img2 = tmp_path / "img2.png"
    img2.write_bytes(b"fake image data 2")

    msg2 = SimpleMessage(
        content="hello again",
        author_id=2,
        channel_id=10,
        message_id=200,
    )

    id2 = index_image_from_message(conn, msg2, str(img2))

    # Duplicate is signaled by negative id
    assert id2 < 0
    assert -id2 == id1

    # Duplicate file must be removed
    assert not img2.exists()

    # DB should contain only one image
    rows = list(fetch_all_images(conn))
    assert len(rows) == 1

    row = get_image_by_id(conn, id1)
    assert row is not None
    assert row["user_text"] == "hello"
    assert row["ocr_text"] == "ocr text"
