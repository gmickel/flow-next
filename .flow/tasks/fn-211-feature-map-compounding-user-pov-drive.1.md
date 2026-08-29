---
satisfies: [R1, R2, R3, R4]
---
# fn-211-feature-map-compounding-user-pov-drive.1 Skill skeleton + seed mode: /flow-next:features with feature-entry contract and Doctor

## Description
Create the canonical skill `plugins/flow-next/skills/flow-next-features/` and its command shim, carrying the shared contracts (mode detection, feature-entry contract, Doctor) plus the whole seed mode. Split this way because seed + shared contracts are the cold-readable foundation the maintain mode and the consumers both point at (spec Early proof point).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-features/SKILL.md`, `plugins/flow-next/skills/flow-next-features/seed.md`, `plugins/flow-next/skills/flow-next-features/references/feature-entry-contract.md`, `plugins/flow-next/skills/flow-next-features/references/doctor-and-proof.md`, `plugins/flow-next/commands/features.md`, `plugins/flow-next/tests/test_features_skill_contract.py`
**Touches:** [plugins/flow-next/skills/flow-next-features/**, plugins/flow-next/commands/features.md, plugins/flow-next/tests/test_features_skill_contract.py]

### Approach
- SKILL.md follows the audit skill's inline shape (`plugins/flow-next/skills/flow-next-audit/SKILL.md:1-42`): frontmatter with `user-invocable: false` + `allowed-tools` (include AskUserQuestion + Task), mode detection resolved by STATE (no `.flow/features/` or explicit init intent -> seed; map present -> maintain), interaction principles, a Forbidden list, and the three-rung FLOWCTL preamble (the skill calls `flowctl memory search`/`memory add` for the drift-tag handoff - see spec Approach).
- Autonomous refusal per R1: scan the autonomy marker FAMILY (never a fixed two-var list - see memory `env-marker-gate-must-scan-the-namespace-2026-06-04`), refuse with a one-line typed report.
- Typed outcome line per the house grammar (examples: `flow-next-pilot/SKILL.md:138`, `flow-next-land/SKILL.md:78`): `FEATURES_VERDICT=<SEEDED|CLEAN|CHANGED|BLOCKED|REFUSED> features=<n> reason="<one line>"` - last line, nothing after.
- Seed mode (seed.md): interview the repo not the user (surface/run/drive/observe/isolate, ask only what cannot be observed); multi-surface repos seed per-surface feature groups under one index (spec Decision Context); write the index README (operating rules per R3: baseline preconditions, driving conventions, proof standards, feature-entry contract pointer) + one file per identified feature (top handful); PROVE every route with one live drive before it lands (partial seed lands proven features, names failures); refusal paths: no drivable surface, no usable driver on this host, broken checkout (fix or report precisely first). Live driving consumes the drive skill by pointer exactly as QA does (`flow-next-qa/workflow.md:321-329` pattern) - never duplicate ladder prose.
- references/feature-entry-contract.md: the four-H2 contract (Sub-features / How to get to it (user POV) / Driving it / Gotchas) plus the REQUIRED one-line `**Surface:**` identifier directly under the H1 paragraph (deterministic values like `web`/`cli`; the index groups by it; consumers select by surface + sub-feature IDs), with ONE worked example feature file + the index shape - written so a cold agent can seed and drive from it alone. Adapt the shape to flow-next voice; per-feature files open with H1 + one behavior paragraph; user paths, stable handles, required state, commands, observable proof; no implementation details.
- references/doctor-and-proof.md: the Doctor contract per R4 (read-only worth-driving check; run before first drive, per fresh session, after any failed drive; never drive an instance this run did not start; never kill by name; cleanup never eats evidence, verified at its named location; orphaned-port and concurrent-run cases end `blocked` per spec Edge Cases) and the proof standards (action + resulting state; side effects verified; real user paths never test-only endpoints; unreachable reported with route + unmet precondition, never verified-via-another-path).
- Command shim: copy the shape of `plugins/flow-next/commands/audit.md` (bare `name: features`).
- Behavioral test `plugins/flow-next/tests/test_features_skill_contract.py` (fn-169 model): extract + execute BOTH predicates from the skill prose - (a) the autonomy-marker scan with a NOVEL marker outside the written list (assert the refusal branch), (b) the state-routing predicate under all three cases: absent `.flow/features/` -> seed, present -> maintain, present + explicit init intent -> seed (run each in a temp dir; assert the routed mode). Then validate the worked example against the four-H2 + Surface shape and assert the `FEATURES_VERDICT=` terminal grammar is stated. This requires the mode-detection and autonomy checks to be written as executable fenced bash the test can extract - keep both predicates in single self-contained fences. Behavior assertions only - no prose pins (G2).
- Canonical prose uses Claude-native tool names with portable-host fallback clauses (CLAUDE.md cross-platform checklist item 2).
## Acceptance
- [ ] Skill directory exists with SKILL.md + seed.md + the two references; command shim present
- [ ] Mode detection is state-resolved; autonomous markers refuse via namespace scan with a typed one-line report
- [ ] Seed proves every landed route by one live drive; partial-seed and the three refusal paths are stated; drive skill consumed by pointer
- [ ] Feature-entry contract carries the four H2s in order plus the required `**Surface:**` line, with a worked example; index operating rules cover preconditions, conventions, proof standards, and surface grouping/selection semantics
- [ ] Doctor contract carries all R4 invariants incl. orphan/concurrent `blocked` outcomes
- [ ] `FEATURES_VERDICT=` terminal line grammar stated and used by every path
- [ ] `test_features_skill_contract.py` executes the autonomy predicate with an out-of-list marker AND the state-routing predicate across absent/present/present-plus-init (asserting seed/maintain/seed), validates the worked example shape, and asserts the terminal grammar - all behavioral, no prose pins
- [ ] No implementation code; no file paths in the map contract beyond the `.flow/features/` layout itself
## Done summary
Built the /flow-next:features skill foundation: SKILL.md (state-resolved seed/maintain mode detection and the autonomy-namespace refusal, both as executable bash fences; FEATURES_VERDICT terminal grammar; forbidden list), seed.md (six phases with Done-when gates: repo interview, checkout health + Doctor, top-handful identification, prove-every-route live driving by pointer to flow-next-drive, map write, cleanup + verdict), references/feature-entry-contract.md (four-H2 contract + required Surface line, worked example feature file and index shape), references/doctor-and-proof.md (Doctor checks/ownership/orphan/concurrent/wedged-UI rules + proof standards), the command shim, and test_features_skill_contract.py (9 behavioral tests: executes the autonomy fence with a novel out-of-list marker, executes mode routing across absent/present/present-plus-init, validates the worked example shape, asserts the terminal grammar). Implemented by a grok-4.6 bridge worker in an isolated worktree; conductor in-host review verdict SHIP; focused test green on the integrated target.

stage: plan-sync - skipped(config: planSync.enabled != true)
stage: impl-review - ran (in-host, verdict SHIP) (model: claude-fable-5)
## Evidence
- Commits: e1eb4f6e
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_features_skill_contract -q  # 9 tests OK (integrated target)
- PRs: