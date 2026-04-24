---
satisfies: [R4, R9, R13, R19]
---

## Description

Phases 5-6: atomic artifact writer + handoff prompt with frozen numbered-options fallback.

**Size:** M
**Files:**
- `plugins/flow-next/skills/flow-next-prospect/workflow.md` (extend)
- `plugins/flow-next/scripts/flowctl.py` (new helpers: `write_prospect_artifact`, `_prospect_slug`, `_prospect_next_id`)
- `.flow/bin/flowctl.py` (mirror)
- `plugins/flow-next/tests/test_prospect_artifact.py` (new — unit tests for writer + slug helpers)

## Approach

**Phase 5 — Write artifact (before handoff):**
- Build YAML frontmatter + body in memory first (no partial writes).
- Atomic write-then-rename: write to `.flow/prospects/.tmp.<pid>.<artifact-id>.md`, `rename()` to final path on success. Ensures Ctrl-C mid-write never leaves a malformed artifact.
- Slug derivation: `slugify(focus_hint or "open-ended") + "-" + YYYY-MM-DD`.
- Same-day collision (R13): suffix with `-2`, `-3`, ...; base slug stays stable for `promote` lookup. Slug derivation is deterministic across processes (sequential suffixes, no uuid).
- Frontmatter fields (required): `title, date, focus_hint, volume, survivor_count, rejected_count, rejection_rate, artifact_id, promoted_ideas: [], status: active`.
- Frontmatter fields (optional, from Phase 2/3 — written only when upstream sets them): `floor_violation: true` (set by Phase 3 when user picks `loosen-floor`/`ship-anyway` on a rejection-floor miss), `generation_under_volume: true` (set by Phase 2 when validated candidate count is below `floor(GENERATION_TARGET_MIN * 0.7)`). Task 3 must accept both keys in the frontmatter dict and round-trip them; never invent default values when absent. <!-- Updated by plan-sync: task 2 landed these two optional frontmatter fields -->
- Body sections (in order): `## Focus`, `## Grounding snapshot`, `## Survivors` (with `### High leverage (1-3)` / `### Worth considering (4-7)` / `### If you have the time (8+)` subsections), `## Rejected`.
- `## Survivors` entries are written from Phase 4's `RANKED` list. Each survivor record carries the full candidate fields from Phase 2 (`title, summary, affected_areas, size, risk_notes, persona`) joined with Phase 4's ranking fields (`position, leverage`, bucket assignment). The body `#### <N>. <title>` block must render `title`, `summary`, `leverage` (forced format `Small-diff lever because X; impact lands on Y.` — period terminal), `size`; `affected_areas`, `risk_notes`, and `persona` are optional body fields (keep them if present, skip cleanly if absent). `next_step` is a hard-coded body template line (`**Next step:** /flow-next:interview`), not a candidate field. <!-- Updated by plan-sync: Phase 4 RANKED carries affected_areas, risk_notes, persona from Phase 2 candidate shape -->
- Reuse `write_memory_entry` as a structural model but do NOT reuse it directly — `cmd_memory_add` has memory-specific validation. Build a parallel helper `write_prospect_artifact(path, frontmatter, body)` that shares the YAML serialization path (via `_format_yaml_value` / `_yaml_scalar_needs_quoting` / `_quote_yaml_scalar`) but skips memory-specific enum validation.

**Phase 6 — Handoff prompt:**
- After artifact is written, blocking prompt via the platform's question tool.
- Prompt text: "Artifact saved to `<path>`. Promote a survivor to an epic now?"
- Options: one per survivor (label: "Promote #1: <title>") + "Skip" + "Interview instead".
- Frozen numbered-options fallback (R19): when no blocking tool available OR the tool errors, print exact string:
  ```
  Saved: .flow/prospects/<artifact-id>.md

  Promote a survivor to an epic?
    1) Promote #1: <title>
    2) Promote #2: <title>
    ...
    N) Skip
    i) Interview (ask /flow-next:interview what to refine)

  Enter choice [1-N|i|skip]:
  ```
- Parse reply:
  - `1` | `2` | ... → invoke `flowctl prospect promote <artifact-id> --idea <N>`
  - `i` | `interview` → print `/flow-next:interview` invocation suggestion (do NOT auto-invoke — user decides target)
  - `skip` | `<empty>` → exit cleanly

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:3874-3955` — YAML serialization helpers + `write_memory_entry` (parallel pattern)
- `plugins/flow-next/scripts/flowctl.py` function `atomic_write` (used throughout memory subsystem)
- `plugins/flow-next/skills/flow-next-impl-review/walkthrough.md:40-46` — platform tool table for blocking questions

**Optional:**
- `plugins/flow-next/skills/flow-next-impl-review/walkthrough.md` — per-finding Apply/Defer/Skip walkthrough as handoff-prompt UX precedent

## Key context

- Atomic rename is critical: same-process concurrent runs on the same day need deterministic suffix allocation. Use `O_EXCL` on open or scan existing files to find next suffix.
- `promoted_ideas` starts as `[]`; task 5 (promote) appends to it. Task 3 just needs to write the empty list correctly.
- Never gate artifact write on the handoff prompt — if the user Ctrl-C's Phase 6, the artifact should already be on disk.

## Acceptance

- [ ] `write_prospect_artifact(path, frontmatter, body)` helper lands in `flowctl.py` with atomic write-then-rename.
- [ ] Same-day slug collision: second invocation suffixes with `-2`; third with `-3`; thread-safe via file-existence check.
- [ ] YAML frontmatter includes all required fields listed in the epic schema (title, date, focus_hint, volume, survivor_count, rejected_count, rejection_rate, artifact_id, promoted_ideas, status) and round-trips optional Phase 2/3 flags (`floor_violation`, `generation_under_volume`) when upstream sets them.
- [ ] Body emits bucketed `## Survivors` subsections (`### High leverage (1-3)`, `### Worth considering (4-7)`, `### If you have the time (8+)`) from Phase 4's `RANKED` list; each `#### <N>. <title>` block renders `title`, `summary`, `leverage` (terminal period), `size`, and `**Next step:** /flow-next:interview`.
- [ ] Handoff prompt uses platform blocking-question tool when available; falls back to frozen numbered-options string format.
- [ ] Frozen fallback format tested — exact string emitted, reply parse handles `1` / `2` / `i` / `interview` / `skip` / empty.
- [ ] Ctrl-C at Phase 6 preserves the artifact (verified via unit test — artifact exists after `write_prospect_artifact` returns, independent of prompt outcome).
- [ ] Unit tests in `test_prospect_artifact.py`: slug derivation, collision suffix, frontmatter round-trip, atomic rename semantics.

## Done summary
Implemented Phases 5-6 of `/flow-next:prospect`: atomic artifact writer (`write_prospect_artifact` + `_prospect_slug` + `_prospect_next_id` + `render_prospect_body` + `validate_prospect_frontmatter`) in `flowctl.py` (mirrored to `.flow/bin/`), handoff-prompt phase with frozen numbered-options fallback in `workflow.md`, and 36 unit tests covering slug derivation, collision suffixing, frontmatter round-trip (including optional `floor_violation` / `generation_under_volume` flags), body rendering with optional `affected_areas` / `risk_notes` / `persona` fields, and concurrent-create EEXIST safety. All 253 plugin tests pass.
## Evidence
- Commits: a485c9ab1a26e25f4b0e742a308d7e17ed196035
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (253 tests, OK), python3 -m unittest plugins.flow-next.tests.test_prospect_artifact -v (36 tests, OK), python3 end-to-end smoke: write+collision+round-trip OK
- PRs: