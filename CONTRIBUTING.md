# Contributing

Thanks for taking an interest in **booking_bot**. Small, focused changes are welcome.

## Development setup

- **Python** `>=3.13` (see `pyproject.toml`)
- **Docker** + **Docker Compose** for Postgres / Redis (see [README → Quick Start](README.md#quick-start))

```bash
cp .env.example .env   # fill BOT_TOKEN, passwords, etc.
docker compose up -d --build
```

For host-run bot + container DBs, follow [Running locally without Docker](README.md#running-locally-without-docker).

Dev tools:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
```

## Checks before you open a PR

From the repo root (with the venv active if you use one):

```bash
ruff check .
mypy .
pytest
```

Optional Postgres integration tests (never against a production database):

```bash
export BOOKING_BOT_INTEGRATION=1
# point POSTGRES_* at an empty test DB — see README → Tests
pytest -m integration
```

CI runs the same suite on pushes and pull requests to `main`.

## Pull requests

1. Branch from the latest `main`.
2. Keep the PR focused (one concern; prefer several small PRs over a kitchen sink).
3. Match existing layout: domain / ports / SQL; handlers stay thin.
4. If you change user-facing copy, update **both** `locales/ru` and `locales/en`.
5. Use the PR template (Summary + Test plan). Do not commit secrets or dumps.

## What not to commit

- `.env`, credentials, Telegram tokens
- Plaintext or age-encrypted database dumps (`backups/`, `*.dump`, `*.dump.age`)
- Age identity private keys

See [SECURITY.md](SECURITY.md) for how to report vulnerabilities (not via public issues).

## Questions

Bug reports and feature ideas: open a GitHub Issue. Security: use GitHub Security Advisories as described in [SECURITY.md](SECURITY.md).
