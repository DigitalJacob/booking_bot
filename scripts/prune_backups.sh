#!/usr/bin/env bash
# Delete age-encrypted Postgres dumps older than BACKUP_KEEP_DAYS.
#
# Required:
#   BACKUP_KEEP_DAYS  — positive integer (days to keep)
# Optional:
#   BACKUP_DIR        — default: <repo>/backups
#
# Usage:
#   BACKUP_KEEP_DAYS=14 ./scripts/prune_backups.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
# shellcheck source=_lib.sh
source "$ROOT/scripts/_lib.sh"

dotenv_fill "$ROOT/.env" BACKUP_KEEP_DAYS BACKUP_DIR

: "${BACKUP_KEEP_DAYS:?BACKUP_KEEP_DAYS is required (positive integer)}"

if [[ ! "$BACKUP_KEEP_DAYS" =~ ^[1-9][0-9]*$ ]]; then
  echo "error: BACKUP_KEEP_DAYS must be a positive integer, got '${BACKUP_KEEP_DAYS}'" >&2
  exit 1
fi

BACKUP_DIR="${BACKUP_DIR:-$ROOT/backups}"

if [[ ! -d "$BACKUP_DIR" ]]; then
  echo "ok: nothing to prune (${BACKUP_DIR} missing)"
  exit 0
fi

# -mtime +N: last modified more than N*24h ago
count=0
while IFS= read -r f; do
  [[ -z "$f" ]] && continue
  echo "  rm ${f}"
  rm -f "$f"
  count=$((count + 1))
done < <(
  find "$BACKUP_DIR" -maxdepth 1 -type f -name '*.dump.age' -mtime "+${BACKUP_KEEP_DAYS}" | sort
)

if [[ "$count" -eq 0 ]]; then
  echo "ok: no dumps older than ${BACKUP_KEEP_DAYS} day(s) in ${BACKUP_DIR}"
  exit 0
fi

echo "ok: pruned ${count} dump(s) older than ${BACKUP_KEEP_DAYS} day(s)"
