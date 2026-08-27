---
satisfies: [R2, R4]
---
# fn-207-prose-contract-for-agent-emitted.2 Emission-point pointers + mirror sync + CHANGELOG

## Description
Wire one-line pointers to docs/prose.md at the three emission points, regenerate the Codex mirror, and stage the CHANGELOG entry (R2, R4). Depends on .1 (the doc must exist for link guards to pass).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-make-pr/workflow.md`, `plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md`, `plugins/flow-next/skills/flow-next-capture/workflow.md`, `plugins/flow-next/codex/**` (regenerated), `CHANGELOG.md`
**Touches:** [plugins/flow-next/skills/flow-next-make-pr/workflow.md, plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md, plugins/flow-next/skills/flow-next-capture/workflow.md, plugins/flow-next/codex/**, CHANGELOG.md]

### Approach
- One line per site, phrased as a non-blocking aside ("Artifact prose follows `<relative-path>/docs/prose.md`; proceed without it if the doc is absent") — never a precondition. Landing sites:
  - make-pr `workflow.md:378-380` (top of Phase 2, body-header rendering) — near, not inside, the §2.5 guardrails
  - tracker-sync `references/comments-sync.md:~38` (structured-comment composition)
  - capture `workflow.md:209-211` (Phase 2 goal line, spec-prose synthesis)
- Tracker-sync pointer precedence (R2 boundary, review-hardened): the pointer line itself defers to the surface's structural contracts — the dedup marker stays the first line and unchanged (`comments-sync.md:75-80`, `:206-210`), projection-only source-truth is never overridden (`:234-238`), and outcome-first applies only when a sourced outcome exists in the payload; never invent outcome prose. Phrase the pointer so prose.md guides wording within the existing envelope, not instead of it.
- Link shape: standard canonical relative depth (`../../docs/prose.md` from a skill root file, `../../../docs/prose.md` from a references/ file) so the mirror's link-depth rewrite covers it — never hand-roll a different shape.
- Run `./scripts/sync-codex.sh` TWICE (idempotency); commit the mirror diff with the canonical change. A guard failure means fix content / extend the transform, never relax the guard.
- Conduct-checklist pass per touched skill (capture, make-pr, tracker-sync) — verify no falsifiable assertion breaks; a one-line pointer should not change any contract.
- CHANGELOG: new `## Unreleased` section at top (none exists currently — top is 4.6.0); one user-outcome-first entry per releasing.md's gate, plain hyphens.

### Investigation targets
**Required** (read before editing):
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md:378-450` — Phase 2 render steps (pointer landing)
- `plugins/flow-next/skills/flow-next-tracker-sync/references/comments-sync.md:30-60,75-80,206-238` — comment composition + marker/envelope contracts the pointer must defer to
- `plugins/flow-next/skills/flow-next-capture/workflow.md:205-220` — Phase 2 synthesis (pointer landing)
- `scripts/sync-codex.sh:208-260` — docs-mirror link-depth rewrite rules (link shape must match)

**Optional:**
- `agent_docs/conduct/make-pr.md`, `agent_docs/conduct/tracker-sync.md`, `agent_docs/conduct/capture.md` — checklists to verify against
- `.flow/memory/bug/build-errors/mirror-regen-exposes-latent-canonical-2026-06-11.md` — mirror-regen gap pattern

### Key context
- G1: each pointer is exactly one line; no rule text duplicated into skill prose.
- None of the target files are prompt-text-pinned (verified at plan time).
- Full gate before handoff: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .` (docs-tree edits are not exempt).

### Acceptance
- [ ] Three one-line pointers landed at the named sites; each phrased as non-blocking; zero duplicated rule text
- [ ] Tracker-sync pointer defers to structural contracts: marker stays first-line/unchanged, projection-only preserved, no invented outcome prose
- [ ] `./scripts/sync-codex.sh` run twice: idempotent, all guards green, mirror diff committed with the canonical change
- [ ] Conduct checklists for capture/make-pr/tracker-sync verified against the diff (no broken assertions)
- [ ] `CHANGELOG.md` gains `## Unreleased` with one user-outcome-first entry; no version bump anywhere
- [ ] Full gate green: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`
## Acceptance
- [ ] Three one-line pointers landed at the named sites; each phrased as non-blocking; zero duplicated rule text
- [ ] Tracker-sync pointer defers to structural contracts: marker stays first-line/unchanged, projection-only preserved, no invented outcome prose
- [ ] `./scripts/sync-codex.sh` run twice: idempotent, all guards green, mirror diff committed with the canonical change
- [ ] Conduct checklists for capture/make-pr/tracker-sync verified against the diff (no broken assertions)
- [ ] `CHANGELOG.md` gains `## Unreleased` with one user-outcome-first entry; no version bump anywhere
- [ ] Full gate green: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
