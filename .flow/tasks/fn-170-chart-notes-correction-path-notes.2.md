---
satisfies: [R2, R5]
---
# fn-170-chart-notes-correction-path-notes.2 chart briefing: render corrections + post-transition status

## Description
---
satisfies: [R2, R5]
---

### Description
Verify appended corrections travel into the briefing `## Notes`, and fix the briefing header rendering the pre-transition chart status.

**Size:** S
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_chart_briefing.py`

### Approach
- `_render_briefing_index_md` reads `chart.get('status')` at flowctl.py:17446 from the chart dict loaded at 17617, but the open->done flip happens at 17830-17852 AFTER the render call (17741). Compute the post-transition chart status first (or move the render after the transition block) and pass it in. Do NOT conflate with the `status` kwarg on the same function signature (~17430) - that is the BRIEFING's status.
<!-- Updated by plan-sync: fn-170-chart-notes-correction-path-notes.1 shifted flowctl.py line numbers by ~+106 (notes_append + sharpen_file_unknown_key additions landed before this section) -->
- Fixture: final briefing that closes the chart renders `**Chart status:** done`, matching `chart show` immediately after.
- Fixture: a chart with an appended correction (from task 1's path) renders both the original note and the dated correction in the briefing `## Notes` (extend `test_notes_section_appears_in_briefing_index`, test_chart_briefing.py:1292).
- Investigate `chart_revision` fingerprint scope: confirm whether `## Notes` participates; document the finding for task 3's docs line (expected: a notes append does not stale prior briefings - immutable snapshots by design).

### Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl.py:17426-17457` - `_render_briefing_index_md` header + Notes copy
- `plugins/flow-next/scripts/flowctl.py:17617,17741,17830-17852` - load, render call, transition order
- `plugins/flow-next/tests/test_chart_briefing.py:1292` - notes-in-briefing fixture to extend

**Optional:**
- `plugins/flow-next/scripts/flowctl.py:27160-27199` - reopen + staled_briefings (fingerprint scope question)
<!-- Updated by plan-sync: fn-170-chart-notes-correction-path-notes.1 used actual line numbers ~+106 past the original estimates in this task's investigation targets -->

### Acceptance
- [ ] Final briefing that transitions the chart renders `**Chart status:** done` (R5)
- [ ] Briefing `## Notes` carries original fact + dated correction (R2 briefing half)
- [ ] Fingerprint-scope finding recorded for the docs task
- [ ] Focused suite green: `cd plugins/flow-next/tests && python3 -m unittest test_chart_briefing -q`

## Acceptance
- [ ] briefing header shows post-transition chart status
- [ ] briefing Notes renders appended corrections
- [ ] fixtures added in test_chart_briefing.py

## Done summary
Fixed `_render_briefing_index_md`'s "Chart status" header to reflect the post-transition status (a final briefing that closes the chart now renders `done`, matching `chart show` immediately after) instead of the stale pre-transition value. Added a regression test proving `notes_append` corrections (from task .1) already flow into the briefing `## Notes` section with no extra plumbing, since `emit_chart_briefing` reads `md_text` fresh from disk. Also confirmed and documented: `chart_decision_revision` (the briefing-fingerprint hash) only covers the JSON sidecar (id/outcome/title/decisions/parked_questions) - `## Notes` lives in markdown only, so a notes_append correction does not stale prior briefings.
## Evidence
- Commits: 5037f5c086f7cbce402eadcdd99f07c380991fd6
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_chart_briefing -q, cd plugins/flow-next/tests && python3 -m unittest test_chart_resolution -q, uvx ruff@0.16.0 check plugins/flow-next/scripts/flowctl.py plugins/flow-next/tests/test_chart_briefing.py
- PRs: