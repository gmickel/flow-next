# /flow-next:chart workflow

Execute the mode selected in [SKILL.md](SKILL.md). Stop on user-blocking error - never plow through with bad state. Prefer concise direct prose in user-facing read-backs. Use plain hyphens only (never em dashes).

## Preamble

```bash
set -e
FLOWCTL="$HOME/.codex/scripts/flowctl"
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
- Offer the local chart-id path via plain-text numbered prompt.
- Create nothing; mutate nothing; do not treat the URL text as a new Outcome.

### 0.2b - Tracker projection gate (optional; best-effort)

Chart projection rides the post-fn-141 lifecycle facade. Local chart
mutations always commit first; remote projection never blocks them.

Gate (both required): bridge active AND `tracker.charts` is the literal `on`.
The perEvent vocabulary (`off | pull | push | reconcile | comment`) does not
select chart ops - chart is always a local-first **push** of the committed
revision when the gate is open. When the gate is closed, flowctl still
succeeds and `tracker_projection.skipped` names the reason
(`tracker.charts_off` / `bridge_inactive`).

```bash
CHARTS_LEAF="$("$FLOWCTL" config get tracker.charts --json 2>/dev/null | jq -r '.value // "off"')"
case "$CHARTS_LEAF" in
 on) CHARTS_ON=1 ;;
 off|null) CHARTS_ON=0 ;;
 pull|push|reconcile|comment) CHARTS_ON=0 ;; # perEvent verbs are not chart gates
 *) CHARTS_ON=0 ;;
esac
if [ "$("$FLOWCTL" sync active --json 2>/dev/null | jq -r '.active // false')" = "true" ] \
 && [ "$CHARTS_ON" = "1" ]; then
 # flowctl chart mutations already call the facade once per committed revision
 # (event: chart.create|chart.wire|chart.claim|chart.release|chart.resolve|
 # chart.supersede|chart.outOfScope|chart.briefing|chart.abandon|chart.reopen).
 # Host recovery handoff on partial remote success: re-invoke the same chart
 # command or rely on the next mutation - event markers + aggregate receipt
 # dedupe so retry converges without duplicate issues/comments/relations.
 # Equivalent one-shot surface (automation):
 # "$FLOWCTL" tracker sync "chart:<chart-id>" --op push --event chart \
 # <legal file flags>
 # Evidence for any synthesized comment: evidence=<chart-revision-sha>.
 # Chart synthesizes owned parent rollup / decision body blocks only - never
 # free-form status masquerading as provider workflow.
 # Best-effort - a tracker failure never rolls back local chart state.
 :
fi
```

### 0.3 - Human pairings

Every human-facing list of decisions pairs **title + D-ID + record link**. Never dump bare identifiers alone (R36).

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

---

## Phase 2: Work mode (adaptive loop)

**Goal:** one session-sized uncertainty from the live frontier, one claim, one evidence route, one transition, re-chart. Never execute a frozen up-front sequence.

### 2.1 - Re-anchor

```bash
"$FLOWCTL" chart show "$CHART_ID" --json
```

Load compact metadata + map body. Re-state **Outcome** and honor standing preferences / named skills in `## Notes`. Do **not** load every decision body/asset yet.

If chart status is `done` or `abandoned`, stop unless the user explicitly asks to reopen (`chart reopen --reason` after read-back). Suggest briefing/capture when done and briefable history exists.

### 2.2 - Frontier is the sole selection input

```bash
"$FLOWCTL" chart frontier "$CHART_ID" --json
```

Frontier = open, unblocked, unclaimed, dependency-ordered.

- Empty + not briefable (blocked/claimed/parked remain) -> report stuck reasons; `CHART_VERDICT=BLOCKED` or `NO_WORK` as appropriate.
- Empty + briefable -> go to Phase 4 briefing path; `CHART_VERDICT=COMPLETE` when briefing succeeds or when reporting briefable with no work left.
- Human pin (`--decision`) must appear on the frontier (or be the open locator-selected D-ID after claim eligibility check). If pinned decision is blocked/claimed/resolved, report and stop - do not silently pick another.

Choose the **smallest** uncertainty whose answer most reduces uncertainty or unlocks others. Prefer cheaper unattended evidence when it settles the same question.

**Oversized decisions:** if the selected question cannot fit one agent context (~100k tokens / one session), **split before claim** via `add-decision` + `wire-decision` (or sharpen on a parent resolve) - never dispatch a workstream-sized D-ID.

### 2.3 - Claim before any work

```bash
"$FLOWCTL" chart claim "<chart-id>.D<n>" --json
```

On conflict: print owner/age; do not work the decision. Offer `release-claim` for owner, or audited `--break-stale --reason` only after age gate. Terminal `BLOCKED` when claim fails and no alternate is selected in this invocation (one invocation never silently switches D-IDs after a failed claim).

### 2.4 - Load full body only for the claimed decision

Read the decision record + assets for the claimed D-ID only. Context discipline: navigation stays compact; selection loads depth.

### 2.5 - Attended hard gate

If stored `attendance` is `attended` **and** the driver is unattended:

1. Persist **no** answer.
2. Do not resolve, out-of-scope, or attach fabricated assets.
3. Prefer `chart release-claim` with note `awaiting human (attended)` when a clean release is available; if the loop crashed mid-claim, leave claim visible for recovery.
4. Terminal:

```text
CHART_VERDICT=NEEDS_HUMAN chart=<id> decision=<D> reason="attended decision requires human; no answer written"
```

### 2.6 - Evidence route by type

| Type | Route |
|---|---|
| `research` | Dispatch read-only scout (`Task` / Explore or portable read-only). Digest facts + citations. Write safe answer file. |
| `probe` | Measure/reproduce against the real system; store results as safe summary + evidence path/ref. |
| `eval` | Bake-off on real fixtures; winner + why. |
| `prototype` | Phase 2.7 (attended lifecycle). |
| `interview` | One question at a time via `plain-text numbered prompt` (numbered fallback). Never self-answer. |
| `task` | Perform only the enabling work; if attended, wait for human completion signal. |

Unsafe content (secrets, guard-triggering destructive commands): refuse to embed. Keep source at repository-relative path or approved HTTPS URL; store redacted summary + link. Describe dangerous operations in prose - never paste literal destructive shell command strings into answers or this skill.

### 2.7 - Prototype lifecycle (attended)

1. **Create or import ONE scoped throwaway artefact** (sketch, branch, HTML mock, fixture) sized to the question.
2. **Attach while open:**

```bash
# asset JSON: { "kind": "path"|"git_ref"|"branch"|"commit"|"url"|"https",
# "reference": "<safe ref>", "display": "<summary>", "revision": "<optional>" }
"$FLOWCTL" chart attach-asset "<chart-id>.D<n>" --asset-file assets.json --json
```

Idempotent; decision stays `open`.

3. **Present** the exact safe reference/revision to the human (not a paraphrase of an unattached path).
4. **Record the reaction** (approve direction / reject / redirect).
5. **Resolve or supersede** with answer file capturing the reaction + asset refs. Use `--supersedes` when the reaction invalidates a prior assumption (Phase 5).
6. If the human does not react this session: release claim with `awaiting reaction` note **or** leave crash/claim state observable. **Resume later from the existing asset** - never rebuild, never infer approval.
7. Prototype code is **evidence**, never silent implementation under plan/work.

Missing or unsafe artefact -> cannot resolve a prototype decision.

### 2.8 - Resolve / out-of-scope / release

**Resolve:**

```bash
"$FLOWCTL" chart resolve "<chart-id>.D<n>" \
 --answer-file answer.md \
 [--sharpen-file sharpen.json] \
 [--supersedes D3,D5] \
 [--keep-dependents] \
 [--assets '[]'] \
 --json
```

**Out-of-scope** (closes without ledger answer; writes `## Boundaries`):

```bash
"$FLOWCTL" chart out-of-scope "<chart-id>.D<n>" --reason "<one line>" --json
```

**Release** without closing (stop / hand back):

```bash
"$FLOWCTL" chart release-claim "<chart-id>.D<n>" --json
```

### 2.9 - Sharpen newly visible decisions

After an answer exposes sharper questions, include them in the same resolve transaction:

```json
{
 "decisions": [
 {
 "title": "Pick retention window",
 "type": "interview",
 "question": "How long must tenant audit logs remain queryable?"
 }
 ],
 "remove_questions": ["<parked-key-that-sharpened>"]
}
```

`resolve --sharpen-file` allocates new D-IDs, wires graph if provided, removes parked keys, all-or-nothing. Do not hand-edit Open Questions.

### 2.10 - Recompute frontier and stop

After every resolve / out-of-scope / supersession:

1. Call `chart frontier` again.
2. Propose the next smallest uncertainty from the **new** state (do not execute it in this invocation).
3. Emit exactly one terminal line, e.g.:

```text
CHART_VERDICT=RESOLVED chart=fn-140 decision=fn-140.D2 reason="storage approach settled via probe; frontier redrawn"
```

Independent unattended frontier members may be offered for **parallel separate invocations** - never batch-claimed here.

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

## Phase 4: Briefing handoff

When `frontier` / completion reports **briefable** (no open decisions including blocked/claimed; no parked Open Questions), or the user asks "one spec or two" / "ready to capture":

1. Cluster resolved decisions; **default N=1**. Propose split only when clusters are genuinely disjoint.
2. For each cluster: one-line rationale; name multi-cluster D-IDs as **shared context** (not duplicated requirements).
3. Read back the proposal for confirmation (merge / split further / override / abort).
4. Write proposal file:

```json
{
 "clusters": [
 {
 "key": "1",
 "rationale": "Single product surface; all decisions share one Outcome",
 "decisions": ["fn-140.D1", "fn-140.D2"]
 }
 ],
 "shared_context": []
}
```

5. Call:

```bash
"$FLOWCTL" chart briefing "$CHART_ID" --proposal-file proposal.json [--force] --json
```

- Ordinary briefing refuses while open/parked remain unless `--force` (draft-only, chart stays open, never capture-ready).
- First non-draft briefing sets chart `done`.

6. Hand off to `/flow-next:capture` with the briefing path / B-ID. Capture owns source tags on criteria it newly authors; chart evidence stays as D-ID links.

Terminal on successful final briefing:

```text
CHART_VERDICT=COMPLETE chart=<id> decision=- reason="briefing B1 emitted; hand off to capture"
```

---

## Phase 5: Supersession steering

When the user says the direction changed (e.g. prototype reversed an earlier assumption):

1. Read back: which prior D-ID(s) are invalidated, what the new answer is, and cascade implications (`depends_on` open dependents lose claims; resolved dependents get replacement D-IDs unless `--keep-dependents`).
2. Resolve the new decision with `--supersedes <D,...>` after consent.
3. Report every affected D-ID. Ledger lines for superseded decisions stay struck-through - never deleted.

---

## Phase 6: Abandon / reopen (explicit only)

- `chart abandon --reason` - terminal stop mid-discovery; decisions preserved.
- `chart reopen --reason` - audited; stales prior briefings and spec links before new work.

Always read back reason and consequence first.

---

## Automation flag map (not required vocabulary)

| Human intent | flowctl |
|---|---|
| Start discovery on an idea | `chart create --title --outcome --initial-map-file` |
| Keep one chart past ceiling | same + `--force-size --reason` after consent |
| What's next | `chart frontier` / `chart show` |
| Work this decision | `chart claim` then route then `resolve` / `out-of-scope` |
| Park a vague unknown | `chart park-question --body-file` |
| Wire edges after create | `chart wire-decision` |
| Attach prototype evidence | `chart attach-asset --asset-file` |
| Sharpen after answer | `resolve --sharpen-file` |
| Reverse prior answer | `resolve --supersedes` |
| Brief for capture | `chart briefing --proposal-file` |
| Re-enter from tracker URL | `chart locate` (local only; degrade if missing) |

---

## Safety and provenance recap

- Citations under Notes; no fabricated D-IDs from imports.
- No acceptance-criterion tags on chart facts/decisions.
- No verified/inferred fact grammar (fn-148 STOPPED).
- No literal destructive shell command strings or realistic secrets in artefacts or skill examples.
- Parallelism = parallel invocations, never one tick claiming many D-IDs.
