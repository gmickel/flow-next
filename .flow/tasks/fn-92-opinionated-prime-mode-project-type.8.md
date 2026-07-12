---
satisfies: [R6, R14]
---

## Description
Scout updates + cross-platform audit.

**Size:** S | **Files:** `plugins/flow-next/agents/claude-md-scout.md`, `plugins/flow-next/agents/build-scout.md`, `plugins/flow-next/agents/testing-scout.md`, `scripts/sync-codex.sh` (only if anchors moved), codex mirror (regen)

## Approach
- claude-md-scout: rubric L57-98 replaced with the DC2 substance tells + deductions + the ONE pillars.md scale; keep plain CLAUDE.md spellings so the sync sed (L1410-1417 rename pass) survives; model frontmatter stays a family alias.
- build-scout/testing-scout: add the "when the dispatch provides a stack row, probe its detect/verify entries first" clause; no denominator reuse (contract already forbids).
- Full sync-codex.sh regen + validation; verify the prime-specific sed still matches; grep the four new reference files for forbidden tokens (scoped to executable contexts per the memory trap).

## Acceptance
- [ ] claude-md-scout rubric = substance tells/deductions on the single scale; sed-survivable; family-alias model kept
- [ ] build/testing scouts consume dispatch stack rows; scouts remain read-only
- [ ] sync-codex.sh regen clean, validation guards pass, mirror diff reviewed; forbidden-token greps green

## Done summary
Replaced claude-md-scout's vague quality-signals rubric with the DC2 substance tells + template-tell deductions + length-band review trigger, all graded on the single published X/8 scale (sed-survivable plain CLAUDE.md spellings, family-alias model kept); added the "probe the dispatched stacks.md Detect/Verify entries first" clause to build-scout and testing-scout (read-only, no denominator reuse); regenerated the Codex mirror with full validation green and confirmed the four prime reference files carry no forbidden executable tokens.
## Evidence
- Commits: 322d73fbb9013d409bd2fa2d9914f220336434df
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p 'test_*.py' (Ran 1615, OK skipped=2, baseline green), bash scripts/sync-codex.sh (validation all green; claude-md-scout renamed to agents-md-scout)
- PRs: