# Scoped flow handoff

For a flow handoff, require the complete tuple and current authority before taking the claim. Keep `REPO_ROOT` on the source checkout for spec/task/QA evidence and CI/resolve actions. Resolve `LAND_BASE_ROOT` to the base worktree in this same clone; verify both physical paths and common git directory. After acquiring the claim, prepare a missing base worktree with `git worktree add <new-owned-directory> <verified-base>` (fetch the base if needed), then validate it below before loading any config. Reuse it on later ticks via `git worktree list`; report the path for recovery. Never move an occupied source or base branch or discard local work. Standalone land defaults `LAND_BASE_ROOT` to `REPO_ROOT` and keeps its checkout behavior. Dry-run creates no worktree and reports an unavailable base as a would-prepare requirement; it executes no merge-verdict command.

```bash
LAND_SCOPE_FAILED=0
if [ -n "${LAND_SCOPE_SPEC:-}" ] || [ -n "${LAND_SCOPE_PR:-}" ]; then
  if [ "${LAND_AUTHORIZED:-0}" != 1 ] || [ -z "${LAND_SCOPE_SPEC:-}" ] || [ -z "${LAND_SCOPE_PR:-}" ]; then
    LAND_SCOPE_FAILED=1
  else
    SCOPE_SPEC_JSON="$("$FLOWCTL" show "$LAND_SCOPE_SPEC" --json)" || LAND_SCOPE_FAILED=1
    SCOPE_PR_JSON="$(gh pr view "$LAND_SCOPE_PR" --json url,number,state,headRefName,headRefOid,baseRefName,isCrossRepository)" || LAND_SCOPE_FAILED=1
    SCOPE_REPO_URL="$(gh repo view --json url --jq .url)" || LAND_SCOPE_FAILED=1
    SCOPE_BRANCH="$(printf '%s\n' "$SCOPE_SPEC_JSON" | jq -er '.branch_name | strings | select(length > 0)')" || LAND_SCOPE_FAILED=1
    printf '%s\n' "$SCOPE_PR_JSON" | jq -e --arg pr "$LAND_SCOPE_PR" --arg repo "$SCOPE_REPO_URL" --arg branch "$SCOPE_BRANCH" '
      .url == $pr and .url == ($repo + "/pull/" + (.number | tostring))
      and .headRefName == $branch and .isCrossRepository == false
      and (.state == "OPEN" or .state == "MERGED")
      and (.baseRefName | type == "string" and length > 0)' >/dev/null || LAND_SCOPE_FAILED=1
    SCOPE_BASE="$(printf '%s\n' "$SCOPE_PR_JSON" | jq -r '.baseRefName')"
    SCOPE_HEAD="$(printf '%s\n' "$SCOPE_PR_JSON" | jq -r '.headRefOid')"
    if [ "$LAND_SCOPE_FAILED" = 0 ] && [ "$(printf '%s\n' "$SCOPE_PR_JSON" | jq -r '.state')" = OPEN ]; then
      if [ "$(git -C "$REPO_ROOT" symbolic-ref -q HEAD)" != "refs/heads/$SCOPE_BRANCH" ]; then
        LAND_SCOPE_FAILED=1
      elif ! [[ "$SCOPE_HEAD" =~ ^[0-9a-f]{40,64}$ ]]; then
        LAND_SCOPE_FAILED=1
      elif [ "$(git -C "$REPO_ROOT" rev-parse HEAD)" != "$SCOPE_HEAD" ]; then
        if [ "${LAND_DRY_RUN:-0}" = 1 ]; then
          LAND_SCOPE_FAILED=1
        else
          git -C "$REPO_ROOT" fetch origin "$SCOPE_HEAD" && git -C "$REPO_ROOT" merge --ff-only "$SCOPE_HEAD" || LAND_SCOPE_FAILED=1
          [ "$(git -C "$REPO_ROOT" rev-parse HEAD)" = "$SCOPE_HEAD" ] || LAND_SCOPE_FAILED=1
        fi
      fi
    fi
    if [ "$LAND_SCOPE_FAILED" = 0 ] && [ "${LAND_DRY_RUN:-0}" != 1 ]; then
      SCOPE_COMMON="$(git -C "$REPO_ROOT" rev-parse --path-format=absolute --git-common-dir)" || LAND_SCOPE_FAILED=1
      BASE_COMMON="$(git -C "${LAND_BASE_ROOT:-/nonexistent}" rev-parse --path-format=absolute --git-common-dir)" || LAND_SCOPE_FAILED=1
      if [ "$SCOPE_COMMON" != "$BASE_COMMON" ] || [ "$(git -C "${LAND_BASE_ROOT:-/nonexistent}" branch --show-current)" != "$SCOPE_BASE" ]; then LAND_SCOPE_FAILED=1; fi
      BASE_STATUS="$(git -C "${LAND_BASE_ROOT:-/nonexistent}" status --porcelain)" || LAND_SCOPE_FAILED=1
      if [ -n "$BASE_STATUS" ]; then LAND_SCOPE_FAILED=1; fi
    fi
  fi
fi
if [ "$LAND_SCOPE_FAILED" = 1 ]; then
  if [ "${LAND_DRY_RUN:-0}" != 1 ]; then
    rm -f "$TICK_LOCK/pid"
    rmdir "$TICK_LOCK"
  fi
  echo 'LAND_VERDICT=NEEDS_HUMAN prs=0 pr=- reason="invalid scoped identity or unusable base workspace"'
  exit 1
fi
LAND_BASE_ROOT="${LAND_BASE_ROOT:-$REPO_ROOT}"
```

`LAND_SCOPE_FAILED=1` stops `NEEDS_HUMAN` with the failing identity/checkout evidence and releases the tick claim if this tick acquired it. No discovery, config command, or landing action follows. Keep the source checkout for pre-merge evidence; the config read and §2.9 use the verified base path, then return to source. After merge, the tail switches to base. Re-check that the PR still has this base at GATE and ACT; a changed target stops this tick for fresh classification, never uses the old base's gates.
