---
satisfies: [R13]
---
# fn-123-cursor-first-class-experience-team.5 print-then-ask read-back contract (capture + interview)

## Description
Repair long approval read-backs (R13). Print-then-ask contract: skills that show a draft/diff for approval print the FULL markdown as an ordinary assistant message first, then issue a short AskUserQuestion (one-line pointer + [inferred] tally/warnings + options only - never embedded multi-paragraph drafts, which render as collapsed plain text in ask bodies). Apply to flow-next-capture (SKILL.md, workflow.md Phase 4, phases.md) including every edit cycle (reprint revised draft before each short ask) and rewrite-mode diffs; apply the same contract to flow-next-interview decision-entry and spec write-back approvals (remove the ambiguous "inline in the question or preceding message" allowance). Autofix paths unchanged (non-interactive, --yes contract intact). Add `plugins/flow-next/tests/test_readback_ask_contract.py` (prose-contract test over canonical + codex-mirror forms, rejecting the old long-question wording); regenerate mirror.

## Acceptance
- Capture interactive read-back: full draft (or rewrite diff) printed as normal markdown BEFORE the ask; the ask contains only pointer + tally + approve/edit/abort (and consider-split when fired).
- Edit cycles reprint the full revised draft before each short ask.
- Interview decision-entry + write-back approvals follow the same print-then-ask contract.
- Autofix remains non-interactive with the --yes contract; no new blocking questions.
- `test_readback_ask_contract` green over canonical and mirror; sync-codex twice-idempotent.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
