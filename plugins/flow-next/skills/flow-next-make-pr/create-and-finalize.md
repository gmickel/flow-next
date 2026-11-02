# Create and finalize

Real create/update only. With several specs, set `PR_TITLE` to a combined-change title of at most 72 characters; otherwise use the spec title verbatim up to 72 characters, or the first goal/context sentence up to 70 plus ellipsis, or spec ID if empty.
Use rendered `BODY_FILE` unchanged. Require
nonempty content; above 65,000 characters stop with the retained file, never
truncate. Clean temporary files on exit.

Set `OPEN_ITEMS_COUNT` from spec open questions, a pending completion review (`completion_review_pending`),
incomplete tasks, open findings on a `NEEDS_WORK` or `BLOCKED` QA receipt, a call
the run left for the person (working-rules.md, Unattended) and other unfinished
authored items. Otherwise the PR opens ready: `deferred_findings` and follow-ups
are listed in the body, not a reason to draft. Restore `CHAIN_PARENT`, `PARENT_PR`, `PARENT_PR_STATE`
from `PHASE0_CONTEXT`. Immediately before push check the aid artifact's head
against HEAD; mismatch uses the labeled fallback, never stale fields.

```bash
source "$(dirname "$FLOWCTL")/make-pr-create.sh"
```

The script owns the draft matrix, closed-head check, push, create/update retries,
tracker linkage and optional stack link. It retains `PR_URL`, `DRAFT_FLAG` and
`STACK_LINE` for finalize. Exit 1 stops finalization. `FLOW_PR_CREATE_CMD` defaults
to `gh pr create` and runs through `sh -c`, so it may carry its own arguments; successful output must contain a PR
URL (`.../pull/<n>`, or Bitbucket's `.../pull-requests/<n>`). The 3-attempt retry loop retries eventual-consistency failures only.
After an exhausted create retry, wait 30 seconds and re-run /flow-next:make-pr (skill detects the existing branch and re-tries).

## Finalize
Only under `--memory`: read [memory-entry.md](memory-entry.md) after a successful creation or update.

Run `"$FLOWCTL" sync active --json`. Only when it reads `active: false`: skip the tracker step;
the slot reads `n/a (bridge inactive)`. Otherwise, including an error: read
[tracker-finalize.md](tracker-finalize.md) and run it.

Print the PR URL, `Reviewer feedback → /flow-next:resolve-pr <number>` and
`Body inspection → /flow-next:make-pr <spec-id> --dry-run` in native host invocation syntax (OpenCode
hyphenates the command). The last summary line is: `Tracker sync: <OK |
MISSING:makePr → retro-fired → OK | MISSING:makePr (retro-fire failed: <reason>) | n/a (bridge inactive)>`.
