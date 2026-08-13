# /flow-next:chart workflow

Execute the mode selected in [SKILL.md](SKILL.md). Stop on user-blocking error - never plow through with bad state. Prefer concise direct prose in user-facing read-backs. Use plain hyphens only (never em dashes).

## Preamble

```bash
set -e
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

Bash vars do not survive across prompt turns - re-declare the FLOWCTL block at the top of any later bash block that needs it.

**Blocking questions:** use bare `plain-text numbered prompt`. If unreachable, print a plain-text numbered prompt with a final `Other - type your own answer` option and wait for the typed reply.

**Read-only scouts:** use `spawn_agent` with `agent_type: explorer`. On hosts without an Explore builtin (e.g. Cursor), use the host's generic read-only dispatch with Edit/Write disallowed. Facts with safe path/revision references only - never judgments that settle attended decisions.

**Unattended driver** (any one signal): `FLOW_RALPH=1`, non-empty `REVIEW_RECEIPT_PATH`, non-empty `FLOW_AUTONOMOUS`, or host loop with no human present. Interactive terminal = attended.

---

## Phase 0: Route

**Goal:** choose chart / work / status / re-enter without treating a locator as a new idea.

### 0.1 - Parse `$ARGUMENTS`

```bash
RAW_ARGS="${ARGUMENTS:-}"
MODE=""
CHART_ID=""
DECISION_PIN=""
STATUS_ONLY=0
SELECTOR=""
```

Classification order (first match wins):

1. **Status** - contains `--status`, or plain-language "what's left", "show status", "remaining cost" with a chart id.
2. **Pinned decision** - `--decision <n>` / `--decision <chart>.D<n>` / bare `fn-N.D<n>` / plain "work decision Dn on ...".
3. **Chart id** - token matching a known chart (`$FLOWCTL chart show <id> --json` succeeds) or plain "work the next decision on `<id>`".
4. **Locator-shaped selector** - looks like a tracker URL, issue key with provider host, or stored tracker identifier. **Before** treating it as a new idea, run Phase 0.2.
5. **Chart mode** - free-form idea / "chart out ..." / remaining prose after flag strip.
**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

6. Empty - ask what to chart or which chart to work (plain-text numbered prompt).

Strip recognized flags from the residual idea text; do not require the user to know flag names.

### 0.2 - Tracker-URL / locator re-entry

Only when classification matched a **locator-shaped selector** (step 4): STOP and read [references/re-entry.md](references/re-entry.md) before treating the selector as anything else. It owns the local-ledger `chart locate` probe, the read-back order, and the degrade path. Idea text, chart ids, and pinned D-IDs skip it.

### 0.2b - Tracker projection gate (optional; best-effort)

Local chart mutations always commit first; remote projection never blocks them. Probe the gate (fails OPEN - an unreadable probe is treated as active):

```bash
ACTIVE=0
# NO pipelines in the probe - capture raw first, rc-checked; parse separately.
RAW_SYNC="$("$FLOWCTL" sync active --json 2>/dev/null)" || ACTIVE=1
RAW_CHARTS="$("$FLOWCTL" config get tracker.charts --json 2>/dev/null)" || ACTIVE=1
if [ "$ACTIVE" = "0" ]; then
  BRIDGE="$(printf '%s' "$RAW_SYNC" | jq -r '.active // false' 2>/dev/null)" || ACTIVE=1
fi
if [ "$ACTIVE" = "0" ]; then
  # perEvent verbs (pull|push|reconcile|comment) are not chart gates - only literal `on`.
  CHARTS_LEAF="$(printf '%s' "$RAW_CHARTS" | jq -r '.value // "off"' 2>/dev/null)" || ACTIVE=1
fi
if [ "$ACTIVE" = "0" ] && [ "$BRIDGE" = "true" ] && [ "$CHARTS_LEAF" = "on" ]; then
  ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
  echo "TRACKER PROJECTION GATE ACTIVE - STOP. Read references/tracker-projection.md before continuing."
fi
```

When the sentinel prints, STOP and Read [references/tracker-projection.md](references/tracker-projection.md) before any further step. When it does not print, projection is off: flowctl still succeeds and `tracker_projection.skipped` names the reason.

### 0.3 - Human pairings

Every human-facing list of decisions pairs **title + D-ID + record link**. Never dump bare identifiers alone (R36).

---

## Mode dispatch (one path per invocation)

A chart session walks ONE of these. Read only the file for the routed mode; the others are dead context.

| Mode | Read |
|---|---|
| **chart** (free-form idea) | [references/chart-mode.md](references/chart-mode.md) - Grounding Snapshot, both STOP shapes, size ceiling, read-back, `chart create --initial-map-file`, Notes seeding |
| **work** (chart id / pinned D-ID) | [references/work-mode.md](references/work-mode.md) - re-anchor, frontier, claim, attended hard gate, evidence routes, prototype lifecycle, resolve/sharpen/notes correction, supersession steering |
| **status** (`--status` / "what's left") | Phase 3 below - render only |
| **briefing / abandon / reopen** | [references/briefing-and-reopen.md](references/briefing-and-reopen.md) - cluster proposal, `chart briefing --proposal-file`, abandon, reopen epochs |

Two invariants hold on every path regardless of mode: the chart stops and creates nothing when the idea names a direction rather than a nameable destination or carries no consequential unknowns, and every invocation ends with exactly one `CHART_VERDICT=` line and nothing after it.

---

## Phase 3: Status mode

```bash
"$FLOWCTL" chart show "$CHART_ID" --json
"$FLOWCTL" chart frontier "$CHART_ID" --json
```

Render:

- Outcome + status
- Counts (resolved / open / blocked / claimed / parked)
- Remaining attended-session estimate (`cost_line` when present)
- Frontier list as title + D-ID + link + type/attendance
- Stuck reasons when not briefable

**Resolve nothing. Claim nothing.** Terminal:

```text
CHART_VERDICT=NO_WORK chart=<id> decision=- reason="status only; no mutations"
```

---

## Safety and provenance recap

- Citations under Notes; no fabricated D-IDs from imports.
- No acceptance-criterion tags on chart facts/decisions.
- No verified/inferred fact grammar (fn-148 STOPPED).
- No literal destructive shell command strings or realistic secrets in artefacts or skill examples.
- Parallelism = parallel invocations, never one tick claiming many D-IDs.
