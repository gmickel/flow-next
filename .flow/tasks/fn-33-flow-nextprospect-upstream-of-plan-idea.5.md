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
   - Use `cmd_prospect_read --json` internally (no duplicate parse code).
   - Refuse if artifact is corrupt (exit 3 with the same error shape as `read`).
   - Refuse if `N < 1` or `N > survivor_count` (exit 2, useful error message).
2. **Idempotency guard (R14):**
   - Read `promoted_ideas` from artifact frontmatter.
   - If `N in promoted_ideas` and no `--force`: exit 2 with message `"Idea #N already promoted to <epic-id>. Use --force to create another epic from the same idea."`
   - Track the epic-id of prior promotes in a parallel frontmatter field `promoted_to: {N: epic_id}` so the error message can reference the specific epic.
3. **Extract survivor:**
   - `_extract_survivor(artifact_body, N)` parses the `## Survivors` section, finds `#### <N>. <title>`, extracts `title`, `summary`, `leverage`, `size` fields. `next_step` is a hard-coded body line (`**Next step:** /flow-next:interview`), not a data field — promote ignores it. Optional body fields `affected_areas`, `risk_notes`, `persona` may be present (from Phase 4's RANKED join, per task 3); parser tolerates their absence cleanly. <!-- Updated by plan-sync: task 2 landed Phase 4 RANKED with affected_areas / risk_notes / persona joined from Phase 2 candidate; next_step is template-only -->
   - Parser tolerates bucket subsection headings (`### High leverage (1-3)` / `### Worth considering (4-7)` / `### If you have the time (8+)`).
   - Exact body line labels shipped by `render_prospect_body` (task 3, flowctl.py:4189-4277): `**Summary:**`, `**Leverage:**`, `**Size:**`, `**Affected areas:**`, `**Risk notes:**`, `**Persona:**`, `**Next step:**`. `**Affected areas:**` renders as a comma-joined string when the candidate list had multiple entries — parser must split on `, ` to recover the list shape if promote needs it (currently it doesn't; skeleton renderer only uses summary / leverage / size). <!-- Updated by plan-sync: body labels taken verbatim from shipped render_prospect_body. -->
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
   - Atomic rewrite: read artifact, update `promoted_ideas` list, update `promoted_to` dict, re-serialize via `write_prospect_artifact` (task 3; flowctl.py:4131). The shipped writer fails-on-exists via `os.link`, so rewrite path is: (a) read → (b) mutate → (c) `os.unlink(path)` + `write_prospect_artifact(path, fm, body)`, OR (b') extend `write_prospect_artifact` with an `overwrite=True` mode for in-place rewrite. Pick the option that preserves the atomic invariant — the `unlink` gap is the risk. Recommended: add `overwrite=True` keyword to the writer in this task and guard it to rewrite-only. `promoted_to` is a new optional frontmatter key — extend `PROSPECT_OPTIONAL_FIELDS` + `PROSPECT_FIELD_ORDER` (`validate_prospect_frontmatter` must continue to pass). <!-- Updated by plan-sync: task 3 shipped write_prospect_artifact with fails-on-exists semantics via os.link; rewrite in promote must add overwrite=True or unlink-then-write. `promoted_to` is new; update the optional-fields set + field-order list. -->
   - If artifact update fails after epic creation: print warning "epic created but artifact not updated; re-run promote with --force if needed". Never rolls back the epic.
7. **Output:**
   - Text: `Promoted idea #N ("<title>") to <epic-id>. Next: /flow-next:interview <epic-id>`
   - `--json`: `{success, epic_id, idea: N, artifact_id, source_link}`

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py` `cmd_epic_create` + `cmd_epic_set_plan` — reuse, don't reinvent
- `plugins/flow-next/scripts/flowctl.py:3009-3031` `create_epic_spec` — default skeleton as baseline to extend
- `plugins/flow-next/scripts/flowctl.py:4131` (`write_prospect_artifact`) + `:3958-4081` (`PROSPECT_REQUIRED_FIELDS`, `PROSPECT_OPTIONAL_FIELDS`, `PROSPECT_FIELD_ORDER`, `validate_prospect_frontmatter`) — reuse for artifact rewrite + `promoted_to` support. <!-- Updated by plan-sync: task 3 shipped these; extend `PROSPECT_OPTIONAL_FIELDS` with `promoted_to` in this task. -->
- `plugins/flow-next/scripts/flowctl.py:4189` (`render_prospect_body`) — the body renderer whose output `_extract_survivor` must parse in reverse. <!-- Updated by plan-sync: treat the shipped render_prospect_body output as the reverse-parser's input contract. -->
- Artifact schema from task 3 — bucket heading format must be parseable in reverse

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
_(populated by /flow-next:work upon completion)_

## Evidence
_(populated by /flow-next:work upon completion)_
