# Plan Review Workflow — Common

## Philosophy

Resolve the mode once, keep shared orchestration here, then load only the
selected backend workflow. Backend execution and rubric material must not leak
into this common file.

## Phase 0: Backend Detection

Run this first, exactly once.

```bash
set -e
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

if command -v rpce-cli >/dev/null 2>&1 \
  || [ -x "$HOME/RepoPrompt/repoprompt_ce_cli" ] \
  || [ -x "$HOME/Library/Application Support/RepoPrompt CE/repoprompt_ce_cli" ] \
  || command -v rp-cli >/dev/null 2>&1; then
  RP_ELIGIBLE=1
else
  RP_ELIGIBLE=0
fi
```

Resolve the canonical spec id from the positional argument before backend
routing. Parse `--review=<mode>` / `--review <mode>` from `$ARGUMENTS` first.
Accepted explicit modes: `rp`, `codex`, `copilot`, `cursor`, `host`, `export`,
`none`.

When an explicit mode exists, set `BACKEND` directly and do not call
`review-backend`. Otherwise:

```bash
SPEC_ID="${1:-}"
BACKEND=$($FLOWCTL review-backend "$SPEC_ID")
```

`review-backend` preserves per-spec → env → config precedence and returns the
bare backend name. If `BACKEND=ASK`, print the existing setup/override guidance
(omit rp when `RP_ELIGIBLE=0`) and exit 1.

If `BACKEND=none`, inform the user that plan review was skipped and return
cleanly. Load no backend file and write no receipt/status.

If `BACKEND=export`, run the existing plan export route from
`flow-next-export-context` with the canonical `SPEC_ID` and focus areas. Preserve
its RepoPrompt setup, selection, prompt composition, Desktop
`review-export-<timestamp>.md` write, `open`, and user-facing “Exported review
context to:” output exactly. Then return. Do not resolve or load any configured
backend, write review receipt/status, or enter the review fix loop.

For an executable review backend, print the existing backend/override summary
(omit rp when ineligible) and continue.

## Phase 1: Common Review Inputs

The selected backend owns invocation, but all review routes use the current
persisted spec:

```bash
$FLOWCTL show "$SPEC_ID" --json
$FLOWCTL cat "$SPEC_ID"
$FLOWCTL checkpoint save --spec "$SPEC_ID" --json
```

This re-anchor is mandatory before every fix cycle. A user-edited spec is the
source of truth; never review or restore a stale generated/checkpoint copy
unless recovering after context compaction.

For Codex/Copilot/Cursor, derive reviewer code anchors from the current spec in
the selected backend's single atomic dispatch fence. For host and rp, provide
the same current spec/task material and review focus.

## Phase 2: Select One Backend Workflow

Read exactly one:

| `$BACKEND` | File |
|---|---|
| `codex` | [workflow-codex.md](workflow-codex.md) |
| `copilot` | [workflow-copilot.md](workflow-copilot.md) |
| `cursor` | [workflow-cursor.md](workflow-cursor.md) |
| `host` | [workflow-host.md](workflow-host.md) |
| `rp` | [workflow-rp.md](workflow-rp.md) |

Do not read any other backend file. Unknown/malformed values fail closed with
the same `ASK`/error behavior; never guess a backend.

## Common Terminal Contract

- `SHIP` → latest status/receipt says ship; reset the cumulative counter where
  the backend does not already do so; return `SHIP`.
- `NEEDS_WORK` → latest status/receipt says needs_work; return to SKILL.md's one
  shared fix loop.
- `MAJOR_RETHINK` → latest status/receipt says needs_work; return immediately
  for typed design-conflict escalation.
- Backend unavailable/transport/no verdict → `<promise>RETRY</promise>` and
  stop. Flowctl records and refunds the reserved round; never manually reset
  the verdict counter. Exit 5 / `TRANSPORT_UNHEALTHY` stops automatic retries.
  Never mix or fall back to another backend.

## Anti-patterns

- Resolving the backend twice
- Loading all backend files before branching
- Letting `none` or `export` read a backend file
- Reviewing a checkpoint instead of the current user-edited spec
- Backgrounding a review call
