#!/usr/bin/env bash
# Encrypted Postgres backup via docker compose + age (streamed; no plaintext dump).
#
# Required (from environment or repo-root .env):
#   POSTGRES_USER, POSTGRES_DB
#   BACKUP_AGE_RECIPIENT  — age public key (age1...)
# Optional:
#   BACKUP_DIR            — default: <repo>/backups
#   BACKUP_KEEP_DAYS      — if set, prune older *.dump.age after a successful dump
#   COMPOSE_FILE          — default: docker-compose.yml in repo root
#
# Auth: uses the official image local-socket trust inside the container
# (no PGPASSWORD on the host process list).
#
# Usage (from anywhere):
#   ./scripts/backup_postgres.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck source=_lib.sh
source "$ROOT/scripts/_lib.sh"

dotenv_fill "$ROOT/.env" \
  POSTGRES_USER POSTGRES_DB \
  BACKUP_AGE_RECIPIENT BACKUP_DIR BACKUP_KEEP_DAYS COMPOSE_FILE

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${BACKUP_AGE_RECIPIENT:?BACKUP_AGE_RECIPIENT is required (age public key)}"

BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"

if ! command -v age >/dev/null 2>&1; then
  echo "error: age not found in PATH (install https://github.com/FiloSottile/age)" >&2
  exit 1
fi

if ! postgres_running; then
  echo "error: postgres service is not running (docker compose up -d postgres)" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
encrypted="${BACKUP_DIR}/booking_bot_${stamp}.dump.age"
partial="${encrypted}.partial"

cleanup() {
  if [[ -n "${partial:-}" && -f "$partial" ]]; then
    rm -f "$partial"
  fi
}
trap cleanup EXIT

echo "dumping ${POSTGRES_DB} and encrypting → ${encrypted}"
compose_cmd exec -T postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
  | age -r "$BACKUP_AGE_RECIPIENT" -o "$partial"

mv -f "$partial" "$encrypted"
partial=""

bytes="$(wc -c <"$encrypted" | tr -d ' ')"
echo "ok: wrote ${encrypted} (${bytes} bytes)"

if [[ -n "${BACKUP_KEEP_DAYS:-}" ]]; then
  "$ROOT/scripts/prune_backups.sh"
fi
