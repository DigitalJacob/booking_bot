# 📅 Booking Bot

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.20-green.svg)](https://docs.aiogram.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.4-red.svg)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docs.docker.com/compose/)
[![Tests](https://img.shields.io/badge/tests-pytest-orange.svg)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Telegram bot that runs appointment booking for a small service business — a barber,
a nail studio, a private tutor. Clients pick a service, see only the time slots that
actually fit it, and book in four taps. The master manages services, opens time slots,
and confirms or declines requests without leaving Telegram. Both sides get notified on
every status change.

Built on a layered architecture with the business logic isolated from Telegram and SQL,
and covered by unit tests.

## Tech Stack

| Technology | Purpose |
|------------|---------|
| **Python 3.13** | Core language |
| **aiogram 3.20** | Telegram Bot API framework |
| **PostgreSQL 17** | Persistent storage for users, services, slots and appointments |
| **Redis 7.4** | FSM state storage for multi-step dialogs |
| **psycopg 3** | Async PostgreSQL driver with connection pooling |
| **Docker Compose** | Runs the bot and all infrastructure services |
| **pytest / pytest-asyncio** | Unit tests for the domain layer |
| **pgAdmin** | Visual database management |
| **environs** | Typed environment variable parsing |
| **aiohttp-socks** | Optional HTTP/SOCKS5 proxy for the Telegram session |

## Architecture

The project is split into three layers with a strict dependency direction —
outer layers know about inner ones, never the reverse.

```
app/
├── domain/           # Business logic. No aiogram, no SQL, no I/O.
│   ├── models/       # Immutable dataclasses: User, Service, Slot, Appointment
│   ├── enums/        # UserRole, AppointmentStatus
│   ├── exceptions.py # SlotTaken, SlotTooShort, ForbiddenBookingAction, ...
│   └── services/     # BookingService — all booking rules live here
│
├── infrastructure/   # Everything that talks to the outside world.
│   └── database/     # Connection pool and repositories (raw SQL only)
│
└── bot/              # Telegram presentation layer.
    ├── handlers/     # Commands and callbacks, grouped by role
    ├── keyboards/    # Inline keyboards and typed CallbackData
    ├── middlewares/  # Transactions, user context, i18n, ban check
    ├── states/       # FSM state groups
    └── i18n/         # Locale resolution
```

**Why it matters in practice.** `BookingService` never imports aiogram or psycopg —
it depends only on repository objects passed into it. That is what makes the booking
rules testable without a database, a Redis instance or a Telegram token: the test
suite swaps in in-memory fakes and runs in well under a second.

Repositories hold **only** SQL. Handlers hold **only** dialog flow and formatting.
A rule like "a slot must be long enough for the chosen service" is written once, in
the domain, and applies no matter which handler triggers it.

Each update is wrapped in a single database transaction by `DataBaseMiddleware`, so a
failure halfway through a booking cannot leave a half-written appointment behind.

## Features

### For clients

- **Guided booking** — step-by-step dialog: service → day → time → confirmation
- **Only bookable slots are shown** — slots shorter than the chosen service, already
  taken, or in the past are filtered out before the client ever sees them
- **`/my_bookings`** — upcoming appointments with their current status
- **Self-service cancellation** — cancel your own booking; the master is notified
- **Status notifications** — a message arrives when the master confirms or declines

### For the master

- **`/today`** — every appointment for the current day as a card with inline actions
- **One-tap confirm / decline** — the keyboard is removed after the action, so a
  finished card cannot be tapped twice by accident
- **Service catalogue** — title, duration and price per service, with soft
  deactivation instead of deletion
- **Time slot management** — open slots by date, start time and duration
- **New booking notifications** — delivered the moment a client books

### For admins

- **`/user`** — look up a user card by `@username` or numeric id
- **`/set_role`** — promote or demote between client, master and admin
- **`/ban` / `/unban`** — shadow ban: banned users get no reply at all, so they cannot
  tell they were blocked and cannot probe the bot for a reaction
- **Guard rails** — an admin cannot ban themselves, demote themselves, or ban other staff
- **Live menu refresh** — the affected user's command menu updates on role change

### Platform

- **Bilingual interface** — Russian and English, switchable at runtime via `/lang`
- **Role-aware command menu** — Telegram shows each user only the commands they may run
- **Language resolution chain** — explicit choice → Telegram client language → default
- **Concurrency safety** — a database unique constraint, not an application check,
  guarantees two clients can never take the same slot
- **UTC everywhere** — all timestamps stored as `TIMESTAMPTZ`
- **Structured logging** with a configurable level and rotating Docker log files

## Commands

| Command | Role | Description |
|---------|------|-------------|
| `/start` | everyone | Register, get the role-specific greeting and menu |
| `/help` | everyone | Command reference for your role |
| `/lang` | everyone | Switch interface language (RU / EN) |
| `/book` | client | Book an appointment |
| `/my_bookings` | client | View and cancel your upcoming appointments |
| `/today` | master | Today's appointments with confirm / decline actions |
| `/services` | master | List your services |
| `/add_service` | master | Add a service (title, duration, price) |
| `/add_slot` | master | Open a time slot (date, start time, duration) |
| `/cancel` | master | Abort the current `/add_service` or `/add_slot` dialog |
| `/user <@username\|id>` | admin | Show a user card |
| `/set_role <id> <role>` | admin | Change a user's role |
| `/ban <@username\|id>` | admin | Ban a user |
| `/unban <@username\|id>` | admin | Lift a ban |

## Roles

Three roles, all stored in the database — nothing is hardcoded in the source.

| Role | Gets |
|------|------|
| `client` | Booking and managing their own appointments. Default for new users. |
| `master` | Service catalogue, time slots, and the daily appointment list. |
| `admin` | User management and role assignment, plus the client commands. |

### First run: bootstrapping the master

A fresh database has no master, so nobody can create services yet. Set it up once:

1. Put your own Telegram id in `ADMIN_IDS` in `.env`.
2. Send `/start` — you are registered as an **admin**.
3. Ask the master to send `/start` too, then take their id from the `users` table
   (or from `/user @their_username`).
4. Promote them: `/set_role <master_id> master`
5. Put that same id in `MASTER_USER_ID` in `.env` and restart the bot.

`MASTER_USER_ID` tells the client `/book` flow whose services and slots to show.
`ADMIN_IDS` only decides which accounts become admins on their first `/start`.

> Don't know your Telegram id? Send any message to [@userinfobot](https://t.me/userinfobot).

## Quick Start

Requires **Docker** and **Docker Compose**. Everything, the bot included, runs in
containers — no local Python installation needed.

### 1. Clone the repository

```bash
git clone git@github.com:DigitalJacob/booking_bot.git
cd booking_bot
```

### 2. Create the environment file

```bash
cp .env.example .env
```

### 3. Fill in `.env`

At minimum set `BOT_TOKEN` (from [@BotFather](https://t.me/BotFather)), `ADMIN_IDS`,
`POSTGRES_PASSWORD` and `REDIS_PASSWORD`. See [Configuration](#configuration) below.

`MASTER_USER_ID` can stay as-is for now — you will fill it in after
[bootstrapping the master](#first-run-bootstrapping-the-master).

### 4. Start everything

```bash
docker compose up -d --build
```

This starts PostgreSQL, Redis, pgAdmin and the bot. Database migrations run
automatically on bot startup.

### 5. Check the logs

```bash
docker compose logs -f bot
```

You should see the bot configured and polling. Now send `/start` in Telegram.

### Useful commands

```bash
docker compose logs -f bot     # follow bot logs
docker compose restart bot     # restart after an .env change
docker compose up -d --build bot   # rebuild after a code change
docker compose down            # stop everything (data is kept)
```

pgAdmin is available at `http://localhost:${PGADMIN_PORT}` with the credentials from
`.env`. Connect to host `postgres`, port `5432`.

### Running locally without Docker

The bot can also run on the host while the databases stay in containers:

```bash
docker compose up -d postgres redis
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python3 -m migrations.create_tables
python3 main.py
```

Keep `POSTGRES_HOST=localhost` and `REDIS_HOST=localhost` in `.env` for this mode.

## Configuration

All settings come from `.env`. Start from `.env.example`.

| Variable | Description |
|----------|-------------|
| `BOT_TOKEN` | Telegram bot token from [@BotFather](https://t.me/BotFather) |
| `ADMIN_IDS` | Comma-separated Telegram ids granted the admin role on first `/start` |
| `MASTER_USER_ID` | Telegram id of the master whose services clients can book |
| `LOG_LEVEL` | `DEBUG` for development, `INFO` for production |
| `LOG_FORMAT` | Python logging format string |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | Database credentials |
| `POSTGRES_HOST` / `POSTGRES_PORT` | `postgres` / `5432` inside Compose |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_DATABASE` | Redis connection for FSM storage |
| `REDIS_USERNAME` / `REDIS_PASSWORD` | Redis credentials |
| `PGADMIN_DEFAULT_EMAIL` / `PGADMIN_DEFAULT_PASSWORD` / `PGADMIN_PORT` | pgAdmin access |
| `PROXY_*` | Optional proxy, disabled by default — see below |

### Optional: proxy

Commented out in `.env.example`. Uncomment all five lines to route the Telegram
session through a proxy:

```env
PROXY_TYPE=http
PROXY_IP=your_proxy_ip
PROXY_PORT=your_proxy_port
PROXY_LOGIN=your_proxy_login
PROXY_PASSWORD=your_proxy_password
```

Use `PROXY_TYPE=socks5` for SOCKS. Leave the lines commented to connect directly.

## Database Schema

Four tables, created automatically by `migrations/create_tables.py` on startup.

| Table | Purpose |
|-------|---------|
| `users` | Telegram id, username, language, role, ban flag |
| `services` | Master's offerings: title, duration, price, active flag |
| `slots` | Bookable time ranges owned by a master |
| `appointments` | Links a client, a service and a slot with a status |

`appointments.status` is one of `pending`, `confirmed`, `cancelled`.

Double booking is prevented at the database level: a partial unique index allows at
most one non-cancelled appointment per slot. Two clients tapping the same slot at the
same moment cannot both win — the loser gets a clean "slot already taken" message
instead of a duplicate row.

All timestamps are `TIMESTAMPTZ` and stored in UTC.

## Tests

The domain layer is covered by unit tests that use in-memory fake repositories, so
no database, Redis or bot token is needed.

```bash
pip install -r requirements-dev.txt
pytest
```

```
...................                                       [100%]
19 passed in 0.10s
```

The suite covers the rules in `BookingService`: rejecting inactive or unknown
services, slots that are taken, in the past, owned by another master or too short for
the chosen service; the confirm and cancel transitions with their permission checks;
and the filtering behind the available-slot and client-appointment listings.

## Project Structure

```
booking_bot/
├── app/
│   ├── bot/                # Telegram layer
│   │   ├── filters/        # Role and locale filters
│   │   ├── handlers/       # admin / client / master / common
│   │   ├── i18n/           # Locale resolution
│   │   ├── keyboards/      # Inline keyboards, CallbackData, menu button
│   │   ├── middlewares/    # DB transactions, user context, i18n, ban check
│   │   ├── states/         # FSM state groups
│   │   ├── utils/          # Notifications and shared formatting
│   │   └── bot.py          # Dispatcher setup and startup
│   ├── domain/             # Models, enums, exceptions, BookingService
│   └── infrastructure/     # Connection pool and repositories
├── config/                 # Typed settings from .env
├── locales/                # ru / en message dictionaries
├── migrations/             # Schema creation
├── tests/                  # Unit tests and fake repositories
├── docker-compose.yml
├── Dockerfile
├── main.py
├── requirements.txt
└── requirements-dev.txt
```

## Roadmap

- Editing and deactivating services and slots from the bot
- Per-master timezone support instead of bot-wide UTC
- Working-hours scheduling — generate availability from a daily schedule and a break
  interval, replacing manually created slots
- Multi-master support, letting clients pick a master first
- Appointment reminders ahead of the scheduled time
- Fetching appointment details in a single joined query to remove N+1 reads

## Feedback

Have ideas or found a bug? Open a GitHub Issue.

## License

MIT License — free to use, modify, and distribute. See [LICENSE](LICENSE).