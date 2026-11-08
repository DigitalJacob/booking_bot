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


@pytest.mark.asyncio
async def test_migrations_create_appointment_reschedules_and_column(
    db_conn: AsyncConnection,
) -> None:
    async with db_conn.cursor() as cursor:
        await cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'appointment_reschedules'
            );
            """
        )
        table_row = await cursor.fetchone()
        await cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'appointments'
                  AND column_name = 'rescheduled_at'
            );
            """
        )
        column_row = await cursor.fetchone()
    assert table_row is not None and table_row[0] is True
    assert column_row is not None and column_row[0] is True
