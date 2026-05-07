---
satisfies: [R20, R21, R22, R23, R24, R25]
---

## Description

Phase 4: push branch + `gh pr create` + flag handling. Includes the spec-amendment-via-task: switch from heredoc-based body to `--body-file` (informed by practice-scout: heredoc breaks on LLM-generated content; cli/cli #29619). Add `sleep 1` post-push for GitHub eventual-consistency lag (cli/cli #2691). Plus PR title format, `--dry-run`, `--memory`, Ralph default `--draft`, anti-pattern warnings.

**Size:** M (workflow.md Phase 4 + Phase 5 + footer; flag matrix logic)
**Files:** `plugins/flow-next/skills/flow-next-make-pr/workflow.md`, `plugins/flow-next/skills/flow-next-make-pr/phases.md`

## Approach

- **Body delivery via `--body-file`** (refinement vs spec R20's heredoc — switch is correct):
  ```bash
  BODY_FILE=$(mktemp -t make-pr-body-XXXXXX.md)
  trap 'rm -f "$BODY_FILE"' EXIT
  # Write rendered body to BODY_FILE via host agent's Write tool

  # Push branch (push-ack received before next step proceeds)
  git push -u origin HEAD 2>/dev/null || true
  sleep 1   # GitHub API eventual-consistency lag (cli/cli #2691)

  # Determine draft vs ready
  DRAFT_FLAG=""
  if [[ "$OPEN_ITEMS_COUNT" -gt 0 ]] || [[ -n "${FLOW_RALPH:-}" ]] || [[ -n "${REVIEW_RECEIPT_PATH:-}" ]]; then
    DRAFT_FLAG="--draft"
  fi
  if [[ "$FORCE_READY" == "1" ]]; then DRAFT_FLAG=""; fi
  if [[ "$FORCE_DRAFT" == "1" ]]; then DRAFT_FLAG="--draft"; fi

  # Create PR with retry-on-Head-sha-eventual-consistency
  # Empirically validated during fn-42 spike: even after push-ack succeeds,
  # `gh pr create` can fail with "Head sha can't be blank, Base sha can't be blank,
  # No commits between main and X" while the GitHub API is still propagating the push.
  # `sleep 1` alone is the cheap fix; the retry loop is the robust one.
  PR_URL=""
  for attempt in 1 2 3; do
    OUT=$(gh pr create --title "$PR_TITLE" --body-file "$BODY_FILE" $DRAFT_FLAG --base "$BASE_REF" --head "$HEAD_BRANCH" 2>&1) && { PR_URL="$OUT"; break; }
    # Retry only on the eventual-consistency error class. Other errors (auth, body too long,
    # PR already exists) should fail fast — re-raise them.
    if [[ "$OUT" == *"Head sha can't be blank"* ]] || [[ "$OUT" == *"No commits between"* ]]; then
      sleep $((attempt * 2))   # 2s, 4s, 6s
      continue
    fi
    echo "$OUT" >&2
    exit 1
  done
  [[ -z "$PR_URL" ]] && { echo "gh pr create failed after 3 retries on eventual-consistency error" >&2; exit 1; }
  echo "$PR_URL"
  ```
  - `gh pr create` has NO `--json` flag (verified by docs-scout). PR URL on stdout single-line. Capture via `PR_URL=$(...)`.
- **PR title format (R21):** epic title if ≤72 chars, else first sentence of `epic.spec_sections.goal_and_context` truncated to 70 chars + ellipsis. NO automatic Conventional-Commits prefix injection — the boundary is correct per spec. (For flow-next-self-use, the epic title already has `chore(.flow):` etc. prefixes if needed.)
- **`--dry-run` flag (R22):** skip Phase 4 entirely. Render body to stdout via `cat "$BODY_FILE"`. Exit 0. Useful for inspection / piping (`flow-next:make-pr --dry-run | pbcopy`) / smoke tests. Does NOT touch git or `gh`.
- **`--memory` flag (R23):** writes a `knowledge/architecture-patterns/` memory entry summarizing the epic. Idempotent — check via `_memory_iter_entries` for any entry with `epic_id: <id>` field; skip if found. Default off because memory entries should be deliberate (not every PR). Body of entry: epic title + first sentence of Goal & Context + R-IDs satisfied + module list (`modules_touched`) + winning structural decisions (from decisions memory) + impact summary.
- **Ralph mode (R24):** detect `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` non-empty. Skip the `AskUserQuestion` body preview entirely. Force `--draft` (Ralph PRs always draft until human approves). Emit PR URL to stdout for the harness to capture. Document in workflow.md why this is the correct shape — autonomous-loop terminus, not a decision point.
- **Anti-pattern warnings (R25):** workflow.md prose explicitly warns against:
  - Letting the agent open the PR without making the PR reviewable (methodology line 574)
  - Auto-merging the PR (out of scope — methodology #9 reserves merge for human)
  - Including raw diff content in body (privacy + duplication)
  - Generating `gh pr merge` invocations (skill never invokes merge)
  - Inflating scope claims beyond what the diff supports
- **Phase 5 output footer:**
  ```
  ✅ PR opened: <PR_URL>

  Next steps:
    - Reviewer feedback → /flow-next:resolve-pr <PR_NUMBER>
    - Iterate on body → /flow-next:make-pr fn-N --update (deferred to v2)
  ```
  - If `--memory` was passed: also note "Memory entry written: <id>"
  - If under Ralph: emit a single-line `PR_URL=<...>` to stdout for harness capture (in addition to the human-readable footer)
- **Body length cap enforcement:** before `gh pr create`, check `wc -c "$BODY_FILE"`. If >65,000, truncate sections in priority: drop full file list first → trim TL;DR to 3 bullets → collapse mermaid to overview-only. Last resort: write full body to `.flow/pr-bodies/<epic-id>.md` and link from a truncated PR body.
- **Existing-PR detection** (covered in T2 Phase 0, but reinforced here): if `gh pr view --json` returns OK during Phase 4, that's a race condition — refuse and exit. Caller should have caught in Phase 0.

## Investigation targets

**Required:**
- `https://cli.github.com/manual/gh_pr_create` — flags, `--body-file`, `--draft`, `--head`/`--base`
- `cli/cli#2691` — `Head sha can't be blank` race condition (the `sleep 1` justification)
- `cli/cli#29619` — Claude Code shell-quoting feedback (the `--body-file` justification)
- Task 1's `cmd_epic_export_cognitive_aid` payload — particularly the deferred-findings count and review-receipts shape (drives `OPEN_ITEMS_COUNT`)

**Optional:**
- `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md` — for the post-PR feedback flow (footer hint)
- `plugins/flow-next/scripts/flowctl.py` `cmd_memory_add` and `_memory_iter_entries` — for the `--memory` flag implementation

## Acceptance

- [ ] Phase 4 prose documents `--body-file` invocation (mktemp + cleanup trap + `gh pr create --body-file "$BODY_FILE"`). Heredoc approach explicitly documented as anti-pattern with citation to cli/cli #29619.
- [ ] `git push -u origin HEAD` followed by `sleep 1` AND a 3-attempt retry loop on the eventual-consistency error class (`Head sha can't be blank` / `No commits between main and X`) — both validated empirically during fn-42 spike. Backoff `2s, 4s, 6s` between retries. Other errors (auth, body too long, PR already exists) fail fast — do NOT retry.
- [ ] `DRAFT_FLAG` matrix documented: open items > 0 → draft; Ralph mode → draft; `--ready` overrides; `--draft` overrides.
- [ ] `--dry-run` skips Phase 4 entirely, prints body to stdout, exits 0. Smoke test (Task 7) covers this.
- [ ] `--memory` writes idempotent `knowledge/architecture-patterns/` entry. Documented body shape (epic title + Goal & Context first sentence + R-IDs + modules_touched + decisions + impact).
- [ ] Ralph mode (FLOW_RALPH=1 or REVIEW_RECEIPT_PATH set): skip AskUserQuestion preview, force --draft, emit PR_URL=... line for harness capture.
- [ ] Anti-pattern warnings appear in workflow.md prose — explicit list, not just "be careful".
- [ ] Phase 5 footer printed with PR URL + next-step hints (resolve-pr, optional --memory mention).
- [ ] Body length cap (65,000 chars target) with truncation order documented: drop file list → trim TL;DR → collapse mermaid → write to `.flow/pr-bodies/` + link.

## Done summary

_(populated by /flow-next:work after task completes)_

## Evidence

_(populated by /flow-next:work after task completes)_
