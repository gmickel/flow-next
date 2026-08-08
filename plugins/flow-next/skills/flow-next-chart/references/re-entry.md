# Tracker-URL / locator re-entry

Read this file only when Phase 0.1 classified the argument as a **locator-shaped selector** (tracker URL, issue key with provider host, or stored tracker identifier). Idea text, chart ids, and pinned D-IDs never reach it.

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

---

### 0.2 - Tracker-URL / locator re-entry

**Contract:** `flowctl chart locate` is a **strictly local** ledger lookup. No remote search, no redirect following, no title inference. Failures mutate nothing.

Probe availability first (subcommand ships in a later task on some trees):

```bash
LOCATE_HELP=$("$FLOWCTL" chart locate --help 2>&1) || true
if printf '%s' "$LOCATE_HELP" | grep -qiE 'locate|usage:'; then
  LOCATE_JSON=$("$FLOWCTL" chart locate "$SELECTOR" --json 2>/dev/null) || LOCATE_JSON=""
else
  LOCATE_JSON=""
  # Degrade: ask for the local chart id; never invent identity from the URL title.
fi
```

When locate succeeds:

1. Read back **canonical local ID**, **title**, and **record link** before any work.
2. Parent chart URL/id -> status/frontier re-anchor (default work mode unless `--status`).
3. Open decision URL/id -> pin that D-ID for work mode.
4. Resolved or superseded decision URL -> show **history** + replacement/frontier options; **never** silently choose different work.

When locate fails or is unavailable:

- Print structured failure or "locate not available".
- Offer the local chart-id path via blocking question.
- Create nothing; mutate nothing; do not treat the URL text as a new Outcome.

