---
satisfies: [R14, R15]
---

## Description

Repo documentation surface + the positioning/decision record. Mechanical, low-risk prose edits across the named doc files, plus one new subsystem reference. The version bump and flow-next.dev site live in .9 (this task does NOT bump the version).

**Size:** M-L (mechanical doc edits; split out from .9's release mechanics)
**Files:** NEW `plugins/flow-next/docs/tracker-sync.md`; edits to `docs/README.md`, `docs/flowctl.md`, `docs/teams.md`, `docs/architecture.md`, `docs/ralph.md`, root `README.md`, `CLAUDE.md`, `GLOSSARY.md`, `.flow/usage.md`, `CHANGELOG.md`.

## Approach

From the docs-gap matrix:
- **NEW `docs/tracker-sync.md`** — subsystem reference: projection-not-coordination, discovery ceremony, sync-state schema (tracker id / lastSyncedAt / merge-base), transport ladder (MCP → GraphQL → no-op), lifecycle sync points, Ralph-safe conflict queueing.
- **`docs/README.md`** — add a Subsystem-references row for tracker-sync.md.
- **`docs/flowctl.md`** — new `### tracker-sync` subsection (after `### prospect`) documenting the .1 `sync` helpers; add the new `tracker.*` config keys (follow the `planSync.*` row pattern).
- **`docs/teams.md`** — Symphony contrast bullet under "What flow-next does *not* replace"; a tracker-bridge item in the adoption ladder (Quarter 1); opt-in `(+ optional tracker sync)` annotations on the lifecycle walkthrough (capture/plan/work/spec-completion-review/make-pr).
- **`docs/architecture.md`** — add `tracker.id` / `lastSyncedAt` / merge-base to the spec-JSON "New fields" list.
- **`docs/ralph.md`** — a paragraph: tracker-sync conflicts queue to deferred-decisions, never block, no `flowctl block` needed.
- **root `README.md`** — Commands-table row for `/flow-next:tracker-sync` + Where-to-look row; **explicitly distinguish it from `/flow-next:sync` (plan-sync)** so the two aren't confused (also note the distinction in `.flow/usage.md` and `docs/flowctl.md`).
- **`CLAUDE.md`** — a Where-to-look table row for tracker-sync.md.
- **`GLOSSARY.md`** — add `Tracker`, `merge-base snapshot`, `discovery ceremony`, and `tracker-key handle` (the hybrid id model) (terms R15 missed).
- **Hybrid id model (R16)** — document in `docs/tracker-sync.md` + `flowctl.md` + `architecture.md`: tracker-first specs are canonically `wor-17-slug` (tasks `wor-17-slug.M`; bare `wor-17`/`wor-17.M` resolve as aliases); flow-first keep `fn-NN` + a resolvable `tracker.identifier` display alias (`WOR-17`); `work/plan/show wor-17` resolve (case-insensitive); ids never rename; **one-team-per-repo** boundary; `fn-N` allocation counts `fn-*` only. `architecture.md` notes the widened resolver/canonicalizer + origin-branched generator.
- **`.flow/usage.md`** — new `# Tracker sync` block (after `# Prospect`).
- **`CHANGELOG.md`** — new version entry, `### Added` (the bridge) + `### Changed` (lifecycle skills gain opt-in touchpoints).
- **Positioning/decision (R14):** ensure teams.md states projection-not-coordination + Linear-first; verify the existing memory decision `tracker-sync-is-projection-not-2026-06-01` covers it.

## Investigation targets

**Required:**
- `plugins/flow-next/docs/README.md`, `flowctl.md` (`### prospect` + config rows), `teams.md` ("does not replace" + adoption ladder + walkthrough), `architecture.md` (New-fields list), `ralph.md` (deferred-decisions section)
- root `README.md` (Commands + Where-to-look), `CLAUDE.md` (Where-to-look table), `GLOSSARY.md`, `.flow/usage.md` (`# Prospect` block pattern), `CHANGELOG.md`

## Acceptance

- [ ] `docs/tracker-sync.md` created + linked from the doc index; flowctl.md / teams.md / architecture.md / ralph.md / root README / CLAUDE.md / GLOSSARY / `.flow/usage.md` / CHANGELOG all updated per the matrix [R15]
- [ ] Docs explicitly distinguish `/flow-next:tracker-sync` (the bridge) from `/flow-next:sync` (plan-sync) in README + `.flow/usage.md` + flowctl.md [R15]
- [ ] teams.md documents projection-not-coordination + Symphony contrast + Linear-first; decision recorded (memory entry verified) [R14]
- [ ] GLOSSARY gains Tracker, merge-base snapshot, discovery ceremony, tracker-key handle [R15]
- [ ] Hybrid id model documented (tracker-first canonical `wor-17-slug` + tasks `wor-17-slug.M`, bare `wor-17`/`wor-17.M` aliases; flow-first `fn-NN` + `tracker.identifier` alias; `work/plan/show wor-17` resolve; no rename; one-team-per-repo) in tracker-sync.md + flowctl.md + architecture.md [R15]
- [ ] No version bump in this task (done in .9); docs match the shipped behavior of .1–.7

## Done summary
Documented the fn-52 tracker-sync bridge across the repo docs surface: new `docs/tracker-sync.md` subsystem reference (projection-not-coordination, discovery ceremony, hybrid id model, sync-state schema, transport ladder, lifecycle touchpoints, Ralph-safe conflict queueing), plus edits to flowctl.md (sync subsection + tracker.* config keys + spec create --tracker-first), teams.md (Symphony-contrast bullet + adoption-ladder item + opt-in walkthrough annotations), architecture.md (spec-JSON tracker fields + widened resolver), ralph.md (conflicts queue, never block), root README + .flow/usage.md (distinguish /flow-next:tracker-sync from /flow-next:sync), CLAUDE.md + docs/README.md index rows, GLOSSARY (4 new terms), and an Unreleased CHANGELOG entry. No version bump (fn-52.9) and no flow-next.dev (fn-52.11).
## Evidence
- Commits: 578b47acde3a7681eec6b1d2ca8d69e5c1775f7c
- Tests: flowctl triage-skip (docs-only release-chore → SHIP)
- PRs: