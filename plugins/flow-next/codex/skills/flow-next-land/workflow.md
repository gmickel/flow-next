# /flow-next:land workflow

Execute these phases in order. One invocation is one tick: discover authored PRs, classify each through the gate tree, take at most ONE action class per PR, and end with the terminal verdict line.

## Review no-repeat terminal

`NOT_RETRYABLE: artifact unchanged since last verdict` with exit `1` from any
review is `LAND_VERDICT=NEEDS_HUMAN`. Stop; do not treat it as CI/transport,
refund it, reset/force it, or redispatch. A human must edit the artifact,
explicitly reset, or deliberately use `--force`.

Review-counter reset and `--force` review dispatch/increment are human-only
recovery tools.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks use `$FLOWCTL`:

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

Shared shell context for the workflow:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
TODAY="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
NOW_EPOCH="$(date -u +%s)"
ORIG_BRANCH="$(git -C "$REPO_ROOT" branch --show-current)"
```

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

Read the `land.*` config — ONE subtree read (fn-110), then jq lookups from the captured JSON. fn-60.2 seeds defaults, but tolerate `null` (pre-seed / pre-subtree flowctl copies, where the whole capture degrades to `{}` or `"value": null`) with hard fallbacks:

```bash
# ONE subtree read: {"key":"land","value":{...}} — the only config invocation in
# this skill. Explicit status branch (NOT `|| echo '{}'`): a failing flowctl can
# still print partial JSON to stdout, and appending '{}' to it would make every
# jq lookup emit two documents, bypassing the "null" fallbacks below.
if ! LAND_CFG="$("$FLOWCTL" config get land --json 2>/dev/null)"; then LAND_CFG='{}'; fi
lcfg() { printf '%s\n' "$LAND_CFG" | jq -r ".value.$1"; }                  # missing key → literal "null"; explicit "" → empty line (same as the old per-key reads)
LAND_RELEASE="$(lcfg release)";                  [[ -z "$LAND_RELEASE" || "$LAND_RELEASE" == "null" ]] && LAND_RELEASE=true
PATIENCE_MIN="$(lcfg patienceMinutes)";          [[ -z "$PATIENCE_MIN" || "$PATIENCE_MIN" == "null" ]] && PATIENCE_MIN=30
REVIEW_SIGNAL="$(lcfg reviewSignal)";            [[ -z "$REVIEW_SIGNAL" || "$REVIEW_SIGNAL" == "null" ]] && REVIEW_SIGNAL=silence
AUTOMATED_REVIEWERS="$(lcfg automatedReviewers)"; [[ "$AUTOMATED_REVIEWERS" == "null" ]] && AUTOMATED_REVIEWERS=""
REVIEW_TRIGGER="$(lcfg reviewTrigger)";          [[ "$REVIEW_TRIGGER" == "null" ]] && REVIEW_TRIGGER=""
CI_FIX_BUDGET="$(lcfg ciFixBudget)";             [[ -z "$CI_FIX_BUDGET" || "$CI_FIX_BUDGET" == "null" ]] && CI_FIX_BUDGET=3
# fn-65.1 — clean-review COMMENT pattern (silence-signal supplement, §2.6).
# CONTRACT (distinct from the keys above — do NOT collapse `""` into the
# default): the seeded built-in default is a STRUCTURED ERE; an unseeded
# pre-fn-65 flowctl copy returns the literal "null" → fall back to the
# built-in; an EXPLICIT empty string "" (the user's off-switch) → DISABLE
# the comment scan; any other value → use it verbatim. `jq -r` prints the
# literal "null" for JSON null and an EMPTY line for "", so the two are
# distinguishable — guard ONLY the "null" case, never `-z`.
CLEAN_REVIEW_PATTERN="$(lcfg cleanReviewCommentPattern)"
if [[ "$CLEAN_REVIEW_PATTERN" == "null" ]]; then
  # pre-seed flowctl (key absent) → the canonical built-in default
  CLEAN_REVIEW_PATTERN="(Didn'?t find any( major)? issues|No( major)? issues found).*Reviewed commit"
fi   # explicit "" stays "" → §2.6 treats empty as DISABLED (no default fallback)
# fn-188 — opt-in repo merge-verdict gate (§2.9). unset / null / "" ALL mean OFF.
MERGE_VERDICT_CMD="$(lcfg mergeVerdictCommand)"; [[ "$MERGE_VERDICT_CMD" == "null" ]] && MERGE_VERDICT_CMD=""
```

Resolve the land ledger — READ-ONLY here (a missing file reads as `{}`; nothing is created or written until an ACT/REPORT write site, so `--dry-run` leaves the filesystem untouched). It lives under the git common dir so it is shared across worktrees and cannot be swept into commits by `git add -A`:

```bash
LEDGER_DIR="$(git -C "$REPO_ROOT" rev-parse --git-common-dir)/flow-next"
LEDGER="$LEDGER_DIR/land-strikes.json"
LEDGER_JSON="$(cat "$LEDGER" 2>/dev/null || echo '{}')"
```

Ledger schema, keyed by PR URL: `{"<pr-url>": {"ci_fix_count": <n>, "rerun_count": <n>, "decision_at_push": "<APPROVED|...|->", "land_pushed_sha": "<sha|->", "ts": "<iso8601>"}}`. It is skill-owned scratch; no flowctl plumbing. Every write site runs `mkdir -p "$LEDGER_DIR"` plus `[ -s "$LEDGER" ] || echo '{}' > "$LEDGER"` first, then writes atomically with `jq` plus `mv`.

## Phase 1 — DISCOVER

**Land babysits only PRs whose authoring spec has every task done** — pilot still owns in-flight specs (the pilot-concurrency interlock), so a tick that acted on a spec with an open task has broken this. Candidates from the minimal listing:

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

**Authorship requires both signals before any mutation** — the branch match above **and** the make-pr breadcrumb in the PR body. A hand-opened PR on a spec branch that got auto-merged has broken this. **`PR_NUMBER` comes from the outcome branch above** (babysit: the single open PR's number; re-entry: `MERGED_PR_NUM`); a `PR_NUMBER` carried over from a prior loop iteration has broken this.

The probe is **structural, not a mention test** (issue #274 — a body that merely *discusses* land's discovery rules and names a spec id must never classify as authored). Primary signal: the invisible machine marker make-pr emits directly under the visible footer (make-pr workflow §2.13b) — `<!-- flow-next:make-pr spec=<spec-id> base=<base-ref> -->`. Prose about the token cannot accidentally form that comment node. Fallback for PRs opened by a pre-marker make-pr: the ANCHORED visible-footer shape — the `flow-next:make-pr` token and the spec id co-occurring on ONE line in the footer's `Generated by … from … <spec-id> …` form — never two independent whole-body presence greps:

```bash
PR_BODY="$(gh pr view "$PR_NUMBER" --json body --jq .body 2>/dev/null || true)"
AUTHORED=0
# FOOTER TAIL extraction, shared by both branches: non-empty lines with the
# structural footer furniture (`---` rules and make-pr §4.6a's appended
# `Ref <id>` tracker line) stripped, then the LAST TWO remaining lines. In a
# canonical make-pr body those are exactly [visible breadcrumb, machine
# marker] (or just [.., breadcrumb] on a pre-marker body). grep's `.` never
# matches a newline (patterns are line-based) - use `.*`, NEVER `[^\n]`,
# which inside shell double quotes becomes a class EXCLUDING the literal
# letter n and rejects every real `fn-*` footer.
FOOTER_TAIL="$(printf '%s\n' "$PR_BODY" | awk 'NF' | grep -vE '^(---+|Refs? .*)$' | tail -2)"
MARKER_LINE="$(printf '%s\n' "$FOOTER_TAIL" | tail -1)"
CRUMB_LINE="$(printf '%s\n' "$FOOTER_TAIL" | head -1)"
# 1) machine marker (make-pr >= 3.11): the exact comment node must be the
#    FINAL structural line AND sit directly under the visible breadcrumb.
#    This conjunction defeats trailing-fenced-example spoofs without parsing
#    Markdown: an example's closing ``` (or any trailing prose) displaces the
#    marker from the final line, and a bare marker pasted at the very bottom
#    still lacks a breadcrumb NAMING THIS SPEC directly above it (the crumb
#    conjunct requires the full "Generated by ... flow-next:make-pr ... from
#    ... <spec-id>" shape, not just the words "Generated by"). Reproducing the
#    FULL two-line canonical footer verbatim is deliberate forgery, which no
#    body-content scheme can defeat - that is issue #274's option 3, attested
#    provenance, explicitly out of scope.
if printf '%s' "$MARKER_LINE" | grep -qE "^<!-- flow-next:make-pr spec=${spec}( base=[^ ]+)? -->$" \
   && printf '%s' "$CRUMB_LINE" | grep -qE "Generated by.*flow-next:make-pr.*from.*${spec}"; then
  AUTHORED=1
# 2) legacy anchored footer (pre-marker make-pr): the FULL canonical footer
#    shape - "Generated by ... flow-next:make-pr ... from ... <spec-id> ...
#    against ... on YYYY-MM-DD" in order on ONE line, date included
#    (markup-tolerant: backticks/italics/link URLs allowed) - and it must BE
#    the FINAL structural line (on a pre-marker body the breadcrumb is last),
#    mirroring the marker branch: a trailing fenced example is displaced by
#    its own closing fence, and a mid-body quoted breadcrumb or hand-written
#    "against current behavior" line never classifies.
elif printf '%s' "$MARKER_LINE" \
   | grep -qE "Generated by.*flow-next:make-pr.*from.*${spec}([^a-z0-9-].*)?against.*on [0-9]{4}-[0-9]{2}-[0-9]{2}"; then
  AUTHORED=1
fi
# AUTHORED=0 → branch-only match → report NEEDS_HUMAN for this PR, never act on it
```

```text
LAND_VERDICT=NO_WORK prs=0 pr=- reason="no open build-loop-authored PRs"
```

Echo the discovery table: candidate specs, branch, PR number/state, authorship result, classification.

Done when: every candidate spec carries one classification (babysit / re-entry / `NEEDS_HUMAN` / silently skipped) and the table is in the transcript.

## Phase 2 — GATE (per PR, read-only)

Classify every discovered PR before acting on any. **This phase performs reads only** — a checkout, push, label, or ledger write inside GATE has broken this. Each PR gets a planned action class + provisional verdict. Process PRs serially in stable spec-id order.

Fetch the gate state in one call per PR:

```bash
PR_STATE="$(gh pr view "$PR_NUMBER" --json url,number,state,isDraft,mergeStateStatus,reviewDecision,headRefOid,baseRefName,labels,commits,createdAt)"
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

Anchored to the actual PUSH time, never a commit's author/committer timestamp alone — a branch pushed NOW carrying earlier-authored or rebased commits must not look "older than the window" on tick one (that would skip the wait entirely), and a land-authored CI-fix push restarts the window. `pushedDate` is the primary signal; when GraphQL returns it null, the fallback is the MAX of the head commit's `committedDate` and the PR's `createdAt` (a just-opened PR's creation time IS its first push's availability time):

```bash
HEAD_SHA="$(printf '%s\n' "$PR_STATE" | jq -r '.headRefOid')"
PUSHED_AT="$(gh api graphql -f query='query($owner:String!,$repo:String!,$oid:GitObjectID!){repository(owner:$owner,name:$repo){object(oid:$oid){... on Commit{pushedDate committedDate}}}}' \
  -f owner="${OWNER_REPO%/*}" -f repo="${OWNER_REPO#*/}" -F oid="$HEAD_SHA" \
  --jq '.data.repository.object.pushedDate // empty')"
if [[ -n "$PUSHED_AT" ]]; then
  LAST_PUSH="$PUSHED_AT"
else
  COMMITTED_AT="$(printf '%s\n' "$PR_STATE" | jq -r '.commits[-1].committedDate // empty')"
  CREATED_AT="$(printf '%s\n' "$PR_STATE" | jq -r '.createdAt // empty')"
  LAST_PUSH="$(printf '%s\n%s\n' "$COMMITTED_AT" "$CREATED_AT" | sort | tail -1)"   # ISO-8601 sorts lexically
fi
PUSH_EPOCH="$(printf '%s' "$LAST_PUSH" | jq -Rr 'fromdateiso8601' 2>/dev/null || echo "$NOW_EPOCH")"
AGE_MIN=$(( (NOW_EPOCH - PUSH_EPOCH) / 60 ))
WINDOW_ELAPSED=$(( AGE_MIN >= PATIENCE_MIN ? 1 : 0 ))
```

### 2.4 — CI tri-state (every check, never `--required`)

**The CI gate reads every check, never the required-only subset** — required-only ignores failing optional CI and deadlocks on repos with no required checks, so a gate scoped with `--required` has broken this:

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

Same GraphQL surface as resolve-pr's fetch — and fully PAGINATED, because `UNRESOLVED == 0` is a merge condition: a >100-thread PR must not read as resolved just because page one was (gh's GraphQL `--paginate` iterates on the `$endCursor` variable; the per-page counts are summed):

```bash
UNRESOLVED="$(gh api graphql --paginate \
  -f query='query($owner:String!,$repo:String!,$pr:Int!,$endCursor:String){repository(owner:$owner,name:$repo){pullRequest(number:$pr){reviewThreads(first:100,after:$endCursor){pageInfo{hasNextPage endCursor} nodes{isResolved}}}}}' \
  -f owner="${OWNER_REPO%/*}" -f repo="${OWNER_REPO#*/}" -F pr="$PR_NUMBER" \
  --jq '[.data.repository.pullRequest.reviewThreads.nodes[] | select(.isResolved | not)] | length' \
  | awk '{s+=$1} END{print s+0}')"
```

`UNRESOLVED > 0` with green CI → plan `resolve` (dispatch resolve-pr in ACT), provisional verdict `RESOLVING`.

### 2.5b — QA verdict gate (flow-side — land IS the promised gate for QA findings)

The QA stage is advisory to the build loop and pilot advances a `NEEDS_WORK` QA pass explicitly on the promise that *"the human reviewer + the land gate act on its findings"* (pilot workflow §5 / §"For qa"). This is that gate — without it, a PR whose latest `qa_verdict` says `NEEDS_WORK` (an open P0/P1 or an uncovered UI-observable R-ID) auto-merges the moment CI is green.

**Read the receipt from the PR HEAD, not land's working tree.** The receipt is committed on the *un-merged spec branch* (qa §6.3b); land ticks run from `ORIG_BRANCH` (the base) and Phase 2 does no checkout — so a working-tree `[[ -f ]]` would find nothing and the gate would silently no-op on every PR. Read the committed file at `$HEAD_SHA` via the API (read-only, dry-run-safe):

```bash
QA_JSON="$(gh api -H "Accept: application/vnd.github.raw" \
  "repos/$OWNER_REPO/contents/.flow/review-receipts/qa-$spec.json?ref=$HEAD_SHA" 2>/dev/null || echo '{}')"
QA_OUTCOME="$(printf '%s' "$QA_JSON" | jq -r '.qa_outcome // ""' 2>/dev/null || echo "")"
```

Gate on the latest committed `qa_outcome` for this PR head (the four-outcome field is `SHIP | NEEDS_WORK | BLOCKED | NA`):

| Latest receipt state at the PR head | Land action |
|---|---|
| 404 / unparseable / `qa_outcome` ∈ {`SHIP`, `NA`, `BLOCKED`} or any other value | **No QA objection** — continue to 2.6. (`BLOCKED` = "no ship *claim* on a QA basis", not "the app is broken" — advisory, exactly as pilot treats it; QA never hard-blocks on couldn't-verify.) |
| `qa_outcome == NEEDS_WORK` | verdict `NEEDS_HUMAN`, action `none`, reason `latest QA verdict at the PR head is NEEDS_WORK (open P0/P1 or uncovered UI R-ID) — merge blocked pending human review or a QA re-run to SHIP`. **No further gates for this PR.** |

**No head_sha freshness check, deliberately.** The receipt read at `$HEAD_SHA` is the latest QA verdict for the commit being merged (each QA run overwrites the committed receipt). Land never re-runs QA, so a `NEEDS_WORK` that predates later commits is no proof the P0 was fixed — the later commits could be an unrelated `ci-fix`, a resolve-pr push, or land's own §3.3 catch-up. **Fail-safe: any `NEEDS_WORK` at the head blocks** until QA re-runs to `SHIP` (which overwrites the receipt → no block) or a human clears it. A merge that proceeded past a head `NEEDS_WORK` has broken this — and closing that path is what shuts both the wrong-tree read and the stale-head laundering channel a naive `head_sha`-equality check would open.

### 2.6 — Review signal (`land.reviewSignal`)

Review bots (e.g. chatgpt-codex-connector) post COMMENTED reviews and never APPROVE; `reviewDecision` will not reflect them. An **automated reviewer** is a review author whose login ends in `[bot]` (REST form — fetch reviews via REST so bot logins carry the suffix), or any login in the `land.automatedReviewers` csv.

**A historical review never satisfies the gate**: after a land-authored push, an old automated review would let the new head merge unreviewed — that has broken this. The signal is therefore **head-current**: an automated review counts only if its `commit_id` equals the current `HEAD_OID`, or it was submitted after the last-push timestamp (some bots attach re-reviews to older commits; submitted-after-push still proves the reviewer saw the new state):

```bash
AUTO_REVIEW_PRESENT=0   # any automated review, ever (drives the trigger branch)
AUTO_REVIEW_CURRENT=0   # automated review of the CURRENT head (drives the silence gate)
AUTO_REVIEW_SOURCE=     # set to "comment" iff the clean-review COMMENT scan (below) satisfied it; empty = reviews-API
AUTO_REVIEW_EVIDENCE=   # comment author + matched SHA prefix (fn-65.1 observability)
while IFS=$'\t' read -r login commit submitted; do
  [[ -z "$login" ]] && continue
  if [[ "$login" == *"[bot]" ]] || [[ ",$AUTOMATED_REVIEWERS," == *",$login,"* ]]; then
    AUTO_REVIEW_PRESENT=1
    if [[ "$commit" == "$HEAD_OID" || "$submitted" > "$LAST_PUSH" ]]; then
      AUTO_REVIEW_CURRENT=1
    fi
  fi
done < <(gh api --paginate "repos/$OWNER_REPO/pulls/$PR_NUMBER/reviews" \
  --jq '.[] | [.user.login, .commit_id, .submitted_at] | @tsv' 2>/dev/null)
```

**Clean-review COMMENT scan (`silence` only — fn-65.1).** A no-findings review bot (e.g. `chatgpt-codex-connector[bot]`) posts an **issue comment** instead of a formal review — that comment NEVER appears in the reviews API above, so `AUTO_REVIEW_CURRENT` reads `0` and the `silence` gate would dead-end at `NEEDS_HUMAN` even though the head was demonstrably re-reviewed clean. This scan supplies that missing evidence. It runs **only** when `REVIEW_SIGNAL == silence` (never on `approve`/`<login>`), **only** when `CLEAN_REVIEW_PATTERN` is non-empty (explicit `""` disables it), and it ONLY ever **sets** `AUTO_REVIEW_CURRENT=1` — it never resets the reviews-API result. It runs BEFORE the draft-trigger check below so a comment-proven head-current review correctly suppresses a now-redundant `@codex review` re-trigger (a clean comment naming the head IS proof the bot reviewed the head). The `gh api` is a read-only paginated GET (dry-run-safe). The login allowlist gate is the SAME `[bot]`-suffix/`AUTOMATED_REVIEWERS` test used by the reviews loop above; the head-current test is the comment analog of the reviews path's `commit_id == HEAD_OID`:

```bash
if [[ "$REVIEW_SIGNAL" == "silence" && -n "$CLEAN_REVIEW_PATTERN" ]]; then
  HEAD_LC="$(printf '%s' "$HEAD_OID" | tr 'A-Z' 'a-z')"
  while IFS=$'\t' read -r login body; do
    [[ -z "$login" ]] && continue
    # 1) automated-reviewer allowlist (verbatim from the reviews loop)
    if [[ "$login" == *"[bot]" ]] || [[ ",$AUTOMATED_REVIEWERS," == *",$login,"* ]]; then
      # 2) body must match the structured clean-review pattern
      printf '%s\n' "$body" | grep -Eiq "$CLEAN_REVIEW_PATTERN" || continue
      # 3) head-current SHA token — EMPTY-GUARDED. Prefer the token on the
      #    `Reviewed commit` marker line; else any hex run in the body.
      #    Lowercase; a token counts ONLY if it is non-empty, >=7 chars, AND
      #    a prefix of HEAD_OID. NEVER test `[[ $HEAD_OID == $token* ]]` on an
      #    unset/empty token — an empty token makes the prefix-glob spuriously
      #    TRUE and would pass on ANY matching comment.
      SHA_TOKENS="$(printf '%s\n' "$body" \
        | grep -Eio 'Reviewed commit[^0-9a-fA-F]*[0-9a-fA-F]{7,40}' \
        | grep -Eio '[0-9a-fA-F]{7,40}')"
      [[ -z "$SHA_TOKENS" ]] && SHA_TOKENS="$(printf '%s\n' "$body" | grep -Eio '[0-9a-fA-F]{7,40}')"
      while IFS= read -r token; do
        token="$(printf '%s' "$token" | tr 'A-Z' 'a-z')"
        # non-empty AND min-length AND prefix-of-head — all three required
        if [[ -n "$token" && ${#token} -ge 7 && "$HEAD_LC" == "$token"* ]]; then
          AUTO_REVIEW_CURRENT=1
          AUTO_REVIEW_SOURCE=comment
          AUTO_REVIEW_EVIDENCE="$login @ ${token:0:12}"
          break
        fi
      done <<< "$SHA_TOKENS"
    fi
  done < <(gh api --paginate "repos/$OWNER_REPO/issues/$PR_NUMBER/comments" \
    --jq '.[] | [.user.login, (.body | gsub("\t";" ") | gsub("\n";" "))] | @tsv' 2>/dev/null)
fi
```

A non-automated login (step 1 fails), a body with no clean phrase (step 2 fails), and a comment whose only SHA is stale or absent (step 3 finds no qualifying token) are each ignored — the gate falls through to the unchanged reviews-API result. `AUTO_REVIEW_SOURCE` defaults unset (reviews-API satisfaction) and is set to `comment` only on a comment-driven match; surface `AUTO_REVIEW_SOURCE` + `AUTO_REVIEW_EVIDENCE` (author + matched SHA prefix) in the `--dry-run` classification report and the verdict report so a transcript reader sees WHY the gate passed.

**Draft-PR review trigger (one-shot per head SHA).** Review bots do not auto-review DRAFT PRs (Codex's triggers are open-for-review, draft→ready, or an explicit `@codex review` comment) — and pilot's PRs are born draft, so without a nudge the review wait would dead-end at the no-review `NEEDS_HUMAN`, and a land-authored CI-fix push would go un-re-reviewed. When the PR `isDraft` AND `land.reviewTrigger` is non-empty AND the ledger's `triggerSha` for this PR differs from the current head SHA AND a review nudge is due (`AUTO_REVIEW_CURRENT == 0` — no automated review of the current head): post the trigger (`gh pr comment "$PR_NUMBER" --body "$REVIEW_TRIGGER"`), set `triggerSha: <head-sha>` in the PR's ledger entry (atomic jq+mv; under `--dry-run` report would-trigger instead of posting), and report `AWAITING_REVIEW`, reason `review trigger posted; patience window open`. Keying the marker to the head SHA means each push gets at most one nudge — never a comment loop. The window still anchors to the last push. An empty `land.reviewTrigger` (the default) never posts — the no-review-beyond-window path stays `NEEDS_HUMAN` as below.

Recommended opt-in trigger text: `@codex review — focus on integration effects,
the diff as narrative, and cross-task regressions. Spec/doc-prose findings are
welcome as FYI, not merge-gating.` Bot comments are outside the review detector
and Ralph-guard blast radius; resolve-pr applies the prose-vs-code triage rule
when handling them.

Signal evaluation (only reached with green CI and `UNRESOLVED == 0`):

- **`silence`** (default): satisfied iff `AUTO_REVIEW_CURRENT == 1` (an automated review of the CURRENT head — see above) AND `UNRESOLVED == 0` AND `WINDOW_ELAPSED == 1` (the window elapsing since the last push with zero unresolved threads IS the no-new-threads convergence — any new thread starts unresolved). Window not elapsed → `AWAITING_REVIEW`, reason `patience window open (<AGE_MIN>/<PATIENCE_MIN>m)`. Window elapsed with NO automated review ever → never merge unreviewed → `NEEDS_HUMAN`, reason `no automated review arrived within the patience window`.
- **`approve`**: satisfied iff `REVIEW_DECISION == "APPROVED"` (the formal decision). Not approved within the window → `AWAITING_REVIEW`; not approved once the window has elapsed (`WINDOW_ELAPSED == 1`) → `NEEDS_HUMAN`, reason `no formal approval within the patience window` (the wait is bounded, same as the other signals); `CHANGES_REQUESTED` → threads should exist → the resolve path; an empty `reviewDecision` (repo has no review policy) is not a block for the OTHER signals, but `approve` explicitly requires the formal decision.
- **`<github-login>`** (any other value): satisfied iff that reviewer's latest review is clean — fetch `gh pr view "$PR_NUMBER" --json latestReviews`, find the entry whose `author.login` matches the configured login (compare with any trailing `[bot]` stripped from both sides — GraphQL bot logins lack the suffix), and require its `state` to be `APPROVED`, or `COMMENTED` with `UNRESOLVED == 0`. `CHANGES_REQUESTED` or no review yet → `AWAITING_REVIEW` within the window, `NEEDS_HUMAN` beyond it.

**§2.6 does not exit the gate tree — §2.7 still runs (the `approve` ordering).** Only §2.1's durable-label skip is terminal; every other gate assigns a PROVISIONAL verdict and falls through, so a later section's assignment wins. Under `reviewSignal: approve` that matters exactly once: when the head is land's own catch-up push, the ledger recorded `decision_at_push == APPROVED`, and the repo has since dismissed that approval, §2.6 assigns `AWAITING_REVIEW` (or `NEEDS_HUMAN` past the window) — and then §2.7's stale-approval detector, whose four conditions describe that same state, overwrites it with `label` → `NEEDS_HUMAN`, reason `stale-approval dismissal loop detected`. The detector is REACHABLE under `approve`, never shadowed; its durable label is the point, because it is what stops the next tick from re-entering the same loop. (§2.8 is the one gate that is genuinely conditional — it runs only when the signal is satisfied.) Server-side catch-up (§3.3) does not retire this path: it still advances the head, so a dismiss-on-push repo still dismisses.

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
- `MERGE_STATE == "DIRTY"`: conflict path → plan `catch-up` (server-side; GitHub itself decides whether the base merges, and refuses when it would conflict; ACT 3.3).
- `MERGE_STATE == "BEHIND"`: plan `catch-up` (the same server-side update, then re-gate next tick).

Both merge states route to the SAME action deliberately: the catch-up is one `gh pr update-branch` call, and GitHub either performs the base merge or refuses it. That removes the old local-rebase-disagrees-with-`mergeStateStatus` surprise — there is no second opinion left to disagree.
- Otherwise (`CLEAN`, `BLOCKED`, `HAS_HOOKS`, `UNSTABLE`): plan `merge`. (`BLOCKED`/`UNSTABLE` reflect server-side rules land already gates harder than — the merge attempt is authoritative; a refusal surfaces in ACT.)

**Record the plan before leaving the gate tree**: `PLANNED_ACTION=<the action class planned above>` (`merge`, `catch-up`, `ci-fix`, `resolve`, `label`, `resume-tail`, `none`) - every "plan X" decision in 2.1-2.8 assigns it. §2.9 and the ACT phase key on this variable; a §2.9 that never ran because nothing assigned `PLANNED_ACTION` has broken this.

### 2.9 — Repo merge-verdict gate (`land.mergeVerdictCommand`, opt-in, fail-closed)

On a repo with no branch protection (free-plan private repos, where rulesets and protection 403) there is no required status check, so 2.4-2.8 gate against a server that has nothing to say. This is the repo-local gate of record: one repo-authored command whose exit code decides whether land may merge. It is block-only - a green verdict grants nothing the other gates did not already grant, it can only take a merge away. Off by default: unset, `null`, and `""` ALL mean OFF and behave byte-for-byte as before this gate existed (deliberately NOT the null-vs-`""` asymmetry of `cleanReviewCommentPattern` in §2.6 - do not copy that shape here).

Reached ONLY when every gate above is satisfied AND the action planned in 2.8 is `merge`. One execution per merge attempt, never one per patience tick - the verdict is freshest at the decision point. Context arrives as ENVIRONMENT only; the configured string is passed to `bash -c` verbatim and is never built from or interpolated with PR-derived text:

```bash
MERGE_VERDICT=skipped        # green | refused | skipped | would-run (Phase 4 evidence)
MERGE_VERDICT_HEAD=""        # the exact head the command judged (pins 3.5's merge)
if [[ -n "$MERGE_VERDICT_CMD" && "$PLANNED_ACTION" == "merge" ]]; then
  if [[ "$LAND_DRY_RUN" == 1 ]]; then
    MERGE_VERDICT=would-run  # R3 — --dry-run NEVER executes the command
  elif [[ "$(git rev-parse --abbrev-ref HEAD)" != "$BASE_REF" ]]; then
    # TRUST GUARD: the command string was read from this checkout's
    # .flow/config.json. On a non-base checkout (e.g. the PR branch itself)
    # that text is the PR author's, not the base's — executing it would let
    # a PR self-approve. Refuse; never execute from an untrusted tree.
    MERGE_VERDICT=refused
    MV_RC=1; MV_ERR="merge-verdict gate requires the base checkout (on $(git rev-parse --abbrev-ref HEAD), base is $BASE_REF)"
  else
    # Bind the merge target BEFORE the command runs: a base that advances
    # mid-run must read as moved, not as judged. Server truth via ls-remote;
    # an empty resolution is a refusal (fail-closed), never a skipped check.
    MERGE_VERDICT_BASE="$(git ls-remote origin "refs/heads/$BASE_REF" | cut -f1)"
    if [[ -z "$MERGE_VERDICT_BASE" ]]; then
      MERGE_VERDICT=refused
      MV_RC=1; MV_ERR="merge-verdict gate cannot resolve origin/$BASE_REF (ls-remote empty/failed)"
    else
      # FOREGROUND RULE: ONE blocking foreground Bash call with a 600s tool
      # timeout (the host tool's bound - the `timeout` binary is not stock on
      # macOS). A tool-level timeout is a refusal, exactly like exit 124.
      MV_ERR_FILE="$(mktemp)"; MV_RC=0
      # cwd = REPO_ROOT on ORIG_BRANCH (Phase 2 does no checkout).
      FLOW_HEAD_SHA="$HEAD_OID" FLOW_BASE_REF="$BASE_REF" \
      FLOW_PR_NUMBER="$PR_NUMBER" FLOW_SPEC_ID="$spec" \
        bash -c "cd \"$REPO_ROOT\" && $MERGE_VERDICT_CMD" >/dev/null 2>"$MV_ERR_FILE" || MV_RC=$?
      MV_ERR="$(tail -n 1 "$MV_ERR_FILE" 2>/dev/null | cut -c1-200)"; rm -f "$MV_ERR_FILE"
      [[ "$MV_RC" -eq 0 ]] && MERGE_VERDICT=green || MERGE_VERDICT=refused
      MERGE_VERDICT_HEAD="$HEAD_OID"
    fi
  fi
fi
```

| Command outcome | Land action |
|---|---|
| exit 0 | **green** - the merge-verdict gate is satisfied; proceed to the planned `merge` (3.5). |
| any non-zero exit - including `124` or a host-tool timeout at the 600s bound, `126`/`127` (unexecutable / not found), `128+N` (signal death) | verdict `NEEDS_HUMAN`, action `none`, reason `merge-verdict command refused (exit <MV_RC>): <MV_ERR>` (last stderr line, ~200 chars). **No merge.** |

**Fail-closed, always.** A configured command that is missing, unexecutable, times out at the 600s bound, or dies on a signal BLOCKS the merge - it is never read as "skip", "not applicable", or "gate unavailable". A tick that merged because the configured command could not run has broken this. The refusal class is `NEEDS_HUMAN`, never `BLOCKED`: `BLOCKED` stays reserved for server-side merge refusals (3.5). No `flow-next:needs-human` label is applied on refusal (same posture as 2.5b) - fix the repo-side cause and the next tick re-gates from scratch.

**A verdict binds a (head, base) pair.** §2.9 records the base's remote SHA at judgment; 3.5 refuses to merge when the base has since moved (verdict `RESOLVING`, re-tick re-judges) - the common cause is an earlier PR in the same tick merging first. This mirrors the strict interpretation of a required check: the command judged one merge target, not whichever base exists later.

**`MERGE_VERDICT` and `MERGE_VERDICT_HEAD` are per-PR state, not loop variables.** A tick that classifies several PRs records both values in each PR's classification record alongside its planned action; a later PR's classification never overwrites an earlier PR's verdict. 3.5 reads the values recorded for THE PR IT IS MERGING - a merge that read another iteration's (or a reset) verdict pair has broken this.

**The command executes ONLY from the base checkout.** The command string and the config that carries it are read from the working tree, so a non-base checkout (the PR branch itself, a feature branch) would execute text the PR author controls - a self-approval channel. The trust guard above refuses on any checkout whose branch is not `BASE_REF`; a gate that executed the command from a non-base checkout has broken this.

**The command runs on the BASE checkout, not the PR.** Phase 2 performs no checkout and land never checks out the PR branch for this gate, so a command that inspects the working tree is grading the base and would pass a broken PR. `$FLOW_HEAD_SHA` (the PR `.headRefOid` captured at the top of Phase 2) is the only thing that names the code being merged: the command must key on it - fetch it (`git fetch origin "$FLOW_HEAD_SHA"`), check it out into a scratch worktree, or read it through the API - and it must exit non-zero when it cannot see that head. `$FLOW_BASE_REF`, `$FLOW_PR_NUMBER`, and `$FLOW_SPEC_ID` carry the rest of the context.

### Dry-run stops here (R17)

`LAND_DRY_RUN == 1` → print the full classification report per PR (CI tri-state read with bucket counts, review-signal state, unresolved count, window age, ledger state, would-be action) plus the discovery table, then the aggregated terminal line computed by the Phase 4 worst-severity rule with the reason prefixed `dry-run: no mutations —`. **When `AUTO_REVIEW_SOURCE == comment`, the review-signal line names the comment path and its evidence** — e.g. `review: silence satisfied via clean-review comment (AUTO_REVIEW_EVIDENCE)` — so a transcript reader sees a comment, not a formal review, carried the gate; a report that hid the comment path has broken this. **When `land.mergeVerdictCommand` is set and the would-be action is `merge`, the report states `mergeVerdict=would-run: <command>`** (§2.9) - the command is NOT executed, because the zero-mutation promise covers it exactly as it covers the review trigger's would-trigger. Nothing was checked out, pushed, labeled, merged, dispatched, executed, or written (ledger untouched).

Done when: every discovered PR has one planned action class and a provisional verdict, and the tree, ledger, and remote are untouched.

## Phase 3 — ACT (at most ONE action class per PR per tick)

Execute each PR's planned action serially. **Every checkout is bracketed by branch hygiene**: record `ORIG_BRANCH` (Preamble), and after the per-PR action `git checkout "$ORIG_BRANCH"` + assert the non-`.flow/` tree is clean before the next PR and before tick end. A tick that moved to the next PR from a foreign branch or a dirty tree has broken this — a dirty tree after an action gives that PR verdict `NEEDS_HUMAN` and ends the tick there (no further PRs; report what happened).

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

     Then: **the edits stay scoped to the failing surface, and staging names only the files you edited** — a `git add -A` in this path has broken this. Run the repo's matching local validation when discoverable; commit `fix(ci): <what>`; `git push`.
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

**The gate reads exactly one thing: resolve-pr's machine-readable terminal line** `RESOLVE_PR_VERDICT=<RESOLVED|PENDING|NEEDS_HUMAN> threads=<n> fixed=<n> needs_human=<n>` — the last line of its output. A verdict inferred from its narration has broken this:

- `RESOLVED` → re-check convergence read-only for the report (resolve-pr's fix commits pushed → the patience window restarted, so the PR re-enters `AWAITING_REVIEW`; with reply-only resolution the window may already be satisfied — the merge still waits for the NEXT tick: one action class per PR per tick). Verdict `RESOLVING`.
- `PENDING` → threads replied, waiting on reviewers → verdict `RESOLVING`; next tick re-checks.
- `NEEDS_HUMAN` → apply the durable label (3.4) + verdict `NEEDS_HUMAN` (resolve-pr's bounded 2 fix-verify cycles already escalated).
- No terminal line (crash) → verdict `NEEDS_HUMAN`, no label (transient — a label needs a human to remove).

resolve-pr pushes commits itself when it fixes code; if it pushed, run the canonical post-push ledger write from 3.1 step 4 — read the fresh state via `gh pr view "$PR_NUMBER" --json headRefOid,reviewDecision` and write BOTH `land_pushed_sha` (the new `headRefOid`) and `decision_at_push` (the `reviewDecision` at push time, `-` when empty). Restore `ORIG_BRANCH` if resolve-pr left the worktree elsewhere; assert clean.

### 3.3 — `catch-up` (server-side, merge-based — land never rebases and never force-pushes)

```bash
CATCHUP_RC=0
CATCHUP_ERR="$(gh pr update-branch "$PR_NUMBER" 2>&1 >/dev/null)" || CATCHUP_RC=$?
```

One API call, no local checkout: GitHub merges `$BASE_REF` into the PR's head branch server-side (`gh pr update-branch` is merge-based by default — land never passes `--rebase`).

- `CATCHUP_RC != 0` → verdict `BLOCKED`, reason `base merge conflicts need hand-resolution: <CATCHUP_ERR>`. GitHub refuses the update precisely when the merge would conflict, so the conflict verdict is the server's — land still never hand-resolves a hunk.
- `CATCHUP_RC == 0` → run the canonical post-push ledger write from 3.1 step 4, sourcing the new head from `gh pr view "$PR_NUMBER" --json headRefOid` (no local checkout exists to read it from): `land_pushed_sha` = that `headRefOid`, `decision_at_push` = the Phase 2 `REVIEW_DECISION`. Verdict `RESOLVING` (the update advances the head, so the patience window restarts and the next tick re-gates).

The worktree never moves in this path — no `gh pr checkout`, no branch restore, nothing to assert clean afterwards.

**This removes land's force-push capability entirely.** No `git rebase`, no `--force-with-lease`: the PR's commit SHAs survive the catch-up, so the evidence recorded against them stays reachable — that is #302's orphaned-evidence CAUSE removed for every repo, not merely detected. Nothing observable is traded for the merge commit: land always squash-merges, so the branch-local shape disappears at merge time either way. Fork PRs are unchanged — `update-branch` fails on a fork whose maintainer-edit permission is off exactly as the old force-push failed → `BLOCKED`, no regression.

### 3.4 — `label` (durable needs-human marker)

```bash
gh label create "flow-next:needs-human" --description "flow-next land: needs human attention" --color "D93F0B" 2>/dev/null || true
gh pr edit "$PR_NUMBER" --add-label "flow-next:needs-human"
```

Verdict `NEEDS_HUMAN` with the planned reason. Later ticks skip the PR at gate 2.1 while the label is present.

### 3.5 — `merge` + post-merge tail

All gates passed in-tick. Pin the head right before merging. When §2.9 ran green, the pin is the exact head the verdict command judged - re-reading a fresher head here would merge a commit no verdict covered; the `--match-head-commit` guard then refuses a moved head server-side and the PR re-gates next tick (`RESOLVING`), which is the fail-closed direction:

```bash
# MERGE_VERDICT / MERGE_VERDICT_HEAD / MERGE_VERDICT_BASE = THIS PR's
# recorded values from its §2.9 classification (per-PR state).
MV_STALE_BASE=0
if [[ "$MERGE_VERDICT" == "green" && -n "$MERGE_VERDICT_HEAD" ]]; then
  # A base that moved since judgment (an earlier PR in this tick merging is
  # the common cause) means the verdict covered a different merge target.
  BASE_NOW="$(git ls-remote origin "refs/heads/$BASE_REF" | cut -f1)"
  if [[ -z "$BASE_NOW" || "$BASE_NOW" != "$MERGE_VERDICT_BASE" ]]; then
    MV_STALE_BASE=1
  fi
  HEAD_OID="$MERGE_VERDICT_HEAD"   # §2.9 judged exactly this head - never a fresher one
else
  HEAD_OID="$(gh pr view "$PR_NUMBER" --json headRefOid --jq .headRefOid)"
fi
if [[ "$MV_STALE_BASE" == 1 ]]; then
  echo "Evidence: merge-verdict stale (base moved since judgment: $MERGE_VERDICT_BASE -> ${BASE_NOW:-unresolvable}) - no merge"
  # Verdict RESOLVING for this PR - the next tick re-gates and re-judges.
  # STOP HERE for this PR: no gh pr ready, no merge, no post-merge tail.
else
  [[ "$IS_DRAFT" == "true" ]] && gh pr ready "$PR_NUMBER"   # idempotent flip; non-draft skips
  # PR-merge seam (#337), same shape as make-pr's `FLOW_PR_CREATE_CMD` (#277).
  # FLOW_PR_MERGE_CMD names the command that MERGES the PR; default
  # `gh pr merge`. Repos that require an App/bot to perform the merge (branch
  # protection that excludes the human identity the tick runs as) point it at
  # a wrapper that supplies its own identity. ENV ONLY - never a `land.*`
  # config key: §2.9's trust guard exists because config-sourced command
  # strings are PR-author-influenceable on a non-base checkout; session env is
  # not.
  # Contract (STABLE - integrators depend on it):
  #   - invoked exactly as, in this fixed argument order:
  #       $FLOW_PR_MERGE_CMD <pr> --squash --delete-branch --match-head-commit <sha>
  #   - the expansion is whitespace-split, never eval'd - the command path must
  #     not contain spaces; everything after it arrives as pre-quoted arguments
  #   - success: exit 0 and the PR is merged. Nonzero = not merged
  #   - the wrapper MUST proxy gh's stderr VERBATIM. Only stderr is captured
  #     here, and the classification below splits head-race (`RESOLVING`,
  #     re-tick) from policy refusal (`BLOCKED`) by reading gh's
  #     head-mismatch text. A wrapper that swallows or rewrites stderr turns
  #     benign races into `BLOCKED` PRs
  #   - never `--auto`, never merge-queue enrollment - the merge stays explicit
  #     (the merge-license boundary binds the interposed command too)
  #   - `--delete-branch` needs a second permission (branch delete) that a
  #     merge-only App may lack; grant it or the merge succeeds and the branch
  #     survives
  # Scope: THIS merge call ONLY. `gh pr ready` above, the post-merge
  # mergeCommit read, the tail, and every other gh call in the tick stay on the
  # session identity, and `gh` stays a preflight requirement.
  MERGE_CMD="${FLOW_PR_MERGE_CMD:-gh pr merge}"
  MERGE_RC=0
  MERGE_ERR="$($MERGE_CMD "$PR_NUMBER" --squash --delete-branch --match-head-commit "$HEAD_OID" 2>&1 >/dev/null)" || MERGE_RC=$?
  if [[ "$MERGE_RC" -ne 0 ]]; then
    echo "Evidence: merge refused (rc=$MERGE_RC) — $MERGE_ERR"
  fi
fi
```

**The merge is always explicit, never `gh pr merge --auto`.** And **`MERGE_RC != 0` skips the whole post-merge tail** — a tail step that ran after a non-zero merge has broken this. Classify from the captured stderr, leave the worktree where it is (no checkout happened yet), and continue to the next PR:

- Head-SHA mismatch refusal (the `--match-head-commit` guard; stderr names the expected/actual sha) — state moved between gate and merge → verdict `RESOLVING` (re-tick), not `BLOCKED`.
- Any other merge refusal (server-side rule) → verdict `BLOCKED`, reason = the captured `MERGE_ERR` line.

Only on `MERGE_RC == 0`, move the worktree onto the merged base BEFORE any tail step — `spec close`, the tracker touchpoint, and release-follow all run from the clean base checkout, never from the (deleted) PR branch or a stale original branch:

```bash
git checkout "$BASE_REF" && git pull --ff-only
TAIL_BASE_OID="$(git rev-parse HEAD)"   # pre-tail base tip — step 4's rollback target
MERGE_OID="$(gh pr view "$PR_NUMBER" --json mergeCommit --jq '.mergeCommit.oid')"
TAIL_OK=1
if [[ -z "$MERGE_OID" ]] || ! git merge-base --is-ancestor "$MERGE_OID" HEAD; then
  echo "Evidence: squash commit ${MERGE_OID:-<unknown>} not on local $BASE_REF after pull"
  TAIL_OK=0
fi
git log --oneline -1   # evidence echo: the squash commit referencing the PR
```

`TAIL_OK == 0` → verdict `NEEDS_HUMAN` for this PR, reason `squash commit missing from local base — tail not run`. **No tail step runs in that state** — no spec close, no tracker, no release; one that did has broken this. Continue to the next PR; a later tick re-enters via the merged-but-unclosed path once the base is fixed. Only with `TAIL_OK == 1` run the tail, in order:

1. **Spec close — local commit, NOT pushed here (#345)** — `"$FLOWCTL" spec close "$spec" --json`. flowctl hard-requires all tasks done; stray non-done tasks at close time → verdict `NEEDS_HUMAN`, reason `spec close refused: <flowctl error>` (report, never force) — the merge stands, a later tick re-enters via the merged-but-unclosed path after a human fixes the task state. Commit the close file-scoped and move on; the push is step 4:

   ```bash
   git add ".flow/specs/${spec}.json" ".flow/specs/${spec}.md" && git commit -m "chore(flow): close ${spec} (landed PR #${PR_NUMBER})"   # stage ONLY this spec's files — pre-existing .flow dirtiness (allowed by the guards) must not ride the close commit
   ```

   **Committing here rather than pushing here is what keeps the rest of the tail reachable on a base that only accepts pull requests** — such a base refuses the push permanently, and persisting first meant one refusal skipped release-follow and the tracker touchpoint after a real merge. Both later steps are safe with the close committed but unpushed: release-follow's precondition is a clean non-`.flow/` tree, which the *commit* satisfies, and the tracker touchpoint gates on its own fresh GitHub `MERGED` probe (step 3), never on the close having been pushed. The tracker touchpoint stays after release-follow so its verdict comment can carry the release outcome, and it commits its own sync state locally for the same step-4 push.
2. **Release-follow** (only when `LAND_RELEASE == true`) — discovery order, first hit wins: `docs/RELEASING.md` → `RELEASING.md` → `agent_docs/releasing.md` → release docs referenced from CLAUDE.md/AGENTS.md → none (stop at merge, verdict `MERGED`). Bounds, all binding:
   - Deterministic, non-interactive commands from the discovered docs ONLY — no invented steps, no prompts, no secrets handling.
   - Clean non-`.flow/` tree required before starting and asserted after.
   - **Idempotency probe BEFORE acting**: check for an existing tag/GitHub release for the target version (`git tag -l <v>`, `gh release view <v>`); already present → resume past completed steps, never re-tag.
   - Release-step failure AFTER the successful merge → verdict `NEEDS_HUMAN` + durable label on the (merged) PR via 3.4 — the merge is NEVER retried, and later ticks never blindly re-run the failed step (re-entry only resumes via the idempotency probe).
   - Release completed → verdict `RELEASED`.
3. **Tracker touchpoint — the only `Done` driver (fn-66, R3/R10)** — deliberately after release-follow so the verdict comment can carry the release outcome. **`land.merged` is active-by-default whenever the bridge is active**, not gated behind `tracker.perEvent.land.merged != off`. This is deliberate (fn-66, R10): a real merge is the only event that legitimately projects `Done`, so leaving it opt-in would let boards stick at `In Review` forever after a merge. Like make-pr's unconditional PR-link path, the merge→Done projection rides the bridge-active predicate alone; a run that gated the status on the `land.merged` leaf has broken this (the leaf, if a repo set it, only tunes the optional verdict comment):

   The complete `tracker.perEvent.land.merged` mapping is explicit: for
   `off`, `pull`, `push`, `reconcile`, and `comment`, a confirmed merge resolves
   to facade op `push`; an unconfirmed merge resolves to facade op `comment`.
   The leaf never gates the terminal status. Land synthesizes comment content by
   name: merged PR URL plus release outcome, or the failed merge-probe diagnostic.

   ```bash
   TRACKER_FIRE=0
   if [ "$("$FLOWCTL" sync active --json | jq -r '.active')" = "true" ]; then
     TRACKER_FIRE=1   # active-by-default — no perEvent gate (fn-66, R10)
   fi
   ```

   **Self-check the `MERGED` probe before dispatching the terminal push (fn-66, R3).** This touchpoint runs from the post-merge tail, but **it never trusts the caller's claim of a merge** — it re-confirms GitHub reports the linked PR `MERGED` for the spec branch. **The probe is fresh, run after `gh pr merge` succeeded and before `TRACKER_TERMINAL_OK` is decided** (this also covers the re-entry path, where the pre-merge probe already saw `MERGED`); reusing the Phase 3.5 `MERGED_PR_NUM` has broken this — on the normal babysit path the PR was `OPEN` at discovery, so that variable is empty even though land just merged it. The merge-evidence invariant binds the **outbound terminal write** and is enforced at the source: **a probe that is not a clean `MERGED` dispatches no `Done` push** (fall back to a non-terminal comment or `NEEDS_HUMAN`), so no path writes `Done` without merge evidence:

   ```bash
   # Fresh post-merge re-probe — NEVER the stale Phase 3.5 MERGED_PR_NUM (empty on the
   # normal OPEN→merge path). This is the authoritative merge-evidence read for the gate.
   MERGED_CONFIRMED="$(gh pr list --head "$BRANCH_NAME" --state all --json state \
     | jq -r '[.[] | select(.state == "MERGED")] | length')"
   if [ "$TRACKER_FIRE" = "1" ] && [ "${MERGED_CONFIRMED:-0}" -gt 0 ]; then
     TRACKER_TERMINAL_OK=1   # GitHub-confirmed MERGED → the gate is satisfied
   else
     TRACKER_TERMINAL_OK=0   # no clean MERGED → comment only, never terminal
   fi
   ```

   `TRACKER_FIRE == 1` → invoke the inline flow-next-tracker-sync wrapper. It
   prepares the approved mode `0600` inputs, makes exactly one fn-140 lifecycle
   facade call, deletes the inputs, and routes any structured recovery.
   For the terminal branch it writes the synthesized merge/release verdict to
   a distinct `COMMENT_FILE`; the tracker-rendered issue body remains the
   regular `--body-file`. Every verdict-comment file starts with the stable
   merge identity `evidence=<merge-commit-sha>`; retries of the same merge
   deduplicate, while a different merge cannot collapse into that marker.
   **The `TRACKER_TERMINAL_OK` self-check selects the operation** — land branches
   on its own GitHub-`MERGED` probe rather than on the caller's merge claim
   (fn-66, R3):

   - **`TRACKER_TERMINAL_OK == 1`** (clean GitHub `MERGED`) → dispatch the terminal `push`:

     ```bash
     "$FLOWCTL" tracker sync "$spec" --op push --event land.merged \
       --comment-file "$COMMENT_FILE" <other legal file flags>
     ```

     The `push` projects the just-closed spec; the tracker-sync skill's own `flowToNormalized(spec, merged)` gate (status-sync.md S-I) resolves the terminal rung — `verified` if completion review shipped, else `done` — so status who-wins flips the issue to the merge-confirmed terminal state, ALSO posting the merge/release verdict comment (include `merged PR: <PR_URL>` and, when the release step ran, the released version). The Done write is **double-gated** (this caller's probe AND the skill's own merge-evidence gate).

   - **`TRACKER_TERMINAL_OK == 0`** (no clean `MERGED` — e.g. the post-merge probe came back empty/ambiguous, a corruption signal) → do NOT dispatch a terminal `push`. Dispatch the **comment-only** path instead and surface `NEEDS_HUMAN`, so no path writes `Done` without merge evidence:

     ```bash
     "$FLOWCTL" tracker sync "$spec" --op comment --event land.merged --body-file "$BODY_FILE" # verdict comment only
     ```

   Best-effort either way: a dispatch failure or tracker error surfaces as a stderr warning in the PR's evidence block and NEVER changes the PR's verdict (the close and any release already stand). Commit any tracked sync state the touchpoint updated, locally and file-scoped (`git add ".flow/specs/${spec}.json" .flow/sync-runs && git commit -m "chore(flow): sync state for ${spec} land.merged touchpoint"` — file-scoped so pre-existing .flow dirtiness never rides along; it carries this spec's sync state + receipts only). **This commit is not pushed here** — it rides step 4's single push together with the close commit, and shares that step's rollback.
4. **Persist — push the tail's `.flow` commits (close + any tracker sync state) together.** Last, after every consequential step has already run. The dirty-tree guards exclude `.flow/`, so an unpushed close would silently sit forever while every other clone (and CI) still sees the spec open:

   ```bash
   git push || { git pull --rebase && git push; }
   ```

   If the push STILL fails, ROLL BACK exactly what this step failed to persist — the tail's local `.flow` commits — so the merged-but-unclosed re-entry path stays reachable from this clone (discovery selects `status == "open"` specs only — a stranded local `done` would orphan the tail):

   ```bash
   git rebase --abort 2>/dev/null || true
   git reset --hard "$TAIL_BASE_OID"   # the pre-tail base tip; safe — every commit dropped was staged file-scoped and carries ONLY this spec's close/sync state
   ```

   Then verdict `NEEDS_HUMAN`, reason `spec close not pushed`. **The rollback is scoped to THIS step and skips NOTHING else** — the merge, release-follow, and the tracker touchpoint already ran and stand; on a pull-request-only base the residue is a cosmetic bookkeeping note, not a stalled lifecycle. Re-ticking after a refused persist is safe by construction: `spec close` succeeds idempotently, release-follow's idempotency probe (step 2) resumes past completed steps and never re-tags, and every verdict comment starts with the stable merge identity `evidence=<merge-commit-sha>` (step 3), so a repeat touchpoint for the same merge deduplicates.

Verdict `MERGED` (or `RELEASED`). On success, drop the PR's ledger entry (atomic `jq 'del(.[$pr])'` + `mv`). End on the base branch with a clean tree (the original branch may have been the now-deleted PR branch — the base IS the restore target after a merge).

### 3.6 — `resume-tail` (re-entry idempotency)

A merged-but-unclosed spec resumes the tail exactly as 3.5 post-merge: checkout base + `git pull --ff-only` + verify the merge commit (via `gh pr view <MERGED_PR_NUM> --json mergeCommit`), then spec close (local commit) → release-follow → tracker touchpoint → persist-push of the tail's `.flow` commits. Never a second merge, never an error for already-completed steps (the release idempotency probe skips them; `spec close` succeeds idempotently on an already-closed spec; the touchpoint's verdict comment dedupes on the merge identity). A previous tick that reached the merge but had its persist refused re-enters here and re-runs the whole tail — the earlier release and tracker work is not repeated destructively, and a second refusal again costs only the bookkeeping note. Verdict `MERGED`/`RELEASED` per how far the tail ran.

Done when: each PR has had exactly one action class executed, the worktree is back on `ORIG_BRANCH` (or the merged base after 3.5/3.6), and the non-`.flow/` tree is clean.

## Phase 4 — REPORT

Echo one evidence block per PR processed:

```text
PR <url> [<spec-id>]
  ci=<green|red|pending|none> checks=<pass>/<total> unresolved=<n> window=<AGE_MIN>/<PATIENCE_MIN>m
  signal=<silence|approve|login>:<satisfied|waiting|never> decision=<reviewDecision|->
  action=<ci-fix|resolve|catch-up|merge|resume-tail|label|none> verdict=<VERDICT> reason="<one line>"
  mergeVerdict=<green|refused|skipped|would-run>
```

`mergeVerdict` reports §2.9: `skipped` when `land.mergeVerdictCommand` is off or the planned action was not `merge`, `would-run` under `--dry-run`, `green`/`refused` from the command's exit code.

When the `silence` signal was satisfied via the clean-review comment path (`AUTO_REVIEW_SOURCE == comment`, fn-65.1), append the comment evidence to the `signal=` line so the report shows the gate passed on a comment, not a formal review — e.g. `signal=silence:satisfied via=comment evidence="<AUTO_REVIEW_EVIDENCE>"`.

Compute the tick verdict as the worst severity across all per-PR verdicts, priority order:

```text
NEEDS_HUMAN > BLOCKED > FIXING_CI > RESOLVING > AWAITING_REVIEW > RELEASED > MERGED
```

`pr=` in the terminal line is the URL of the deciding PR (first PR carrying the worst verdict); `prs=` is the count of PRs processed (babysit + re-entry + discovery NEEDS_HUMAN entries). Zero processed PRs → `NO_WORK` with `prs=0 pr=-`.

Assert tick-end hygiene before printing: current branch is `ORIG_BRANCH` (or the merged base when 3.5/3.6 ran) and the non-`.flow/` tree is clean — a violation downgrades the tick to `NEEDS_HUMAN` with the hygiene failure as the reason.

```text
LAND_VERDICT=<verdict|NO_WORK> prs=<n> pr=<deciding-pr-url|-> reason="<one line>"
```
