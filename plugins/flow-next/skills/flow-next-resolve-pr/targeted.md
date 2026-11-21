# Targeted mode (gated reference)

> Read from [workflow.md](workflow.md) only when Phase 0 set `MODE=targeted` (a comment URL).

## Phase 1: narrow the feedback

**Targeted mode** — narrow `FEEDBACK_JSON` to the single item identified by the URL.

For `TARGETED_TYPE=review_thread` (inline review comment) — Phase 1 skipped `get-pr-comments`; resolve the comment's thread directly and build a minimal single-thread feedback payload:

```bash
COMMENT_NODE_ID=$(gh api "repos/$OWNER/$REPO/pulls/comments/$COMMENT_REST_ID" --jq .node_id)
THREAD_JSON=$(bash "$SCRIPTS/get-thread-for-comment" "$PR_NUMBER" "$COMMENT_NODE_ID" "$OWNER/$REPO")
if [[ -n "$THREAD_JSON" ]]; then
  FEEDBACK_JSON=$(printf '%s\n' "$THREAD_JSON" | jq --arg pr "$PR_NUMBER" '
    {
      pr_number: ($pr | tonumber),
      # GitHub can surface open review threads as either false or null.
      # Treat only literal true as resolved (same predicate as get-pr-comments).
      review_threads: (if .isResolved == true then [] else [del(.isResolved)] end),
      pr_comments: [],
      review_bodies: [],
      cross_invocation: (
        if .isResolved == true then
          {signal: true, resolved_threads: [{id: .id, path: .path, line: (.line // .originalLine)}]}
        else
          {signal: false, resolved_threads: []}
        end
      )
    }')
else
  FEEDBACK_JSON=$(jq -n --arg pr "$PR_NUMBER" '{pr_number: ($pr | tonumber), review_threads: [], pr_comments: [], review_bodies: [], cross_invocation: {signal: false, resolved_threads: []}}')
fi
```

For `TARGETED_TYPE=pr_comment` (top-level PR comment) — Phase 1 skipped `get-pr-comments`; fetch the single comment via REST and build a minimal feedback payload:

```bash
PR_COMMENT_JSON=$(gh api "repos/$OWNER/$REPO/issues/comments/$COMMENT_REST_ID" \
  --jq '{id: .node_id, author: .user.login, body: .body, createdAt: .created_at}')
FEEDBACK_JSON=$(jq --argjson c "$PR_COMMENT_JSON" --arg pr "$PR_NUMBER" '
  {
    pr_number: ($pr | tonumber),
    review_threads: [],
    pr_comments: [$c],
    review_bodies: [],
    cross_invocation: {signal: false, resolved_threads: []}
  }' <<<'{}')
```

## Phase 2: triage

**Targeted mode skips this phase entirely** — the user explicitly asked for that one item, treat it as `new` regardless of triage heuristics:

```bash
if [[ "$MODE" == "targeted" ]]; then
  echo "Triage: skipped (targeted mode — single item)."
  # Fall through to Phase 3 with the single item marked new.
fi
```

## Phase 3: cluster analysis

**Targeted mode skips this phase entirely** — single-item dispatch, no cluster surface:

```bash
if [[ "$MODE" == "targeted" ]]; then
  echo "Cluster analysis: skipped (targeted mode — single item)."
  # Skip to Phase 4 with the single item as its own unit.
fi
```
