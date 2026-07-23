---
satisfies: [R2, R3, R12, R13]
---
# fn-130-reached-path-skill-prompt-optimization.2 Consolidate copy-mode version drift contract

## Description
Replace the duplicated setup-version ceremony in 18 lifecycle skills with the parent spec version contract: one concise copy-mode instruction in Plan, no runtime preflight in other skills, and Setup as sole owner of setup-mode/snippet integrity. Update executable and written documentation in the same task. This is the one fleet-wide semantic mutation applied before structural routing experiments.

**Size:** M (broad but mechanical fan-out; one semantic contract)
**Files:** the Pre-check sections in `plugins/flow-next/skills/{flow-next-audit,flow-next-capture,flow-next-interview,flow-next-land,flow-next-make-pr,flow-next-map,flow-next-memory-migrate,flow-next-pilot,flow-next-plan,flow-next-prime,flow-next-prospect,flow-next-qa,flow-next-ralph-init,flow-next-resolve-pr,flow-next-strategy,flow-next-sync,flow-next-tracker-sync,flow-next-work}/SKILL.md`; `plugins/flow-next/tests/test_precheck_mode_contract.py`; `agent_docs/setup-modes.md`; `agent_docs/optimizing-skills.md`; `README.md`; `plugins/flow-next/docs/troubleshooting.md`; `CHANGELOG.md`; corresponding Codex mirror; flow-next.dev install/setup/troubleshooting sources.

### Frozen interactive contract
When copy-mode metadata and installed-plugin evidence both exist and differ, Plan asks exactly:

`Local Flow-Next copy v<X> differs from plugin v<Y>. Refresh before planning?`

Options and continuation are frozen:
1. `Refresh now (Recommended)` — stop cleanly; tell the user to run `/flow-next:setup`, then rerun Plan. Plan never invokes Setup and never resumes the same invocation.
2. `Continue this run` — emit one warning and continue planning. Write no acknowledgement field.

Canonical Plan uses `AskUserQuestion`; `scripts/sync-codex.sh` applies the repository's existing numbered plain-text fallback in the Codex mirror. Autonomous, Ralph, and receipt-driven paths emit one warning per invocation and continue. Match, plugin mode, or unavailable/missing comparison evidence is silent.

### Approach
- Run the frozen `B0` version matrix from task 130.1 against the current ceremony.
- Apply only the version mutation and produce `V1/B1`: hash every canonical/mirror prompt file and rerun all cluster baselines after version removal. Later tasks must verify their input hash against `B1` and compare structural candidates to `B1`, never directly to `B0`.
- Keep one Plan instruction implementing the exact question/options/continuation above.
- Remove lifecycle writes/reads of `version_ack` and `snippet_ack`; tolerate old metadata without migration. Do not alter Setup mode plumbing or snippet marker validation inside Setup.
- Assert all other skill roots contain no legacy precheck ceremony. Direct non-Plan invocations no longer detect drift by design.
- Remove universal-warning claims from repo/site docs while preserving the copy-mode rule: rerun setup after plugin updates.
- Correct optimization promotion prose to `Unreleased` plus later batched release; no version manifest edits.

### Frozen fixtures
- copy match; interactive copy mismatch choosing Refresh; interactive mismatch choosing Continue; autonomous, Ralph, and receipt-path mismatch; missing `.flow/meta.json`; missing plugin version; plugin mode; missing jq; stale acknowledgement fields.
- Claude canonical and Codex mirror; static environment-root cases for Droid/Cursor/Grok where a live host cannot expose the comparison path.

### Investigation targets
**Required**
- `plugins/flow-next/tests/test_precheck_mode_contract.py:76-131` — current executable contract to supersede deliberately.
- `agent_docs/setup-modes.md:31-39` — stale contributor description of the ceremony.
- `README.md:127-133` and `plugins/flow-next/docs/troubleshooting.md:5-14` — current user-facing warning claims.
- `plugins/flow-next/skills/flow-next-plan/SKILL.md` — sole retained consumer.
- `plugins/flow-next/skills/flow-next-setup/workflow.md` — setup-mode/snippet ownership that must remain.

**Optional**
- fn-95, fn-99, and fn-121 specs — historical rationale, superseded only for lifecycle prechecks.

## Acceptance
- [ ] `B0` and post-version `V1/B1` matrices are recorded with canonical/mirror prompt hashes; structural tasks fail closed if their input differs from `B1` and compare candidates against `B1`.
- [ ] The exact mismatch question, both option labels, clean-stop/rerun behavior, continue-once warning, no acknowledgement write, and autonomous-once warning are asserted on canonical and Codex paths.
- [ ] Canonical and mirrored Plan carry exactly one concise copy-mode contract; no other lifecycle skill contains the legacy precheck or acknowledgement ceremony.
- [ ] Setup mode, setup-version stamping, snippet marker replacement, and legacy metadata tolerance remain functional.
- [ ] `test_precheck_mode_contract.py` asserts the new Plan-only contract and fails if the fleet ceremony regrows.
- [ ] README, repo troubleshooting/setup-mode docs, flow-next.dev install/setup/troubleshooting, optimization guidance, and `CHANGELOG.md` `Unreleased` agree; no universal-warning claim remains.
- [ ] No hook, new flowctl helper, config key, version bump, or release is introduced.
- [ ] `scripts/sync-codex.sh` runs twice idempotently and focused precheck/setup/mirror tests pass.

## Done summary
Replaced the duplicated lifecycle setup-version ceremony with one concise Plan-only copy-mode contract across canonical and Codex surfaces. Interactive Plan now offers the frozen refresh/continue choice; autonomous, Ralph, and receipt-driven Plan paths warn once and continue; all other lifecycle skills perform no version preflight. Setup remains the sole owner of setup mode, snippet integrity, and setup-version stamping. Updated repository and flow-next.dev guidance, corrected optimization promotion policy to Unreleased plus batched releases, made immutable B0 validation commit-sourced, and froze 117 V1/B1 manifests from commit 8ed71a73ccc593a8a018dcdb805a86f396dcf76f with a fail-closed per-cluster input checker.
## Evidence
- Commits: 8ed71a73ccc593a8a018dcdb805a86f396dcf76f, b5a8a42b
- Tests: python3 -m unittest -q test_precheck_mode_contract test_setup_mode_stamp test_setup_snippet_lockstep test_setup_cursor_host test_setup_grok_host test_token_budgets test_skill_prose_diet test_pilot_backlog_mirror_safety test_reached_path_harness (128 passed), python3 optimization/reached-path/run_eval.py --self-test (passed), python3 optimization/reached-path/run_eval.py --validate-b0 (117 manifests passed), python3 optimization/reached-path/run_eval.py --validate-b1 (117 manifests passed), python3 optimization/reached-path/run_eval.py --check-b1-input <each of 11 clusters> (passed), ./scripts/sync-codex.sh twice (idempotent), bun run build in flow-next.dev (Astro check/build passed), git diff --check (passed)
- PRs: