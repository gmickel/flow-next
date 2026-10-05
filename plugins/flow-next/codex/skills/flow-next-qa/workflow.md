# /flow-next:qa workflow

Run the phases in order. Stop on a user-blocking error rather than continuing with bad state, and
never invent evidence to keep going. Every path, including no target and no driver, ends with the
receipt in §6.3.

## Preamble

```bash
set -e
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
```

Needs `jq` and `git`. `SPEC_ID`, `NO_PROMPT` and the overrides come from SKILL.md. Without a
`.flow/` directory, print `No .flow/ directory — /flow-next:qa runs inside a flow-next-managed repo.`
and exit 1.

Questions below are info prompts for undocumented facts, never "shall I run / ship?" gates. With
`NO_PROMPT=1` nothing is asked:

| Fact | Interactive | Autonomous |
|------|-------------|------------|
| Spec id (1.1) | ask | branch match only; else error exit |
| Base ref (1.2) | ask | BLOCKED |
| Target URL (3.1) | ask | BLOCKED |
| Test accounts (3.2) | ask | BLOCKED |

BLOCKED here means: set `QA_OUTCOME=BLOCKED` and a `BLOCKED_REASON`, go straight to §6.3, write
the receipt and exit cleanly.

---

## Phase 1: discover

### 1.1 Spec id

When `SPEC_ID` is empty: read [references/spec-from-branch.md](references/spec-from-branch.md) and
resolve it as it says. Then confirm it is a spec, not a task:

```bash
$FLOWCTL show "$SPEC_ID" --json | jq -e '.tasks != null' >/dev/null \
  || { echo "Not a spec: $SPEC_ID (QA runs against a spec, not a single task)." >&2; exit 1; }
```

### 1.2 Base and the spec payload

The base is `QA_BASE_REF` when given, else the first ref that resolves:

```bash
DEFAULT_BRANCH="${QA_BASE_REF:-}"
for candidate in origin/main main origin/master master; do
  [[ -n "$DEFAULT_BRANCH" ]] && break
  if git -C "$REPO_ROOT" rev-parse --verify --quiet "$candidate" >/dev/null 2>&1; then DEFAULT_BRANCH="$candidate"; fi
done
if [[ -z "$DEFAULT_BRANCH" ]]; then   # a default branch not named main/master
  git -C "$REPO_ROOT" symbolic-ref --quiet refs/remotes/origin/HEAD >/dev/null 2>&1 \
    || git -C "$REPO_ROOT" remote set-head origin -a >/dev/null 2>&1 || true
  ORIGIN_HEAD="$(git -C "$REPO_ROOT" symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || true)"
  if git -C "$REPO_ROOT" rev-parse --verify --quiet "$ORIGIN_HEAD" >/dev/null 2>&1; then DEFAULT_BRANCH="$ORIGIN_HEAD"; fi
fi
```

If nothing resolved: ask for the base ref, or under `NO_PROMPT=1` go BLOCKED with
`BLOCKED_REASON="no base branch detected — pass an explicit --base"`. Otherwise validate the ref
and load the payload once:

```bash
git -C "$REPO_ROOT" rev-parse --verify --quiet "$DEFAULT_BRANCH" >/dev/null \
  || { echo "Base ref '$DEFAULT_BRANCH' is not a valid git ref." >&2; exit 1; }
BASE_REF="$(git -C "$REPO_ROOT" merge-base "$DEFAULT_BRANCH" HEAD 2>/dev/null || echo "$DEFAULT_BRANCH")"
PAYLOAD="$($FLOWCTL spec export-cognitive-aid "$SPEC_ID" --base "$BASE_REF" --json)"
```

`$PAYLOAD` is the only source for Phase 2; do not export again. `spec.spec_sections` holds
`acceptance_criteria[]` (`{id, text, tag}`), `boundaries[]`, `decision_context[]`
(`{question, answer}`), `goal_and_context` and `architecture_overview`. The top-level `tasks[]`
holds each task's `satisfies` and `evidence` (`{commits, tests, files_touched}`). The task objects
in `flowctl show <spec>` carry neither, so never decide subtraction from them.

Empty `acceptance_criteria`: nothing to drive; the outcome is NA.

### 1.3 Feature map

When `.flow/features/` exists, follow "Live-app stages" in
[feature-entry-contract.md](../flow-next-features/references/feature-entry-contract.md) and load
only the matching feature file. The map supplies navigation only; scenarios still come from the
spec and SHIP still rests on live evidence. A map that does not cover this target (no matching
surface or feature, or a malformed entry) counts as absent for that target: derive routes as usual.

### Autonomous preflight

Under `NO_PROMPT=1`, resolve the target (§3.1) and accounts (§3.2) now. A missing target, or
missing accounts that scenarios need, goes BLOCKED immediately with empty coverage. A public-only
target needs no account.

---

## Phase 2: derive

### 2.0 Subtract what work already proved

Skip the live run for an R-ID only when **all three** hold; otherwise keep it live:

1. A `tasks[]` entry's `satisfies` lists this R-ID.
2. That task's `evidence.tests` holds a specific, re-runnable command tied to this criterion
   (`pnpm test src/foo.test.ts`, a named unittest). A broad command (`pnpm test`, `make`,
   `npm run build`) proves no specific criterion.
3. The criterion is statically verifiable (a pure function, a build gate, a CLI exit code with a
   deterministic test). Anything observable in the running app (a UI flow, rendered state, a
   request round-trip, an external integration) is always live, even if a task says it is done.

`files_touched`, `commits`, `prs` and any "I verified X" narration never subtract. With no task
evidence, nothing subtracts. When in doubt, keep it live.

### 2.1 Build the scenarios

When 1.3 loaded a feature, scenario steps use its routes and commands.

1. **Criteria to scenarios.** Each user-observable criterion gets at least one scenario: persona,
   goal, the steps a real user takes, and the expected result. Backend/CLI criteria get none;
   mark them `backend/CLI — not live-QA-able`. Every write-path scenario also gets an error-path
   variant (invalid input, empty, error or permission state).
2. **Boundaries** are non-goals: never test them, and never file a "missing" feature a boundary
   excludes.
3. **Decision context** supplies the expected behaviour for the scenarios it governs.
4. **Prior bugs.** Search `$FLOWCTL memory search "<surface or module>" --track bug` for the
   touched surfaces and add a `regression` scenario (no R-ID; it does not count toward coverage)
   for each prior bug that still plausibly applies, unless a boundary excludes it or the diff
   removed the code.

### 2.2 Coverage table

One row per `acceptance_criteria[].id`, in spec order, never renumbered:

```markdown
| R-ID | Acceptance criterion | Scenario(s) | Coverage |
|------|----------------------|-------------|----------|
| R1 | <criterion text, ≤120 chars + … if truncated> | S1, S2 | live |
| R3 | <…> | — | ⚠️ no live scenario |
| R7 | <…> | — | backend/CLI — not live-QA-able |
| R9 | <…> | — | subtracted (fn-1.2 · test_x) |
```

Coverage is exactly one of `live`, `subtracted (<task-id> · <test-cmd>)` (all three §2.0
conditions held), `backend/CLI — not live-QA-able`, or `⚠️ no live scenario` (user-observable but
not covered: a gap). A runtime or UI criterion is never `subtracted`.

---

## Phase 3: prepare

Resolve what to drive and as whom. The driving commands (viewport, storage clearing, sessions,
auth state) are flow-next-drive's: `../flow-next-drive/references/commands.md`,
`session-management.md` and `auth.md`.

### 3.1 Target

First that resolves; never assume `localhost` silently:

1. `QA_TARGET_URL` (from `--target` or the environment).
2. A deploy URL in the spec's `architecture_overview` or `goal_and_context`.
3. A deploy URL in the README, `.env.example` or deploy config, or a documented dev-server URL and
   start command.
4. Ask which URL to test (a deploy or a local dev server); under `NO_PROMPT=1`, BLOCKED.

A target that turns out unreachable is not a failure here; it becomes BLOCKED in Phase 4.

### 3.2 Test accounts

When a scenario needs to sign in, use the documented way (auth dev mode, seed script, fixtures,
`.env.test.example`). If none is documented, ask; under `NO_PROMPT=1`, scenarios that cannot run
without an account make the outcome BLOCKED. Never guess credentials and never commit a password.
When a scenario needs an account or a fresh-user persona, read
[references/prepare-surface.md](references/prepare-surface.md).

### 3.3 Session hygiene

Stale session state causes false failures and hides real ones. Before each scenario:

- A fresh-user scenario starts with cleared cookies, `localStorage` and `sessionStorage`, signed out.
- One isolated browser session per agent (`--session`); when isolation is not guaranteed, run
  scenarios sequentially.
- Leave about 30s between auth attempts. On a rate limit (429), stop that scenario and treat it as
  blocked; do not retry.
- Each scenario gets its own persona; switching role means sign out, clear storage, new session.

If behaviour still depends on hidden prior state with clean hygiene, that is a bug (usually P1):
capture the storage contents before clearing them as its evidence.

### 3.4 Viewports and order

On a web surface, run at one desktop (1280×800) and one mobile (375×812) viewport (emulation),
leading with the spec's primary target. If the spec does not say, infer it from the repo and note
the assumption; never ask, since both run either way. Layout bugs hide at the size you skip, so run the
relevant scenarios at both. The viewport never blocks the run.

Run write paths first when later scenarios read what they create, and note the created ids.

---

## Phase 4: execute

QA does not re-implement driving. Read [flow-next-drive](../flow-next-drive/SKILL.md) and the
reference for the driver it resolves, and run its flow yourself for each scenario: observe,
snapshot fresh refs, act, verify (including console and failed requests), capture. Do not copy
driver command detail into QA notes or findings.

For each scenario, save a screenshot and the console output at the moment that matters under
`.flow/tmp/qa-<spec-id>/`, and record `{driver_rung, target_url, viewport, screenshot_path,
console_path}`. Evidence is referenced by path, never inlined wholesale into the receipt or a
memory body. For a write path, confirm the persisted result (server or DB row, API response),
not the optimistic UI.

No reachable target, or no driver beyond flow-next-drive's manual last rung: set
`QA_OUTCOME=BLOCKED` with `BLOCKED_REASON` (`no live deploy reachable` or `no driver available`)
and go to §6.3. Never stop without the receipt: `flow --auto` strikes a spec that has none.

---

## Phase 5: file

When a scenario fails, run the failing step once more (fresh snapshot, same persona and viewport).
File only if it fails both times; a pass on retry is a flake for the run notes.

Severity comes from what the user experiences:

- **P0**: the user cannot finish the scenario's goal; data loss, security, crash.
- **P1**: broken or wrong with a workaround, or a recoverable wrong result.
- **P2**: cosmetic, edge polish, accessibility, console noise.

Between two levels, take the higher when the core flow or data integrity is involved. Never
lower a P0 to keep the verdict green.

Each finding carries persona, steps to reproduce, expected (quoted from the spec) and actual, and
its evidence: screenshot path, console path (last ~30 lines), full URL, and for a write path the
persisted result. File it at once, before the next scenario. **Before filing the first finding,
read [references/bug-filing.md](references/bug-filing.md)**; it has the body template and the
filing commands. Filing keeps overlap scoring on; never pass `--no-overlap-check`. Add each filed
entry's path to `QA_FILED_MEMORY`. With memory disabled, record the finding in the run notes; it
still counts.

Keep every finding, P2 included, for the receipt: `id`, `severity`, `confidence`
(`0|25|50|75|100`), `classification` (`introduced|pre_existing`), `reason`, and `file` (the
surface or file).

### 5.5 Stale mapped routes

When a mapped route does not match the live app: that is a drift note, never a P0/P1/P2 finding,
and `.flow/features/` is never edited. Read [references/drift-notes.md](references/drift-notes.md)
to record it, then keep testing the criterion by another route.

---

## Phase 6: verdict

### 6.1 Outcome

Pick the first that applies:

1. **BLOCKED**: no reachable target, no driver, or the scenarios need data only a CI or staging
   environment holds. Could not verify; not a failure of the app.
   Set `blocked_reason`.
2. **NA**: no criterion is user-observable. Set `na_reason`.
3. **NEEDS_WORK** (NO): any open P0 or P1, or a `⚠️ no live scenario` row.
4. **SHIP** (YES): every scenario passed on the live app, no open P0/P1, and every user-observable
   R-ID is `live` or `subtracted`.

### 6.2 Evidence check

