# Refine — post-write-back offers

Read the one section the sentinel named.

- [Tracker sync](#tracker-sync) — project the refined spec to its linked tracker issue.
- [Mark-ready offer](#mark-ready-offer) — optional readiness prompt, spec inputs only.

## Tracker sync

Runs after the write-back when the tracker bridge is active and `tracker.perEvent.interview` (the key keeps its old name) is set to anything but `off`. Refinements made in flow go to the tracker, and tracker-side edits fold into the right spec sections. Re-read the setting once and map it to the operation:

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
LEAF="$("$FLOWCTL" config get tracker.perEvent.interview --json | jq -r '.value')"
case "$LEAF" in
  pull|push|reconcile|comment) OP="$LEAF" ;;
  *) OP="off" ;;   # off, null, or malformed: stay silent
esac
if [ "$OP" != "off" ]; then
  # Invoke the inline flow-next-tracker-sync wrapper. It prepares the approved
  # operation-specific 0600 input files, then makes one lifecycle call, chosen
  # as its steps.md section 4 says: for pull or reconcile, --prepare first; a
  # reconcile classified flow-only with no genuine comments is a push with no
  # body inputs,
  #   "$FLOWCTL" tracker sync "$SPEC_ID" --op push --event interview
  # and every other case is
  #   "$FLOWCTL" tracker sync "$SPEC_ID" --op "$OP" --event interview <legal file flags>
  # For OP=comment, write the comment yourself: a compact summary of the refined
  # spec and the decisions settled in this session. The 0600 --body-file's first
  # line is `evidence=<sha256-of-current-spec-file>`; delete the file after the
  # call. No content travels in argv.
  # Unlinked specs are created and linked inside the facade. With no reachable
  # transport this is best-effort; a tracker failure never blocks the write-back.
  :
fi
```

## Mark-ready offer

Only for a spec input; tasks and files carry no spec readiness. Runs after the write-back and any tracker sync. Skip it when `/flow-next:flow` dispatched this refine in the current run: flow's route decides the next step.

The gate fails open to this file, so check both conditions before asking:

- At least one spec in the repo is already ready (`$FLOWCTL specs --json`). Repos that have not adopted readiness never see this question; the first adoption comes from `flowctl spec ready`, the tracker setup, or prime, never from this prompt.
- `tracker.readyState` is not configured. When the tracker owns readiness, a local mark would be reverted by the next sync, so do not offer one.

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

When both hold, ask once with `plain-text numbered prompt`:

- **header:** `Mark ready?`
- **body:** `Mark <spec-id> ready for execution? Readiness is adopted in this repo (<N> ready spec(s)). Recommended: keep-draft — re-read the refined spec on disk first; readiness is the person's gate, not a refine reflex. Confidence: [judgment-call].`
- **options:** `mark-ready` (run `$FLOWCTL spec ready <spec-id> --json`; idempotent), `keep-draft` (the default; no write).

A failed `spec ready` prints a warning and continues; it never blocks the write-back.
