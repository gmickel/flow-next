# flowctl memory upsert — deterministic find-or-create for recurrence-deduped memos

## Problem

Skills that write recurrence-deduped memory entries (the `feature-map-drift` memos in `/flow-next:qa` workflow.md §5.5 and `flow-next-features` maintain.md) must fold: look up whether an entry with a deterministic title identity already exists, then `memory add --update <id>` or create. That fold is hand-rolled bash+jq duplicated across two skills today, and it drew a whole finding class during fn-211 review (search-vs-list confusion — `memory search` tokenizes so identity match is fuzzy; `.matches[]` vs `.entries[]` payload shape; lookup identity drifting from the written title). Per the architecture split rule this is pure plumbing ("list these things / set this field") that belongs in flowctl, not prose.

## Approach

One new subcommand: `flowctl memory upsert` — same field surface as `memory add`, plus a deterministic match step. Exact-title match within the given `--track` (case-sensitive byte equality, no tokenization). Zero matches → create (identical to `add`). Exactly one match → update that entry in place (identical to `add --update <id>`). More than one match → fail closed with the ambiguous entry ids listed; never guess. Reuse the existing add/update code path — upsert is a thin resolution layer, not a second writer.

The two skills' fold blocks collapse to a single `upsert` call each (judgment about memo content stays in prose; only the find-or-create mechanics move).

## Acceptance criteria

- **R1:** `flowctl memory upsert` accepts the same flags as `memory add` (minus `--update`, which it owns internally, and minus the deprecated positional `content` / `--type`): `--track`, `--category`, `--title`, `--module`, `--tags`, `--body-file`, the per-track fields, `--no-overlap-check`, `--json`. `--title` and `--track` are required — missing either errors with a clear message (exit nonzero), since the title-within-track pair IS the match identity.
- **R2:** Match semantics: entries in the given track whose `title` equals `--title` byte-for-byte. Zero matches → creates a new entry exactly as `memory add` would. One match → updates that entry exactly as `memory add --update <id>` would (body and provided fields replace; unspecified optional fields follow existing `--update` semantics unchanged). Two or more matches → exit nonzero, message lists every matching entry id, no write occurs.
- **R3:** `--json` output carries `entry_id` and an `action` field with value `created` or `updated` (ambiguous/failed runs produce no success payload). Non-JSON output states the same in one line.
- **R4:** Stale entries are still matched (an upsert on a stale entry updates it; status handling follows existing `--update` semantics — upsert adds no new status logic). Legacy flat-file entries are out of scope: upsert matches categorized entries only, and this is stated in the CLI help text.
- **R5:** The two consumers are simplified in the same change: qa workflow.md §5.5 and features maintain.md replace their list+jq fold with one `upsert` call, preserving the deterministic `drift: <surface>/<feature-slug> <sub-feature-id>` title identity and the `feature-map-drift` tag. No behavior change beyond the mechanics (same memos, same identities). `./scripts/sync-codex.sh` run twice, mirror diff committed.
- **R6:** Docs updated in the same change: `plugins/flow-next/docs/flowctl.md` (memory section) and `plugins/flow-next/docs/memory-schema.md` (a short upsert note in the lifecycle prose). Repo CHANGELOG gains an `## Unreleased` entry (no version bump — batched release).
- **R7:** Focused unit tests cover: create path, update path, ambiguous fail-closed path, missing `--title`/`--track` errors, `--json` payload shape (`entry_id` + `action`), and stale-entry match. Tests live beside the existing memory tests.

## Boundaries

- No fuzzy/tokenized matching, no tag-scoped or module-scoped match variants — exact title within track only (YAGNI; the identity convention is deterministic by design).
- No changes to `memory add`/`search`/`list` behavior.
- No new config keys.
- Skill-prose changes limited to the two fold blocks (R5); no other skill adopts upsert in this change.

## Quick commands

- `cd plugins/flow-next/tests && python3 -m unittest test_memory_upsert -q` (new suite; plus whichever existing memory suites cover add/update — run those focused too)
- `uvx ruff@0.16.0 check plugins/flow-next/scripts/flowctl.py`
