---
satisfies: [R11, R15]
---
# fn-122-harden-verdict-graduate-recurring.3 Docs sweep + codex mirror + CHANGELOG

## Description
Sweep every doc and generated surface that enumerates memory statuses, audit outcomes, or memory commands, then regenerate the Codex mirror and stage the CHANGELOG entry. This is the finalization task — docs, mirror, and changelog fold into one task by convention, not one task per artifact.

Depends on `.1` (the shipped CLI surface) and `.2` (the shipped skill prose): documentation describes what landed, not what was planned.

**Size:** M
**Files:**
- `plugins/flow-next/docs/memory-schema.md`
- `plugins/flow-next/docs/flowctl.md`
- `plugins/flow-next/docs/self-improving.md`
- `README.md` (root)
- `plugins/flow-next/agents/memory-scout.md`
- `CHANGELOG.md`
- `plugins/flow-next/codex/**` (regenerated only, never hand-edited)

### Approach

Sweep by grep, not by memory — the recurring failure on this repo is a named-file sweep that misses a secondary surface. Grep the tree for the five-outcome enumeration and for the `active|stale` status enum, and fix every hit:

```bash
grep -rn "Consolidate / Replace / Delete\|Consolidate/Replace/Delete" --include="*.md" .
grep -rn "active|stale\|active, stale\|active/stale" --include="*.md" plugins/ README.md
```

Known hits from plan-time scouting (re-verify line numbers):
- `plugins/flow-next/docs/memory-schema.md` (~:110-150) — status values gain `hardened`; the optional-frontmatter list gains `hardened_into`; the audit-lifecycle prose goes from five outcomes to six and describes the graduation + un-graduation path. Also add the R15 note, stated **honestly** — do not claim a read-side guarantee that does not exist. `validate_memory_frontmatter` runs only inside `write_memory_entry` (`flowctl.py:9607`); reads never validate. So an older flowctl **silently reads** a `hardened` entry and, because its default filter excludes only `stale`, will **surface** it in default `memory list` / `search` / memory-scout results. The loud failure is write-side: any older-flowctl rewrite of that entry fails validation on the unknown status and the unknown `hardened_into` field, so there is no silent corruption. Document read-through / write-refusal, and name lockstep upgrade of the two flowctl copies as the mitigation. No compatibility shim is being added, and the docs must not imply one.
- `plugins/flow-next/docs/flowctl.md:860` — status enum; `:893-894` — `--status` choices on list and search; `:900` — the "defaults to active / stale excluded" prose now covers hardened; `:913-918` — `mark-fresh` also reverts hardened; plus a new `#### memory mark-hardened` subsection matching the existing mark-stale/mark-fresh subsection shape (heading, one-line effect, fenced bash example, idempotency note).
- `plugins/flow-next/docs/self-improving.md:11` and `:18` — both five-outcome enumerations; add a clause that Harden closes the loop from memory to enforced gate.
- `README.md:368` — the `/flow-next:audit` feature-table row enumerating the outcomes.
- `plugins/flow-next/agents/memory-scout.md:45` — the `--status` filter row: hardened entries are excluded by default through the same mechanism as stale, so a previously-surfaced entry disappearing after hardening is expected, not a bug.
- `CHANGELOG.md` — an entry under `## [Unreleased]` in the repo's existing prose-bulleted style. **No version bump**: do not run `scripts/bump.sh`, do not touch version manifests or `FLOW_NEXT_VERSION` (batched-release rule).

Then regenerate the Codex mirror: run `./scripts/sync-codex.sh` TWICE (the second run proves idempotency) and commit the mirror diff alongside the canonical changes. Its validation guards must stay green.

<!-- Updated by plan-sync: fn-122-harden-verdict-graduate-recurring.2 already ran sync-codex.sh (twice, idempotent, guards green) and committed the regenerated mirror, including a widened flow-next-audit description at scripts/sync-codex.sh:1577 ("keep, update, consolidate, replace, delete, or harden" / "graduate a recurring lesson into a gate"). This task's docs edits (memory-schema.md, flowctl.md, README.md, self-improving.md, agents/memory-scout.md, CHANGELOG.md) are not mirror inputs, so re-running sync-codex.sh here is expected to produce NO diff on either run -- that is a pass, not a sign something is missing. Still run it twice per the checklist as a regression check (someone could have edited a mirrored skill file since .2 landed), but do not go looking for a description to widen -- that edit already happened. -->

Check `GLOSSARY.md` — it currently defines neither memory statuses nor audit outcomes. Add a `Harden` / `Hardened` term only if the sweep shows the vocabulary is otherwise undiscoverable; otherwise leave it and say so.

### Investigation targets

**Required** (read before coding):
- `plugins/flow-next/docs/flowctl.md:856-945` — the `### memory` reference section and the mark-stale/mark-fresh subsection shape to mirror
- `plugins/flow-next/docs/memory-schema.md:100-160` — status values, optional fields, audit lifecycle
- `CHANGELOG.md:1-40` — the `## [Unreleased]` block and the entry style used in the most recent version block

**Optional** (reference as needed):
- `plugins/flow-next/docs/self-improving.md:1-25`
- `plugins/flow-next/agents/memory-scout.md:40-90`
- `scripts/sync-codex.sh:1500-1640` — where the audit skill is referenced in mirror generation

### Key context

- Documentation describes the shipped behavior. Read the actual `flowctl memory mark-hardened --help` output and the landed skill prose before writing; do not copy flag names from the spec.
- The Codex mirror is generated. Hand-editing `plugins/flow-next/codex/**` is always wrong; the fix is always upstream in the canonical file plus a re-run of the sync script.
- If `sync-codex.sh` fails a validation guard on new prose from task `.2`, that is a real finding — a new Claude-only phrase may need a transform and a hard-fail guard. Report it rather than weakening the guard.
- Downstream properties (flow-next.dev, the AI x SDLC guide, the Obsidian vault) are the maintainer's separate pass and are explicitly out of scope for this task.

## Acceptance

- [ ] `docs/memory-schema.md` documents `hardened` as a status value, `hardened_into` as an optional field, the six-outcome audit lifecycle, and the graduation / un-graduation (`mark-fresh`) path (R11).
- [ ] `docs/memory-schema.md` states the cross-version contract accurately: reads are silent (an old flowctl surfaces hardened entries because its default filter excludes only `stale`), writes are refused (validation fails on the unknown status/field), so the failure mode is misclassification-then-write-refusal, never silent corruption. Lockstep upgrade of both flowctl copies is named as the mitigation; no compatibility shim is claimed (R15).
- [ ] The docs contain no claim that an older flowctl rejects a hardened entry on read — verified by re-reading the landed prose against `flowctl.py:9607` (the only `validate_memory_frontmatter` call site).
- [ ] `docs/flowctl.md` has a `#### memory mark-hardened` subsection matching the existing sibling shape; the status enum, both `--status` choice lists, the default-exclusion prose, and the `mark-fresh` description all reflect hardened (R11).
- [ ] `docs/self-improving.md` and root `README.md` enumerate six outcomes wherever they previously enumerated five (R11).
- [ ] `agents/memory-scout.md` notes that hardened entries are excluded from default retrieval by the same status filter as stale (R7 discoverability).
- [ ] A grep sweep for the five-outcome enumeration and the `active|stale` status enum across `*.md` returns no stale hits outside the generated `codex/` mirror; the sweep commands and their output are recorded in the task evidence.
- [ ] `CHANGELOG.md` has an entry under `## [Unreleased]`; no version bump, no manifest or `FLOW_NEXT_VERSION` change (R11).
- [ ] `./scripts/sync-codex.sh` run twice with all validation guards green; the second run produces no further diff (idempotent); the mirror diff is committed with the canonical changes (R11).
- [ ] GLOSSARY.md either gains the Harden term or the decision to leave it unchanged is stated with a reason.
- [ ] Full gate green at completion: `python3 scripts/run_tests_parallel.py`.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
