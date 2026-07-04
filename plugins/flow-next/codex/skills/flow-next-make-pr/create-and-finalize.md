# make-pr — create + finalize (Phase 4.1 → Phase 5), loaded on a real create

> Read this ONLY after Phase 4.0's `--dry-run` short-circuit does NOT fire — i.e. an actual PR is
> being created/updated. It is the post-render create + finalize machinery (title, body persist,
> truncation, tracker linkage, `gh pr create`/`gh pr edit`, retry loop, failure hints, Phase 5
> receipt + footer + PR_URL emission). Split out of the always-loaded workflow.md so the render
> path (Phases 0-3) + the `--dry-run` preview never pay its ~9k tokens.

### 4.1 — PR title format (R21)

Compute the PR title from the spec before push so it's ready for `gh pr create` (§4.6). Priority:

1. **Spec title verbatim** if `len(spec.title) <= 72`.
2. **First sentence of `spec.spec_sections.goal_and_context`** truncated to 70 chars + `…` (single Unicode ellipsis) when spec title is empty OR exceeds 72.

```bash
SPEC_TITLE=$(printf '%s' "$SPEC_JSON" | jq -r '.title // ""')
GOAL_FIRST_SENTENCE=$(printf '%s' "$SPEC_JSON" | jq -r '(.spec_sections.goal_and_context // "") | split(". ")[0]')

if [[ -n "$SPEC_TITLE" && "${#SPEC_TITLE}" -le 72 ]]; then
 PR_TITLE="$SPEC_TITLE"
elif [[ -n "$GOAL_FIRST_SENTENCE" ]]; then
 if [[ "${#GOAL_FIRST_SENTENCE}" -gt 70 ]]; then
 PR_TITLE="${GOAL_FIRST_SENTENCE:0:70}…"
 else
 PR_TITLE="$GOAL_FIRST_SENTENCE"
 fi
else
 PR_TITLE="$SPEC_ID" # last-resort fallback; spec id is always populated
fi
```

**No automatic Conventional-Commits prefix injection.** The boundary is correct per spec — flow-next-self-use specs carry their `chore(.flow):` / `feat(flow-next):` / `fix(flow-next):` prefix in the spec title already. Other repos with different conventions won't get unwanted prefixes added. The skill is not opinionated about commit message format; it mirrors the spec title verbatim.

If the spec title contains characters problematic for shell quoting (single-quotes, backticks), they survive intact through `--title` because we pass the variable directly without re-interpreting. `gh` itself accepts the title argument as one shell token — no escaping needed.

### 4.2 — Draft-vs-ready matrix (R24)

Compute `DRAFT_FLAG` from a four-input matrix: `OPEN_ITEMS_COUNT`, Ralph context, `--draft` force flag, `--ready` force flag. **Resolution order: explicit force flags win over context-derived defaults.** This is the smart draft/ready default the autonomous create relies on: draft when `OPEN_ITEMS_COUNT > 0` (or Ralph / autonomous / `--draft`), ready otherwise (or `--ready`).

```bash
# Default state — neither flag forced; let context decide.
DRAFT_FLAG=""

# Layer 1: Ralph OR autonomous mode forces draft (autonomous-loop opens-for-human-review default).
if [[ "$RALPH" == "1" || "$AUTONOMOUS" == "1" ]]; then
 DRAFT_FLAG="--draft"
fi

# Layer 2: Open items default to draft (incomplete state shouldn't go straight to ready).
# OPEN_ITEMS_COUNT comes from Phase 1 — counts spec open_questions + deferred_findings + spec-completion-review needs_work flag.
if [[ "$OPEN_ITEMS_COUNT" -gt 0 ]]; then
 DRAFT_FLAG="--draft"
fi

# Layer 3: Explicit --draft force.
if [[ "$DRAFT_FORCE" == "draft" ]]; then
 DRAFT_FLAG="--draft"
fi

# Layer 4: Explicit --ready force overrides everything except Ralph/autonomous.
# Layer 1 is a hard invariant — autonomous loops (Ralph or pilot) MUST NOT open ready PRs even with --ready in args.
if [[ "$DRAFT_FORCE" == "ready" && "$RALPH" != "1" && "$AUTONOMOUS" != "1" ]]; then
 DRAFT_FLAG=""
fi

# Conflict surfacing: --draft AND --ready in the same invocation is the SKILL.md last-flag-wins rule.
# DRAFT_FORCE captured the last one already; this layer just makes the conflict legible at runtime.
if [[ "$DRAFT_FORCE" == "ready" && ( "$RALPH" == "1" || "$AUTONOMOUS" == "1" ) ]]; then
 echo "Note: --ready ignored under Ralph/autonomous mode. PR will open as draft (autonomous-loop terminus)." >&2
fi
```

**Matrix summary:**

| Context | OPEN_ITEMS | --draft | --ready | Result |
|---------|-----------|---------|---------|--------|
| Interactive | 0 | — | — | ready |
| Interactive | >0 | — | — | draft |
| Interactive | — | yes | — | draft |
| Interactive | 0 | — | yes | ready |
| Interactive | >0 | — | yes | **ready** (user forced) |
| Ralph / Autonomous | 0 | — | — | draft |
| Ralph / Autonomous | — | — | yes | draft (autonomous always draft) |
| Ralph / Autonomous | — | yes | — | draft |

`--draft` and `--ready` in the same invocation is handled by SKILL.md mode-detection's "last-flag-wins" rule — `DRAFT_FORCE` ends up as whichever flag appeared last in `$ARGUMENTS`. The conflict isn't a hard error.

**OPEN_ITEMS_COUNT derivation** (combines Phase 1's payload with the separate spec-completion-review status from §2.11 Source C):

```bash
# Sources A + B come from EXPORT_PAYLOAD (spec open_questions + deferred_findings).
PAYLOAD_OPEN=$(printf '%s' "$EXPORT_PAYLOAD" | jq '
 ( (.spec.spec_sections.open_questions // []) | length ) +
 ( ([(.deferred_findings // [])[] | (.items // [])[]] | length) )
')

# Source C — spec-completion-review verdict. Read directly from the spec JSON;
# the export-cognitive-aid payload v1 emits review_receipts as a list ([]) —
# NOT an object — so indexing it with a key like .completion_review_status
# would throw "Cannot index array with string" under `set -e` and abort the
# skill. Reuse the same flowctl path §2.11 Source C uses.
SPEC_REVIEW_STATUS=$("$FLOWCTL" show "$SPEC_ID" --json | jq -r '.completion_review_status // "unknown"')
SPEC_REVIEW_OPEN=0
if [[ "$SPEC_REVIEW_STATUS" == "needs_work" ]]; then
 SPEC_REVIEW_OPEN=1
fi

OPEN_ITEMS_COUNT=$(( PAYLOAD_OPEN + SPEC_REVIEW_OPEN ))
```

This same count drives both the §2.11 Open items section bullet count and the draft-flag layer 2 default. Single source of truth — no recompute risk.

### 4.3 — Body delivery via `--body-file` (R20 refinement)

Persist the rendered body to a tempfile so §4.6 can hand it to `gh pr create --body-file` (and `--dry-run` at §4.0 can print it for inspection). Use `--body-file`, never a heredoc: LLM-generated body content contains backticks / `$` / quotes the shell re-interprets on the way to `gh`, corrupting heredoc input; `--body-file` sidesteps it.

```bash
BODY_FILE=$(mktemp -t make-pr-body-XXXXXX.md)
trap 'rm -f "$BODY_FILE"' EXIT

# Host agent's Write tool emits the rendered body string into "$BODY_FILE".
# (Phase 2/3 produced the body content; this is the persistence step.)
# Cross-platform note: sync-codex.sh leaves Write as Write — same tool on Codex.
```

After the Write call, validate the file is non-empty before proceeding to push + create:

```bash
if [[ ! -s "$BODY_FILE" ]]; then
 echo "Error: rendered body is empty. Phase 2/3 produced no content — re-check abort conditions (§2.7)." >&2
 exit 1
fi
```

**Anti-pattern (do not do this):**

```bash
# DO NOT — heredoc content leaks shell metacharacters
gh pr create --body "$(cat <<EOF
$BODY_CONTENT
EOF
)"
```

The heredoc form survives simple bodies but fails on (a) backtick-wrapped code refs (the shell tries to execute), (b) `$variable` substitution (literal `$module_name` in markdown becomes empty), (c) escaped quotes inside markdown tables. `--body-file` is the only reliable form.

### 4.4 — Body length cap + truncation policy

`gh pr create` accepts up to ~65,536 characters in `--body-file` (GitHub PR API limit; `gh` surfaces it as a 422). Our internal soft cap is **65,000 chars** to leave headroom for the footer breadcrumb. When the rendered body exceeds the cap, truncate in this priority order (most-droppable first):

1. **Drop the full file list** in `## Where to look` if present — replace with `(file list elided; see diff)`.
2. **Trim TL;DR** to 3 bullets if currently 4-5 — keep only the top-priority headline + top 2 task-derived bullets.
3. **Collapse mermaid section** to overview-only — replace multi-diagram structure with one `graph TB` overview + the lead prose paragraph.
4. **Last resort: spill to `.flow/pr-bodies/<spec-id>.md`** — write the full body to that path, replace PR body with: `# <spec-title>\n\nFull cognitive-aid body exceeds 65K char limit. Read at \`.flow/pr-bodies/<spec-id>.md\` (committed alongside this PR).` Then `git add .flow/pr-bodies/ && git commit -m "chore: spill PR body for <spec-id>"` before push.

```bash
BODY_BYTES=$(wc -c < "$BODY_FILE" | tr -d ' ')
if [[ "$BODY_BYTES" -gt 65000 ]]; then
 : "host agent runs the truncation cascade above"
 : "(1) drop file list (2) trim TL;DR (3) collapse mermaid (4) spill to .flow/pr-bodies/"
fi
```

In practice the cap rarely trips — a typical cognitive-aid body is 4-12K chars. The cap exists for the pathological "20-task spec with 50-row R-ID coverage table + 3 mermaid diagrams + 30 deferred findings" case. For any normal flow-next spec, this section is unreachable. Document it so the failure mode is visible, not so the path is hot.

### 4.5 — No confirm gate — create directly (autonomous)

**make-pr does not ask the user to confirm before opening the PR.** Invoking `/flow-next:make-pr` IS the intent; the body is deterministically rendered from structured state (low hallucination risk); the default is a **draft** when there are open items (reversible). Asking "create / dry-run / edit / abort" was friction that fought the project's "host agent IS the intelligence, minimize touchpoints" ethos — it is **removed**. Interactive and Ralph now both flow from §4.4 (body persisted) straight into §4.6 (push + create); the only difference is the draft decision (§4.2): interactive uses the smart `OPEN_ITEMS_COUNT` heuristic, Ralph forces `--draft`.

The escape hatches are the **flags**, not a prompt:
- `--dry-run` — render the body to stdout and exit 0 **before** any push / `gh pr create` (the "let me see it first" path; handled at §4.0).
- `--ready` / `--draft` — override the draft/ready decision.
- Want to hand-edit the body? `--dry-run | pbcopy`, edit, or edit the PR on GitHub after it opens (it's a draft).

`plain-text numbered prompt` is still used in **Phase 0** — but only to resolve genuinely-missing info make-pr cannot derive (no base ref and no detection match; no spec detected). Those are *information* prompts, not a confirm gate, and are rare. A spec with not-all-tasks-done no longer blocks on a prompt — it **warns to stderr and proceeds** (the open items make it a draft anyway; §0 / §4.2).

### 4.6 — Push branch + `gh pr create` retry loop (R20 refinement)

Reached directly after §4.4 (body persisted) — no confirm gate. `git push -u origin HEAD` first; **then** wait one second (cli/cli #2691 — GitHub's API trails the git protocol push by tens to hundreds of milliseconds, with the worst observed lag in single-digit seconds). After the sleep, run `gh pr create` inside a 3-attempt retry loop that catches **only** the eventual-consistency error class. Other errors (auth, body too long, PR already exists) fail fast.

```bash
# Resolve current branch BEFORE push. `gh pr create --head` needs an explicit
# branch name (Phase 0's PHASE0_CONTEXT.branch is JSON-only and not exported as
# a shell var here), and a detached HEAD has no branch to push or open a PR
# against — fail fast with a clear message rather than letting `gh` produce a
# cryptic "Head sha can't be blank" error after the push.
HEAD_BRANCH=$(git branch --show-current)
if [[ -z "$HEAD_BRANCH" ]]; then
 echo "Error: detached HEAD or empty branch name; cannot create PR. Check out a branch first." >&2
 exit 1
fi

# Push branch. We don't pre-check `git rev-parse @{push}` — the cost of a redundant
# push (zero-byte upload) is much smaller than the bug surface of a "skipped because
# we thought it was already pushed but it actually wasn't" path.
PUSH_OUT=$(git push -u origin HEAD 2>&1)
PUSH_RC=$?
if [[ "$PUSH_RC" -ne 0 ]]; then
 echo "Error: git push failed:" >&2
 echo "$PUSH_OUT" >&2
 exit 1
fi

sleep 1 # GitHub API eventual-consistency lag (cli/cli #2691)

# --update mode: the PR already exists (from §0.6, captured as $UPDATE_PR_NUMBER) and is
# already tracker-linked. Skip §4.6a linkage + the create retry loop below — just replace
# its body with the freshly-rendered content, then fall through to the receipt / PR_URL
# emission. The push above already landed the fix commits the refreshed body describes.
if [[ "${UPDATE_MODE:-0}" == "1" ]]; then
 # Re-derive the target PR number here (the §0.6 var does not survive across tool-call
 # bash blocks). $BODY_FILE is the known §4.4 tempfile path (same one create mode uses).
 UPDATE_PR_NUMBER=$(gh pr view --json number,state --jq 'select(.state=="OPEN") | .number' 2>/dev/null || true)
 if [[ -z "$UPDATE_PR_NUMBER" ]]; then
 echo "Error: --update: no open PR on this branch at edit time." >&2; exit 1
 fi
 if gh pr edit "$UPDATE_PR_NUMBER" --body-file "$BODY_FILE"; then
 PR_URL=$(gh pr view "$UPDATE_PR_NUMBER" --json url --jq '.url')
 echo "Updated PR #$UPDATE_PR_NUMBER body (refreshed against the current diff)." >&2
 else
 echo "Error: gh pr edit #$UPDATE_PR_NUMBER --body-file failed." >&2
 exit 1
 fi
 # PR_URL is set — the Ralph `PR_URL=` stdout line (§5.4) + receipts emit as usual.
fi
```

**When `UPDATE_MODE=1` the block above finished the PR (body refreshed against the current diff, `PR_URL` set) — SKIP the rest of §4.6 (the §4.6a tracker linkage + the `gh pr create` retry loop are CREATE-ONLY, and the PR is already linked) and proceed straight to §5.** Everything below in §4.6 runs only in create mode (`UPDATE_MODE != 1`):

```bash
# `gh pr create --base` expects a BRANCH name, not a remote-tracking ref —
# passing `origin/main` opens the PR against a branch literally named
# `origin/main` and fails. Phase 0.3's cascade prefers `origin/main` (then
# `main`, etc.) for the local git work (merge-base, diff, rev-list) — those
# all accept remote-tracking refs and benefit from the freshness of the
# remote tip. Strip the `origin/` prefix only at the gh boundary.
BASE_BRANCH="${BASE_REF#origin/}"

# 4.6a — PR↔issue linkage (any tracker). Put a NON-CLOSING reference to the tracker
# issue in the PR body BEFORE `gh pr create`, so the link forms at creation. This
# is what makes the integration auto-link the PR — and for Linear, what makes
# Linear Diffs render the PR inside the issue. Gate is just **bridge active** — no
# `makePr` opt-in: a reference line is zero-cost, side-effect-light hygiene and is
# the whole point. NON-CLOSING (`Ref`/`Refs`, never `Fixes`/`Closes`) so merge does
# NOT auto-complete the tracker issue — flow-next owns the lifecycle (R7/R10).
# Every probe here is fully non-fatal under `set -e`: each flowctl AND each jq is
# `2>/dev/null` + `|| true`, so an inactive bridge, a bridge with NO linked tracker
# id, malformed JSON, or a missing jq all degrade to an empty var → clean no-op,
# never aborting the run after the push but before `gh pr create`.
TRK_ACTIVE=$("$FLOWCTL" sync active --json 2>/dev/null | jq -r '.active // empty' 2>/dev/null || true)
if [ "$TRK_ACTIVE" = "true" ]; then
 TRK_TYPE=$("$FLOWCTL" config get tracker.type --json 2>/dev/null | jq -r '.value // empty' 2>/dev/null || true)
 TRK_STATE=$("$FLOWCTL" sync get-state "$SPEC_ID" --json 2>/dev/null || printf '{}')
 TRK_ID=$(printf '%s' "$TRK_STATE" | jq -r '.tracker.identifier // empty' 2>/dev/null || true)
 REF=""
 case "$TRK_TYPE" in
 linear) [ -n "$TRK_ID" ] && REF="Ref ${TRK_ID}" ;; # WOR-N → Linear auto-link + Diffs
 github) [ -n "$TRK_ID" ] && REF="Refs ${TRK_ID}" ;; # #N → native GitHub cross-reference
 gitlab) [ -n "$TRK_ID" ] && REF="Ref \`${TRK_ID}\`" ;; # <project>#<iid> in BACKTICKS → inline code, so GitHub does NOT autolink it as a cross-repo "owner/repo#N" reference (a GitLab key whose path also names a GitHub repo would otherwise mis-link to GitHub issue #N). A GitHub-PR ref can't link a GitLab issue anyway — the real cross-link is the §5.6 non-closing PR-URL note on the GitLab issue.
 jira) REF="" ;; # NO PR-body ref — Jira has neither PR auto-linkify (Linear) nor `gh` (GitHub), and a `PROJ-123` key in a GitHub PR body would not link the Jira issue anyway. The real cross-link is the §5.6 in-adapter **remote link** (POST /issue/{key}/remotelink) on the Jira issue (jira.md §makePr).
 esac
 # Idempotency: match the exact ref LINE (whole-line, case-insensitive), NOT any
 # substring — the cognitive-aid body already mentions the spec path
 # (.flow/specs/wor-17-slug.md), so a substring grep for "WOR-17" would
 # false-positive and silently skip the ref. `-x` whole-line + `-F` fixed-string.
 # Size: the §4.4 cap targets 65,000 chars (vs GitHub's ~65,536 hard limit), so the
 # ~25-char ref line fits within the reserved headroom — no re-cap needed.
 if [ -n "$REF" ] && ! grep -qixF "$REF" "$BODY_FILE"; then
 printf '\n\n---\n%s\n' "$REF" >> "$BODY_FILE"
 fi
fi

# Retry loop. Only retry on the eventual-consistency error class. Other errors
# fail fast — re-running gh pr create after a 422 (body too long) or 401 (auth)
# just produces the same error.
PR_URL=""
for attempt in 1 2 3; do
 CREATE_OUT=$(gh pr create \
 --title "$PR_TITLE" \
 --body-file "$BODY_FILE" \
 $DRAFT_FLAG \
 --base "$BASE_BRANCH" \
 --head "$HEAD_BRANCH" 2>&1) && { PR_URL="$CREATE_OUT"; break; }

 # Eventual-consistency error class — retry. Empirically validated during fn-42 spike:
 # even after `git push` returns 0 and `sleep 1` elapses, gh pr create can fail with
 # "Head sha can't be blank, Base sha can't be blank, No commits between main and X"
 # while the GitHub API still propagates the push.
 case "$CREATE_OUT" in
 *"Head sha can't be blank"*|*"No commits between"*)
 sleep $((attempt * 2)) # 2s, 4s, 6s — total worst-case 12s before bailing
 continue
 ;;
 esac

 # Any other error: fail fast.
 echo "Error: gh pr create failed:" >&2
 echo "$CREATE_OUT" >&2
 exit 1
done

if [[ -z "$PR_URL" ]]; then
 echo "Error: gh pr create failed after 3 retries on eventual-consistency error." >&2
 echo "Manual recovery: wait 30s and re-run /flow-next:make-pr (skill detects the existing branch and re-tries)." >&2
 exit 1
fi

# 4.6b — Post-create ref verify/repair (fn-57 R4). §4.6a appends the ref to the
# LOCAL body file before create — the guard exists to catch a hand-rolled
# `gh pr create` (or a stale / absent local file) that bypassed it, opening the
# PR without its issue link. Happy path asserts LOCALLY (cheap grep on
# $BODY_FILE — the file `gh pr create --body-file` just consumed — no network);
# the live `gh pr view` round-trip fires ONLY when the local append demonstrably
# did not run. $REF and $TRK_ACTIVE are the §4.6a-derived values and the matcher
# is the SAME whole-line `grep -qixF` — ONE derivation, all sites, no drift
# (substring matching would false-positive on the spec path in the body, see
# §4.6a). Fully non-fatal: the PR is already open; every step degrades to a
# no-op under `set -e`.
if [ "$TRK_ACTIVE" = "true" ] && [ -n "$REF" ]; then
 if grep -qixF "$REF" "$BODY_FILE" 2>/dev/null; then
 : # §4.6a append verified locally — the create consumed $BODY_FILE, so the
 # live PR carries the ref; skip the refetch.
 else
 # Bypass case — §4.6a didn't run against this file. Verify/repair on the
 # LIVE PR body.
 if LIVE_BODY=$(gh pr view "$PR_URL" --json body --jq .body 2>/dev/null); then
 if ! printf '%s\n' "$LIVE_BODY" | grep -qixF "$REF"; then
 # Append-only read-modify-write: `gh pr edit` has NO append flag, so
 # fetch→edit has a narrow window where a concurrent body edit would be
 # overwritten — documented, accepted race (bodies are regenerable).
 NEW_BODY=$(printf '%s\n\n---\n%s\n' "$LIVE_BODY" "$REF")
 # Re-check GitHub's 65,536-char hard cap: §4.4 capped the LOCAL body at
 # 65,000, but the LIVE body may differ — a near-cap body + ref can 422.
 if [ "${#NEW_BODY}" -le 65536 ]; then
 printf '%s\n' "$NEW_BODY" | gh pr edit "$PR_URL" --body-file - 2>/dev/null || true
 fi
 fi
 fi
 fi
fi
```

**`gh pr create` has NO `--json` flag** (verified by docs-scout and the `gh pr create --help` output). The PR URL lands on stdout as a single line; capture via `PR_URL=$(...)`. Don't try to pipe through `jq`.

`HEAD_BRANCH` is assigned at the top of §4.6 via `git branch --show-current` and validated non-empty before the push (matches the value of `PHASE0_CONTEXT.branch` from Phase 0, but resolved fresh in shell scope so the snippet is self-contained — `PHASE0_CONTEXT` is JSON, not exported as a shell var). Passing `--head` explicitly is defensive — `gh` defaults to the current branch when `--head` is omitted, but explicit beats implicit when the worktree might be in detached-HEAD or the user ran the skill from inside a git submodule. The detached-HEAD validation runs before push so the failure mode is "no branch, no push" rather than "push, then fail at gh pr create with a cryptic empty-`--head` error."

### 4.7 — Failure recovery hints

When `gh pr create` fails after the retry loop is exhausted, the skill emits manual-recovery instructions to stderr before exiting:

- **Eventual-consistency exhaustion** (3 retries): `Manual recovery: wait 30s and re-run /flow-next:make-pr (skill detects the existing branch and re-tries).` The branch is already pushed — only the PR creation step needs re-running.
- **Body too long (422)**: `Manual recovery: re-run with --no-mermaid (saves ~3-8K chars) or wait for the truncation policy to spill to .flow/pr-bodies/.` Should not happen because §4.4 truncation runs before invocation; if it does, the cap heuristic underestimated the body.
- **PR already exists (409)**: `An OPEN PR exists. /flow-next:resolve-pr addresses review feedback on the existing PR. To replace it, close the open one first via gh pr close.` Phase 0.6 should have caught this; if it slipped through, the user hit a race between Phase 0 check and Phase 4 push.
- **Authentication (401/403)**: `Run 'gh auth status' and 'gh auth login --hostname github.com' to re-authenticate.` Phase 0.1 should have caught this; if it slipped through, the token expired between Phase 0 and Phase 4.
- **Workflow-scope push rejection**: `git push` fails with `refusing to allow an OAuth App to create or update workflow .github/workflows/…` (or similar) when the branch touches workflow files and the HTTPS token lacks the `workflow` scope. Recovery: push via the SSH remote (`git push git@github.com:<owner>/<repo>.git HEAD`) or re-auth with `gh auth refresh -s workflow`, then re-run — the PR-create step itself is unaffected once the branch is up.

### Done when

- `--dry-run` short-circuits (§4.0) before any state change (no body persisted, no push, no PR, no memory). Body lands on stdout from the in-memory string. Exit 0.
- PR title computed (§4.1) via priority: spec title (≤72) → first sentence of `goal_and_context` (≤70 + `…`) → spec id fallback. No Conventional-Commits prefix injection.
- Draft flag computed (§4.2) via matrix layers (Ralph/autonomous → open items → `--draft` → `--ready`; layer 1 always wins). `--ready` ignored under Ralph/autonomous; conflict surfaced via stderr note.
- `OPEN_ITEMS_COUNT` derived once from the Phase 1 payload as `len(open_questions) + sum(deferred_findings.items) + (completion_review_status == "needs_work" ? 1 : 0)` — the same source feeds §2.11's Open items and §4.2 layer 2.
- Body delivered via `--body-file` (§4.3) — mktemp + cleanup trap. Heredoc form documented as anti-pattern with cli/cli #29619 citation.
- Body length cap (65,000 chars target) enforced (§4.4) via truncation cascade: drop file list → trim TL;DR → collapse mermaid → spill to `.flow/pr-bodies/`.
- **No interactive confirm gate** — make-pr creates the PR directly (autonomous). `--dry-run` (§4.0) is the inspection escape hatch; `--ready`/`--draft` override the draft decision. Phase 0 may still `plain-text numbered prompt` to resolve genuinely-missing info (base/spec), never to confirm.
- §4.6: `HEAD_BRANCH=$(git branch --show-current)` resolved + validated non-empty (rejects detached HEAD with a clear stderr error before any push — an empty `--head` would fail with a cryptic "Head sha can't be blank"), then §4.6a links the PR to the tracker issue (if active), then `git push -u origin HEAD`, then `sleep 1` (cli/cli #2691 eventual-consistency lag), then 3-attempt retry loop on the eventual-consistency error class (`Head sha can't be blank` / `No commits between`). Backoff `2s, 4s, 6s`. Other errors fail fast — auth (401/403), body-too-long (422), PR-already-exists (409) do NOT retry.
- `gh pr create --title --body-file --base --head [--draft]` invoked with `--base "${BASE_REF#origin/}"` (strip the remote-tracking prefix — `--base` expects a branch name, not `origin/main`). PR URL captured from stdout (single line; `gh pr create` has no `--json` flag).
- §4.6b (post-create, bridge active + ref derived): happy path asserts locally (whole-line `grep -qixF "$REF"` on `$BODY_FILE` — the file the create consumed; no network). Live PR body fetched (`gh pr view --json body`) ONLY when the local assertion fails (hand-rolled-create / stale-file bypass), then repaired append-only via `gh pr edit --body-file -` when absent, 65,536-char cap re-checked. Idempotent (ref already present → untouched) and fully non-fatal.
- Failure recovery hints (§4.7) printed to stderr before exit on each error class.

---

## Phase 5: Output + footer

**Goal:** print the success artefact (PR URL + breadcrumb) and run the optional `--memory` side effect. This phase fires only after `gh pr create` returned a URL on stdout.

### 5.0 — Success footer

```bash
cat <<EOF
✅ PR opened: $PR_URL

Next steps:
 - Reviewer feedback → /flow-next:resolve-pr ${PR_URL##*/}
 - Body inspection → /flow-next:make-pr $SPEC_ID --dry-run
EOF
```

`${PR_URL##*/}` extracts the trailing PR number from the URL (e.g. `https://github.com/foo/bar/pull/123` → `123`). The hint passes the PR number to `/flow-next:resolve-pr` so the reviewer-feedback flow runs without re-resolving the URL.

`/flow-next:make-pr ... --update` (regenerate PR body for an existing open PR) is **deferred to v2** — surface as a "TODO" in the next-steps hint only when the user has indicated they'd want it. v1 keeps the surface narrow.

### 5.1 — `--memory` side effect (R23)

When `$WRITE_MEMORY == 1`, write a `knowledge/architecture-patterns/` memory entry summarizing what shipped. **Idempotent** — if an entry tagged `spec-<SPEC_ID>` already exists, skip the write and emit a stderr note. Default off because every-PR memory inflation is the failure mode this gate prevents.

**Idempotency check:**

```bash
if [[ "$WRITE_MEMORY" == "1" ]]; then
 SPEC_TAG="spec-$SPEC_ID"
 EXISTING_ENTRY=$("$FLOWCTL" memory list --track knowledge --category architecture-patterns --json 2>/dev/null \
 | jq -r --arg tag "$SPEC_TAG" \
 '.entries[]? | select((.tags // []) | index($tag)) | .entry_id' \
 | head -1)

 if [[ -n "$EXISTING_ENTRY" ]]; then
 echo "Note: memory entry already exists for $SPEC_ID ($EXISTING_ENTRY) — skipping --memory write." >&2
 else
 : "compose body, call flowctl memory add (see §5.2)"
 fi
fi
```

The idempotency key is the `spec-<SPEC_ID>` tag, NOT a frontmatter `spec_id` field. The memory frontmatter validator (`validate_memory_frontmatter`) rejects unknown top-level fields — adding `spec_id` would produce a validation error. Tags are the canonical extension point.

`--memory` does not fire under `--dry-run` (covered in §4.0). It also does not fire when `gh pr create` failed — Phase 5 only runs after a successful PR creation in §4.6, so this is a natural sequence guarantee.

### 5.2 — Memory entry body shape

The entry body is fixed-template — host agent fills in the slots from the export payload. **No paraphrasing**, no editorialization. Same hallucination-guardrail discipline as the PR body itself.

```markdown
## What shipped

<spec.title> (PR <PR_URL>) — <first sentence of spec.spec_sections.goal_and_context>.

## R-IDs satisfied

R<i>, R<j>, R<k>. (Source: spec.spec_sections.acceptance_criteria, with task satisfies[] mapping.)

## Modules touched

`<module-1>`, `<module-2>`, `<module-3>`. (Source: diff_summary.modules_touched[].)

## Decisions captured

- **<title>** — <first_sentence>. (Source: memory_during_spec.decisions[].)

## Impact

<one-paragraph summary of what changed and why a future debugger searching for these symptoms would find this entry.>
```

If a section's source data is empty, omit the section heading entirely (same §2.6 omission rule as the PR body). The "Decisions captured" section is skipped when `memory_during_spec.decisions[]` is empty; "R-IDs satisfied" is skipped when `acceptance_criteria` is empty (rare).

The "Impact" section is the only host-agent-prose section. Two-to-four sentences, plain language, anchored to the modules and R-IDs above. **Never speculate about future work** ("this opens the door to..."). State what happened and why a future debugger would care.

### 5.3 — Memory entry write invocation

```bash
if [[ "$WRITE_MEMORY" == "1" && -z "$EXISTING_ENTRY" ]]; then
 MEMORY_BODY_FILE=$(mktemp -t make-pr-memory-XXXXXX.md)
 trap 'rm -f "$MEMORY_BODY_FILE" "$BODY_FILE"' EXIT

 # Host agent's Write tool emits the §5.2 body template into "$MEMORY_BODY_FILE",
 # filling slots from EXPORT_PAYLOAD.

 MEMORY_TITLE="$SPEC_TITLE — what shipped"
 if [[ "${#MEMORY_TITLE}" -gt 80 ]]; then
 MEMORY_TITLE="${MEMORY_TITLE:0:77}..."
 fi

 # Tags: spec-<id> (idempotency key) + first 2 modules_touched (search relevance) +
 # any glossary terms added (cross-link signal).
 MODULES=$(printf '%s' "$EXPORT_PAYLOAD" | jq -r '.diff_summary.modules_touched // [] | .[0:2] | join(",")')
 TAGS="spec-$SPEC_ID"
 [[ -n "$MODULES" ]] && TAGS="$TAGS,$MODULES"

 # Module field: most-touched module (first in modules_touched, already churn-sorted).
 PRIMARY_MODULE=$(printf '%s' "$EXPORT_PAYLOAD" | jq -r '.diff_summary.modules_touched // [] | .[0] // ""')

 MEMORY_ADD_OUT=$("$FLOWCTL" memory add \
 --track knowledge \
 --category architecture-patterns \
 --title "$MEMORY_TITLE" \
 ${PRIMARY_MODULE:+--module "$PRIMARY_MODULE"} \
 --tags "$TAGS" \
 --applies-when "Future spec touches $PRIMARY_MODULE or related modules — this entry shows what $SPEC_ID established." \
 --body-file "$MEMORY_BODY_FILE" \
 --json 2>&1) || {
 echo "Warning: --memory write failed (non-fatal — PR is open):" >&2
 echo "$MEMORY_ADD_OUT" >&2
 }

 MEMORY_ID=$(printf '%s' "$MEMORY_ADD_OUT" | jq -r '.entry_id // empty' 2>/dev/null)
 if [[ -n "$MEMORY_ID" ]]; then
 echo "Memory entry written: $MEMORY_ID" >&2
 fi
fi
```

**Failure mode handling:** if `flowctl memory add` fails (overlap detection rejected the entry, frontmatter validation failed, disk write error), the failure is **non-fatal** — the PR is already open, and re-running with `--memory` later will retry. Print the error to stderr; do NOT exit non-zero. The user's primary deliverable (the PR) succeeded; the secondary deliverable (memory entry) didn't.

`--applies-when` is the knowledge-track required field. The phrasing follows the existing `audit-sync-codexsh-during-planning-for-2026-04-30` example: forward-looking, anchored to a module the future searcher would query for.

### 5.4 — Ralph stdout shape

Under Ralph (`$RALPH == 1`), the success footer changes shape — the harness expects the PR URL on stdout in a parseable form, with all human-readable framing routed through stderr. This contract is keyed on `RALPH` ALONE — `AUTONOMOUS=1` without Ralph uses the interactive footer; autonomous drivers (pilot) confirm the PR via `gh`, not by scraping `PR_URL=`.

```bash
if [[ "$RALPH" == "1" ]]; then
 # Single-line stdout: PR_URL=<url>
 echo "PR_URL=$PR_URL"
 # Human-readable framing → stderr.
 echo "" >&2
 echo "✅ Draft PR opened: $PR_URL" >&2
 echo "Reviewer should run: /flow-next:resolve-pr ${PR_URL##*/}" >&2
else
 # Interactive mode: §5.0 success footer to stdout.
 cat <<EOF
✅ PR opened: $PR_URL

Next steps:
 - Reviewer feedback → /flow-next:resolve-pr ${PR_URL##*/}
 - Body inspection → /flow-next:make-pr $SPEC_ID --dry-run
EOF
 if [[ -n "${MEMORY_ID:-}" ]]; then
 echo " - Memory entry written: $MEMORY_ID"
 fi
fi
```

R24 invariant: under Ralph the PR URL is the **sole stdout artefact** in machine-parseable form (`PR_URL=<url>`), so the harness can capture it via `eval "$(/flow-next:make-pr ...)"` or by grep / tail. Everything else (memory write notes, recovery hints, breadcrumbs, the §5.7 tracker-sync check + `Tracker sync:` summary line) routes through stderr where the harness logs it but doesn't parse it.

### 5.6 — Tracker sync (opt-in) — link the PR to the issue + move it to In Review (Diffs-ready)

**Runs whenever the tracker bridge is active, after `gh pr create` returned a `$PR_URL` in §4.6 (never under `--dry-run` — Phase 4.0 short-circuits before Phase 5).** No separate `makePr` opt-in — linking a PR to its issue is zero-/near-zero-cost hygiene and is the whole value (Linear Diffs). Links the PR to the tracker issue (R10), append-only and conflict-free (R8). **Not Ralph-blocked** (attaching a link is a confident, conflict-free op).

**In Review status push rides this SAME unconditional bridge-active path (fn-66, R2).** Because an open PR for the branch is by definition the *In Review* lifecycle rung, moving the linked issue to `In Review` is part of the same PR↔issue linkage that powers Linear Diffs — it is **NOT gated behind `tracker.perEvent.makePr != off`** (that leaf gates only the optional breadcrumb comment, not the link/status that make the bridge useful). A just-created PR is `OPEN`, so the merge-evidence probe yields `open` and `reconcileStatus(spec, issue, open)` → `in-review` (status-sync.md row 4); the dispatch below reconciles the issue to that non-terminal rung (never terminal — a freshly-opened PR has no merge evidence). The dispatch uses the **`reconcile`** op (not `push`) precisely so this In Review nudge rides the body-preserving 3-way merge — a `push` would re-render and overwrite the issue body first (steps.md push() lines 134-136), clobbering human tracker-side edits.

The **primary linkage already happened in §4.6a** — the `Ref <identifier>` line in the PR body, which makes the host's tracker integration auto-link the PR. §5.6 is the **enhancement layer** and is **transport- and tracker-type-aware**:

- **Linear (`tracker.type == linear`):** the §4.6a body ref is what makes **Linear Diffs** render the PR inside the issue (Linear's GitHub integration auto-links on the `WOR-N` identifier). On the **GraphQL rung**, additionally create the *rich* GitHub-PR attachment + status sync via `attachmentLinkURL(issueId, $PR_URL)` (Linear auto-detects the GitHub URL; do NOT use `attachmentCreate` — that yields a dumb attachment with no diff/status). On the **MCP rung** there is no URL-attach tool, so it relies entirely on the §4.6a auto-link (sufficient — the integration does the rest). Optionally also post a one-line breadcrumb comment.
 - *Prereqs are user-side and flow-next can't set them:* the Linear GitHub integration must have **code access**, the user needs a **personal GitHub connection**, and **"Enable code reviews"** must be on. Without these the PR still links (status sync works); only the rendered diff view requires them. (Documented in `docs/tracker-sync.md`.)
- **GitHub (`tracker.type == github`):** the PR and issue share the repo — use a **native `Refs #N`** (non-closing) reference, handled by the GitHub adapter (`github.md`). No Linear-style attachment, no "Diffs".

```bash
if [[ -n "$PR_URL" ]] \
 && [ "$("$FLOWCTL" sync active --json | jq -r '.active')" = "true" ]; then
 # Invoke the flow-next-tracker-sync skill with the canonical lifecycle dispatch
 # grammar — `operation: <verb> <id>, event: <key>` (verbatim, no descriptors in
 # the operation token):
 # skill: flow-next-tracker-sync (operation: reconcile <spec-id>, event: makePr)
 # The `reconcile` op (open-PR evidence) moves the issue to In Review AND links $PR_URL —
 # BOTH ride this unconditional bridge-active path (NOT gated behind perEvent.makePr):
 # the link powers Diffs and In Review is the honest lifecycle state for an open PR.
 # WHY `reconcile`, NOT `push` (fn-66 regression fix): `push` renders the COMPLETE
 # spec body and writeIssue's it BEFORE setStatus (steps.md push() lines 134-136), so
 # opening a PR just to nudge In Review would CLOBBER any human tracker-side body edits
 # made since the last sync. `reconcile` runs the 3-way body merge (steps.md reconcile()
 # lines 177-185) that PRESERVES tracker-side edits, and sets In Review as part of the
 # SAME op via reconcileStatus(spec, issue, open) → in-review (status-sync.md row 4 / R2).
 # A genuine body conflict queues (sync defer) or asks — it NEVER blocks the open PR.
 # linear → rich attachment via attachmentLinkURL (GraphQL rung) + setStatus(in-review)
 # via reconcileStatus (open prEvidence → in-review, non-terminal, status-sync.md
 # row 4); the §4.6a body ref already enabled the auto-link + Diffs. Optional breadcrumb comment.
 # github → native `Refs #N` (github.md) + status:in-review label.
 # gitlab → the GitLab adapter posts a non-closing PR-URL **note** on the issue
 # (gitlab.md §makePr) — NEVER a `Closes #N` (flow-next owns terminal Done
 # via land.merged) — + the open/closed-side status:in-review label. A
 # GitHub-PR body ref can't auto-link a cross-instance GitLab issue, so the
 # note IS the cross-link; the §4.6a `Ref <project>#<iid>` is a human breadcrumb.
 # jira → the Jira adapter writes the PR link as a **remote link**
 # (POST /issue/{key}/remotelink, jira.md §makePr) — NEVER a transition to Done
 # (flow-next owns terminal Done via land.merged, gated on MERGED) — + the
 # In Review transition via reconcileStatus (open prEvidence → in-review). No
 # PR-body ref auto-links a Jira issue, so the remote link IS the cross-link.
 # On a remote-link POST failure (permission / older DC) it falls back to a
 # PR-URL **comment** carrying the lifecycle marker (jira.md §makePr).
 # (PR URL source: reconcile RE-DERIVES it from `mergeEvidenceProbe(spec.branch_name)` —
 # the same probe yielding open/merged queries the code host `gh pr … --json url,state`
 # (status-sync.md) — so the op token `reconcile <spec-id>` deliberately omits it; the
 # note dedupes on the URL so a re-run never stacks duplicates. gitlab.md §makePr.)
 # The open PR is the merge-evidence `open` bucket → In Review, NEVER terminal (no MERGED).
 # Unlinked spec → flow-first link (create + base-snapshot) first, then reconcile the now-linked
 # spec → link the PR / Diff + In Review (tracker-sync §Phase 3 create-if-unlinked). No-op only if no transport reachable.
 # Best-effort — the PR is already open; a tracker failure must NOT exit non-zero.
 # Under Ralph, framing routes to stderr (keeps the PR_URL=<url> stdout invariant).
 :
fi
```

The PR is already open before this step; a tracker failure surfaces as a stderr warning and never changes the exit code (same non-fatal discipline as the `--memory` write in §5.1). The skill emits its own receipt, event-tagged `--event makePr` — the tag §5.7's end-of-run `sync check` audits. The `In Review` status push is non-terminal (`reconcileStatus(spec, issue, open) → in-review`, status-sync.md row 4) — an open PR is never `Done`. **`reconcile` (not `push`) is deliberate (fn-66):** the body-preserving 3-way merge means moving the issue to In Review on PR open can never overwrite human tracker-side body edits — the prior conflict-free guarantee of the old `link $PR_URL` path, now extended to the status nudge.

### 5.7 — Tracker-sync end-of-run check — LAST action before exit (fn-57)

Read-only audit: did the `makePr` touchpoint actually fire this run (receipt-backed)? It runs independently of §5.6, so a wholesale-skipped dispatch block is still caught. With no tracker configured, `sync check` exits silently in constant time — the summary slot then reads `n/a (bridge inactive)` and nothing else changes. (A disabled `tracker.perEvent.makePr` leaf is never MISSING — §5.6 still fires as bridge-active hygiene, but the audit only forces opted-in events.)

```bash
# --since: the PR's createdAt — on-disk anchor (bash vars do NOT survive across
# prompt turns; gh re-derives it anytime). Receipts older than the PR never clear.
SINCE=$(gh pr view "$PR_URL" --json createdAt --jq .createdAt 2>/dev/null || true)

[ -n "$SINCE" ] && "$FLOWCTL" sync check "$SPEC_ID" --events makePr --since "$SINCE" --json
# Empty output → bridge inactive → slot = `n/a (bridge inactive)`. Otherwise
# `.missing` empty → slot = `OK`; non-empty → retro-fire (below).
# Ralph stdout invariant (§5.4 R24): stdout is reserved for the single
# `PR_URL=<url>` line — under Ralph, route ALL check + summary lines to stderr.
```

**Retro-fire on MISSING — exactly ONE cycle, never blocking:**

1. Record the retro-fire start anchor (the re-check needs it as `--since`): `date -u +%Y-%m-%dT%H:%M:%SZ`
2. Invoke the **flow-next-tracker-sync skill directly** — the same dispatch as §5.6, with its `event:` tag, in the canonical `operation: <verb> <id>, event: <key>` grammar: `skill: flow-next-tracker-sync (operation: reconcile <spec-id>, event: makePr)` (the `reconcile` op links $PR_URL + moves the issue to In Review via the body-preserving 3-way merge — never clobbers tracker-side edits, fn-66; the PR URL rides as evidence, not in the op token) — NEVER this check block as a wrapper (no recursion).
3. Re-check with `--since` = the step-1 anchor:
 `"$FLOWCTL" sync check "$SPEC_ID" --events makePr --since "<retro-fire-start>" --json`
4. Record the final state in the summary slot. Still MISSING after the one cycle is a recorded, visible outcome — never a second retro-fire, never a block (the PR is already open; a tracker hiccup must not become a hard stop). Recovery guidance lives in the receipt note + `docs/tracker-sync.md`.

**Mandatory summary slot — the LAST line the skill prints.** Exactly four states; an explicit `n/a` proves the check ran, an absent line is a skipped check:

```text
Tracker sync: <OK | MISSING:makePr → retro-fired → OK | MISSING:makePr (retro-fire failed: <reason>) | n/a (bridge inactive)>
```

Interactive mode: append it after the §5.0 success footer on stdout. Under Ralph: **stderr ONLY** — stdout's sole artefact stays the single `PR_URL=<url>` line (§5.4 R24 invariant).

### 5.5 — Cleanup

`trap 'rm -f "$BODY_FILE"' EXIT` from §4.3 fires automatically when the script exits (success or failure). The memory body file is added to the trap when `--memory` fires (§5.3). No explicit cleanup needed; trap discipline handles both files.

The PR body file ends up in `/tmp/`, OS-cleaned on reboot even when trap doesn't fire (e.g. `kill -9`). No persistent on-disk artefact survives a make-pr invocation, with the single exception of the `--memory` side effect (which writes a permanent entry under `.flow/memory/knowledge/architecture-patterns/`).

### Done when

- `✅ PR opened: <URL>` printed on stdout in interactive mode; `PR_URL=<URL>` single-line in Ralph mode.
- Next-steps hint includes `/flow-next:resolve-pr <PR_NUMBER>` (interactive only — Ralph emits to stderr).
- `--memory` flag triggers the memory write ONLY when `WRITE_MEMORY == 1` AND not dry-run AND `gh pr create` succeeded. Idempotent — skipped with a stderr note when an entry tagged `spec-<SPEC_ID>` already exists.
- Memory entry uses `--track knowledge --category architecture-patterns`, with `spec-<SPEC_ID>` as the leading tag (the idempotency key) followed by the first 2 entries of `modules_touched[]`; `module` field set to the first (most-touched) entry of `modules_touched[]`. Frontmatter never carries a `spec_id` field (rejected by `validate_memory_frontmatter`); idempotency uses tags only.
- Memory body shape follows the §5.2 template (What shipped / R-IDs satisfied / Modules touched / Decisions captured / Impact). Section omission rule honored.
- Memory write failure surfaces as stderr warning, never exits non-zero — PR is already opened.
- Ralph-mode invariant: the PR URL is the sole stdout artefact (`PR_URL=<url>` form); everything else (memory write notes, recovery hints, tracker-sync slot) routes through stderr.
- §5.6 dispatch carries `event: makePr`; §5.7 end-of-run `sync check` ran (`--events makePr`, `--since` = the PR's `createdAt`), retro-fired any MISSING touchpoint exactly once, and the final printed line is the mandatory four-state `Tracker sync:` slot — stderr-only under Ralph (stdout stays `PR_URL=<url>`).
- Tempfiles cleaned up via `trap … EXIT`. No persistent artefact except the optional memory entry.

---
