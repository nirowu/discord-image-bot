# tests/test_random.py
import os
import sys
import sqlite3

import pytest

# Ensure repo root is importable when pytest's rootdir is not the project root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# In minimal environments (like this sandbox) discord.py might not be installed.
# The real project depends on discord.py; this stub keeps unit tests runnable.
try:  # pragma: no cover
    import discord  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    import types

    discord = types.ModuleType("discord")

    class _Choice:  # minimal stub for discord.app_commands.Choice
        def __init__(self, name: str, value: str):
            self.name = name
            self.value = value

    app_commands = types.SimpleNamespace(Choice=_Choice)
    discord.app_commands = app_commands

    class File:  # minimal stub
        def __init__(self, path: str):
            self.path = path

    discord.File = File

    sys.modules["discord"] = discord

# Stub OCR deps in minimal environments.
try:  # pragma: no cover
    import easyocr  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    import types

    easyocr = types.ModuleType("easyocr")

    class Reader:
        def __init__(self, *_args, **_kwargs):
            pass

        def readtext(self, _img, detail=0):
            return []

    easyocr.Reader = Reader
    sys.modules["easyocr"] = easyocr

try:  # pragma: no cover
    import cv2  # type: ignore
except ModuleNotFoundError:  # pragma: no cover
    import types

    cv2 = types.ModuleType("cv2")
    cv2.COLOR_BGR2GRAY = 0

    def imread(_path):
        return None

    def resize(img, *_args, **_kwargs):
        return img

    def cvtColor(img, _code):
        return img

    cv2.imread = imread
    cv2.resize = resize
    cv2.cvtColor = cvtColor

    cv2.typing = types.SimpleNamespace(MatLike=object)

    sys.modules["cv2"] = cv2

import storage
import bot


class DummyResponse:
    def __init__(self):
        self.calls = []

    async def send_message(self, *args, **kwargs):
        self.calls.append((args, kwargs))


class DummyInteraction:
    def __init__(self):
        self.response = DummyResponse()


def make_conn():
    conn = sqlite3.connect(":memory:")
    storage.init_db(conn)
    return conn


def test_get_random_image_empty_returns_none():
    conn = make_conn()
    assert storage.get_random_image(conn) is None


def test_get_random_image_returns_a_row():
    conn = make_conn()
    ids = []
    for i in range(5):
        ids.append(
            storage.insert_image_for_test(
                conn,
                uploader_id="u",
                channel_id="c",
                message_id=str(i),
                file_path=f"/tmp/img_{i}.png",
                index_text=f"img {i}",
            )
        )

    row = storage.get_random_image(conn)
    assert row is not None
    assert row["id"] in ids


@pytest.mark.asyncio
async def test_run_random_command_sends_a_file(monkeypatch):
    conn = make_conn()
    storage.insert_image_for_test(
        conn,
        uploader_id="u",
        channel_id="c",
        message_id="m",
        file_path="/tmp/img.png",
        index_text="hello",
    )

    # Avoid touching the filesystem; discord.File normally opens the path.
    class FakeFile:
        def __init__(self, path):
            self.path = path

    monkeypatch.setattr(bot.discord, "File", FakeFile)

    interaction = DummyInteraction()
    await bot.run_random_command(interaction, conn)

    assert len(interaction.response.calls) == 1
    _args, kwargs = interaction.response.calls[0]
    assert kwargs["ephemeral"] is False
    assert isinstance(kwargs["file"], FakeFile)
    assert kwargs["file"].path == "/tmp/img.png"

