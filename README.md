# 📅 Booking Bot

[![Python](https://img.shields.io/badge/Python-3.13-blue.svg)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.20-green.svg)](https://docs.aiogram.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-17-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7.4-red.svg)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-blue.svg)](https://docs.docker.com/compose/)
[![Tests](https://img.shields.io/badge/tests-pytest-orange.svg)](https://docs.pytest.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A Telegram bot that runs appointment booking for a small service business — a barber,
a nail studio, a private tutor. Clients agree to personal-data processing, leave a
short contact profile once, pick a service, see only the times that actually fit it,
and book in a few taps. The master manages services, schedule (weekly hours or
monthly open days, chosen at deploy) and time off, sees the client's name and phone
on every card, and confirms or declines either from the **Bookings** screen or
straight from the new-booking notification. Both sides get notified on every status
change, plus evening-before and hour-ahead reminders for confirmed appointments.

Navigation is a sticky inline hub: `/start` refreshes it in place, `/menu` posts a
fresh hub message (useful after clearing the chat). Built on a layered architecture
with the business logic isolated from Telegram and SQL, and covered by unit tests.

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
    ├── bot_commands.py  # Telegram ☰ menu (/start, /menu)
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

- **Contact profile** — before the first booking (or when consent is missing /
  outdated), the client sees a short personal-data notice (operator name and
  contacts from `.env`), then first name, last name and phone via a share-contact
  button or manual input; after that **Book** continues to services. Editable later
  from **Profile** (consent is asked again only if the stored version no longer
  matches `PDN_CONSENT_VERSION`)
- **Guided booking** — **Book**: service → month (only months with open days and
  free slots) → day on a month calendar (only bookable days are tappable) → time →
  confirmation
- **Services catalog** — browse active services with description and photo (separate
  from booking; card opens as a new message)
- **Only bookable times are shown** — windows outside the master's open schedule
  (weekly hours or monthly open days), blocked by time off, already taken, or in
  the past are filtered out before the client sees them; month and day pickers
  respect the same filters within `booking_horizon_days`
- **My bookings** — sticky list of upcoming appointments; open a card to cancel
- **Self-service cancellation** — cancel your own booking; the master is notified
- **Status notifications** — a message arrives when the master confirms or declines
  (dismiss with **OK**)
- **Appointment reminders** — for each **confirmed** visit, an evening-before push
  (local window from `.env`) and an hour-ahead push; **OK** dismisses, **Cancel
  appointment** asks for confirm then an optional short reason (or skip)

### For the master

- **Bookings** — sticky week view → day → appointment card (navigate weeks with ← / →)
- **Client name and phone on every card and notification** — not just a Telegram id,
  so the master can actually call the person
- **One-tap confirm / decline** — from a booking card or directly from the new-booking
  push; past slots are read-only (no action buttons), and a stale button is rejected
  server-side
- **Appointment reminders** — same evening-before and hour-ahead pushes as the client
  (with the client's name and phone); cancel from the reminder notifies the client,
  optionally with a reason
- **Services** — catalogue with title, duration, price, description and photo; add,
  edit (including description/photo from the card) and soft deactivate
- **Schedule → Working hours** *(when `SCHEDULE_MODE=weekly`)* — view / edit
  repeating weekly intervals
- **Schedule → Work days** *(when `SCHEDULE_MODE=monthly`)* — choose a month from
  the next 12 (compact labels in two columns, e.g. `сен 26`), pick open days on a
  month calendar, set hours for newly selected days (other days keep their hours),
  close days with an optional warn if bookings exist; **Show current schedule**
  lists saved days and hours
- **Schedule → Time off** — view / edit upcoming absences: full days / date ranges
  or hours in one day; past-only blocks are rejected because the list shows
  upcoming intervals only
  (in monthly mode, a full closed day is usually an untoggled work day; use
  time off for a partial-day block inside an open day)
- **Schedule → Break between appointments** — set `gap_minutes` (pause after each
  visit before the next bookable start; `0` = back-to-back)
- **Schedule → Minimum lead time** — set `min_lead_minutes` (clients cannot book a
  start sooner than this many minutes from now; `0` = allow immediately)
- **Schedule → Slot grid step** — set `slot_step_minutes` (spacing between offered
  start times; default / reset = step equals the chosen service duration)

### For admins

- **Moderation on the hub** — User card, Set role, Ban and Unban as root actions
  (no client booking or profile in the admin menu); flows ask for id/@ on the sticky
  hub message, then restore the menu and send a short result notice with **OK**
- **Shadowban** — banned users get no reply at all, so they cannot tell they were
  blocked and cannot probe the bot for a reaction
- **Guard rails** — an admin cannot ban themselves, demote themselves, or ban other staff

### Platform

- **Sticky hub** — `/start` opens or reuses one role-specific button menu; `/menu`
  always sends a new hub message and points sticky navigation at it; screens edit
  that message in place instead of flooding the chat
- **Bilingual interface** — Russian and English, switchable at runtime under
  **Settings → Language**
- **Language resolution chain** — explicit choice → Telegram client language → default
- **Profile gate** — **Book** requires personal-data consent (current version) and a
  complete contact profile first, then resumes the booking flow on the sticky hub;
  everything else stays available without them
- **Inline Cancel** — multi-step flows (booking, profile, services, schedule, time off,
  gap, min lead, slot step, admin) abort with a button, not a slash command
- **Username sync** — a changed Telegram `@username` is picked up automatically, so
  admin lookups by username keep working
- **Concurrency safety** — a database exclusion constraint, not an application check,
  guarantees two clients can never book overlapping times for the same master
- **UTC everywhere** — all timestamps stored as `TIMESTAMPTZ`
- **Background reminder worker** — an asyncio task started with the bot polls due
  confirmed appointments and sends each reminder once (tracked per kind on the row)
- **Structured logging** with a configurable level and rotating Docker log files

## Navigation

The Telegram ☰ menu exposes **`/start`** (start / refresh the sticky hub) and
**`/menu`** (new hub message — e.g. after the chat was cleared). Everything else
is inline buttons on the sticky hub message.

| Hub path                                   | Role     | What it does                                                             |
|--------------------------------------------|----------|--------------------------------------------------------------------------|
| **Book**                                   | client   | Consent (if needed) → profile (if needed) → service → month → day → time |
| **Services**                               | client   | Browse active services (description / photo)                             |
| **My bookings**                            | client   | Upcoming appointments (open / cancel)                                    |
| **Profile → Show / Edit**                  | client   | View or update name and phone (consent first if missing / outdated)      |
| **Bookings**                               | master   | Week → day → card (confirm / cancel)                                     |
| **Services**                               | master   | List, add, edit, description/photo, deactivate                           |
| **Schedule → Working hours**               | master   | Weekly mode: view / edit repeating intervals                             |
| **Schedule → Work days**                   | master   | Monthly mode: 12 months ahead → calendar days, hours, summary            |
| **Schedule → Time off**                    | master   | View / edit upcoming absences (full days or hours)                       |
| **Schedule → Break between appointments**  | master   | Set pause after each visit (`gap_minutes`)                               |
| **Schedule → Minimum lead time**           | master   | Set how soon clients may book (`min_lead_minutes`)                       |
| **Schedule → Slot grid step**              | master   | Set start-time grid (`slot_step_minutes`; NULL = duration)               |
| **User card / Set role / Ban / Unban**     | admin    | Moderation flows (id or `@username`)                                     |
| **Settings → Language**                    | everyone | Switch RU / EN                                                           |
| **Settings → Help**                        | everyone | Short role-specific help                                                 |
| **← Back** / **⌂ Menu**                    | everyone | Hub navigation                                                           |
| **OK**                                     | everyone | Dismiss a result / status notice                                         |

## Roles

Three roles, all stored in the database — nothing is hardcoded in the source.

| Role      | Gets                                                                                                       |
|-----------|------------------------------------------------------------------------------------------------------------|
| `client`  | Consent + contact profile, booking, and managing their own appointments. Default for new users.            |
| `master`  | Service catalogue, schedule (weekly or monthly by deploy mode), time off, and the weekly appointment list. |
| `admin`   | User moderation only (lookup, roles, ban / unban) — no client booking features.                            |

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

| Variable                                                              | Description                                                                                        |
|-----------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| `BOT_TOKEN`                                                           | Telegram bot token from [@BotFather](https://t.me/BotFather)                                       |
| `ADMIN_IDS`                                                           | Comma-separated Telegram ids granted the admin role on first `/start`                              |
| `MASTER_USER_ID`                                                      | Telegram id of the master whose services clients can book                                          |
| `TIMEZONE`                                                            | IANA timezone for display and local schedule input (default `Europe/Moscow`); storage stays UTC    |
| `SCHEDULE_MODE`                                                       | `weekly` or `monthly` — schedule shape for this deploy (pick once; switching is not supported)     |
| `PDN_CONSENT_VERSION`                                                 | Version label stored with consent (default `v1`); bump to re-ask all clients                       |
| `PDN_OPERATOR_NAME`                                                   | Operator name shown on the short consent screen (empty → locale fallback)                          |
| `PDN_OPERATOR_CONTACTS`                                               | Operator contacts on the consent screen (empty → locale fallback)                                  |
| `PDN_POLICY_URL`                                                      | Optional `http(s)://…` link for **Full terms** (hidden when empty)                                 |
| `REMINDER_LEAD_MINUTES`                                               | Hour-ahead reminder: send when `starts_at` is within this many minutes (default `60`)              |
| `REMINDER_EVENING_HOUR_START` / `REMINDER_EVENING_HOUR_END`           | Evening reminder: half-open local hour window `[START, END)` on the day before (default `20`/`22`) |
| `LOG_LEVEL`                                                           | `DEBUG` for development, `INFO` for production                                                     |
| `LOG_FORMAT`                                                          | Python logging format string                                                                       |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD`                 | Database credentials                                                                               |
| `POSTGRES_HOST` / `POSTGRES_PORT`                                     | `postgres` / `5432` inside Compose                                                                 |
| `REDIS_HOST` / `REDIS_PORT` / `REDIS_DATABASE`                        | Redis connection for FSM storage                                                                   |
| `REDIS_USERNAME` / `REDIS_PASSWORD`                                   | Redis credentials                                                                                  |
| `PGADMIN_DEFAULT_EMAIL` / `PGADMIN_DEFAULT_PASSWORD` / `PGADMIN_PORT` | pgAdmin access                                                                                     |
| `PROXY_*`                                                             | Optional proxy, disabled by default — see below                                                    |

Personal-data notice text lives in locales; operator fields and the optional full-policy
URL come from the `PDN_*` variables above. Decline / Cancel do not store consent, so the
screen appears again on the next **Book** or **Profile** edit until the client agrees.
Bump `PDN_CONSENT_VERSION` (and restart) when the policy changes and you need everyone
to re-accept.

Reminder times use bot `TIMEZONE`. Evening reminders fire only on the calendar day
before a **confirmed** appointment while the local clock is in
`[REMINDER_EVENING_HOUR_START, REMINDER_EVENING_HOUR_END)`. Hour reminders fire once
`now` is inside `REMINDER_LEAD_MINUTES` before `starts_at` (and not after the start).
Each of the four kinds (client/master × evening/hour) is sent at most once.

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

Core booking tables (plus `schema_migrations`, `master_settings`, `working_hours`,
`work_dates` and `time_off`).
Schema is applied by versioned SQL files in `migrations/versions/`, run via `python -m migrations.migrate`
on startup.

| Table              | Purpose                                                                                                                 |
|--------------------|-------------------------------------------------------------------------------------------------------------------------|
| `users`            | Telegram id, username, language, role, ban flag, contact profile, PDN consent (`pdn_consent_at`, `pdn_consent_version`) |
| `services`         | Master's offerings: title, duration, price, description, photo file id, active flag                                     |
| `appointments`     | Client, service, status, time range (`starts_at` / `ends_at`), reminder sent-at columns                                 |
| `master_settings`  | Per-master timezone, grid step, gap, lead time and booking horizon                                                      |
| `working_hours`    | Weekly mode: weekday (ISO 1=Mon…7=Sun) and local time ranges per master                                                 |
| `work_dates`       | Monthly mode: concrete open dates with local `starts_time` / `ends_time` (unique per master+day)                        |
| `time_off`         | Absolute blocked intervals (day off, break, vacation) per master                                                        |

`users.pdn_consent_at` / `pdn_consent_version` are written when the client taps **Agree**
on the short notice (`migration 012`). They must match the current `PDN_CONSENT_VERSION`
for **Book** and profile edit to skip the consent step.

`services.description` (optional, up to 1000 characters) and `photo_file_id` (Telegram
photo file id) are set from the master's service card and shown in the client
**Services** catalog. Booking still uses title / duration / price only.

`appointments.status` is one of `pending`, `confirmed`, `cancelled`.

Appointments store `starts_at` / `ends_at`. Active appointments for the same master
cannot overlap in time: a GiST `EXCLUDE` on `tstzrange(starts_at, ends_at, '[)')`
enforces that.

Reminder delivery marks
`client_evening_reminded_at` / `client_hour_reminded_at` /
`master_evening_reminded_at` / `master_hour_reminded_at` when the matching push is
sent (`migration 013`). Only **confirmed** rows are eligible; a NULL column means
that kind has not been sent yet.

Availability for **Book** is computed from the schedule for this deploy
(`SCHEDULE_MODE`): **`weekly`** uses `working_hours` by weekday; **`monthly`** uses
`work_dates` for concrete open days. In both modes, `time_off` and existing
appointments are subtracted (`AvailabilityService`), using `master_settings` for
step, gap, lead time and horizon. The client month list comes from
`AvailabilityService.list_open_months` (open schedule months inside the horizon
that still have free slots for the chosen service). Switching mode does not migrate
data — after a change you must restart and fill the matching schedule tables.

`master_settings.gap_minutes` defaults to `0` (back-to-back) and is editable under
**Schedule → Break between appointments**. `min_lead_minutes` defaults to `0` and is
editable under **Schedule → Minimum lead time**. `booking_horizon_days` defaults to
`180` (how far ahead **Book** offers months and slots; not editable from the hub yet).
`slot_step_minutes` is `NULL` until customized (editable under **Schedule → Slot grid
step**, with a reset to “use service duration”) and means “step equals the chosen
service duration” (when a candidate overlaps a busy block including gap, availability
jumps to that block’s end so the next start can land on `ends_at + gap` even with a
coarser step).
Display/input timezone still comes from `.env` `TIMEZONE` until the bot reads this table.

`working_hours` stores repeating weekly intervals as local wall-clock `TIME` values;
the master's timezone (settings / `.env`) interprets them when computing availability.
Used when `SCHEDULE_MODE=weekly`.

`work_dates` stores concrete open calendar days with one local interval per day
(`UNIQUE (master_user_id, work_date)`). Used when `SCHEDULE_MODE=monthly`. The hub
month picker offers the next 12 months from today. Saving hours upserts only the
newly selected days; closing days deletes those rows (with a confirm if
pending/confirmed appointments fall on them — bookings are kept).

Day-off and breaks are intentionally kept out of the weekly template — they live in
the separate `time_off` table. In monthly mode, closing a full day is an untoggled
work day; use `time_off` for a partial-day block inside an open day.

`time_off` holds concrete `TIMESTAMPTZ` blocks that remove availability — full days
(midnight → next midnight) or same-day clock windows from the hub.
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
...........................................                              [100%]
43 passed in 0.10s
```

The suite covers `BookingService`, `AvailabilityService` and reminder due-rules:
window booking (including monthly open days and open-month listing), confirm and
cancel transitions with permission checks, client appointment listing filters, and
evening / hour reminder eligibility (confirmed only, lead window, half-open evening
hours, already-sent skip).

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
│   │   ├── reminders.py    # Background appointment-reminder worker
│   │   ├── bot_commands.py # Telegram ☰ menu (/start, /menu)
│   │   └── bot.py          # Dispatcher setup and startup
│   ├── domain/             # Models, enums, exceptions, booking / availability / reminders
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
- Multi-master support, letting clients pick a master first
- Per-language service titles set by the master
- Fetching appointment details in a single joined query to remove N+1 reads

## Feedback

Have ideas or found a bug? Open a GitHub Issue.

## License

MIT License — free to use, modify, and distribute. See [LICENSE](LICENSE).

Made with ❤️ by [DigitalJacob](https://github.com/DigitalJacob)
