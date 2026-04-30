---
satisfies: [R2, R16]
---

## Description

Extend the categorized memory schema with a `decisions` knowledge category and decision-specific optional frontmatter fields. Pure schema/plumbing change; no skill behavior — interview's three-criteria gate (T3) and audit's per-entry judge (T5) consume this category once it lands.

**Size:** S
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/scripts/ci_test.sh`

## Approach

- Add `"decisions"` to `MEMORY_CATEGORIES["knowledge"]` list at `flowctl.py:3670-3676`.
- Extend `MEMORY_KNOWLEDGE_FIELDS` (or add a parallel `MEMORY_DECISION_FIELDS`) at `flowctl.py:3679-3698` with optional fields: `decision_status` (enum: `proposed | accepted | superseded`), `superseded_by`, `alternatives_considered` (list).
- Update `MEMORY_FIELD_ORDER` at `flowctl.py:3722-3741` with explicit slots for new fields (preserves deterministic write order — gotcha flagged by repo-scout).
- Update `cmd_memory_init()` at `flowctl.py:4965-5052` so `flowctl memory init` lazy-creates `.flow/memory/knowledge/decisions/.gitkeep` (extend the directory loop ~line 5011).
- Validator (`validate_memory_frontmatter` at `flowctl.py:4571-4655`) picks up new optional fields automatically via the allowed-fields union. Add an enum-check for `decision_status` per the `MEMORY_STATUS` precedent at `flowctl.py:3718`.
- `ci_test.sh:170-180` Memory System block: add an assertion that creates a decisions-track entry with all three optional fields, reads it back via `flowctl memory list --track knowledge --category decisions --json`, and verifies field round-trip.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:3659-3744` — full memory-schema constants block
- `plugins/flow-next/scripts/flowctl.py:4965-5052` — `cmd_memory_init` lazy-create pattern (extend the directory loop)
- `plugins/flow-next/scripts/flowctl.py:4571-4655` — `validate_memory_frontmatter`
- `plugins/flow-next/scripts/ci_test.sh:170-180` — Memory System test section

**Optional:**
- `plugins/flow-next/scripts/flowctl.py:3722-3741` — `MEMORY_FIELD_ORDER` (deterministic write-order tuple)

## Acceptance

- [ ] `flowctl memory init` creates `.flow/memory/knowledge/decisions/.gitkeep`
- [ ] `flowctl memory add --track knowledge --category decisions --title "..." --body "..."` succeeds and writes to `.flow/memory/knowledge/decisions/<slug>-<date>.md`
- [ ] Optional fields `decision_status`, `superseded_by`, `alternatives_considered` round-trip through frontmatter (write → read → match)
- [ ] `decision_status` rejects values outside the `proposed | accepted | superseded` enum
- [ ] `flowctl memory list --track knowledge --category decisions` returns the entry
- [ ] `MEMORY_FIELD_ORDER` includes explicit slots for new fields (deterministic write order verified by repeated read+write cycle)
- [ ] `ci_test.sh` decisions-track assertion passes

## Done summary

## Evidence
