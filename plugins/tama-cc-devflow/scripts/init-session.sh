#!/usr/bin/env bash
# Create a new devflow session directory (the shared whiteboard) and point `current` at it.
# Usage: init-session.sh --slug <slug> --claude-session <id>
# Prints the absolute session directory on stdout.
set -euo pipefail

SLUG=""
CLAUDE_SESSION=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slug) SLUG="$2"; shift 2 ;;
    --claude-session) CLAUDE_SESSION="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 1 ;;
  esac
done
[[ -n "$SLUG" ]] || { echo "--slug is required" >&2; exit 1; }
[[ -n "$CLAUDE_SESSION" ]] || { echo "--claude-session is required" >&2; exit 1; }
command -v python3 >/dev/null || { echo "python3 is required" >&2; exit 1; }
command -v git >/dev/null || { echo "git is required" >&2; exit 1; }

PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"
ROOT="$PROJECT_DIR/.tama-cc-devflow"
SLUG="$(echo "$SLUG" | tr '[:upper:]' '[:lower:]' | sed -E 's/[^a-z0-9]+/-/g; s/^-+//; s/-+$//' | cut -c1-40)"
SESSION_ID="$(date +%Y%m%d-%H%M%S)-$SLUG"
DIR="$ROOT/$SESSION_ID"

mkdir -p "$DIR"/{design,tasks,reviews}
NOW="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cat > "$DIR/status.json" <<JSON
{
  "session_id": "$SESSION_ID",
  "claude_session_id": "$CLAUDE_SESSION",
  "created_at": "$NOW",
  "updated_at": "$NOW",
  "size": null,
  "phase": "init",
  "branch": null,
  "base_branch": "$(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD)",
  "review_rounds": { "design": 0 },
  "tasks": {},
  "human_decisions_required": [],
  "pr_url": null
}
JSON

cat > "$DIR/context.md" <<MD
# Context

## Original request

(filled by the orchestrator)

## Requirements

## Constraints

## Related files

## Clarifications (human answers)

MD

cat > "$DIR/decisions.md" <<MD
# Decisions

<!-- One entry per important decision. Keep it short. -->
<!--
## D1: <title>
- Decision:
- Reason:
-->
MD

echo "$SESSION_ID" > "$ROOT/current"

echo "$DIR"
