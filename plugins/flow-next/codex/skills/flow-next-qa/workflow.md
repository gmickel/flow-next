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
FLOWCTL="$HOME/.codex/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
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

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

If still empty: ask via `plain-text numbered prompt` (info prompt — *"Which spec should I QA?"*, options drawn from `$FLOWCTL specs`). Under Ralph this is a hard error (see Phase A). Never silently default to a spec.

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
#
# Honor a caller-supplied base override first: a `--base <ref>` flag (when the
# Mode-Detection block parses one) or a `QA_BASE_REF` env var sets DEFAULT_BRANCH
# before the cascade, so the detection only runs when nothing was passed.
DEFAULT_BRANCH="${QA_BASE_REF:-}"
if [[ -z "$DEFAULT_BRANCH" ]]; then
 for candidate in origin/main main origin/master master; do
 if git -C "$REPO_ROOT" rev-parse --verify --quiet "$candidate" >/dev/null 2>&1; then
 DEFAULT_BRANCH="$candidate"; break
 fi
 done
fi
# Fall back to the repo's ACTUAL default branch when it isn't named main/master
# (develop, trunk, …). `origin/HEAD` is the remote's recorded default; resolve it
# to `origin/<branch>` and verify the ref actually exists. `git remote set-head
# origin -a` repairs an unset symbolic-ref on clones that never recorded one.
if [[ -z "$DEFAULT_BRANCH" ]]; then
 ORIGIN_HEAD="$(git -C "$REPO_ROOT" symbolic-ref --quiet refs/remotes/origin/HEAD 2>/dev/null \
 | sed 's#^refs/remotes/##')"
 if [[ -z "$ORIGIN_HEAD" ]]; then
 git -C "$REPO_ROOT" remote set-head origin -a >/dev/null 2>&1 || true
 ORIGIN_HEAD="$(git -C "$REPO_ROOT" symbolic-ref --quiet refs/remotes/origin/HEAD 2>/dev/null \
 | sed 's#^refs/remotes/##')"
 fi
 if [[ -n "$ORIGIN_HEAD" ]] && git -C "$REPO_ROOT" rev-parse --verify --quiet "$ORIGIN_HEAD" >/dev/null 2>&1; then
 DEFAULT_BRANCH="$ORIGIN_HEAD"
 fi
fi
# Still nothing — ask the user for the base (interactive), or hard-error under
# Ralph. Mirrors make-pr §0.3: never silently exit on an unusual default branch.
if [[ -z "$DEFAULT_BRANCH" ]]; then
 if [[ "${RALPH:-0}" == "1" ]]; then
 echo "No base branch detected (origin/main, main, origin/master, master, origin/HEAD all missing). Pass an explicit base or check the clone." >&2
 exit 1
 fi
 # Interactive: ask for the base ref via plain-text numbered prompt (info prompt — no frozen
 # options; accept a typed ref). Validate the answer with rev-parse below; on
 # abort, exit 1. (sync-codex.sh rewrites plain-text numbered prompt to a numbered prompt.)
 : "ask user for DEFAULT_BRANCH via plain-text numbered prompt; on abort exit 1"
fi
# Validate the resolved/typed base actually exists before computing the merge-base.
if ! git -C "$REPO_ROOT" rev-parse --verify --quiet "$DEFAULT_BRANCH" >/dev/null 2>&1; then
 echo "Base ref '$DEFAULT_BRANCH' is not a valid git ref. Check with: git rev-parse --verify $DEFAULT_BRANCH" >&2
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
 r_ids: [R<i>, ...] # which AC it exercises
 persona: <who — a fresh real user>
 goal: <what they're trying to do>
 steps: [<observable user action>, ...]
 expected: <from decision_context / AC — what the live app should do>
 excluded_by: [<boundary text>, ...] # only if a boundary trims this scenario
```

Scenarios carry forward to Phase 3 (prepare) and Phase 4 (execute). At least one scenario (or an explicit "no UI-observable AC → N/A" determination) must exist before leaving Phase 2.

---

## Phase 3: prepare

<!-- OWNER: fn-53.3 — accounts, session hygiene, device matrix; BRB lean-borrow reference. -->

**Goal:** make the live app driveable before Phase 4 touches it — resolve the **target URL / app**, **test accounts**, **session hygiene**, and the **device matrix** (one desktop + one mobile viewport). The QA discipline this phase applies (the five hygiene rules, persona suffixing, the write-path-first / one-tab-per-shard caution) is the lean BRB borrow in **[references/qa-discipline.md](references/qa-discipline.md)** — read it before preparing. Ask the user (`plain-text numbered prompt`, info-only — never a confirm gate) when the URL or accounts are undocumented (R7). Under Ralph, an undocumented URL / accounts is a hard limitation → BLOCKED (Phase A), not a prompt.

**Driving stays fn-51's job.** This phase resolves *what to drive and as whom*; the concrete commands (set viewport, clear storage, save/load auth state) live in fn-51's references — point at them, never duplicate the prose:

- Viewport + screenshot: `flow-next-drive/references/commands.md` (`agent-browser set viewport W H`, `agent-browser screenshot …`)
- Per-session isolation (`--session`): `flow-next-drive/references/session-management.md`
- Auth / state persistence (`state save` / `state load`, header auth): `flow-next-drive/references/auth.md`

### 3.1 — Resolve the target URL / app

Find the live target a real user would hit, in this priority order. Stop at the first that resolves; do **not** silently default to `localhost`:

1. **Caller override** — a `--target <url>` flag or a `QA_TARGET_URL` env var, when present.
2. **Spec signal** — a deploy URL named in `spec.spec_sections.architecture_overview` / `goal_and_context` (Phase 1's payload).
3. **Repo signal** — a deploy URL in `README`, `.env.example`, or a deploy config (Vercel / Netlify / Cloudflare); or a documented dev-server URL + start command for a localhost run.
4. **Ask the user** (`plain-text numbered prompt`, info prompt — *"What URL should I QA — a live deploy or a local dev server?"*). Under Ralph this is a hard limitation → BLOCKED.

A target the driver cannot reach (no live deploy, no localhost app started) is **not** a Phase 3 failure — it carries forward to the Phase 6 **BLOCKED** outcome (R13 graceful surface), never a fabricated PASS.

### 3.2 — Resolve test accounts (ask when undocumented)

Most scenarios beyond the public happy path need credentials. Resolve them before authoring auth-dependent steps:

1. Look for a documented playbook — auth-provider dev mode, a seed script (`scripts/seed-*`, `db/seeds/`, `supabase/seed.sql`), fixtures (`__fixtures__/`, `test-data/`), or a `.env.test.example`.
2. If none is documented, **ask the user** (`plain-text numbered prompt`, info prompt): the auth provider / dev-user docs, an admin account (or permission to create one), and the per-run email-suffix convention. Offer to document the convention as part of the pass.
3. **Never guess credentials**, and never commit a password to the repo — record only the email pattern + role; pass secrets via the existing chat / vault. (Provider fixtures like Clerk's `424242` OTP or Stripe's `4242…` test card are out of this lean borrow's scope — reach for the provider's docs when a flow needs one.)

Generate fresh-user personas with the collision-proof suffix from `qa-discipline.md` — `qa-<persona>+run<MMDD>-<N>@example.com` (`example.com` never sends real mail; bump `N` on every retry).

### 3.3 — Session hygiene (the fresh-user contract)

Apply the **five hygiene rules** from [references/qa-discipline.md](references/qa-discipline.md) — they are the highest-dividend borrow:

1. **Fresh user = fresh storage** — clear `localStorage` + `sessionStorage` **and** cookies before any fresh-user scenario (cookies alone are not enough; storage outlives a logout).
2. **One session per agent** — isolate via agent-browser `--session <name>`; if isolation can't be guaranteed, run sequentially.
3. **Cool-down between auth attempts** (~30s; on a 429 → BLOCKED, do not retry-spam).
4. **Unique persona per scenario** (bump the `+run…-N` suffix on retry — a reused failed email leaves the provider stuck).
5. **Reset between role changes** — full sign-out + storage clear + tab reset, not just "click sign out".

Run the **pre-scenario hygiene checklist** (qa-discipline.md) for each scenario; the exact storage-clear / auth commands are fn-51's (`auth.md`, `session-management.md`). If, with perfect hygiene, behavior still depends on unpredictable prior session state, **that is the bug** — file it (typically P1), capturing the storage snapshot before clearing as evidence.

### 3.4 — Device matrix (v1 = viewport emulation only)

v1 covers **one desktop + one mobile viewport** via fn-51's web ladder — viewport **emulation**, not real-device / cross-device testing (the spec's planning decision; true device coverage inherits fn-51's surface support later):

| Mode | Reference viewport | Set via (fn-51) |
|------|--------------------|-----------------|
| Desktop | `1280 × 800` | `agent-browser set viewport 1280 800` |
| Mobile | `375 × 812` | `agent-browser set viewport 375 812` |

Lead with the app's **primary** target: take it from the spec; if the spec is silent, ask the user which mode matters most; if the user is unavailable (e.g. Ralph), infer the likely primary from repo signals (responsive CSS / framework defaults / marketing copy) and **note the assumption** in the run notes. Record the chosen viewports against each scenario so Phase 4 drives at the right size and the evidence tuple's `viewport` field is accurate. Layout / overflow / tap-target bugs hide at the breakpoint you skip — run the relevant scenarios at **both** viewports, not just the primary.

### 3.5 — Write-path-first ordering

When a later scenario reads data an earlier scenario creates (a group, org, workspace, invite), order the **write path first** so the artifact exists before any scenario that reads it; record the created IDs / invite URLs in the run notes for reuse. This is the caution in `qa-discipline.md` — v1 runs scenarios sequentially with one host agent, so it is an ordering rule, not a parallel coordinator. For any write path, Phase 4 must verify the **server / DB row or API response** (the write-side-effect evidence in [references/bug-filing.md](references/bug-filing.md)) — never trust the optimistic UI render.

After Phase 3, each scenario carries: its persona (+ suffix), its viewport(s), its fresh-vs-returning storage requirement, and the resolved target URL — everything Phase 4 needs to drive it via the fn-51 read-and-drive contract.

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

<!-- OWNER: fn-53.2 — structured P0/P1/P2 findings + evidence; feed the bug memory track. -->

**Goal:** file each failure as a structured P0/P1/P2 finding (persona, steps-to-reproduce, expected vs actual, evidence pointers), **filed immediately on FAIL** — not batched at the end. Findings feed the bug memory track via `memory add --track bug` (built-in overlap dedup — **never** `--no-overlap-check`) and carry the R-ID(s) they trace back to.

The full filing discipline (taxonomy, evidence rules, reproduce-before-file, the `memory add` invocation, dedup surfacing, promote-to-spec) lives in **[references/bug-filing.md](references/bug-filing.md)** — read it before filing. The flow on the host:

### 5.1 — Reproduce before you file (twice)

Agentic driving is non-deterministic. A single failed observation is not yet a finding. **Re-run the scenario's failing step a second time** (fresh `observe → snapshot → act → verify`, same persona/viewport). File only if it fails both times. A pass-on-retry is a flake — record it in the run notes (not a finding), and move on. This defends the verdict against false P0s (the GitHub-Eng gap: self-reported failure ≈82% accurate; reproduce-twice closes it with structural evidence).

### 5.2 — Severity (P0/P1/P2)

Assign from the taxonomy in [references/bug-filing.md](references/bug-filing.md):

- **P0** — blocks the core flow / data loss / security / crash: a real user cannot complete the scenario's goal.
- **P1** — major degradation with a workaround, or a wrong-but-recoverable result.
- **P2** — minor / cosmetic / edge polish.

**Tie-break (never downgrade to avoid stopping):** when between two severities, take the **higher** if it touches the core flow or data integrity. A single open P0 is a NO in Phase 6 — do **not** relabel a P0 as P1 to keep the verdict green. Severity rests on observed user impact, never on convenience.

### 5.3 — Capture the evidence pointers

Every finding cites **real captured evidence** (from Phase 4, under `.flow/tmp/qa-<spec-id>/`), never narration:

- **Console** — the last ~30 lines, verbatim (`.flow/tmp/qa-<spec-id>/<sid>-console.log`), referenced by path.
- **Screenshot** — path under `.flow/tmp/qa-<spec-id>/` at the moment of failure.
- **URL** — the full URL including query string at the point of failure.
- **Write side-effects** — for any write path (create/update/delete), the server/DB row or API response confirming the actual persisted state.

Evidence lives under `.flow/tmp/` (gitignored) and is **referenced by path**, never inlined into the receipt or memory body wholesale.

### 5.4 — File the finding to bug memory (immediately, with dedup)

On a confirmed FAIL, file at once via `memory add --track bug` **with overlap dedup left ON**. See [references/bug-filing.md](references/bug-filing.md) §"Filing to bug memory" for the full command and the finding body template. Skeleton:

```bash
# memory disabled → no-op cleanly (still record the finding in the run notes for the verdict).
if [ "$($FLOWCTL config get memory.enabled --json | jq -r '.value')" = "true" ]; then
 mkdir -p .flow/tmp/qa-"$SPEC_ID"
 # Write the finding body (problem / repro / expected-vs-actual / evidence pointers / R-IDs)
 # to .flow/tmp/qa-$SPEC_ID/finding-<sid>.md per the reference template, then:
 $FLOWCTL memory add \
 --track bug --category "<ui|runtime-errors|integration|data|...>" \
 --title "<persona> can't <goal> — <one-line symptom>" \
 --module "<surface / route / component>" \
 --tags "qa,<spec-id>,<surface>" \
 --symptoms "<observed actual>" \
 --root-cause "(observed via live QA — unconfirmed)" \
 --body-file .flow/tmp/qa-"$SPEC_ID"/finding-<sid>.md
 # NEVER pass --no-overlap-check. High overlap updates the existing entry in
 # place; moderate overlap creates a related_to cross-reference. Surface
 # "matches existing entry X" instead of re-filing on a re-run (idempotency).
fi
```

The `memory add` overlap check is the dedup mechanism (per `docs/memory-schema.md`): a re-run of QA does **not** re-file the same finding — it folds into the existing entry. Findings can be **promoted to a flow spec/task** for the fix (compose from `flowctl spec create` / `/flow-next:capture`) — that is the spec↔scenario↔finding↔R-ID loop closing; see the reference.

Track every finding's id and severity in a running list for Phase 6. **Read source to assert a PASS is forbidden (R1)** — but reading source to *explain* an already-evidenced failure (root-cause hint for the fix) is fine; the PASS gate is what's evidence-locked, not the post-hoc explanation.

---

## Phase 6: verdict

<!-- OWNER: fn-53.2 — YES/NO ship verdict + open P0/P1 list; emit the qa_verdict receipt. -->

**Goal:** end with a YES/NO ship verdict + the open P0/P1 list, emitted as a `type: qa_verdict` proof-of-work receipt. The verdict rests on **captured evidence** (Phase 4) and **filed findings** (Phase 5) — never on agent narration, never on reading the diff.

### 6.1 — Pick the `qa_outcome` (the four-outcome matrix)

QA has **four** distinct outcomes. Pick exactly one, in this precedence order:

1. **BLOCKED** — no live deploy reachable OR no driver available (incl. fn-51 degraded to the terminal manual rung). Could not verify. **BLOCKED ≠ FAIL** — it is "no ship *claim* on a QA basis," not "the app is broken." Set `blocked_reason`.
2. **NA** — the spec has **no driveable user-visible AC** (all backend/CLI/non-UI — like most of flow-next's own specs). Live QA raises no objection because there is nothing to drive. Set `na_reason`.
3. **NEEDS_WORK** — any open P0 or P1 finding, **OR** incomplete `live` coverage of a UI-observable R-ID (an honest gap is a NO, never a confident PASS). This is the NO outcome.
4. **SHIP** — all derived scenarios pass on the live app, **zero** open P0/P1, and the R-ID coverage spine is complete for every UI-observable criterion. The YES outcome.

**Honesty rules (load-bearing):**
- A **single open P0 = NEEDS_WORK.** Do not downgrade a P0 to P1 to avoid stopping (Phase 5.2 tie-break).
- **Incomplete R-ID coverage = NEEDS_WORK**, not SHIP — a `⚠️ no live scenario` row on a UI-observable R-ID is an uncovered gap.
- **SHIP is forbidden without captured live-app evidence (R1).** If you cannot point to a screenshot/console/observed-state artifact per passing scenario, the outcome is BLOCKED, never SHIP.

### 6.2 — Project `qa_outcome` → `verdict` (the Ralph-guard enum)

`ralph-guard.py` validates **only** `verdict ∈ {SHIP, NEEDS_WORK, MAJOR_RETHINK}` (`validate_receipt_data`). The four QA outcomes live in `qa_outcome`; `verdict` is the enum-compatible **projection**:

| `qa_outcome` | `verdict` | Rationale |
|--------------|-----------|-----------|
| `SHIP` | `SHIP` | all pass, zero open P0/P1, coverage complete |
| `NEEDS_WORK` | `NEEDS_WORK` | open P0/P1 or incomplete coverage |
| `BLOCKED` | `NEEDS_WORK` | could not verify → no ship claim on a QA basis |
| `NA` | `SHIP` | no driveable UI → live QA raises no objection (`na_reason` records why) |

QA never emits `MAJOR_RETHINK` — it is a valid enum member the guard accepts, but the QA matrix has no outcome that maps to it.

### 6.3 — Write the `qa_verdict` receipt (direct write — the make-pr pattern)

QA has **no review-backend subprocess**, so the receipt is written **directly** (the make-pr / impl-review-RP precedent — write the JSON yourself, **not** via a `flowctl <backend> validate --receipt` path). Resolve the path from the caller (`--receipt` flag or `REVIEW_RECEIPT_PATH`) else default to the committed `.flow/review-receipts/qa-<spec-id>.json`; `mkdir -p` the parent first.

**Build the JSON with `python3`, not a `cat <<EOF` heredoc.** `blocked_reason` / `na_reason` are free-form strings the agent fills from observed state (e.g. a driver error message) — raw shell interpolation into JSON would emit malformed output (or allow field injection) the moment a reason contains a quote, backslash, or newline. Passing the values as `os.environ` and serializing with `json.dump` escapes them correctly:

```bash
# QA_OUTCOME ∈ {SHIP,NEEDS_WORK,NA,BLOCKED} from §6.1; project to the enum (§6.2).
case "$QA_OUTCOME" in
 SHIP) VERDICT="SHIP" ;;
 NEEDS_WORK) VERDICT="NEEDS_WORK" ;;
 BLOCKED) VERDICT="NEEDS_WORK" ;;
 NA) VERDICT="SHIP" ;;
 *) echo "Internal error: bad qa_outcome '$QA_OUTCOME'" >&2; exit 1 ;;
esac

# MODE describes the run context (informational; the guard does not gate on it):
# ralph (REVIEW_RECEIPT_PATH set) | rp (--receipt passed) | interactive (default).
if [ -n "${REVIEW_RECEIPT_PATH:-}" ]; then MODE="ralph"
elif [ -n "${QA_RECEIPT_OVERRIDE:-}" ]; then MODE="rp"
else MODE="interactive"; fi

RECEIPT_PATH="${QA_RECEIPT_OVERRIDE:-${REVIEW_RECEIPT_PATH:-$REPO_ROOT/.flow/review-receipts/qa-$SPEC_ID.json}}"
mkdir -p "$(dirname "$RECEIPT_PATH")"

# OPEN_P0P1 = JSON array literal of open-P0/P1 finding ids from Phase 5; default "[]".
# Reason fields are set ONLY for their outcome (BLOCKED → blocked_reason, NA → na_reason);
# leave the others empty so python omits them.
export QA_TYPE="qa_verdict" QA_ID="$SPEC_ID" QA_MODE="$MODE" QA_VERDICT="$VERDICT" \
 QA_OUTCOME OPEN_P0P1="${OPEN_P0P1:-[]}" \
 BLOCKED_REASON="${BLOCKED_REASON:-}" NA_REASON="${NA_REASON:-}"

python3 - "$RECEIPT_PATH" <<'PY'
import datetime, json, os, sys
r = {"type": os.environ["QA_TYPE"], "id": os.environ["QA_ID"],
 "mode": os.environ["QA_MODE"], "verdict": os.environ["QA_VERDICT"],
 "qa_outcome": os.environ["QA_OUTCOME"],
 "open_p0p1": json.loads(os.environ["OPEN_P0P1"] or "[]")}
if os.environ["QA_OUTCOME"] == "BLOCKED" and os.environ.get("BLOCKED_REASON"):
 r["blocked_reason"] = os.environ["BLOCKED_REASON"] # json.dump escapes free-form text
if os.environ["QA_OUTCOME"] == "NA" and os.environ.get("NA_REASON"):
 r["na_reason"] = os.environ["NA_REASON"]
r["timestamp"] = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
with open(sys.argv[1], "w", encoding="utf-8") as fh:
 json.dump(r, fh); fh.write("\n")
PY
echo "QA_VERDICT_WRITTEN: $RECEIPT_PATH ($QA_OUTCOME → $VERDICT)"
```

The default path `.flow/review-receipts/qa-<spec-id>.json` is **committed** (the receipts dir is tracked); `.flow/tmp/` (evidence) is gitignored. A second QA pass **overwrites** the latest receipt (idempotent) — findings dedup against bug memory (Phase 5), the receipt reflects the latest run.

**There is NO generic `flowctl receipt write` helper** — compose the JSON as above. `qa-*.json` is not a path the Ralph guard's `parse_receipt_path` recognizes, so it validates via the plain verdict-enum check only (the planning decision: QA is **not** a hard Ralph receipt-gate in v1 — no `ralph-guard.py` change).

### 6.4 — Surface the verdict to the user

Print the YES/NO call, the `qa_outcome`, the open P0/P1 list (with finding ids + severities), and the R-ID coverage table (reused from Phase 2.2, now annotated with pass/fail per scenario). The verdict is shaped to feed `spec-completion-review` ("does the *live app* satisfy the AC, not just the code") — documented-only in v1; completion-review does not yet read the qa receipt.

---

## Phase A: autonomy

<!-- OWNER: fn-53.4 — Ralph-aware-not-blocked detect-once; opt-in tracker.perEvent.qa; graceful degradation. -->

**Goal:** detect Ralph **once** and route deterministically (R11) — autonomous when the target URL + test accounts are configured (emits the verdict receipt, no prompts); asks the user (info-only) when they are undocumented. The skill is **not a hard Ralph-block** — there is **no** top-of-skill `FLOW_RALPH` exit-2 guard (the make-pr §0.0 precedent; see [SKILL.md](SKILL.md) Forbidden). Phase A also owns the opt-in tracker verdict post (`tracker.perEvent.qa`) and the graceful-degradation contract when no live deploy / driver is present. The full routing table, gating predicate, and degradation matrix live in **[references/autonomy.md](references/autonomy.md)** — read it before any Ralph or tracker step.

### A.1 — Detect Ralph once, route deterministically (R11)

Detect at the top of the run, then route downstream — never re-probe per phase (the make-pr §0.0 pattern):

```bash
RALPH=0
if [ -n "${REVIEW_RECEIPT_PATH:-}" ] || [ "${FLOW_RALPH:-}" = "1" ]; then
 RALPH=1
