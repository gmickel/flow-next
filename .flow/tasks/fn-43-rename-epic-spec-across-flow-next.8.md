---
satisfies: [R12]
---

## Description

Rewrite the capture skill (93 epic refs across 3 files) to use spec vocabulary. CLI verb references update from `flowctl epic create + epic set-plan` to `flowctl spec create + spec set-plan`. Source-tagging logic stays unchanged; only the prose around it shifts. The mandatory read-back loop and Phase 0 duplicate detection refer to "epic specs" today -- these become "specs".

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-capture/SKILL.md` (~16 refs)
- `plugins/flow-next/skills/flow-next-capture/workflow.md` (~57 refs)
- `plugins/flow-next/skills/flow-next-capture/phases.md` (~16 refs)

## Approach

- Wholesale "epic" -> "spec" pass on prose. Specifically:
  - "synthesize conversation context into an epic spec" -> "synthesize conversation context into a spec".
  - "creates fresh epics" -> "creates fresh specs".
  - "Capture creates fresh epics; allocate R-IDs sequentially from R1" -> "Capture creates fresh specs; ...".
- CLI examples: `flowctl epic create --title "..." --json` -> `flowctl spec create`, `flowctl epic set-plan` -> `flowctl spec set-plan`.
- Phase 5 ("Write via flowctl"): heredoc commands updated.
- Phase 6 ("Suggested next step"): update `Spec captured at .flow/specs/<id>.md` line (already says "Spec" -- keep).
- Source-tag taxonomy (`[user]` / `[paraphrase]` / `[inferred]` / `[strategy:<track>]`) untouched.
- The mode-detection bash snippet uses `RAW_ARGS` parsing -- no epic-named variables to rename here.
- Argument parsing: `--rewrite <epic-id>` flag -- rename to `--rewrite <spec-id>` in help text and prose; the flag name itself stays `--rewrite` (no need to alias).

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-capture/SKILL.md`.
- `plugins/flow-next/skills/flow-next-capture/workflow.md`.
- `plugins/flow-next/skills/flow-next-capture/phases.md`.

**Optional:**
- The CLAUDE.md "Creating a spec" section references the manual heredoc this skill replaces; cross-check for prose consistency (T11a covers CLAUDE.md edits).

## Acceptance

- [ ] No `flowctl epic create + epic set-plan` references in any capture skill file.
- [ ] No "epic spec" prose in any capture skill file (replaced with "spec").
- [ ] Phase 5 heredoc examples use `flowctl spec set-plan`.
- [ ] Source-tag taxonomy section unchanged.

## Done summary

## Evidence
- Commits:
- Tests:
- PRs:
