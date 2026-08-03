---
satisfies: [R3]
---
# fn-159-convergence-aware-review-terminals-and.3 NEEDS_HUMAN terminal verdict end-to-end (parser, status maps, ralph-guard, grammar sweep)

## Description
Add NEEDS_HUMAN as a first-class terminal verdict end-to-end with persist-then-exit ordering: parser, both flowctl status maps + status-CLI choices, ralph-guard verdict sites, per-path terminal points, prompt grammar lines, skill prose, ralph-init templates.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/scripts/hooks/ralph-guard.py`, SKILL.md/workflow-*.md verdict enumerations (NON-canonical prose only; incl. the three workflow-rp.md fences), `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh` (NOT the prompt_*.md templates — those are pinned in TEMPLATE_HASHES and move to .4), `GLOSSARY.md`, tests. **NO canonical prompt-template (references/*.md) or `*_FALLBACK` edits here — task .4 owns ALL template/fallback/pin/fixture changes in one pass (round-2 P1: .3 landing template edits first leaves the parity suite red and churns pins twice).**

### Approach
- Parser: extend regex at flowctl.py:4516 to include NEEDS_HUMAN; update the "UNCHANGED" comment (:4526). Completion grammar: SHIP|NEEDS_WORK|NEEDS_HUMAN.
- **Persist-then-exit (review P1 — exiting 4 inside `_finish_backend_exec` or the RP recorder skips receipt/status persistence):** NEEDS_HUMAN flows through the NORMAL verdict return path — `_finish_backend_exec` returns it, `review-rounds record` consumes the round and returns it with EXIT 0, receipt write / `review-findings attach` / status writes complete — and only the OUTERMOST layer exits 4 printing `ESCALATE: reviewer requested human review`: in-process backends = the backend handler's post-persistence tail; RP = a final workflow-fence step AFTER record+attach+status. Define per path: plan, impl, completion, standalone, host, RP. Update the three workflow-rp.md fences (verdict grep pattern + final terminal step).
- Status: as landed by .1, the verdict→status literal (`{"SHIP": "ship", "NEEDS_WORK": "needs_work", "MAJOR_RETHINK": "needs_work"}`) now appears at **three** call sites, not the two originally anticipated — the old `:9388-9392`/`:35838` line refs are stale (that code no longer lives there) and the third site is new, introduced by .1's journal architecture: `expected_status` in `_record_review_attempt_locked` (flowctl.py:10122-10126, post-.2), the folded immediate write in the same function (flowctl.py:10319-10323, post-.2), and the replay/finalize-completion path in `_complete_review_journal` (flowctl.py:9847-9851, post-.2). All three need `"NEEDS_HUMAN": "needs_human"` — missing the third means a replayed NEEDS_HUMAN journal never writes status. `spec set-plan-review-status` / completion-status argparse choices accept `needs_human`. <!-- Updated by plan-sync: fn-159-convergence-aware-review-terminals-and.1 introduced a third status-derivation call site (_complete_review_journal replay path) not present when this task was scoped; fn-159-convergence-aware-review-terminals-and.2 (stall detector + digest backfill) shifted all three sites further forward (were ~9784-9788/9940-9944/9511-9516 post-.1) -->
- **Investigation-target line numbers below predate .1's and .2's landing and have shifted** (the file grew further in the 9400-11100 region for the stall detector, digest backfill, and structured ratchet); use the three call sites named above rather than the original `:9385-9400`/`:35830-35850` anchors.
- ralph-guard.py: `VALID_RECEIPT_VERDICTS` (L112) + three `<verdict>(...)` regexes (~L917/932/994).
- Hand the prompt-template grammar line + NEEDS_HUMAN guidance wording to task .4 (single parity rebaseline). This task changes NO hash-pinned file.
- Sweep skill prose verdict enumerations (non-pinned files only), ralph.sh, GLOSSARY.md Receipt entry. ralph-init `prompt_{plan,work,completion}.md` are hash-pinned (TEMPLATE_HASHES) — their verdict-grammar edits belong to .4's single pin pass. Never hand-edit codex/ (sync at .6).

### Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl.py:4499-4530, 9385-9400, 35830-35850` — parser + maps
- flowctl backend handlers' post-record tails (grep `record_review_attempt(` call sites) — where the exit-4 tail goes
- `plugins/flow-next/scripts/hooks/ralph-guard.py:100-130, 900-1000`
- `plugins/flow-next/skills/flow-next-plan-review/workflow-rp.md` — verdict grep + record fence
- `plugins/flow-next/tests/test_prompt_text_pinned.py:61-170` — pin procedure

**Optional:**
- `plugins/flow-next/tests/test_codex_verdict_extraction.py`
- `.flow/memory/bug/runtime-errors/structured-review-parsers-must-2026-07-30.md`

### Key context
- No new exit codes; NO pilot/land logic edits — they match `ESCALATE:` generically; verify by reading, don't edit.
- Tests must assert attempt row + receipt + status ALL present before exit-4 is observed, including a nonzero-exit transport process that still delivered the verdict.

### Acceptance
- [ ] Parser accepts NEEDS_HUMAN everywhere; completion grammar correct
- [ ] Round consumed via normal path; receipt/attach/status complete BEFORE outermost exit 4 + marker (per-path tests)
- [ ] Both status maps + status-CLI choices write/accept `needs_human`
- [ ] ralph-guard accepts NEEDS_HUMAN receipts (all sites, test added)
- [ ] workflow-rp.md fences updated (grep pattern + terminal step); zero hash-pinned files touched (pins land in .4)

- Round-4: NEEDS_HUMAN terminal tests include the incomplete-finalization replay path — a status/attach failure after record leads the next invocation to replay persistence and then emit exit 4, never to re-dispatch.
## Acceptance
- [ ] R3 satisfied: persist-then-exit ordering proven per path; four grammar code sites + prose sweep complete
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
