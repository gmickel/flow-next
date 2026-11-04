#!/usr/bin/env bash
# Source from make-pr after setting its documented inputs; outputs remain in the caller.
set -e
# Windows jq.exe ends lines with CRLF; drop the CR so values match paths and compare equal (#541).
jq() { command jq "$@" | tr -d '\r'; return "${PIPESTATUS[0]}"; }
# The PR reads below run gh unless this block points them at the forge's read helper.
FORGE=""; PR_READ=""; PR_HEAD_REFS=""; GLAB_ANSWER=no
# On GitLab the three PR reads run the merge-request helper.
gitlab_reads() {
  ORIGIN_PROJECT=${ORIGIN_URL#*:}; [[ "$ORIGIN_URL" != *://* ]] || ORIGIN_PROJECT=${ORIGIN_URL#*://*/}
  ORIGIN_PROJECT=${ORIGIN_PROJECT%/}; ORIGIN_PROJECT=${ORIGIN_PROJECT#/}; ORIGIN_PROJECT=${ORIGIN_PROJECT%.git}
  export GITLAB_HOST="$ORIGIN_HOST" ORIGIN_PROJECT
  PR_READ="$(dirname "$FLOWCTL")/make-pr-gitlab.sh"; PR_HEAD_REFS=refs/merge-requests
}
{
  # The origin remote's host names the forge: GitHub pull requests through gh, GitLab merge
  # requests through glab; any other host stops before any close or push (#583).
  # An SSH host alias resolves through ssh -G, as in gh. The same rule is repo_forge in flowctl.py.
  # A dry run names the forge too, so its reads match a real run; it skips the stops and checks.
  ORIGIN_URL=$(git -C "$REPO_ROOT" remote get-url origin 2>/dev/null) || ORIGIN_URL=""
  ORIGIN_HOST=$(printf '%s' "$ORIGIN_URL" | sed -E 's#^[a-z+]+://([^@/]*@)?([^/:]+).*#\2#; s#^([^@/]*@)?([^/:]+):.*#\2#')
  if [[ "$ORIGIN_URL" != *://* || "$ORIGIN_URL" == ssh://* || "$ORIGIN_URL" == git+ssh://* ]]; then
    SSH_HOST=$(ssh -G "$ORIGIN_HOST" 2>/dev/null | awk '/^hostname /{print $2; exit}') || SSH_HOST=""
    [[ -z "$SSH_HOST" ]] || ORIGIN_HOST="$SSH_HOST"
  fi
  if [[ "$ORIGIN_HOST" == github.com || "$ORIGIN_HOST" == ssh.github.com ]]; then
    FORGE=github
  else
    # An http(s) port is the forge's own (an SSH port is not), so it stays on the host.
    ORIGIN_HOST="$(printf '%s' "$ORIGIN_HOST" | tr '[:upper:]' '[:lower:]')$(printf '%s' "$ORIGIN_URL" | sed -nE 's#^https?://([^@/]*@)?[^/:]+(:[0-9]+)(/.*)?$#\2#p')"
    # An SSH origin names no web port; glab's own GITLAB_HOST does when it names the same host.
    GL_HOST=$(printf '%s' "${GITLAB_HOST:-}" | tr '[:upper:]' '[:lower:]' | sed -E 's#^https?://##; s#/+$##')
    if [[ "$ORIGIN_URL" != http://* && "$ORIGIN_URL" != https://* && "$ORIGIN_HOST" != gitlab.com && -n "$GL_HOST" && "${GL_HOST%%:*}" == "$ORIGIN_HOST" ]]; then
      ORIGIN_HOST="$GL_HOST"
    fi
    ENTERPRISE_GH="${GH_ENTERPRISE_TOKEN:-}${GITHUB_ENTERPRISE_TOKEN:-}"
    if [[ ! "$ORIGIN_HOST" =~ ^[a-z0-9.-]+(:[0-9]+)?$ ]]; then
      GLAB_ANSWER=unknown
    elif [[ "$ORIGIN_HOST" == gitlab.com || ( -n "${CI_SERVER_HOST:-}" && "${ORIGIN_HOST%%:*}" == "$(printf '%s' "$CI_SERVER_HOST" | tr '[:upper:]' '[:lower:]')" ) ]]; then
      FORGE=gitlab
    elif [[ -z "$ENTERPRISE_GH" ]] && command -v gh >/dev/null 2>&1 && gh auth token --hostname "$ORIGIN_HOST" >/dev/null 2>&1; then
      FORGE=github
    elif command -v glab >/dev/null 2>&1; then
      # Only glab's logged-out answer is a no; a failed answer (an offline host) leaves the
      # host unknown. gh with an enterprise token claims every host, so glab answered first.
      if GLAB_STATUS=$(glab auth status --hostname "$ORIGIN_HOST" 2>&1); then GLAB_ANSWER=yes; FORGE=gitlab
      elif [[ "$(printf '%s' "$GLAB_STATUS" | tr -s '[:space:]' ' ')" != *"has not been authenticated"* ]]; then GLAB_ANSWER=unknown; fi
    fi
    if [[ -z "$FORGE" && -n "$ENTERPRISE_GH" && "$GLAB_ANSWER" == no ]] && command -v gh >/dev/null 2>&1 \
      && gh auth token --hostname "$ORIGIN_HOST" >/dev/null 2>&1; then
      FORGE=github
    fi
  fi
  if [[ "$DRY_RUN" == "1" ]]; then
    # A preview reads merge requests when glab can answer, and otherwise previews through gh as before.
    if [[ "$FORGE" == gitlab ]] && command -v glab >/dev/null 2>&1 \
      && { [[ "$GLAB_ANSWER" == yes ]] || glab auth status --hostname "$ORIGIN_HOST" >/dev/null 2>&1; }; then
      gitlab_reads
    fi
  elif [[ -z "$FORGE" ]]; then
    echo "NEEDS_HUMAN: make-pr opens GitHub pull requests only on github.com or a host gh is logged in to, and GitLab merge requests on gitlab.com or a host glab is logged in to; origin host ${ORIGIN_HOST:-none} is neither. Run gh auth login --hostname ${ORIGIN_HOST:-<host>} or glab auth login --hostname ${ORIGIN_HOST:-<host>} (with an SSH origin whose GitLab web port differs, set GITLAB_HOST=<host>:<port>), or open the request by hand." >&2; exit 2
  elif [[ "$FORGE" == gitlab ]]; then
    if ! command -v glab >/dev/null 2>&1; then
      echo "Error: glab CLI not installed. Install glab from https://gitlab.com/gitlab-org/cli then run glab auth login --hostname $ORIGIN_HOST." >&2; exit 1; fi
    if [[ "$GLAB_ANSWER" != yes ]] && ! glab auth status --hostname "$ORIGIN_HOST" >/dev/null 2>&1; then
      echo "Error: glab CLI not authenticated to $ORIGIN_HOST, or the host is unreachable; run glab auth login --hostname $ORIGIN_HOST." >&2; exit 1; fi
    # The one forge guard: on GitLab the three PR reads run the merge-request helper.
    gitlab_reads
    if ! "$PR_READ" api-scope; then
      echo "NEEDS_HUMAN: make-pr needs a glab token with api scope on $ORIGIN_HOST to open merge requests; run glab auth login --hostname $ORIGIN_HOST with an api-scoped token." >&2; exit 2; fi
  else
    if ! command -v gh >/dev/null 2>&1; then
      echo "Error: gh CLI not installed. Install gh from https://cli.github.com then run gh auth login." >&2; exit 1; fi
    # github.com first; otherwise any logged-in host, since later gh calls pick the host from the remote (GitHub Enterprise, #532).
    if ! gh auth status --hostname github.com >/dev/null 2>&1 && ! gh auth status >/dev/null 2>&1; then
      echo "Error: gh CLI not authenticated; run gh auth status to see which host needs gh auth login." >&2; exit 1; fi
  fi
}
# end:block
# fence:chain-detect — inputs: REPO_ROOT, FLOWCTL, SPEC_ID, BASE_REF, DRY_RUN
# A dry run may preview against a commit SHA; a live PR base must be a branch.
if [[ "$DRY_RUN" == "1" && "$BASE_REF" =~ ^[0-9a-f]{7,40}$ ]] && git -C "$REPO_ROOT" rev-parse --verify --quiet "$BASE_REF^{commit}" >/dev/null 2>&1; then
  :
elif [[ -n "$BASE_REF" && "$BASE_REF" != refs/* ]]; then
  BASE_BRANCH="${BASE_REF#origin/}"
  if [[ "$DRY_RUN" != "1" ]]; then
    git -C "$REPO_ROOT" fetch -q origin "refs/heads/${BASE_BRANCH}:refs/remotes/origin/${BASE_BRANCH}" || { echo "Error: cannot refresh origin/$BASE_BRANCH" >&2; exit 1; }
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
    # The exit ends this shell; the no-spec path needs the forge's values from this line.
    [[ -z "$PR_READ" ]] || printf 'FORGE=%q PR_READ=%q GITLAB_HOST=%q ORIGIN_PROJECT=%q\n' "$FORGE" "$PR_READ" "$GITLAB_HOST" "$ORIGIN_PROJECT"
    echo "NO_SPEC"; exit 4
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
    if git -C "$REPO_ROOT" fetch -q origin "refs/heads/${DEP_BRANCH}:refs/remotes/origin/${DEP_BRANCH}" 2>/dev/null; then DEP_REF="refs/remotes/origin/$DEP_BRANCH"; fi
    if DEP_PR_LIST=$("${PR_READ:-gh}" pr list --head "$DEP_BRANCH" --state all --json number,state,baseRefName 2>/dev/null); then
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
      DEP_PR_HEAD="refs/pull/$DEP_PR_NUMBER/head"; [[ -z "${PR_HEAD_REFS:-}" ]] || DEP_PR_HEAD="$PR_HEAD_REFS/$DEP_PR_NUMBER/head"
      if git -C "$REPO_ROOT" fetch -q origin "${DEP_PR_HEAD}:refs/flow-next/parent/$DEP_BRANCH" 2>/dev/null; then
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
      git -C "$REPO_ROOT" fetch -q origin "refs/heads/${PARENT_PR_BASE}:refs/remotes/origin/${PARENT_PR_BASE}" 2>/dev/null \
        || { echo "NEEDS_HUMAN: cannot refresh chain base $PARENT_PR_BASE from origin; no rewrite" >&2; exit 2; }
      REWRITE_ONTO="origin/$PARENT_PR_BASE"; BASE_REF="$REWRITE_ONTO"; CHAIN_REWRITE=1 ;;
    CLOSED)
      echo "NEEDS_HUMAN: parent $CHAIN_PARENT PR #$PARENT_PR closed unmerged; the chain is broken" >&2
      exit 2 ;;
  esac
fi
[[ -z "$BASE_REF" ]] && BASE_REF="$CHAIN_BASE"
if [[ -z "$BASE_REF" ]]; then
  if [[ "$AUTONOMOUS" == "1" ]]; then
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
# end:block
# --- §0.5: tasks-done validation (single show capture = spec-existence validation) ---
if ! SPEC_JSON=$("$FLOWCTL" show "$SPEC_ID" --json 2>/dev/null); then
  echo "Error: spec '$SPEC_ID' not found in .flow/specs/. Check id with: $FLOWCTL specs" >&2; exit 1; fi
SPEC_ID=$(printf '%s' "$SPEC_JSON" | jq -r '.id')
OPEN_TASKS=$(printf '%s' "$SPEC_JSON" | jq -r '[.tasks[]? | select(.status != "done" and .status != "retired") | .id] | join(", ")')
TASK_COUNT=$(printf '%s' "$SPEC_JSON" | jq '[.tasks[]?] | length')
OPEN_COUNT=$(printf '%s' "$SPEC_JSON" | jq '[.tasks[]? | select(.status != "done" and .status != "retired")] | length')
if [[ "$OPEN_COUNT" -gt 0 ]]; then
  if [[ "$AUTONOMOUS" == "1" ]]; then
    echo "Error: $OPEN_COUNT task(s) under $SPEC_ID still open ($OPEN_TASKS). Autonomous context cannot open PRs for incomplete specs." >&2
    exit 2
  else
    echo "Note: $OPEN_COUNT task(s) not yet done ($OPEN_TASKS); the spec remains open and is not closed. Opening as a DRAFT. Once /flow-next:work finishes them, run /flow-next:make-pr $SPEC_ID --update to close the spec, then mark the PR ready." >&2
  fi
fi
if [[ "$TASK_COUNT" -eq 0 ]]; then
  echo "Note: $SPEC_ID has no tasks; the spec remains open and is not closed." >&2
fi
# A configured completion review that has not passed keeps the spec open, so land cannot merge unreviewed work (#477).
REVIEW_PENDING=$(printf '%s' "$SPEC_JSON" | jq -r '.completion_review_pending // false')
if [[ "$REVIEW_PENDING" == "true" && "$OPEN_COUNT" -eq 0 && "$(printf '%s' "$SPEC_JSON" | jq -r '.status')" != "done" ]]; then
  REVIEW_STATUS=$(printf '%s' "$SPEC_JSON" | jq -r '.completion_review_status // "unknown"')
  if [[ "$AUTONOMOUS" == "1" ]]; then
    echo "Error: completion review for $SPEC_ID reads $REVIEW_STATUS. Autonomous context cannot open PRs for unreviewed specs." >&2
    exit 2
  fi
  echo "Note: completion review for $SPEC_ID reads $REVIEW_STATUS; the spec remains open and is not closed. Opening as a DRAFT. Once /flow-next:spec-completion-review $SPEC_ID passes, run /flow-next:make-pr $SPEC_ID --update to close the spec, then mark the PR ready." >&2
fi
# gh's failure is its "no PR on this branch"; a failed merge-request read is never "no MR".
EXISTING_JSON=$("${PR_READ:-gh}" pr view --json url,state,number 2>/dev/null) || [[ -z "${PR_READ:-}" ]] || {
  [[ "$DRY_RUN" == "1" ]] && echo "Note: cannot read the merge requests of this branch under --dry-run; previewing as if none is open." >&2; } || {
  echo "NEEDS_HUMAN: cannot read the merge requests of this branch; nothing closed or pushed" >&2; exit 2; }
EXISTING_JSON=$(printf '%s' "$EXISTING_JSON" | jq -c 'select(.state == "OPEN")' || true)
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
    PRIOR_PRS=$("${PR_READ:-gh}" pr list --head "$HEAD_BRANCH" --state all --json number,state --jq '[.[] | select(.state=="OPEN" or .state=="MERGED")] | length' 2>/dev/null) || PRIOR_PRS=""
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
if [[ "$DRY_RUN" != "1" && "$TASK_COUNT" -gt 0 && "$OPEN_COUNT" -eq 0 && "$REVIEW_PENDING" != "true" && "$(printf '%s' "$SPEC_JSON" | jq -r '.status')" != "done" ]]; then
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
    git -C "$REPO_ROOT" commit -m "${CLOSE_COMMIT_MESSAGE:-chore(flow): close $SPEC_ID}" -- "${CLOSE_PATHS[@]}" || {
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
# end:block
