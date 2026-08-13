---
satisfies: [R6]
---
# fn-190-flowctl-startup-importable-entry-for.3 Measurement record, CHANGELOG entry, and the full gate

## Description
Close the change out: the recorded measurement, the outcome-first CHANGELOG entry under `## Unreleased`, and the full gate including the OS smoke matrix. No version bump (batched release decision per the project instruction file).

**Size:** S
**Files:** `CHANGELOG.md`; `plugins/flow-next/docs/flowctl.md` (only if task .2 left a gap); task summaries
**Touches:** [CHANGELOG.md]

### Approach
- CHANGELOG entry under `## Unreleased`, in the register documented in `agent_docs/releasing.md`: lead with what got faster for whom (the local gate, worker waves, autonomous ticks - and consumers, since plugin mode PATH-resolves the same wrapper), then the mechanism, then the numbers as outcomes. State the bound honestly: this is per-invocation startup, NOT an end-to-end or agent-speed claim.
- Include the deliberate non-gain: read-only install dirs stay at today's speed by design.
- Verify prompt-pin hashes are unchanged (`test_prompt_text_pinned`) - nothing in this spec should move an embedded prompt constant, so an unchanged hash is the proof, not a formality.
- Full gate: `python3 scripts/run_tests_parallel.py` (capture the exit code directly, never via a pipe) plus `uvx ruff@0.16.0 check .`. Confirm the tree is clean after a warm run so no `__pycache__` leaks into the commit.

### Acceptance
- [ ] `## Unreleased` CHANGELOG entry present, outcome-first, with the startup numbers and the explicit no-end-to-end-claim bound; no version bump
- [ ] `test_prompt_text_pinned` green with unchanged hashes
- [ ] Full suite + ruff green, exit codes captured directly; OS smoke matrix green in CI
- [ ] Working tree clean after a warm flowctl run (no untracked `__pycache__`)

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
