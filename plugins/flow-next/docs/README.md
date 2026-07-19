# Flow-Next docs

The offline-resilient reference for flow-next — **repeatable agentic engineering**: durable specs, re-anchored workers, adversarial reviews, receipts. Each file here is self-contained, terse, and offline-readable. Cross-links use relative repo paths — fork-survivable, no external URLs.

**Start here by intent:**

- *"What is this and how do I install it?"* → [root README](../../../README.md) — pitch, tenets, install, 5-command happy path.
- *"What skills exist?"* → [`skills.md`](skills.md) — all 28 skills, triggers, one-liners.
- *"How do we adopt this as a team?"* → [`teams.md`](teams.md) — handover objects, Spec-as-PR, adoption ladder.
- *"How do I run it autonomously?"* → [`ralph.md`](ralph.md) + the pilot/land skill pages below.
- *"Which model does what, and how do I change that?"* → [`orchestration.md`](orchestration.md) — routing surfaces, steering, CLAUDE.md model tables, loop chaining.
- *"What's every flag on every command?"* → [`flowctl.md`](flowctl.md).

> For the repo's strategic intent see [`../../../STRATEGY.md`](../../../STRATEGY.md). For canonical vocabulary (Spec, R-ID, Handover object, Receipt, render lens, …) see [`../../../GLOSSARY.md`](../../../GLOSSARY.md).

## Subsystem references

| Doc | What's in it |
|-----|--------------|
| [`architecture.md`](architecture.md) | `.flow/` directory layout, spec-first task model, ID format, separation of concerns, task completion shape |
| [`skills.md`](skills.md) | Skills catalog — all 28 skills (22 slash-command, 6 phrase-triggered), grouped by lifecycle / autonomy / maintenance, each linked to its `SKILL.md` |
| [`spec-template.md`](spec-template.md) | Canonical scaffold cross-link, R-ID rules, confidence anchors, introduced-vs-pre-existing, protected artifacts, trivial-diff skip, receipt schema |
| [`memory-schema.md`](memory-schema.md) | Categorized memory tree (bug / knowledge tracks), frontmatter schemas, decisions subtree, audit lifecycle, legacy migration |
| [`tracker-sync.md`](tracker-sync.md) | `/flow-next:tracker-sync` bridge — projection-not-coordination, discovery ceremony, hybrid id model, sync-state schema, transport ladder (Linear/GitHub/GitLab/Jira), lifecycle touchpoints, Ralph-safe conflict queueing; distinct from `/flow-next:sync` (plan-sync) |
| [`html-artifacts.md`](html-artifacts.md) | Optional HTML artifact mode (2.0.0+) — `artifacts.html.enabled` activation, the shared disclosure reference, spec lens (capture §5.10 / plan Step 8.5, state-dependent rendering), PR lens (make-pr Phase 1.5, R-ID-verified review instrument), GitHub display limitation + commit-vs-gitignore, conversational regen, Lavish (`lavish-axi`) optional companion, autonomous generate-only discipline |
| [`glossary.md`](glossary.md) | Repo-root `GLOSSARY.md` shape, resolution walk, subcommands, R17 forbidden-vocabulary guard |
| [`strategy.md`](strategy.md) | Repo-root `STRATEGY.md` shape, Rumelt sections, foreign-file refusal, R19 fluff guard, how downstream skills consume it |
| [`self-improving.md`](self-improving.md) | How the system compounds through normal work — memory, glossary, decision records, strategy loops (seeded / grown / read / pruned); the no-manual-ceremony principle |
| [`platforms.md`](platforms.md) | Install matrix (Claude Code / Codex / Droid / OpenCode), cross-platform patterns, Codex model mapping, community ports, optional skill requirements (`/flow-next:map` Node 22+ + `clawpatch`) |
| [`sync-codex.md`](sync-codex.md) | `scripts/sync-codex.sh` pipeline shape, validation guards, plain-text transform (fn-45), R17 cross-link discipline |
| [`troubleshooting.md`](troubleshooting.md) | Reset stuck tasks, `.flow/` cleanup, Ralph debugging, receipt validation, rp-cli conflict resolution, `/flow-next:map` clawpatch failure modes, uninstall |

## Workflow references

