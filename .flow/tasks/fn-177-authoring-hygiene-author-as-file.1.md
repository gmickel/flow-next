---
satisfies: [R1, R2, R3]
---
# fn-177-authoring-hygiene-author-as-file.1 Transplant author-as-file + tiered testing, author examples-are-exhaustive, regen mirrors

## Description
Apply `c354e78f` (plan steps.md author-as-file) and `570b2fa7` (worker.md tiered testing) - both verified to apply cleanly on main via cherry-pick - author the examples-are-exhaustive template block fresh, regenerate mirrors.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-plan/steps.md`, `plugins/flow-next/agents/worker.md`, `plugins/flow-next/templates/spec.md`, `.flow/templates/spec.md` (copy), `plugins/flow-next/codex/**` (regenerated)

### Approach
- `git cherry-pick -n c354e78f && git cherry-pick -n 570b2fa7` applies both payloads.
- **Correction to c354e78f (Route A hunk):** the tested line `flowctl spec cat <id> --plan > ...` names a verb that does not exist. Replace that invocation with `"$FLOWCTL" cat <id> > "${TMPDIR:-/tmp}/flow-plan-body-<suffix>.md"` - same intent (dump the current spec body to a file for Edit-based revision), real verb.
- **templates/spec.md, fresh block (R2):** add an EXAMPLES ARE EXHAUSTIVE comment block after the SCOPE DISCIPLINE comment block, in the same voice: when a spec shows an output/event/API shape, the fields shown ARE the contract - implementations must not add fields to a shown shape; if a field is intended, show it. Absolutely NO length/byte-budget language.
- Verify R3's gate integrity: the tiered-runs bullet names the pre-edit baseline and pre-review/pre-commit verification as where the FULL suite runs - the surrounding worker.md gate prose (Phase 1 baseline, Phase 3/4 verification) must remain textually unchanged.
- Copy updated `plugins/flow-next/templates/spec.md` over `.flow/templates/spec.md`.
- `./scripts/sync-codex.sh` TWICE (second run no diff); verify both worker bullets survive in `codex/agents/worker.toml` and the steps.md mirror carries the Write-tool prose.
- No Claude-native-only assumptions beyond the Write/Edit tool names, which are the canonical cross-host vocabulary (sync-codex leaves Write/Edit as-is; Cursor/Droid understand them).

### Investigation targets
**Required** (read before editing):
- `git show c354e78f` and `git show 570b2fa7` - the payloads
- `plugins/flow-next/skills/flow-next-plan/steps.md` Step 5 (Route A/B compose sites)
- `plugins/flow-next/agents/worker.md` Rules list + Phase 1/3 gate prose
- `plugins/flow-next/templates/spec.md` comment blocks before the title

### Acceptance
- [ ] No heredoc document composition remains in the plan skill; Write/Edit path present; ~10-line heredoc exception stated; phantom verb corrected (R1)
- [ ] Template carries examples-are-exhaustive with zero budget language (R2)
- [ ] Worker rules carry both bullets; baseline/pre-review/pre-commit full-suite gate prose textually intact (R3)
- [ ] sync-codex.sh x2 idempotent; codex mirror diff committed with the canonical change; .flow/templates/spec.md refreshed
- [ ] Focused suite green: `cd plugins/flow-next/tests && python3 -m unittest test_dogfood_template_parity test_template_canonical test_review_prompt_constraints -q`

## Acceptance
- [ ] TBD

## Done summary
Transplanted c354e78f (author-as-file across the plan skill's Route A/B compose sites and task-batch compose) and 570b2fa7 (worker test-mass discipline + tiered runs bullets; baseline/pre-review/pre-commit full-suite gate prose verified textually intact). Authored the EXAMPLES ARE EXHAUSTIVE template comment fresh (contract language, zero budget language). Two corrections to tested wording, both recorded in the commit: phantom `spec cat --plan` verb -> real `cat`; stale Route B scaffold heredoc framing reframed to Write-tool (the tested commit missed its own rule there). Mirrors idempotent; template copy refreshed; focused suite green.
## Evidence
- Commits: 1d3731e9
- Tests: python3 -m unittest test_dogfood_template_parity test_template_canonical test_review_prompt_constraints test_prompt_text_pinned test_review_prompt_template_parity -q, ./scripts/sync-codex.sh x2 idempotent, uvx ruff@0.16.0 check .
- PRs: