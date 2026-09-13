# Scoped flow handoff

For a flow handoff, require the complete tuple and current authority before taking the claim. Keep `REPO_ROOT` on the source checkout for spec/task/QA evidence and CI/resolve actions. Resolve `LAND_BASE_ROOT` to the base worktree in this same clone; verify both physical paths and common git directory. After acquiring the claim, prepare a missing base worktree with `git worktree add <new-owned-directory> <verified-base>` (fetch the base if needed), then validate it below before loading any config. Reuse it on later ticks via `git worktree list`; report the path for recovery. Never move an occupied source or base branch or discard local work. Standalone land defaults `LAND_BASE_ROOT` to `REPO_ROOT` and keeps its checkout behavior. Dry-run creates no worktree and reports an unavailable base as a would-prepare requirement; it executes no merge-verdict command.

After a chain cascade (§3.7) or GitHub's stack retarget, the PR head is a rewrite of the same commits, so the source checkout cannot fast-forward to it. The reconcile below moves a clean, owned checkout onto such a head only when both directions hold: every commit on the new head exists by stable patch-id among the local commits above the base (a head carrying a patch the checkout never had is not a rewrite of this work), and every local commit missing from the new head is already contained in the base (the merged parent's commits, verified by reverse-applying each one against the base tree) — a local-only commit that is in neither is unpushed work, and the checkout stays where it is:

```bash
# fence:scope-reconcile — inputs: REPO_ROOT, SCOPE_BASE, SCOPE_HEAD (fetched); → rc 0 when the checkout was moved
land_scope_patch_in_base() {   # $1 commit, $2 base ref → rc 0 when the commit's change is already present in the base tree (reverse-apply check on a scratch index)
  local idx rc; idx="$(git -C "$REPO_ROOT" rev-parse --git-path flow-next-reconcile.index)"
  GIT_INDEX_FILE="$idx" git -C "$REPO_ROOT" read-tree "$2" 2>/dev/null || { rm -f "$idx"; return 1; }
  git -C "$REPO_ROOT" diff "$1^" "$1" | GIT_INDEX_FILE="$idx" git -C "$REPO_ROOT" apply --cached --check -R 2>/dev/null; rc=$?
  rm -f "$idx"; return $rc
}
land_scope_reconcile_rewrite() {
  local base local_ids remote_ids c id
  [[ -z "$(git -C "$REPO_ROOT" status --porcelain)" ]] || return 1                      # never discard local work
  git -C "$REPO_ROOT" fetch -q origin "refs/heads/$SCOPE_BASE" 2>/dev/null || return 1
  base="origin/$SCOPE_BASE"
  remote_ids="$(for c in $(git -C "$REPO_ROOT" rev-list "$(git -C "$REPO_ROOT" merge-base "$SCOPE_HEAD" "$base")..$SCOPE_HEAD"); do git -C "$REPO_ROOT" show "$c" | git patch-id --stable | cut -d' ' -f1; done | sort -u)"
  [[ -n "$remote_ids" ]] || return 1
  local_ids=""
  for c in $(git -C "$REPO_ROOT" rev-list "$(git -C "$REPO_ROOT" merge-base HEAD "$base")..HEAD"); do
    id="$(git -C "$REPO_ROOT" show "$c" | git patch-id --stable | cut -d' ' -f1)"; local_ids="$local_ids$id
"
    # a local commit absent from the new head must already be in the base (the merged parent's work); anything else is unpushed work → refuse
    printf '%s\n' "$remote_ids" | grep -qx "$id" || land_scope_patch_in_base "$c" "$base" || return 1
  done
  [[ -z "$(comm -13 <(printf '%s' "$local_ids" | sort -u) <(printf '%s\n' "$remote_ids"))" ]] || return 1   # a remote patch the checkout never had → not a rewrite of this work
  git -C "$REPO_ROOT" reset -q --hard "$SCOPE_HEAD"
}
```

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
          git -C "$REPO_ROOT" fetch origin "$SCOPE_HEAD" && { git -C "$REPO_ROOT" merge --ff-only "$SCOPE_HEAD" 2>/dev/null || land_scope_reconcile_rewrite; } || LAND_SCOPE_FAILED=1
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
