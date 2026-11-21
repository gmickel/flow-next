# Targeted mode (gated reference)

> Read from [workflow.md](workflow.md) only when Phase 0 set `MODE=targeted` (a comment URL).

## Phase 1: narrow the feedback

**Targeted mode** — narrow `FEEDBACK_JSON` to the single item identified by the URL.

For `TARGETED_TYPE=review_thread` (inline review comment):

```bash
COMMENT_NODE_ID=$(gh api "repos/$OWNER/$REPO/pulls/comments/$COMMENT_REST_ID" --jq .node_id)
# Match directly inside FEEDBACK_JSON first; fall back to get-thread-for-comment only if absent (e.g. resolved thread).
THREAD_ID=$(jq -r --arg cid "$COMMENT_NODE_ID" 'first(.review_threads[] | select(.comments[]?.id == $cid) | .id) // empty' <<<"$FEEDBACK_JSON")
if [[ -z "$THREAD_ID" ]]; then
  THREAD_JSON=$(bash "$SCRIPTS/get-thread-for-comment" "$PR_NUMBER" "$COMMENT_NODE_ID" "$OWNER/$REPO")
  THREAD_ID=$(jq -r .id <<<"$THREAD_JSON")
fi
# Keep only the matching thread; drop pr_comments + review_bodies; zero cross-invocation signal.
FEEDBACK_JSON=$(jq --arg tid "$THREAD_ID" '
  .review_threads |= map(select(.id == $tid))
  | .pr_comments = []
  | .review_bodies = []
  | .cross_invocation = {signal: false, resolved_threads: []}
' <<<"$FEEDBACK_JSON")
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
