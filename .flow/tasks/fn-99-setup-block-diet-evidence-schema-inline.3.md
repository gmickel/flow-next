# fn-99-setup-block-diet-evidence-schema-inline.3 usage.md trim: consumer audit, cuts, sandbox line, budget tests, changelogs

## Description
Content change only: consumer audit, usage.md trim, sandbox guidance, tripwire tests, 3-way atomic landing. Satisfies R5 (content half), R10, R11. Depends on .1 (block final). The eval gate + changelog/docs staging moved to task .4 for regression isolation.

Scope:
1. Consumer audit FIRST (R11): grep skills/, agents/, docs/, commands/ + repo/site orchestration pages for `usage.md` references (generic vs section-specific). Any cut section still pointed at -> keep it or update the pointer here. Reconcile the "read every session" loading-contract wording (repo + docs-site orchestration pages) to the actual contract, preserving anchors. Record audit results in the task summary.
2. Trim `templates/usage.md` (~5.3k -> ~2-2.5k tok): cut File Structure (:12-40), the --help-duplicating bulk of Common Commands (:48-194; keep ~10-line typical-flow core incl. the done line), Deprecation (:283-293). Keep: CLI, IDs, slimmed core, Orchestration & model steering (fn-94/fn-97 territory - no restructuring), Workflow, Evidence JSON Format, Parallel Worktrees, More Info. New prose syntax-neutral or sync-rewritable (CI guard sync-codex.sh:1654).
3. Sandbox-blocked-commit guidance (R11): primary line in `plugins/flow-next/agents/worker.md` adjacent to its evidence/commit teaching (:381-421 region) - if the sandbox denies git commit, still complete flowctl done with evidence and record the restriction in the summary, never block the task; secondary line in usage.md Workflow.
4. Token-budget tripwire tests (R10): claude-md-snippet.md <=300 tok-equiv, templates/usage.md <=2.8k tok-equiv (chars/4), comments pointing at this spec + eval memory. Budget by size, never by grepping forbidden tokens (memory: final-gate greps hit prohibition prose).
5. 3-way atomic: template + `.flow/usage.md` dogfood + `./scripts/sync-codex.sh` regen in one commit (test_dogfood_template_parity.py).
## Acceptance
- Audit recorded; zero dangling section pointers; loading-contract wording reconciled (R11).
- usage.md ~2-2.5k tok-equiv, keep-list intact; parity green; mirror regenerated, no /flow-next: leaks (R5 content).
- worker.md + usage.md carry the sandbox line (R11).
- Budget tests green and fail on regrowth (R10).
- Unit + smoke green. No changelog/docs-site edits in this task (task .4).
## Done summary
Trimmed the usage.md template from 5392 to 1928 tok-equiv (cut File Structure, the --help-duplicating Common Commands bulk down to a 10-line typical-flow core incl. the done line, and Deprecation; kept CLI/IDs/Orchestration-verbatim/Workflow/Evidence/Worktrees/More Info), landed 3-way atomically (template + .flow/usage.md dogfood + codex mirror regen, parity + slash-token guards green), and amended the snippet twins' evidence line to the eval-proven minimal-arm phrasing ("<sha>"/"<command>" placeholders + claim -> implement -> commit flow teach, 249 tok-equiv each, repo CLAUDE.md block refreshed via flowctl setup-block: pristine -> refreshed).

Consumer audit (R11): the only section-specific usage.md pointers in skills/agents/docs/commands target "Orchestration & model steering" (kept verbatim); zero pointers at cut sections; the "read every session" loading-contract claim in docs/orchestration.md corrected to read-on-demand (docs-site counterpart deferred to task .4 with the staging). Sandbox-blocked-commit guidance added to agents/worker.md Phase 5 (primary) and usage.md Workflow (secondary). Token-budget tripwires (R10) added as tests/test_token_budgets.py: block <=300 / usage.md <=2800 tok-equiv, size-only by design (no forbidden-token greps), eval-rationale comments. Note: .flow/locks/ (fn-99.1 lock dir) gitignored via user pattern; flowctl auto-gitignore fix flagged as a follow-up task. Codex impl-review (gpt-5.5): SHIP on r1. Implementation delegated to codex gpt-5.6-terra (medium); orchestrator kept git/review/landing.
## Evidence
- Commits: f564dab4ab6c53ff5bffdce546e06452661cc0ff
- Tests: python3 -m unittest discover -s tests (plugins/flow-next, 1786 tests OK, baseline: green 1784), bash plugins/flow-next/scripts/smoke_test.sh (144 passed), python3 -m unittest tests.test_setup_snippet_lockstep tests.test_setup_block_helper tests.test_dogfood_template_parity tests.test_token_budgets tests.test_flow_gitignore (25 OK), ./scripts/sync-codex.sh (all mirror guards green incl. sync-codex.sh:1654 usage.md slash-token guard)
- PRs: