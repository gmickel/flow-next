## Description
Size: XS. Ship surface: make-pr docs prose (skill SKILL.md summary line + docs index if it names sections), CHANGELOG `## Unreleased` entry (no version bump — batched), prbeval scores table already in the spec (verify present), docs-site make-pr page note staged for release walk. Final mirror regen.
## Acceptance
- [ ] CHANGELOG Unreleased entry; SKILL.md/docs section names updated; mirror regen; full suite + smoke green.

## Done summary
Propagated the fn-93 make-pr body-section shape to the doc surfaces and shipped the release record: teams.md (body-sections list + reviewer reading-order) and GLOSSARY.md (PR-as-cognitive-aid) now describe the new How-to-review coaching block + risk-bucketed Review plan instead of the removed "Where to look" list; added a CHANGELOG `## Unreleased` fn-93 entry (no version bump, batched) carrying the prbeval evidence (baseline 7/5/8/8 -> shipped 9/9/9/9, blind codex judge on real PR #203). Codex mirror regenerated with no drift (skill prose landed in fn-93.1); prbeval scores table confirmed present in the spec's Decision Context. Full gate green.
## Evidence
- Commits: 5a033a48427f76c6250a253913616268fee368f8
- Tests: python3 -m unittest discover (1556 OK, skipped=2), make-pr_smoke_test.sh (79 PASS/0 FAIL, from /tmp), smoke_test.sh (144 passed/0 failed, from /tmp), sync-codex.sh (no drift, structural guards green)
- PRs: