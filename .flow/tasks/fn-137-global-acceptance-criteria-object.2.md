---
satisfies: [R2, R4]
---
# fn-137-global-acceptance-criteria-object.2 Completion-review integration + compliance in receipts

## Description
Completion review applies existing criteria; receipts carry per-criterion compliance.

**Size:** M

**Files:** flowctl.py completion-review prompt templates (+ any rp/host prose line), receipt write + validation, parser extension (fn-136 infrastructure - this spec assumes fn-136 landed; if sequencing flips, this task ships the minimal shared block parser), tests + fixtures.

### Approach
- Prompt: when criteria exist, inject a compact criteria block (user content) + an Output Format addition mandating a `## Global criteria` section: per criterion `G<N>: met|violated|n/a - <note>`; violations must ALSO appear as normal findings (severity per reviewer judgment) so the fn-136 findings channel stays the single findings surface.
- Receipt: `criteria: [{id, status, note?}]` parsed deterministically (extend the fn-136 parser); degrade-to-absent.
- Token discipline: injection gated on file existence (zero-cost-absent test from .1 goes green); template delta measured.
- Fixtures: real-shaped completion-review outputs with criteria sections.

## Acceptance
- [ ] All completion-review backends apply criteria + receipts carry compliance; degrade-to-absent (R2).
- [ ] Zero-cost-absent proven; template deltas measured; sync-codex idempotent if prose touched (R4).

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