A SHIP with nothing captured is not a SHIP:

```bash
if [[ "$QA_OUTCOME" == "SHIP" ]]; then
  EVIDENCE_COUNT="$(find ".flow/tmp/qa-${SPEC_ID}" -maxdepth 1 -type f \( -name '*.png' -o -name '*.log' \) 2>/dev/null | wc -l | tr -d ' ')"
  if [[ "${EVIDENCE_COUNT:-0}" -eq 0 ]]; then
    QA_OUTCOME="BLOCKED"
    BLOCKED_REASON="SHIP claimed without captured live-app evidence — no screenshot/console artifact under .flow/tmp/qa-${SPEC_ID}/ (PASS rests on evidence, never narration)"
  fi
fi
```

### 6.3 — Write the receipt

Write the JSON payload with the Write tool to `$QA_RECEIPT_INPUT` (shape:
`$FLOWCTL qa receipt --skeleton`): `id`, `qa_outcome`, every Phase 5 finding under `findings`,
`rid_coverage.rids` (`[{id, coverage}]`, coverage one of `live`, `subtracted`,
`no_live_scenario`, `backend_cli`), and `blocked_reason` or `na_reason` for those outcomes only.
Set `mode` to `receipt` when the caller passed `--receipt` or set `REVIEW_RECEIPT_PATH`, otherwise
`interactive`; left out, it becomes `receipt`, because the call below always passes `--receipt`.

```bash
RECEIPT_PATH="${QA_RECEIPT_OVERRIDE:-${REVIEW_RECEIPT_PATH:-$REPO_ROOT/.flow/review-receipts/qa-$SPEC_ID.json}}"
$FLOWCTL qa receipt --from-json "$QA_RECEIPT_INPUT" --receipt "$RECEIPT_PATH" --json
```

The verb adds `type: qa_verdict`, the projected `verdict` (SHIP and NA become `SHIP`;
NEEDS_WORK and BLOCKED become `NEEDS_WORK`), `head_sha`, `branch`, coverage counts, `open_p0p1`,
the timestamp and prior-finding status. On a validation error it lists every problem and leaves
the old receipt in place: fix the payload and rerun; never drop findings. A later pass overwrites
the receipt.

### 6.3b Commit (autonomous only)

Only when `QA_AUTONOMOUS=1`: read [references/autonomous-commit.md](references/autonomous-commit.md)
and run its commit. An interactive run leaves commits to the user.

### 6.4 Report

Print the YES/NO call with `qa_outcome` (and its reason), the open P0/P1 findings with ids,
severities and one-line symptoms, the coverage table marked pass/fail per scenario, and what to
re-test after a fix. On NO or BLOCKED this should be enough for a fresh session to pick up.

### 6.5 Tracker post (opt-in)

```bash
ACTIVE=0
# NO pipelines in the probe — a failed producer masked by a healthy consumer
# fails CLOSED. Capture raw first, rc-checked; parse separately.
RAW="$($FLOWCTL config get tracker.perEvent.qa --json 2>/dev/null)" || ACTIVE=1   # probe ERROR ⇒ ACTIVE (fail open)
if [ "$ACTIVE" = "0" ]; then
  QA_LEAF="$(printf '%s' "$RAW" | jq -r '.value' 2>/dev/null)" || ACTIVE=1        # parse ERROR ⇒ ACTIVE
  [ "$QA_LEAF" != "off" ] && [ "$QA_LEAF" != "null" ] && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
  echo "TRACKER QA LEAF ACTIVE — STOP. Read references/autonomy.md#tracker-verdict-post and execute it before finishing."
fi
```

When it prints, read [references/autonomy.md](references/autonomy.md) and post the verdict as a
comment whose first line is `evidence=<tested-head-sha>`. Otherwise (the default `off`) nothing
is posted. The post is best-effort and never changes the receipt.

### Before you finish

- One receipt exists at `RECEIPT_PATH` with `qa_outcome`, `verdict`, `head_sha`, `branch`,
  `rid_coverage` and `open_p0p1`, whatever the outcome.
- Every criterion is a coverage row; no runtime or UI criterion is `subtracted`.
- Every filed finding was reproduced twice and cites real evidence.
- Under `NO_PROMPT=1`, nothing was asked.
