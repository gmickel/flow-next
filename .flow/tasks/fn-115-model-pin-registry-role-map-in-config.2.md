# fn-115-model-pin-registry-role-map-in-config.2 Setup refresh ceremony (probe, judge, propose, stamp)

## Description
Setup refresh ceremony: the agent probes, judges, proposes, stamps.

**Size:** M
**Files:** plugins/flow-next/skills/flow-next-setup/workflow.md (+ any split files), tests (prose pins)

### Approach

- Read the fn-115 spec sketch item 3. Add the ceremony to setup (fresh AND re-runs), AFTER the existing config questions: (a) probe installed CLIs for ground truth - cursor-agent --list-models, copilot -p "/model", codex accept-probe (foreground, short timeout, skip a probe when its CLI is absent); (b) the agent judges from its own knowledge which current tiers fit each role (fast/cheap fastJudge, strongest review, value delegate, scout tiers); (c) diff against the config role map and propose via AskUserQuestion (current -> proposed, one-line reason each; sync-codex rewrites the ask); (d) write accepted pins via flowctl config set + stamp models.verifiedAt.
- Skips SILENTLY in autonomous contexts (the same three markers fn-113 uses).
- Failure-feedback prose: the ceremony scans recent review receipts for fallback-ladder activations (model_used differing from the pinned model) and folds pin-keeps-failing -> propose replacement into its judgment; zero new plumbing.
- Offer (not force) updating the CLAUDE.md routing table in the same pass - it is agent-owned prose already.
- Prose-contract test pinning: ceremony present in setup, autonomous skip stated, probe commands named, verifiedAt stamp step present.
- sync-codex x2. NO git commands, no flowctl start/done, no em dashes.

### Acceptance

- [ ] Ceremony prose complete (probe/judge/propose/write/stamp), autonomous-silent, receipt-scan feedback included
- [ ] CLAUDE.md routing-table offer present; prose-contract test pins the pieces
- [ ] Focused: setup prose suites + test_skill_prose_diet.py green; sync-codex idempotent

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
