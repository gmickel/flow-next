---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R10]
---
# fn-147-source-tags-in-interview-provenance-for.1 Emit source tags from interview write-back + drift-pin test

## Description
Teach `/flow-next:interview` to emit source tags on the acceptance criteria it writes, plus the drift-pin test. Prose at the emission sites, one Python test, sync. No parser change, no new vocabulary, no cross-model review (established pattern: capture already does this).

**Size:** S

**Files:**
- `plugins/flow-next/skills/flow-next-interview/references/write-back.md` (NEW IDEA branch, EXISTING SPEC branch, merged-body contract)
- `plugins/flow-next/skills/flow-next-interview/SKILL.md` (one pointer line at the acceptance-criteria authoring guidance)
- `plugins/flow-next/tests/test_readback_ask_contract.py` or a sibling test file (drift pin)
- `plugins/flow-next/codex/` (regenerated, not hand-edited)

### Approach

- Copy capture's SHORT tag guidance to each interview emission site. Do NOT relocate or centralise capture's tables: fn-84.2 tried exactly that DRY move, regressed a fixture 15->14, and was reverted. Proximity is load-bearing; repeat the short imperative at the action site.
- Rules the prose must carry at the emission site: tag only criteria this pass newly writes; never add/change/remove a tag on an existing bullet (provenance is frozen like the R-ID number); untagged legacy criteria stay untagged; trailing-token format `[user]` / `[paraphrase]` / `[inferred]` / `[strategy:<track>]`.
- Per-pass semantics (settle in prose, R7): `[user]` = the human in THIS pass (PO under business, tech lead under technical). No new pass-dimension grammar.
- No-self-blessing (R6): decide with the evidence in front of you and record the rationale in the spec's Decision Context. Default lean: adopt capture's rule only for `[inferred]` criteria the interview did NOT ask a question about; criteria resolved by an actual answered question are already verified by construction.
- Drift pin: a test asserting interview's and capture's tag vocabulary/definitions match (string-level assertions on both skill trees), so neither can drift without failing CI.
- Discrimination check (R5): author one frozen mini-transcript fixture where some criteria are quoted answers and some are agent gap-fills; run the emission once and eyeball that tags separate. This is a manual verification recorded in evidence, not a new CI harness.
- `./scripts/sync-codex.sh` twice; guards green.

### Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-capture/workflow.md` (tag guidance to mirror, wording source)
- `plugins/flow-next/skills/flow-next-interview/references/write-back.md`
- `plugins/flow-next/tests/test_readback_ask_contract.py:142` (existing capture pin, pattern to follow)
- `plugins/flow-next/scripts/flowctl.py` `_export_parse_acceptance_criteria` (read-only: confirm format)

**Optional:**
- `agent_docs/optimizing-skills.md` (fn-84.2 proximity lesson; fn-84.3 interview regression history)

### Key context

Interview is accuracy-critical with a history of regressing on "obviously safe" prose edits. Keep additions short, at the emission sites, and do not touch question flow: tagging is a property of how a criterion is written down, never an extra question. Prompt weight must not grow materially (R8).

## Acceptance
- [ ] Interview emits a trailing source tag on every acceptance criterion it newly writes, in all three write-back branches (NEW IDEA, EXISTING SPEC, merged body)
- [ ] Prose forbids retagging existing criteria; untagged legacy bullets stay untagged
- [ ] Per-pass `[user]` semantics stated where the tags are emitted
- [ ] No-self-blessing decision recorded in fn-147 Decision Context and implemented or explicitly declined
- [ ] Drift-pin test asserts capture and interview tag definitions match; fails if either changes alone
- [ ] Frozen-fixture emission shows mixed tags (not uniform [inferred]); evidence recorded
- [ ] Tally recipe (grep over `flowctl cat`) returns non-empty mixed-tag output on the fixture spec
- [ ] sync-codex.sh run twice, idempotent, guards green; focused tests green


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
