# fn-79-task-set-acceptanceset-description-must.1 Normalize task-section content: strip title-like leading H2, demote embedded H2→H3, self-heal layered files

## Description

Implement `normalize_section_content(section, new_content)` in `flowctl.py` and apply it at both task-section write sites: `patch_task_section` (`flowctl.py:5124` — covers `task set-description` / `set-acceptance` via `_task_set_section` `flowctl.py:15597`, and `task set-spec --description/--acceptance`) and `cmd_task_create`'s `--acceptance-file` embed path. Add the self-heal for already-layered files (fn-78 damage shape). Pure stdlib; tests; one docs line + CHANGELOG Unreleased entry.

## Acceptance

- **R1:** A single normalization helper strips a leading H2 only when it matches the target section's **known-title-variant grammar** (exact name; optional legacy `Criteria`/`criteria` word; optional separator-introduced suffix `(`/`—`/`:`/`-`; regex shape `^##\s+Acceptance(\s+[Cc]riteria)?\s*([(:—-].*)?$` — an arbitrary different word like `## Acceptance Tests` is demoted, never stripped) and demotes all remaining H2 headings in content to H3, skipping fenced code blocks (``` and ~~~ fences tracked).
- **R2:** `patch_task_section` applies the helper to `new_content`; `task set-acceptance` / `set-description` / `set-spec --acceptance/--description` produce exactly ONE target section — repeated invocation with the same input is byte-idempotent (no layering).
- **R3:** `task create --acceptance-file` applies the helper before embedding, so an input file beginning with its own `## Acceptance Criteria …` H2 yields a well-formed skeleton with no rogue sibling section.
- **R4:** Self-heal: on a file already damaged in the fn-78 shape (one OR MORE contiguous rogue NON-canonical title-variant spans after the target section — repeated layering stacks several), one `set-acceptance` call replaces the target section AND every contiguous rogue span, leaving one clean section. The fold set excludes the exact canonical heading — a duplicate byte-exact `## Acceptance` still raises the existing duplicate-heading error (R6). Unrelated skeleton sections (`## Done summary`, `## Evidence`, `## Description`) are never folded.
- **R5:** Regression tests (unittest, matching the repo's existing test layout) cover: leading-H2 acceptance file at create; set-acceptance twice (idempotent); embedded H2 demotion; `## ` inside code fences untouched; legacy `## Acceptance criteria` variant; self-heal of a pre-layered file AND a doubly-layered file (two-plus rogue spans); `## Acceptance Tests` demoted-not-stripped negative case; unrelated-section preservation.
- **R6:** Existing error semantics (duplicate canonical heading raises, missing section raises) and JSON output unchanged; full suite green (`python3 -m unittest discover` + the repo's smoke test).
- **R7:** `docs/flowctl.md` gains one line on the normalization under the task set-acceptance/set-description/create docs; CHANGELOG `## Unreleased` entry added. NO version bump.

**Files:** `plugins/flow-next/scripts/flowctl.py`, tests (repo's existing test dir), `plugins/flow-next/docs/flowctl.md`, `CHANGELOG.md`.

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
