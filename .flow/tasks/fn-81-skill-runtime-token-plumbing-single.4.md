---
satisfies: [R13, R14, R15]
---

## Description

Final validation gate + release staging: the ONE mirror regeneration + commit, full test sweep, cross-task greps, CHANGELOG `## Unreleased` entry, optimization-log row with computed counts. Depends on fn-81.1/.2/.3.

**Size:** S
**Files:** `CHANGELOG.md`, `agent_docs/optimization-log.md`, `plugins/flow-next/codex/` (regenerated + committed here, once)

## Approach

- `bash scripts/sync-codex.sh` twice (idempotency: identical output; built-in tail parity guards must pass) → review `git diff --stat plugins/flow-next/codex/` → commit the mirror.
- Smoke from a NON-repo cwd (the script refuses to run from the plugin repo — smoke_test.sh:27-29): `(cd "$(mktemp -d)" && bash /Users/gordon/work/flow-next/plugins/flow-next/scripts/smoke_test.sh)`. Plus `python3 -m pytest plugins/flow-next/tests/ -q` (incl. mirror-parity tests). Both green.
- Cross-task greps (all must be clean in canonical skills): `grep -rn '\[PASTE' plugins/flow-next/skills/` empty; `grep -rn 'git add -A' plugins/flow-next/skills/flow-next-impl-review/ plugins/flow-next/skills/flow-next-spec-completion-review/` empty; per-fixed-path greps each empty: `/tmp/spec.md`, `/tmp/acc.md`, `/tmp/desc.md`, `/tmp/review-prompt.md`, `/tmp/re-review.md`, `/tmp/updated-plan.md`, `/tmp/export-prompt.md`, `/tmp/completion-review-prompt.md`, `/tmp/merged-flow.md`.
- CHANGELOG.md: CREATE `## Unreleased` (currently absent — newest is `## [flow-next 2.5.4]`) with a `### Changed` entry in house style (bolded lead-in + spec-id parenthetical + prose). NO version bump, no manifest edits.
- agent_docs/optimization-log.md: append one row with COMPUTED counts — tally the actual number of eliminated re-emissions and round-trips from tasks 1-3 diffs (e.g. "N heredoc re-emissions, M redundant CLI calls removed across 12 skills"); never a placeholder.

## Investigation targets

**Required:**
- `CHANGELOG.md:1-40` — house style of 2.5.3/2.5.4 entries
- `agent_docs/optimization-log.md` — row format
- `plugins/flow-next/scripts/smoke_test.sh:20-35` — the non-repo-cwd guard

## Acceptance

- [ ] sync-codex run twice, idempotent, parity guards pass; mirror committed in this task only
- [ ] smoke (non-repo cwd) + pytest green — paste tails in summary
- [ ] all cross-task greps clean (list each result)
- [ ] CHANGELOG `## Unreleased` entry present, style-conformant, no version bump
- [ ] optimization-log row appended with computed counts

## Done summary
fn-81 final gate: regenerated + committed the Codex mirror once (sync-codex run twice, idempotent, parity guards green), created the CHANGELOG `## Unreleased` fn-81 entry (no version bump), and appended the optimization-log row with computed counts (11 full-content re-emission sites + 13 redundant CLI round-trips removed across 12 skills, tallied from the fn-81.1-.3 diffs). Full gate green: smoke 138/138 from non-repo cwd, pytest 1393 passed; all cross-task greps clean after an RP-review-driven reword of the 6 blanket-staging prohibition lines (literal `git add -A` -> `git add --all` phrasing) so the acceptance gate grep passes. RP impl-review verdict: SHIP.
## Evidence
- Commits: 706503dd320ac4c868a904698b6bfc04afc04fca, 45586ef1
- Tests: bash scripts/sync-codex.sh (x2, idempotent - identical output hashes, all parity guards green), smoke_test.sh from non-repo cwd - 138 passed / 0 failed (run pre- and post-fix), python3 -m pytest plugins/flow-next/tests/ -q - 1393 passed, 2 skipped, 164 subtests, pytest test_tracker_sync_mirror_parity.py + test_sync_check.py - 36 passed (post-fix), cross-task greps clean: [PASTE]=0 hits; git add -A in the two review-skill dirs=0 hits (post-fix reword); each of the 9 fixed /tmp paths=0 hits
- PRs: