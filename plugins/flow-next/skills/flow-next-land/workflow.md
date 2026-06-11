# /flow-next:land workflow

Execute these phases in order. One invocation is one tick: discover authored PRs, classify each through the gate tree, take at most ONE action class per PR, and end with the terminal verdict line.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

Shared shell context for the workflow:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TODAY="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
NOW_EPOCH="$(date -u +%s)"
ORIG_BRANCH="$(git -C "$REPO_ROOT" branch --show-current)"
```

`jq`, `git`, and `gh` must be on PATH; confirm `gh auth status >/dev/null 2>&1` up-front (failure → `LAND_VERDICT=NEEDS_HUMAN prs=0 pr=- reason="gh not authenticated"`). `LAND_DRY_RUN` comes from SKILL.md Mode Detection. gh surfaces below are verified against gh 2.93.0.

## Phase 0 — Guards, config, ledger

Hard-stop when land is invoked under the Ralph harness. Emit the parseable terminal failure and act on nothing:

```bash
if [[ -n "${FLOW_RALPH:-}" || -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
  echo "Ralph and land are alternative drivers — never nest them" >&2
  echo 'LAND_VERDICT=NEEDS_HUMAN prs=0 pr=- reason="nested under Ralph harness (FLOW_RALPH/REVIEW_RECEIPT_PATH set) — refuse to run"'
  exit 1
fi
```

Refuse a dirty non-`.flow/` tree at tick start. Leave state untouched for diagnosis:

```bash
if git -C "$REPO_ROOT" status --porcelain | grep -v '^.. \.flow/' >/dev/null; then
  echo "Evidence: dirty non-.flow working tree at tick start"
  git -C "$REPO_ROOT" status --porcelain | grep -v '^.. \.flow/' || true
  echo 'LAND_VERDICT=NEEDS_HUMAN prs=0 pr=- reason="dirty working tree at tick start"'
  exit 0
fi
```

Read the `land.*` config. fn-60.2 seeds defaults, but tolerate `null` (pre-seed flowctl copies) with hard fallbacks:

```bash
cfg() { "$FLOWCTL" config get "$1" --json 2>/dev/null | jq -r '.value'; }
LAND_RELEASE="$(cfg land.release)";                  [[ -z "$LAND_RELEASE" || "$LAND_RELEASE" == "null" ]] && LAND_RELEASE=true
PATIENCE_MIN="$(cfg land.patienceMinutes)";          [[ -z "$PATIENCE_MIN" || "$PATIENCE_MIN" == "null" ]] && PATIENCE_MIN=30
REVIEW_SIGNAL="$(cfg land.reviewSignal)";            [[ -z "$REVIEW_SIGNAL" || "$REVIEW_SIGNAL" == "null" ]] && REVIEW_SIGNAL=silence
AUTOMATED_REVIEWERS="$(cfg land.automatedReviewers)"; [[ "$AUTOMATED_REVIEWERS" == "null" ]] && AUTOMATED_REVIEWERS=""
CI_FIX_BUDGET="$(cfg land.ciFixBudget)";             [[ -z "$CI_FIX_BUDGET" || "$CI_FIX_BUDGET" == "null" ]] && CI_FIX_BUDGET=3
```

Resolve the land ledger — READ-ONLY here (a missing file reads as `{}`; nothing is created or written until an ACT/REPORT write site, so `--dry-run` leaves the filesystem untouched). It lives under the git common dir so it is shared across worktrees and cannot be swept into commits by `git add -A`:

```bash
LEDGER_DIR="$(git -C "$REPO_ROOT" rev-parse --git-common-dir)/flow-next"
LEDGER="$LEDGER_DIR/land-strikes.json"
LEDGER_JSON="$(cat "$LEDGER" 2>/dev/null || echo '{}')"
```

Ledger schema, keyed by PR URL: `{"<pr-url>": {"ci_fix_count": <n>, "rerun_count": <n>, "decision_at_push": "<APPROVED|...|->", "land_pushed_sha": "<sha|->", "ts": "<iso8601>"}}`. It is skill-owned scratch; no flowctl plumbing. Every write site runs `mkdir -p "$LEDGER_DIR"` plus `[ -s "$LEDGER" ] || echo '{}' > "$LEDGER"` first, then writes atomically with `jq` plus `mv`.

## Phase 1 — DISCOVER

Land only babysits PRs whose authoring spec has ALL tasks done (pilot still owns in-flight specs — the pilot-concurrency interlock). Candidates from the minimal listing:

```bash
SPECS_JSON="$($FLOWCTL specs --json)"
CANDIDATE_SPECS="$(printf '%s\n' "$SPECS_JSON" | jq -r '.specs[] | select(.status == "open" and .tasks > 0 and .tasks == .done) | .id')"
```

For each candidate spec, resolve its branch and probe gh (`--state all` because a bare OPEN-only probe hides the merged-but-unclosed re-entry case, and `gh pr view` returns rc 0 for CLOSED/MERGED — the fn-42 finding — so always filter on `.state` via jq):

```bash
SPEC_JSON="$($FLOWCTL show "$spec" --json)"
BRANCH_NAME="$(printf '%s\n' "$SPEC_JSON" | jq -r '.branch_name // empty')"
[[ -z "$BRANCH_NAME" ]] && continue   # no branch contract → not build-loop-authored

PR_PROBE_FAILED=0
PR_JSON="$(gh pr list --head "$BRANCH_NAME" --state all --json url,state,number,isDraft --limit 20 2>/dev/null)" || PR_PROBE_FAILED=1
OPEN_PRS="$(printf '%s\n' "${PR_JSON:-[]}" | jq -c '[.[] | select(.state == "OPEN")]')"
OPEN_COUNT="$(printf '%s\n' "$OPEN_PRS" | jq 'length')"
MERGED_PR_NUM="$(printf '%s\n' "${PR_JSON:-[]}" | jq -r '[.[] | select(.state == "MERGED")][0].number // empty')"
```

Discovery outcomes per spec:

- gh probe failed (missing, unauthenticated, API error): per-PR-class `NEEDS_HUMAN` entry for this spec, reason `gh probe failed`; never guess.
- `OPEN_COUNT > 1`: two open PRs on one spec branch → `NEEDS_HUMAN` entry, no mutation.
- `OPEN_COUNT == 1` AND a MERGED PR also exists for the branch: ambiguous reopened/re-pushed state → `NEEDS_HUMAN` entry, no mutation.
- `OPEN_COUNT == 1`: babysit path → `PR_NUMBER="$(printf '%s\n' "$OPEN_PRS" | jq -r '.[0].number')"`, then the authorship check (below) → babysit candidate.
- `OPEN_COUNT == 0` and `MERGED_PR_NUM` non-empty: the spec is merged-but-unclosed → `PR_NUMBER="$MERGED_PR_NUM"`, then the authorship check → **re-entry candidate** (resume the post-merge tail: close → tracker → release; never a second merge).
- `OPEN_COUNT == 0` and no MERGED PR (no PR, or CLOSED-without-merge only): not land's work — skip silently (pilot owns the no-PR state; a closed-unmerged PR is human-rejected work land must not resurrect).

**Authorship requires BOTH signals before any mutation** (a hand-opened PR on a spec branch must not be auto-merged): the branch match above AND the make-pr breadcrumb in the PR body. `PR_NUMBER` MUST have been assigned by the outcome branch above (babysit: the single open PR's number; re-entry: `MERGED_PR_NUM`) — never reuse a prior loop iteration's value.

The breadcrumb probe is **markup-agnostic**: the canonical make-pr footer is italicized, wraps the command in backticks, and renders the spec id as a link (make-pr workflow §2.13b "Footer breadcrumb"), so matching one exact plain phrase would never succeed. Instead require the body to contain BOTH the `flow-next:make-pr` token AND the spec id:

```bash
PR_BODY="$(gh pr view "$PR_NUMBER" --json body --jq .body 2>/dev/null || true)"
if printf '%s' "$PR_BODY" | grep -qF "flow-next:make-pr" \
   && printf '%s' "$PR_BODY" | grep -qF "$spec"; then
  AUTHORED=1
else
  # branch-only match → report NEEDS_HUMAN for this PR, never act on it
  AUTHORED=0
fi
```

Zero candidates (no babysit, no re-entry, no NEEDS_HUMAN discovery entries) ends the tick:

```text
LAND_VERDICT=NO_WORK prs=0 pr=- reason="no open build-loop-authored PRs"
```

Echo the discovery table: candidate specs, branch, PR number/state, authorship result, classification.

## Phase 2 — GATE (per PR, read-only)

Classify every discovered PR before acting on any. This phase performs reads only — no checkout, no push, no label, no ledger write. Each PR gets a planned action class + provisional verdict. Process PRs serially in stable spec-id order.

Fetch the gate state in one call per PR:

```bash
PR_STATE="$(gh pr view "$PR_NUMBER" --json url,number,state,isDraft,mergeStateStatus,reviewDecision,headRefOid,baseRefName,labels,commits)"
PR_URL="$(printf '%s\n' "$PR_STATE" | jq -r '.url')"
HEAD_OID="$(printf '%s\n' "$PR_STATE" | jq -r '.headRefOid')"
BASE_REF="$(printf '%s\n' "$PR_STATE" | jq -r '.baseRefName')"
IS_DRAFT="$(printf '%s\n' "$PR_STATE" | jq -r '.isDraft')"
MERGE_STATE="$(printf '%s\n' "$PR_STATE" | jq -r '.mergeStateStatus')"
REVIEW_DECISION="$(printf '%s\n' "$PR_STATE" | jq -r '.reviewDecision // ""')"
OWNER_REPO="$(gh repo view --json owner,name --jq '.owner.login + "/" + .name')"
```

### 2.1 — Durable-label skip (first gate)

```bash
HAS_NH_LABEL="$(printf '%s\n' "$PR_STATE" | jq -r '[.labels[].name] | index("flow-next:needs-human") != null')"
```

`true` → verdict `NEEDS_HUMAN`, action `none`, reason `durable flow-next:needs-human label present — skipped`. No further gates for this PR (the label survives sessions; a human removes it to re-enroll the PR).

### 2.2 — Re-entry candidates

A merged-but-unclosed spec (from DISCOVER) plans action `resume-tail` directly — no CI/review gates apply to a merged PR. Provisional verdict `MERGED` (upgraded to `RELEASED` if the tail's release step runs).

### 2.3 — Patience-window anchor

Anchored to the LAST PUSH, never `createdAt` — a land-authored CI-fix push restarts the window:

```bash
LAST_PUSH="$(printf '%s\n' "$PR_STATE" | jq -r '.commits[-1].committedDate // empty')"
if [[ -z "$LAST_PUSH" ]]; then
  # Fallback: REST head sha → commit pushedDate via GraphQL
  HEAD_SHA="$(gh api "repos/$OWNER_REPO/pulls/$PR_NUMBER" --jq '.head.sha')"
  LAST_PUSH="$(gh api graphql -f query='query($owner:String!,$repo:String!,$oid:GitObjectID!){repository(owner:$owner,name:$repo){object(oid:$oid){... on Commit{pushedDate committedDate}}}}' \
    -f owner="${OWNER_REPO%/*}" -f repo="${OWNER_REPO#*/}" -F oid="$HEAD_SHA" \
    --jq '.data.repository.object.pushedDate // .data.repository.object.committedDate')"
fi
PUSH_EPOCH="$(printf '%s' "$LAST_PUSH" | jq -Rr 'fromdateiso8601' 2>/dev/null || echo "$NOW_EPOCH")"
AGE_MIN=$(( (NOW_EPOCH - PUSH_EPOCH) / 60 ))
WINDOW_ELAPSED=$(( AGE_MIN >= PATIENCE_MIN ? 1 : 0 ))
```

### 2.4 — CI tri-state (ALL checks, never `--required`)

Gate on ALL checks — required-only ignores failing optional CI and deadlocks on repos with no required checks:

```bash
CHECKS_RC=0
CHECKS_JSON="$(gh pr checks "$PR_NUMBER" --json bucket,name,link 2>/dev/null)" || CHECKS_RC=$?
[[ -z "$CHECKS_JSON" ]] && CHECKS_JSON='[]'
CHECK_TOTAL="$(printf '%s\n' "$CHECKS_JSON" | jq 'length')"
CHECK_FAILS="$(printf '%s\n' "$CHECKS_JSON" | jq '[.[] | select(.bucket == "fail" or .bucket == "cancel")] | length')"
CHECK_PENDING="$(printf '%s\n' "$CHECKS_JSON" | jq '[.[] | select(.bucket == "pending")] | length')"
```

Tri-state classification (gh buckets are `pass`, `fail`, `pending`, `skipping`, `cancel`; exit code 8 = checks pending):

| Observation | CI state |
|---|---|
| `CHECK_FAILS > 0` (`fail` or `cancel` bucket) | **red** → plan `ci-fix` (budget check in 2.7) |
| `CHECK_PENDING > 0` or `CHECKS_RC == 8` | **pending** → wait; NOT a fix trigger, NOT green |
| `CHECK_TOTAL == 0` and window NOT elapsed | **pending** — checks have not registered after the push yet; never treat empty as success |
| `CHECK_TOTAL == 0` and window elapsed | `NEEDS_HUMAN`, reason `no checks registered beyond the patience window` |
| every bucket ∈ {`pass`, `skipping`} (and `CHECK_TOTAL > 0`) | **green** → continue to review gates |

CI pending → verdict `AWAITING_REVIEW`, action `none`, reason `CI pending (<n> checks)`. Only green proceeds.

### 2.5 — Unresolved review threads

Same GraphQL surface as resolve-pr's fetch (first 100 covers the gate question "are there ANY unresolved"; resolve-pr itself paginates fully when dispatched):

```bash
UNRESOLVED="$(gh api graphql \
  -f query='query($owner:String!,$repo:String!,$pr:Int!){repository(owner:$owner,name:$repo){pullRequest(number:$pr){reviewThreads(first:100){nodes{isResolved}}}}}' \
  -f owner="${OWNER_REPO%/*}" -f repo="${OWNER_REPO#*/}" -F pr="$PR_NUMBER" \
  --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved | not)] | length')"
```

`UNRESOLVED > 0` with green CI → plan `resolve` (dispatch resolve-pr in ACT), provisional verdict `RESOLVING`.

### 2.6 — Review signal (`land.reviewSignal`)

Review bots (e.g. chatgpt-codex-connector) post COMMENTED reviews and never APPROVE; `reviewDecision` will not reflect them. An **automated reviewer** is a review author whose login ends in `[bot]` (REST form — fetch reviews via REST so bot logins carry the suffix), or any login in the `land.automatedReviewers` csv:

```bash
REVIEW_LOGINS="$(gh api --paginate "repos/$OWNER_REPO/pulls/$PR_NUMBER/reviews" --jq '.[].user.login' 2>/dev/null | sort -u)"
AUTO_REVIEW_PRESENT=0
while IFS= read -r login; do
  [[ -z "$login" ]] && continue
  if [[ "$login" == *"[bot]" ]] || [[ ",$AUTOMATED_REVIEWERS," == *",$login,"* ]]; then
    AUTO_REVIEW_PRESENT=1
  fi
done <<< "$REVIEW_LOGINS"
```

**Draft-PR review trigger (one-shot).** Review bots do not auto-review DRAFT PRs (Codex's triggers are open-for-review, draft→ready, or an explicit `@codex review` comment) — and pilot's PRs are born draft, so without a nudge the review wait would dead-end at the no-review `NEEDS_HUMAN`. When `AUTO_REVIEW_PRESENT == 0` AND the PR `isDraft` AND `land.reviewTrigger` is non-empty AND the ledger carries no `triggerPosted` marker for this PR: post the trigger ONCE (`gh pr comment "$PR_NUMBER" --body "$REVIEW_TRIGGER"`), set `triggerPosted: true` in the PR's ledger entry (atomic jq+mv; under `--dry-run` report would-trigger instead of posting), and report `AWAITING_REVIEW`, reason `review trigger posted; patience window open`. The window still anchors to the last push. An empty `land.reviewTrigger` (the default) never posts — the no-review-beyond-window path stays `NEEDS_HUMAN` as below.

Signal evaluation (only reached with green CI and `UNRESOLVED == 0`):

- **`silence`** (default): satisfied iff `AUTO_REVIEW_PRESENT == 1` AND `UNRESOLVED == 0` AND `WINDOW_ELAPSED == 1` (the window elapsing since the last push with zero unresolved threads IS the no-new-threads convergence — any new thread starts unresolved). Window not elapsed → `AWAITING_REVIEW`, reason `patience window open (<AGE_MIN>/<PATIENCE_MIN>m)`. Window elapsed with NO automated review ever → never merge unreviewed → `NEEDS_HUMAN`, reason `no automated review arrived within the patience window`.
- **`approve`**: satisfied iff `REVIEW_DECISION == "APPROVED"` (the formal decision). Not approved within the window → `AWAITING_REVIEW`; not approved once the window has elapsed (`WINDOW_ELAPSED == 1`) → `NEEDS_HUMAN`, reason `no formal approval within the patience window` (the wait is bounded, same as the other signals); `CHANGES_REQUESTED` → threads should exist → the resolve path; an empty `reviewDecision` (repo has no review policy) is not a block for the OTHER signals, but `approve` explicitly requires the formal decision.
- **`<github-login>`** (any other value): satisfied iff that reviewer's latest review is clean — fetch `gh pr view "$PR_NUMBER" --json latestReviews`, find the entry whose `author.login` matches the configured login (compare with any trailing `[bot]` stripped from both sides — GraphQL bot logins lack the suffix), and require its `state` to be `APPROVED`, or `COMMENTED` with `UNRESOLVED == 0`. `CHANGES_REQUESTED` or no review yet → `AWAITING_REVIEW` within the window, `NEEDS_HUMAN` beyond it.

### 2.7 — CI-fix budget + stale-approval detection (ledger reads)

```bash
PR_LEDGER="$(printf '%s\n' "$LEDGER_JSON" | jq -c --arg pr "$PR_URL" '.[$pr] // {}')"
CI_FIX_COUNT="$(printf '%s\n' "$PR_LEDGER" | jq -r '.ci_fix_count // 0')"
DECISION_AT_PUSH="$(printf '%s\n' "$PR_LEDGER" | jq -r '.decision_at_push // "-"')"
LAND_PUSHED_SHA="$(printf '%s\n' "$PR_LEDGER" | jq -r '.land_pushed_sha // "-"')"
```

- Planned `ci-fix` with `CI_FIX_COUNT >= CI_FIX_BUDGET` → plan `label` instead: durable `flow-next:needs-human` label + verdict `NEEDS_HUMAN`, reason `CI-fix budget exhausted (<count>/<budget>)`.
- **Stale-approval loop**: if `DECISION_AT_PUSH == "APPROVED"` AND `LAND_PUSHED_SHA == HEAD_OID` (the head is still our push) AND `REVIEW_DECISION == "REVIEW_REQUIRED"` AND `UNRESOLVED == 0`, the repo dismisses stale approvals on push — re-looping would ping-pong forever. Plan `label` → `NEEDS_HUMAN`, reason `stale-approval dismissal loop detected`.

### 2.8 — Merge-state gates (only when the review signal is satisfied)

- `MERGE_STATE == "UNKNOWN"`: GitHub recomputes asynchronously — re-poll `gh pr view "$PR_NUMBER" --json mergeStateStatus` up to 3 times with `sleep 3` between; still UNKNOWN → verdict `RESOLVING`, action `none` (re-tick).
- `MERGE_STATE == "DIRTY"`: conflict path → plan `rebase` (mechanical only; ACT 3.3).
- `MERGE_STATE == "BEHIND"`: plan `rebase` (same mechanical update, then re-gate next tick).
- Otherwise (`CLEAN`, `BLOCKED`, `HAS_HOOKS`, `UNSTABLE`): plan `merge`. (`BLOCKED`/`UNSTABLE` reflect server-side rules land already gates harder than — the merge attempt is authoritative; a refusal surfaces in ACT.)

### Dry-run stops here (R17)

`LAND_DRY_RUN == 1` → print the full classification report per PR (CI tri-state read with bucket counts, review-signal state, unresolved count, window age, ledger state, would-be action) plus the discovery table, then the aggregated terminal line computed by the Phase 4 worst-severity rule with the reason prefixed `dry-run: no mutations —`. Nothing was checked out, pushed, labeled, merged, dispatched, or written (ledger untouched).

## Phase 3 — ACT (at most ONE action class per PR per tick)

Execute each PR's planned action serially. Branch hygiene around EVERY checkout: record `ORIG_BRANCH` (Preamble), and after the per-PR action `git checkout "$ORIG_BRANCH"` + assert the non-`.flow/` tree is clean before the next PR and before tick end. A dirty tree after an action → verdict `NEEDS_HUMAN` for that PR and STOP the tick (no further PRs; report what happened).

### 3.1 — `ci-fix`

1. `gh pr checkout "$PR_NUMBER"` (the spec branch lives in this repo; checkout tracks it).
2. Inspect the failing check from the Phase 2 `CHECKS_JSON` (`name`, `bucket`, `link`). When the link maps to a GitHub Actions run (`/actions/runs/<id>` in the URL), derive the run id and read `gh run view <id> --log-failed`. External/status checks with no Actions run: use the check name/link as evidence and attempt only locally-discoverable matching validation. Logs unavailable AND no local validation exists → verdict `NEEDS_HUMAN`, restore branch, continue (never pretend CI was diagnosed).
3. Judge relatedness against the PR diff:
   - **Unrelated** (infra flake, e.g. runner timeout, network): ONE `gh run rerun <id>` for that run — verdict `FIXING_CI`, reason `infra flake — rerun dispatched`, restore branch, continue. The FIRST rerun for a PR consumes NO budget strike (diagnosis-only ticks must never durably label a healthy PR); a REPEAT flake on a later tick is a fresh attempt against the budget — it increments `ci_fix_count` alongside `rerun_count`. One rerun per PR per tick. Ledger write (every write site: `mkdir -p "$LEDGER_DIR"`, seed if missing, atomic `jq` + `mv`):

     ```bash
     mkdir -p "$LEDGER_DIR"; [ -s "$LEDGER" ] || echo '{}' > "$LEDGER"
     tmp="$LEDGER.tmp.$$"
     jq --arg pr "$PR_URL" --arg ts "$TODAY" '
       .[$pr].rerun_count = ((.[$pr].rerun_count // 0) + 1) | .[$pr].ts = $ts
       | (if .[$pr].rerun_count > 1 then .[$pr].ci_fix_count = ((.[$pr].ci_fix_count // 0) + 1) else . end)
     ' "$LEDGER" > "$tmp" && mv "$tmp" "$LEDGER"
     ```

   - **Related**: consume a budget strike BEFORE pushing — a crashed push still consumed an attempt:

     ```bash
     mkdir -p "$LEDGER_DIR"; [ -s "$LEDGER" ] || echo '{}' > "$LEDGER"
     tmp="$LEDGER.tmp.$$"
     jq --arg pr "$PR_URL" --arg ts "$TODAY" --arg dec "$REVIEW_DECISION" '
       .[$pr].ci_fix_count = ((.[$pr].ci_fix_count // 0) + 1) | .[$pr].ts = $ts | .[$pr].decision_at_push = (if $dec == "" then "-" else $dec end)
     ' "$LEDGER" > "$tmp" && mv "$tmp" "$LEDGER"
     ```

     Then: scope edits to the failing surface ONLY; run the repo's matching local validation when discoverable; stage ONLY the files you edited (NEVER `git add -A` here); commit `fix(ci): <what>`; `git push`.
4. After a successful push, record the push for stale-approval detection — this is THE canonical post-push ledger write (3.2 and 3.3 reuse it verbatim); it records BOTH the pushed sha and the review decision observed at push time:

   ```bash
   PUSHED_SHA="$(git rev-parse HEAD)"
   tmp="$LEDGER.tmp.$$"
   jq --arg pr "$PR_URL" --arg sha "$PUSHED_SHA" --arg dec "$REVIEW_DECISION" '
     .[$pr].land_pushed_sha = $sha | .[$pr].decision_at_push = (if $dec == "" then "-" else $dec end)
   ' "$LEDGER" > "$tmp" && mv "$tmp" "$LEDGER"
   ```

5. Verdict `FIXING_CI`. The push restarts the patience window (next tick re-anchors). Restore `ORIG_BRANCH`, assert clean.

### 3.2 — `resolve`

Dispatch the resolve-pr skill via the Skill tool — slash-command form, autonomous token:

```text
/flow-next:resolve-pr <PR_NUMBER> mode:autonomous
```

Gate ONLY on its machine-readable terminal line `RESOLVE_PR_VERDICT=<RESOLVED|PENDING|NEEDS_HUMAN> threads=<n> fixed=<n> needs_human=<n>` (the LAST line of its output — never on narration):

- `RESOLVED` → re-check convergence read-only for the report (resolve-pr's fix commits pushed → the patience window restarted, so the PR re-enters `AWAITING_REVIEW`; with reply-only resolution the window may already be satisfied — the merge still waits for the NEXT tick: one action class per PR per tick). Verdict `RESOLVING`.
- `PENDING` → threads replied, waiting on reviewers → verdict `RESOLVING`; next tick re-checks.
- `NEEDS_HUMAN` → apply the durable label (3.4) + verdict `NEEDS_HUMAN` (resolve-pr's bounded 2 fix-verify cycles already escalated).
- No terminal line (crash) → verdict `NEEDS_HUMAN`, no label (transient — a label needs a human to remove).

resolve-pr pushes commits itself when it fixes code; if it pushed, run the canonical post-push ledger write from 3.1 step 4 — read the fresh state via `gh pr view "$PR_NUMBER" --json headRefOid,reviewDecision` and write BOTH `land_pushed_sha` (the new `headRefOid`) and `decision_at_push` (the `reviewDecision` at push time, `-` when empty). Restore `ORIG_BRANCH` if resolve-pr left the worktree elsewhere; assert clean.

### 3.3 — `rebase` (mechanical only — v1 never hand-resolves conflicts)

```bash
gh pr checkout "$PR_NUMBER"
git fetch origin "$BASE_REF"
if ! git rebase "origin/$BASE_REF"; then
  git rebase --abort
  git checkout "$ORIG_BRANCH"
  # ANY conflict hunk → BLOCKED (verdict), reason "merge conflict needs hand-resolution"
fi
```

Clean rebase → `git push --force-with-lease` (restarts the patience window) → run the canonical post-push ledger write from 3.1 step 4 (`land_pushed_sha` = the rebased HEAD, `decision_at_push` = the Phase 2 `REVIEW_DECISION`) → verdict `RESOLVING` (re-gate next tick). Restore `ORIG_BRANCH`, assert clean.

### 3.4 — `label` (durable needs-human marker)

```bash
gh label create "flow-next:needs-human" --description "flow-next land: needs human attention" --color "D93F0B" 2>/dev/null || true
gh pr edit "$PR_NUMBER" --add-label "flow-next:needs-human"
```

Verdict `NEEDS_HUMAN` with the planned reason. Later ticks skip the PR at gate 2.1 while the label is present.

### 3.5 — `merge` + post-merge tail

All gates passed in-tick. Re-read the head right before merging and pin it:

```bash
HEAD_OID="$(gh pr view "$PR_NUMBER" --json headRefOid --jq .headRefOid)"
[[ "$IS_DRAFT" == "true" ]] && gh pr ready "$PR_NUMBER"     # idempotent flip; non-draft skips
MERGE_RC=0
MERGE_ERR="$(gh pr merge "$PR_NUMBER" --squash --delete-branch --match-head-commit "$HEAD_OID" 2>&1 >/dev/null)" || MERGE_RC=$?
if [[ "$MERGE_RC" -ne 0 ]]; then
  echo "Evidence: merge refused (rc=$MERGE_RC) — $MERGE_ERR"
fi
```

NEVER `gh pr merge --auto`. **`MERGE_RC != 0` skips the ENTIRE post-merge tail** — classify from the captured stderr, leave the worktree where it is (no checkout happened yet), and continue to the next PR:

- Head-SHA mismatch refusal (the `--match-head-commit` guard; stderr names the expected/actual sha) — state moved between gate and merge → verdict `RESOLVING` (re-tick), not `BLOCKED`.
- Any other merge refusal (server-side rule) → verdict `BLOCKED`, reason = the captured `MERGE_ERR` line.

Only on `MERGE_RC == 0`, move the worktree onto the merged base BEFORE any tail step — `spec close`, the tracker touchpoint, and release-follow all run from the clean base checkout, never from the (deleted) PR branch or a stale original branch:

```bash
git checkout "$BASE_REF" && git pull --ff-only
MERGE_OID="$(gh pr view "$PR_NUMBER" --json mergeCommit --jq '.mergeCommit.oid')"
TAIL_OK=1
if [[ -z "$MERGE_OID" ]] || ! git merge-base --is-ancestor "$MERGE_OID" HEAD; then
  echo "Evidence: squash commit ${MERGE_OID:-<unknown>} not on local $BASE_REF after pull"
  TAIL_OK=0
fi
git log --oneline -1   # evidence echo: the squash commit referencing the PR
```

`TAIL_OK == 0` → verdict `NEEDS_HUMAN` for this PR, reason `squash commit missing from local base — tail not run`; do NOT run ANY tail step (no spec close, no tracker, no release) and continue to the next PR — a later tick re-enters via the merged-but-unclosed path once the base is fixed. Only with `TAIL_OK == 1` run the tail, in order:

1. **Spec close** — `"$FLOWCTL" spec close "$spec" --json`. flowctl hard-requires all tasks done; stray non-done tasks at close time → verdict `NEEDS_HUMAN`, reason `spec close refused: <flowctl error>` (report, never force) — the merge stands, a later tick re-enters via the merged-but-unclosed path after a human fixes the task state. Do NOT commit yet — the tracker touchpoint below may update tracked `.flow` sync state; step 3 persists both in one commit.
2. **Tracker touchpoint (opt-in, best-effort)** — gated exactly like every fn-57 touchpoint (active AND leaf ≠ off/null; an unseeded leaf reads `null` = off):

   ```bash
   LEAF="$("$FLOWCTL" config get tracker.perEvent.land.merged --json | jq -r '.value')"
   TRACKER_FIRE=0
   if [ "$("$FLOWCTL" sync active --json | jq -r '.active')" = "true" ] \
      && [ "$LEAF" != "off" ] && [ "$LEAF" != "null" ]; then
     TRACKER_FIRE=1
   fi
   ```

   `TRACKER_FIRE == 1` → you MUST dispatch the tracker-sync skill via the Skill tool — this is a real skill invocation, not narration, and it uses the fn-57 lifecycle dispatch grammar (operation token + event tag, same shape as work/make-pr touchpoints):

   ```text
   skill: flow-next-tracker-sync   (operation: push <spec-id>, event: land.merged)
   ```

   The push projects the just-closed spec onto the linked issue — status who-wins flips it to the configured terminal state — and posts the merge/release verdict comment (include `merged PR: <PR_URL>` and, when the release step ran, the released version). The tracker-sync skill owns the transport, status who-wins, comment dedup, and emits its own receipt event-tagged `land.merged` (the fn-57 layer). Best-effort: a dispatch failure or tracker error surfaces as a stderr warning in the PR's evidence block and NEVER blocks the remaining tail steps or changes the PR's verdict.
3. **Persist the `.flow` state** — one commit covering the spec close AND any tracked sync state the touchpoint updated. The dirty-tree guards exclude `.flow/`, so an unpushed close would silently sit forever while every other clone (and CI) still sees the spec open:

   ```bash
   git add .flow && git commit -m "chore(flow): close ${spec} (landed PR #${PR_NUMBER})"
   git push || { git pull --rebase && git push; }
   ```

   If the push STILL fails, ROLL BACK the local close so the merged-but-unclosed re-entry path stays reachable from this clone (discovery selects `status == "open"` specs only — a stranded local `done` would orphan the tail):

   ```bash
   git rebase --abort 2>/dev/null || true
   git reset --hard HEAD^   # safe: the commit contains ONLY the .flow close/sync state; the tree was clean before it
   ```

   Then verdict `NEEDS_HUMAN`, reason `spec close not pushed`; skip release-follow for this PR and continue to the next — a later tick re-enters via merged-but-unclosed and retries the whole tail (`spec close` succeeds idempotently on a re-run).
4. **Release-follow** (only when `LAND_RELEASE == true`) — discovery order, first hit wins: `docs/RELEASING.md` → `RELEASING.md` → `agent_docs/releasing.md` → release docs referenced from CLAUDE.md/AGENTS.md → none (stop at merge, verdict `MERGED`). Bounds, all binding:
   - Deterministic, non-interactive commands from the discovered docs ONLY — no invented steps, no prompts, no secrets handling.
   - Clean non-`.flow/` tree required before starting and asserted after.
   - **Idempotency probe BEFORE acting**: check for an existing tag/GitHub release for the target version (`git tag -l <v>`, `gh release view <v>`); already present → resume past completed steps, never re-tag.
   - Release-step failure AFTER the successful merge → verdict `NEEDS_HUMAN` + durable label on the (merged) PR via 3.4 — the merge is NEVER retried, and later ticks never blindly re-run the failed step (re-entry only resumes via the idempotency probe).
   - Release completed → verdict `RELEASED`.

Verdict `MERGED` (or `RELEASED`). On success, drop the PR's ledger entry (atomic `jq 'del(.[$pr])'` + `mv`). End on the base branch with a clean tree (the original branch may have been the now-deleted PR branch — the base IS the restore target after a merge).

### 3.6 — `resume-tail` (re-entry idempotency)

A merged-but-unclosed spec resumes the tail exactly as 3.5 post-merge: checkout base + `git pull --ff-only` + verify the merge commit (via `gh pr view <MERGED_PR_NUM> --json mergeCommit`), then spec close → tracker touchpoint → persist `.flow` → release-follow. Never a second merge, never an error for already-completed steps (the release idempotency probe skips them; `spec close` succeeds idempotently on an already-closed spec). Verdict `MERGED`/`RELEASED` per how far the tail ran.

## Phase 4 — REPORT

Echo one evidence block per PR processed:

```text
PR <url> [<spec-id>]
  ci=<green|red|pending|none> checks=<pass>/<total> unresolved=<n> window=<AGE_MIN>/<PATIENCE_MIN>m
  signal=<silence|approve|login>:<satisfied|waiting|never> decision=<reviewDecision|->
  action=<ci-fix|resolve|rebase|merge|resume-tail|label|none> verdict=<VERDICT> reason="<one line>"
```

Compute the tick verdict as the worst severity across all per-PR verdicts, priority order:

```text
NEEDS_HUMAN > BLOCKED > FIXING_CI > RESOLVING > AWAITING_REVIEW > RELEASED > MERGED
```

`pr=` in the terminal line is the URL of the deciding PR (first PR carrying the worst verdict); `prs=` is the count of PRs processed (babysit + re-entry + discovery NEEDS_HUMAN entries). Zero processed PRs → `NO_WORK` with `prs=0 pr=-`.

Assert tick-end hygiene before printing: current branch is `ORIG_BRANCH` (or the merged base when 3.5/3.6 ran) and the non-`.flow/` tree is clean — a violation downgrades the tick to `NEEDS_HUMAN` with the hygiene failure as the reason.

The terminal line is always the LAST line of the tick output. Print nothing after it:

```text
LAND_VERDICT=<verdict|NO_WORK> prs=<n> pr=<deciding-pr-url|-> reason="<one line>"
```
