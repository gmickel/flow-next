# flow --auto: pilot adopts the routing reference and runs long-horizon over the same rails

<!-- Fleshed out on 2026-09-11 from the fn-238 stub, the shipped pilot skill (4.18.1), and the fn-238 branch state. Source tags: [user] is the maintainer's stated direction in the stub and the fn-238 conversation; [paraphrase] restates it; [inferred] is design the maintainer has not yet confirmed and should read first. A fresh agent needs nothing outside this file, the fn-238 spec, and the pilot skill as it ships today. -->

## Goal & Context
<!-- Goal & Context: 55% [user], 30% [paraphrase], 15% [inferred] -->

After fn-238 ships the attended conductor and the shared routing reference, the only difference between flow and pilot is attended versus unattended. Pilot still classifies the next stage from state through its own stage table; flow classifies from content and context through the routing reference. Two copies of one judgment drift. This spec makes the unattended driver the same judgment behind a second entry shape, `flow --auto`, and retires pilot as a separate skill.

Frontier models handle long-horizon work well enough that pilot's one-stage-per-tick discipline is now compensation for a limit that no longer exists. A tick pays a full re-anchor (skill re-read, config snapshot, selection, classification, branch resolution) at every stage boundary, and the driver pays an interval on top. fn-219 measured that cost when it chained `qa` into `make-pr` inside one tick and closed the table at that one row because every other transition could fail into human territory. The flow hop loop already re-evaluates after each stage and stops at a human decision, so the transitions fn-219 could not chain are exactly what flow does by construction.

Three things survive because they are harness limits, not model limits. Fresh-context separation between writer and reviewer stays. Externalised state (receipts, evidence, the strikes ledger, the decision log) stays so a run that dies at hour six resumes from disk on the next invocation. The tick contract with its terminal verdict line stays as the portable floor for hosts without stable long sessions, and as the audit trail on every host.

MergeFoundry (the maintainer's flow-swarm orchestrator) owns its own scheduler and does not need these primitives. Flow-Next does, because it runs inside third-party harnesses with flaky session and wake boundaries.

Two follow-ups stay sequenced. fn-240 adds harness and model autorouting once one driver exists to consume it. Land is untouched by this spec and keeps the merge tail.

## Architecture & Data Models
<!-- Architecture & Data Models: 35% [user], 35% [paraphrase], 30% [inferred] -->

**One skill, two entry shapes.** `/flow-next:flow` gains `--auto`. Without it, flow is the attended conductor fn-238 shipped. With it, flow is the unattended driver: no questions, ready-flag selection instead of intent, pilot's rails, and the terminal verdict line. The hop loop (route, run the routed stage, re-evaluate) is shared. Attended flow stops at the next human decision; `--auto` stops at the next decision that needs a human and reports it as a verdict instead of asking.

**Long-horizon by default, tick as the floor.** `flow --auto` runs the whole route for one item in one invocation: it classifies, dispatches the stage, verifies from observed state, records the hop, and re-classifies until the item reaches a terminal (PR exists, deferred to land, asked, blocked, needs human, no work). `flow --auto --tick` runs exactly one hop and stops, which is today's pilot tick. The driver recipe per host chooses the shape; there is no capability probe and no automatic degrade. A long session that dies mid-run loses nothing: every hop ends with the same receipts, evidence echo, and ledger write a tick ends with, so the next invocation classifies from disk and continues. This is how pilot already resumes across ticks; `--auto` reuses it across hops.

**Classification reads the routing reference.** Pilot's Phase 2 stage table is deleted. `--auto` classifies from `references/route-matrix.md` for the spec-state rows (no tasks, planned, in progress, all done, open PR), `references/plan-vs-no-plan.md` for a ready spec with no tasks and no recorded route, and `references/gate-selection.md` for review, QA, and completion review. The routing files gain no autonomy-specific rows; the rules already name the state and the gate. What stays in the auto workflow is what the reference cannot carry: the ready-flag consent boundary, selection order, the collision and re-bless checks, the all-done PR probe, the branch matrix, the evidence echo, and the ledger.

**Pilot's rails move unchanged.** Ralph-nesting refusal, dirty-tree refusal at start and after each hop, the strikes ledger under the git common dir with its human clear verb (`flowctl pilot strikes clear`), two healthy no-advance hops unready the spec, the all-done PR probe (open defers to land, merged with nothing new is inconsistent, closed without merge is inconsistent), the branch matrix, the `mode:autonomous` token to every dispatched stage, the closed chain table, never merge, never invoke land, never author a spec, never promote, backlog mode's park-and-ask through tracker-sync, the decision log under `.flow/pilot-runs/`, and the ready flag or `tracker.readyState` as the consent boundary. The rails become the auto workflow's guards and phases, read only under `--auto`. Config keys (`pilot.autonomy`, `pilot.gateClasses`, `pipeline.qa`, `pipeline.chainStages`), flowctl verbs (`flowctl pilot strikes`, `flowctl pilot-log`), ledger paths, and the `PILOT_VERDICT` name do not change. Renaming them would break every driver, the land hand-off, and the Ralph template for no user benefit.

**Backlog mode becomes `flow --auto --backlog`.** `references/backlog-mode.md` moves under the flow skill unchanged. The `pilot.autonomy=backlog` config value still enables it. In long-horizon mode a backlog run drives one selected item to its terminal, then stops; the next invocation selects the next item. One item per run bounds a long session.

**The chain table dissolves into the hop loop.** With hops running back to back, `pipeline.chainStages` has nothing left to chain: `qa` into `make-pr` is just the next hop. The key stays accepted for one release and is ignored with one stderr notice; in tick mode it keeps its exact semantics (the `qa+make-pr` tick) until the alias is removed. The chain-stages tests move to the tick-mode contract.

**`pipeline.qa=auto` under `--auto`.** The QA gate reads `references/gate-selection.md`, so `auto` now runs unattended too: at all-done, when the acceptance describes UI behaviour on a drivable surface and a target can be started, QA runs; otherwise the hop records `skipped(config: pipeline.qa=auto: <reason>)` and advances to make-pr. The literal-`on` gate keeps its exact semantics. QA never blocks the loop.

**Alias for one release.** `/flow-next:pilot` stays as a command shim that rewrites its arguments onto `flow --auto --tick` (`--spec <id>` becomes the positional id; `--backlog`, `--dry-run`, `--review`, `--research`, `--depth` pass through) and prints one deprecation line to stderr. The verdict grammar is byte-identical, so existing `/loop`, `/goal`, and driver prompts keep parsing. The release after this one removes the shim, the pilot skill directory, its command entry, its conduct page, and its Codex mirror.

**The auto workflow lives in one gated file.** `skills/flow-next-flow/auto.md` holds the guards, selection, classification glue, branch matrix, dispatch, verify, and report phases, read only when `--auto` is parsed. Attended runs never load it. SKILL.md gains the `--auto` and `--tick` tokens, the inverted autonomy rule (attended refuses under a marker; `--auto` refuses only under Ralph), and one pointer line. The always-loaded growth is those lines and nothing else; the auto workflow is the pilot workflow with its stage table replaced by routing-reference reads and its single-tick exit replaced by the hop loop.

**Suggested build order.** The auto workflow and the SKILL.md tokens first, moving pilot's phases and references across without behavioural change. Then the classification swap (delete the stage table, read the routing files) with the existing pilot tests re-pointed and green. Then the hop loop and `--tick`. Then the alias shim, the config-key notice, and the QA `auto` read. Then tests, Codex mirrors, repository docs, guide and vault surfaces. Then the long-horizon study. The docs-site work last, after the release is cut.

## API Contracts
<!-- API Contracts: 40% [user], 30% [paraphrase], 30% [inferred] -->

- `/flow-next:flow --auto [<spec-id>] [--tick] [--backlog] [--explain] [--review=<backend>] [--research=<grep|rp>] [--depth=<level>]`. With a spec id, the run is scope-locked to that spec and it must still pass the ready predicate. Without one, selection runs as pilot's does today (ready flag, satisfied `depends_on_epics`, no other-actor claim, strikes). `--auto` never accepts intent, a path, a branch, or free text; the ready flag is the consent boundary and there is no capture upstream of it. Unknown flags warn to stderr and are ignored, as today.
- `--tick` runs one hop and ends. Without it the run continues until a terminal. Both shapes end with exactly one `PILOT_VERDICT` line as the last line of output, with the grammar pilot emits today: `PILOT_VERDICT=<ADVANCED|ASKED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason="<one line>"`. A long-horizon run names every dispatched stage in order joined by `+` (the shape fn-219 introduced for `qa+make-pr`) and carries the last hop's verdict; `TRIAGED` stays dry-run only.
- `--explain` under `--auto` prints the selected spec, the classified stage, the routing row and gate it came from, the consulted status fields, the PR probe result, and would-clear ledger entries, then stops with the dry-run verdict and no write, no checkout, no dispatch. `--dry-run` is accepted as its alias for one release through the pilot shim.
- Every hop echoes the same evidence block pilot echoes today (`stage=`, before and after fields, `advanced=`) and one `stage: <name> - ran | skipped(<reason>) | failed(<reason>)` line with the model annotation rule fn-178 set. A long-horizon run has one block and one line per hop.
- `/flow-next:pilot [args]` for one release: rewrites to `flow --auto --tick [args]`, prints `pilot is now flow --auto --tick; this alias is removed in the next release` to stderr, and behaves byte-for-byte as the tick.
- `pipeline.chainStages` for one release: read and honoured in tick mode; ignored in long-horizon mode with one stderr notice. Removed with the alias.
- `pipeline.qa`: `off`, `on`, and `auto` all take effect under `--auto` per `references/gate-selection.md`. `on` and `off` are byte-for-byte unchanged.
- A zero-task ready spec with no recorded route: `--auto` applies `references/plan-vs-no-plan.md`, records the route (`flowctl spec set-no-plan` or `clear-no-plan`), echoes the signal that decided it, and dispatches. A recorded route, an intentional plan, an explicit design-review request, or a `needs_work` / `needs_human` plan review stays authoritative exactly as fn-237 set it.
- Land is unchanged: `DEFERRED_TO_LAND` keeps its meaning, land keeps its discovery, gates, merge license, and release tail.

## Edge Cases & Constraints
<!-- Edge Cases & Constraints: 30% [user], 35% [paraphrase], 35% [inferred] -->

- `--auto` refuses under Ralph (`FLOW_RALPH`, `REVIEW_RECEIPT_PATH`) with pilot's exact terminal line. It does not refuse under `FLOW_AUTONOMOUS` or `mode:autonomous`, because it sets those for the stages it dispatches. Attended flow keeps fn-238's refusal under every marker. Pilot, Ralph, and flow stay three drivers, never nested; `--auto` never dispatches land or a second driver.
- A long-horizon run that crashes, is killed, or hits a session limit leaves the same state a dead tick leaves: committed receipts, a ledger entry, a branch. The next invocation classifies from disk. Nothing is resumed from transcript.
- A hop that ends `NEEDS_HUMAN`, `ASKED`, `BLOCKED`, `DEFERRED_TO_LAND`, or `NO_WORK` ends the run; only `ADVANCED` continues. The two-strike rule bounds a spec that advances nothing twice; the finite stage set bounds a spec that advances (plan, plan-review, work, qa, make-pr, then a PR exists).
- The dirty-tree guard runs at run start and after every hop. A dirty non-`.flow/` tree after a dispatch is crash-class: stop, leave state, no strike, exactly as today.
- Branch resolution runs before every hop through the existing matrix. A long-horizon run may cross from a plan hop on the default branch to a work hop on the spec branch; the matrix already handles each row, and the run never plans onto a branch with an open PR.
- Review no-repeat: a delegated review exiting with `NOT_RETRYABLE: artifact unchanged since last verdict` ends the run `NEEDS_HUMAN`. Counter reset and `--force` stay human-only.
- Backlog mode keeps every invariant as enforcing bash, not prose: the dispatch allowlist, never author a spec, single item per run, dep deadlock surfaces as `ASKED`. The allowlist gains nothing; `resolve-pr` and `land` stay outside it.
- Under `--auto`, `references/prototype-before-ask.md` does not license a blocking question. An unattended fork that is not observable is `NEEDS_HUMAN` in ready mode and `ASKED` in backlog mode. An observable fork may be settled by running something only inside the dispatched stage's existing license (the no-plan worker's parallel license, plan's scouts), never by flow itself.
- A host without stable long sessions runs `--tick` under its loop primitive. The per-harness reach pages name the recommended shape; the skill probes nothing. A host where a long run is cut mid-hop is the crash case above, not a data-loss case.
- The pilot shim and the pilot skill directory coexist for one release. The Codex sync roster carries both; the legacy-cleanup install test knows the shim is a redirect, not a stale copy.
- Repo-public specs may carry vault pointers as `gno://` URIs. They never carry the pointed-at text.

## Acceptance Criteria

- **R1:** `flow --auto` advances a ready item through its full route in one invocation (hop after hop until a terminal) and, with `--tick`, by exactly one hop, with the same terminal verdict grammar pilot emits today. A long-horizon run names every dispatched stage joined by `+` and carries the last hop's verdict; one evidence block and one `stage:` line per hop are in the transcript. [paraphrase]
- **R2:** Every pilot rail listed under Architecture is preserved byte-for-byte in behaviour: Ralph-nesting refusal, dirty-tree refusal at start and after each hop, strikes ledger with the two-strike unready and the `flowctl pilot strikes clear` recovery, the all-done PR probe outcomes, the branch matrix, `mode:autonomous` to every stage, never merge, never invoke land, never author a spec, never promote, backlog park-and-ask, the decision log. The existing pilot tests (`test_pilot_strikes`, `test_pilot_strikes_prose`, `test_pilot_chain_stages`, `test_pilot_log`, `test_pilot_backlog_substrate`, `test_pilot_backlog_mirror_safety`, `test_tracker_sync_backlog_mode`, `test_stage_model_provenance`, and the pilot rows in `test_flowctl_surface`, `test_command_shim_flatten`, `test_pipeline_qa_auto`) are re-pointed at the flow skill and stay green. [paraphrase]
- **R3:** Classification comes from the routing reference. Pilot's stage table is deleted; the auto workflow names the routing file it reads at each classification point and carries no second copy of a rule. Selection, consent, collision, re-bless, the PR probe, and the branch matrix stay in the auto workflow because the reference cannot carry them. [user]
- **R4:** `/flow-next:pilot` exists for one release as a shim onto `flow --auto --tick`, maps every pilot argument, prints one deprecation line, and behaves byte-for-byte as today's tick. The changelog states the retirement and the removal release. The following release removes the shim, the skill directory, the command entry, the conduct page, the Codex mirror, and the sync-roster rows. [inferred]
- **R5:** `/loop`, `/goal`, and Ralph recipes in the repository docs are rewritten as optional wrappers for hosts without stable long sessions: the default recipe is one `flow --auto` invocation per item, the loop recipe is `flow --auto --tick` under the host's loop primitive, and Ralph stays the deprecated hardened harness with its own reference. [paraphrase]
- **R6:** `flow --auto --backlog` runs backlog mode with `references/backlog-mode.md` moved unchanged, `pilot.autonomy=backlog` still enabling it, one selected item per run, and every safety invariant enforced as bash at its site. [paraphrase]
- **R7:** `pipeline.qa=auto` takes effect under `--auto` through `references/gate-selection.md`; `on` and `off` are byte-for-byte unchanged; a skipped QA hop records its reason and advances. `pipeline.chainStages` is honoured in tick mode, ignored with a notice in long-horizon mode, and removed with the alias. [inferred]
- **R8:** A zero-task ready spec with no recorded route is routed by `references/plan-vs-no-plan.md` under `--auto`, the route is recorded before mint, and the deciding signal is echoed. Recorded routes, intentional plans, explicit design-review requests, and failed plan reviews stay authoritative. [inferred]
- **R9:** `--explain` under `--auto` prints the selection, the classified stage with its routing row and gate, the consulted fields, the PR probe, and would-clear ledger entries, with no write, checkout, or dispatch; `--dry-run` aliases it for one release. [paraphrase]
- **R10:** Attended flow keeps fn-238's refusal under every autonomy marker; `--auto` refuses only under Ralph and never dispatches land or another driver. Land is byte-for-byte unchanged. [user]
- **R11:** All skill and reference prose written or moved by this spec follows the repository's gated-reference contract and the vault's instruction criteria: the auto workflow is read only under `--auto`, backlog mode only under `--backlog`, always-loaded SKILL.md growth is the two tokens, the inverted refusal, and one pointer, and each growth states what it buys (G1). The flow conduct checklist gains the auto rows and the pilot checklist is retired with the alias. [user]
- **R12:** A long-horizon study runs in the maintainer's eval harness as its own task: a frozen model, harness, and spec set; `flow --auto` versus `flow --auto --tick` under a host loop on the same specs; pre-registered endpoints of terminal parity (same verdict, same PR state, same receipts) first and wall-clock second; retained negative results. A wall-clock win without terminal parity is a failure. Moving pilot's phases under flow is not accepted as behavioural equivalence without it. [paraphrase]
- **R13:** Tests assert behaviour or contract only (G2): the verdict grammar in both shapes, the shim's argument mapping, the classification pointers resolving to routing files that exist, the chain-stages tick-only behaviour, the QA `auto` read under `--auto`, the route recording for a zero-task spec, and the refusal inversion. Codex mirrors regenerate twice with no diff. Every repository, guide, and vault surface in the Downstream section is updated in the same workstream, each verified with its own check, and publication state is reported separately from source completion. [user]
- **R14 (last step, after every other criterion is verified and the release is cut):** The flow-next.dev work: the autonomy section's pilot page becomes the `flow --auto` page, driving-a-loop, going-autonomous, and unattended-operation are rewritten around the two shapes, the pilot skill page is marked deprecated for one release and removed with the alias, both navigation sources are updated, and the docs-site changelog carries the story beat. This release is the major beat: the callout fn-238 deferred lands here, covering flow, `flow --auto`, and the road to fn-240. Copy follows the artifact prose contract and the messaging discipline. The site build passes. [inferred]

## Boundaries

- No change to land. [user]
- No new flowctl subcommand that reads, weighs, or decides. No capability probe, no session-length detector, no automatic tick degrade. [paraphrase]
- No renamed config key, flowctl verb, ledger path, decision-log path, or verdict name. [inferred]
- No change to the routing reference files beyond what an added or removed skill requires under fn-238's staleness rule. Autonomy-specific rows do not belong there. [inferred]
- No harness or model autorouting. That is fn-240. [user]
- No parallel item fan-out inside a run. One item per run; MergeFoundry owns multi-item scheduling. [paraphrase]
- No attribution of the routing rules to any external system in the spec, the reference, the docs, or the changelog. [user]

## Downstream

Tallied 2026-09-11 against the live properties and the fn-238 branch. Every item is part of this spec's scope. Prose on every public surface follows the artifact prose contract and the maintainer's messaging discipline: positive formulations, proof-backed claims, one story beat per release, role labels over model ids. This release is the major beat and carries the designed callout fn-238 deferred.

### Repository (GitHub)

- **Flow skill.** `SKILL.md` (`--auto`, `--tick`, inverted refusal, one pointer), new gated `auto.md`, `references/backlog-mode.md` and `references/qa-stage.md` moved from pilot, the conduct checklist rows, plugin and marketplace manifests where the pilot entry is listed, Codex mirror regenerated twice with no diff.
- **Pilot shim.** `commands/pilot.md` rewritten as the redirect; `skills/flow-next-pilot/` kept for one release with a top-of-file deprecation line; both removed the release after, with `agent_docs/conduct/pilot.md`, the conduct index row, the sync-roster rows, and the legacy-cleanup install test rows.
- **flowctl.** No behaviour change. `pipeline.chainStages` description text in the schema generator gains the deprecation note; the schema regenerates.
- **Docs.** Root README (Going autonomous, the `/goal` and `/loop` examples), docs index, skills index (Autonomous loops), orchestration (Chaining the loops, the driver composition prompt, the within-one-invocation section), ralph (framing as the deprecated hardened harness, recipes), running-lean, teams, tracker-sync (backlog mode entry point), troubleshooting, flowctl (config rows for `pilot.*` and `pipeline.chainStages`), release-history, glossary (driver, tick, long-horizon run; the verdict entry), changelog, strategy (command-count metric, the one-dial claim), the reach pages per harness (recommended shape: long-horizon or tick), and the pilot mentions in capture, plan, work, qa, make-pr, land, resolve-pr, impl-review, plan-review, spec-completion-review, deps, features, audit, and map skill prose.
- **Tests.** Behaviour or contract only, per R13, plus the existing land tests that read `DEFERRED_TO_LAND`.

### flow-next.dev (R14, last step)

- **Autonomy section.** `autonomy/pilot.mdx` becomes the `flow --auto` page (two shapes, rails, verdict, resume from disk). `driving-a-loop`, `going-autonomous`, `unattended-operation`, `land`, `ralph` revised for the two shapes.
- **Skill pages.** `skills/pilot.mdx` marked deprecated with the alias, removed with it; `skills/flow.mdx` (fn-238) gains the `--auto` section; both navigation sources updated (site nav groups and the Starlight sidebar).
- **Pages to revise.** Choosing your route, understand pipeline, what each layer costs, how work gets proven, concepts, explore first, why flow-next, cookbook, live QA (auto unattended), model routing, review workflow, writing specs, cli reference, configuration (`pipeline.chainStages` deprecation, `pilot.*` keys), tracker operations, platforms, receipts, review backends, standing criteria, troubleshooting, faq, glossary, compatibility, install.
- **Home page.** The designed major-release callout: flow, `flow --auto`, and the road to fn-240 framed as the road ahead.
- **Release.** Docs-site changelog entry as the story beat, site version constant and package version bumped. The site's version constant lags the repo; reconcile before this lands.
- **Gate.** Site build passes. This block starts only after R1 to R13 are verified and the release is cut.

### AI x SDLC guide

- `guides/flow-next.md` (the autonomous delivery section and the pipeline breakdown), `factory-and-multi-agent`, `governance-loops`, `discipline-patterns`, `methodology`, `model-routing`, `plugins`, `production-grade`, and the per-harness pages (Claude Code, Codex, Cursor, Gemini CLI, coding assistants, cloud and desktop) where they name pilot or the loop recipe. README command mentions.

### Vault

- Autonomy note (the three-driver section becomes two shapes of one driver; pilot retired), Autonomy Rungs mapping, Skills Catalog (pilot row retired, flow row gains `--auto`), Release Timeline beat, Vocabulary and Concepts (driver, tick, long-horizon run), Lifecycle and Handover Objects (the hop as the handover unit), Messaging Library (the one-dial claim gets its unattended rung), Strategy and Positioning. Reindex and verify retrieval.

### Not affected

- Land, MergeFoundry, the client microsites, and the AI x SDLC bundled onboarding copy. The maintainer's blog has no flow-next post to update.

## Decision Context

### Motivation

- Direction stated during fn-238 capture: the router is the smallest new piece; everything it routes to already exists and proves its work. Pilot retires once its judgment and flow's are the same reference. [user]
- Keep tick mode because harness boundaries are flaky and Flow-Next does not own the orchestrator. [user]
- The tick was the discipline that made unattended runs auditable on models that lost the thread across stages. The audit trail survives as receipts, evidence echoes, and the ledger; the per-stage re-anchor cost does not need to. fn-219's closed chain table is the measured evidence that in-invocation continuation works and that the boundaries it could not cross are human-decision boundaries, which is where the hop loop stops anyway. [paraphrase]
- The strategy's bitter-lesson principle applies: scaffolding around a model's current weakness rots into cost. One-stage-per-invocation was that scaffolding. [strategy:Design principles]

### Implementation Tradeoffs

- One skill with two shapes rather than two skills sharing a reference. A separate `flow-auto` skill would keep the command count up and reopen the drift the reference closes. `--auto` is a mode token on the same conductor, and the auto workflow is a gated file attended runs never load, so the attended context cost is the tokens and one pointer. [inferred]
- Long-horizon default with an explicit `--tick`, not a capability probe. The rolling scheduler's dispatch probe measures one property (non-blocking subagent dispatch) and even that needed a dated measurement per host. Session stability is not observable from inside a session. The driver recipe per host is where that knowledge lives, and the reach pages already carry per-host recipes. [inferred]
- The zero-task route under `--auto` applies the rule and records it, mirroring capture under flow in fn-238. This is the second deliberate exception to the spec-level field's never-inferred rule, stated here so design review accepts it as intent. The alternative, refusing to run a zero-task ready spec until a human recorded the route, would make the ready flag an incomplete consent and send every captured spec back to a human for a second click. The signals the rule reads are all observable from the spec and the config; nothing is guessed. [inferred]
- No renames. Config keys, verbs, paths, and the verdict name carry `pilot` in their spelling after the skill is gone. That is a cosmetic debt accepted to keep every driver, the land hand-off, and the Ralph template parsing unchanged. A rename is a separate, deliberate break for a later major. [inferred]
- The alias lasts one release, not zero and not several. Zero breaks running loops on the day of release. Several keeps two entry points alive long enough to drift. [inferred]
- `pipeline.chainStages` is deprecated rather than kept. Its whole purpose was to skip one re-anchor between two stages; the hop loop skips all of them. Keeping it in long-horizon mode would be a knob with no effect. [inferred]
- Implementation guidance during the build. Before editing any always-loaded skill text, read `gno://ai/Context Layer/Agent Instruction Audit and Optimization Prompt.md`, its criteria worksheet `gno://ai/Context Layer/Context Layer - Instruction Audit Criteria (Astra and Fable).md`, and the progressive-disclosure synthesis `gno://ai/Context Layer/Context Layer - Astra and Fable Instruction Design (Sep 2026).md`, together with the repository's skill-authoring guide and its gated-reference contract. Apply the skill rows of the keep-versus-question table, the per-rule decision record, and the closing deletion pass. GNO is available on the maintainer's hosts. [user]

### Open for the maintainer before work

- Whether `--auto` should apply the plan-versus-no-plan rule to a zero-task ready spec (R8) or refuse until the route is recorded. This spec proposes applying it.
- Whether the one-release alias window is right, or whether the shim should live two releases for teams on slower upgrade cadences.
- Whether `pipeline.chainStages` is deprecated with the alias or kept as a tick-mode-only key indefinitely.

## Requirement coverage

Direct route: one implicit owner task satisfies R1 to R14. R14 runs last.
