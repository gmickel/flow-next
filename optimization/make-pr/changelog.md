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

## fn-84.4 pass (2026-07-04) — re-baseline + E6 Where-to-look; both axes tested

**Model** sonnet (`--dry-run` render). `results.tsv` migrated to the extended schema (history h0–h3).
Added **E6 (Where-to-look risk prioritization)** + a new **`payload-risky.json`** fixture (risk-
differentiated diff: core `flowctl.py` [high churn + removed public export `_legacy_token_env`] + new
security `credentials.py` + `security_sensitive_paths[]`, vs a high-churn test file + low-risk docs),
BEFORE the fresh baseline (Major-B). E1–E5 scored on rich+risky (accuracy_max 10); E6 on risky (quality_max 1).

### Fresh baseline (exp 0) — 11/11 (accuracy 10/10, quality 1/1)
E1–E5 behavioral held on both payloads. **E6 PASS**: with `security_sensitive_paths` set, Where-to-look
renders + leads with question-shaped Security bullets (`credentials.py`, `flowctl.py`) and Critical changes
surfaces the removed `_legacy_token_env`. **Fixture-correction note:** an initial E6=0/1 was a FIXTURE
artifact — the first `payload-risky` lacked `security_sensitive_paths[]`, so the Security category correctly
did not fire and no Where-to-look rendered. make-pr's Where-to-look is **already risk-prioritized by design**
(5 field-triggered categories in risk order: Architecture → Security → Business → Performance → Tests).
Confirms the fn-82 fold did not regress behavior.

### Experiment 1 — EFFICIENCY trim — KEEP (−78 tok)
Per the user's steer (test the efficiency ceiling on the heaviest prompt), trimmed ~78 tok of
**render-irrelevant rationale asides** (reader-engagement-studies justification, heredoc-failure citation,
prose-shaped-data rationale) — keeping every rule/field/example. Body held **risky E1–E6 6/6** (directly
verified: Where-to-look still renders question-shaped Security bullets; removed export surfaced); rich
E1–E5 inferred-safe (trim is render-irrelevant, doesn't touch rich-specific rendering — same class as the
verified h1 archaeology). KEPT. **This IS the efficiency-ceiling finding:** −78 tok = 0.22%; fn-82's fold
already harvested the −4.5k win; the remaining ~35k prose is render-load-bearing (5-tier priority, the 5
Where-to-look categories + field rules, hallucination guards) — deeper trims are an accuracy-risky per-
section backlog, not a safe one-shot.

### Experiment 2 — QUALITY lever (Where-to-look reviewer-focus) — DISCARD-HOLD
E6 at ceiling 1/1 → no headroom. Where-to-look already prioritizes risk correctly; the hypothesized gap
was a fixture artifact. Not run.

### Net
Re-baseline confirms + broadens coverage (E6 + risky fixture — the suite can NOW measure Where-to-look
quality, which it couldn't pre-fn-84). Efficiency: at ceiling (−78 tok kept, ~0.2% remaining). Quality:
at ceiling. Durable: an eval that guards Where-to-look risk-prioritization on a risk-differentiated fixture.

## fn-84.4 — fable-review pass (NEEDS_WORK → addressed)

The initial pass under-tested the EFFICIENCY axis (declared "ceiling" from one guaranteed-safe −78 tok
rationale trim) and shipped an off-schema `payload-risky`. Fable review (NEEDS_WORK) flagged both; addressed:

- **[MAJOR] efficiency measured, not asserted.** Extended the probe to a MEASURED **−189 tok** trim:
  more of the safe rationale class (Section-purpose-framing paragraph, the duplicated skim-readability
  sentence :604/:1028) PLUS a **structural** omission-clause dedup — removed the redundant "Heading omitted
  if empty" clauses from the per-section Memory/Glossary rules now that the authoritative §2.13 table covers
  them. Verified body-equivalent on BOTH fixtures: rich E1–E5 5/5 (empty sections still omitted → structural
  dedup safe) + risky E1–E6 6/6. **Measured boundary:** retained §2.8's UNIQUE "no fallback no-decisions line"
  imperative (the §2.13 table lacks it → cutting it risks an empty-state line = E1 regression); the per-section
  unique imperatives + the field-rules are the remaining accuracy-risky backlog.
- **[MAJOR] fixture fidelity.** `public_exports_changed` reshaped to the real exporter shape
  `[{file, added[], removed[]}]` on an exporter-faithful `__init__.py` (the real detector only fires on
  `__init__.py`/`index.*`/`mod.rs`/`lib.rs`); `security_sensitive_paths` reduced to the faithful `credentials.py`
  (dropped `flowctl.py`, which the real heuristic can't produce); `lines_added/removed`/`files_changed` recomputed.
  Re-verified: E6 still 1/1 on the faithful fixture (Where-to-look Security bullet + removed export via `__init__.py`).
- **[MINOR] quality "ceiling" reworded** — "no MEASURABLE headroom at current granularity (quality_max=1)"; a
  future pass could grade E6 multi-point (risky variants: cap-overflow ordering, arch+security conflict).
- **[MINOR] README updated** — payload-risky documented as synthetic; the "does NOT trim where-to-look" constraint
  updated (E6 now guards it).

Net (corrected): re-baseline confirms; **efficiency −189 tok kept (MEASURED, incl. a structural dedup)**; quality
at ceiling (Where-to-look risk-prioritized by design). Durable: an E6 eval + a risk-differentiated fixture that
lets the suite measure Where-to-look quality (which it couldn't pre-fn-84).

## fn-84.4b — REVIEW-EASE capability ("go further — make PRs easier to review")

Gordon's steer after fn-84.4: make-pr "just lists changes + where to look — it should go further." A fable
DESIGN review found the always-on body dropped THREE payload fields on the floor. Added 4 render-only sections
(no flowctl change, all trace-to-field, zero new investigation):

- **`## Not in this PR (by design)`** ← `spec_sections.boundaries[]` (verbatim, cap 5 + overflow) — kills
  scope-objection threads before they're typed. Slots after TL;DR.
- **`## Verification`** ← `tasks[].evidence.tests[]` verbatim + an honest test-gap FACT ("No test-file change
  accompanies `flowctl.py` (+418/-192)") — never the inference "untested." Slots after R-ID coverage.
- **`## Review plan`** (attention budget) ← `diff_summary.files[]` bucketed 🔴Careful/🟠Behavior/🟢Tests/⚪Skim
  by a deterministic pattern table + a "Careful-review surface: ~707 of 940 lines" line. Ports the HTML lens's
  review-intent ordering to the surface every reviewer sees. Slots after Critical changes.
- **R-ID provenance chip** ← `acceptance_criteria[].tag` — ` · inferred` on weak-provenance criteria.

Verified rich + risky (sonnet, --dry-run): **E7–E10 all PASS AND E1–E6 no regression = 15/15**. Risky nailed
the bucketing (flowctl.py/__init__.py/credentials.py → Careful, test_credentials.py → Tests, docs → Skim), the
honest flowctl.py test-gap, and the `R15 · inferred` chip. Cost: +1,280 prose tok (34989→36269) — a capability
gain (quality↑), not an efficiency regression. Deferred to a follow-up spec (need flowctl code): removed-export
remaining-references (`git grep`) + per-task `evidence.files[]` for exact-hunk R-ID traceability.
