---
satisfies: [R5]
---
# fn-169-review-subsystem-agentic-first-pass.5 Re-measure against the pre-registered gate; log the verdict

## Description
Run the fixture against the new behavior and hold the change to the gate written in `.2`.

**Size:** M
**Files:** `optimization/review-prompt/`, `agent_docs/optimization-log.md`

### Approach
- Re-run the `.2` fixture on the post-change code, codex + cursor, >=3 runs, and compare against the recorded baseline.
- Score every metric: `verdict_delivered`, `range_correct`, turns-to-verdict, scope precision, correctness/smell detection, over-flag on the clean corpus, resumed per-ordinal grammar compliance.
- Apply the gate as written, without renegotiation: any missed verdict or any decoy finding blocks the ship regardless of the token win. Wall-clock is recorded, not gated.
- Also run the narrow arm the evidence pointed at: a diff that fits ENTIRELY under the old 50 KB cap — the only case where removing the payload could add round-trips, since larger diffs already forced fetching.
- If an arm fails, record it and stop; `.4` narrows or reverts rather than the gate moving.
- Log kept AND discarded results in `agent_docs/optimization-log.md`, per the harness discipline.

### Investigation targets
**Required:**
- `.2`'s recorded baseline and pre-registered gate
- `agent_docs/optimization-log.md` — the entry format

### Key context
- Deps `.2` (baseline + gate) and `.4` (the change being measured).
- Expect MORE genuine findings now that reviewers see 100% instead of ~10% of the diff. That is correct behavior, not a regression — volume is tunable via the impl-review prompt and is deliberately a follow-up eval, not a gate here.
- Expect token cost down hard; speed up or flat. Do not report speed as a win unless the numbers show it.

## Acceptance
- [ ] Post-change measurement complete on codex + cursor, >=3 runs, all metrics scored
- [ ] The pre-registered gate is applied verbatim; the pass/fail decision and every number land in `agent_docs/optimization-log.md`
- [ ] The small-diff arm (fits under the old 50 KB cap) is measured explicitly
- [ ] Discarded/failed arms recorded, not dropped
- [ ] Prompt-token delta reported; wall-clock reported as an observation, not a claim
- [ ] If any gate item fails, the failure is recorded and `.4` is narrowed/reverted rather than the gate being adjusted

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
