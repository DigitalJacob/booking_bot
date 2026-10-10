import pytest
from psycopg import AsyncConnection

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_migrations_create_appointments_table(db_conn: AsyncConnection) -> None:
    async with db_conn.cursor() as cursor:
        await cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'appointments'
            );
            """
        )
        row = await cursor.fetchone()
    assert row is not None
    assert row[0] is True


@pytest.mark.asyncio
async def test_migrations_install_appointments_no_overlap(
        db_conn: AsyncConnection,
) -> None:
    async with db_conn.cursor() as cursor:
        await cursor.execute(
            """
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'appointments_no_overlap';
            """
        )
        row = await cursor.fetchone()
    assert row is not None
