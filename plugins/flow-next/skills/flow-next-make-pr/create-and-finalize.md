# Create and finalize

Real create/update only. Title: spec title verbatim up to 72 characters; otherwise first goal/context sentence
up to 70 plus ellipsis, or spec ID if empty. Persist the rendered body using Write to a private `BODY_FILE`
tempfile, never shell-interpolate its content. Require nonempty content. If over 65,000 characters, stop with
the retained local file; never spill a commit after close or truncate renderer output by hand. Clean temporary
files on exit.

## Draft state
Set `OPEN_ITEMS_COUNT` from spec open questions, `deferred_findings`, completion review `needs_work` (read
`flowctl show`), and incomplete tasks. Include other unfinished authored open items; QA findings remain
advisory, not draft gates. Restore `CHAIN_PARENT`, `PARENT_PR`, `PARENT_PR_STATE` from `PHASE0_CONTEXT`.
```bash
# fence:draft-matrix — inputs: RALPH, AUTONOMOUS, OPEN_ITEMS_COUNT, DRAFT_FORCE, CHAIN_PARENT (from PHASE0_CONTEXT.chain_parent; empty when not chained)
DRAFT_FLAG=""
if [[ "$RALPH" == "1" || "$AUTONOMOUS" == "1" ]]; then DRAFT_FLAG="--draft"; fi
if [[ -n "${CHAIN_PARENT:-}" && "$OPEN_ITEMS_COUNT" -eq 0 ]]; then DRAFT_FLAG=""; fi
if [[ "$OPEN_ITEMS_COUNT" -gt 0 ]]; then DRAFT_FLAG="--draft"; fi
if [[ "$DRAFT_FORCE" == "draft" ]]; then DRAFT_FLAG="--draft"; fi
if [[ "$DRAFT_FORCE" == "ready" && "$RALPH" != "1" && "$AUTONOMOUS" != "1" ]]; then DRAFT_FLAG=""; fi
if [[ -n "${CHAIN_PARENT:-}" && "$OPEN_ITEMS_COUNT" -gt 0 ]]; then DRAFT_FLAG="--draft"; fi
if [[ "$DRAFT_FORCE" == "ready" && ( "$RALPH" == "1" || "$AUTONOMOUS" == "1" ) ]]; then
  echo "Note: --ready ignored under Ralph/autonomous mode. PR will open as draft (autonomous-loop terminus)." >&2
fi
```

## Push and create/update
Immediately before push, require the current artifact's head to match HEAD; a mismatch uses the labeled
fallback, never stale fields. The closed-head fence also stops any create whose branch or head changed after
close.
```bash
HEAD_BRANCH=$(git branch --show-current)
if [[ -z "$HEAD_BRANCH" ]]; then
  echo "Error: detached HEAD or empty branch name; cannot create PR. Check out a branch first." >&2; exit 1; fi
# fence:closed-head-check
if [[ "$(printf '%s' "$PHASE0_CONTEXT" | jq -r '.spec_closed // false')" == "true" ]]; then
  if [[ "$(git rev-parse HEAD)" != "$(printf '%s' "$PHASE0_CONTEXT" | jq -r '.head')" || "$HEAD_BRANCH" != "$(printf '%s' "$PHASE0_CONTEXT" | jq -r '.branch')" ]]; then
    echo "Error: PR head changed after spec close; rerun make-pr before opening the PR" >&2; exit 1; fi
fi
# fence:closed-head-check-end
PUSH_OUT=$(git push -u origin HEAD 2>&1)
PUSH_RC=$?
if [[ "$PUSH_RC" -ne 0 ]]; then
  echo "Error: git push failed:" >&2
  echo "$PUSH_OUT" >&2
  exit 1
fi
sleep 1   # GitHub API eventual-consistency lag (cli/cli #2691)
if [[ "${UPDATE_MODE:-0}" == "1" ]]; then
  UPDATE_PR_NUMBER=$(gh pr view --json number,state --jq 'select(.state=="OPEN") | .number' 2>/dev/null || true)
  if [[ -z "$UPDATE_PR_NUMBER" ]]; then
    echo "Error: --update: no open PR on this branch at edit time." >&2; exit 1
  fi
fi
```

Update mode preserves stack metadata from the existing PR:
```bash
# fence:stack-line-refresh — inputs: UPDATE_MODE, UPDATE_PR_NUMBER, BODY_FILE; gh on PATH
if [[ "${UPDATE_MODE:-0}" == "1" ]]; then
  STACK_OBJ=$(gh api "repos/{owner}/{repo}/pulls/$UPDATE_PR_NUMBER" --jq '.stack // empty' 2>/dev/null) || STACK_OBJ=""
  if [[ -n "$STACK_OBJ" ]] && ! grep -q '^> \*\*Stack:\*\*' "$BODY_FILE"; then
    STACK_LINE=$(printf '%s' "$STACK_OBJ" | jq -r '"**Stack:** #\(.number), layer \(.position) of \(.size)"')
    printf '\n> %s\n' "$STACK_LINE" >> "$BODY_FILE"
  fi
fi
```
```bash
if [[ "${UPDATE_MODE:-0}" == "1" ]]; then
  if gh pr edit "$UPDATE_PR_NUMBER" --body-file "$BODY_FILE"; then
    PR_URL=$(gh pr view "$UPDATE_PR_NUMBER" --json url --jq '.url')
    echo "Updated PR #$UPDATE_PR_NUMBER body (refreshed against the current diff)." >&2
  else
    echo "Error: gh pr edit #$UPDATE_PR_NUMBER --body-file failed." >&2
    exit 1
  fi
fi
```

An update now skips create-only linkage and creation below, then finalizes. On create, the seam
`FLOW_PR_CREATE_CMD` defaults to `gh pr create`, whitespace split without eval; the executable path cannot
contain spaces. It receives `--title`, `--body-file`, optional `--draft`, `--base`, `--head`; success must
print a PR URL, with logging allowed. The 3-attempt retry loop handles eventual-consistency errors only; other operations use
gh. Strip `origin/` only at the gh boundary.
```bash
BASE_BRANCH="${BASE_REF#origin/}"
TRK_ACTIVE=$("$FLOWCTL" sync active --json 2>/dev/null | jq -r '.active // empty' 2>/dev/null || true)
if [ "$TRK_ACTIVE" = "true" ]; then
  TRK_TYPE=$("$FLOWCTL" config get tracker.type --json 2>/dev/null | jq -r '.value // empty' 2>/dev/null || true)
  TRK_STATE=$("$FLOWCTL" sync get-state "$SPEC_ID" --json 2>/dev/null || printf '{}')
  TRK_ID=$(printf '%s' "$TRK_STATE" | jq -r '.tracker.identifier // empty' 2>/dev/null || true)
  REF=""
  case "$TRK_TYPE" in
    linear) [ -n "$TRK_ID" ] && REF="Ref ${TRK_ID}" ;;
    github) [ -n "$TRK_ID" ] && REF="Refs ${TRK_ID}" ;;
    gitlab) [ -n "$TRK_ID" ] && REF="Ref \`${TRK_ID}\`" ;;
    jira)   REF="" ;;
  esac
  if [ -n "$REF" ] && ! grep -qixF "$REF" "$BODY_FILE"; then
    printf '\n\n---\n%s\n' "$REF" >> "$BODY_FILE"
  fi
fi
PR_CREATE_CMD="${FLOW_PR_CREATE_CMD:-gh pr create}"
PR_URL=""
for attempt in 1 2 3; do
  if CREATE_OUT=$($PR_CREATE_CMD \
    --title "$PR_TITLE" \
    --body-file "$BODY_FILE" \
    $DRAFT_FLAG \
    --base "$BASE_BRANCH" \
    --head "$HEAD_BRANCH" 2>&1); then
    PR_URL=$(printf '%s\n' "$CREATE_OUT" | grep -Eo 'https://[^[:space:]]+/pull/[0-9]+' | tail -n1 || true)
    if [[ -z "$PR_URL" ]]; then
      echo "Error: PR create reported success but printed no PR URL (FLOW_PR_CREATE_CMD contract: print the .../pull/<n> URL)." >&2
      echo "$CREATE_OUT" >&2
      exit 1
    fi
    break
  fi
  case "$CREATE_OUT" in
    *"Head sha can't be blank"*|*"No commits between"*)
      sleep $((attempt * 2))   # 2s, 4s, 6s — total worst-case 12s before bailing
      continue
      ;;
  esac
  echo "Error: PR create failed ($PR_CREATE_CMD):" >&2
  echo "$CREATE_OUT" >&2
  exit 1
done
if [[ -z "$PR_URL" ]]; then
  echo "Error: Eventual-consistency exhaustion after 3 attempts." >&2
  echo "Manual recovery: wait 30s and re-run /flow-next:make-pr (skill detects the existing branch and re-tries)." >&2
  exit 1
fi
```

Link an open parent into a GitHub stack. Failures emit one stderr note and leave a plain chain, without retry
or unstack. Other forges skip the call.
```bash
# fence:stack-link — inputs: REPO_ROOT, PR_URL, BODY_FILE, CHAIN_PARENT, PARENT_PR, PARENT_PR_STATE (from PHASE0_CONTEXT); gh on PATH
STACK_LINE=""
if [[ -n "${CHAIN_PARENT:-}" && -n "${PARENT_PR:-}" && "${PARENT_PR_STATE:-}" == "OPEN" ]] \
   && git -C "$REPO_ROOT" remote get-url origin 2>/dev/null | grep -qi 'github\.com'; then
  NEW_PR="${PR_URL##*/}"
  STACK_NUMBER=""; LINK_RC=1; LINK_OUT=""
  OWNER_REPO=$(gh repo view --json owner,name --jq '.owner.login + "/" + .name' 2>&1) || { LINK_OUT="$OWNER_REPO"; OWNER_REPO=""; }
  if [[ -n "$OWNER_REPO" ]] && STACK_GET=$(gh api "repos/$OWNER_REPO/stacks?pull_request=$PARENT_PR" 2>&1); then
    STACK_NUMBER=$(printf '%s' "$STACK_GET" | jq -r '.[0].number // empty' 2>/dev/null)
    if [[ -n "$STACK_NUMBER" ]]; then
      if LINK_OUT=$(gh api --method POST "repos/$OWNER_REPO/stacks/$STACK_NUMBER/add" -F "pull_requests[]=$NEW_PR" 2>&1); then LINK_RC=0; fi
    else
      if LINK_OUT=$(gh api --method POST "repos/$OWNER_REPO/stacks" -F "pull_requests[]=$PARENT_PR" -F "pull_requests[]=$NEW_PR" 2>&1); then LINK_RC=0; fi
    fi
  elif [[ -n "$OWNER_REPO" ]]; then
    LINK_OUT="$STACK_GET"
  fi
  if [[ "$LINK_RC" -eq 0 ]]; then
    STACK_NUMBER=$(printf '%s' "$LINK_OUT" | jq -r --arg fallback "$STACK_NUMBER" '.number // $fallback' 2>/dev/null)
    STACK_SIZE=$(printf '%s' "$LINK_OUT" | jq -r '.pull_requests | length' 2>/dev/null)
    STACK_POS=$(printf '%s' "$LINK_OUT" | jq -r --argjson n "$NEW_PR" '(.pull_requests | map(.number) | index($n)) + 1' 2>/dev/null)
    STACK_LINE="**Stack:** #$STACK_NUMBER, layer $STACK_POS of $STACK_SIZE"
    printf '\n> %s\n' "$STACK_LINE" >> "$BODY_FILE"
    gh pr edit "$NEW_PR" --body-file "$BODY_FILE" >/dev/null 2>&1 || echo "stack line not written: gh pr edit #$NEW_PR failed" >&2
  else
    HTTP_CODE=$(printf '%s' "$LINK_OUT" | grep -Eo 'HTTP [0-9]{3}' | head -1 | cut -d' ' -f2)
    echo "stack link skipped: HTTP ${HTTP_CODE:-transport} $(printf '%s' "$LINK_OUT" | head -1)" >&2
  fi
fi
```
```bash
if [ "$TRK_ACTIVE" = "true" ] && [ -n "$REF" ]; then
  if grep -qixF "$REF" "$BODY_FILE" 2>/dev/null; then
    :
  else
    if LIVE_BODY=$(gh pr view "$PR_URL" --json body --jq .body 2>/dev/null); then
      if ! printf '%s\n' "$LIVE_BODY" | grep -qixF "$REF"; then
        NEW_BODY=$(printf '%s\n\n---\n%s\n' "$LIVE_BODY" "$REF")
        if [ "${#NEW_BODY}" -le 65536 ]; then
          printf '%s\n' "$NEW_BODY" | gh pr edit "$PR_URL" --body-file - 2>/dev/null || true
        fi
      fi
    fi
  fi
fi
```

## Finalize
After successful creation or update, optionally write a grounded `knowledge/architecture-patterns` memory
entry under `--memory`, with tag `spec-<SPEC_ID>` as its idempotency key; skip if that tag already exists.
Its prose follows [docs/prose.md](../../docs/prose.md) when present. Memory failure is non-fatal; never write by default or in dry-run.

When the bridge is active, invoke the inline tracker-sync wrapper with the prepared snapshots and optional
private breadcrumb, making one lifecycle call:
```bash
if [[ -n "$PR_URL" ]] && [ "$("$FLOWCTL" sync active --json | jq -r '.active')" = "true" ]; then
  # "$FLOWCTL" tracker sync "$SPEC_ID" --op reconcile --event makePr --pr-url "$PR_URL" <other legal file flags>
  :
fi
```
`off|pull|push|reconcile|comment` all use body-preserving `reconcile` for PR linkage and In Review;
`tracker.perEvent.makePr` gates only the optional breadcrumb, which Make PR synthesizes from the URL and
opened-PR context. Create-if-unlinked first; unreachable transport is a no-op. Use provider-native links or
URL-deduplicated fallback; never overwrite issue prose or mark Done. Failures warn without changing PR
success.

Audit `sync check "$SPEC_ID" --events makePr --since <PR-createdAt> --json` independently of dispatch. If
MISSING, record a UTC start, Retro-fire the same wrapper once with explicit `--pr-url`, then recheck since
that start. Never loop. Print the PR URL, `Reviewer feedback → /flow-next:resolve-pr <number>` and
`Body inspection → /flow-next:make-pr <spec-id> --dry-run` in native host invocation syntax (OpenCode
hyphenates the command). Under Ralph stdout is solely `PR_URL=<url>`, all other output goes to stderr. The last summary line (stderr under Ralph) is: `Tracker sync: <OK |
MISSING:makePr → retro-fired → OK | MISSING:makePr (retro-fire failed: <reason>) | n/a (bridge inactive)>`.
