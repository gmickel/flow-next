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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
