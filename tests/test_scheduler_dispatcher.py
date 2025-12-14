import time

import pytest

from features.scheduling.dispatcher import dispatch_due_messages
from features.scheduling.storage import (
    init_scheduler_db,
    create_scheduled_message,
    list_scheduled_messages,
)
from storage import init_db, insert_image_for_test


class FakeChannel:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, file=None):
        self.sent.append({"content": content, "file": file})


class FakeBot:
    def __init__(self, channels):
        self._channels = channels

    def get_channel(self, channel_id: int):
        return self._channels.get(channel_id)


@pytest.mark.asyncio
async def test_dispatch_sends_and_marks_sent(conn):
    init_scheduler_db(conn)
    now = int(time.time())

    channel = FakeChannel()
    bot = FakeBot({123: channel})

    create_scheduled_message(
        conn,
        channel_id="123",
        kind="text",
        content="hello scheduled",
        run_at=now - 1,
        repeat_interval=None,
        created_by="u1",
    )

    sent_count = await dispatch_due_messages(bot, conn, now=now)
    assert sent_count == 1
    assert channel.sent == [{"content": "hello scheduled", "file": None}]

    rows = list_scheduled_messages(conn, include_non_pending=True)
    assert rows[0]["status"] == "sent"


@pytest.mark.asyncio
async def test_dispatch_marks_failed_if_channel_missing(conn):
    init_scheduler_db(conn)
    now = int(time.time())

    bot = FakeBot({})

    create_scheduled_message(
        conn,
        channel_id="999",
        kind="text",
        content="will fail",
        run_at=now - 1,
        repeat_interval=None,
        created_by="u1",
    )

    sent_count = await dispatch_due_messages(bot, conn, now=now)
    assert sent_count == 0

    rows = list_scheduled_messages(conn, include_non_pending=True)
    assert rows[0]["status"] == "failed"
    assert "not found" in (rows[0]["error"] or "")


@pytest.mark.asyncio
async def test_dispatch_image_search_handler(conn, monkeypatch):
    init_db(conn)
    init_scheduler_db(conn)
    now = int(time.time())

    insert_image_for_test(conn, "u", "c", "m", "/tmp/1.png", "cat on sofa")

    class FakeDiscordFile:
        def __init__(self, path):
            self.path = path

    monkeypatch.setattr("discord.File", FakeDiscordFile)

    async def image_handler(channel, conn_arg, query: str):
        from search import search_best_match

        matches = search_best_match(conn_arg, query, limit=1)
        if not matches:
            await channel.send(content="No matching image found.")
            return
        await channel.send(file=FakeDiscordFile(matches[0]["file_path"]))

    channel = FakeChannel()
    bot = FakeBot({123: channel})

    create_scheduled_message(
        conn,
        channel_id="123",
        kind="image_search",
        content="cot on sofe",
        run_at=now - 1,
        repeat_interval=None,
        created_by="u1",
    )

    sent_count = await dispatch_due_messages(
        bot,
        conn,
        now=now,
        handlers={"image_search": image_handler},
    )
    assert sent_count == 1
    assert channel.sent[0]["file"].path == "/tmp/1.png"


@pytest.mark.asyncio
async def test_dispatch_repeat_reschedules_and_announces_next(conn):
    init_scheduler_db(conn)
    now = int(time.time())

    channel = FakeChannel()
    bot = FakeBot({123: channel})

    create_scheduled_message(
        conn,
        channel_id="123",
        kind="text",
        content="repeat me",
        run_at=now - 1,
        repeat_interval="minute",
        created_by="u1",
    )

    sent_count = await dispatch_due_messages(bot, conn, now=now)
    assert sent_count == 1

    assert channel.sent[0]["content"] == "repeat me"
    assert "Next at" in (channel.sent[1]["content"] or "")

    rows = list_scheduled_messages(conn, include_non_pending=True)
    assert rows[0]["status"] == "pending"
    assert rows[0]["run_at"] > now
