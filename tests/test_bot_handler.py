# tests/test_bot_handler.py
import pytest
from bot import handle_text_query


class FakeChannel:
    def __init__(self):
        self.sent = []

    async def send(self, content=None, file=None):
        self.sent.append({
            "content": content,
            "file": file,
        })


class FakeMessage:
    def __init__(self, content):
        self.content = content
        self.channel = FakeChannel()


@pytest.mark.asyncio
async def test_text_message_calls_search(monkeypatch, conn):
    called = {"query": None}

    # Fake search returns no matches
    def fake_search(conn_arg, query, limit=1):
        called["query"] = query
        return []

    monkeypatch.setattr("bot.search_best_match", fake_search)

    msg = FakeMessage("cat")

    await handle_text_query(conn, msg)

    # search query recorded
    assert called["query"] == "cat"

    # bot should respond "No matching image found."
    assert msg.channel.sent[0]["content"] == "No matching image found."
    assert msg.channel.sent[0]["file"] is None


@pytest.mark.asyncio
async def test_text_message_returns_image(monkeypatch, conn):
    # Fake a search result: return one mock row with file_path
    def fake_search(conn_arg, query, limit=1):
        return [{
            "id": 1,
            "file_path": "/tmp/test.png",
            "index_text": "a test image"
        }]

    monkeypatch.setattr("bot.search_best_match", fake_search)

    # Fake discord.File so it doesn't try to open an actual file
    class FakeDiscordFile:
        def __init__(self, path):
            self.path = path

    monkeypatch.setattr("discord.File", FakeDiscordFile)

    msg = FakeMessage("test")

    await handle_text_query(conn, msg)

    sent = msg.channel.sent[0]

    # It should send a file object (our fake)
    assert isinstance(sent["file"], FakeDiscordFile)
    assert sent["file"].path == "/tmp/test.png"

    # Should NOT send text when sending a file
    assert sent["content"] is None
