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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
