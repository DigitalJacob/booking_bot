"""Schema checks for manual_clients and appointments client XOR (migration 015)."""

from datetime import UTC, datetime, timedelta

import pytest
from psycopg import AsyncConnection
from psycopg.errors import CheckViolation, UniqueViolation

pytestmark = pytest.mark.integration

MASTER_A = 1101
MASTER_B = 1102
CLIENT_TG = 2101

START = datetime(2026, 11, 1, 10, 0, tzinfo=UTC)
END = START + timedelta(hours=1)


async def _seed_users_and_service(conn: AsyncConnection) -> int:
    async with conn.cursor() as cursor:
        for user_id, role in (
            (MASTER_A, "master"),
            (MASTER_B, "master"),
            (CLIENT_TG, "client"),
        ):
            await cursor.execute(
                """
                INSERT INTO users (user_id, language, role)
                VALUES (%s, 'ru', %s);
                """,
                (user_id, role),
            )
        await cursor.execute(
            """
            INSERT INTO services (master_user_id, title, duration_minutes, price)
            VALUES (%s, 'Schema test', 60, 1000)
            RETURNING id;
            """,
            (MASTER_A,),
        )
        row = await cursor.fetchone()
    assert row is not None
    await conn.commit()
    return int(row[0])


async def _insert_manual_client(
    conn: AsyncConnection,
    *,
    master_user_id: int,
    name: str,
    phone: str,
    phone_digits: str,
) -> int:
    async with conn.cursor() as cursor:
        await cursor.execute(
            """
            INSERT INTO manual_clients (
                master_user_id, name, phone, phone_digits
            )
            VALUES (%s, %s, %s, %s)
            RETURNING id;
            """,
            (master_user_id, name, phone, phone_digits),
        )
        row = await cursor.fetchone()
    assert row is not None
    await conn.commit()
    return int(row[0])


@pytest.mark.asyncio
async def test_manual_clients_table_exists(db_conn: AsyncConnection) -> None:
    async with db_conn.cursor() as cursor:
        await cursor.execute(
            """
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = 'manual_clients'
            );
            """
        )
        row = await cursor.fetchone()
    assert row is not None
    assert row[0] is True


@pytest.mark.asyncio
async def test_appointments_client_xor_constraint_exists(
    db_conn: AsyncConnection,
) -> None:
    async with db_conn.cursor() as cursor:
        await cursor.execute(
            """
            SELECT 1
            FROM pg_constraint
            WHERE conname = 'appointments_client_xor';
            """
        )
        row = await cursor.fetchone()
    assert row is not None


@pytest.mark.asyncio
async def test_appointment_with_only_telegram_client_ok(
    db_conn: AsyncConnection,
) -> None:
    service_id = await _seed_users_and_service(db_conn)
    async with db_conn.cursor() as cursor:
        await cursor.execute(
            """
            INSERT INTO appointments (
                client_user_id,
                master_user_id,
                service_id,
                starts_at,
                ends_at,
                status
            )
            VALUES (%s, %s, %s, %s, %s, 'confirmed')
            RETURNING id, manual_client_id;
            """,
            (CLIENT_TG, MASTER_A, service_id, START, END),
        )
        row = await cursor.fetchone()
    await db_conn.commit()
    assert row is not None
    assert row[0] > 0
    assert row[1] is None


@pytest.mark.asyncio
async def test_appointment_with_only_manual_client_ok(
    db_conn: AsyncConnection,
) -> None:
    service_id = await _seed_users_and_service(db_conn)
    manual_id = await _insert_manual_client(
        db_conn,
        master_user_id=MASTER_A,
        name="Ivan",
        phone="+79991234567",
        phone_digits="79991234567",
    )
    async with db_conn.cursor() as cursor:
        await cursor.execute(
            """
            INSERT INTO appointments (
                client_user_id,
                manual_client_id,
                master_user_id,
                service_id,
                starts_at,
                ends_at,
                status
            )
            VALUES (NULL, %s, %s, %s, %s, %s, 'confirmed')
            RETURNING id, client_user_id, manual_client_id;
            """,
            (manual_id, MASTER_A, service_id, START, END),
        )
        row = await cursor.fetchone()
    await db_conn.commit()
    assert row is not None
    assert row[1] is None
    assert row[2] == manual_id


@pytest.mark.asyncio
async def test_appointment_rejects_both_clients(
    db_conn: AsyncConnection,
) -> None:
    service_id = await _seed_users_and_service(db_conn)
    manual_id = await _insert_manual_client(
        db_conn,
        master_user_id=MASTER_A,
        name="Ivan",
        phone="+79991234567",
        phone_digits="79991234567",
    )
    with pytest.raises(CheckViolation):
        async with db_conn.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO appointments (
                    client_user_id,
                    manual_client_id,
                    master_user_id,
                    service_id,
                    starts_at,
                    ends_at,
                    status
                )
                VALUES (%s, %s, %s, %s, %s, %s, 'confirmed');
                """,
                (CLIENT_TG, manual_id, MASTER_A, service_id, START, END),
            )
    await db_conn.rollback()


@pytest.mark.asyncio
async def test_appointment_rejects_neither_client(
    db_conn: AsyncConnection,
) -> None:
    service_id = await _seed_users_and_service(db_conn)
    with pytest.raises(CheckViolation):
        async with db_conn.cursor() as cursor:
            await cursor.execute(
                """
                INSERT INTO appointments (
                    client_user_id,
                    manual_client_id,
                    master_user_id,
                    service_id,
                    starts_at,
                    ends_at,
                    status
                )
                VALUES (NULL, NULL, %s, %s, %s, %s, 'confirmed');
                """,
                (MASTER_A, service_id, START, END),
            )
    await db_conn.rollback()


@pytest.mark.asyncio
async def test_manual_clients_phone_unique_per_master(
    db_conn: AsyncConnection,
) -> None:
    await _seed_users_and_service(db_conn)
    await _insert_manual_client(
        db_conn,
        master_user_id=MASTER_A,
        name="Ivan",
        phone="+79991234567",
        phone_digits="79991234567",
    )
    with pytest.raises(UniqueViolation):
        await _insert_manual_client(
            db_conn,
            master_user_id=MASTER_A,
            name="Ivan Duplicate",
            phone="8 (999) 123-45-67",
            phone_digits="79991234567",
        )
    await db_conn.rollback()


@pytest.mark.asyncio
async def test_manual_clients_same_phone_different_masters_ok(
    db_conn: AsyncConnection,
) -> None:
    await _seed_users_and_service(db_conn)
    first = await _insert_manual_client(
        db_conn,
        master_user_id=MASTER_A,
        name="Ivan A",
        phone="+79991234567",
        phone_digits="79991234567",
    )
    second = await _insert_manual_client(
        db_conn,
        master_user_id=MASTER_B,
        name="Ivan B",
        phone="+79991234567",
        phone_digits="79991234567",
    )
    assert first != second
