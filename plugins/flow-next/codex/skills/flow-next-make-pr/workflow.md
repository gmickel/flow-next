# /flow-next:make-pr workflow

Run in order; preserve variables. Require `.flow/`, git, jq and Python. Failed preflight, close, staging or close commit stops before export and PR creation; never skip close.
Use `set -e`, the resolved `FLOWCTL`, and `REPO_ROOT=$(git rev-parse --show-toplevel)`.
## Phase 0: Pre-flight

Run the fences; an information prompt may interrupt and rerun its fence. Dry-run skips installation/auth checks.
Explicit `--base <branch>` uses `origin/<branch>`, refreshed on real runs. Chain detection uses shared history; first match wins.
Merged-parent rewrites require create, a clean tree, ancestry and lease guards; dry-run reports and update never rewrites.
```bash
RALPH=0
if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
  RALPH=1
fi
if [[ "$DRY_RUN" != "1" ]]; then
  if ! command -v gh >/dev/null 2>&1; then
    echo "Error: gh CLI not installed. Install gh from https://cli.github.com then run gh auth login --hostname github.com." >&2; exit 1; fi
  if ! gh auth status --hostname github.com >/dev/null 2>&1; then
    echo "Error: gh CLI not authenticated; run gh auth login --hostname github.com." >&2; exit 1; fi
fi
```
Resolve `SPEC_ID` from the argument or the first current-branch `branch_name` match in
`.flow/specs/*.json`; with no match leave it empty for the range fallback below.
```bash
# fence:chain-detect — inputs: REPO_ROOT, FLOWCTL, SPEC_ID, BASE_REF, DRY_RUN
if [[ -n "$BASE_REF" && "$BASE_REF" != refs/* ]]; then
  BASE_BRANCH="${BASE_REF#origin/}"
  if [[ "$DRY_RUN" != "1" ]]; then
    git -C "$REPO_ROOT" fetch -q origin "refs/heads/$BASE_BRANCH:refs/remotes/origin/$BASE_BRANCH" || { echo "Error: cannot refresh origin/$BASE_BRANCH" >&2; exit 1; }
  fi
  BASE_REF="origin/$BASE_BRANCH"
fi
CHAIN_BASE=""
for candidate in origin/main main origin/master master; do
  if git -C "$REPO_ROOT" rev-parse --verify --quiet "$candidate" >/dev/null 2>&1; then
    CHAIN_BASE="$candidate"
    break
  fi
done
if [[ -z "$SPEC_ID" ]]; then
  CLOSED_IDS='{"spec_ids":[]}'; [[ -z "${BASE_REF:-$CHAIN_BASE}" ]] || CLOSED_IDS=$("$FLOWCTL" spec closed-in-range --base "${BASE_REF:-$CHAIN_BASE}" --json) || { printf '%s\n' "$CLOSED_IDS" >&2; exit 1; }
  SPEC_ID=$(printf '%s' "$CLOSED_IDS" | jq -r '.spec_ids[-1] // empty')
  if [[ -z "$SPEC_ID" ]]; then
    [[ "$RALPH" == "1" || "$AUTONOMOUS" == "1" ]] && exit 2
    echo "NEED_INPUT: SPEC_ID"; exit 3
  fi
fi
CHAIN_PARENT=""; CHAIN_PARENT_BRANCH=""; CHAIN_BOUNDARY=""; PARENT_PR=""; PARENT_PR_STATE=""; CHAIN_REWRITE=0; REWRITE_ONTO=""
if [[ -z "$BASE_REF" && -n "$CHAIN_BASE" ]]; then
  [[ "$CHAIN_BASE" == origin/* ]] && { git -C "$REPO_ROOT" fetch -q origin "refs/heads/${CHAIN_BASE#origin/}:refs/remotes/$CHAIN_BASE" 2>/dev/null || echo "Note: could not refresh $CHAIN_BASE from origin; chain detection uses the local ref." >&2; }
  CLOSED_IDS=$("$FLOWCTL" spec closed-in-range --base "$CHAIN_BASE" --json) || { printf '%s\n' "$CLOSED_IDS" >&2; exit 1; }
  for DEP in $("$FLOWCTL" show "$SPEC_ID" --json 2>/dev/null | jq -r '.depends_on_epics[]?'); do
    # Closed-set membership excludes closes inherited from a stacked parent branch.
    if printf '%s' "$CLOSED_IDS" | jq -e --arg dep "$DEP" '.spec_ids | index($dep) != null' >/dev/null; then continue; fi
    DEP_JSON=$("$FLOWCTL" show "$DEP" --json 2>/dev/null) || continue
    DEP_BRANCH=$(printf '%s' "$DEP_JSON" | jq -r '.branch_name // empty')
    [[ -z "$DEP_BRANCH" ]] && continue
    DEP_REF=""
    if git -C "$REPO_ROOT" fetch -q origin "refs/heads/$DEP_BRANCH:refs/remotes/origin/$DEP_BRANCH" 2>/dev/null; then DEP_REF="refs/remotes/origin/$DEP_BRANCH"; fi
    if DEP_PR_LIST=$(gh pr list --head "$DEP_BRANCH" --state all --json number,state,baseRefName 2>/dev/null); then
      DEP_PR_JSON=$(printf '%s' "$DEP_PR_LIST" | jq -c '(map(select(.state=="OPEN")) + map(select(.state=="MERGED")) + map(select(.state=="CLOSED"))) | .[0] // empty')
    elif [[ "$DRY_RUN" == "1" ]]; then
      echo "Note: cannot read the PR state of $DEP_BRANCH under --dry-run; treating parent $DEP as open." >&2
      DEP_PR_JSON=""
    else
      echo "NEEDS_HUMAN: cannot read the PR state of parent $DEP ($DEP_BRANCH)" >&2
      exit 2
    fi
    DEP_PR_STATE=$(printf '%s' "$DEP_PR_JSON" | jq -r '.state // empty')
    DEP_PR_NUMBER=$(printf '%s' "$DEP_PR_JSON" | jq -r '.number // empty')
    if [[ "$DEP_PR_STATE" == "MERGED" && "$(printf '%s' "$DEP_PR_JSON" | jq -r '.baseRefName // empty')" == "$(git -C "$REPO_ROOT" branch --show-current)" ]]; then continue; fi
    if [[ -z "$DEP_REF" && "$DEP_PR_STATE" == "MERGED" ]]; then
      if git -C "$REPO_ROOT" fetch -q origin "refs/pull/$DEP_PR_NUMBER/head:refs/flow-next/parent/$DEP_BRANCH" 2>/dev/null; then
        DEP_REF="refs/flow-next/parent/$DEP_BRANCH"
      else
        echo "NEEDS_HUMAN: cannot establish the chain boundary for $DEP; parent history unreachable" >&2
        exit 2
      fi
    fi
    if [[ -z "$DEP_REF" ]]; then
      DEP_COMPLETE=$(printf '%s' "$DEP_JSON" | jq '([.tasks[]?] | length > 0) and ([.tasks[]? | select(.status != "done")] | length == 0)')
      if [[ "$DEP_COMPLETE" == "true" ]]; then
        DEP_CHAIN=$("$FLOWCTL" spec chain "$SPEC_ID" --json) || {
          echo "NEEDS_HUMAN: cannot establish the chain boundary for $DEP; chain probe failed" >&2; exit 2;
        }
        if [[ "$(printf '%s' "$DEP_CHAIN" | jq --arg dep "$DEP" '(.parent == $dep) or (.eligible != true)')" == "true" ]]; then
          echo "NEEDS_HUMAN: cannot establish the chain boundary for $DEP; parent history unreachable ($(printf '%s' "$DEP_CHAIN" | jq -r '.reason'))" >&2; exit 2; fi
      fi
      continue   # shared chain evidence permits a landed dependency with no history left
    fi
    MB=$(git -C "$REPO_ROOT" merge-base HEAD "$DEP_REF" 2>/dev/null) || continue
    if git -C "$REPO_ROOT" merge-base --is-ancestor "$MB" "$CHAIN_BASE" 2>/dev/null; then
      continue   # shared history is on the chain base: merge-commit/fast-forward parent, or no chain
    fi
    CHAIN_PARENT="$DEP"; CHAIN_PARENT_BRANCH="$DEP_BRANCH"; CHAIN_BOUNDARY="$MB"
    PARENT_PR="$DEP_PR_NUMBER"; PARENT_PR_STATE="$DEP_PR_STATE"
    break
  done
fi
if [[ -n "$CHAIN_PARENT" ]]; then
  case "$PARENT_PR_STATE" in
    OPEN|"")
      BASE_REF="origin/$CHAIN_PARENT_BRANCH" ;;
    MERGED)
      PARENT_PR_BASE=$(printf '%s' "$DEP_PR_JSON" | jq -r '.baseRefName // empty')
      : "${PARENT_PR_BASE:=${CHAIN_BASE#origin/}}"
      git -C "$REPO_ROOT" fetch -q origin "refs/heads/$PARENT_PR_BASE:refs/remotes/origin/$PARENT_PR_BASE" 2>/dev/null \
        || { echo "NEEDS_HUMAN: cannot refresh chain base $PARENT_PR_BASE from origin; no rewrite" >&2; exit 2; }
      REWRITE_ONTO="origin/$PARENT_PR_BASE"; BASE_REF="$REWRITE_ONTO"; CHAIN_REWRITE=1 ;;
    CLOSED)
      echo "NEEDS_HUMAN: parent $CHAIN_PARENT PR #$PARENT_PR closed unmerged; the chain is broken" >&2
      exit 2 ;;
  esac
fi
[[ -z "$BASE_REF" ]] && BASE_REF="$CHAIN_BASE"
if [[ -z "$BASE_REF" ]]; then
  if [[ "$RALPH" == "1" || "$AUTONOMOUS" == "1" ]]; then
    echo "Error: no base ref detected (origin/main, main, origin/master, master all missing). Pass --base <ref> explicitly." >&2; exit 2; fi
  echo "NEED_INPUT: BASE_REF (origin/main, main, origin/master, master all missing)"
  exit 3
fi
if ! git -C "$REPO_ROOT" rev-parse --verify --quiet "$BASE_REF" >/dev/null 2>&1; then
  echo "Error: base ref '$BASE_REF' is not a valid git ref. Check with: git rev-parse --verify $BASE_REF" >&2; exit 1; fi
HEAD_SHA=$(git -C "$REPO_ROOT" rev-parse --verify HEAD 2>/dev/null) || {
  echo "Error: HEAD does not resolve to a commit. Repo state is broken; run from a normal branch." >&2; exit 1; }
BASE_SHA=$(git -C "$REPO_ROOT" rev-parse --verify "$BASE_REF" 2>/dev/null)
if [[ "$HEAD_SHA" == "$BASE_SHA" ]]; then
  echo "Error: HEAD and base ($BASE_REF) point at the same commit. Nothing to PR." >&2; exit 1; fi
MERGE_BASE=$(git -C "$REPO_ROOT" merge-base "$BASE_REF" HEAD 2>/dev/null) || {
  echo "Error: HEAD and base ($BASE_REF) share no merge-base — unrelated histories. Pick a different --base." >&2
  exit 1; }
COMMITS_AHEAD=$(git -C "$REPO_ROOT" rev-list --count "$MERGE_BASE..HEAD")
if [[ "$COMMITS_AHEAD" -lt 1 ]]; then
  echo "Error: HEAD has 0 commits since merge-base with $BASE_REF. Nothing to PR." >&2; exit 1; fi
```
```bash
# --- §0.5: tasks-done validation (single show capture = spec-existence validation) ---
if ! SPEC_JSON=$("$FLOWCTL" show "$SPEC_ID" --json 2>/dev/null); then
  echo "Error: spec '$SPEC_ID' not found in .flow/specs/. Check id with: $FLOWCTL specs" >&2; exit 1; fi
SPEC_ID=$(printf '%s' "$SPEC_JSON" | jq -r '.id')
OPEN_TASKS=$(printf '%s' "$SPEC_JSON" | jq -r '[.tasks[]? | select(.status != "done") | .id] | join(", ")')
TASK_COUNT=$(printf '%s' "$SPEC_JSON" | jq '[.tasks[]?] | length')
OPEN_COUNT=$(printf '%s' "$SPEC_JSON" | jq '[.tasks[]? | select(.status != "done")] | length')
if [[ "$OPEN_COUNT" -gt 0 ]]; then
  if [[ "$RALPH" == "1" || "$AUTONOMOUS" == "1" ]]; then
    echo "Error: $OPEN_COUNT task(s) under $SPEC_ID still open ($OPEN_TASKS). Autonomous context cannot open PRs for incomplete specs." >&2
    exit 2
  else
    echo "Note: $OPEN_COUNT task(s) not yet done ($OPEN_TASKS); the spec remains open and is not closed. Opening as a DRAFT. Run /flow-next:work to finish, then mark the PR ready." >&2
  fi
fi
if [[ "$TASK_COUNT" -eq 0 ]]; then
  echo "Note: $SPEC_ID has no tasks; the spec remains open and is not closed." >&2
fi
EXISTING_JSON=$(gh pr view --json url,state,number 2>/dev/null | jq -c 'select(.state == "OPEN")' || true)
EXISTING=$(printf '%s' "$EXISTING_JSON" | jq -r '.url // empty' 2>/dev/null || true)
UPDATE_PR_NUMBER=$(printf '%s' "$EXISTING_JSON" | jq -r '.number // empty' 2>/dev/null || true)
if [[ "${UPDATE_MODE:-0}" == "1" ]]; then
  if [[ -z "$EXISTING" ]]; then
    echo "Error: --update needs an existing OPEN pull request on this branch; none found. Run /flow-next:make-pr (without --update) to create one first." >&2; exit 1; fi
  echo "Update mode: refreshing PR #$UPDATE_PR_NUMBER body against the current diff." >&2
elif [[ -n "$EXISTING" ]]; then
  echo "Error: branch already has an OPEN PR: $EXISTING; use --update or /flow-next:resolve-pr." >&2
  exit 1
fi
# fence:chain-rewrite — inputs: REPO_ROOT, BASE_REF, CHAIN_REWRITE, CHAIN_PARENT, CHAIN_BOUNDARY, REWRITE_ONTO, DRY_RUN, UPDATE_MODE; gh on PATH unless --dry-run
if [[ "${CHAIN_REWRITE:-0}" == "1" ]]; then
  HEAD_BRANCH=$(git -C "$REPO_ROOT" branch --show-current)
  if [[ "$DRY_RUN" == "1" ]]; then
    echo "would rebase $HEAD_BRANCH onto ${REWRITE_ONTO#origin/} from $CHAIN_BOUNDARY" >&2
  elif [[ "${UPDATE_MODE:-0}" != "1" ]]; then
    PRIOR_PRS=$(gh pr list --head "$HEAD_BRANCH" --state all --json number,state --jq '[.[] | select(.state=="OPEN" or .state=="MERGED")] | length' 2>/dev/null) || PRIOR_PRS=""
    [[ "$PRIOR_PRS" == "0" ]] || { echo "NEEDS_HUMAN: $HEAD_BRANCH already has an open or merged PR, or the probe failed; no rewrite" >&2; exit 2; }
    git -C "$REPO_ROOT" merge-base --is-ancestor "$CHAIN_BOUNDARY" HEAD 2>/dev/null || { echo "NEEDS_HUMAN: chain boundary $CHAIN_BOUNDARY is not an ancestor of HEAD" >&2; exit 2; }
    [[ -z "$(git -C "$REPO_ROOT" status --porcelain)" ]] || { echo "NEEDS_HUMAN: working tree not clean; commit or stash before the merged-parent rewrite" >&2; exit 2; }
    PRE_HEAD=$(git -C "$REPO_ROOT" rev-parse HEAD)
    REMOTE_LS=$(git -C "$REPO_ROOT" ls-remote origin "refs/heads/$HEAD_BRANCH" 2>/dev/null) \
      || { echo "NEEDS_HUMAN: cannot read origin for $HEAD_BRANCH; no rewrite" >&2; exit 2; }
    REMOTE_SHA=$(printf '%s' "$REMOTE_LS" | cut -f1)
    if [[ -n "$REMOTE_SHA" && "$REMOTE_SHA" != "$PRE_HEAD" ]]; then
      echo "NEEDS_HUMAN: $HEAD_BRANCH on origin ($REMOTE_SHA) differs from HEAD; push or pull first" >&2; exit 2
    fi
    if ! git -C "$REPO_ROOT" rebase --onto "$REWRITE_ONTO" "$CHAIN_BOUNDARY" >/dev/null 2>&1; then
      CONFLICTS=$(git -C "$REPO_ROOT" diff --name-only --diff-filter=U | tr '\n' ' ')
      git -C "$REPO_ROOT" rebase --abort 2>/dev/null
      echo "NEEDS_HUMAN: parent $CHAIN_PARENT merged; rebase $HEAD_BRANCH onto ${REWRITE_ONTO#origin/} conflicts in ${CONFLICTS% }" >&2; exit 2
    fi
    if [[ -n "$REMOTE_SHA" ]]; then
      if ! git -C "$REPO_ROOT" push -q --force-with-lease="refs/heads/$HEAD_BRANCH:$REMOTE_SHA" origin "$HEAD_BRANCH" 2>/dev/null; then
        git -C "$REPO_ROOT" reset -q --hard "$PRE_HEAD"
        echo "NEEDS_HUMAN: $HEAD_BRANCH moved on origin during rewrite" >&2; exit 2
      fi
    fi
    HEAD_SHA=$(git -C "$REPO_ROOT" rev-parse --verify HEAD)
    COMMITS_AHEAD=$(git -C "$REPO_ROOT" rev-list --count "$(git -C "$REPO_ROOT" merge-base "$BASE_REF" HEAD)..HEAD")
  fi
  CHAIN_PARENT=""
fi
# fence:spec-close
SPEC_CLOSED=0
if [[ "$DRY_RUN" != "1" && "${UPDATE_MODE:-0}" != "1" && "$TASK_COUNT" -gt 0 && "$OPEN_COUNT" -eq 0 && "$(printf '%s' "$SPEC_JSON" | jq -r '.status')" != "done" ]]; then
  CURRENT_BRANCH=$(git -C "$REPO_ROOT" branch --show-current)
  [[ -n "$CURRENT_BRANCH" ]] || { echo "Error: cannot close for a detached PR head" >&2; exit 1; }
  SPEC_CLOSE_PATH=".flow/specs/$SPEC_ID.json"
  [[ -f "$REPO_ROOT/$SPEC_CLOSE_PATH" ]] || SPEC_CLOSE_PATH=".flow/epics/$SPEC_ID.json"
  PRE_CLOSE_PATHS=("$SPEC_CLOSE_PATH")
  while IFS= read -r TASK_ID; do
    PRE_CLOSE_PATHS+=(".flow/tasks/$TASK_ID.json")
  done < <(printf '%s' "$SPEC_JSON" | jq -r '.tasks[]?.id')
  CLOSE_DIRTY=$(git -C "$REPO_ROOT" status --porcelain --untracked-files=no -- "${PRE_CLOSE_PATHS[@]}") || {
    echo "Error: cannot inspect spec close paths; PR not opened" >&2; exit 1;
  }
  [[ -z "$CLOSE_DIRTY" ]] || {
    echo "Error: pending changes in spec close paths; commit them before make-pr closes the spec; PR not opened" >&2; exit 1;
  }
  if [[ "$(printf '%s' "$SPEC_JSON" | jq -r '.branch_name // empty')" != "$CURRENT_BRANCH" ]]; then
    "$FLOWCTL" spec set-branch "$SPEC_ID" --branch "$CURRENT_BRANCH" --json || {
      echo "Error: spec branch update failed; PR not opened" >&2; exit 1;
    }
  fi
  if ! CLOSE_JSON=$("$FLOWCTL" spec close "$SPEC_ID" --json); then
    printf '%s\n' "$CLOSE_JSON" >&2
    echo "Error: spec close failed; PR not opened (see reason above)" >&2; exit 1;
  fi
  CLOSE_PATHS=()
  while IFS= read -r CLOSE_PATH; do
    CLOSE_PATHS+=("$CLOSE_PATH")
  done < <(printf '%s' "$CLOSE_JSON" | jq -r '.modified_paths[]')
  git -C "$REPO_ROOT" add -- "${CLOSE_PATHS[@]}" || {
    echo "Error: spec close already written locally; staging failed; PR not opened" >&2; exit 1;
  }
  if ! git -C "$REPO_ROOT" diff --cached --quiet -- "${CLOSE_PATHS[@]}"; then
    git -C "$REPO_ROOT" commit -m "chore(flow): close $SPEC_ID" -- "${CLOSE_PATHS[@]}" || {
      echo "Error: spec close already written locally; commit failed; PR not opened" >&2; exit 1;
    }
  fi
  HEAD_SHA=$(git -C "$REPO_ROOT" rev-parse --verify HEAD)
  COMMITS_AHEAD=$(git -C "$REPO_ROOT" rev-list --count "$(git -C "$REPO_ROOT" merge-base "$BASE_REF" HEAD)..HEAD")
  SPEC_CLOSED=1
fi
# fence:spec-close-end
PHASE0_CONTEXT=$(jq -n --arg head "$HEAD_SHA" --arg branch "$(git -C "$REPO_ROOT" branch --show-current)" \
  --argjson commits_ahead "$COMMITS_AHEAD" --argjson spec_closed "$SPEC_CLOSED" --arg chain_parent "$CHAIN_PARENT" --arg parent_pr "$PARENT_PR" --arg parent_pr_state "$PARENT_PR_STATE" \
  '{head:$head, branch:$branch, commits_ahead:$commits_ahead, spec_closed:($spec_closed==1), chain_parent:$chain_parent, parent_pr:$parent_pr, parent_pr_state:$parent_pr_state}')
```

Already-closed specs stay untouched. Otherwise completed specs close on the head branch before Phase 1. Incomplete or
task-less specs have no close commit and still compose interactively. For `OPEN_COUNT > 0`,
Ralph/autonomous hard-errors (exit 2). Dry-run and body-only updates never close. Under `--update` an
existing OPEN PR is REQUIRED; closed/merged PRs do not prevent a create. Preserve `PHASE0_CONTEXT.head`.
## Phase 1: Gather inputs

Capture `EXPORT_PAYLOAD` from `$FLOWCTL spec export-cognitive-aid "$SPEC_ID"
--base "$BASE_REF" --json` once, after close. Refresh `HEAD_SHA` and `MERGE_BASE`
from this head and base. For each entry in `specs` (otherwise the host), stop for empty goal/context AND
empty task summaries. Only the host aborts for nonempty criteria ALL in `tasks_summary.undeclared_r_ids`
(`Undeclared R-ID coverage`); siblings render those requirements as uncovered. No requirements is valid.
## Phase 1.5: Structured PR cognitive-aid

Read [pr-cognitive-aid.md](pr-cognitive-aid.md) and execute it on every entry path, including dry-run and
update, before optional HTML or body delivery.
## Phase 1.5b: HTML render lens (opt-in)

```bash
HTML_LENS=$("$FLOWCTL" config get artifacts.html.enabled --json | jq -r 'if .value == true then "true" else "false" end')
[[ "$DRY_RUN" == "1" ]] && HTML_LENS=false
```

When true, read [html-lens.md](html-lens.md) in full and execute it end-to-end. When false,
do not read `html-lens.md` or the shared disclosure reference; emit no artifact, commit, body line or output. The lens is
unchanged; retain its optional Render lens line when it succeeds.
## Phase 2: Deliver the briefing

Use rendered `BODY_FILE` unchanged; append the enabled lens line before `Ref` / Stack lines.
The renderer's numbered groups and linked file lists supply the structural sketch; the lens's old summary-block references mean this position.

For dry-run, print `BODY_FILE` and stop. Otherwise read [create-and-finalize.md](create-and-finalize.md) and
complete it.

[Manual smoke](references/manual-smoke.md) is a maintainer checklist, never loaded at runtime.
