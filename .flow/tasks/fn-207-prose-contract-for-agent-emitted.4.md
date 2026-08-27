---
satisfies: [R5]
---
# fn-207-prose-contract-for-agent-emitted.4 Full pointer coverage: 11 surfaces + prose.md scope correction

## Description
Wire the R5 pointer set — one-line non-blocking asides at every remaining artifact-prose emission surface — correct prose.md's scope sentence, regenerate the mirror, and extend the CHANGELOG entry. Depends on .3 (agents/ docs-link transform + guard must exist before agent-file pointers land).

**Size:** M
**Files:** 11 pointer sites + `plugins/flow-next/docs/prose.md` + `CHANGELOG.md` + `plugins/flow-next/codex/**` (regenerated)
**Touches:** [plugins/flow-next/skills/flow-next-interview/references/write-back.md, plugins/flow-next/agents/pr-comment-resolver.md, plugins/flow-next/skills/flow-next-plan/steps.md, plugins/flow-next/skills/flow-next-chart/references/briefing-and-reopen.md, plugins/flow-next/skills/flow-next-strategy/references/first-run.md, plugins/flow-next/skills/flow-next-strategy/references/update.md, plugins/flow-next/skills/flow-next-qa/references/bug-filing.md, plugins/flow-next/skills/flow-next-land/workflow.md, plugins/flow-next/skills/flow-next-prospect/workflow.md, plugins/flow-next/skills/flow-next-prime/workflow.md, plugins/flow-next/skills/flow-next-audit/phases.md, plugins/flow-next/agents/worker.md, plugins/flow-next/docs/prose.md, CHANGELOG.md, plugins/flow-next/codex/**]

### Approach
- One line per site, same non-blocking shape as the shipped three ("Artifact prose follows `<relative-path>` ... proceed without it when the doc is absent"). Landing sites and link depths (from the enumeration sweep):
  1. interview `references/write-back.md` ~L100 (fill-section-bodies step) — `../../../docs/prose.md`
  2. `agents/pr-comment-resolver.md` §5 compose-the-reply — `../docs/prose.md` (agents/ is a SIBLING of docs/: one level up only)
  3. plan `steps.md` Step 5 (top of the plan-content authoring) — `../../docs/prose.md`
  4. chart `references/briefing-and-reopen.md` Phase 4 rationale step — `../../../docs/prose.md`
  5. strategy `references/first-run.md` section-authoring step — `../../../docs/prose.md`
  6. strategy `references/update.md` section-editing step — `../../../docs/prose.md`
  7. qa `references/bug-filing.md` finding-body template intro — `../../../docs/prose.md`
  8. land `workflow.md` post-merge comment-synthesis step ~L728 — `../../docs/prose.md`
  9. prospect `workflow.md` Phase 2 candidate-prose step ~L361 — `../../docs/prose.md`
  10. prime `workflow.md` §5.5.2 propose-terms step — `../../docs/prose.md`
  11. audit `phases.md` §Replace/§Harden authoring (one pointer where the three authoring sections share a head, or at §Replace if no shared head) — `../../docs/prose.md`
  12. `agents/worker.md` write-summary step ~L425 — `../docs/prose.md`
- Surface-contract deference where the surface has structural contracts (land's tracker comment: marker/projection rules, same clause shape as tracker-sync's pointer; others plain).
- prose.md line 3: replace the "Other prose surfaces (interview's spec write-back, resolve-pr replies, the visual digest) are governed by the same rules but do not carry pointers yet." sentence — coverage is now complete; the visual digest is excluded as ephemeral chat output by contract (never a written artifact). Name the emission-point classes rather than enumerating all twelve skills in the intro.
- CHANGELOG: EXTEND the existing `## Unreleased` entry (same feature, wider coverage) — do not add a second entry; keep it em-dash-free per prose.md rule 9 (round-1 review lesson).
- Run `./scripts/sync-codex.sh` TWICE; agent-file pointers must come out rewritten in the mirror (R6 transform) and all guards green. Commit mirror diff with the canonical change.
- Conduct-checklist pass per touched skill with a checklist (interview, plan, chart, strategy, qa, land, prospect, prime, audit, resolve-pr, work) — verify no falsifiable assertion breaks; pointers are non-contractual asides.

### Investigation targets
**Required** (read before editing):
- The three shipped pointers (make-pr workflow.md:382, tracker-sync references/comments-sync.md:47, capture workflow.md:213) — the exact shape to replicate
- `scripts/sync-codex.sh` — the .3-extended agents transform (verify the depth it expects)
- Each landing site listed above (read the surrounding step before placing the line)

**Optional:**
- `agent_docs/conduct/` — the eleven checklists to verify against

### Key context
- G1: one line per site, no rule text duplicated. None of the 13 files is prompt-text-pinned.
- agents/*.md model fields and body must stay host-neutral (Cursor/Droid/Grok read canonical as-is; OpenCode copies agent bodies byte-identical — the pointer degrades silently there by design).
- Full gate before handoff: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`.

### Acceptance
- [ ] All 12 pointer lines landed (11 surfaces; strategy has two reference files), each one line, non-blocking, no duplicated rule text
- [ ] prose.md scope sentence corrected: complete coverage, visual excluded as ephemeral-by-contract
- [ ] `./scripts/sync-codex.sh` run twice: idempotent, guards green, agent-file pointers rewritten in the mirror, mirror diff committed
- [ ] Conduct checklists for all touched skills verified (no broken assertions)
- [ ] CHANGELOG `## Unreleased` entry extended in place (single entry, em-dash-free); no version bump
- [ ] Full gate green: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`

## Acceptance
- [ ] All 12 pointer lines landed (11 surfaces; strategy has two reference files), each one line, non-blocking, no duplicated rule text
- [ ] prose.md scope sentence corrected: complete coverage, visual excluded as ephemeral-by-contract
- [ ] `./scripts/sync-codex.sh` run twice: idempotent, guards green, agent-file pointers rewritten in the mirror, mirror diff committed
- [ ] Conduct checklists for all touched skills verified (no broken assertions)
- [ ] CHANGELOG `## Unreleased` entry extended in place (single entry, em-dash-free); no version bump
- [ ] Full gate green: `python3 scripts/run_tests_parallel.py` + `uvx ruff@0.16.0 check .`

## Done summary
Landed all 12 remaining prose-contract pointer lines (11 surfaces; strategy has two reference files): interview write-back, resolve-pr replies (agents/pr-comment-resolver.md), plan Step 5, chart briefing, strategy first-run + update, qa bug filing, land verdict comment (structural-contracts-win shape deferring to the merge-evidence gate and projection rules), prospect candidates, prime glossary definitions, audit memory-entry authoring, and the worker done summary (agents/worker.md). Corrected prose.md's intro to name emission-point classes, state complete coverage, and exclude the visual digest as ephemeral-by-contract. Regenerated the codex mirror (sync-codex twice, idempotent, all guards green); the agent-file pointers came out rewritten to `../docs/flow-next/prose.md` in both TOMLs, the first live exercise of the fn-207.3 agents transform. Extended the CHANGELOG `## Unreleased` entry in place, em-dash-free. Conduct checklists for all 11 touched skills verified: pointers are non-contractual one-line asides, no falsifiable assertion breaks.

baseline: green (sync-codex x2 rc=0/0, test_prompt_text_pinned rc=0 pre-edit)

Pointer authoring bridged to cursor-agent (cursor-grok-4.6-high) per explicit routing instruction; bridge output was clean on first pass (13 files, exact placements); host applied two placement corrections (chart and qa pointers moved above their colon-introduced blocks) and dropped a temporal "now" in prose.md.

stage: impl-review - skipped(policy: host-deferred - conductor owns the gate)
## Evidence
- Commits: c20fcc96ae027fe828fe9fe07cf89dc18492b52f, cf603095337729aca1f9e44391136802fe291f49
- Tests: python3 scripts/run_tests_parallel.py (4505 ran, 0 failures), uvx ruff@0.16.0 check ., ./scripts/sync-codex.sh x2 (idempotent, guards green; re-run x2 after round-1 fixes), cd plugins/flow-next/tests && python3 -m unittest test_prompt_text_pinned -q
- PRs:
stage: impl-review - ran (model: claude-fable-5, host backend, cross-family from grok-4.6 writer; NEEDS_WORK round 1 -> SHIP round 2, fixes cf603095)
stage: plan-sync - skipped(config: planSync.enabled != true)
