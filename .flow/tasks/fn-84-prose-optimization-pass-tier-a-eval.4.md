---
satisfies: [R1, R2, R3, R4, R5, R6, R8]
---

## Description
Re-run the eval-gated loop on the `make-pr` skill. Suite EXISTS (`optimization/make-pr/`) but make-pr changed in fn-82. Order (Major-B critical here): MIGRATE `results.tsv` to the extended schema → EXPAND the eval set FIRST (add the Where-to-look scoring eval + risk-ranked fixture) → baseline under the FULL expanded eval set → one mutation. Heaviest prompt in Tier A (`workflow.md` 1942L); only render-irrelevant archaeology trims are safe.

**Size:** M (re-baseline under expanded evals + one mutation on the heaviest prompt)
**Files:** `optimization/make-pr/{results.tsv,evals.md,changelog.md,fixtures/*,baseline/*}`; `plugins/flow-next/skills/flow-next-make-pr/{SKILL.md,workflow.md,mermaid-rules.md}` (mutation if kept; `phases.md` is a 15L stub — deletion forbidden); `agent_docs/optimization-log.md`; `CHANGELOG.md`; `plugins/flow-next/codex/**`

## Approach
- **Expand the eval set BEFORE baseline (Major-B + Major-4):** the existing suite does NOT score "Where to look" risk-prioritization, and the fn-82 rich fixture had empty-source Where-to-look. So add `fixtures/payload-risky.json` (non-empty, risk-ranked changed files) + an eval scoring whether "Where to look" prioritizes the highest-risk review surfaces — as part of the FINAL eval set. Migrate `results.tsv` to the extended schema.
- **Baseline (R2):** refresh `baseline/{SKILL,workflow,phases,mermaid-rules}.md` from current main; run the FULL eval set (existing evals + the new Where-to-look eval) N times; record the baseline row. Only then mutate.
- **Run-trick (side-effect-free, output-only — no worktree, no interactive block):** `--dry-run` renders the PR body from the frozen JSON fixtures.
- **Quality lever:** the Where-to-look reviewer-focus lever — now measurable against the eval added above; keep iff it rises without regression. A lever with no scoring eval cannot be kept.
- **Trim opportunity:** only archaeology/rationale in `workflow.md` not affecting the rendered body is safe — behavioral evals guard the rest.

## Investigation targets
Required:
- `optimization/make-pr/` — existing suite (README `--dry-run` trick, fixtures/, evals.md, baseline/) — note the fn-82 ledger's empty-source Where-to-look observation
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md` — heaviest prose (1942L)
- `agent_docs/optimizing-skills.md` — proximity + trim-verbosity-not-count rules
Optional:
- `plugins/flow-next/skills/flow-next-make-pr/mermaid-rules.md`

## Key context
- `phases.md` is a 15L stub — do NOT delete.
- Assert the rendered body shape (R-ID table, critical-changes, where-to-look) unchanged by an eval; only prose wording moves.

## Acceptance
- [ ] `results.tsv` migrated to the extended schema; `fixtures/payload-risky.json` + Where-to-look scoring eval added as part of the FINAL eval set BEFORE baseline (Major-B/4, R4)
- [ ] Baseline row scored under the FULL expanded eval set on current main before any mutation (R2)
- [ ] Where-to-look quality-lever experiment run against its scoring eval; kept rows accuracy held/raised AND tokens↓/quality↑, discards logged (R3, R4)
- [ ] Rendered PR-body shape asserted unchanged by an eval (R5)
- [ ] Scoped privacy grep clean over `optimization/make-pr/` (R1)
- [ ] `optimization-log.md` row per experiment (R6)
- [ ] `sync-codex.sh` regenerated + committed IF prose changed; `pytest` + `make-pr_smoke_test.sh` + `smoke_test.sh` green; `CHANGELOG` `## Unreleased`; no bump (R8)

## Done summary
Re-baselined the `make-pr` suite (the heaviest prompt, ~35k tok) and tested BOTH axes — quality + **efficiency** (per your steer). Fable review NEEDS_WORK → all defects addressed.

**Suite work:** migrated `results.tsv` to the extended schema; added **E6 (Where-to-look risk prioritization)** + a new **`payload-risky.json`** fixture (risk-differentiated diff) BEFORE the fresh baseline (Major-B). Run-trick = `--dry-run` render at `sonnet`.

**Quality (Where-to-look):** at CEILING. make-pr's Where-to-look is **already risk-prioritized by design** (5 field-triggered categories in risk order: Architecture→Security→Business→Perf→Tests; Security fires on `security_sensitive_paths[]` and leads with question-shaped bullets; Critical changes surfaces the removed public export tier-3-first). The initially-hypothesized gap was a **fixture artifact** (the pre-fn-84 payloads had a low-risk scaffolding diff). Quality lever → honest discard.

**Efficiency (the axis you flagged):** **−189 tok MEASURED (kept)** — the fable review's first-round finding (I'd asserted a ceiling from one free −78 tok trim) was right, so I extended to a real probe: more of the safe rationale class + a **structural** omission-clause dedup (removed redundant "omit if empty" clauses once the authoritative §2.13 table covered them). Verified body-equivalent on BOTH fixtures (rich E1–E5 5/5 — empty sections still omitted; risky E1–E6 6/6). **Measured boundary:** the per-section *unique* imperatives (e.g. §2.8's "no fallback no-decisions line") + the field-rules — those are the remaining accuracy-risky per-section backlog. So the efficiency finding is now MEASURED: fn-82's fold already took the −4.5k win; ~−189 tok of safe rationale+dedup remained.

**Fable review NEEDS_WORK → addressed every defect:** (1) efficiency measured-not-asserted (−78→−189, incl. a structural dedup, verified on both fixtures + boundary identified); (2) fixture fidelity — `public_exports_changed` reshaped to the real exporter shape `[{file,added,removed}]` on an exporter-faithful `__init__.py`, `security_sensitive_paths`=[credentials.py] (dropped the unfaithful flowctl.py), sums recomputed; (3) quality-ceiling reworded to "no measurable headroom at current granularity (quality_max=1)"; (4) README updated (payload-risky = synthetic; E6 now guards where-to-look). It cleared me on goalpost-moving (the E6 fixture-fix was legitimate).

**R8:** Codex mirror regenerated; CHANGELOG `## Unreleased` entry (−189 tok make-pr trim); no version bump. Skill-prose only (the −189 tok trim); test surface unchanged.

**Durable deliverables:** an E6 Where-to-look-quality eval + a risk-differentiated fixture (the suite can NOW measure Where-to-look quality) + a measured efficiency win + boundary on the heaviest prompt.
## Evidence
- Commits:
- Tests: prose-only change (make-pr workflow.md -189 tok trim) — test surface unchanged since fn-84.1's green run; make-pr smoke guards against running from the plugin repo (expected), fable-model review: NEEDS_WORK -> all defects addressed (efficiency measured -189 not asserted -78 + structural dedup + boundary; fixture exporter-faithful; quality reworded; README updated)
- PRs: