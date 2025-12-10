# tests/test_slash.py
import pytest
from bot import run_img_command, run_img_autocomplete


class FakeResponse:
    def __init__(self):
        self.sent = []

    async def send_message(self, content=None, file=None, ephemeral=False):
        self.sent.append({"content": content, "file": file, "ephemeral": ephemeral})

    async def send_autocomplete(self, choices):
        self.sent.append({"choices": choices})


class FakeInteraction:
    def __init__(self):
        self.response = FakeResponse()


@pytest.mark.asyncio
async def test_img_command_no_match(monkeypatch, conn):
    def fake_search(conn_arg, query, limit=1):
        return []

    monkeypatch.setattr("bot.search_best_match", fake_search)

    interaction = FakeInteraction()

    await run_img_command(interaction, conn, "nothing")

    sent = interaction.response.sent[0]
    assert sent["content"] == "No image found"
    assert sent["ephemeral"] is True


@pytest.mark.asyncio
async def test_img_command_returns_image(monkeypatch, conn):
    class FakeDiscordFile:
        def __init__(self, path):
            self.path = path

    monkeypatch.setattr("discord.File", FakeDiscordFile)

    def fake_search(conn_arg, query, limit=1):
        return [{
            "file_path": "/tmp/test.png",
            "index_text": "image result"
        }]

    monkeypatch.setattr("bot.search_best_match", fake_search)

    interaction = FakeInteraction()
    await run_img_command(interaction, conn, "image")

    sent = interaction.response.sent[0]
    assert sent["file"].path == "/tmp/test.png"
    assert sent["ephemeral"] is False


@pytest.mark.asyncio
async def test_img_autocomplete(monkeypatch, conn):
    def fake_search(conn_arg, query, limit=5):
        return [
            {"index_text": "cat"},
            {"index_text": "dog"},
            {"index_text": "bird"},
        ]

    monkeypatch.setattr("bot.search_best_match", fake_search)

    interaction = FakeInteraction()
    await run_img_autocomplete(interaction, conn, "a")

    sent = interaction.response.sent[0]
    choices = sent["choices"]

    assert len(choices) == 3
    assert choices[0].name == "cat"
    assert choices[1].name == "dog"
    assert choices[2].name == "bird"