| Doc | What's in it |
|-----|--------------|
| [`flowctl.md`](flowctl.md) | Full `flowctl` CLI reference — every command, every flag, JSON shapes, exit codes (including the [`repo-map`](flowctl.md#repo-map) readers consumed by the `/flow-next:map` opt-in skill) |
| [`orchestration.md`](orchestration.md) | Orchestration & model routing — the steering principle (one-off / durable / config), subagent tiers, review-backend grammar + precedence, `delegate:codex`, per-spec backend fields, CLAUDE.md model-routing tables, pilot+land loop chaining, what stays fixed |
| [`../skills/flow-next-prime/SKILL.md`](../skills/flow-next-prime/SKILL.md) | `/flow-next:prime` - opinionated agent-readiness assessment. Classifies the project (lifecycle / topology / size / stack / delivery shape) via the deterministic [`flowctl prime classify`](flowctl.md#prime-classify) emitter, judges **substance not existence**, verifies commands actually run, and leads with an operability verdict + ranked next-actions instead of a bare level. Four reference files under the skill dir: `classification.md` (five axes + emitter schema + `--classify-only` block), `playbooks.md` (per-shape playbooks), `stacks.md` (per-stack matrix), `harness.md` (agent-harness/permissions check-set); the scored census lives in `pillars.md`. `--classify-only` = cheap portfolio-triage sweep. **No `docs/prime.md` page** - [`skills.md`](skills.md) is the catalog surface and the SKILL.md + its four references are the deep reference; the flow-next.dev docs-site prime page is the public rendering (deferred to the maintainer's release walk). |
| [`../skills/flow-next-qa/SKILL.md`](../skills/flow-next-qa/SKILL.md) | `/flow-next:qa` — live-app real-user QA pass. Derives scenarios from the spec (AC / R-IDs / boundaries), drives the running app via [`flow-next-drive`](../skills/flow-next-drive/SKILL.md), files structured P0/P1/P2 findings with evidence, ends with a YES/NO ship verdict receipt (`type: qa_verdict`). FORBIDDEN from marking PASS by reading source. Runs user-invoked OR as the optional `pipeline.qa` pilot stage (default off, fn-72). **Augments — never replaces — CI/staging/manual QA**; requires a live deploy + a driver. |
| [`../skills/flow-next-pilot/SKILL.md`](../skills/flow-next-pilot/SKILL.md) | `/flow-next:pilot` — single-tick conductor for plan / plan-review / work / make-pr, plus an **optional `qa` stage** (`pipeline.qa==on`, default off, fn-72) at the all-tasks-done juncture before make-pr, and an **opt-in backlog mode** (`pilot.autonomy=backlog`, default off, fn-68) that widens selection from "one ready spec" to the whole open backlog (flow + tracker), triaging the top dep-ordered item and surfacing async questions when stuck — never authoring, never promoting, never merging. Covers `PILOT_VERDICT` grammar (incl. backlog `ASKED`), `mode:autonomous` signal, strikes ledger, driver recipes, and Ralph as the alternative driver — never nested. See [`references/backlog-mode.md`](../skills/flow-next-pilot/references/backlog-mode.md). |
| [`../skills/flow-next-land/SKILL.md`](../skills/flow-next-land/SKILL.md) | `/flow-next:land` — cadence-tick ship loop babysitting build-loop-authored PRs. Covers the `LAND_VERDICT` grammar, dual authorship signals, CI tri-state + fix budget, patience window, `land.reviewSignal`, the confined auto-merge override, post-merge tail (spec close → tracker → release-follow), and `--dry-run`. Opt-in. |
| [`ralph.md`](ralph.md) | Ralph autonomous mode internals — hooks, receipts, iteration cap, DCG setup, sandbox options |
| [`../skills/flow-next-work/references/codex-delegation.md`](../skills/flow-next-work/references/codex-delegation.md) | `/flow-next:work` opt-in Codex implementation-delegation — host pre-flight gates + one-time consent, `codex exec` invocation + result schema, orchestration split / one run per task / classification / safety, circuit breaker + Ralph-safe + ralph-guard amendment + receipts + attribution. OFF by default. |
| [`teams.md`](teams.md) | Spec-driven team workflow — handover objects, Spec-as-PR, parallel work from one spec, symmetric interview, adoption ladder |
| [`ci-workflow-example.yml`](ci-workflow-example.yml) | Drop-in GitHub Actions example running `flowctl validate --all` |

## Conventions

- **R17 cross-link discipline.** Each doc here is a self-contained reference. Canonical sources (`templates/spec.md`, `scripts/sync-codex.sh`, `STRATEGY.md`, `GLOSSARY.md`) are linked, never re-embedded.
- **Relative paths only.** No absolute `github.com/...` URLs anywhere in this tree — fork-survivable + offline-readable.
- **Length discipline.** Reference shape (tables, lists, schemas first; narrative second). Brevity beats completeness.

## See also

- [`../README.md`](../README.md) — plugin overview, install, workflow narrative.
- [`../../../STRATEGY.md`](../../../STRATEGY.md) — flow-next's strategic intent + active tracks.
- [`../../../GLOSSARY.md`](../../../GLOSSARY.md) — canonical vocabulary (Spec, Task, R-ID, ...).
- [`../../../CONTRIBUTING.md`](../../../CONTRIBUTING.md) — contributor entry point (local dev, adding skills, releasing).
- [`../../../CLAUDE.md`](../../../CLAUDE.md) — repo-level guide for working in this codebase.
