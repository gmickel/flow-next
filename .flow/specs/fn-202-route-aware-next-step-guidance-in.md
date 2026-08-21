# Route-aware next-step guidance in capture and plan closers

## Goal & Context

Field request (flow-next company call, 2026-08-21): the pipeline-variations doc explains which stages a change actually needs (selector: risk + remaining unknowns, never size) — but it's documentation, and documentation doesn't fire at the decision point. Both closers already print a static next-step menu; the ask is one line of applied judgment above it.

At capture-close and plan-close the host agent has maximal context: it just synthesized the spec (knows which decisions stayed open, how contract-heavy the criteria are, the blast radius) or just decomposed it (knows task sizes, design risk, wave shape). Applying the smallest-sufficient rule there costs one sentence and zero dispatches — and the biggest wall-clock saving in the pipeline is a ceremony stage that never runs because the user was told, at the right moment, that it converts no unknown and bounds no risk.

Lesson this operationalizes (SCB program + Touches enforcement, both 2026-08): described behavior never fires; prose at the decision point does.

## Requirements

- R1: **Capture closer recommendation.** Capture's Phase 6 footer (workflow.md §Phase 6, the `Next:` block) gains ONE recommendation line printed above the existing menu: the host judges the just-written spec's risk and remaining unknowns per the smallest-sufficient rule in `docs/pipeline-variations.md` and prints `Recommended next: /flow-next:<stage> <id> — <one-clause reason>; <named alternative when it applies>`. The static menu stays verbatim below it. Judgment inputs the prose names explicitly: open `[inferred]` criteria and Parked unknowns (→ interview), resolved decisions + real design risk (→ plan), near-zero risk fully-known change (→ plan, noting work may be enough). Existing conditional footers (R25 biz-suggestion, memory-hits) unchanged and un-reordered.
- R2: **Plan closer recommendation.** Plan's Step 8 summary (and its interactive `references/next-steps-menu.md`) gains the same one-line shape for the plan-review-vs-straight-to-work decision. Guardrail stated in the prose: recommend skipping plan-review ONLY for the clearly-ceremony shapes the variants doc names (docs/chore-class, small-task-class with no design risk); any remaining design risk → plan-review recommended (it is the cheapest measured catch in the pipeline). The `AUTONOMOUS=1` branch is untouched — no recommendation line there.
- R3: **Single rubric home.** Neither closer copies routing rubric text. Each carries only the instruction to judge plus a link to `docs/pipeline-variations.md` (and may name `/flow-next:guide` as the deeper router on genuine ambiguity). The selector is risk + unknowns — the prose must not introduce size-based routing.
- R4: **Advisory phrasing, menu preserved.** The line is a recommendation with a reason and (where sensible) a named alternative — never a bare directive, never a gate, never a blocking question. Menu-not-a-rail doctrine intact; no config key, no persisted route/classification, no pilot/work/land changes.
- R5: **Cross-harness sync.** `./scripts/sync-codex.sh` run twice, mirror diff committed; verify the touched closer sections are NOT inside any hardcoded sync heredoc (SECTION3C-class check — grep sync-codex.sh for replacement blocks covering capture workflow.md / plan steps.md / next-steps-menu.md before assuming transform-through). New prose introduces no Claude-builtin references, so Cursor/Droid/Grok/OpenCode consume it as-is (checklist item 2); OpenCode needs nothing (skills blanket-scatter; no agent/frontmatter changes).
- R6: **Conduct checklists.** `agent_docs/conduct/` entries for capture and plan gain one falsifiable item each (closer printed exactly one recommendation line with reason + alternative above the unchanged menu; no rubric text copied into the closer). Dogfood each edited skill once, mark items pass/fail before handoff.
- R7: **Docs.** `docs/pipeline-variations.md` gains one line noting the capture/plan closers apply its rule (cross-link both ways per the big-picture sweep rule). CHANGELOG `## Unreleased` entry, user-outcome-first. No version bump (batched release rule).

## Decision Context

- Interview's closer is OUT of v1 scope: interview already ends by routing back to plan, and its refine loop makes a route recommendation redundant. Revisit on field demand.
- Plan-review is deliberately protected: 2026-08 eval data shows it catching interpretation bugs at 4.2 min — the skip recommendation fires only on variants-doc ceremony shapes, not on general low confidence.
- No spec-frontmatter persistence of the assessed route: that would be conditional machinery for autonomous paths, ruled out (standing no-knobs decision). Interactive advisory only.
- Prose-only change → plan-review skipped for this spec per maintainer call (the change is itself the docs-tier shape).

## Boundaries

- IS: two closer prose additions, conduct rows, one docs cross-link, mirror sync, CHANGELOG.
- IS-NOT: new skill, config keys, pilot/autonomous behavior, deterministic classifier, rubric duplication, guide-skill changes, interview changes.

## Quick commands

- `cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned test_skill_prose_diet -q` (focused; full gate once at the end: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`)

## Gap resolutions (plan round, 2026-08-21)

- **Rewrite-mode footer: IN scope.** `references/rewrite-mode.md`'s own `Next:` block gets the same single recommendation line — a rewritten spec is precisely when the route may change.
- **Split-proposal: per-spec recommendations.** Each created spec gets its own line in its own footer block (each spec is its own route); the existing shared dependency-edge line owns execution order. One sentence added there stating exactly that; no reconciliation logic.
- **chart is an EXCLUDED recommendation target.** pipeline-variations places chart/prospect upstream of capture; recommending chart from a capture closer would contradict the doc being applied. Legal targets: `/flow-next:interview`, `/flow-next:plan` (optionally noting a minimal single-task plan fits the near-zero-risk shape — capture creates only the spec, so a task must exist before `work` can run), and `/flow-next:guide` on genuine ambiguity.
- **Readiness is an explicit judgment input** alongside open `[inferred]` criteria and Parked unknowns: a spec left not-ready or `[inferred]`-heavy leans interview; the recommendation must never read as a readiness claim.
- **The line is MANDATORY — no silent omission.** When signals genuinely conflict, the recommendation IS `/flow-next:guide` with a "signals conflict" reason. Keeps the conduct row falsifiable (exactly one line, every run).
- **Plan menu re-print loop:** re-judge at each menu print — a go-deeper/simplify round can change the risk picture, and the judgment costs one sentence. Stale advice is worse than none.
- **Plan-review-skip guardrail is itself falsifiable:** a skip recommendation must name one of the two ceremony shapes (docs/chore-class, small-task-no-design-risk); any other skip recommendation is a conduct failure.
- **R5 scope widened:** the sync-codex transform-through grep also covers `rewrite-mode.md` and `split-proposal.md`.
- **Conduct dogfood names its variant** (base capture path; interactive plan menu).
