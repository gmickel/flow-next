---
satisfies: [R4, R5]
---
# fn-179-issue-batch-r-id-parser-straggler.2 setup workflow.md: inode-based HITS count + CLAUDECODE platform branch

## Description
Spec fn-179 items 3-4 (#305, #306). Replace the argument-echo HITS formula with a distinct-file count via stat inode (BSD/GNU portable, per-candidate); key the claude-code cascade branch on CLAUDECODE=1 instead of CLAUDE_PLUGIN_ROOT. Add fixtures: case-insensitive single-SPEC.md HITS=1, and CLAUDECODE=1/no-plugin-root classifying claude-code, beside the existing host cases. sync-codex.sh twice, mirror diff committed.

## Acceptance
R4, R5 of the spec. Existing droid/cursor/codex fixture outcomes unchanged; sync-codex idempotent.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
