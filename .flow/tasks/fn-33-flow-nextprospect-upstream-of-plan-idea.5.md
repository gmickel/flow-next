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
   - Atomic rewrite: read artifact, update `promoted_ideas` list, update `promoted_to` dict, re-serialize with same YAML helpers as task 3, atomic write-then-rename.
   - If artifact update fails after epic creation: print warning "epic created but artifact not updated; re-run promote with --force if needed". Never rolls back the epic.
7. **Output:**
   - Text: `Promoted idea #N ("<title>") to <epic-id>. Next: /flow-next:interview <epic-id>`
   - `--json`: `{success, epic_id, idea: N, artifact_id, source_link}`

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py` `cmd_epic_create` + `cmd_epic_set_plan` — reuse, don't reinvent
- `plugins/flow-next/scripts/flowctl.py:3009-3031` `create_epic_spec` — default skeleton as baseline to extend
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
