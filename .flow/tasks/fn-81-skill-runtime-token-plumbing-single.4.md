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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
