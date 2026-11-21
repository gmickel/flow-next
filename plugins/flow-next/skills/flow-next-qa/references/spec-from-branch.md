# Spec id from the branch (gated reference)

> Read from [workflow.md](../workflow.md) §1.1 only when `SPEC_ID` is empty.

When `SPEC_ID` is empty, match the current branch against each spec's stored `branch_name` (never
against the spec id itself):

```bash
if [[ -z "$SPEC_ID" ]]; then
  CURRENT_BRANCH="$(git -C "$REPO_ROOT" branch --show-current 2>/dev/null || echo "")"
  if [[ -n "$CURRENT_BRANCH" ]]; then
    SPEC_ID=$(
      find "$REPO_ROOT/.flow/specs" "$REPO_ROOT/.flow/epics" -maxdepth 1 -name '*.json' \
        -exec jq -r --arg b "$CURRENT_BRANCH" 'select(.branch_name == $b) | .id' {} + 2>/dev/null \
      | head -1)
  fi
fi
```

Still empty: ask which spec to QA (options from `$FLOWCTL specs`), or under `NO_PROMPT=1` exit
non-zero with a message. Never default silently.
