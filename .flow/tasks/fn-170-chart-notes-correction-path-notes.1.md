---
satisfies: [R1, R3, R4]
---
# fn-170-chart-notes-correction-path-notes.1 chart resolve: notes_append + sharpen unknown-key rejection

## Description
---
satisfies: [R1, R3, R4]
---

### Description
Add the `notes_append` key to `resolve --sharpen-file` and make unknown sharpen keys a hard validation error.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_chart_resolution.py`

### Approach
- `_parse_sharpen_file` (flowctl.py:15806-15861): accept `notes_append` (non-empty string); diff `data.keys()` against the accepted set {decisions, remove_questions, remove_parked, parked_removals, notes_append}; unknown key -> `ChartError("validation", "sharpen_file_unknown_key", ...)` naming offending + accepted keys. Keep the accepted-key set in ONE constant shared by the error message and the `--sharpen-file` argparse help text.
- Ordering: unknown-key (structural) check BEFORE `refuse_if_unsafe_prose` (flowctl.py:15171) on the notes content - a typo gets the key error, not a prose-scan error. Refusal happens before any allocation/persistence, same as create-notes (14498).
- Normalization: per-line - keep existing `- ` markers, prefix bare lines; flowctl stamps each appended bullet `- [corrected <YYYY-MM-DD>]` (tool owns the date, caller text is prose).
- Append inside `resolve_chart_decision` on the SAME `md_text` local the transaction already mutates (ledger pattern 15533-15549), via `_replace_chart_section` (14041 - literal-text lambda substitution, appends `## Notes` if missing), committed through the single `run_chart_transaction` (~16616). Cascade/--supersedes: append ONCE per resolve call.
- Identical-retry guard (15952-15988): `notes_append` joins the non-empty sharpen-content check and is reported under `details.ignored_sharpen` (add a notes entry). Post-reopen re-resolve is NOT a retry (status not `resolved`) - appends fresh.
- JSON result: `notes_appended` ALWAYS a list of appended bullet strings (empty when none) - consistent with `removed_questions`, never a boolean.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:15806-15861` - `_parse_sharpen_file`
- `plugins/flow-next/scripts/flowctl.py:15952-15988` - identical-retry / ignored_sharpen shape
- `plugins/flow-next/scripts/flowctl.py:15533-15549` + `:16616` - md_text mutation + transaction commit pattern
- `plugins/flow-next/scripts/flowctl.py:14041-14060` - `_replace_chart_section` literal-lambda contract
- `plugins/flow-next/tests/test_chart_resolution.py:509,1013,1074,1280` - existing sharpen fixtures + conventions

**Optional:**
- `plugins/flow-next/scripts/flowctl.py:14493-14498` - create-time notes prose refusal
- `plugins/flow-next/scripts/flowctl.py:26855` - cmd_chart_resolve CLI entry

### Key context
- `_replace_chart_section` uses lambda substitution to avoid regex backslash expansion - build the replacement the same way or a correction containing `\d` corrupts the file.
- In-repo sharpen callers (chart workflow.md:374,410; SKILL.md:97,109) pass only accepted keys - confirm before landing.
- No prompt-text changes: `test_prompt_text_pinned` must stay untouched.

### Acceptance
- [ ] `notes_append` appends date-stamped bullets to `## Notes` in the same resolve transaction; existing notes byte-untouched (R1)
- [ ] Empty/whitespace/non-string `notes_append` rejected; unsafe prose refused before persistence (R1)
- [ ] Unknown sharpen key -> `sharpen_file_unknown_key` listing offending + accepted keys, checked before prose refusal; aliases still accepted; nothing persisted (R3)
- [ ] Identical retry with `notes_append` -> no double-append, reported in `ignored_sharpen`; post-reopen re-resolve appends fresh (R4)
- [ ] Result JSON `notes_appended` is always a list (R2 result-field half)
- [ ] New tests: no-Notes-section chart, mixed bulleting, backslash content, two sequential appends under lock, unknown-key ordering, retry + reopen fixtures
- [ ] Focused suite green: `cd plugins/flow-next/tests && python3 -m unittest test_chart_resolution -q`

## Acceptance
- [ ] notes_append appends date-stamped bullets via the chart writer in the same transaction; append-only
- [ ] sharpen_file_unknown_key rejection before prose refusal; aliases intact; zero persistence on reject
- [ ] ignored_sharpen covers notes_append on identical retry; reopen re-resolve appends fresh
- [ ] notes_appended always a list in resolve JSON
- [ ] regression tests for all of the above in test_chart_resolution.py

## Done summary
Added `notes_append` to `chart resolve --sharpen-file` (append-only, date-stamped bullets into `## Notes`, one append per resolve call, always-list `notes_appended` result field, folded into the identical-retry `ignored_sharpen` guard) and made any unrecognized `--sharpen-file` key a hard `sharpen_file_unknown_key` validation error checked before unsafe-prose refusal, via a single shared accepted-keys constant. 10 new regression tests added to `test_chart_resolution.py` (26 total in the file, all green); ruff clean; dual-copy + tracker manifest propagated.
## Evidence
- Commits: 34e12f8966e5cedbea0f4cbbb4af5e1f3279b4d3
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_chart_resolution -q, uvx ruff@0.16.0 check plugins/flow-next/scripts/flowctl.py plugins/flow-next/tests/test_chart_resolution.py, python3 -m unittest test_chart_resolution -q (26/26 OK, conductor re-run)
- PRs: