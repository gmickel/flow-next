# fn-167-bugbot-pre-push-review-stage.4 Prebuild the Bugbot smoke fixtures (agent-run; minimizes the manual session)

## Description
Prebuild everything the human-run smoke (task .1) needs, so the manual Cursor session is reduced to: enable Bugbot, run /review-bugbot, push/open PRs per checklist, record observations, revert the toggle.

**Size:** S
**Files:** `scratch/bugbot-smoke/` on fixture branches only - NEVER on main; no real code touched.

### Approach
- Fixture location `scratch/bugbot-smoke/` at repo root: outside every CI path filter (test-flow-next triggers on plugins/**, workflow file, installers) so smoke PRs run zero CI legs and observations stay clean; outside ruff's scope concerns (JS fixture).
- Branch `fn-167-smoke/bugbot-target` off main: one commit adding a small JS module with 2-3 deliberate, obvious-to-a-reviewer bugs (the kind Bugbot visibly flags: unawaited promise in a loop, == NaN comparison, off-by-one slice) + a README declaring it a deliberate-bug fixture for fn-167 (so no future reader 'fixes' it).
- Branch `fn-167-smoke/bugbot-dedup` off the same base carrying the IDENTICAL patch (cherry-pick, same patch-id - verify with `git patch-id` on both) for the dedup + draft-PR probes.
- `RUNBOOK.md` in the fixture dir: task .1's steps condensed to a numbered checklist with exact commands, the settings to record, which branch serves which probe, the further-commit probe snippet, and the revert-Bugbot reminder.
- Push both branches. Do NOT open PRs - PR creation is an observation step that depends on dashboard settings state.

### Acceptance
- [ ] Both branches pushed; `git patch-id` identical across them
- [ ] Fixture touches only scratch/bugbot-smoke/; no CI workflow triggers on the diff (verify path filters)
- [ ] RUNBOOK.md covers all three probes from task .1 (dedup, findings visibility, draft behavior) + settings record + revert step
- [ ] Task .1 updated to point at the runbook as its entry point

## Acceptance
- [ ] fixture branches pushed with identical patch-ids
- [ ] zero CI triggers on the fixture diff
- [ ] runbook covers all three probes + revert
- [ ] task .1 references the runbook

## Done summary
Prebuilt the fn-167 manual smoke: fixture branches fn-167-smoke/bugbot-target and fn-167-smoke/bugbot-dedup pushed with byte-identical patch-ids (6c49a82a), deliberate-bug JS fixture outside every CI path filter, RUNBOOK.md condensing task .1 to 7 steps covering all four probes (findings visibility, dedup, draft behavior, run-once interaction) plus settings record and revert. Task .1 re-pointed at the runbook as entry.
## Evidence
- Commits: c683b8ca51df52aec0660b0737b6c745607db599
- Tests: git patch-id parity: 6c49a82a on both branches, CI path-filter check: scratch/ matches no workflow trigger
- PRs: