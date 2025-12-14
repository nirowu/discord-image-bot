import time

from features.scheduling.storage import (
    init_scheduler_db,
    create_scheduled_message,
    list_scheduled_messages,
    cancel_scheduled_message,
    claim_due_messages,
    mark_sent,
)


def test_create_and_list_pending(conn):
    init_scheduler_db(conn)
    now = int(time.time())

    schedule_id = create_scheduled_message(
        conn,
        channel_id="123",
        kind="text",
        content="hello later",
        run_at=now + 60,
        created_by="u1",
    )
    assert isinstance(schedule_id, int)

    rows = list_scheduled_messages(conn, channel_id="123")
    assert len(rows) == 1
    assert rows[0]["id"] == schedule_id
    assert rows[0]["status"] == "pending"
    assert rows[0]["kind"] == "text"


def test_cancel_only_by_creator(conn):
    init_scheduler_db(conn)
    now = int(time.time())

    schedule_id = create_scheduled_message(
        conn,
        channel_id="123",
        kind="text",
        content="will be canceled",
        run_at=now + 60,
        created_by="u1",
    )

    assert cancel_scheduled_message(conn, schedule_id=schedule_id, requester_id="u2") is False
    assert cancel_scheduled_message(conn, schedule_id=schedule_id, requester_id="u1") is True

    rows = list_scheduled_messages(conn, include_non_pending=True)
    assert rows[0]["status"] == "canceled"


def test_claim_due_and_mark_sent(conn):
    init_scheduler_db(conn)
    now = int(time.time())

    schedule_id = create_scheduled_message(
        conn,
        channel_id="123",
        kind="text",
        content="due now",
        run_at=now - 1,
        created_by="u1",
    )

    claimed = claim_due_messages(conn, now=now, limit=10)
    assert [r["id"] for r in claimed] == [schedule_id]
    assert claimed[0]["status"] == "sending"

    mark_sent(conn, schedule_id, sent_at=now)

    rows = list_scheduled_messages(conn, include_non_pending=True)
    assert rows[0]["status"] == "sent"
    assert rows[0]["sent_at"] == now
