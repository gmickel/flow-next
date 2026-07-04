# Binary evals (6) — E1–E5 behavioral body-equivalence (accuracy floor) + E6 Where-to-look quality

**fn-84.4 extended-schema split:** E1–E5 are the BEHAVIORAL/ACCURACY floor (hallucination guards +
body-equivalence), scored on the `--dry-run` rendered body for **payload-rich AND payload-risky**
(accuracy_max = 5 × 2 = **10**). **E6 is the QUALITY-lever scoring eval** (Where-to-look risk
prioritization), scored on **payload-risky** only — rich/sparse have no risk-differentiated diff, which
is exactly why the pre-fn-84 suite couldn't measure Where-to-look quality (Major-4). quality_max = 1 × 1
= **1**. max_score = **11**. E6 authored BEFORE the fresh re-baseline (Major-B). `payload-sparse` is an
E1 empty-section-omission spot-check (not scored into the total). A prompt-TRIM is kept only if it holds
every eval AND cuts tokens (efficiency); the QUALITY lever is kept if E6 rises without any E1–E5 regress.

EVAL 1: Section set + order  [BEHAVIORAL]
Question: Does the body render the expected sections in the load-bearing order (Title/summary →
TL;DR → R-ID coverage → Critical changes → [Decisions made] → [Memory left behind] → [Open items] →
Where to look → footer breadcrumb), emitting a section iff its payload data is non-empty?
Pass: section set + order matches; sections with data present, empty sections omitted.
Fail: a data-backed section missing, an empty section emitted with a sentinel, or out-of-order.

EVAL 2: R-ID coverage complete  [ACCURACY]
Question: Does the R-ID coverage reflect the task `satisfies[]` union (R1–R16 from the 11 tasks),
mapping each covered R-ID to its task(s)/evidence, with uncovered R-IDs flagged ⚠️ (none here →
none flagged)?
Pass: coverage derived from `tasks[].satisfies` + evidence commits; no R-ID invented; no false ⚠️.
Fail: fabricated coverage, missing covered R-IDs, or a covered R-ID wrongly flagged uncovered.

EVAL 3: No hallucinated paths/SHAs  [ACCURACY]
Question: Is every file path in the body present in `diff_summary.files[]`, and every commit SHA in
`tasks[].evidence.commits[]` (no path/SHA invented from spec text)?
Pass: all paths ∈ diff_summary.files; all SHAs ∈ task evidence. Zero fabrication.
Fail: any path or SHA not traceable to the payload.

EVAL 4: Decisions/memory traced honestly  [ACCURACY]
Question: Does the Decisions / Memory content come from `memory_during_epic` (1 decision, 7 bugs,
0 architecture_patterns) with no invented "why", and empty surfaces (glossary, strategy, reviews)
honestly omitted rather than confabulated?
Pass: decisions/bugs mirror the payload; empty surfaces omitted; no narrated rationale.
Fail: invented decision rationale, fabricated memory ids, or a confabulated empty surface.

EVAL 5: No raw diff / no confirm gate / breadcrumb  [BEHAVIORAL]
Question: Does the body avoid quoting raw diff code, include the footer provenance breadcrumb, and
(being --dry-run) render to stdout WITHOUT any push / gh pr create / confirm prompt?
Pass: no code snippets; breadcrumb present; dry-run short-circuits cleanly (no PR side effect).
Fail: code quoted, breadcrumb missing, or any push/create/confirm attempted.

EVAL 6: Where-to-look risk prioritization  [QUALITY-LEVER SCORING EVAL — payload-risky only]
Question: On payload-risky (`diff_summary.security_sensitive_paths = [credentials.py, flowctl.py]`; a removed
public export `_legacy_token_env`; a high-churn TEST file + low-risk docs), does the `## Where to look` section
(a) RENDER — its Security category (§2.12 cat 2) triggers on `security_sensitive_paths[]` — and (b) LEAD with
question-shaped Security bullets for the credential/core files, ahead of the Tests/Business/Performance
categories (§2.12 order = Architecture → Security → Business → Perf → Tests); AND does `## Critical changes`
SURFACE the removed public export (`_legacy_token_env`, tier-3 removed-first)?
Pass: Where to look renders with Security bullets for `credentials.py`/`flowctl.py` FIRST (question-shaped,
Security ahead of lower categories); the removed `_legacy_token_env` appears in Critical changes.
Fail: Where to look OMITS the Security category despite `security_sensitive_paths` being set, buries security
below Tests, uses labels instead of questions, or Critical changes omits the removed public export.
NOTE: Critical-changes tier-1 CHURN ordering (the test file ranking high by churn) is BY DESIGN (§2.4 5-tier),
NOT an E6 failure — E6 scores the Where-to-look reviewer-focus surface + the removed-export surfacing.

---

## fn-84.4b — REVIEW-EASE capability evals (E7–E10, the "go further" goal)

New render sections that make PRs easier to review (fable design review 2026-07-04). These verify the new
capability renders CORRECTLY and without hallucination — the zero-fabrication floor for each new section.
They were impossible before the sections existed (baseline-without = N/A); the new prose must pass them AND
keep E1–E6 green (no regression). Scored on payload-risky unless noted. max_score grows by 4 → **15**.

EVAL 7: Review plan / attention budget  [REVIEW-EASE] — payload-risky
Pass: `## Review plan` renders; a **Careful-review surface** line with numbers; EVERY `diff_summary.files[]`
path appears in exactly one bucket; `credentials.py` + `flowctl.py` + `__init__.py` in 🔴 Careful; the docs /
CHANGELOG / README paths in ⚪ Skim; `test_credentials.py` in 🟢 Tests; buckets in Careful→Behavior→Tests→Skim
order. Fail: a path invented or missing, a path double-bucketed, a security/export file dropped to Skim, or the section absent.

EVAL 8: Verification evidence  [REVIEW-EASE] — payload-risky
Pass: `## Verification` renders; each per-task line's items are VERBATIM `tasks[].evidence.tests[]` entries
(no paraphrase, no "passed review" summary of a NEEDS_WORK history); the honest test-gap line names
`flowctl.py` (high-churn source, +418/-192) as having no accompanying test-file change while `test_credentials.py`
is the diff's test file; the word "untested" NEVER appears. Fail: an invented test claim, a paraphrased entry,
"untested"/inference wording, or a fabricated gap on a file that has a companion test.

EVAL 9: Not in this PR (by design)  [REVIEW-EASE] — payload-rich (9 boundaries)
Pass: `## Not in this PR (by design)` renders directly after TL;DR; ≤5 bullets, each a VERBATIM (truncated)
`spec_sections.boundaries[]` entry; more-than-5 → a `…and N more (see spec)` line. Fail: an invented/softened
boundary, >5 bullets with no overflow line, or the section absent when boundaries[] is non-empty.

EVAL 10: R-ID provenance chip  [REVIEW-EASE] — payload-rich (1 inferred, 14 paraphrase)
Pass: the R-ID coverage table renders ` · inferred` in the R-ID cell of the ONE `inferred`-tagged criterion
and NO chip on the `paraphrase`/empty-tagged rows. Fail: chip missing on the inferred row, or a chip on a
paraphrase row (false provenance warning).
