---
satisfies: [R1, R2, R11, R12]
---

## Description
New reference files: classification.md + stacks.md.

**Size:** M | **Files:** `plugins/flow-next/skills/flow-next-prime/classification.md`, `plugins/flow-next/skills/flow-next-prime/stacks.md` (both new, flat skill-root siblings)

## Approach
- classification.md: the five axes verbatim from spec Architecture Phase 0.5 - lifecycle signals, TWO-BIT topology (monorepo bit with the cross-referenced-manifests rule; constellation bit with tiers a/b/c incl. prose cross-repo references and the workspace-parent dampener), size bands with the FULL exclusion list (tool-managed dirs, vendored, fixtures, hash-duplicates, script-regenerated, legacy snapshots), manifest-gated stacks with LOC-histogram corroboration, multi-valued delivery shape with the ordering rule (markers first, denominators recomputed once - resolution 9).
- Per-axis confidence fields (never punctuation); thresholds as a tunable table; the orthogonal `assessment_scope` field (repository | workspace-member | constellation-home-base) with evidence + playbook routing (final review round).
- Edge-case ladder per resolution 8: unborn HEAD, non-git dir, worktree-sibling exclusion (gitdir resolves to same repo), cwd-below-toplevel member detection, portable timeout pattern (no bare timeout binary), POSIX classes.
- `--classify-only` output contract per resolutions 7+19: the deterministic axes emit from `flowctl prime classify --json` (this task specifies the emitter JSON schema in classification.md; the flowctl implementation itself lands in task 4); the skill layer adds shape/confidence/asks.
- stacks.md: 15+ rows per the spec matrix (TS/JS through COBOL) with detect / verify / LSP / map / gotchas columns; the map column gates the DE7 `/flow-next:map` suggestion; LEG-pattern instantiations live in rows, never in skill logic; unknown-stack degrade line.

## Key context
- Pattern/instantiation discipline is load-bearing (spec): adding a stack = adding a row.
- No scout-dispatch text in these files (sync-codex sed scope, resolution 12).

## Acceptance
- [ ] Five axes fully specified with signals, thresholds table, confidence fields, exclusion lists (R1)
- [ ] Workspace dampener + worktree-sibling exclusion + tier-c prose references present; edge ladder covers no-git/unborn/subdir/portability (resolution 8)
- [ ] --classify-only block schema pinned as the `flowctl prime classify --json` emitter contract (resolutions 7/19)
- [ ] stacks.md >= 15 rows incl. Delphi/VB6/COBOL/PLSQL with honest none-practical cells; DE7 map gating stated (R11)
- [ ] Zero scout-dispatch or bare ask-tool tokens in either file (grep, executable-context scoped)

## Done summary
Added two new prime skill reference files (flat skill-root siblings, matching pillars.md/remediation.md): classification.md pins the five classification axes (lifecycle, two-bit topology with workspace dampener + tier-c prose refs, size band with the full exclusion list, manifest-gated stacks, multi-valued delivery shape), a tunable thresholds table, per-axis confidence, the orthogonal assessment_scope field, the resolution-8 edge-case ladder, and the `flowctl prime classify --json` emitter schema + `--classify-only` block contract (resolutions 7/19/21b). stacks.md ships the 15-row matrix (TS/JS through COBOL) with detect/verify/LSP/map/gotchas, honest none-practical cells for Delphi/VB6/PowerBuilder/COBOL/PL-SQL, the DR7 dev-MCP gate, per-stack LEG1-LEG9 instantiations as data, DE7 /flow-next:map gating on the Map column, and the unknown-stack generic degrade. Codex mirror regenerated via sync-codex.sh.
## Evidence
- Commits: 6bfcabda7ca0011e05810ee78589eb4067655e75
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' (1581 tests, OK skipped=2, exit 0 - baseline green, post-edit green), bash scripts/sync-codex.sh (all validation gates pass; mirror regenerated), grep guard: zero AskUserQuestion/scout-dispatch tokens and zero em/en dashes in both new files
- PRs: