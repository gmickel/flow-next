# Tracker-URL / locator re-entry

Read this file only when Phase 0.1 classified the argument as a **locator-shaped selector** (tracker URL, issue key with provider host, or stored tracker identifier). Idea text, chart ids, and pinned D-IDs never reach it.

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

---

### 0.2 - Tracker-URL / locator re-entry

**Contract:** `flowctl chart locate` is a **strictly local** ledger lookup. No remote search, no redirect following, no title inference. Failures mutate nothing.

```bash
LOCATE_JSON=$("$FLOWCTL" chart locate "$SELECTOR" --json 2>/dev/null) || true   # a failure still prints its JSON envelope
```

When locate succeeds (`.success` is true):

1. Read back **canonical local ID**, **title**, and **record link** before any work.
2. Parent chart URL/id -> status/frontier re-anchor (default work mode unless `--status`).
3. Open decision URL/id -> pin that D-ID for work mode.
4. Resolved or superseded decision URL -> show **history** + replacement/frontier options; **never** silently choose different work.

When locate fails (`.success` is false, or no output):

- Print the structured failure.
- Offer the local chart-id path via plain-text numbered prompt.
- Create nothing; mutate nothing; do not treat the URL text as a new Outcome.

