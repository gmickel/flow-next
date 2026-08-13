# Chart mode - ground, propose, create

Read this file only when Phase 0 routed to **chart mode** (a free-form idea, "chart out ...", or residual prose after flag strip). Work, status, and re-entry paths never need it.

- [Phase 1: Chart mode (ground -> propose -> create)](#phase-1-chart-mode-ground---propose---create)
- [1.1 - Ordered Grounding Snapshot](#11---ordered-grounding-snapshot)
- [1.2 - Refuse to chart -> STOP (two shapes)](#12---refuse-to-chart---stop-two-shapes)
- [1.3 - Shape the initial map (breadth-first, visible only)](#13---shape-the-initial-map-breadth-first-visible-only)
- [1.4 - Read-back before persistence](#14---read-back-before-persistence)
- [1.5 - Persist via flowctl only](#15---persist-via-flowctl-only)
- [1.6 - Notes seeding](#16---notes-seeding)

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

---

## Phase 1: Chart mode (ground -> propose -> create)

**Goal:** bounded Grounding Snapshot, read-back, then either create the visible frontier or stop without persistence. **Resolve no decisions in this session.**

### 1.1 - Ordered Grounding Snapshot

Follow the ordered pattern used by prospect (ground sources first, titles/tags + safe references only - never raw file dumps). This is **not** open-ended research and does not search the world before the user can begin.

Read, in order, only immediately relevant in-scope sources:

1. **User prompt and attachments** - stated Outcome signals, known facts, constraints, links the user supplied.
2. **Repository strategy / instructions / current implementation** - strategy snapshot when populated, project instructions, code pointers the idea clearly touches.
3. **Directly relevant specs and chart history** - open specs titles, prior charts that overlap the idea.
4. **Explicitly connected knowledge sources** - memory hits when memory is enabled and the focus is concept-like; user-supplied external docs only when provided or made available.

Outside-repository material is read only when the user supplied it or made the source available.

Emit a structured snapshot under `## Grounding Snapshot`:

```text
## Grounding Snapshot

candidate_outcome: <1-2 lines>
known_facts:
  - <fact> [ref: <path|commit|https> rev:<optional>]
conflicts_or_staleness:
  - <uncertainty - missing, conflicting, stale, inaccessible, or secret-bearing>
smallest_visible_frontier:
  - <proposed title> (type: research|probe|eval|prototype|interview|task) [attendance if task]
parked_unknowns:
  - <in-scope but not yet sharp enough to be a decision record>
attended_unattended_cost:
  - <N decisions: U unattended, A attended; estimated sessions with you>
```

**Grounding rules:**

- Preserve safe evidence references and capture revision/fingerprint where the source provides one.
- Missing, inaccessible, conflicting, stale, secret-bearing, ignored, symlink-escaping, or outside-repo material remains **uncertainty** - never becomes a fact by inference.
- Imported background stays under proposed `## Notes` with citations. **No imported fact becomes a D-ID.**
- Do not apply acceptance-criterion trailing tags to chart facts.
- Do not invent verified/inferred fact grammar (fn-148 closed STOPPED - no product claim).
- Ask only questions not already answered by approved evidence.

Compose blocks with graceful degradation (`scanned: none (<reason>)` when a source is absent), matching prospect's style for strategy/specs/memory/git signals as relevant to the idea.

### 1.2 - Refuse to chart -> STOP (two shapes)

**Shape A - no nameable destination.** Before anything else, confirm the idea has an end state you can name: the spec, decision, or change this effort is finding its way to. Chart's premise is *destination known, route unknown*. A theme or direction ("make the CLI more deterministic", "improve our test story") has no finish line, so no Outcome can be stated, nothing can be ruled out of scope, and the map never closes. Do not chart it and do not silently chart a guessed narrowing of it. Say what is missing, then offer exactly two routes: narrow to one effort with a stateable end state (invite the narrowed prompt), or run `/flow-next:prospect` when the real ask is which effort to pick. **Create nothing.**

```text
CHART_VERDICT=NO_WORK chart=- decision=- reason="direction not destination; narrow to one effort or run prospect"
```

**Shape B - no consequential unknowns.** If after grounding the effort has **no consequential unknowns** (intent and boundaries already stateable; nothing worth parking; no decision that would change capture):

1. Say so clearly.
2. Recommend `/flow-next:capture` or authoring the spec / direct change path.
3. **Create nothing.**
4. Terminal line:

```text
CHART_VERDICT=NO_WORK chart=- decision=- reason="no consequential unknowns; capture or direct route"
```

### 1.3 - Shape the initial map (breadth-first, visible only)

Build **only the first visible frontier**, breadth-first from the Outcome. Do not precompute a complete discovery plan. Independent unattended evidence routes may appear on the frontier for later parallel dispatch; charting still resolves none.

Each proposed decision needs:

- `title` (human-readable)
- `type` (required)
- `question` / body (what it settles)
- `attendance` only when `type=task`
- optional `blocked_by` / `depends_on` using provisional local refs (`D1`, `1`, ...)

Parked questions are strings or objects with body text - in-scope unknowns not yet sharp enough for a decision record. Sharp-but-blocked items are decision records, not parked.

**Size ceiling:** read `chart.maxDecisions` (default 12):

```bash
CEILING=$("$FLOWCTL" config get chart.maxDecisions --json 2>/dev/null | jq -r '.value // 12')
```

If proposed decision count `> CEILING`:

1. **Refuse by default.**
2. Offer **narrow the Outcome** or **split into two charts** first.
3. Only if the user explicitly insists on one oversized chart: warn with count, ceiling, and consequence; read back consent; then pass `--force-size --reason "<consent reason>"` on create. Record only after that read-back.

### 1.4 - Read-back before persistence

Present before any write:

- Named `## Outcome`
- Grounding known-facts (cited) + conflicts/staleness as uncertainty
- Smallest visible frontier (title + type + attendance)
- Parked unknowns
- Attended/unattended cost line, e.g. `9 decisions: 5 unattended (parallel, ~1 session), 4 attended (~4 sessions). Estimated 4-5 working sessions with you.`

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

Use `plain-text numbered prompt` (or numbered plain-text fallback) for approve / edit / abort. Edit cycles revise the proposal and re-read-back. Abort creates nothing.

### 1.5 - Persist via flowctl only

Write an initial-map JSON file (never hand-edit `.flow/charts/`):

```json
{
  "decisions": [
    {
      "title": "Research provider limits",
      "type": "research",
      "question": "What hard limits does the provider publish for multi-tenant rate isolation?"
    },
    {
      "title": "Prototype tenancy UX",
      "type": "prototype",
      "question": "Does the tenant switcher mental model match operators?"
    }
  ],
  "parked_questions": [
    "Whether billing splits per tenant or per workspace"
  ],
  "notes": "- Tenancy today is a single shared schema [ref: src/db/schema.sql rev:9f2c1ab]\n- Provider rate limits are per-account, not per-key [ref: https://example.invalid/docs/limits]"
}
```

```bash
"$FLOWCTL" chart create \
  --title "<short title>" \
  --outcome "<outcome text>" \
  --initial-map-file "<path>" \
  [--force-size --reason "<consent reason>"] \
  --json
```

On success:

- `## Decisions` ledger starts empty of answers (records exist; nothing resolved).
- Print chart id, path, cost line, frontier summary.
- **Close by offering independent unattended frontier decisions for parallel dispatch as separate `/flow-next:chart <id>` (or pinned) invocations.** Charting session still resolves none.
- Terminal line example:

```text
CHART_VERDICT=NO_WORK chart=<id> decision=- reason="chart created; frontier offered; chart mode resolves nothing"
```

### 1.6 - Notes seeding

Known facts with citations go into the chart's `## Notes` through the initial-map file's optional `notes` string - `chart create --initial-map-file` seeds the `## Notes` section from it (R52). Keep each line a cited fact with its safe reference/revision. Do **not** fabricate resolved ledger lines for background: a fact under Notes is never a D-ID.

