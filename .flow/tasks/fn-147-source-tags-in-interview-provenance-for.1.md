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
`/flow-next:interview` now emits source tags on the acceptance criteria it writes, closing the gap where every tag-based affordance (the grounded-vs-guessed tally, targeted re-interview of `[inferred]` items) only worked for capture-authored specs.

Prose at the three write-back emission sites plus a clause on each per-pass acceptance bullet in SKILL.md, carrying the four hard rules: tag only what this pass authors, never retag another pass's criterion, untagged legacy stays untagged (and untagged means unknown provenance, never `[user]`), uniform tagging is a failure. Per-pass semantics stated: `[user]` is the PO under a business pass, the tech lead under a technical pass.

Capture's tables were not touched, moved, or centralised - fn-84.2 proved relocating that guidance regresses accuracy, so the definitions are repeated at the emission sites and drift is prevented by a test instead.

Drift pin (`test_interview_source_tags.py`): tag tokens are extracted from each file's source-tag table and asserted as set-equality against the vocabulary, so a rename, a drop, or an ADDITION on either side fails CI. Extraction is anchored to the `| Tag | Meaning |` header because capture/phases.md carries a second table of confidence markers that would otherwise contaminate the set. The shared definitions and the read-back tally shape are pinned too.

R6 decision recorded in the spec: interview inherits capture's no-self-blessing rule, narrowed to `[inferred]` criteria no question covered - a blanket rule would fire on nearly every interview run and train users to ignore it.

Three review rounds (host backend, fable-5 @ medium, fresh reviewer each round). Round 2 found the drift pin was one-sided on tag vocabulary; round 3 found the docstring overstated coverage because a presence-only assertion cannot catch additions. Both were real defects in my own work and were fixed at the substance rather than the wording.

Known follow-up for task .2: the tally recipe published in 3.7.0 uses `\[[a-z:]+\]`, which silently drops every `[strategy:*]` criterion (live specs contain `[strategy:Cross-platform parity]` and similar with uppercase, spaces and hyphens). Docs bug, not an emission bug.
## Evidence
- Commits: c2136bb5dc2e998faeaa02d129912d55110673dc, 207e4b7705545e651c4354d96ac9ada4009c7f78, 52a715a1719913c9753d23cd14d54ea6c7911974
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_interview_source_tags -q  (12 tests OK), cd plugins/flow-next/tests && python3 -m unittest test_interview_source_tags test_prompt_text_pinned test_readback_ask_contract -q  (27+ tests OK), python3 scripts/run_tests_parallel.py  (files=156 ran=3298 failures=0 errors=0 skipped=4), uvx ruff@0.16.0 check .  (All checks passed), ./scripts/sync-codex.sh run twice - idempotent, guards green, zero mirror drift, R4 tally recipe over tests/fixtures/interview_source_tags/emitted-criteria.md -> user 2 (R1 R3) / paraphrase 1 (R2) / inferred 2 (R4 R5) / strategy:Self-serve 1 (R6) - non-empty and mixed, 4 distinct tags over 6 criteria, R5 discrimination: frozen transcript (3 answered questions, 1 skip, 2 never-asked, 1 strategy track) emits 4 distinct tags, not collapsed to [inferred]; enforced by test_frozen_fixture_shows_mixed_tags, R8 prompt weight vs base 8c881bff: interview SKILL.md 49816 -> 50337 chars (+521, +1.0%, always-loaded); write-back.md 16426 -> 19933 chars (+3507, +21.4%, loaded only at completion), Drift-pin efficacy proven by in-memory simulation (capture files never modified): capture adds a 5th tag FAILS (previously green), capture renames [user] FAILS, capture drops [paraphrase] FAILS, tally middot->slash FAILS, Review: host backend, fable-5 @ medium, 3 rounds - round 1 NEEDS_WORK, round 2 NEEDS_WORK (1 Major + 5 actionable Minors + 1 refuted), round 3 SHIP with 2 non-blocking findings, both taken
- PRs: