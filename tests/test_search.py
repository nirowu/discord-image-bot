# tests/test_search.py
from storage import insert_image_for_test
from search import search_best_match


def test_search_picks_closest_text(conn):
    insert_image_for_test(conn, "u1", "c1", "m1", "/tmp/1.png", "cat on sofa")
    insert_image_for_test(conn, "u2", "c1", "m2", "/tmp/2.png", "dog in garden")

    result = search_best_match(conn, "cot on sofe")
    assert len(result) == 1
    assert result[0]["index_text"] == "cat on sofa"


def test_search_rejects_low_scores(conn):
    insert_image_for_test(conn, "u1", "c1", "m1", "/tmp/1.png", "cat on sofa")

    result = search_best_match(conn, "unrelated text")
    assert result == []

