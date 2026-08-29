# fn-209-no-plan-work-route-tool-permission-audit.6 Finalization: mirror regen, manifest, changelogs, What's-new, full gate

## Description
Single finalization task (per the folding rule): regenerate the mirrors and manifest that tasks 1-5 deliberately left uncommitted so their Touches stayed disjoint, land the user-facing release notes, and run the full gate.

**Size:** S-M
**Files:** `plugins/flow-next/codex/**` (regen), `plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json` (regen), `plugins/flow-next/docs/README.md`, `CHANGELOG.md`
**Touches:** [plugins/flow-next/codex/**, plugins/flow-next/scripts/flowctl_tracker/MANIFEST.json, plugins/flow-next/docs/README.md, CHANGELOG.md]

### Approach
- `./scripts/sync-codex.sh` TWICE (idempotency; hard-fail guards are load-bearing - fix content or extend a transform, never relax a guard; the concrete new one is the fn-208.2 guard at `scripts/sync-codex.sh:609-620` asserting the `FORBIDDEN:`/`TIMEBOX:` literals survive the SECTION3C heredoc, now :502-588). Then VERIFY the changed literals actually landed in the mirror files by grep - never infer propagation from a green exit (memory: canonical-3c-edits-vanish-from-codex-2026-08-28). Commit the mirror diff.
- `python3 scripts/gen_tracker_manifest.py` (flowctl.py changed in task 4).
- docs README "What's new" entry (bold name - paragraph - Enable - Details links shape), ABOVE the 4.8.0 autonomy-hardening entry at :84 (newest-first).
- CHANGELOG: `## Unreleased` no longer exists (fn-208 shipped as `## [flow-next 4.8.0] - 2026-08-29`) - CREATE the section above the 4.8.0 heading, user-outcome-first per agent_docs/releasing.md; the flow-next.dev changelog is an EXPLICIT post-merge hold per the spec's AC preamble - flag it prominently in the done summary (never attempt it from this checkout); the maintainer stages it in the docs-site repo.
- Verify make-pr's coverage path on a no-plan-shaped spec (single task, satisfies = all R-IDs) renders without the declared-coverage abort - a read-through of `flow-next-make-pr/workflow.md` qualifier clauses plus one dry-run if cheap.
- Full gate: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .` - both green before handoff.

### Investigation targets
**Required:**
- `scripts/sync-codex.sh` guard output on first run - drives any transform extensions
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md` - declared-coverage qualifier clauses

### Acceptance
- [ ] sync-codex run twice, idempotent, guards green, mirror diff committed
- [ ] tracker manifest regenerated and committed
- [ ] What's-new + CHANGELOG Unreleased entries staged (no version bump); docs-site changelog flagged in done summary
- [ ] make-pr no-plan coverage path verified (no abort)
- [ ] full suite + ruff green
### Acceptance
- [ ] TBD

### Done summary
TBD

### Evidence
- Commits:
- Tests:
- PRs:
## Acceptance
- [ ] TBD

## Done summary
Finalized fn-209: regenerated the codex mirror (4 sync runs — 2 extra because the new What's-new entry lands in the mirrored docs/README.md — all idempotent, guards green, propagation grep-verified including the new no-plan-route.md codex twin), regenerated the tracker manifest, staged the release notes (CHANGELOG `## Unreleased` Added/Fixed pair above 4.8.0; What's-new entry above the 4.8.0 entry, no version bump), applied the conductor-sanctioned P3 sweep (no-plan-route FORBIDDEN non-path clauses + contradicted-signal sentence; five→six at README.md:201, docs README index :28, teams.md:66; ralph.sh ui_complete now prints its optional $1 hint like ui_fail; test_next_zero_task dead helper params trimmed), and verified make-pr's coverage path renders a no-plan-shaped spec (abort keys on undeclared_r_ids; the minted task declares all R-IDs — read-through, dry-run skipped as not cheap in an ephemeral workspace). Full gate green at fbb17655: run_tests_parallel 4511 ran / 0 failures + ruff 0.16.0 clean; green receipt minted.

**POST-MERGE HOLD: the flow-next.dev changelog entry is NOT done and must be staged by the maintainer in the docs-site repo after merge (explicit spec AC preamble; never attempted from this checkout).**

Deviations called out: docs/README.md:96 ("five worked routes", 4.x What's-new entry) and CHANGELOG.md:285 left at "five" — historical release entries per fn209-5's deliberate ruling; the conductor sweep listed :96 as in-Touches, safer path chosen (changing a dated release entry would make it historically wrong). ui_complete fix took the print-optional-$1 branch (preserves the NEEDS_TASKS hint, mirrors ui_fail, 2-line diff).

baseline: green (focused Quick-command suites pre-edit; full-suite receipt check: RUN, no honorable receipt at base)

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
## Evidence
- Commits: e5e5506203f04111fa3540840f62759aa58e6db5, 7e27fcce
- Tests: python3 scripts/run_tests_parallel.py (193 files, 4511 ran, 0 failures; green receipt fbb17655-unittest), uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh && ./scripts/sync-codex.sh (idempotent x2 pairs, guards green), cd plugins/flow-next/tests && python3 -m unittest test_next_zero_task test_reference_encoding_guard -q, bash -n plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh
- PRs:stage: plan-sync - skipped(config: planSync.enabled != true)
