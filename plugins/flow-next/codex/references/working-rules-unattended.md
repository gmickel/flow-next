# Working rules: unattended runs (gated reference)

> Read from [working-rules.md](working-rules.md) only when the run is unattended (`--auto`), or a
> person or project instruction asks to review until SHIP (§ Review loop).

## Unattended

- **Unattended** (`--auto`): nobody is waiting. Never ask; decide from evidence, and stop only
  for a call only a human can make or an irreversible action. A human call that does not block
  the rest of the work (refreshing a frozen fixture, a requirement only CI can prove) goes in the
  pull request as an open item, on a draft pull request; finish the rest instead of stopping.
  Under `--until=merge` you also hold the merge, so make such a call yourself when it is
  reversible, inside the spec and backed by evidence (updating a snapshot or golden file that your
  change legitimately altered), and record it in the Decisions list. A call that is not (irreversible, a product
  choice the spec does not settle, or one that makes merging unsafe) stops the run `NEEDS_HUMAN`
  before the merge.
  Fix a discovery only when it blocks the change you were asked for, as its own commit; list the rest as follow-ups
  in the final report. Keep a
  Decisions list in the final report and the pull request body: each default you chose, finding
  you declined and review you skipped, with the evidence behind it.

## Review loop

Unattended (`--auto`, with or without `--until=merge`), nobody is there to decide what is left, so
aim for the best result: fix, re-review the fixes, and repeat until SHIP, with flowctl's round cap
and stall check as the backstop (an `ESCALATE:` from either is a stop). A person or project instruction that asks for it ("review
until SHIP") loops the same way. In the loop, decline hardening, scope creep and problems that
existed before the change, one `Declined #<n>: <reason>` line each in the fix commit. If the
reviewer keeps only findings like that, all below Major, end the loop yourself: report the
override and list each disagreement, with both sides' reasons, in the Decisions list and the pull
request. Never end it over a finding that shows a stated requirement broken; fix that. The verdict
stays the reviewer's: the receipt keeps it, and you never write a SHIP. The loop's end (SHIP, or a
recorded override) gates the handoff and any merge.
