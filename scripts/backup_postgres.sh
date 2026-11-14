#!/usr/bin/env bash
# Encrypted Postgres backup via docker compose + age.
#
# Required (from environment or repo-root .env):
#   POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
#   BACKUP_AGE_RECIPIENT  — age public key (age1...)
# Optional:
#   BACKUP_DIR            — default: <repo>/backups
#   BACKUP_KEEP_DAYS      — if set, prune older *.dump.age after a successful dump
#   COMPOSE_FILE          — default: docker-compose.yml in repo root
#
# Usage (from anywhere):
#   ./scripts/backup_postgres.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${BACKUP_AGE_RECIPIENT:?BACKUP_AGE_RECIPIENT is required (age public key)}"

BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"
COMPOSE=(docker compose)
if [[ -n "${COMPOSE_FILE:-}" ]]; then
  COMPOSE=(docker compose -f "$COMPOSE_FILE")
fi

if ! command -v age >/dev/null 2>&1; then
  echo "error: age not found in PATH (install https://github.com/FiloSottile/age)" >&2
  exit 1
fi

if ! "${COMPOSE[@]}" ps --status running --services 2>/dev/null | grep -qx postgres; then
  echo "error: postgres service is not running (docker compose up -d postgres)" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"
plain="$(mktemp "${TMPDIR:-/tmp}/booking_bot_${stamp}.XXXXXX.dump")"
encrypted="${BACKUP_DIR}/booking_bot_${stamp}.dump.age"

cleanup() {
  if [[ -n "${plain:-}" && -f "$plain" ]]; then
    rm -f "$plain"
  fi
}
trap cleanup EXIT

echo "dumping ${POSTGRES_DB} via compose service postgres..."
"${COMPOSE[@]}" exec -T \
  -e "PGPASSWORD=${POSTGRES_PASSWORD}" \
  postgres \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc \
  >"$plain"

echo "encrypting with age → ${encrypted}"
age -r "$BACKUP_AGE_RECIPIENT" -o "$encrypted" "$plain"
rm -f "$plain"
plain=""

bytes="$(wc -c <"$encrypted" | tr -d ' ')"
echo "ok: wrote ${encrypted} (${bytes} bytes)"

if [[ -n "${BACKUP_KEEP_DAYS:-}" ]]; then
  "$ROOT/scripts/prune_backups.sh"
fi
