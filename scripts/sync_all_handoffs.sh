#!/usr/bin/env bash
set -euo pipefail

# sync_all_handoffs.sh
# Local -> iCloud -> Cloud (sanitized docs/agent/CLOUD_HANDOFF.md)
#
# Fail-closed + secret-safe:
# - Never prints file contents.
# - Never auto-commits or auto-pushes.
# - Fails immediately if external sync or sanitization fails.
#
# Environment overrides (intended for local dev + tests):
# - SYNC_ONEPILOT_REPO_ROOT: override repository root (default: repo/.. relative to this script)
# - SYNC_ONEPILOT_LOCAL_HANDOFF_PATH: override local HANDOFF.md path (default: "$REPO_ROOT/HANDOFF.md")
# - SYNC_ONEPILOT_ICLOUD_HANDOFF_PATH: override iCloud HANDOFF.md path
# - SYNC_ONEPILOT_HANDOFF_SH: path to external script that performs Local -> iCloud sync
# - SYNC_ONEPILOT_HANDOFF_CMD: command string to run for Local -> iCloud sync (alternative to _SH)
# - SYNC_CLOUD_HANDOFF_PYTHON_SCRIPT: override sanitizer script path (default: "$REPO_ROOT/scripts/sync_cloud_handoff.py")
# - SYNC_CLOUD_HANDOFF_OUTPUT_PATH: override CLOUD_HANDOFF output path
# - SYNC_CLOUD_HANDOFF_FETCH: "true" (default) or "false" (adds --no-fetch)

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${SYNC_ONEPILOT_REPO_ROOT:-"$(cd -- "$SCRIPT_DIR/.." && pwd)"}"

LOCAL_HANDOFF_PATH="${SYNC_ONEPILOT_LOCAL_HANDOFF_PATH:-"$REPO_ROOT/HANDOFF.md"}"
ICLOUD_HANDOFF_PATH="${SYNC_ONEPILOT_ICLOUD_HANDOFF_PATH:-"$HOME/Library/Mobile Documents/com~apple~CloudDocs/AI-Projects/OnePilot AI/HANDOFF.md"}"
OUTPUT_PATH="${SYNC_CLOUD_HANDOFF_OUTPUT_PATH:-"$REPO_ROOT/docs/agent/CLOUD_HANDOFF.md"}"

SYNC_SH_DEFAULT="$HOME/.local/bin/sync-onepilot-handoff.sh"
SYNC_SH="${SYNC_ONEPILOT_HANDOFF_SH:-""}"
SYNC_CMD="${SYNC_ONEPILOT_HANDOFF_CMD:-""}"

SANITIZER_SCRIPT="${SYNC_CLOUD_HANDOFF_PYTHON_SCRIPT:-"$REPO_ROOT/scripts/sync_cloud_handoff.py"}"
FETCH="${SYNC_CLOUD_HANDOFF_FETCH:-"true"}"

run_fail() {
  echo "error: $*" >&2
  exit 1
}

is_nonempty_markdown_like() {
  local path="$1"
  [[ -s "$path" ]] || return 1

  # Basic structure check without dumping contents:
  # - at least 3 lines
  # - at least one markdown heading OR at least one bullet OR an OP task id
  local line_count
  line_count="$(wc -l < "$path" | tr -d ' ')"
  [[ "$line_count" -ge 3 ]] || return 1

  # If contents include "OP-xxx" task IDs or markdown headings/bullets, treat as valid.
  # (We avoid printing content; grep is quiet.)
  if grep -E -q '(^#|^##|- |^\*+ )|(^OP-[0-9]{3})' "$path"; then
    return 0
  fi
  return 1
}

mtime_epoch_seconds() {
  # GNU stat: %Y = mtime as epoch seconds.
  stat -c %Y "$1" 2>/dev/null || true
}

echo "sync: Local -> iCloud (external handoff sync)"

if [[ -n "$SYNC_CMD" && -n "$SYNC_SH" ]]; then
  run_fail "set only one of SYNC_ONEPILOT_HANDOFF_CMD or SYNC_ONEPILOT_HANDOFF_SH"
fi

before_local_mtime="$(mtime_epoch_seconds "$LOCAL_HANDOFF_PATH")"
before_icloud_mtime="$(mtime_epoch_seconds "$ICLOUD_HANDOFF_PATH")"

if [[ -n "$SYNC_CMD" ]]; then
  # shellcheck disable=SC2086
  bash -lc "$SYNC_CMD"
elif [[ -n "$SYNC_SH" ]]; then
  [[ -x "$SYNC_SH" ]] || run_fail "external sync script not found or not executable: $SYNC_SH"
  "$SYNC_SH"
else
  [[ -x "$SYNC_SH_DEFAULT" ]] || run_fail "external sync script not found or not executable: $SYNC_SH_DEFAULT (set SYNC_ONEPILOT_HANDOFF_SH)"
  "$SYNC_SH_DEFAULT"
fi

echo "sync: verifying HANDOFF files"

[[ -f "$LOCAL_HANDOFF_PATH" ]] || run_fail "missing local HANDOFF after external sync: $LOCAL_HANDOFF_PATH"
[[ -s "$LOCAL_HANDOFF_PATH" ]] || run_fail "empty local HANDOFF after external sync: $LOCAL_HANDOFF_PATH"

[[ -f "$ICLOUD_HANDOFF_PATH" ]] || run_fail "missing iCloud HANDOFF after external sync: $ICLOUD_HANDOFF_PATH"
[[ -s "$ICLOUD_HANDOFF_PATH" ]] || run_fail "empty iCloud HANDOFF after external sync: $ICLOUD_HANDOFF_PATH"

if [[ -n "$before_icloud_mtime" ]]; then
  after_icloud_mtime="$(mtime_epoch_seconds "$ICLOUD_HANDOFF_PATH")"
  if [[ "$after_icloud_mtime" -le "$before_icloud_mtime" ]]; then
    run_fail "iCloud HANDOFF did not update mtime (expected newer): $ICLOUD_HANDOFF_PATH"
  fi
fi

# "Matches expected non-empty structure" requirement.
is_nonempty_markdown_like "$ICLOUD_HANDOFF_PATH" || run_fail "iCloud HANDOFF did not match expected non-empty structure: $ICLOUD_HANDOFF_PATH"

echo "sync: Local -> Cloud (sanitizer)"

[[ -f "$SANITIZER_SCRIPT" ]] || run_fail "sanitizer script not found: $SANITIZER_SCRIPT"

PY_ARGS=(
  --repo-root "$REPO_ROOT"
  --handoff "$LOCAL_HANDOFF_PATH"
  --output "$OUTPUT_PATH"
)

if [[ "${FETCH,,}" == "false" ]]; then
  PY_ARGS+=(--no-fetch)
fi

python3 "$SANITIZER_SCRIPT" "${PY_ARGS[@]}"

[[ -f "$OUTPUT_PATH" ]] || run_fail "sanitizer completed but output missing: $OUTPUT_PATH"
[[ -s "$OUTPUT_PATH" ]] || run_fail "sanitizer completed but output is empty: $OUTPUT_PATH"

echo "sync: ready for review: $OUTPUT_PATH"

