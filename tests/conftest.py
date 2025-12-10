# tests/conftest.py
import sqlite3
import pytest

from storage import init_db


@pytest.fixture
def conn():
    """Fresh in-memory DB for each test."""
    connection = sqlite3.connect(":memory:")
    # Enable row access by column name if you want, but we convert to dict anyway
    init_db(connection)
    yield connection
    connection.close()

