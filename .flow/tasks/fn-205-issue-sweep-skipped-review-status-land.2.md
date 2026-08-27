---
satisfies: [R1, R5]
---
# fn-205-issue-sweep-skipped-review-status-land.2 Work skill: 3g skip persists the excused member; drop --review=export from the roster

## Description
Two edits in the same skill family, combined because they touch the same two files (R1 and R5). 3g's policy skip starts persisting `not_required` instead of leaving `unknown`, and `--review=export` leaves the accepted impl-review roster. Depends on the plumbing task: prose that writes a token argparse rejects turns a silent no-op into a hard parser failure.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-work/phases.md`, `plugins/flow-next/skills/flow-next-work/SKILL.md`, `plugins/flow-next/skills/flow-next-work/references/setup-questions.md`, `plugins/flow-next/commands/work.md`, `plugins/flow-next/skills/flow-next-impl-review/SKILL.md`
**Touches:** [plugins/flow-next/skills/flow-next-work/phases.md, plugins/flow-next/skills/flow-next-work/SKILL.md, plugins/flow-next/skills/flow-next-work/references/setup-questions.md, plugins/flow-next/commands/work.md, plugins/flow-next/skills/flow-next-impl-review/SKILL.md]

### Approach
- R1, primary site: `phases.md:379-399`. Lines 398-399 currently say explicitly not to write the status and to leave it `unknown`. Replace that instruction (do not append a caveat — G1) with the write, gated on the current value being `unknown` so a spec already carrying `needs_work` / `needs_human` is never upgraded to satisfied. Keep the run-scoped stage line at `:395` (`completion-review - skipped(policy: ...)`) verbatim — the word `skipped` is correct for a stage outcome; only the persisted member is renamed.
- R1, second site: the same policy is restated at `SKILL.md:141` and in the Done-when at `phases.md:456`. All restatements move together or the skill contradicts itself.
- R5: delete the export line at `SKILL.md:109` and remove `export` from the tip at `references/setup-questions.md:21`. The roster must agree with the review-mode enum work already hands to workers at `phases.md:237` (`REVIEW_MODE: none|rp|codex|copilot|cursor|host-deferred`), which never contained `export` — that enum is the truth the advertised roster was drifting from. Note SKILL.md's own routing sentence at `:112-113` already omits export, so `:109` contradicts its own block.
- R5, missed surface (verified 2026-08-27): `plugins/flow-next/commands/work.md:4` argument-hint reads `[--review=rp|export|none]` — drop `export` there too; it is the first thing a user sees.
- R5, the other mouth: impl-review's own parser accepts export with no workflow behind it. Remove `export` from `flow-next-impl-review/SKILL.md:37` (priority list) and delete the parse line at `:50` (`--review=export ... → use export`), failing closed with the same not-a-backend message naming `/flow-next:plan-review --review=export`. Keep `:32`'s "export is a MODE, not a configured backend" sentence only if it still reads true after the drop — rewrite it to point at plan-review if not (G1: replace, don't append). No test pins these lines (the prose-diet pin at `test_skill_prose_diet.py:307-315` is plan-review's) — but do NOT touch any `flow-next-plan-review/` file; those ARE pinned.
- R5 fail-closed: an explicit `--review=export` is rejected at option-parse time, before any dispatch, with a message that export is not an impl-review backend and naming the manual path (`/flow-next:plan-review --review=export` is where export legitimately lives). Never remap it to another backend, and never let it reach the impl-review dispatch.
- work-rolling needs no edit: it consumes work's option parsing by pointer (`flow-next-work-rolling/SKILL.md:9,37,51`) and has no literal `export`. Confirm by grep rather than editing, and record the pointer relation in the task summary — R5's work-rolling half is satisfied by inheritance.
- Do NOT run `./scripts/sync-codex.sh` (finalization owns the single regen). If any edit lands inside `phases.md` section 3c, flag it — that section is a hardcoded heredoc in the sync script and would need the same edit there.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/skills/flow-next-work/phases.md:379-399` — the 3g skip branch and its explicit do-not-write instruction
- `plugins/flow-next/skills/flow-next-work/phases.md:220-240` — review-mode resolution and the worker handoff enum at `:237`
- `plugins/flow-next/skills/flow-next-work/SKILL.md:104-113` — the advertised roster and the sentence that routes every non-`none` mode into impl-review
- `plugins/flow-next/skills/flow-next-work/SKILL.md:141` — the second statement of the skip policy

**Optional** (reference as needed):
- `plugins/flow-next/skills/flow-next-plan-review/workflow.md:32,50-53` — where export legitimately terminates, for the rejection message's manual-path pointer

### Acceptance
- [ ] 3g writes `not_required` through the CLI when it skips, and only when the current value is `unknown` (R1)
- [ ] The `unknown`-on-skip instruction is gone from `phases.md:398-399`, `phases.md:456` and `SKILL.md:141` — replaced, not supplemented (G1)
- [ ] The 3g stage line still reads `skipped(policy: ...)` — run-scoped wording unchanged
- [ ] `--review=export` no longer appears as an accepted work review mode in `SKILL.md`, `references/setup-questions.md`, or the `commands/work.md` argument-hint (R5)
- [ ] An explicit export request fails closed at parse time with a message naming it as not-an-impl-review-backend plus the manual path; nothing dispatches (R5)
- [ ] The advertised roster matches `phases.md:237`'s worker enum exactly
- [ ] work-rolling verified export-free by pointer, with no restated roster added to it
- [ ] impl-review's accepted modes no longer include `export`; an explicit `--review=export` to impl-review fails closed naming the plan-review manual path; `flow-next-plan-review/` files untouched
- [ ] `cd plugins/flow-next/tests && python3 -m unittest test_skill_prose_diet test_backend_spec -q` green

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
