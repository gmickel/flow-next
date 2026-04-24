# fn-31-pr-feedback-resolver.5 Targeted mode + --dry-run + --no-cluster flags

## Description

Polish the orchestration with three argument modes / flags: comment-URL targeted mode (single thread), `--dry-run` (fetch + plan only), `--no-cluster` (skip Phase 3 clustering).

**Size:** S

**Files:**
- `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md` (Phase 0 argument parsing + mode branching)

<!-- Updated by plan-sync: fn-31.3 workflow.md also accepts `#issuecomment-\d+` URLs for top-level pr_comment targeting; earlier spec only listed the `#discussion_r...` review-thread form. -->

## Targeted mode

When `$ARGUMENTS` contains a comment URL, two shapes are supported:

- `https://github.com/OWNER/REPO/pull/NUMBER#discussion_rCOMMENT_ID` — inline review-thread comment (maps to one `review_thread`).
- `https://github.com/OWNER/REPO/pull/NUMBER#issuecomment-COMMENT_ID` — top-level PR comment (maps to one `pr_comment`; no thread to resolve, reply only).

Handling:

1. Parse URL for OWNER, REPO, PR number, comment REST ID + URL kind (`discussion_r` vs `issuecomment`).
2. For `discussion_r` URLs, get comment node ID via REST:

   ```bash
   gh api repos/OWNER/REPO/pulls/comments/COMMENT_ID --jq '{node_id, path, line, body}'
   ```

3. For review-thread URLs, map to thread via scripts/get-thread-for-comment:

   ```bash
   bash scripts/get-thread-for-comment "$PR_NUMBER" "$COMMENT_NODE_ID" "$OWNER/$REPO"
   ```

4. For `issuecomment` URLs, fetch the single pr_comment via `gh api repos/OWNER/REPO/issues/comments/COMMENT_ID` and bypass thread lookup.
5. Dispatch one `pr-comment-resolver` agent for that single unit (same fields as full mode; pass `isOutdated` + `line` / `originalLine` / etc. for review threads; omit path/line for pr_comments).
6. Then follow same validate → commit → push → reply → resolve flow as full mode, scoped to the single item. Review-thread URLs reply+resolve via GraphQL; pr_comment URLs reply via `gh pr comment` only (no resolve mechanism).

### Behavior differences from full mode

- Skip Phase 2 triage (just one thread, user wants it handled).
- Skip Phase 3 cluster analysis (single-target, no cluster surface).
- Summary output shows just the one item.

### Example

```
/flow-next:resolve-pr https://github.com/gmickel/flow-next/pull/42#discussion_r1234567890
```

Expected: fetches thread, dispatches resolver, commits + replies + resolves (or needs-human).

## `--dry-run` flag

Parsed in Phase 0 as a flag; strip before mode detection.

Behavior:
- Phase 1: fetch happens (read-only, always safe)
- Phase 2: triage happens (read-only computation)
- Phase 3: cluster analysis happens (read-only computation)
- Phase 4: plan assembled and printed
- **STOP** — no dispatch, no edits, no commits, no replies, no resolves

Output: the plan as if Phase 4 completed, plus a clear `DRY RUN — no changes made.` banner.

## `--no-cluster` flag

Parsed in Phase 0 as a flag; strip before mode detection.

Behavior: skip Phase 3 entirely. All new items dispatched individually (even if cluster analysis would have produced a cluster).

Use case: user knows this is a one-off review, wants fast individual-only dispatch.

## Argument parsing priority

```
# Strip flags first
DRY_RUN=false
NO_CLUSTER=false
for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=true ;;
    --no-cluster) NO_CLUSTER=true ;;
  esac
done

# Remaining positional: PR number, URL, comment URL, or blank
```

## Acceptance

- **AC1:** Comment URL detected via either regex (`https://github\.com/.+/pull/\d+#discussion_r\d+` for review-thread comments, `https://github\.com/.+/pull/\d+#issuecomment-\d+` for top-level pr_comments).
- **AC2:** Targeted mode fetches only the one item (thread or pr_comment) + posts fix + replies (+ resolves for review threads).
- **AC3:** Targeted mode skips triage phase (Phase 2) and cluster phase (Phase 3).
- **AC4:** `--dry-run` exits after Phase 4 with plan printout, no mutations.
- **AC5:** `--no-cluster` skips Phase 3; all items go individual.
- **AC6:** Flags can be combined: `/flow-next:resolve-pr 123 --dry-run --no-cluster` works.
- **AC7:** Targeted mode + `--dry-run` prints the single-item plan without dispatching resolver.

## Dependencies

- fn-31-pr-feedback-resolver.1 (scripts)
- fn-31-pr-feedback-resolver.3 (workflow.md phases)

## Done summary
Filled gaps in resolve-pr workflow.md Phase 0/1/2/3 for targeted mode (both URL shapes), --dry-run, --no-cluster. Phase 0 now uses authoritative regex with MODE/TARGETED_TYPE capture. Phase 1 narrows FEEDBACK_JSON for review-thread URLs and bypasses thread lookup for issuecomment URLs (via REST issues/comments). Phases 2 and 3 explicitly skip in targeted mode. All 7 acceptance criteria smoke-tested locally.
## Evidence
- Commits: c92a8e609b22e040d480ccf508fb212e6e4493bb
- Tests: bash regex smoke test (all 6 TARGET shapes), jq filter smoke (targeted review_thread narrowing), jq construction smoke (targeted pr_comment minimal payload), AC7 integration smoke (targeted + --dry-run combo)
- PRs: