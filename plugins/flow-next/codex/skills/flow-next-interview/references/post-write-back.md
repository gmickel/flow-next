# Interview — post-write-back options (loaded when a gate sentinel prints)

> Read the ONE section the sentinel named. With no tracker configured and readiness unadopted, neither
> gate fires and this file is never read.

Contents:

- [Tracker sync](#tracker-sync) — spec push/pull + merge to the linked tracker issue (opt-in).
- [Mark-ready offer](#mark-ready-offer) — optional readiness prompt, flow spec inputs only.

## Tracker sync

**Optional. Runs only when the tracker bridge is active AND `interview` is opted in. With no tracker configured this is a no-op — the interview behaves exactly as today.** After the refined spec is written back (`## Write Refined Spec`), project the enrichment to the linked tracker issue and reconcile two-way (R6): interview enrichment done in flow flows back to the tracker; tracker-side edits fold into the right flow sections. (Skip for the file-input case — there is no flow spec yet.)

`LEAF` was read by the gate probe in SKILL.md (shared gating predicate — work SKILL.md); bash variables do not survive across prompt turns, so re-read the leaf ONCE at the top of this block and map it to the operation:

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
LEAF="$("$FLOWCTL" config get tracker.perEvent.interview --json | jq -r '.value')" # read the leaf ONCE
case "$LEAF" in
 pull) OP="pull" ;;
 push) OP="push" ;;
 reconcile) OP="reconcile" ;;
 comment) OP="comment" ;;
 off|null) OP="off" ;;
 *) OP="off" ;; # malformed config stays silent
esac
if [ "$OP" != "off" ]; then
 # Invoke the inline flow-next-tracker-sync wrapper. It prepares the approved
 # operation-specific 0600 input files, then makes exactly one lifecycle call:
 # "$FLOWCTL" tracker sync "$SPEC_ID" --op "$OP" --event interview <legal file flags>
 # For OP=comment, Interview synthesizes the comment content by name: a compact
 # refined-spec summary and the decisions resolved in this interview. The
 # 0600 --body-file FIRST line is
 # `evidence=<sha256-of-current-spec-file>`; delete the file after the call.
 # No content travels in argv.
 # Unlinked specs create and link inside the facade. No reachable transport is
 # best-effort; a tracker failure never blocks the interview write-back.
 :
fi
```

## Mark-ready offer

Applies ONLY when the input was a flow spec (Detect Input Type patterns 1/3) — task ids and file paths carry no spec readiness. Same consent shape and visibility predicate as capture's read-back follow-up (fn-58). Runs after the write-back and the tracker-sync block.

The gate probe in SKILL.md already computed `READY_STATE` and `READY_ADOPTED`. Both must hold (probe failures degrade to "don't offer" for the predicate itself; the gate fails open to reading this file, so re-check here before asking):

- `READY_ADOPTED -ge 1` — readiness is adopted in this repo (≥1 spec already marked ready); non-adopters see no question anywhere. First adoption enters via `flowctl spec ready`, the tracker ceremony, or prime — never via this prompt.
- `READY_STATE` empty — `tracker.readyState` NOT configured. Tracker-authoritative readiness is a one-way pull; never invite a local edit the next sync would silently revert.

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

When the predicate holds, ask once via `plain-text numbered prompt` (lead with recommendation):

- **header**: `Mark ready?`
- **body**: `Mark <spec-id> ready for execution? Readiness is adopted in this repo (<READY_ADOPTED> ready spec(s)). Recommended: keep-draft — re-read the refined spec on disk first; readiness is the human gate, not an interview reflex. Confidence: [judgment-call].`
- **options** (frozen): `mark-ready` (run `$FLOWCTL spec ready <spec-id> --json` — idempotent), `keep-draft` (default — no readiness write)

Best-effort: a failed `spec ready` prints a warning and continues — never blocks the interview write-back.
