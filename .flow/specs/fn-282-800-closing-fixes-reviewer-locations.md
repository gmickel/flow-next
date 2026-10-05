# 8.0.0 closing fixes: reviewer locations, set-backend errors, retiring a spec, criteria and stall docs

## Goal & Context

Small fixes the maintainer chose to land on the 8.0 branch before its pull request, found while building fn-280 and fn-281 or reported on GitHub. [paraphrase] Each is deterministic (parser, CLI text, close semantics, docs), so they are proven by tests, not fn-271 draws. [paraphrase]

1. A reviewer finding whose location carries a trailing note (`store.py:18-25 (with ...)`) fails the findings parser, and the coordinator's merge plan then refuses that round until the merged file is supplied by hand. It can happen on any backend. [paraphrase]
2. `flowctl spec set-backend` errors print `<function field at 0x...>` instead of the flag name. [paraphrase]
3. GitHub #503 (reported by @sn-furali): a spec that is superseded, moot or delivered elsewhere has no truthful way to close. `done` is the only state, its never-run tasks must read `done`, no completion-review value fits, and land counts a retired task-less spec as no work. Closing fn-196 as superseded by fn-281 on 2026-10-05 hit exactly this. [paraphrase]
4. This repository's standing criteria (`.flow/criteria.md`): drop G3 (narrow, covered by STRATEGY.md "The owner holds the license", judged not-applicable on almost every review) and correct the header, which says criteria are judged only by completion review; since fn-281 R6 a single-task spec's implementation review judges them too. [paraphrase]
5. The `.flow/memory` decision record for the stall check (fn-168) still describes the old rule; fn-281 R7 changed it to three consecutive `not-fixed` rounds that never refuse an unreviewed committed fix. [paraphrase]

<!-- Source: 40% user / 50% [paraphrase] / 10% [inferred] -->

## Acceptance Criteria

- **R1:** A finding location with trailing text after the path and line or range parses to that path and line or range on every backend, and a round containing one no longer makes the merge plan refuse. Errors: a location with no parseable path and line still parses as no anchor, as today. [paraphrase]
- **R2:** Every `spec set-backend` error names the flag or value the user typed, never a Python object representation. Errors: no error surface beyond today's. [paraphrase]
- **R3:** `flowctl spec close <id> --retire <superseded|moot|delivered-elsewhere> [--by <spec-or-PR>...]` closes a spec as retired: the reason and successors are recorded on the spec, never-run tasks are settled without being recorded as implemented, completion review records an excusal that is not `ship` and that every close and merge gate accepts, `flowctl next` stops routing to the spec and its tasks, and land counts a retired task-less spec as closed. An ordinary close behaves as today. Errors: an unknown reason is refused with the accepted list; `--by` without `--retire` is refused; retiring an already-closed spec is refused. [paraphrase]
- **R4:** Retired specs read truthfully wherever a spec's end state is shown (show/list output, the PR briefing, tracker projection keeps today's surfaced-not-applied behaviour for cancels). Errors: no error surface. [inferred]
- **R5:** The skill text that tells the agent how to close a spec as won't-do uses `--retire` with the matching reason, on every harness (Codex mirror regenerated). Errors: no error surface. [paraphrase]
- **R6:** `.flow/criteria.md` no longer contains G3 (IDs are never renumbered; G3 is removed, not reassigned) and its header says criteria are judged by completion review and, for a single-task spec, by its implementation review. Errors: no error surface. [paraphrase]
- **R7:** The fn-168 stall decision record in `.flow/memory` states the current rule (three consecutive `not-fixed` rounds; an unreviewed committed fix is never refused). Errors: no error surface. [paraphrase]
- **R8:** The CHANGELOG Unreleased entry lists these fixes and credits @sn-furali for #503; flowctl help text is regenerated; full suite, smoke, mirror, anchor and help checks pass. Errors: no error surface. [paraphrase]

## Boundaries

- No opt-in tracker mapping of retired specs to a cancelled or duplicate state (#503's optional item); the projection keeps surfacing cancels rather than applying them. [paraphrase]
- No completion-review precondition at close (#477) in this spec. [paraphrase]
- No new task cancel or skip command beyond what `--retire` needs to settle never-run tasks. [inferred]
- No fn-271 draws; prompt and skill behaviour on the build route is unchanged apart from R5's close wording. [paraphrase]

## Decision Context

- **Maintainer, 2026-10-05:** "yes you should and the global acc criteria fixes, all of the things you recommend, no draws needed". [paraphrase]
- Reviews focus on overengineering, slop and YAGNI: #503 is delivered in its smallest truthful form, and anything the flag makes unnecessary is deleted. [paraphrase]

## Strategy Alignment

- Serves "Agent first": a truthful close record written after acting, no new form before acting. [inferred]
