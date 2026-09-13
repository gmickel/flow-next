# Chains and stacks — land reference

Read from `workflow.md` §2.0 (shape), §2.8 (frontier rule), §3.5b (native merge), and §3.7 (`retarget`). This page holds the vocabulary, the invariant, and the one cascade fence the plain path executes. Everything else about chains is a rule the tick applies from the PR and git each time; nothing here is stored beyond the ledger fields `workflow.md` Phase 0 lists.

## Vocabulary

- **Chain**: a dependent PR whose base is the parent's branch, on any host. **Stack**: GitHub's server-side object over a chain (the REST payload's non-null `stack`). **Layer**: one PR in either. **Frontier**: the bottom open layer, the only one land merges.
- **Native path**: the PR carries a `stack` object; GitHub owns sequential merge (`merge-async`) and auto-retarget. **Plain path**: `stack` is null and the base heads another PR; land owns the retarget.
- **Verdict head / verdict patch-id**: the head a review verdict was satisfied at, and the stable `git patch-id` of base-to-head there (§2.2b).

## The three shapes and the frontier rule

| `stack` | base ref | Shape | Merge | Retarget |
|---|---|---|---|---|
| non-null | any | stacked layer | `merge-async`, squash, `direct_merge`, `sha` pin (§3.5b) | GitHub |
| null | heads an open or merged PR | plain chain layer | `gh pr merge` (§3.5) | land (§3.7, below) |
| null | heads no PR (the chain base) | standalone | `gh pr merge` with `--delete-branch` unless children exist | none |

A stacked layer merges only when the stack read in the same tick, and once more immediately before the submit, shows it as the lowest open layer: `merge-async` on a higher layer merges every open layer below it (the collapse hazard), and two reads bound that window to seconds. A plain chain layer merges only when its base is the chain base and every `depends_on_epics` spec is `done`. Land merges at most one layer per tick; after a merge every remaining planned action in the same tick downgrades to `RESOLVING`, and the next layer advances only after the merged layer's re-probe shows `state == MERGED` with a non-null `mergedAt`.

## Children and the branch janitor

Before any merge, `gh pr list --base <head branch> --state open` counts open children on every shape. A PR with children merges without `--delete-branch` (deleting first closes the child, verified 2026-08-27) and its branch goes into the ledger's top-level `pending_branch_deletes`; the §0.5 sweep at the start of every tick deletes a recorded branch once no open PR targets it (422 removes the entry silently, 403 is reported once per tick and kept). Native merges never delete a branch (verified 2026-09-13), so a stacked merge always records its branch.

## The chain invariant

Every open layer's history contains the current tip of the layer below it. That is what makes `git merge-base <child> <parent tip>` the exact boundary of the parent's work inside the child, and why a rewrite of one layer cascades upward in the same operation. Only land, inside its tick claim, rewrites a chained branch; work and make-pr never rewrite a branch that has a PR, and resolve-pr and the ci-fix step push commits, never rewrites. A human rebase that keeps the invariant is absorbed by the patch-id rule; one that breaks it surfaces as a conflict or as a boundary the cascade refuses.

## Cascade (plain path, `retarget`)

Two phases so that a failure in the second is always resumable: **prepare** every open layer above the merged one locally, bottom-up, each rebased from its merge-base with the pre-rewrite tip of the layer below onto the rewritten tip below it (the chain base for the first), kept under `refs/flow-next/cascade/<layer>`; then **publish** from a ledger record written before the first push. The record shape is exhaustive: `{"chain_base": "<ref>", "merged_parent": "<branch>", "layers": [{"branch": "<b>", "pr": <number>, "old_tip": "<sha>", "new_tip": "<sha>", "published": false, "base_edited": false}]}` (`base_edited` meaningful on the first layer only). A tick that finds a record resumes it and does nothing else for that chain until it clears.

Inputs: `MERGED_PARENT` (the merged parent's branch), `PARENT_PR` (its number), `CHAIN_BASE`, the ledger variables, `OWNER_REPO`, `TODAY`; `gh` on PATH; the clone's `origin`. Outputs: `CASCADE_VERDICT` (`resolving` after a complete or lease-interrupted cascade, `blocked` on a conflict, `needs_human`) and `CASCADE_REASON`. The fence is shell-portable (no indexed arrays; bash and zsh both run it).

```bash
# fence:cascade — inputs: MERGED_PARENT, PARENT_PR, CHAIN_BASE, LEDGER, LEDGER_DIR, LEDGER_JSON, OWNER_REPO, TODAY; gh on PATH; origin reachable
CASCADE_VERDICT=resolving; CASCADE_REASON=""; CASCADE_STOPPED=""
CASCADE_NS="refs/flow-next/cascade"; WT_ROOT="$LEDGER_DIR/cascade-wt"
cascade_write() { mkdir -p "$LEDGER_DIR"; [ -s "$LEDGER" ] || echo '{}' > "$LEDGER"; tmp="$LEDGER.tmp.$$"; jq "$@" "$LEDGER" > "$tmp" && mv "$tmp" "$LEDGER"; LEDGER_JSON="$(cat "$LEDGER")"; }
cascade_stop() { CASCADE_VERDICT="$1"; CASCADE_REASON="$2"; CASCADE_STOPPED=1; }   # every later phase is skipped once a stop is recorded
cascade_clear_refs() { git for-each-ref --format='%(refname)' "$CASCADE_NS/" | while read -r r; do git update-ref -d "$r"; done; }
cascade_rebase() {   # $1 layer, $2 from-tip, $3 fork, $4 onto → prints the new tip; rc 1 = conflict (prints the conflicting files instead), rc 2 = worktree failure
  local wt="$WT_ROOT/$1" new
  git worktree remove --force "$wt" 2>/dev/null; git worktree prune
  git worktree add -q --detach "$wt" "$2" 2>/dev/null || return 2
  if ! git -C "$wt" rebase --onto "$4" "$3" >/dev/null 2>&1; then
    git -C "$wt" diff --name-only --diff-filter=U | tr '\n' ' '
    git -C "$wt" rebase --abort 2>/dev/null; git worktree remove --force "$wt"; return 1
  fi
  new="$(git -C "$wt" rev-parse HEAD)"; git worktree remove --force "$wt"
  git update-ref "$CASCADE_NS/$1" "$new"; printf '%s' "$new"
}
cascade_pushed() {   # $1 pr number, $2 new tip — the canonical post-push ledger write (§3.1 step 4) for a published layer
  local url dec; url="$(gh pr view "$1" --json url --jq .url 2>/dev/null)"; dec="$(gh pr view "$1" --json reviewDecision --jq '.reviewDecision // "-"' 2>/dev/null)"
  [[ -n "$url" ]] && cascade_write --arg pr "$url" --arg sha "$2" --arg dec "${dec:--}" '.[$pr].land_pushed_sha = $sha | .[$pr].decision_at_push = (if $dec == "" then "-" else $dec end)'
}

RECORD="$(printf '%s\n' "$LEDGER_JSON" | jq -c '.cascade // empty')"
if [[ -z "$RECORD" ]]; then
  # ---- PREPARE (no remote writes) ----
  LAYERS=""; BELOW="$MERGED_PARENT"
  while :; do
    KIDS="$(gh pr list --base "$BELOW" --state open --json number,headRefName --limit 20 2>/dev/null)" || { cascade_stop resolving "cannot read the children of $BELOW; nothing prepared, re-tick"; break; }
    KID_N="$(printf '%s\n' "$KIDS" | jq 'length')"
    [[ "$KID_N" == 0 ]] && break
    [[ "$KID_N" != 1 ]] && { cascade_stop needs_human "$BELOW has $KID_N open children; the cascade needs a linear chain"; break; }
    BELOW="$(printf '%s\n' "$KIDS" | jq -r '.[0].headRefName')"
    LAYERS="${LAYERS}${BELOW}	$(printf '%s\n' "$KIDS" | jq -r '.[0].number')
"
  done
  if [[ -z "$CASCADE_STOPPED" && -z "$LAYERS" ]]; then cascade_stop needs_human "no open layer above $MERGED_PARENT; nothing to retarget"; fi
  if [[ -z "$CASCADE_STOPPED" ]]; then
    git fetch -q origin "refs/heads/$CHAIN_BASE" $(printf '%s' "$LAYERS" | cut -f1 | sed 's|^|refs/heads/|') 2>/dev/null \
      || cascade_stop needs_human "cannot fetch the chain from origin"
  fi
  if [[ -z "$CASCADE_STOPPED" ]]; then
    if git fetch -q origin "refs/heads/$MERGED_PARENT" 2>/dev/null; then
      BELOW_OLD="$(git rev-parse "origin/$MERGED_PARENT")"
    else
      # parent branch already deleted by a human: fall back to the first layer's recorded base SHA (verdict_base), made reachable via the merged PR's head ref
      FIRST_PR="$(printf '%s' "$LAYERS" | head -1 | cut -f2)"; FIRST_URL="$(gh pr view "$FIRST_PR" --json url --jq .url 2>/dev/null)"
      BELOW_OLD="$(printf '%s\n' "$LEDGER_JSON" | jq -r --arg pr "$FIRST_URL" '.[$pr].verdict_base // ""')"
      git fetch -q origin "refs/pull/$PARENT_PR/head" 2>/dev/null || true
      { [[ -z "$BELOW_OLD" ]] || ! git cat-file -e "$BELOW_OLD^{commit}" 2>/dev/null; } \
        && cascade_stop needs_human "parent branch $MERGED_PARENT gone; rebase #$FIRST_PR onto $CHAIN_BASE by hand"
    fi
  fi
  if [[ -z "$CASCADE_STOPPED" ]]; then
    ONTO="$(git rev-parse "origin/$CHAIN_BASE")"; ONTO_NAME="$CHAIN_BASE"; PREPARED='[]'
    while IFS='	' read -r LAYER PRN; do
      [[ -z "$LAYER" ]] && continue
      OLD_TIP="$(git rev-parse "origin/$LAYER")"
      FORK="$(git merge-base "$OLD_TIP" "$BELOW_OLD")"   # boundary against the PRE-rewrite tip of the layer below
      if [[ -z "$FORK" ]] || git merge-base --is-ancestor "$FORK" "origin/$CHAIN_BASE"; then
        cascade_stop needs_human "chain history for $LAYER does not contain its parent; rebase by hand"; break
      fi
      NEW_TIP="$(cascade_rebase "$LAYER" "$OLD_TIP" "$FORK" "$ONTO")" || {
        [[ $? -eq 1 ]] && cascade_stop blocked "retarget of #$PRN onto $ONTO_NAME conflicts in ${NEW_TIP:-<unknown>}" \
                       || cascade_stop needs_human "cannot create a worktree for $LAYER"; break; }
      PREPARED="$(printf '%s' "$PREPARED" | jq -c --arg b "$LAYER" --argjson pr "$PRN" --arg o "$OLD_TIP" --arg n "$NEW_TIP" '. + [{"branch": $b, "pr": $pr, "old_tip": $o, "new_tip": $n, "published": false, "base_edited": false}]')"
      ONTO="$NEW_TIP"; ONTO_NAME="$LAYER"; BELOW_OLD="$OLD_TIP"
    done <<EOF_LAYERS
$LAYERS
EOF_LAYERS
    if [[ -z "$CASCADE_STOPPED" ]]; then
      cascade_write --arg cb "$CHAIN_BASE" --arg mp "$MERGED_PARENT" --argjson layers "$PREPARED" '.cascade = {"chain_base": $cb, "merged_parent": $mp, "layers": $layers}'   # the record precedes the first push
      RECORD="$(printf '%s\n' "$LEDGER_JSON" | jq -c '.cascade')"
    else
      cascade_clear_refs   # nothing published, no record: the chain is exactly as before
    fi
  fi
fi

if [[ -n "$RECORD" && -z "$CASCADE_STOPPED" ]]; then
  # ---- RECONCILE (no remote writes): each unpublished layer's remote head against the recorded tips. A layer that
  # must be re-prepared invalidates every layer above it, and every replacement is PERSISTED in the record before
  # the publish pass pushes anything — an interruption between two pushes never publishes a stale upper tip. ----
  CHAIN_BASE="$(printf '%s' "$RECORD" | jq -r '.chain_base')"; MERGED_PARENT="$(printf '%s' "$RECORD" | jq -r '.merged_parent')"
  git fetch -q origin "refs/heads/$CHAIN_BASE" $(printf '%s' "$RECORD" | jq -r '.layers[].branch' | sed 's|^|refs/heads/|') 2>/dev/null || true
  git fetch -q origin "refs/heads/$MERGED_PARENT" 2>/dev/null || true
  BELOW_OLD="$(git rev-parse -q --verify "origin/$MERGED_PARENT" 2>/dev/null || true)"; BELOW_NEW="$(git rev-parse "origin/$CHAIN_BASE")"
  REPREPARE=0; IDX=0
  while IFS='	' read -r LAYER PRN OLD_TIP NEW_TIP PUBLISHED BASE_EDITED; do
    [[ -z "$LAYER" ]] && continue
    if [[ "$PUBLISHED" != true ]]; then
      if ! git cat-file -e "$OLD_TIP^{commit}" 2>/dev/null || ! git cat-file -e "$NEW_TIP^{commit}" 2>/dev/null; then
        cascade_stop needs_human "cascade for $MERGED_PARENT was prepared in another checkout; finish it there or rebase by hand"; break
      fi
      REMOTE="$(git ls-remote origin "refs/heads/$LAYER" | cut -f1)"
      if [[ "$REPREPARE" == 0 ]] && { [[ "$REMOTE" == "$NEW_TIP" ]] || git merge-base --is-ancestor "$NEW_TIP" "$REMOTE" 2>/dev/null; }; then
        cascade_write --argjson i "$IDX" '.cascade.layers[$i].published = true'   # the push landed (possibly with commits on top): no second rewrite
      elif [[ "$REPREPARE" == 0 && "$REMOTE" == "$OLD_TIP" ]]; then
        :   # the prepared tip is still valid; the publish pass pushes it
      elif [[ "$REPREPARE" == 1 ]] || git merge-base --is-ancestor "$OLD_TIP" "$REMOTE" 2>/dev/null; then
        # someone committed on the old history, or a layer below was re-prepared: re-prepare from the CURRENT head against the recorded tips below
        [[ -z "$BELOW_OLD" ]] && { cascade_stop needs_human "parent branch $MERGED_PARENT gone during a cascade; rebase #$PRN onto $CHAIN_BASE by hand"; break; }
        FORK="$(git merge-base "$REMOTE" "$BELOW_OLD")"
        RENEW="$(cascade_rebase "$LAYER" "$REMOTE" "$FORK" "$BELOW_NEW")" || {
          [[ $? -eq 1 ]] && cascade_stop blocked "retarget of #$PRN conflicts in ${RENEW:-<unknown>} (record kept)" \
                         || cascade_stop needs_human "cannot create a worktree for $LAYER"; break; }
        cascade_write --argjson i "$IDX" --arg o "$REMOTE" --arg n "$RENEW" '.cascade.layers[$i].old_tip = $o | .cascade.layers[$i].new_tip = $n'
        OLD_TIP="$REMOTE"; NEW_TIP="$RENEW"; REPREPARE=1
      else
        cascade_stop needs_human "$LAYER was rewritten by someone else during a cascade; reconcile by hand"; break
      fi
    fi
    BELOW_OLD="$OLD_TIP"; BELOW_NEW="$NEW_TIP"; IDX=$((IDX + 1))
  done <<EOF_RECONCILE
$(printf '%s' "$RECORD" | jq -r '.layers[] | [.branch, (.pr|tostring), .old_tip, .new_tip, (.published|tostring), (.base_edited|tostring)] | @tsv')
EOF_RECONCILE
fi
if [[ -n "$RECORD" && -z "$CASCADE_STOPPED" ]]; then
  # ---- PUBLISH (bottom-up, from the persisted record): lease on the recorded old tip, base edit for the first layer ----
  RECORD="$(printf '%s\n' "$LEDGER_JSON" | jq -c '.cascade')"; IDX=0
  while IFS='	' read -r LAYER PRN OLD_TIP NEW_TIP PUBLISHED BASE_EDITED; do
    [[ -z "$LAYER" ]] && continue
    if [[ "$PUBLISHED" != true ]]; then
      if ! git push -q --force-with-lease="refs/heads/$LAYER:$OLD_TIP" origin "$NEW_TIP:refs/heads/$LAYER" 2>/dev/null; then
        cascade_stop resolving "lease on $LAYER failed at $OLD_TIP; the record is kept and the next tick resumes"; break
      fi
      cascade_pushed "$PRN" "$NEW_TIP"
      cascade_write --argjson i "$IDX" '.cascade.layers[$i].published = true'
    fi
    if [[ "$IDX" == 0 && "$BASE_EDITED" != true ]]; then   # first layer only: retarget onto the chain base
      if ! gh pr edit "$PRN" --base "$CHAIN_BASE" >/dev/null 2>&1; then
        cascade_stop resolving "base edit of #$PRN to $CHAIN_BASE failed; retried next tick"; break
      fi
      cascade_write '.cascade.layers[0].base_edited = true'
    fi
    IDX=$((IDX + 1))
  done <<EOF_PUBLISH
$(printf '%s' "$RECORD" | jq -r '.layers[] | [.branch, (.pr|tostring), .old_tip, .new_tip, (.published|tostring), (.base_edited|tostring)] | @tsv')
EOF_PUBLISH
  if [[ -z "$CASCADE_STOPPED" ]] && printf '%s\n' "$LEDGER_JSON" | jq -e '.cascade.layers | all(.published) and (.[0].base_edited)' >/dev/null; then
    cascade_write 'del(.cascade)'; cascade_clear_refs
    CASCADE_REASON="cascade above $MERGED_PARENT published; layers re-gate next tick"
  fi
fi
```

Rules the fence encodes, for the reader:

- The record is written before the first push and cleared only after the last base edit. A push can succeed while the ledger write after it is lost, which is why resumption reconciles each unpublished layer's remote head first, in this order: at or above `new_tip` (published, no rewrite), at `old_tip` (push as prepared), above `old_tip` (re-prepare from the current head against the recorded tips below, and every layer above it likewise), anything else (`NEEDS_HUMAN`, a foreign rewrite). The reconcile pass persists every replacement tip in the record before the publish pass pushes anything, so a lease failure or crash between two pushes never leaves an upper layer's stale prepared tip to be published later.
- A failed child-list read during discovery prepares nothing and re-ticks (`RESOLVING`); a chain truncated by an unread layer would publish a lower rewrite and strand the layers above it.
- A boundary that resolves onto the chain base means the invariant was already broken below; the whole cascade is refused before any push. A rebase conflict during prepare aborts that layer, removes the worktree, writes no record, and reports `BLOCKED` naming the files; land never hand-resolves a conflict. A lease failure during publish keeps the record and reports `RESOLVING`.
- The recorded old tips are reachable only through this clone's objects after a force-push; a record whose objects are missing (another clone) is `NEEDS_HUMAN`. Land already runs from one clone per ledger.
- The merged parent branch must still exist for the first boundary (the janitor guarantees it while a child targets it); when a human deleted it, the first layer's `verdict_base` (GitHub's `base.sha` at the last satisfied tick) is the boundary, or the cascade is `NEEDS_HUMAN`.
- This is the only force-push land performs: the open layers of a chain it babysits, each with a lease on the exact tip it read, inside the tick claim, after the layer below merged. Every other step keeps the no-force-push rule, and `SKILL.md`'s Forbidden list says so.
- After publication, each layer's next gate evaluation computes its patch-id against its new base (§2.2b); an unchanged patch keeps the review verdict, and CI re-runs because the base changed.

## Stacks: what GitHub does for you, and what land still checks

After the frontier merges via `merge-async`, GitHub retargets the layer above to the stack's base and rewrites its head (both events attributed to the account that submitted the merge, never a bot; `land_pushed_sha` is written only by land's own pushes, so §2.7 never mistakes GitHub's rewrite for a land push). The rewritten layer's patch-id is unchanged (verified 2026-09-13), so the review verdict carries; CI re-runs. A human who merges the frontier from the stack UI between ticks needs nothing from land beyond the next re-read. A human who unstacks the chain flips it to the plain path on the next tick with no ledger migration. A stack read that is not a clean 404 degrades to the plain-path classification for that tick with one stderr line; a 404 on a PR whose payload still carries a `stack` object is `NEEDS_HUMAN`.

## Troubleshooting pointers

`chain broken; parent #<n> closed unmerged`, `retarget of #<n> ... conflicts in <files>`, and `merge-async still pending` are described in [`docs/troubleshooting.md`](../../../docs/flow-next/troubleshooting.md).
