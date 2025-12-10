# tests/test_storage.py
from storage import save_image_record, get_image_by_id, fetch_all_images


def test_save_and_get_image(conn):
    img_id = save_image_record(
        conn,
        uploader_id="123",
        channel_id="456",
        message_id="789",
        file_path="/tmp/a.png",
        user_text="hello",
        ocr_text="world",
    )

    row = get_image_by_id(conn, img_id)
    assert row is not None
    assert row["uploader_id"] == "123"
    assert row["index_text"] == "hello world"


def test_fetch_all_images(conn):
    from storage import insert_image_for_test

    insert_image_for_test(conn, "u1", "c1", "m1", "/tmp/1.png", "cat on sofa")
    insert_image_for_test(conn, "u2", "c1", "m2", "/tmp/2.png", "dog in garden")

    rows = list(fetch_all_images(conn))
    assert len(rows) == 2
    texts = sorted(r["index_text"] for r in rows)
    assert texts == ["cat on sofa", "dog in garden"]

