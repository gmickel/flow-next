---
satisfies: [R12]
---

## Description

Extend `/flow-next:audit` to walk glossary terms (grep code for term + `_Avoid_` aliases; mark stale on absence; surface alias-creep) and decision entries (verify the constraint still holds; prompt for supersession on conflict).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-audit/workflow.md`, `plugins/flow-next/skills/flow-next-audit/phases.md`, possibly `plugins/flow-next/skills/flow-next-audit/SKILL.md`, regenerate Codex mirror

## Approach

- **Decision walk is automatic.** Once T1 ships and `MEMORY_CATEGORIES["knowledge"]` includes `"decisions"`, the existing memory-walk in `workflow.md:21-127` (Phase 0) picks up `decisions/` entries. Document calibration in `phases.md`: for decision entries, the per-entry judge asks "does the constraint that motivated this decision still hold?" instead of the generic "is this still relevant?". The 5 outcomes (Keep / Update / Consolidate / Replace / Delete) carry over but `Replace` for decisions means "supersede" — write a new entry pointing at the old via `superseded_by`.
- **Glossary walk is new.** Add a new phase (e.g. Phase 0.5 "Glossary scan") that runs after the memory walk:
  - Walk all `GLOSSARY.md` files via `find . -name GLOSSARY.md -not -path './node_modules/*' -not -path './.git/*'`
  - For each term in each file: `grep -rE "\\b<term>\\b" <code-paths>` (code-paths = tracked source files; exclude `.flow/`, `node_modules/`, build artifacts; respect `.gitignore` via `git ls-files | xargs grep`)
  - Zero hits AND zero `_Avoid_` alias hits → mark stale (use Edit tool on the glossary file with a `<!-- stale: <reason> -->` comment after the term, OR document a manual flow if a `flowctl glossary mark-stale` subcommand isn't shipped in T2; defer to T2 review)
  - `_Avoid_` alias creeping into new code (alias hits in code) → Phase 3 question: "alias `<X>` is appearing in code at <file:line>; rename uses to `<canonical>` or update glossary?"
- Update `SKILL.md` allowed-tools if needed (likely no change — Read/Grep/Glob/Edit already allowed via the existing `allowed-tools` frontmatter).
- Update Phase 0 prose to mention that decisions/ entries are included automatically (post-T1).
- Run `scripts/sync-codex.sh` to regenerate Codex mirror.
- **R17 compliance**: no DDD terminology in skill prose.

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-audit/workflow.md:21-127` — Phase 0 memory walk (decisions auto-included; document)
- `plugins/flow-next/skills/flow-next-audit/workflow.md:131-204` — Phase 1 investigation pattern (template for glossary walk)
- `plugins/flow-next/skills/flow-next-audit/phases.md` — phase reference + outcome calibration table (extend with decision calibration)
- `plugins/flow-next/skills/flow-next-audit/SKILL.md` — top-level skill behavior

**Optional:**
- `plugins/flow-next/scripts/flowctl.py` — `cmd_memory_mark_stale` precedent if extending to glossary stale-marking

## Acceptance

- [ ] `/flow-next:audit` walk includes glossary terms (root + subdir `GLOSSARY.md` files via `find`)
- [ ] For each term: grep tracked code files for term + `_Avoid_` aliases; absence on both → marked/flagged stale
- [ ] `_Avoid_` alias appearing in code surfaces as a Phase 3 question (interactive) or stale-flag (autofix)
- [ ] Decisions track is automatically walked once schema extension lands (T1 dep verified)
- [ ] Decision-entry per-entry judge calibrates on "constraint still holds?" — `phases.md` documents this
- [ ] `Replace` outcome for decisions = write new entry with `superseded_by: <old-id>`; old entry's `decision_status` set to `superseded`
- [ ] `phases.md` documents the new glossary phase + decision calibration
- [ ] `scripts/sync-codex.sh` regenerates Codex mirror cleanly
- [ ] No DDD jargon in skill prose (R17)
- [ ] Manual smoke: run `/flow-next:audit` on a project with stale glossary term + outdated decision; both surface in the report

## Done summary

## Evidence
