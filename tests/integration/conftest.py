"""Postgres fixtures for repository integration tests.

Skipped unless all of these are set:
  BOOKING_BOT_INTEGRATION=1
  POSTGRES_HOST, POSTGRES_PORT, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD

Use a dedicated database (e.g. booking_bot_test), not the bot's production volume.
Fixtures call ``run_migrations`` directly — they do not load bot ``Config`` / ``.env``
secrets like BOT_TOKEN.
"""

from __future__ import annotations

import asyncio
import os

import pytest
import pytest_asyncio
from app.infrastructure.database.connection import build_pg_conninfo
from migrations.migrate import run_migrations
from psycopg import AsyncConnection

# Tables with app data (not schema_migrations). CASCADE clears FK dependents.
_TRUNCATE_TABLES = (
    "appointments",
    "services",
    "time_off",
    "work_dates",
    "working_hours",
    "master_settings",
    "users",
)


def _integration_enabled() -> bool:
    return os.environ.get("BOOKING_BOT_INTEGRATION") == "1"


def _postgres_conninfo_or_skip() -> str:
    if not _integration_enabled():
        pytest.skip(
            "Set BOOKING_BOT_INTEGRATION=1 and POSTGRES_* to run integration tests",
        )
    host = os.environ.get("POSTGRES_HOST", "").strip()
    db_name = os.environ.get("POSTGRES_DB", "").strip()
    user = os.environ.get("POSTGRES_USER", "").strip()
    password = os.environ.get("POSTGRES_PASSWORD")
    port_raw = os.environ.get("POSTGRES_PORT", "5432").strip()
    if not host or not db_name or not user or password is None:
        pytest.skip(
            "POSTGRES_HOST, POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD required",
        )
    try:
        port = int(port_raw)
    except ValueError:
        pytest.skip(f"Invalid POSTGRES_PORT: {port_raw!r}")
    return build_pg_conninfo(
        db_name=db_name,
        host=host,
        port=port,
        user=user,
        password=password,
    )


@pytest.fixture(scope="session")
def postgres_conninfo() -> str:
    return _postgres_conninfo_or_skip()


@pytest.fixture(scope="session")
def _schema_ready(postgres_conninfo: str) -> None:
    async def _migrate() -> None:
        conn = await AsyncConnection.connect(conninfo=postgres_conninfo)
        try:
            await run_migrations(conn)
            await conn.commit()
        finally:
            await conn.close()

    asyncio.run(_migrate())


async def _truncate_app_tables(conn: AsyncConnection) -> None:
    tables = ", ".join(_TRUNCATE_TABLES)
    async with conn.cursor() as cursor:
        await cursor.execute(f"TRUNCATE {tables} RESTART IDENTITY CASCADE;")
    await conn.commit()


@pytest_asyncio.fixture
async def db_conn(_schema_ready: None, postgres_conninfo: str):
    """Clean connection with schema applied; tables truncated before each test."""
    conn = await AsyncConnection.connect(conninfo=postgres_conninfo)
    try:
        await _truncate_app_tables(conn)
        yield conn
    finally:
        await conn.close()
