import asyncio
import logging
import os
import sys
from pathlib import Path

from psycopg import AsyncConnection, Error

from app.infrastructure.database.connection import get_pg_connection
from config.config import Config, load_config


config: Config = load_config()

logging.basicConfig(
    level=logging.getLevelName(level=config.log.level),
    format=config.log.format,
)

logger = logging.getLogger(__name__)

if sys.platform.startswith("win") or os.name == "nt":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


VERSIONS_DIR = Path(__file__).resolve().parent / "versions"


async def _ensure_migrations_table(conn: AsyncConnection) -> None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            query="""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    version TEXT PRIMARY KEY,
                    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """
        )


async def _applied_versions(conn: AsyncConnection) -> set[str]:
    async with conn.cursor() as cursor:
        await cursor.execute("SELECT version FROM schema_migrations;")
        rows = await cursor.fetchall()
    return {row[0] for row in rows}


async def _users_table_exists(conn: AsyncConnection) -> bool:
    async with conn.cursor() as cursor:
        await cursor.execute(
            query="""
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                        AND table_name = 'users'
                );
            """
        )
        row = await cursor.fetchone()
    return bool(row and row[0])


def _list_migration_files() -> list[Path]:
    if not VERSIONS_DIR.is_dir():
        raise FileNotFoundError(f"Migrations directory not found: {VERSIONS_DIR}")
    files = sorted(VERSIONS_DIR.glob("*.sql"))
    return files


def _version_id(path: Path) -> str:
    return path.stem


async def _mark_applied(conn: AsyncConnection, version: str) -> None:
    async with conn.cursor() as cursor:
        await cursor.execute(
            query="""
                INSERT INTO schema_migrations (version)
                VALUES (%s)
                ON CONFLICT (version) DO NOTHING;
            """,
            params=(version, ),
        )


async def _apply_sql_file(conn: AsyncConnection, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    async with conn.cursor() as cursor:
        await cursor.execute(sql) # type: ignore[arg-type]


async def run_migrations(conn: AsyncConnection) -> None:
    await _ensure_migrations_table(conn)

    files = _list_migration_files()
    if not files:
        logger.warning("No migration files found in %s", VERSIONS_DIR)
        return

    applied = await _applied_versions(conn)

    first = files[0]
    first_version = _version_id(first)
    if (
        first_version not in applied
        and await _users_table_exists(conn)
    ):
        async with conn.transaction():
            await _mark_applied(conn, first_version)
        applied.add(first_version)
        logger.info(
            "Baseline: marked %s as applied (existing schema detected)",
            first_version,
        )

    for path in files:
        version = _version_id(path)
        if version in applied:
            logger.info("Skip migration %s (already applied)", version)
            continue

        logger.info("Applying migration %s ...", version)
        async with conn.transaction():
            await _apply_sql_file(conn, path)
            await _mark_applied(conn, version)
        logger.info("Applied migration %s", version)


async def main() -> None:
    connection: AsyncConnection | None = None
    try:
        connection = await get_pg_connection(
            db_name=config.db.name,
            host=config.db.host,
            port=config.db.port,
            user=config.db.user,
            password=config.db.password,
        )
        async with connection:
            await run_migrations(connection)
        logger.info("Migrations finished successfully")
    except Error as db_error:
        logger.exception("Database-specific error: %s", db_error)
        raise
    except Exception:
        logger.exception("Unhandled error during migrations")
        raise
    finally:
        if connection and not connection.closed:
            await connection.close()
            logger.info("Connection to Postgres closed")


if __name__ == "__main__":
    asyncio.run(main())
