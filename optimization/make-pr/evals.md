# Binary evals (5) — behavioral (body-equivalence). max per run = 5.

Scored on the `--dry-run` rendered PR body for the rich frozen payload. The trim is kept only if it
holds every eval (a prompt-trim must leave the rendered body behaviorally unchanged). 3 of 5 are
accuracy evals (hallucination guards) per R3.

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
