#!/usr/bin/env bash
# Decrypt an age-encrypted Postgres dump and restore into a non-prod database.
#
# Required (from environment or repo-root .env):
#   POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
#   BACKUP_AGE_IDENTITY   — path to age private key (never commit)
#   CONFIRM_RESTORE=1     — explicit acknowledgement
# Optional:
#   RESTORE_TARGET_DB     — default: ${POSTGRES_DB}_restore
#   ALLOW_RESTORE_TO_PRIMARY=1 — required if RESTORE_TARGET_DB == POSTGRES_DB
#   COMPOSE_FILE          — default: docker-compose.yml in repo root
#
# Usage:
#   CONFIRM_RESTORE=1 ./scripts/restore_postgres.sh backups/booking_bot_….dump.age
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

usage() {
  echo "usage: CONFIRM_RESTORE=1 $0 <path-to.dump.age>" >&2
  exit 2
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage
[[ $# -eq 1 ]] || usage

encrypted="$1"
if [[ ! -f "$encrypted" ]]; then
  echo "error: file not found: ${encrypted}" >&2
  exit 1
fi

: "${POSTGRES_USER:?POSTGRES_USER is required}"
: "${POSTGRES_PASSWORD:?POSTGRES_PASSWORD is required}"
: "${POSTGRES_DB:?POSTGRES_DB is required}"
: "${BACKUP_AGE_IDENTITY:?BACKUP_AGE_IDENTITY is required (path to age private key)}"

if [[ "${CONFIRM_RESTORE:-}" != "1" ]]; then
  echo "error: set CONFIRM_RESTORE=1 to acknowledge a restore" >&2
  exit 1
fi

if [[ ! -f "$BACKUP_AGE_IDENTITY" ]]; then
  echo "error: age identity not found: ${BACKUP_AGE_IDENTITY}" >&2
  exit 1
fi

RESTORE_TARGET_DB="${RESTORE_TARGET_DB:-${POSTGRES_DB}_restore}"

if [[ "$RESTORE_TARGET_DB" == "$POSTGRES_DB" && "${ALLOW_RESTORE_TO_PRIMARY:-}" != "1" ]]; then
  echo "error: refusing to restore into primary DB '${POSTGRES_DB}'" >&2
  echo "hint: default target is '${POSTGRES_DB}_restore', or set ALLOW_RESTORE_TO_PRIMARY=1" >&2
  exit 1
fi

if [[ ! "$RESTORE_TARGET_DB" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
  echo "error: unsafe RESTORE_TARGET_DB '${RESTORE_TARGET_DB}' (use [a-zA-Z0-9_]+)" >&2
  exit 1
fi

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

psql_exec() {
  "${COMPOSE[@]}" exec -T \
    -e "PGPASSWORD=${POSTGRES_PASSWORD}" \
    postgres \
    psql -U "$POSTGRES_USER" -d postgres -v ON_ERROR_STOP=1 "$@"
}

plain="$(mktemp "${TMPDIR:-/tmp}/booking_bot_restore.XXXXXX.dump")"
cleanup() {
  if [[ -n "${plain:-}" && -f "$plain" ]]; then
    rm -f "$plain"
  fi
}
trap cleanup EXIT

echo "decrypting ${encrypted}..."
age -d -i "$BACKUP_AGE_IDENTITY" -o "$plain" "$encrypted"

exists="$(
  psql_exec -tAc "SELECT 1 FROM pg_database WHERE datname='${RESTORE_TARGET_DB}'" \
    | tr -d '[:space:]'
)"
if [[ "$exists" != "1" ]]; then
  echo "creating database ${RESTORE_TARGET_DB}..."
  psql_exec -c "CREATE DATABASE ${RESTORE_TARGET_DB}"
fi

echo "restoring into ${RESTORE_TARGET_DB} (pg_restore --clean --if-exists)..."
"${COMPOSE[@]}" exec -T \
  -e "PGPASSWORD=${POSTGRES_PASSWORD}" \
  postgres \
  pg_restore -U "$POSTGRES_USER" -d "$RESTORE_TARGET_DB" --clean --if-exists \
  <"$plain"

rm -f "$plain"
plain=""

echo "ok: restored ${encrypted} → database ${RESTORE_TARGET_DB}"
