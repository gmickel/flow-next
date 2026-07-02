# Autoresearch changelog — make-pr (heavy prompt, R6)

Each entry: experiment N, keep/discard, score, change, reasoning, result.
Lever: prompt-trim (input savings), behavioral guard (rendered body equivalent).
Run-trick: --dry-run render from a frozen export-cognitive-aid payload (fixtures/payload-rich.json)
via general-purpose subagent. Model held: opus. 5 behavioral/accuracy evals.
Capture-lesson constraint: do NOT trim guardrails/routing/omission prose (accuracy-critical,
proximity-sensitive); only the render-irrelevant fn-42.N build-archaeology is in scope this pass.

## Experiment 0 — baseline
**Score:** 5/5 (rich payload, N=1 — proportionate: the candidate trim is render-irrelevant archaeology)
**Per-eval:** Section-set/order ✓ · R-ID-coverage ✓ · No-halluc-paths/SHAs ✓ · Decisions/memory-honest ✓ · No-raw-diff/breadcrumb/dry-run ✓
**Render:** full body — title+summary blockquote (Spec/Branch/Tasks 11/R-ID 16/16) → TL;DR (5 bullets) → R-ID coverage table (R1-R16 each mapped to its task(s) via `satisfies` + evidence-commit links) → Critical changes (5 high-churn bullets + honest "no cross-module/public-interface/security signal" note) → Decisions made (the 1 payload decision) → Memory left behind (the 7 payload bugs; 0 architecture_patterns omitted) → Glossary/strategy (glossary empty→omitted; 3 strategy tracks served) → Open items omitted (no deferred findings) → Where to look (Architecture + Behavior correctness) → footer breadcrumb. Dry-run short-circuited cleanly (no push/create/confirm).
**Minor (skill behavior, not a trim concern):** the agent synthesized GitHub `#diff-<hash>` URL anchors it can't know — disclosed honestly in a note. Cosmetic URL artifact, not a path/SHA/claim fabrication; identical across baseline+experiment so it doesn't affect the comparison.

## Experiment 1 — KEEP
**Score:** 5/5 (held baseline) — body behaviorally equivalent on the rich payload.
**Change (one hypothesis = render-irrelevant archaeology removal):** stripped all 29 `fn-42.N`
build-scaffolding refs — the stale "implemented in fn-42.3"-style task attributions in headings,
parentheticals, a `phases.md` "Owner task" table column, and 2 orphaned scaffolding sentences
("This task is responsible for steps 1-4…", "Phase 0 is implemented in this task…"). Kept the useful
`§Phase N` cross-references; only the task-id noise was removed. ~170 tokens off (SKILL −44,
workflow −87, phases −39). Did NOT touch the §2.5 hallucination guardrails, the 5-tier
critical-changes priority, the where-to-look categories, the omission rules, or the mermaid triggers
(all accuracy/render-shaping — the capture lesson).
**Result:** rendered body held 5/5 — same section set + order, same R1-R16 coverage from
`tasks[].satisfies` + evidence commits, same 1-decision/7-bug memory mirror, empty surfaces omitted,
breadcrumb present, dry-run short-circuited. The two renders differed only in run-variance ways
unrelated to the trim, both favoring the trimmed run: it correctly fired Phase-3 mermaid trigger 5
(>15 files in >3 modules — baseline missed it) and used clean relative paths instead of fabricated
GitHub `#diff-<hash>` anchors. Neither is trim-caused. KEEP.

## Conclusion (this pass)
The cleanly-safe trim on make-pr is ~170 tokens of build archaeology — real hygiene, modest size.
The honest finding: **make-pr's ~31k is mostly load-bearing** — 5 phases, 11 conditional body
sections, 10 hallucination guardrails, mermaid rules, push/retry, memory templating. Per the capture
lesson, its verbose render prose is accuracy-shaping and proximity-sensitive; trimming it is an
accuracy-risky **per-section backlog** (each section needs its own eval-guarded experiment), not a
one-shot. Deliverables: the archaeology trim (kept), a reusable --dry-run behavioral-eval harness +
two real frozen payloads (rich/sparse) for future per-section trims.

## Experiment 2 — re-baseline (fn-82.4, 2026-07-02)
**Score:** 5/5 (rich payload, N=1). Fresh baseline on the fn-82 branch (post fn-81 single-emission +
fn-82.1-.3 reshapes) before the phases.md fold — the exp-0/1 rows predate those reshapes.
**Per-eval:** Section-set/order ✓ · R-ID-coverage ✓ (16/16 from `tasks[].satisfies` + evidence) ·
No-halluc-paths/SHAs ✓ (23/23 SHAs + 5/5 paths payload-traceable, checked programmatically) ·
Decisions/memory-honest ✓ (1 decision + 7 bugs mirrored, 0 patterns, empty surfaces omitted) ·
No-raw-diff/breadcrumb/dry-run ✓. Note: this run omitted `## Where to look` — legitimate under
§2.12 (docs-only diff: no Architecture anchor, security/business/performance empty, Tests bullet
suppressed); exp-0 emitted it — run variance on a judgment call, both spec-defensible.

## Experiment 3 — KEEP (fn-82.4 fold)
**Score:** 5/5 (held baseline).
**Change (one hypothesis = fold, not gate):** folded every phases.md `**Done when:**` checklist
verbatim into workflow.md's inline `### Done when` blocks (union — richer phases.md items added,
new Phase-1 block, Phase-0/1.5 failure-modes lists), reduced phases.md to a 15-line stub (stable
link target — deletion forbidden), removed phases.md from SKILL.md's force-load list + the
`$FLOWCTL` preamble mention. No guardrail/routing/render prose touched. Working set −18.1KB
(~4.5k tok)/run; workflow.md +6.4KB. The phases.md-only "Body ≤8000 chars" cross-phase invariant
(contradicting §4.4's 65,000-char cap) died with the stub — it was stale archaeology.
**Result:** body held 5/5 — same section order, 16/16 coverage, 36/36 SHAs traceable, same
1-decision/7-bug mirror, trigger-5 `graph TB` + prose summary, breadcrumb, dry-run short-circuit.
Variance: this run EMITTED the Where-to-look Tests bullet (baseline suppressed it) — same
docs-only judgment call as exp 2's note, rule text identical in both rounds (it lives in
workflow.md §2.12, which the fold did not touch). Not fold-caused. KEEP.
