# fn-92-opinionated-prime-mode-project-type.4 Eval fixtures + expectation harness skeleton (R19 red)

## Description
Eval skeleton first (design-before-build): fixtures + expectation harness, landing red/pending.

**Size:** M | **Files:** `optimization/prime/` (new dir: fixture builders + expectation table + runner), `plugins/flow-next/tests/test_prime_eval.py` (thin unittest wrapper)

### Approach
- Fixture builders create temp git-init repos (NEVER in-tree .git dirs - test_scout_fallback_contract.py L20-25 gotcha): workspace-parent (25+ sibling repos, shared org), tier-a plain siblings, tier-b home base (parent manifest + compose), greenfield, greenfield-x-constellation, worktree-sibling (git worktree of the same repo).
- Expectation table as data (per-row iteration per memory: tests drive source-of-truth tables): fixture/repo -> expected lifecycle, topology bits, band, shapes, and the substance true-positive + no-false-positive sets from the spec's eval-validation section (echo string-literals dropped, fixture-corpus env reads excluded, per-package .env.example found, extraction-failure flagged).
- Runner harness in optimization/prime/ per the reveval precedent; unittest wrapper marks pending/skip until task 9 flips it.

### Key context
- unittest, not pytest; CI = python -m unittest discover, 3-OS matrix - keep builders portable.
- This lands BEFORE the skill rewrite per fable-review-evals discipline; task 9 makes it green.
## Acceptance
- [ ] Fixture builders produce all six synthetic shapes in tmpdirs via git init (R19)
- [ ] Expectation table covers classification axes + substance TP/no-FP sets as data rows
- [ ] unittest wrapper present, pending/skipped cleanly (suite stays green), portable on 3-OS
- [ ] No in-tree nested .git; no fixture depends on the host workspace layout
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