fi
```

- **No top-of-skill exit guard.** `RALPH=1` does **not** abort the skill. QA runs in Ralph; it just routes differently (the make-pr precedent — autonomous loops emitting a QA verdict is the intended use). Do **not** add a `FLOW_RALPH`/`REVIEW_RECEIPT_PATH` exit-2 guard.
- **`plain-text numbered prompt` is info-only, never a confirm gate.** It resolves *undocumented* facts (target URL, test accounts — Phases 1.1, 3.1, 3.2), never "shall I run QA? / ship?". Interactive asks; Ralph cannot ask, so an undocumented URL/accounts under Ralph is a **hard limitation → BLOCKED** (Phase 6, `blocked_reason`), not a prompt and not an exit.
- **Autonomous path:** target URL + test accounts configured (spec / config / env) → derive → drive → file → emit the `qa_verdict` receipt to the caller-supplied `--receipt` / `REVIEW_RECEIPT_PATH` (Phase 6.3), zero prompts. The verdict path is identical to interactive; only the prompt-vs-BLOCKED branch on *undocumented* inputs differs.

### A.2 — Graceful degradation (R13)

No live deploy reachable, OR no driver available (incl. fn-51 degraded to its terminal manual rung per [flow-next-drive/SKILL.md](../flow-next-drive/SKILL.md) "Driver detection & graceful degradation") → surface the limitation as a **BLOCKED** verdict (Phase 6.1 / the §4.2 BLOCKED proof receipt), add **nothing** to the base flow, exit clean. Inherit fn-51's degradation table — do not re-derive it. BLOCKED ≠ FAIL: it is "no ship *claim* on a QA basis," never a fabricated PASS and never a hard error.

### A.3 — Opt-in tracker verdict post (`tracker.perEvent.qa`, R9)

After the Phase 6 verdict is written, optionally post it as a structured tracker comment — gated identically to every other lifecycle touchpoint (fn-52 pattern; see [flow-next-work/SKILL.md](../flow-next-work/SKILL.md) "Shared gating predicate"). Runs ONLY when the bridge is active AND the leaf is opted in; otherwise a silent no-op. **Best-effort** — a tracker failure never blocks the verdict:

```bash
QA_LEAF="$($FLOWCTL config get tracker.perEvent.qa --json | jq -r '.value')"
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
 && [ "$QA_LEAF" != "off" ] && [ "$QA_LEAF" != "null" ]; then
 # comment is the ONLY sensible verb for a QA verdict — post it as a tracker
 # comment via the flow-next-tracker-sync skill. Any non-`off` value (a stray
 # push/pull/reconcile) is treated as comment, never as a body/status op.
 # The verdict + qa_outcome + open-P0/P1 list compose the comment body.
 : # invoke flow-next-tracker-sync (comment op, best-effort — never blocks)
fi
```

The leaf accepts `off` | `comment` (default `off`). `comment` is the only verdict-meaningful verb; treat any other non-`off` value as `comment` (never `push`/`pull`/`reconcile`). The actual transport / comment dedup / receipt lives entirely in the **flow-next-tracker-sync** skill — Phase A only gates + delegates.
