#!/usr/bin/env bash
# Shared helpers for backup / restore / prune. Sourced, not executed.
#
# dotenv_fill FILE KEY [KEY...]
#   Load selected KEY=VALUE lines from a dotenv file without `source`.
#   Already-set environment variables win (CLI / systemd overrides).
#   Supports optional surrounding single/double quotes; strips an unquoted
#   trailing " # comment". Does not expand shell variables or run commands.

dotenv_fill() {
  local file="$1"
  shift
  [[ -f "$file" ]] || return 0
  [[ $# -ge 1 ]] || return 0

  local want_re=""
  local k
  for k in "$@"; do
    want_re+="${want_re:+|}${k}"
  done

  local line key val
  while IFS= read -r line || [[ -n "$line" ]]; do
    line="${line%$'\r'}"
    [[ "$line" =~ ^[[:space:]]*# ]] && continue
    [[ "$line" =~ ^[[:space:]]*$ ]] && continue
    [[ "$line" =~ ^([A-Za-z_][A-Za-z0-9_]*)=(.*)$ ]] || continue
    key="${BASH_REMATCH[1]}"
    val="${BASH_REMATCH[2]}"
    [[ "$key" =~ ^(${want_re})$ ]] || continue

    # Skip if already set in this environment (including empty).
    if [[ -n "${!key+x}" ]]; then
      continue
    fi

    if [[ "$val" =~ ^\"(.*)\"[[:space:]]*$ ]]; then
      val="${BASH_REMATCH[1]}"
    elif [[ "$val" =~ ^\'(.*)\'[[:space:]]*$ ]]; then
      val="${BASH_REMATCH[1]}"
    else
      if [[ "$val" == *" #"* ]]; then
        val="${val%% #*}"
      fi
      val="${val%"${val##*[![:space:]]}"}"
    fi

    printf -v "$key" '%s' "$val"
    export "$key"
  done <"$file"
}

compose_cmd() {
  if [[ -n "${COMPOSE_FILE:-}" ]]; then
    docker compose -f "$COMPOSE_FILE" "$@"
  else
    docker compose "$@"
  fi
}

postgres_running() {
  compose_cmd ps --status running --services 2>/dev/null | grep -qx postgres
}
