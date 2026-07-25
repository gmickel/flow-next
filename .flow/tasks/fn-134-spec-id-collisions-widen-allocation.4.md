---
satisfies: [R15, R17, R18]
---
# fn-134-spec-id-collisions-widen-allocation.4 Repo docs: correct GitHub/GitLab claims, Notable updates surface, CHANGELOG

## Description
Repo documentation pass, including the correction of every statement that GitHub and GitLab cannot use tracker-first, and the new **Notable updates** surface on the docs home.

**Size:** M
**Files:**
- `plugins/flow-next/docs/{tracker-sync.md,teams.md,flowctl.md,architecture.md,README.md}`
- `plugins/flow-next/skills/flow-next-tracker-sync/{SKILL.md,steps.md,references/gitlab.md,references/identity.md,references/github.md}`
- `GLOSSARY.md`, `CHANGELOG.md`
- `.flow/usage.md` + `plugins/flow-next/templates/usage.md` (dual copy, keep identical)
- `agent_docs/releasing.md`
- `plugins/flow-next/codex/**` (regenerated)

### Approach

**Correct the false statements first (R18).** These currently say GitHub/GitLab are flow-first only, which synthetic keys make untrue:
- `docs/tracker-sync.md:47`
- `skills/flow-next-tracker-sync/SKILL.md:142`
- `skills/flow-next-tracker-sync/steps.md:277-290` (the "GitLab grabs go FLOW-FIRST" block)
- `skills/flow-next-tracker-sync/references/gitlab.md:365-378`
- `references/github.md` if an equivalent exists
Keep the accurate part (these are not literal `KEY-N` identifiers); drop the "therefore flow-first only" conclusion and document the synthetic mint.

**Substance updates:**
- `docs/tracker-sync.md` - hybrid id model gains the synthetic-key table, the `tracker.specIds` gate, the GitLab `iid`-vs-global-id re-point hazard, and a short duplicate-ordinal / disambiguation note.
- `docs/teams.md:425-429` - tracker-keyed ids are the recommended team default, and why (collision avoidance).
- `docs/flowctl.md` - `tracker.specIds` row alongside the other `tracker.*` keys; note that skills route to `--tracker-first` automatically. **The `validate` JSON example at `:693-698` shows the collision as a `root_error` and goes stale** - update it to the warning behavior.
- `docs/architecture.md:82-89` - id scheme, synthetic keys, and one line on the widened allocation.
- `GLOSSARY.md:133-135` - the tracker-key handle entry currently implies only Linear/Jira mint; extend for synthetic keys and note that `fn` remains the only globally reserved prefix.
- `.flow/usage.md` + template - one line that tracker-keyed ids coexist and resolve. Keep both copies identical; this file is deliberately terse.

**Notable updates surface (R17).** Add a short, append-only section to `plugins/flow-next/docs/README.md` (the GitHub docs entry point): behavior-affecting changes and new opt-in defaults, one line each plus how to enable. Seed it with `tracker.specIds`. Document its own format inline so later releases append consistently, and add updating it as a step in `agent_docs/releasing.md` so it does not decay.

**CHANGELOG** entry under `## [Unreleased]`. No version bump.

### Investigation targets

**Required** (read before coding):
- `plugins/flow-next/docs/tracker-sync.md:40-70` - hybrid id model
- `plugins/flow-next/docs/flowctl.md:690-700` and the `tracker.*` config table
- `plugins/flow-next/docs/README.md` - where a Notable updates section belongs
- `agent_docs/releasing.md` - the release step list

**Optional** (reference as needed):
- `GLOSSARY.md:130-140`
- `plugins/flow-next/docs/architecture.md:80-95`

### Key context

Document the behavior that actually shipped in tasks `.1`-`.3`. Read the landed config and CLI surface rather than copying this task file.

Sweep by grep, not by memory: the named-file list above came from scouting, but this repo has repeatedly hit secondary surfaces that a named sweep missed.

The codex mirror is generated. Never hand-edit; run `sync-codex.sh` twice and commit the diff.

## Acceptance

- [ ] Every GitHub/GitLab "cannot do tracker-first" statement is corrected; a grep sweep proves none remain, and the sweep command and output are recorded in the task evidence (R18).
- [ ] `docs/tracker-sync.md`, `docs/teams.md`, `docs/flowctl.md`, `docs/architecture.md`, `GLOSSARY.md`, and both `usage.md` copies reflect `tracker.specIds`, synthetic keys, and the widened allocation (R15).
- [ ] The stale `validate` root-error example in `docs/flowctl.md:693-698` shows the new warning behavior.
- [ ] A **Notable updates** section exists on `plugins/flow-next/docs/README.md`, is seeded with `tracker.specIds`, documents its own append format, and is named as a step in `agent_docs/releasing.md` (R17).
- [ ] Both `usage.md` copies remain byte-identical.
- [ ] `CHANGELOG.md` has an entry under `## [Unreleased]`; no version bump, no manifest touched.
- [ ] `./scripts/sync-codex.sh` run twice: idempotent, guards green, mirror diff committed.
- [ ] Full gate green: `python3 scripts/run_tests_parallel.py`.


## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
