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
Wired one-line prose-contract pointers at the three emission points named by the spec (R2): make-pr workflow.md Phase 2 top (body-header rendering, near not inside the section 2.5 guardrails), tracker-sync references/comments-sync.md at structured-comment composition, and capture workflow.md Phase 2 (spec-prose synthesis). Each pointer is exactly one non-blocking line citing docs/prose.md via the standard canonical relative shape (`../../docs/prose.md` skill-root, `../../../docs/prose.md` references) with zero duplicated rule text; the tracker-sync pointer invokes prose.md's "structural contracts win" precedence and keeps marker/envelope/projection-only constraints authoritative. Regenerated the Codex mirror (R4): sync-codex.sh run twice, idempotent, all guards green — prose.md now mirrors to docs/flow-next/prose.md with its README index row, and all three pointer links were namespace-rewritten correctly. CHANGELOG.md gains a new `## Unreleased` Added entry (user-outcome-first per releasing.md's gate); no version bump. Conduct checklists for make-pr/tracker-sync/capture verified against the diff — no falsifiable assertion touched.

Pointer lines authored via the cursor-agent bridge (cursor-grok-4.6-high) per explicit routing instruction, one foreground call, verified against the edit spec with zero stray edits. Commit also carries the conductor's pre-existing fn-207.1 receipt stage lines (uncommitted on the branch at claim time).

baseline: green (test_prompt_text_pinned pre-edit OK at b02bd260)
Verify: gate classify exited FULL (force-full prefix plugins/flow-next/codex/); gate check unittest: RUN (no honorable receipt); python3 scripts/run_tests_parallel.py: files=192 ran=4505 failures=0 errors=0; uvx ruff@0.16.0 check .: all checks passed; green receipt written for gate unittest at HEAD.

## Evidence
- Commits: 7169b9e36f23fe85948107bb65ebbfbbbda45a41, f91abd74de38605247a9f9a97ec49f9c67d95986
- Tests: python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh (twice, idempotent, guards green), cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned -q, python3 -m unittest test_codex_persona_and_project_doc test_cursor_docs_contract test_chart_docs_inventory -q (review round 2)
- PRs:
stage: impl-review - ran (model: claude-fable-5, host backend, cross-family from grok-4.6 writer; NEEDS_WORK round 1 -> SHIP round 2, fixes f91abd74)
stage: plan-sync - skipped(config: planSync.enabled != true)
