# 📅 Booking Bot

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.20-green.svg)](https://docs.aiogram.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.4-red.svg)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docs.docker.com/compose/)
[![Tests](https://img.shields.io/badge/tests-pytest-orange.svg)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Telegram bot that runs appointment booking for a small service business — a barber,
a nail studio, a private tutor. Clients leave a short contact profile once, pick a
service, see only the times that actually fit it, and book in a few taps. The
master manages services, a weekly schedule and time off, sees the client's name and
phone on every card, and confirms or declines either from the **Bookings** screen or
straight from the new-booking notification. Both sides get notified on every status
change.

Navigation is a sticky inline hub opened by `/start` — there are no other slash
commands. Built on a layered architecture with the business logic isolated from
Telegram and SQL, and covered by unit tests.

## Tech Stack

| Technology                  | Purpose                                                           |
|-----------------------------|-------------------------------------------------------------------|
| **Python 3.13**             | Core language                                                     |
| **aiogram 3.20**            | Telegram Bot API framework                                        |
| **PostgreSQL 17**           | Persistent storage for users, services, schedule and appointments |
| **Redis 7.4**               | FSM state storage for multi-step dialogs                          |
| **psycopg 3**               | Async PostgreSQL driver with connection pooling                   |
| **Docker Compose**          | Runs the bot and all infrastructure services                      |
| **pytest / pytest-asyncio** | Unit tests for the domain layer                                   |
| **pgAdmin**                 | Visual database management                                        |
| **environs**                | Typed environment variable parsing                                |
| **aiohttp-socks**           | Optional HTTP/SOCKS5 proxy for the Telegram session               |

## Architecture

The project is split into three layers with a strict dependency direction —
outer layers know about inner ones, never the reverse.

```
app/
├── domain/           # Business logic. No aiogram, no SQL, no I/O.
│   ├── models/       # Immutable dataclasses: User, Service, Appointment
│   ├── enums/        # UserRole, AppointmentStatus
│   ├── exceptions.py # TimeConflict, WindowNotAvailable, ForbiddenBookingAction, ...
│   └── services/     # BookingService, AvailabilityService
│
├── infrastructure/   # Everything that talks to the outside world.
│   └── database/     # Connection pool and repositories (raw SQL only)
│
└── bot/              # Telegram presentation layer.
    ├── handlers/     # Hub leaves and callbacks, grouped by role
    ├── keyboards/    # Inline keyboards and typed CallbackData
    ├── middlewares/  # Transactions, user context, i18n, ban check
    ├── states/       # FSM state groups
    ├── utils/        # Notifications, sticky hub helpers, shared formatting
    ├── bot_commands.py  # Telegram ☰ menu (/start only)
    └── i18n/         # Locale resolution
```

**Why it matters in practice.** `BookingService` never imports aiogram or psycopg —
it depends only on repository objects passed into it. That is what makes the booking
rules testable without a database, a Redis instance or a Telegram token: the test
suite swaps in in-memory fakes and runs in well under a second.

Repositories hold **only** SQL. Handlers hold **only** dialog flow and formatting.
A rule like "only free windows from the master's schedule are offered" is written once, in
the domain, and applies no matter which handler triggers it.

Each update is wrapped in a single database transaction by `DataBaseMiddleware`, so a
failure halfway through a booking cannot leave a half-written appointment behind.

## Features

### For clients

- **Contact profile** — first name, last name and phone collected once before the
  first booking, via a share-contact button or manual input; editable later from
  **Profile**
- **Guided booking** — **Book**: service → day → time → confirmation
- **Only bookable times are shown** — windows outside working hours, blocked by
  time off, already taken, or in the past are filtered out before the client sees them
- **My bookings** — sticky list of upcoming appointments; open a card to cancel
- **Self-service cancellation** — cancel your own booking; the master is notified
- **Status notifications** — a message arrives when the master confirms or declines
  (dismiss with **OK**)

### For the master

- **Bookings** — sticky week view → day → appointment card (navigate weeks with ← / →)
- **Client name and phone on every card and notification** — not just a Telegram id,
  so the master can actually call the person
- **One-tap confirm / decline** — from a booking card or directly from the new-booking
  push; past slots are read-only (no action buttons), and a stale button is rejected
  server-side
- **Services** — catalogue with title, duration and price; add, edit and soft deactivate
- **Schedule → Working hours** — view / edit repeating weekly intervals
- **Schedule → Time off** — view / edit upcoming absences: full days / date ranges
  or hours in one day; past-only blocks are rejected because the list shows
  upcoming intervals only
- **Schedule → Break between appointments** — set `gap_minutes` (pause after each
  visit before the next bookable start; `0` = back-to-back)

### For admins

- **Moderation on the hub** — User card, Set role, Ban and Unban as root actions
  (no client booking or profile in the admin menu); flows ask for id/@ on the sticky
  hub message, then restore the menu and send a short result notice with **OK**
- **Shadowban** — banned users get no reply at all, so they cannot tell they were
  blocked and cannot probe the bot for a reaction
- **Guard rails** — an admin cannot ban themselves, demote themselves, or ban other staff

### Platform

- **Sticky hub** — `/start` opens (or reuses) one role-specific button menu; screens
  edit that message in place instead of flooding the chat
- **Bilingual interface** — Russian and English, switchable at runtime under
  **Settings → Language**
- **Language resolution chain** — explicit choice → Telegram client language → default
- **Profile gate** — **Book** asks for the contact profile first; everything else stays
  available without it
- **Inline Cancel** — multi-step flows (booking, profile, services, schedule, time off,
  gap, admin) abort with a button, not a slash command
- **Username sync** — a changed Telegram `@username` is picked up automatically, so
  admin lookups by username keep working
- **Concurrency safety** — a database exclusion constraint, not an application check,
  guarantees two clients can never book overlapping times for the same master
- **UTC everywhere** — all timestamps stored as `TIMESTAMPTZ`
- **Structured logging** with a configurable level and rotating Docker log files

## Navigation

The Telegram ☰ menu exposes only **`/start`** (restart / open the hub). Everything
else is inline buttons on the sticky hub message.

| Hub path                               | Role     | What it does                                              |
|----------------------------------------|----------|-----------------------------------------------------------|
| **Book**                               | client   | Book an appointment (asks for the profile first if empty) |
| **My bookings**                        | client   | Upcoming appointments (open / cancel)                     |
| **Profile → Show / Edit**              | client   | View or update name and phone                             |
| **Bookings**                           | master   | Week → day → card (confirm / cancel)                      |
| **Services**                           | master   | List, add, edit, deactivate services                      |
| **Schedule → Working hours**           | master   | View / edit weekly working intervals                      |
| **Schedule → Time off**                | master   | View / edit upcoming absences (full days or hours)        |
| **Schedule → Break between appointments** | master | Set pause after each visit (`gap_minutes`)             |
| **User card / Set role / Ban / Unban** | admin    | Moderation flows (id or `@username`)                      |
| **Settings → Language**                | everyone | Switch RU / EN                                            |
| **Settings → Help**                    | everyone | Short role-specific help                                  |
| **← Back** / **⌂ Menu**                | everyone | Hub navigation                                            |
| **OK**                                 | everyone | Dismiss a result / status notice                          |

## Roles

Three roles, all stored in the database — nothing is hardcoded in the source.

| Role      | Gets                                                                                  |
|-----------|---------------------------------------------------------------------------------------|
| `client`  | Contact profile, booking, and managing their own appointments. Default for new users. |
| `master`  | Service catalogue, weekly schedule, time off, and the weekly appointment list.        |
| `admin`   | User moderation only (lookup, roles, ban / unban) — no client booking features.       |

### First run: bootstrapping the master

A fresh database has no master, so nobody can create services yet. Set it up once:

1. Put your own Telegram id in `ADMIN_IDS` in `.env`.
2. Send `/start` — you are registered as an **admin** and see the moderation hub.
3. Ask the master to send `/start` too, then open **User card** and look them up by
   id or `@username`.
4. Open **Set role**, enter the same id/@, choose **master**.
5. Put that same id in `MASTER_USER_ID` in `.env` and restart the bot.

`MASTER_USER_ID` is the master whose services clients book via **Book**.
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

This starts PostgreSQL, Redis, pgAdmin and the bot. Pending schema migrations run
automatically on bot startup (`python -m migrations.migrate`).

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
python3 -m migrations.migrate
python3 main.py
```

Keep `POSTGRES_HOST=localhost` and `REDIS_HOST=localhost` in `.env` for this mode.

## Configuration

All settings come from `.env`. Start from `.env.example`.

| Variable                                                              | Description                                                                                     |
|-----------------------------------------------------------------------|-------------------------------------------------------------------------------------------------|
| `BOT_TOKEN`                                                           | Telegram bot token from [@BotFather](https://t.me/BotFather)                                    |
| `ADMIN_IDS`                                                           | Comma-separated Telegram ids granted the admin role on first `/start`                           |
| `MASTER_USER_ID`                                                      | Telegram id of the master whose services clients can book                                       |
| `TIMEZONE`                                                            | IANA timezone for display and local schedule input (default `Europe/Moscow`); storage stays UTC |
| `LOG_LEVEL`                                                           | `DEBUG` for development, `INFO` for production                                                  |
| `LOG_FORMAT`                                                          | Python logging format string                                                                    |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD`                 | Database credentials                                                                            |
| `POSTGRES_HOST` / `POSTGRES_PORT`                                     | `postgres` / `5432` inside Compose                                                              |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_DATABASE`                        | Redis connection for FSM storage                                                                |
| `REDIS_USERNAME` / `REDIS_PASSWORD`                                   | Redis credentials                                                                               |
| `PGADMIN_DEFAULT_EMAIL` / `PGADMIN_DEFAULT_PASSWORD` / `PGADMIN_PORT` | pgAdmin access                                                                                  |
| `PROXY_*`                                                             | Optional proxy, disabled by default — see below                                                 |

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

Core booking tables (plus `schema_migrations`, `master_settings`, `working_hours` and `time_off`).
Schema is applied by versioned SQL files in `migrations/versions/`, run via `python -m migrations.migrate`
on startup.

| Table             | Purpose                                                                                         |
|-------------------|-------------------------------------------------------------------------------------------------|
| `users`           | Telegram id, username, language, role, ban flag, contact profile (first name, last name, phone) |
| `services`        | Master's offerings: title, duration, price, active flag                                         |
| `appointments`    | Client, service, status, and concrete time range (`starts_at` / `ends_at`)                      |
| `master_settings` | Per-master timezone, grid step, gap, lead time and booking horizon                              |
| `working_hours`   | Weekly template: weekday (ISO 1=Mon…7=Sun) and local time ranges per master                     |
| `time_off`        | Absolute blocked intervals (day off, break, vacation) per master                                |

`appointments.status` is one of `pending`, `confirmed`, `cancelled`.

Appointments store `starts_at` / `ends_at`. Active appointments for the same master
cannot overlap in time: a GiST `EXCLUDE` on `tstzrange(starts_at, ends_at, '[)')`
enforces that.

Availability for **Book** is computed from `working_hours`, minus `time_off` and
existing appointments (`AvailabilityService`), using `master_settings` for step, gap,
lead time and horizon.

`master_settings.gap_minutes` defaults to `0` (back-to-back) and is editable under
**Schedule → Break between appointments**. `slot_step_minutes` is `NULL` until
customized and means “step equals the chosen service duration”.
Display/input timezone still comes from `.env` `TIMEZONE` until the bot reads this table.

`working_hours` stores repeating weekly intervals as local wall-clock `TIME` values;
the master's timezone (settings / `.env`) interprets them when computing availability.
Day-off and breaks are intentionally kept out of this table — they live in the separate `time_off` table.

`time_off` holds concrete `TIMESTAMPTZ` blocks that remove availability — full days
(midnight → next midnight) or same-day clock windows from the hub. Weekly open hours
stay in `working_hours`.

All timestamps are `TIMESTAMPTZ` and stored in UTC.

### Schema migrations

Schema changes live in `migrations/versions/*.sql` (ordered by filename:
`001_…`, `002_…`, …). On startup the bot runs `python -m migrations.migrate`,
which applies only versions not yet recorded in `schema_migrations`.

Existing databases created before versioned migrations are handled automatically:
if the `users` table already exists and `001_initial` is not in the journal, the
runner baselines it (marks applied without re-running `CREATE TABLE`).

## Tests

The domain layer is covered by unit tests that use in-memory fake repositories, so
no database, Redis or bot token is needed.

```bash
pip install -r requirements-dev.txt
pytest
```

```
.....................                                       [100%]
21 passed in 0.16s
```

The suite covers `BookingService` and `AvailabilityService`: window booking rules,
confirm and cancel transitions with permission checks, and client appointment listing filters.

## Project Structure

```
booking_bot/
├── app/
│   ├── bot/                # Telegram layer
│   │   ├── filters/        # Role and locale filters
│   │   ├── handlers/       # admin / client / master / common
│   │   ├── i18n/           # Locale resolution
│   │   ├── keyboards/      # Inline keyboards and typed CallbackData
│   │   ├── middlewares/    # DB transactions, user context, i18n, ban check
│   │   ├── states/         # FSM state groups
│   │   ├── utils/          # Notifications, hub helpers, shared formatting
│   │   ├── bot_commands.py # Telegram ☰ menu (/start only)
│   │   └── bot.py          # Dispatcher setup and startup
│   ├── domain/             # Models, enums, exceptions, BookingService, AvailabilityService
│   └── infrastructure/     # Connection pool and repositories
├── config/                 # Typed settings from .env
├── locales/                # ru / en message dictionaries
├── migrations/             # Versioned SQL migrations and runner
├── tests/                  # Unit tests and fake repositories
├── docker-compose.yml
├── Dockerfile
├── main.py
├── requirements.txt
└── requirements-dev.txt
```

## Roadmap

- Per-master timezone setting (currently: bot-wide `TIMEZONE` in `.env`)
- Slot grid step UI (`slot_step_minutes`; today defaults to service duration)
- Multi-master support, letting clients pick a master first
- Appointment reminders ahead of the scheduled time
- Per-language service titles set by the master
- Fetching appointment details in a single joined query to remove N+1 reads

## Feedback

Have ideas or found a bug? Open a GitHub Issue.

## License

MIT License — free to use, modify, and distribute. See [LICENSE](LICENSE).

Made with ❤️ by [DigitalJacob](https://github.com/DigitalJacob)
