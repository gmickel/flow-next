---
satisfies: [R2]
---
# fn-180-declared-vs-evidenced-r-id-coverage.2 make-pr skill: plan-gate rendering + abort re-keyed on undeclared coverage

## Description
Spec fn-180 item 1 (#301). make-pr renders per-criterion claimed-not-evidenced status at a plan gate and aborts only when coverage is undeclared (the condition the abort was meant to catch). Update the skill prose + any reference; sync-codex twice.

Post-capture (3.19 branch-disclosure, see spec Edge Cases): make-pr is split across workflow.md / create-and-finalize.md / phases.md + references; the unrenderable-abort to re-key is workflow.md's rendering step (§2.7 abort conditions). Fixtures follow the pin-shape rule (agent_docs/adding-skills.md). Conduct checklist: agent_docs/conduct/make-pr.md.

**Files:** plugins/flow-next/skills/flow-next-make-pr/workflow.md (+ any reached-path file carrying the abort/coverage prose) + codex mirror regen; make-pr prose-contract tests

## Acceptance
R2 of the spec. #301's abort repro renders instead of aborting; undeclared-coverage state still aborts with corrected stderr advice.

## Done summary
make-pr prose per fn-180 R2 (#301). Coverage abort re-keyed on undeclared_r_ids (fires only when NO task claims ANY criterion - the one state where the advice is actionable) with corrected stderr: "Undeclared R-ID coverage ... Add satisfies entries ... or re-run /flow-next:plan". Plan-gate spec (all todo, fully declared) renders: three-state coverage table (Evidenced / claimed-not-evidenced with hourglass rows keeping the claiming task links / Undeclared with the warning marker), summary ratio stays evidenced-only with claimed/undeclared clauses appended when non-zero, post-table lines split so the warning belongs only to genuinely unclaimed criteria. Artifact-current path documented as evidenced-only by construction (rid refs bind to commits); abort runs on the export payload pre-artifact; qualifier clauses carve out same as the residue count. Guardrail rule 7 sharpened; stale SKILL.md/0.5 lines corrected. Conduct checklist make-pr.md: 6/6 pass. 5 new prose-contract fixtures (content + reachability).
## Evidence
- Commits: b656216b
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_make_pr_reached_path test_export_traceability -q (46 OK), 8 prose/fixture suites (150 OK), post-mirror reached-path (78 OK)
- PRs: