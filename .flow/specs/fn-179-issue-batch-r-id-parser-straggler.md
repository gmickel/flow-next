# Overview

Six small, fully-evidenced defects from the sn-furali 2026-08-08 report batch (#300, #303, #305, #306, #308, #316). Every one has a minimal repro verified against 3.16.3 and re-verified against current main this session. Minimal-path fixes only; each issue's own suggested fix is the accepted design unless noted.

**Evidence standing: reporter-supplied repros driven against released tags; all confirmed present on main at 6a187734. No new evals.**

## Goal & Context

Close the five mechanical bugs and one record-integrity gap in one pass: the third R-ID parser straggler, the silent acceptance-criteria drop, the case-insensitive SPEC.md miscount, the platform misdetection on our primary host, the `--select` slot-resolution hole, and the claim repair-vs-takeover conflation.

## Architecture & Data Models

All changes are point fixes in existing code paths:

1. **#300:** `_PR_COGNITIVE_AID_RID_RE` gains the `[a-z]?` suffix class, matching what #147/#152 made canonical elsewhere: `^R[1-9][0-9]*[a-z]?$`. Both call sites (sources[].ref and rIds[]) covered by the one constant.
2. **#303:** `_export_parse_acceptance_criteria` (a) recognizes the token when the bold run continues past it (title form `**R14 - title**` and parenthetical form `**R15 (note):**`), anchoring on the token and stopping at the first `**` or `:` boundary; (b) captures wrapped criterion text until the next bullet or blank line instead of end-of-line; (c) adds a residue count to the payload: bullets in the section matching `- **R` that did NOT parse. The residue counter is the durable half - it stays correct for the next unseen shape.
3. **#305:** setup workflow.md HITS formula counts distinct files by inode, not echoed argument names (portable stat per candidate; `stat -f %i` BSD / `stat -c %i` GNU). Branch bodies unchanged.
4. **#306:** setup workflow.md Step 0 platform cascade keys the Claude Code branch on `CLAUDECODE=1` (existing idiom, used by the codex-delegation guard) instead of `CLAUDE_PLUGIN_ROOT`, which never reaches a plugin skill's Bash env. Droid and Cursor branches untouched.
5. **#308:** `tracker resolve --select` runs the normal assignment over the remaining slots after merging the selection and persists the union (issue's option 1). The selection is a tiebreak for one ambiguous slot, not a reason to skip the others; `missing_required` then flows through the existing `_assignment_to_data` CONFLICT guard.
6. **#316:** `flowctl start <id> --reclaim` rewrites the claimant deliberately with a repair-flavored claim note (e.g. `Reclaimed from <identity> (identity repair)`), so `--force` keeps its takeover meaning. Flag on the existing verb, no new command.

## Edge Cases & Constraints

- #303: `R5a` suffix parsing is the positive control separating this from #147; keep a fixture asserting it.
- #305: fix must work on both BSD and GNU stat; workflow.md prose is fixture-tested (host-detection tests show the pattern) and fn-160.3 will later move this prose - land the fix so the split carries it.
- #306: add a `CLAUDE_PLUGIN_ROOT`-unset / `CLAUDECODE=1` case beside the existing host cases in `tests/test_setup_grok_host.py`-style fixtures.
- #308: never auto-fill the secondary `started` slot (`in_review`); the two-state case genuinely needs the human tiebreak. That design is right and stays.
- #316: no validation of which identities are legitimate (governance belongs to the consuming repo); no sibling-identity warning heuristic.
- workflow.md changes require `./scripts/sync-codex.sh` twice + mirror diff committed; flowctl.py changes require dual-copy propagation + `test_prompt_text_pinned` awareness.

## Acceptance Criteria

- **R1:** `pr-cognitive-aid validate` accepts `R4a`-form ids at both call sites; `R4ab` and `R-4` stay rejected. Errors: none beyond existing messages.
- **R2:** The acceptance-criteria parser returns title-form and parenthetical-form bullets with correct ids and full text, and wrapped criteria keep their continuation lines. The issue #303 five-bullet repro parses 5 of 5.
- **R3:** The export payload carries a residue count of `- **R`-shaped bullets that did not parse; non-zero residue is visible to make-pr consumers. Errors: residue never aborts the export.
- **R4:** On a case-insensitive filesystem with a single `SPEC.md`, setup discovery takes the HITS=1 branch and prints no both-files warning; case-sensitive dual-file repos still take HITS=2.
- **R5:** On Claude Code, the setup platform cascade classifies `claude-code` via `CLAUDECODE`, with a fixture covering the plugin-skill env (no `CLAUDE_PLUGIN_ROOT`). Droid/Cursor/codex fixture outcomes unchanged.
- **R6:** After `tracker resolve --select <slot>=<id>`, all unambiguously resolvable REQUIRED slots are filled and persisted; a REQUIRED-incomplete result is a CONFLICT, never a fresh stamp. The issue #308 five-step repro ends with a complete map at step 3.
- **R7:** `flowctl start <id> --reclaim` rewrites the claimant with a repair claim note distinct from the `--force` takeover note; `--force` behavior unchanged.
- **R8:** Mirrors, dual flowctl copies, docs touched where user-facing behavior changed, CHANGELOG Unreleased entries crediting @sn-furali per issue. Errors: parity red blocks merge.

## Boundaries

- No new commands; #316 is a flag on `start`.
- No change to the `in_review` never-auto-fill policy (#308).
- No widening of #303 into a general markdown parser; token-anchored recognition plus residue reporting only.
- No headless setup or byte-compare-gate changes (#314 territory, answered separately).
- Version bump deferred to the batched release per CLAUDE.md.

## Decision Context

Issues #305/#306 could have been folded into fn-160 (which splits the same workflow.md prose), but landing them as one-line fixes first means fn-160's split carries corrected prose instead of sequencing bugfixes behind a larger refactor. #316's optional sibling-identity warning was dropped as heuristic creep; the record-integrity half is the part prose cannot fix. All six fixes take the reporter's own suggested design where one was offered, because each was verified correct against main this session.
