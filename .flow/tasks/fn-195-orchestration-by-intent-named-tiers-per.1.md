---
satisfies: [R1, R3, R4]
---
# fn-195-orchestration-by-intent-named-tiers-per.1 Write the routing contract: tier vocabulary, precedence, reach pages

## Description
Author the contract before deleting anything that contradicts it. Define the four tiers plus the unset default in exactly one place, write one short reach page per supported harness, and state the precedence line at every dispatch site. This task creates the target; later tasks remove what disagrees with it.

**Size:** M/L
**Files:** NEW single tier-vocabulary section (implementer names its home - the usage guide is the natural one, since it is read on demand); NEW one reach page per harness under the docs tree (six: the four first-class hosts, the community port, and a generic fallback); `plugins/flow-next/skills/flow-next-work/phases.md` and `agents/worker.md` (dispatch-site precedence line); `plugins/flow-next/skills/flow-next-plan/steps.md` (scout fan-out dispatch sites); `plugins/flow-next/docs/orchestration.md` (becomes the tier-guidance page)
**Touches:** [plugins/flow-next/docs/orchestration.md, plugins/flow-next/docs/glossary.md, plugins/flow-next/skills/flow-next-work/phases.md, plugins/flow-next/skills/flow-next-plan/steps.md, plugins/flow-next/agents/worker.md]

### Approach
- Tier names are exactly the four in the spec plus unset. They are a user-facing interface: choose the wording once, and do not invent synonyms in different files (the dictionary already bans synonym drift - add these terms to it).
- A reach page states, for that harness: which reach mechanisms exist (in-session, in-host subagent, shell out to another CLI), which do not, what the degradation is when one is missing, and the discover-then-invoke habit where the harness can list what it offers. Keep each page short - this is a reference, not a tutorial.
- The precedence line is one sentence at each dispatch site: explicit argument, then the project routing block, then the agent default, then the session model. Same wording everywhere; do not paraphrase per file.
- The worked example in the spec is a consumer's own phrasing - reuse it verbatim as the example rather than authoring a new one.
- Do NOT write concrete model identifiers anywhere in this task's output. Tier guidance describes kinds of work.
- Mirror regeneration is deferred to the final task; this one may leave the mirror stale.

### Investigation targets
**Required** (read before writing):
- `plugins/flow-next/docs/orchestration.md` - what the current routing story claims, so the replacement is a rewrite rather than an addition
- `plugins/flow-next/docs/platforms.md` - the existing per-host knowledge that reach pages inherit (including which host cannot select a subagent model)
- `plugins/flow-next/docs/glossary.md` and the repo dictionary - where the four terms get their canonical definitions

### Key context
- The mechanism already works in the field; this is documentation of behavior, not a design experiment. Nothing here needs a spike.

### Acceptance
- [ ] Four tier names plus unset defined in exactly one place, in user-facing English, added to the project dictionary
- [ ] One short reach page per supported harness: mechanisms, absences, degradation, discover-then-invoke
- [ ] Identical precedence sentence at every dispatch site that routes work
- [ ] Zero concrete model identifiers introduced by this task
- [ ] Focused suites green for the files touched

## Acceptance
- [ ] TBD

## Done summary
Wrote the routing contract: the four tier names (reviewer, implementer, fast scout, thinking scout) plus the unset default are now defined in exactly one place (`plugins/flow-next/docs/orchestration.md` § Tiers) with the routing-block grammar and the spec's worked example verbatim; one short reach page per supported harness lives under `plugins/flow-next/docs/reach/`; and the identical routing-precedence sentence now appears at every dispatch site that routes work (work/phases.md worker spawn + quality auditor, plan/steps.md scout fan-out + gap analyst, agents/worker.md review). Tier/Reach and the four tier names were added to the project dictionary with synonym bans; zero concrete model identifiers were introduced.

Notes for the conductor:
- Seven reach pages, not the six the task file parenthesized: R3 says one page per SUPPORTED harness, and Grok Build is first-class per docs/platforms.md. Pages: claude-code, codex, droid, cursor, grok-build, opencode, generic (+ README index).
- Contradicting legacy material in orchestration.md (role map, model tables, slugs) was deliberately left for task .3, per this task's "later tasks remove what disagrees with it". Only two collisions were resolved here: the stale precedence chain sentence, and the "Subagent tiers" heading/column (retitled "Agent defaults - the floor" so the word "tier" has one meaning).
- Mirror left stale on purpose (regen owned by .5). No .flow/**, no codex/**, no flow-next-setup/** touched.
- FLOWCTL BUG FOUND (not fixed - flowctl.py is out of this task's Touches): `flowctl glossary add` rewrites the whole GLOSSARY.md from its parse and corrupts an existing multi-entry file - it drops the file's intro prose above the first term, duplicates every `_Relates to_` line, and injects runs of blank lines (the parser folds the trailing `_Relates to_` line into the definition body, then re-emits it). Reproduced on this repo's root GLOSSARY.md; restored from HEAD and appended the six entries by hand instead. Worth its own bug/spec.

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
stage: delegation - skipped(config: delegation off)


Integrated onto spec branch as 3be3d785; review fixes 1f863fae + 4976cf11 (precedence coverage widened to 9 sites, glossary avoid-list trims, prime fan-out tier statement corrected, reach index links); stray-artifact cleanup 877d953d.

stage: impl-review - ran (host backend, fresh fable-5 reviewers; r1 NEEDS_WORK -> fixes -> r2 NEEDS_WORK -> fixes -> r3 SHIP)stage: plan-sync - ran (drift: yes; .3 gained R3 + workflow-host pin-table ownership, .5 dictionary item reworded to survival-check; cross-spec deferred to conductor)

## Evidence
- Commits: 3be3d785ecdb1fbda07efc27c716f019c3cd51a2, 1f863fae65d4296ce853251e75538779f28502da, 4976cf11df7ccf2e293f0ffa134981fcfb973efe
- Tests: python3 scripts/run_tests_parallel.py (192 files, 4407 tests, OK), cd plugins/flow-next/tests && python3 -m unittest test_cursor_host_docs test_chart_docs_inventory test_parallel_work_prose test_worker_anchor_prose test_skill_prose_diet test_review_findings_docs test_two_axis_audit_contract test_r22_invariant test_gate_classify test_prompt_text_pinned -q (142 tests, OK), uvx ruff@0.16.0 check . (All checks passed), integrated verify: python3 scripts/run_tests_parallel.py @4976cf11 (192 files, 4407 tests, 0F 0E) + uvx ruff@0.16.0 check . (clean), impl-review: host backend r1 NEEDS_WORK (2 P2 + 3 P3), r2 NEEDS_WORK (fix mislabeled prime tier + vocab leak), r3 SHIP (reviewer claude-fable-5, fresh subagents; receipt /tmp/impl-review-receipt-fn-195-orchestration-by-intent-named-tiers-per.1.json)
- PRs: