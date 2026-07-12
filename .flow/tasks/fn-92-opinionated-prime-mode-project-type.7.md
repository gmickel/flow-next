---
satisfies: [R3, R6b, R7, R8, R9, R10, R16]
---

## Description
workflow.md Phase 4/5/5.5 + remediation.md + QA cross-ref: report, remediation, fix-all boundaries.

**Size:** M | **Files:** `plugins/flow-next/skills/flow-next-prime/workflow.md` (Phases 4/5/5.5/7), `plugins/flow-next/skills/flow-next-prime/remediation.md`, `plugins/flow-next/skills/flow-next-qa/SKILL.md` (one cross-ref line)

## Approach
- Phase 4 report template: classification block, operability tier + gate status + top-5 headline (level to secondary metadata), per-shape blocks from playbooks.md, QA-readiness line (R16 tail: recommend qa/pipeline.qa ONLY when tier 3 + DR core pass; else name missing DR items; shape-capped = not-applicable), DE7 suggestion stack-gated via stacks.md map column, DC8 lines unchanged, compression rule (resolution 13), Unresolved-questions section, freshness caveat.
- Phase 5: questions draw from the tiered catalog (playbooks.md) instead of the four fixed JSONs; max-4-options and never-Pillar-6-8 rules kept; Q2 hook option reframed to layered gates (resolution 15); --fix-all honors the catalog tier column + boundary rules.
- Phase 5.5 untouched except read-back gate confirmed. Phase 7 re-run reuse rule tail.
- remediation.md: new templates (orientation map skeleton, home-base starter kit marked outside-ROOT/consent-only, bootstrap-plan, encoding-guard hook, headless compile wrapper, deny-rules baseline, run-and-observe recipe); hook templates reframed (format/lint staged-scope, tests-to-verify note); never-bulk-generate-CLAUDE.md strengthened; DC2 denominator normalized to the pillars.md scale.

## Key context
- CRITICAL sync-codex anchors: the Phase 5 consent sentence (L253) and scout-dispatch lines must stay byte-identical OR sync-codex.sh co-updated in this same task (resolution 12). Run scripts/sync-codex.sh + validation before commit.
- HP7 read-vs-exercise distinction stated where remediation offers hooks (gap 27).

## Acceptance
- [ ] Report leads verdict + top-5 with file-level actions; level demoted; per-shape + QA-readiness + unresolved-questions blocks present (R3, R7-R10, R16 tail)
- [ ] Phase 5 remediation catalog-driven with tier column; --fix-all boundaries enforced incl. greenfield rule (resolutions 5/6/16)
- [ ] remediation.md new templates present, consent classes marked; hook framing = layered gates; scaffolded artifacts exercised-in-pass rule stated (R6b, R7)
- [ ] qa SKILL.md carries the one-line prime cross-ref; sync-codex regen + validation green; anchor sentences preserved or sync co-updated

## Done summary
Rewrote flow-next-prime Phases 4/5/5.5/7 and remediation.md for the opinionated verdict-led report: Phase 4 now leads with the classification + operability tier + hard-gate status + top-5 ranked actions (rendering Phase 3's verdict assembly, level demoted), with per-shape bodies, the render-only QA-readiness line, stack-gated DE7 map suggestion, an Unresolved-questions section, and a freshness/re-run caveat; Phase 5 remediation is catalog-driven with tier + consent boundaries and layered-gate hooks; remediation.md gained the seven consent-classed templates (orientation map, home-base kit, bootstrap plan, encoding-guard hook, headless compile wrapper, deny-rules baseline, run-and-observe recipe) plus reframed hooks, strengthened never-bulk-generate, DC2 X/8 sweep, and HP7 read-vs-exercise rules. qa SKILL.md carries the one-line prime cross-ref. Codex mirror regenerated (sync-codex validation green); full suite 1615 tests green.
## Evidence
- Commits: a8f30f76d8959fec4ac3b5a3961a3562a45e7482
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' (1615 tests, OK skipped=2), bash scripts/sync-codex.sh (validation green)
- PRs: