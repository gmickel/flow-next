## Conversation Evidence

> user (turn 1): "https://github.blog/changelog/2026-07-30-stacked-pull-requests-are-now-in-public-preview/ [...] research task. how does this help flow-next, and does it conflict with our new make-pr or does it improve it"
> user (turn 2): "capture it, probable 2 specs, then commit and push so we have the specs stored. other agents working here too, don't interfere with each other"

Research findings this capture rests on (agent research, 2026-07-31): GitHub stacked PRs (public preview 2026-07-30) let an ordered series of PRs each target the branch below; each layer's PR shows only that layer's diff and carries a stack map; stacks are created via the web UI or the gh-stack CLI extension (init/add/push/submit/view); branch protections and required checks apply per layer; merge-queue integration is still rolling out. make-pr's existing base-ref override plus the export-cognitive-aid base-scoped diff already produce correct layer-scoped PR bodies when the base points at a lower branch - the architecture anticipated this; stacking improves make-pr rather than conflicting with it.

## Goal & Context

<!-- Source-tag breakdown: 15% [user], 45% [paraphrase], 40% [inferred] -->

Today a spec that depends on an unmerged spec stalls the build loop: pilot cannot drain it until the parent PR merges. GitHub's native stacked PRs remove that stall - pilot can branch a dependent spec off the parent spec's branch and open its PR as the next stack layer, so the build loop keeps producing while the ship loop babysits the whole stack. Reviewers get per-layer diffs (which compose with the cognitive-aid body: the stack map answers "where am I in the change", the body answers "where do I focus in this layer"), and different layers can receive different cross-model reviews in parallel.

This is deliberately deferred: the feature is a public preview explicitly subject to change, requires the gh-stack CLI extension for stack-linked creation, and its merge-queue interplay is unfinished. This spec parks the design so it is ready to activate when the preview stabilizes - merge-queue general availability is the suggested revisit trigger.

## Acceptance Criteria

- **R1:** Pilot can drain a ready spec whose dependency spec has an open unmerged PR by branching off the dependency's branch and opening the new PR as a stack layer on top of it - instead of skipping the spec until the parent merges. [paraphrase]
- **R2:** make-pr gains a stack-aware create path: when the resolved base is another spec's branch and the stack tooling is available, the PR is created as a linked stack layer; otherwise it degrades to the existing plain dependent-PR create with the explicit base. [paraphrase]
- **R3:** make-pr's base-detection cascade gains a parent-spec rung: a spec with a flow dependency on an unmerged spec resolves its default base to that spec's branch (explicit base override still wins). [inferred]
- **R4:** The cognitive-aid body of a layer PR is scoped to that layer's diff only (base = parent branch) and states its stack position in one line. [paraphrase]
- **R5:** Land merges stacks bottom-up, one layer per tick, re-gating upper layers after each GitHub auto-retarget; the stack collapse merge stays forbidden. Depends on the companion land-hardening spec landing first. [paraphrase]
- **R6:** The whole capability is opt-in and preview-gated: with the gate off (default), pilot, make-pr, and land behave exactly as today; no hard dependency on the gh-stack extension is introduced for non-stacked flows. [user]
- **R7:** Cross-platform: hosts without the stack tooling degrade gracefully to today's serial dependent-spec behavior with a stated reason, never a hard failure. [inferred]

## Boundaries

- Deferred: do not implement while the GitHub feature is in public preview; revisit when stack semantics stabilize (suggested trigger: merge-queue support for stacks reaches general availability). [user]
- No merge-queue enrollment by land, stacked or not. [paraphrase]
- No stack authoring under Ralph or any autonomous driver until the opt-in gate is explicitly enabled by the user. [inferred]
- Not a replacement for spec dependencies or the tracker relations projection - stacking is a delivery mechanism, not a planning model. [inferred]

## Decision Context

Motivation: this directly serves the one-dial-to-autonomous claim - the merge-wait stall is currently the main serialization point in multi-spec autonomous runs, and native stacking removes it without weakening any gate (branch protections and per-layer checks still apply). The research verdict was that stacking improves make-pr (the base-scoped export already produces layer-correct bodies) and only land needs hardening, which is split into the companion spec so the insurance lands independently of this deferred feature. [paraphrase]

## Requirement coverage

| R-ID | Task |
|------|------|
| R1 | TBD - populate via /flow-next:plan |
| R2 | TBD - populate via /flow-next:plan |
| R3 | TBD - populate via /flow-next:plan |
| R4 | TBD - populate via /flow-next:plan |
| R5 | TBD - populate via /flow-next:plan |
| R6 | TBD - populate via /flow-next:plan |
| R7 | TBD - populate via /flow-next:plan |
