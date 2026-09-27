---
satisfies: [R1, R2, R3, R4, R5, R6]
---
# fn-266-answer-questions-by-experiment-in.1 Implement Answer questions by experiment in refine and prototypes

## Description
Implement the whole spec in one task: refine's experiment-answerable category and `## Resolved via Experiment` record (taxonomy, SKILL.md rule, write-back, per-pass notes, template + SPEC.md override + pinning tests), flow's prototype reference (variants behind one switcher, prior art first for an open design space), repo docs, and the flow-next.dev pages in the separate site repo.

Review focus (maintainer steering): overengineering, slop and YAGNI. Prose over machinery; flag any added rule, section, or test that the spec's R-IDs do not require.
## Acceptance
Every R-ID in the parent spec's ## Acceptance Criteria is satisfied; judge this task against the spec's criteria directly.

## Done summary
Refine now treats experiment-answerable questions (behaviour, timing, layout, output, performance, eval separation) as a fourth taxonomy category: it runs a read-only or disposable experiment in `.flow/tmp/experiments/` and records the question, what ran, what was observed and the decision under a new `## Resolved via Experiment` auxiliary section; stateful, destructive or external experiments and inconclusive results go to the user with the data. Flow's prototype reference builds competing variants behind one labelled switcher, gathers prior art first when the design space is open, and keeps direction choice a preference call (`NEEDS_HUMAN` unattended).

- R1/R3: `questions-shared.md` taxonomy + refine `SKILL.md` Experiment-answerable rule (renamed from Empirically-answerable; conduct checklist `agent_docs/conduct/refine.md` follows).
- R2: section added to `templates/spec.md`, the `SPEC.md` override, the SKILL.md preserve rule, `write-back.md` templates and both pass references; pinned by `test_template_canonical.py`, `test_r22_invariant.py` (aux enumeration) and the re-pinned template hash in `test_prompt_text_pinned.py` (deliberate wording change).
- R4/R5: `flow-next-flow/references/prototype-before-ask.md` (no new reference file); autonomy rule extended to direction choice.
- R6: flow-next.dev worktree `/home/gordon/work/flow-next.dev-fn-266`, branch `fn-266-answer-questions-by-experiment-in`, commit `e6febe3` (refine, flow, explore-first, prototype-to-spec pages), local only, not pushed; astro build, link check and site tests green.
- Also: CHANGELOG Unreleased entry, `docs/skills.md` refine row, codex mirror regenerated.
- Plan's own "empirically answerable" probe rule (`flow-next-plan/steps.md`) left as is: outside this spec's refine/flow surface.

Baseline: green (full suite 5231 tests, ruff clean) pre-edit.
Review: codex fan-out, three draws gpt-6-astra, all SHIP with zero findings. The template hash re-pin landed after the review (mechanical pin update the review's sandbox could not run).

Tier: session - explicit override: implementer opus 5.5 (actual: claude-opus-5-5)

stage: impl-review - ran

stage: plan-sync - skipped(config: planSync.enabled != true)
## Evidence
- Commits: 04778368381c47f3413a1377b6b038d4800b4e7e, f02ca960b2f4b5a8d423069f41b54e38bb68ca27, 68a93f0c32f069219b003b9403a821ed90f40802
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh --check
- PRs: