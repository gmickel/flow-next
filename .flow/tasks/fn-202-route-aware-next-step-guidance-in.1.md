---
satisfies: [R1, R3, R4]
---
# fn-202-route-aware-next-step-guidance-in.1 Capture closer: Recommended-next line in base, rewrite, and split footers

## Description
Add the host-judged `Recommended next:` line to capture's Phase 6 footer surfaces, per the spec's gap resolutions.

**Files:** plugins/flow-next/skills/flow-next-capture/workflow.md (§Phase 6, insertion between the `Tracker sync:` line and the `Next:` menu, workflow.md:658-668), references/rewrite-mode.md (its own `Next:` block, ~:91), references/split-proposal.md (per-spec footer blocks, ~:69-71).

**Approach:** follow the R25 biz-suggestion precedent (workflow.md:674-691): prose states the judgment rule, the footer renders one literal line, with the 'informational only — never a blocking prompt' disclaimer register. The prose names the judgment inputs explicitly: readiness state, open `[inferred]` criteria, Parked unknowns (→ interview); resolved decisions + real design risk (→ plan); near-zero-risk fully-known (→ plan, noting work may suffice). Legal targets ONLY: /flow-next:interview, /flow-next:plan (with optional work note), /flow-next:guide on genuine signal conflict — chart is an explicit non-target (upstream of capture per pipeline-variations). The line is MANDATORY every run (no silent omission; conflicted → guide). Line shape: `Recommended next: /flow-next:<stage> <id> — <one-clause reason>; <named alternative when it applies>`. Link the smallest-sufficient rule once per touched file as [docs/pipeline-variations.md](../../docs/pipeline-variations.md) — NO rubric text copied, no size-based language. Split-proposal: one recommendation per created spec inside its own footer block + one sentence stating recommendations are per-spec and the shared dependency-edge line owns execution order. Existing conditional footers (R25, memory-hits, Glossary/Readiness/Artifact optional lines) stay byte-identical and un-reordered.

**Touches:** [plugins/flow-next/skills/flow-next-capture/workflow.md, plugins/flow-next/skills/flow-next-capture/references/rewrite-mode.md, plugins/flow-next/skills/flow-next-capture/references/split-proposal.md]

## Acceptance
- Base footer prints exactly ONE `Recommended next:` line above the unchanged `Next:` menu, after `Tracker sync:`; menu text byte-identical
- Rewrite-mode and split-proposal footers carry the same single-line shape; split is per-spec with the dependency-edge sentence
- Judgment inputs named in prose incl. readiness; chart excluded; guide is the mandated conflicted-signals fallback; no rubric text copied; one pipeline-variations link per touched file; no size-based selector language
- R25 / memory-hits / optional footer lines unchanged and un-reordered (diff shows pure insertion)
- Error surface: none beyond the mandated guide fallback (no new bash, no config reads)

## Done summary
Added the mandatory host-judged `Recommended next:` line to capture's three closer footers: base Phase 6 footer (between `Tracker sync:` and the unchanged `Next:` menu), rewrite-mode footer (re-judged on rewrite), and split-proposal per-spec footer blocks (one recommendation per created spec; the shared dependency-edge line owns execution order). Prose names the judgment inputs (readiness, open `[inferred]` criteria, Parked unknowns -> interview; design risk -> plan; near-zero-risk -> plan noting work may suffice), restricts targets to interview/plan/guide (guide as the conflicted-signals fallback; chart excluded), links docs/pipeline-variations.md once per touched file, copies no rubric text, uses no size-based language. Diff is 10 pure insertions, 0 deletions - existing R25/memory-hits/optional footer lines byte-identical and un-reordered.

stage: impl-review - skipped(config: REVIEW_MODE=none)
## Evidence
- Commits: f3639a47
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned test_skill_prose_diet -q (integrated head, green), uvx ruff@0.16.0 check . (green)
- PRs: