---
satisfies: [R6, R14, R20]
---

## Description

`flowctl prospect promote <artifact-id> --idea <N>` — converts a ranked survivor to a new epic with pre-filled skeleton, plus idempotency guard and `promoted_ideas` tracking.

**Size:** M
**Files:**
- `plugins/flow-next/scripts/flowctl.py` (new: `cmd_prospect_promote`, `_extract_survivor`, `_render_epic_skeleton_from_prospect`)
- `.flow/bin/flowctl.py` (mirror)
- `plugins/flow-next/tests/test_prospect_promote.py` (new)

## Approach

**`flowctl prospect promote <artifact-id> --idea <N> [--epic-title "..."] [--force] [--json]`:**

1. **Load + validate artifact:**
   - Reuse the task 4 helpers directly (no subprocess / duplicate parse code): `_prospect_resolve_id(prospects_dir, artifact_id)` → descriptor, then `_prospect_parse_frontmatter(text)` for frontmatter and `_prospect_extract_section(text, "survivors")` + `_prospect_extract_survivors(body)` for the ranked list. <!-- Updated by plan-sync: task 4 shipped these helpers (flowctl.py:4296 _prospect_parse_frontmatter, :7147 _prospect_resolve_id, :7208 _prospect_extract_section, :7241 _prospect_extract_survivors). Shelling out to `cmd_prospect_read --json` would reparse the file and lose the descriptor; call the helpers inline. -->
   - Refuse if artifact is corrupt: check `descriptor["status"] == "corrupt"` (from `_prospect_artifact_status`, flowctl.py:4414) and exit 3 with `f"[ARTIFACT CORRUPT: {descriptor['corruption']}]"` — same shape as `cmd_prospect_read`'s corrupt branch (flowctl.py:7489-7511).
   - Refuse if `N < 1` or `N > survivor_count` (exit 2, useful error message).
2. **Idempotency guard (R14):**
   - Read `promoted_ideas` from artifact frontmatter.
   - If `N in promoted_ideas` and no `--force`: exit 2 with message `"Idea #N already promoted to <epic-id>. Use --force to create another epic from the same idea."`
   - Track the epic-id of prior promotes in a parallel frontmatter field `promoted_to: {N: epic_id}` so the error message can reference the specific epic.
3. **Extract survivor:**
   - Task 4 shipped `_prospect_extract_survivors(body) -> list[dict]` (flowctl.py:7241); it returns every entry with `position` (int), `title`, `bucket`, plus each `**Label:**` field keyed as lowercase-underscored (e.g. `summary`, `leverage`, `size`, `affected_areas`, `risk_notes`, `persona`, `next_step`). `_extract_survivor(artifact_body, N)` becomes a thin filter: `next((s for s in _prospect_extract_survivors(body) if s["position"] == N), None)`. `next_step` is a hard-coded template line — promote ignores it. Optional fields (`affected_areas`, `risk_notes`, `persona`) may be absent; parser already tolerates that. <!-- Updated by plan-sync: task 4 shipped _prospect_extract_survivors as a bundled reverse-parser; task 5 filters the result instead of reimplementing. -->
   - Bucket heading tolerance is built-in (task 4 parses `### <bucket>` and carries `bucket: str` on every entry).
   - Exact body line labels shipped by `render_prospect_body` (task 3, flowctl.py:4189-4277): `**Summary:**`, `**Leverage:**`, `**Size:**`, `**Affected areas:**`, `**Risk notes:**`, `**Persona:**`, `**Next step:**`. `**Affected areas:**` renders as a comma-joined string when the candidate list had multiple entries; the shipped parser keeps the raw string — promote splits on `, ` only if it needs the list shape (skeleton renderer uses summary / leverage / size / affected_areas raw, so no split needed). <!-- Updated by plan-sync: body labels taken verbatim from shipped render_prospect_body; reverse parser (task 4) leaves multi-value fields as raw strings. -->
4. **Create epic:**
   - Call existing `cmd_epic_create(title=epic_title or survivor.title)` — reuses slug derivation, directory allocation, skeleton generation.
   - Capture new epic-id.
5. **Rewrite epic spec with prospect context:**
   - Call `cmd_epic_set_plan(epic_id, body)` with a body that extends the default skeleton:
     ```markdown
     # <epic title>

     ## Overview
     <survivor.summary>

     ## Leverage
     <survivor.leverage sentence>

     ## Suggested size
     <survivor.size> (from prospect ranking)

     ## Source
     - Prospect: `.flow/prospects/<artifact-id>.md#idea-N`
     - Focus hint: <artifact.focus_hint>
     - Prospected: <artifact.date>

     ## Acceptance criteria

     _(to be defined — run `/flow-next:interview <epic-id>` or `/flow-next:plan <epic-id>` next)_
     ```
6. **Update artifact frontmatter (R20):**
   - Atomic rewrite: read artifact, update `promoted_ideas` list, update `promoted_to` dict, re-serialize. Task 3's `write_prospect_artifact` (flowctl.py:4131) fails-on-exists via `os.link`, so it can't clobber. Task 4's `cmd_prospect_archive` (flowctl.py:7560-7668) already implements the canonical in-place rewrite pattern: write temp alongside src → `os.replace(tmp, src)`. Promote should follow the same pattern — either (a) inline the tmp+`os.replace` dance (≈12 lines; matches archive's approach byte-for-byte), OR (b) extract a shared `_prospect_rewrite_in_place(path, fm, body)` helper and call it from both `cmd_prospect_archive` and promote. Recommended: extract the helper in this task; archive's current inline code can be refactored to call it in the same patch. Do NOT add `overwrite=True` to `write_prospect_artifact` — keeping that writer strictly create-only preserves the collision-detection invariant `_prospect_next_id` relies on. <!-- Updated by plan-sync: task 4 shipped the archive rewrite pattern (tmp file → os.replace); reuse it via shared helper rather than mutating write_prospect_artifact's fails-on-exists contract. -->
   - `promoted_to` is a new optional frontmatter key — extend `PROSPECT_OPTIONAL_FIELDS` + `PROSPECT_FIELD_ORDER` (flowctl.py:3980, :3986). `validate_prospect_frontmatter` must continue to pass. Task 4 also uses `_format_prospect_yaml_value` which handles list/dict values; dict rendering (`promoted_to: {2: [epic-A]}`) may need an inline-dict code path (current writer only handles list/scalar/bool inline — verify before shipping, add dict-inline rendering if missing).
   - If artifact update fails after epic creation: print warning "epic created but artifact not updated; re-run promote with --force if needed". Never rolls back the epic.
7. **Output:**
   - Text: `Promoted idea #N ("<title>") to <epic-id>. Next: /flow-next:interview <epic-id>`
   - `--json`: `{success, epic_id, idea: N, artifact_id, source_link}`

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py` `cmd_epic_create` + `cmd_epic_set_plan` — reuse, don't reinvent
- `plugins/flow-next/scripts/flowctl.py:3009-3031` `create_epic_spec` — default skeleton as baseline to extend
- `plugins/flow-next/scripts/flowctl.py:3958-4081` — task 3's `PROSPECT_REQUIRED_FIELDS`, `PROSPECT_OPTIONAL_FIELDS`, `PROSPECT_FIELD_ORDER`, `validate_prospect_frontmatter`, `_format_prospect_yaml_value`, `_prospect_frontmatter_sort_key`. Extend `PROSPECT_OPTIONAL_FIELDS` + `PROSPECT_FIELD_ORDER` with `promoted_to` in this task; verify `_format_prospect_yaml_value` handles dict values (add inline-dict branch if missing).
- `plugins/flow-next/scripts/flowctl.py:4189` (`render_prospect_body`) — the body renderer whose output the reverse parser must tolerate. <!-- Updated by plan-sync: treat the shipped render_prospect_body output as the reverse-parser's input contract. -->
- `plugins/flow-next/scripts/flowctl.py:7147` (`_prospect_resolve_id`) + `:7208` (`_prospect_extract_section`) + `:7241` (`_prospect_extract_survivors`) — reuse for artifact load + survivor extraction (task 4, fn-33.4). <!-- Updated by plan-sync: task 4 shipped id resolution + section slicer + survivor reverse-parser; filter by position for promote's single-idea lookup. -->
- `plugins/flow-next/scripts/flowctl.py:4296` (`_prospect_parse_frontmatter`) — parse artifact frontmatter for the rewrite (task 4). <!-- Updated by plan-sync: canonical parser shipped in task 4; reuse rather than rolling a parallel. -->
- `plugins/flow-next/scripts/flowctl.py:4341` (`_prospect_detect_corruption`) + `:4414` (`_prospect_artifact_status`) — compute `status == "corrupt"` to gate promote refusal (exit 3). <!-- Updated by plan-sync: task 4's status helper is the single source of truth for corruption gating. -->
- `plugins/flow-next/scripts/flowctl.py:7560-7668` (`cmd_prospect_archive`) — canonical in-place rewrite pattern (temp file + `os.replace`); extract as shared helper or mirror inline. <!-- Updated by plan-sync: archive's rewrite pattern is the precedent; avoid touching write_prospect_artifact's fails-on-exists contract. -->

**Optional:**
- `plugins/flow-next/scripts/flowctl.py` `cmd_memory_add` update-in-place logic — YAML rewrite precedent

## Key context

- Epic creation uses the real `cmd_epic_create` path (not a skeleton shim). This means `flowctl prospect promote` actually allocates the next epic id, writes `.flow/epics/<id>.json` + `.flow/specs/<id>.md`, and respects any future epic-create side effects (dep allocation etc.).
- `--force` bypasses idempotency but still appends to `promoted_ideas` + `promoted_to` — the second epic-id is tracked separately (`promoted_to: {3: [epic-A, epic-B]}`), so audit history is preserved.
- The epic's `## Source` link is the handoff breadcrumb — users (or agents) reading the new epic can trace back to the prospect artifact for context.

## Acceptance

- [ ] `flowctl prospect promote <id> --idea <N>` creates a new epic via `cmd_epic_create`, returns epic-id.
- [ ] Epic spec includes `## Source` section linking back to `.flow/prospects/<artifact-id>.md#idea-N` + focus hint + prospect date.
- [ ] Idempotency: second promote of same `N` fails with useful message; `--force` allows it and tracks both epic-ids in `promoted_to: {N: [id1, id2]}`.
- [ ] Artifact frontmatter atomically updated with `promoted_ideas` (sorted, deduped) + `promoted_to` dict on every successful promote.
- [ ] `--json` returns `{success, epic_id, idea, artifact_id, source_link}`.
- [ ] Invalid `--idea N` (out of range, missing, rejected-position) exits 2 with a specific error.
- [ ] Corrupt artifact refuses promote (exit 3, matches `read` behavior).
- [ ] Unit tests cover: basic promote, idempotency refuse, `--force` override, out-of-range N, corrupt artifact refuse, promoted_ideas + promoted_to tracking.

## Done summary
Implemented `flowctl prospect promote <id> --idea <N>` with idempotency guard (R14) and `promoted_to` per-idea epic-id tracking (R20). Reuses task-4 helpers (`_prospect_resolve_id`, `_prospect_parse_frontmatter`, `_prospect_extract_section`, `_prospect_extract_survivors`); extracted shared `_prospect_rewrite_in_place` (atomic tmp+os.replace) used by both promote and refactored archive without changing `write_prospect_artifact`'s fails-on-exists contract; extended frontmatter schema with inline-flow dict rendering + parser fallback; 21 new unit tests cover happy path, idempotency, --force, edge cases.
## Evidence
- Commits: 9dd36768b446d87771b0d2c5c276844c4c6879cd
- Tests: python3 -m unittest discover -s plugins/flow-next/tests
- PRs: