# /flow-next:qa workflow

Execute these phases in order. Each gates on the prior. Stop on a user-blocking error — never plow through with bad state, and never fabricate evidence to keep going.

The phases below are laid out as **disjoint, clearly-delimited sections** so the serial downstream tasks each edit ONE section without colliding on this shared file:

| Phase | Section anchor | Owner |
|-------|----------------|-------|
| discover | `## Phase 1: discover` | fn-53.1 (this task) |
| derive | `## Phase 2: derive` | fn-53.1 (this task) |
| prepare | `## Phase 3: prepare` | fn-53.3 |
| execute | `## Phase 4: execute` | fn-53.4 |
| file | `## Phase 5: file` | fn-53.2 |
| verdict | `## Phase 6: verdict` | fn-53.2 |
| autonomy | `## Phase A: autonomy` | fn-53.4 |

Downstream tasks: replace only the body under your owned anchor. Do NOT touch a sibling phase's section — that is what keeps this file merge-safe across the serial task chain.

## Preamble

```bash
set -e
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TODAY="$(date -u +%Y-%m-%d)"
```

`jq`, `python3` (or `python`), and `git` must be on PATH. `SPEC_ID` comes from the SKILL.md mode-detection block (may be empty — Phase 1 resolves it).

If `.flow/` does not exist, print `No .flow/ directory — /flow-next:qa runs inside a flow-next-managed repo.` and exit 1.

**The hard rule applies through every phase:** PASS / SHIP is forbidden from source inspection. The verdict rests on live-app evidence captured in Phase 4, never on reading the diff. No live app reachable → BLOCKED, never PASS.

---

## Phase 1: discover

**Goal:** resolve the spec id, then pull the structured cognitive-aid payload that Phase 2 derives scenarios from. The spec is the source of intent — read it before touching the app.

### 1.1 — Resolve the spec id

`SPEC_ID` may arrive from the argument list. When empty, resolve it from the current branch, then fall back to an info prompt. Match the branch against each spec's stored `branch_name` (NOT against the branch literal — a flow branch name need not equal the spec id), reusing the make-pr pattern (`flow-next-make-pr/workflow.md` §0.2). Scan `.flow/specs/*.json` (canonical) and `.flow/epics/*.json` (legacy alias dir):

```bash
if [[ -z "$SPEC_ID" ]]; then
  CURRENT_BRANCH="$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null || echo "")"
  if [[ -n "$CURRENT_BRANCH" ]]; then
    SPEC_ID=$(
      { find "$REPO_ROOT/.flow/specs" -maxdepth 1 -name '*.json' 2>/dev/null
        find "$REPO_ROOT/.flow/epics" -maxdepth 1 -name '*.json' 2>/dev/null
      } \
      | xargs -I{} jq -r --arg b "$CURRENT_BRANCH" \
          'select(.branch_name == $b) | .id' {} 2>/dev/null \
      | head -1)
  fi
fi
```

If still empty: ask via `AskUserQuestion` (info prompt — *"Which spec should I QA?"*, options drawn from `$FLOWCTL specs`). Under Ralph this is a hard error (see Phase A). Never silently default to a spec.

Validate the resolved id is a spec (not a task):

```bash
$FLOWCTL show "$SPEC_ID" --json | jq -e '.tasks != null' >/dev/null \
  || { echo "Not a spec: $SPEC_ID (QA runs against a spec, not a single task)." >&2; exit 1; }
```

### 1.2 — Resolve the diff base + pull the cognitive-aid payload

`spec export-cognitive-aid` requires a `--base` ref. QA only needs the **spec** section (AC / R-IDs / boundaries / decision context) to derive scenarios — request that section explicitly to keep the payload small:

```bash
# Base-branch detection cascade (reuses make-pr §0.3): pick the first ref that
# actually resolves. `git rev-parse --verify --quiet` is the gate — a bare `sed`
# pipeline exits 0 even when origin/HEAD is unset, which would leave the base
# empty and break the merge-base below.
DEFAULT_BRANCH=""
for candidate in origin/main main origin/master master; do
  if git -C "$REPO_ROOT" rev-parse --verify --quiet "$candidate" >/dev/null 2>&1; then
    DEFAULT_BRANCH="$candidate"; break
  fi
done
if [[ -z "$DEFAULT_BRANCH" ]]; then
  echo "No base branch found (origin/main, main, origin/master, master all missing). Pass an explicit base or check the clone." >&2
  exit 1
fi
# Diff base = the merge-base, so a branch that's behind the default still gets a
# stable base. Fall back to the default branch itself if no merge-base exists.
BASE_REF="$(git -C "$REPO_ROOT" merge-base "$DEFAULT_BRANCH" HEAD 2>/dev/null || echo "$DEFAULT_BRANCH")"

PAYLOAD="$($FLOWCTL spec export-cognitive-aid "$SPEC_ID" --base "$BASE_REF" --section spec --json)"
```

The `spec.spec_sections` object carries the fields Phase 2 maps:

| Field | Type | Phase 2 use |
|-------|------|-------------|
| `acceptance_criteria[]` | `[{id, text, tag}]` | **AC → scenarios** + the R-ID coverage spine |
| `boundaries[]` | `[string]` | **what NOT to test** (suppress false bugs) |
| `decision_context[]` | `[{question, answer}]` | **expected behavior** (the *Expected* column) |
| `goal_and_context` | string | scenario framing / persona intent |
| `architecture_overview` | string | which surfaces exist to drive |

If `acceptance_criteria` is empty, there is nothing to derive scenarios from — emit a clean **N/A verdict** in Phase 6 (no driveable intent), never crash.

---

## Phase 2: derive

**Goal:** turn the spec into a scenario set with a coverage spine. This is the spec-as-intent advantage — the host already encodes intent instead of reconstructing it (a spec-less QA tool burns a whole reference rediscovering what is in `.flow/specs/`).

### 2.1 — The four mappings

Walk `spec.spec_sections` and build the scenario set:

1. **AC → scenarios.** Each `acceptance_criteria[]` entry with a *user-observable* surface becomes ≥1 scenario: a persona, a goal, and the steps a real user takes to exercise that criterion on the live app. Backend / CLI / non-UI criteria yield **no** scenario (they are covered by static review) — note them as "not live-QA-able" rather than inventing a fake UI path.
2. **R-IDs → coverage spine.** Every `acceptance_criteria[].id` is a row in the coverage table (reuse the make-pr R-ID coverage-table pattern — see §2.2). Each scenario maps back to the R-ID(s) it exercises. R-IDs with no scenario are flagged `⚠️ no live scenario` (an honest gap, never a confident PASS).
3. **Boundaries → exclusions.** Each `boundaries[]` entry is an **explicit non-goal**: a behavior QA must NOT test (e.g. "NOT a code review — drives the live app, not the source"). This suppresses false bugs — a "missing" feature that a boundary declares out of scope is not a finding.
4. **Decision context → expected behavior.** Each `decision_context[]` `{question, answer}` pair seeds the **Expected** column for the scenario(s) it governs — the resolved-default behavior the live app should exhibit. A scenario's pass/fail is `observed vs this expected`, captured as evidence.

### 2.2 — Coverage spine (R-ID table)

Render an R-ID coverage table — exact column order, reusing the make-pr pattern (`flow-next-make-pr/workflow.md` §2.3):

```markdown
| R-ID | Acceptance criterion | Scenario(s) | Coverage |
|------|----------------------|-------------|----------|
| R1 | <criterion text, ≤120 chars + … if truncated> | S1, S2 | live |
| R3 | <…> | — | ⚠️ no live scenario |
| R7 | <…> | — | backend/CLI — not live-QA-able |
```

- **R-ID column** — every entry from `acceptance_criteria[].id`, in spec order. Never renumber; preserve gaps verbatim.
- **Acceptance criterion column** — `acceptance_criteria[].text` truncated to 120 chars (append a single `…` if truncated). Never edit content.
- **Scenario(s) column** — the scenario ids (`S1`, `S2`, …) that exercise this R-ID; `—` when none.
- **Coverage column** — `live` (a scenario will drive it), `⚠️ no live scenario` (UI-observable but uncovered — a gap), or `backend/CLI — not live-QA-able` (no UI surface).

This table is the traceability backbone: spec-AC ↔ scenario ↔ (later) finding ↔ R-ID. Phase 6 reuses it for the verdict; incomplete `live` coverage of UI-observable R-IDs is grounds for NEEDS_WORK, not SHIP.

### 2.3 — Scenario record shape

Each derived scenario is recorded as:

```
S<n>:
  r_ids:    [R<i>, ...]        # which AC it exercises
  persona:  <who — a fresh real user>
  goal:     <what they're trying to do>
  steps:    [<observable user action>, ...]
  expected: <from decision_context / AC — what the live app should do>
  excluded_by: [<boundary text>, ...]   # only if a boundary trims this scenario
```

Scenarios carry forward to Phase 3 (prepare) and Phase 4 (execute). At least one scenario (or an explicit "no UI-observable AC → N/A" determination) must exist before leaving Phase 2.

---

## Phase 3: prepare

<!-- OWNER: fn-53.3 — accounts, session hygiene, device matrix; BRB lean-borrow reference.
     Fill the body below. Do NOT edit sibling phase sections. -->

**Goal:** make the live app driveable — resolve the target URL / app, test accounts, session hygiene (stale storage, persona suffixing), and the device matrix (viewport set). Ask the user when undocumented (R7). *(Skeleton anchor — implemented in fn-53.3.)*

---

## Phase 4: execute

<!-- OWNER: fn-53.4 — drive the live app via the fn-51 read-and-drive contract; autonomy routing.
     Fill the body below. Do NOT edit sibling phase sections. -->

**Goal:** drive each scenario against the live app via the **fn-51 read-and-drive contract** (the host reads fn-51's workflow + references and executes `observe → snapshot → act → verify → capture` itself — QA never re-implements driving). Record the evidence tuple per scenario: `{driver_rung, target_url, viewport, screenshot_path, console_path}`; transient evidence (screenshots, console dumps) lands under `.flow/tmp/` (gitignored), referenced by path, never inlined. *(Skeleton anchor — full execution + autonomy implemented in fn-53.4.)*

### 4.1 — The fn-51 read-and-drive contract (skeleton — proof point)

This task (fn-53.1) exercises the contract end-to-end on ≥1 derived scenario to prove the thesis:

1. **Read fn-51's driving flow** — `plugins/flow-next/skills/flow-next-drive/SKILL.md` (surface detection + universal flow + ladder) and the relevant rung reference under `plugins/flow-next/skills/flow-next-drive/references/`. Do NOT duplicate that prose here.
2. **Resolve a target.** A live deploy URL or a localhost app. If none is reachable, jump to the BLOCKED proof receipt (§4.2) — the R13 graceful-surface path.
3. **Drive the scenario** via fn-51's universal flow (`observe → snapshot fresh refs → act → verify → capture`), using whatever driver rung the environment resolves (agent-browser is the only assumed-present driver; everything else is probe-and-degrade).
4. **Capture evidence.** Screenshot + console at the moment of interest to `.flow/tmp/qa-<spec-id>/`, and record the evidence tuple.

### 4.2 — BLOCKED proof receipt (R13 path — no live target)

When no live deploy + driver is reachable, the proof point is still satisfied: it proves scenario derivation + the fn-51 dispatch handoff + the evidence-tuple plumbing — only the captured screenshot is absent. Emit a BLOCKED proof receipt and stop:

```bash
mkdir -p .flow/tmp/qa-"$SPEC_ID"
cat > .flow/tmp/qa-"$SPEC_ID"/proof-receipt.json <<EOF
{ "type": "qa_proof", "id": "$SPEC_ID", "outcome": "BLOCKED",
  "blocked_reason": "<no live deploy reachable | no driver available>",
  "scenarios_derived": <N>, "evidence_tuple_plumbed": true,
  "fn51_handoff": "read-and-drive contract exercised; driver probe found <rung|none>",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)" }
EOF
```

Only re-evaluate the approach if **derivation** or the **fn-51 handoff** itself fails — a missing live target is an expected, surfaced limitation, not a thesis failure.

---

## Phase 5: file

<!-- OWNER: fn-53.2 — structured P0/P1/P2 findings + evidence; feed the bug memory track.
     Fill the body below. Do NOT edit sibling phase sections. -->

**Goal:** file each failure as a structured P0/P1/P2 finding (persona, steps-to-reproduce, expected vs actual, evidence: console / screenshot / URL), filed immediately on FAIL. Findings feed the bug memory track via `memory add --track bug` (built-in overlap dedup — never `--no-overlap-check`) and carry the R-ID(s) they trace back to. *(Skeleton anchor — implemented in fn-53.2.)*

---

## Phase 6: verdict

<!-- OWNER: fn-53.2 — YES/NO ship verdict + open P0/P1 list; emit the qa_verdict receipt.
     Fill the body below. Do NOT edit sibling phase sections. -->

**Goal:** end with a YES/NO ship verdict + open P0/P1 list, emitted as a `type: qa_verdict` proof-of-work receipt. Four outcomes carried in `qa_outcome` — `SHIP` / `NEEDS_WORK` / `NA` (no driveable UI) / `BLOCKED` (no live deploy or driver) — with `verdict` holding the enum-compatible projection (`BLOCKED→NEEDS_WORK`, `NA→SHIP`). Honesty rules: incomplete R-ID coverage = NEEDS_WORK; a single open P0 = NEEDS_WORK; BLOCKED ≠ FAIL; the verdict rests on captured evidence, never narration. *(Skeleton anchor — implemented in fn-53.2.)*

---

## Phase A: autonomy

<!-- OWNER: fn-53.4 — Ralph-aware-not-blocked detect-once; opt-in tracker.perEvent.qa; graceful degradation.
     Fill the body below. Do NOT edit sibling phase sections. -->

**Goal:** detect Ralph once and route deterministically (R11) — autonomous when target URL + test accounts are configured (emits the verdict receipt to the caller-supplied `--receipt`/`REVIEW_RECEIPT_PATH`); asks the user when they are undocumented. **Not a hard Ralph-block** — no `FLOW_RALPH` exit-2 guard. Opt-in tracker verdict post (`tracker.perEvent.qa`) and graceful degradation when no driver is present. *(Skeleton anchor — implemented in fn-53.4.)*
