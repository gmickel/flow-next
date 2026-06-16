---
satisfies: [R1, R4]
---

## Description
Make every shipped skill discoverable and stop the "Where to look" tables from drifting. Today five real skills (`flow-next-deps`, `flow-next-export-context`, `flow-next-rp-explorer`, `flow-next-worktree-kit`, `flow-next-setup`) are absent from the README commands table, the docs index, AND the CLAUDE.md "Where to look" table, and there is no skills catalog anywhere. Add a skills catalog covering all 26 skills, surface the five missing skills in the README skills/commands surface, and bring the `CLAUDE.md`/`AGENTS.md` "Where to look" table to parity with the README's (it currently omits `docs/spec-template.md`, `docs/glossary.md`, `docs/strategy.md`, `docs/sync-codex.md`).

**Size:** M
**Files:** `README.md`, `CLAUDE.md` (= `AGENTS.md` symlink — edit once), `plugins/flow-next/docs/README.md`; new `plugins/flow-next/docs/skills.md` (skills catalog — or extend the existing doc index, implementer's call).

## Approach
- Derive the authoritative skill list: `ls -d plugins/flow-next/skills/*/`. Cross-check against the README commands table (`README.md:210-231`) and the doc index.
- For each missing skill, note whether it is slash-command-triggered or phrase-triggered (mark phrase-only ones clearly, mirroring how the SKILL.md descriptions read).
- Catalog placement: a new `docs/skills.md` linked from the doc index is the natural home; keep it a thin reference table (name · trigger · one-line purpose · SKILL.md link), relative paths only (R17).
- Reconcile the two "Where to look" tables to an identical doc-row set (or document the deliberate audience divergence in a one-line note).

## Investigation targets
**Required** (read before coding):
- `README.md:210-276` — commands table + "Where to look" table
- `CLAUDE.md` "Where to look" table — the subset that needs parity rows added
- `plugins/flow-next/docs/README.md` — the doc index + link conventions (relative paths, reference-table shape, R17)

**Optional** (reference as needed):
- `plugins/flow-next/skills/flow-next-deps/SKILL.md`, `flow-next-export-context/SKILL.md`, `flow-next-rp-explorer/SKILL.md`, `flow-next-worktree-kit/SKILL.md`, `flow-next-setup/SKILL.md` — descriptions/triggers for the catalog rows

## Key context
- **Coordinate with fn-54**: fn-54 R1 adds a `CLAUDE.md` "Where to look" row (`agent_docs/optimizing-skills.md`). Treat that row as fn-54-owned; do not renumber/clobber it — sequence after fn-54 lands or re-anchor on `CLAUDE.md` before editing.
- `AGENTS.md` is a symlink to `CLAUDE.md` — one edit covers both.
- Count claims must stay accurate if any wording changes the stated totals (memory: count-drift across README + manifests).
- Run `./scripts/sync-codex.sh` only if a synced file changes (these are mostly root/docs files, but verify).

## Design context
*Skip — these are markdown reference tables, no UI/design-system surface.*

## Acceptance
- [ ] A skills catalog lists all 26 skills (name · trigger · purpose · SKILL.md link); `ls -d plugins/flow-next/skills/*/ | wc -l` matches the catalog row count.
- [ ] The five previously-invisible skills appear in the README skills/commands surface and the catalog.
- [ ] `README.md` and `CLAUDE.md`/`AGENTS.md` "Where to look" tables have an identical doc-row set (or a documented deliberate divergence), without disturbing the fn-54-owned row.
- [ ] All new links are relative repo paths (R17); `bash scripts/ci_test.sh` passes.

## Done summary
Landed via PR #175 (commit 669fba2) — GitHub docs overhaul. Spec/task scaffold was never committed; deliverables shipped without flow bookkeeping. Closing retroactively.
## Evidence
- Commits:
- Tests:
- PRs: