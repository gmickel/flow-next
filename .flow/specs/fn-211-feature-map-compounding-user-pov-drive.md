# Feature map: compounding user-POV drive knowledge

## Goal & Context

<!-- Goal & Context: 60% [user], 40% [paraphrase] -->

Today every `/flow-next:qa` run re-derives "how do I even reach this screen" from scratch. That is correct but nothing compounds: the navigation knowledge, the gotchas, and the health-check discipline evaporate when the run ends, and the next run pays for them again. [paraphrase]

The feature map is the compounding layer: a committed, maintained directory (`.flow/features/`, beside `.flow/memory/`) that records, from the user's point of view, what each user-facing feature is, how a user reaches it, how an agent drives it, and what traps waste a verification run. QA and drive stop re-deriving navigation; work can reuse it to verify what it built. [user]

The one-line split that keeps every existing contract intact: **map = how a user gets there (compounds). Spec = what to prove this time. Live drive = proof.** [user]

## Architecture & Data Models

<!-- Architecture: 70% [user], 30% [inferred] -->

- `.flow/features/README.md` — the index and operating rules: what the directory is, baseline preconditions (launch target, disposable data/profile, seed state), driving conventions (stable handles — roles, accessible names, prompt strings — over coordinates; commands treated as literal), proof standards (capture the user action and the resulting state, not just the final screen; verify side effects beside what is visible; exercise real user paths, never test-only endpoints; report an unreachable path with the attempted route and unmet precondition, never as verified-via-another-path), and the feature-entry contract. A cold agent must be able to drive from the map alone. [paraphrase]
- One file per user-facing feature. Each opens with an H1 title plus one paragraph of user-visible behavior, then exactly four H2s in order: `Sub-features` (short IDs, one line each), `How to get to it (user POV)` (every user entry point), `Driving it` (starts with `Preconditions:`, then labeled bullets pairing each user action with an exact command and its observable result), `Gotchas` (traps that waste or invalidate a run). User paths, stable handles, required state, commands, observable proof — no implementation details. [user]
- The map is **committed** (it is maintained team knowledge, like memory — not a runtime receipt). [paraphrase]
- Consumers discover it by existence check only: no config key, no registration. Absent directory = exactly today's behavior at zero added cost. [paraphrase]

## Edge Cases & Constraints

- A repo with no drivable user surface (a pure library) → seed refuses honestly with the reason instead of manufacturing a map - and the same refusal covers a real surface with no usable driver on this host (name the missing driver).
- A checkout that does not build or start as-is → fix that first or report it precisely; never write a map against a broken base (it teaches wrong steps). A genuinely irrelevant missing asset may be created as clearly-marked verification scaffolding and removed in cleanup.
- Isolation: state whether two instances can run side by side (ports, data dirs, profiles); when they cannot, the map says so and a run refuses to double-drive a shared instance rather than corrupt the user's session.
- A wedged UI state on a healthy process (Doctor cannot see it) → reset to a known state or relaunch rather than hoping.
- An orphaned instance from a crashed prior run (port owned by a process this run did not start) → Doctor reports it and the run ends `blocked` with the reclaim instruction for the human; the kill-by-name ban holds even for our own wreckage.
- Two concurrent runs: each run's disposable profile/port (the index's baseline preconditions) is the isolation mechanism; where the app cannot run twice, Doctor's owned-port check fails and the second run ends `blocked` - never a shared drive.
- A source reader that errors or times out for one feature → that feature is marked blocked-for-this-pass and named in the outcome; the pass continues for the rest.
- Removing a feature the product deleted is a source-confirmed deletion - no live drive required to prove an absence.

## Acceptance Criteria

- **R1:** A new user-invoked skill `/flow-next:features` with two modes resolved by state: no `.flow/features/` (or explicit init intent) → seed; map present → maintain. It is never dispatched by pilot, land, Ralph, or any autonomous driver - under any autonomy marker (scan the marker family, never a fixed variable list) it refuses with a one-line typed report - and every run ends with a typed outcome line so a host loop can drive it on a cadence. [paraphrase]
- **R2:** Seed interviews the repo, not the user — surface, run command, drive mechanism, observable evidence, isolation — asking only what it cannot observe, then writes the index plus one file per identified user-facing feature (the top handful to start; the map exists so later passes extend it). Every seeded route is proven by one live drive before it lands: nothing enters the map that was not driven once, and a cleanup that eats the proof fails the step. On a partial seed (some routes prove, one fails), the proven features land and the failures are reported by name - never all-or-nothing discard, never an undriven entry.
- **R3:** The index carries the operating rules (baseline preconditions, driving conventions, proof standards, feature-entry contract) so a cold agent can drive from the map alone; feature files follow the four-H2 contract exactly. [user]
- **R4:** The Doctor contract: one read-only check answering "is this instance worth driving" (right build/version, port owned by this run, auth valid) — run before the first drive, on each fresh session, and again after any failed drive. Never drive an instance this run did not start; never kill by process name — kill what this run started; cleanup removes instances and scratch state, never evidence, verified at its named location after teardown. [user]
- **R5:** Maintain is the audit-shaped pass: index hygiene → one read-only source reader per feature, dispatched concurrently (readers never drive, never edit) → reconcile (merge recipes into as few app states as practical, spot-check cited drift, sweep recent churn for unmapped user-facing surfaces — a concrete source path required before calling one missing) → one live pass covering every feature (required even when source looks clean) → triage (wrong user-POV description = doc drift, fix the map; working behavior the harness cannot drive = harness gap, fix it and re-drive before shipping; broken app behavior = product bug, report it, keep it out of the PR) → ship or stop. Outcomes are exactly `clean` (no branch, no PR), `changed` (one PR of proven map/harness corrections only), or `blocked` (names what blocked); a feature is `verified-unreachable` only with the concrete prerequisite and the route attempted — an unstated prerequisite is itself drift. [user]
- **R6:** Maintain's edit scope is the map directory and any harness scripts it owns — never product code. [user]
- **R7:** `/flow-next:qa` and `flow-next-drive` consume the map by pointer when it exists — navigation, preconditions, and gotchas — while the spec still supplies this run's ACs/R-IDs and live captured evidence remains the only basis for SHIP. A QA run that finds a stale route files it as a finding for the next maintain pass; it never edits the map mid-run. Absent map: both behave exactly as today. [user] [strategy:Self-improving through normal work]
- **R8:** The docs story is planned as part of the feature, not left to the release sweep: the plan decides deliberately where the feature map sits in the repo docs and on flow-next.dev — its place in the understand narrative (how work gets proven, what compounds) and the guides layer (live QA, choosing your route), not only a skill reference page — because this is a new, substantial capability people should discover through the site's story, with the release-time big-picture sweep as the backstop, not the plan. [user]

## Boundaries

- No autonomous trigger of any kind: not a pilot stage, not a land tail step, not a Ralph iteration, no post-merge hook. Cadence belongs to the human or their host loop. [user]
- The map is never the intent source: specs and acceptance criteria stay the contract of what to prove; the map is how-to-drive only. [user]
- User navigation never moves into spec Quick commands — those stay the code gate (focused tests / lint / suite); the map is the live-user gate. Different consumers. [user]
- No frozen this-run scenarios in the map — they rot and miss the change under test. [user]
- Not a merge with `/flow-next:map` (the code-POV clawpatch index) — different layer, both stay. [paraphrase]
- flowctl plumbing minimal to none in v1: the skill validates the four-H2 shape itself; a deterministic validator can follow once the format proves out. [paraphrase]
- Maintain is not a second QA pass and never replaces QA. [user]

## Strategy Alignment

Active tracks served by this plan:
- **Self-improving through normal work** - the map is a fifth compounding surface beside memory, glossary, decisions, and strategy: seeded once, kept honest by an audit-shaped loop, read by QA/drive so navigation knowledge stops evaporating per run.

## Decision Context

- One skill, two state-resolved modes, rather than separate create/maintain commands — fewer surfaces, and the state (map present or not) already answers which mode is meant. [paraphrase]
- Consumers gate on directory existence, not config — zero cost and zero behavior change for every repo without a map, and no knob to document. [paraphrase]
- The map is committed team knowledge (like memory), not runtime state (like receipts) — its whole value is surviving the session and the machine. [user]
- The maintain loop's unit of rigor is the feature, not every sentence: cover every feature file from source and exercise every feature live, without terminalising every bullet. [paraphrase]
- Worker consumption during implementation is deferred out of v1 (resolved at plan time): QA/drive are the proven consumers; a work-prose pointer can follow once the map exists in anger.
- Maintain's `changed` outcome ships as a chore PR with a hand-written body matching the make-pr structure (summary / what changed / per-feature outcomes / evidence pointers) - never `/flow-next:make-pr` (it requires a spec behind the diff) and never a merge (house rule; land or the human merges).
- A stale route QA finds is filed as a `knowledge`-track memory entry tagged `feature-map-drift`; maintain's index-hygiene step searches that tag. No new queue file, no memory-schema change.
- QA's map read happens in its discover phase (existence check, then load navigation/preconditions/gotchas) so scenario derivation can cite map-sourced commands instead of re-deriving routes.
- A multi-surface repo (web + CLI) seeds per-surface feature groups under the one index; every feature file carries a required one-line `**Surface:**` identifier directly under its H1 paragraph (e.g. `web`, `cli`), the index groups entries by that identifier, and consumers select features deterministically by surface + sub-feature IDs - enumeration is observation, not a question for the user.
- Maintain run notes and live-pass evidence live under the gitignored per-run tmp convention the QA skill already uses; the `changed` PR carries `.flow/features/**` plus owned harness corrections (a proven harness fix must ship, or a clean checkout stays undrivable); run notes, scratch state, and evidence stay out. `blocked` is terminal for the invocation - the next run re-enters fresh (maintain is idempotent), no resume state.
- Full launch, not the experimental tier: R8's docs story (understand narrative + guides) is exactly what the experimental tier skips, and this is a capability people should discover through the site.

## Approach

- One new canonical skill directory with the house three-file split: an overview SKILL.md (frontmatter, mode detection with the autonomous-refusal marker scan, interaction principles, forbidden list), a seed workflow, and a maintain workflow - plus gated references for the feature-entry contract (a worked four-H2 example the skill and readers share) and the Doctor/proof standards. A flat command shim follows the existing shim template.
- Seed and maintain follow the audit skill's shape (host judgment, phase Done-when gates); the live pass consumes the drive skill's driving flow by pointer, exactly as QA does - never duplicated prose.
- Maintain's per-feature source readers are read-only scout dispatches reusing the existing read-only dispatch shape (portable-host fallback clause included); no new agent, so the OpenCode agent allowlist is untouched.
- The typed outcome line follows the house grammar: `FEATURES_VERDICT=<SEEDED|CLEAN|CHANGED|BLOCKED|REFUSED> features=<n> reason="<one line>"`, the last line of output.
- The skill needs no flowctl calls except `memory search`/`memory add` for the drift-tag handoff - the standard three-rung preamble appears in EVERY top-level file that invokes flowctl (SKILL.md and maintain.md), per house convention.
- Behavioral test coverage (fn-169 model - behavior, never prose pins): a focused unit test extracts and EXECUTES both skill predicates - the autonomy-marker scan against an env carrying a marker OUTSIDE the written list (asserting refusal), and the state-routing predicate for all three cases (absent `.flow/features/` routes to seed; present routes to maintain; present plus explicit init intent routes to seed) - then validates the worked example in the feature-entry contract against the four-H2 shape + required Surface line, and asserts the terminal `FEATURES_VERDICT=` grammar is stated as the last-line contract. Finalization additionally runs a NON-REFUSAL cold seed smoke (a real map seeded against a small target) plus the repo full gate.
- Registration trio for the codex mirror: the openai.yaml generation call, the required-skills roster entry, and a mirror regen (twice, idempotent); manifest description counts swept manually.

## Docs integration (R8 - decided placement)

Repo docs (shipped with the feature): the self-improving doc gains the feature map as a fifth loop (its most load-bearing edit); the architecture doc's `.flow/` layout gains a features section beside the charts one; the skills roster and docs index gain rows; QA/drive row descriptions gain the consumes-map clause; conduct checklist page + guide routing row per the adding-skills checklist; CHANGELOG under Unreleased.

Site (executed in the docs-site repo at release, per the release doc's downstream walk - the placement is decided HERE): how-it-compounds gains the fifth loop (table row + section, count language kept evergreen); a new skills/features reference page (stating explicitly that this map is committed - the opposite default from the code-map page); live-qa gains the consumes-map note beside its existing augments-never-replaces note; the skills index grid gains a row under repo-and-memory maintenance (deliberately NOT a node in the pipeline diagram - the map is not a stage); nav registration in the sidebar config; the site glossary needs the collision resolved - it already defines "Feature map" as the code-POV clawpatch index, so the two senses get qualifying parentheticals ("code index" vs "user-POV drive map") plus the Doctor term; cookbook gains seed/cadence recipes; choosing-your-route gets at most a see-also line (it selects stages; the map is not one).

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_features_skill_contract -q
./scripts/sync-codex.sh && ./scripts/sync-codex.sh
python3 scripts/check_doc_anchors.py
```

## Early proof point

Task fn-211-feature-map-compounding-user-pov-drive.1 validates the core approach (the feature-entry contract and seed workflow read cold-executable: a fresh agent could seed a map from them). If the contract cannot be written so a cold reader drives from it alone, re-evaluate the four-H2 shape before building maintain and the consumers.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Skill with state-resolved seed/maintain modes, autonomous refusal, typed outcome line | fn-211-feature-map-compounding-user-pov-drive.1 | - |
| R2 | Seed: repo interview, per-feature files, every route proven by one live drive | fn-211-feature-map-compounding-user-pov-drive.1 | - |
| R3 | Index operating rules + four-H2 feature-entry contract | fn-211-feature-map-compounding-user-pov-drive.1 | - |
| R4 | Doctor contract + ownership/cleanup invariants | fn-211-feature-map-compounding-user-pov-drive.1 | - |
| R5 | Maintain: audit-shaped pass with clean/changed/blocked + verified-unreachable | fn-211-feature-map-compounding-user-pov-drive.2 | - |
| R6 | Maintain edit scope: map + owned harness only, never product code | fn-211-feature-map-compounding-user-pov-drive.2 | - |
| R7 | QA/drive consume by pointer; stale routes filed for the next maintain pass | fn-211-feature-map-compounding-user-pov-drive.3 | - |
| R8 | Docs story decided and shipped: repo docs + site placement | fn-211-feature-map-compounding-user-pov-drive.4 | - |

