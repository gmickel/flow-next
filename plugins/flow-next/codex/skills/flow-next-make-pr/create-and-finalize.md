# Create and finalize

Real create/update only. With several specs, set `PR_TITLE` to a combined-change title of at most 72 characters; otherwise use the spec title verbatim up to 72 characters, or the first goal/context sentence up to 70 plus ellipsis, or spec ID if empty.
Use rendered `BODY_FILE` unchanged, with any enabled lens line appended. Require
nonempty content; above 65,000 characters stop with the retained file, never
truncate. Clean temporary files on exit.

Set `OPEN_ITEMS_COUNT` from spec open questions, `deferred_findings`, completion
review `needs_work`, incomplete tasks and other unfinished authored items; QA
findings remain advisory. Restore `CHAIN_PARENT`, `PARENT_PR`, `PARENT_PR_STATE`
from `PHASE0_CONTEXT`. Immediately before push check the aid artifact's head
against HEAD; mismatch uses the labeled fallback, never stale fields.

```bash
source "$(dirname "$FLOWCTL")/make-pr-create.sh"
```

The script owns the draft matrix, closed-head check, push, create/update retries,
tracker linkage and optional stack link. It retains `PR_URL`, `DRAFT_FLAG` and
`STACK_LINE` for finalize. Exit 1 stops finalization. `FLOW_PR_CREATE_CMD` defaults
to `gh pr create`: whitespace-split, no eval; successful output must contain a PR
URL. The 3-attempt retry loop retries eventual-consistency failures only.
After an exhausted create retry, wait 30 seconds and re-run $flow-next-make-pr (skill detects the existing branch and re-tries).

## Finalize
After successful creation or update, optionally write a grounded `knowledge/architecture-patterns` memory
entry under `--memory`, with tag `spec-<SPEC_ID>` as its idempotency key; skip if that tag already exists.
Its prose follows [docs/prose.md](../../docs/flow-next/prose.md) when present. Memory failure is non-fatal; never write by default or in dry-run.

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
that start. Never loop. Print the PR URL, `Reviewer feedback → $flow-next-resolve-pr <number>` and
`Body inspection → $flow-next-make-pr <spec-id> --dry-run` in native host invocation syntax (OpenCode
hyphenates the command). Under Ralph stdout is solely `PR_URL=<url>`, all other output goes to stderr. The last summary line (stderr under Ralph) is: `Tracker sync: <OK |
MISSING:makePr → retro-fired → OK | MISSING:makePr (retro-fire failed: <reason>) | n/a (bridge inactive)>`.
