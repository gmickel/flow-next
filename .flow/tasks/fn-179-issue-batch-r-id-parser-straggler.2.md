---
satisfies: [R4, R5]
---
# fn-179-issue-batch-r-id-parser-straggler.2 setup workflow.md: inode-based HITS count + CLAUDECODE platform branch

## Description
Spec fn-179 items 3-4 (#305, #306). Replace the argument-echo HITS formula with a distinct-file count via stat inode (BSD/GNU portable, per-candidate); key the claude-code cascade branch on CLAUDECODE=1 instead of CLAUDE_PLUGIN_ROOT. Add fixtures: case-insensitive single-SPEC.md HITS=1, and CLAUDECODE=1/no-plugin-root classifying claude-code, beside the existing host cases. sync-codex.sh twice, mirror diff committed.

Post-capture (3.19-3.21 style wave, see spec Edge Cases): update the Step 0 `### Done when` bullet and the detection-matrix line that name CLAUDE_PLUGIN_ROOT in the same edit; CLAUDECODE=1 is child-inherited, so pair it with a positive discriminator per the workflow's inherited-env doctrine. New fixtures follow the pin-shape rule (agent_docs/adding-skills.md: content + reachability, never bare location). Conduct checklist: agent_docs/conduct/setup.md.

**Files:** plugins/flow-next/skills/flow-next-setup/workflow.md (Step 0 cascade + its Done-when bound + detection-fixtures matrix; SPEC.md discovery HITS) + codex mirror regen; host-detection/discovery fixtures under plugins/flow-next/tests/

## Acceptance
R4, R5 of the spec. Existing droid/cursor/codex fixture outcomes unchanged; sync-codex idempotent.

## Done summary
Setup workflow fixes per fn-179 R4-R5 (#305, #306). SPEC.md discovery HITS now counts distinct files by inode (BSD stat -f %i / GNU stat -c %i, per candidate) - case-insensitive single-file repos take HITS=1 with no bogus both-files warning; branch bodies unchanged. Step 0 cascade detects Claude Code via CLAUDECODE=1 paired with a positive discriminator (.claude-plugin/plugin.json at the resolved PLUGIN_ROOT) and a deliberately LOWERED rung (after Droid/Cursor/Grok, before the codex fallback) because CLAUDECODE is child-inherited and those hosts prove themselves with their own process signals - deviation from the matrix's "precedence unchanged" note, accepted on review with the nesting-edge trade documented. All six prose surfaces naming the old signal changed in one edit; detection matrix items 8-10 added; fixtures follow the pin-shape rule (content + reachability). Conduct checklist setup.md: all 6 items pass; live-setup dogfood replaced by executing the extracted fences under fixtures. Orchestrator follow-up ba41e2df fixed the .4 regression this task's full-suite run caught (synthetic Namespace without reclaim attr).
## Evidence
- Commits: 45469dda
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_setup_spec_discovery_hits test_setup_grok_host + 9 suites -q (144 OK, 1 skip APFS), python3 scripts/run_tests_parallel.py (4385 ran; 4 errors were .4's missing-attr regression, fixed in ba41e2df)
- PRs: