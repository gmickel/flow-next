---
satisfies: [R1, R2, R7, R13]
---

## Description

Convert capture (Phase 4→5) and interview (Write Refined Spec, all three branches) to the single-emission write pattern: draft body Written ONCE via the Write tool to a literal unique path (the tool render is the user-visible read-back), revisions via Edit tool with a full-file Read before each re-approval, flowctl consumes `--file <literal path>`. Also: collapse interview's duplicate spec fetch; single config-get at capture's tracker gate (R7 capture site). CANONICAL FILES ONLY — mirror regen is fn-81.4's (local sync-codex validation run allowed, mirror tree not committed here).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-capture/workflow.md`, `plugins/flow-next/skills/flow-next-interview/SKILL.md`

## Approach

- **Path-persistence rule (spec §Approach 1):** the draft path is a literal agent-composed path (`${TMPDIR:-/tmp}/flow-capture-draft-<spec-id>-<agent-chosen suffix>.md`), used verbatim in the Write call AND the later `spec set-plan <id> --file <path>` call — never a shell variable across tool calls. mktemp only within a single bash block.
- capture Phase 4.1: build the payload by WRITING the draft to that path; §4.2 `AskUserQuestion` body carries the summary payload (R-ID list, `[inferred]` tally, rewrite diff note) + "full draft in the Write render above (expand if collapsed)"; frozen approve/edit/abort, 3-cycle cap (workflow.md:559), autofix `--yes` print-substitute (:561-568), "never silently skip" (:576) ALL preserved.
- **Edit-cycle read-back (spec §Approach 1):** on `edit`, apply Edit-tool deltas, then Read the FULL draft file before re-asking approval — the Read render is that cycle's mandatory full read-back AND satisfies Edit's read-before-edit for the next cycle. One full emission per edit cycle (same as today's re-show — no regression).
- capture Phase 5 (:701-704): replace the `$SPEC_BODY` heredoc (vars don't survive tool calls — the :707-709 comment becomes obsolete, remove it) with `spec set-plan "$SPEC_ID" --file <literal draft path>`. Phase-5 anchor-file ordering + Phase 6 sync check untouched.
- capture tracker gate (:786-787): read `tracker.perEvent.capture` once into a var, per canonical `LEAF=` pattern at flow-next-work/SKILL.md:184-190.
- interview: three branches at SKILL.md:685-710 (new idea), :736-761 (existing spec), :776-785 (task) — replace `cat > /tmp/spec.md <<'EOF'` skeleton-placeholder heredocs with "Write the composed body to <literal unique path> via the Write tool, then `spec set-plan <id> --file <path>`" (same for acc/desc in the task branch). Collapse the duplicate fetch: spec body fetched at :202-203 (show+cat), re-fetched at :730 — instruct reuse of the earlier read unless the interview mutated the spec since. Edit-cycle Read rule applies to interview read-backs too.
- MAY run `bash scripts/sync-codex.sh` locally to validate the canonical edits survive the rewriter (esp. near §4.2 AskUserQuestion prose) — do NOT commit the regenerated mirror (fn-81.4 owns it).

## Investigation targets

**Required** (read before editing):
- `plugins/flow-next/skills/flow-next-capture/workflow.md:461-580` — Phase 4 read-back loop (contract to preserve)
- `plugins/flow-next/skills/flow-next-capture/workflow.md:690-720` — Phase 5 write + anchor ordering
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:619-800` — Write Refined Spec section
- `plugins/flow-next/skills/flow-next-work/SKILL.md:184-190` — canonical single-fetch LEAF pattern

**Optional:**
- `scripts/sync-codex.sh:452-1071` — AskUserQuestion rewrite machinery (fragility check)

## Key context

This is the spec's early proof point — fn-81.2 and fn-81.3 depend on this task. If the Write-render read-back can't preserve full-content visibility, STOP and re-evaluate pattern 1 (fall back to read-back-in-question + single heredoc) before other skills adopt it. Gap-analysis facts: bash vars do not survive across tool calls (applies to the draft PATH too — hence the literal-path rule); long Write renders collapse in the terminal until expanded; Codex apply_patch on a NEW file shows full content.

## Acceptance

- [ ] capture emits the spec body exactly once per approval cycle (Write render; Read render per edit cycle); heredoc re-emission gone; approve/edit/abort + cap + autofix semantics behavior-equivalent
- [ ] draft path handled per the path-persistence rule (literal path, no cross-tool-call shell var); no fixed `/tmp/spec.md`-style paths remain in touched files
- [ ] interview branches use Write + `--file <literal path>`; duplicate spec fetch collapsed; edit-cycle Read rule stated
- [ ] capture tracker gate reads its config leaf once
- [ ] canonical-only diff (no `plugins/flow-next/codex/` changes committed); local sync-codex validation run recorded in summary

## Done summary
Converted capture (Phase 4→5) and interview (all three Write-Refined-Spec branches) to the single-emission write pattern: draft body Written ONCE via the Write tool to a literal unique path (render = read-back), Edit-tool revisions with a mandatory full-file Read before each re-approval, flowctl consumes `spec set-plan/set-acceptance/set-spec --file <literal path>` — the `$SPEC_BODY` heredoc re-emission and fixed `/tmp/spec.md`/`/tmp/acc.md`/`/tmp/desc.md` paths are gone. Capture's tracker gate reads `tracker.perEvent.capture` once (LEAF pattern); interview's duplicate spec fetch collapsed onto the Detect-Input-Type read. Canonical files only; local sync-codex.sh validation run passed (mirror regen deferred to fn-81.4). RP impl-review: SHIP (first pass).
## Evidence
- Commits: 94924748a87566ef7ca9e31b03041bb2b40e1103
- Tests: uv run --with pytest python -m pytest plugins/flow-next/tests/ -q (1393 passed, 2 skipped, 164 subtests), bash scripts/sync-codex.sh (all validators green; regenerated mirror stashed, not committed — fn-81.4 owns mirror regen), grep -rn '/tmp/spec.md|/tmp/acc.md|/tmp/desc.md|SPEC_BODY' touched skills → zero hits
- PRs: