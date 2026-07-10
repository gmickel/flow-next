## Description
Size: XS. One small prose touch in make-pr workflow.md: the Review plan / Traceability rendering references the four fields opportunistically (coordinate with fn-93's sections — whichever lands second reconciles). flowctl.md export section + CHANGELOG Unreleased + mirror regen.
## Acceptance
- [ ] Render references the fields with graceful-absence wording; docs + CHANGELOG; mirror regen; gates green.

## Done summary
Added the CHANGELOG `## Unreleased` entry covering fn-86's four additive `export-cognitive-aid` traceability fields (changed_symbols / derived / removed_export_refs / evidence.files) landed by fn-86.1, noting the make-pr render consumption ships with fn-93's Review-plan contract (PR #204). flowctl.md export section was already documented complete by .1 (verified, no gap); Codex mirror regenerated with all guards green and zero drift. Full unittest (1577 OK, skipped 2) + smoke (144 passed / 0 failed) green from the worktree root.

Render-consumption verification (host override — workflow.md intentionally NOT edited here; fn-93 / PR #204 owns it): confirmed origin/fn-93-make-pr-reviewer-effort-reduction-risk workflow.md §2.4c/§2.4d genuinely consumes the fn-86 fields opportunistically — changed_symbols as symbol anchors (L645), derived for safe-to-skim bucketing (L655), and the review signal (L613) — all with graceful-absence wording.
## Evidence
- Commits: e24e82b1e3cd01d759975a702d16d885595438d6
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' (from worktree root) -> Ran 1577, OK (skipped=2), bash plugins/flow-next/scripts/smoke_test.sh (from neutral cwd) -> 144 passed / 0 failed, SMOKE_EXIT=0, sync-codex.sh -> all guards green, zero mirror drift
- PRs: