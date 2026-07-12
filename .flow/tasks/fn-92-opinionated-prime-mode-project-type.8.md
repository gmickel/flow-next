# fn-92-opinionated-prime-mode-project-type.8 Scout updates (claude-md-scout rubric, dispatch context lines) + sync-codex audit

## Description
Scout updates + cross-platform audit.

**Size:** S | **Files:** `plugins/flow-next/agents/claude-md-scout.md`, `plugins/flow-next/agents/build-scout.md`, `plugins/flow-next/agents/testing-scout.md`, `scripts/sync-codex.sh` (only if anchors moved), codex mirror (regen)

### Approach
- claude-md-scout: rubric L57-98 replaced with the DC2 substance tells + deductions + the ONE pillars.md scale; keep plain CLAUDE.md spellings so the sync sed (L1410-1417 rename pass) survives; model frontmatter stays a family alias.
- build-scout/testing-scout: add the "when the dispatch provides a stack row, probe its detect/verify entries first" clause; no denominator reuse (contract already forbids).
- Full sync-codex.sh regen + validation; verify the prime-specific sed still matches; grep the four new reference files for forbidden tokens (scoped to executable contexts per the memory trap).
## Acceptance
- [ ] claude-md-scout rubric = substance tells/deductions on the single scale; sed-survivable; family-alias model kept
- [ ] build/testing scouts consume dispatch stack rows; scouts remain read-only
- [ ] sync-codex.sh regen clean, validation guards pass, mirror diff reviewed; forbidden-token greps green
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
