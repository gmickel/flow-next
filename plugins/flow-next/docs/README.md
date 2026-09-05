# Flow-Next docs

The offline-resilient reference for flow-next. Every file here is self-contained and readable without a network, and every cross-link is a relative repo path so a fork keeps working.

## Start here by intent

| You want to know | Read |
|---|---|
| What is this, and how do I install it? | [root README](../../../README.md) |
| Which stages does *this* change need? | [`pipeline-variations.md`](pipeline-variations.md) |
| Do I need all of it? | [`running-lean.md`](running-lean.md) |
| What skills exist? | [`skills.md`](skills.md) |
| How do we adopt this as a team? | [`teams.md`](teams.md) |
| Which model does what, which pipeline shape an item takes, and how do I change either? | [`orchestration.md`](orchestration.md) |
| How does *my* harness reach another model? | [`reach/README.md`](reach/README.md) |
| What's every flag on every command? | [`flowctl.md`](flowctl.md) |
| Something is stuck. | [`troubleshooting.md`](troubleshooting.md) |
| This idea is too big to capture yet. | [`../skills/flow-next-chart/SKILL.md`](../skills/flow-next-chart/SKILL.md) |
| I don't know which stage to run. | [`../skills/flow-next-guide/SKILL.md`](../skills/flow-next-guide/SKILL.md) |

The repo's strategic intent is [`STRATEGY.md`](../../../STRATEGY.md). The vocabulary, with the synonyms to avoid, is [`GLOSSARY.md`](../../../GLOSSARY.md); it is a dictionary rather than an encyclopedia, and the concepts are explained on the pages below. The retired long-form version is archived at [`agent_docs/archive/GLOSSARY-full.md`](../../../agent_docs/archive/GLOSSARY-full.md).

## Understand the system

| Doc | Answers |
|---|---|
| [`running-lean.md`](running-lean.md) | Which layers to switch on at all, what each one costs, and how to get the capability without the standing cost |
| [`pipeline-variations.md`](pipeline-variations.md) | Six worked routes from epic to docs chore, and the risk-and-unknowns rule that picks between them |
| [`architecture.md`](architecture.md) | The `.flow/` layout, the spec-first task model, and what a spec's [`## Quick commands`](architecture.md#verification-tiers-the-specs-quick-commands) block is for |
| [`self-improving.md`](self-improving.md) | How memory, glossary, decisions, strategy, and the feature map compound through work you already do |
| [`teams.md`](teams.md) | Handover objects, spec-as-PR, parallel work from one spec, the adoption ladder |
| [`platforms.md`](platforms.md) | Per-harness install and caveats for Claude Code, Codex, Droid, Cursor, Grok Build, and OpenCode |

## Run the pipeline

| Doc | Answers |
|---|---|
| [`worked-example.md`](worked-example.md) | One actual requirement, review finding, correction, and PR handover |
| [`skills.md`](skills.md) | All 32 skills in the published catalog, what triggers each one, and what it does |
| [`spec-template.md`](spec-template.md) | What belongs in a spec, the R-ID rules, and how to customize the scaffold from a root `SPEC.md` |
| [`flowctl.md`](flowctl.md) | The full CLI: every command, flag, JSON shape, and exit code |
| [`orchestration.md`](orchestration.md) | Two routing axes: the pipeline shape per item (six deciders, each printing its reason) and the model per job (four tiers, the routing block, review backends, the bridge route); an unattended field case with 38 landed PRs and a five-rung setup ladder |
| [`reach/README.md`](reach/README.md) | What each harness can actually reach, and how it degrades when it cannot |
| [`../skills/flow-next-pilot/SKILL.md`](../skills/flow-next-pilot/SKILL.md) | The build loop: one ready spec, one stage per tick, one verdict line |
| [`../skills/flow-next-land/SKILL.md`](../skills/flow-next-land/SKILL.md) | The ship loop: CI, review convergence, the gated merge, the release tail |
| [`../skills/flow-next-qa/SKILL.md`](../skills/flow-next-qa/SKILL.md) | The live-app pass (consumes `.flow/features/` navigation when present), and why it may never mark PASS by reading source |
| [`../skills/flow-next-features/SKILL.md`](../skills/flow-next-features/SKILL.md) | Seed or maintain the committed user-POV drive map that QA and drive reuse for navigation |
| [`ralph.md`](ralph.md) | The deprecated hardened harness, still supported and still documented |
| [`tracker-sync.md`](tracker-sync.md) | Projecting a spec onto Linear, GitHub, GitLab, or Jira, and reconciling it back |
| [`html-artifacts.md`](html-artifacts.md) | The opt-in HTML render lenses for spec review and PR review |

## Contracts and schemas

| Doc | Answers |
|---|---|
| [`prose.md`](prose.md) | The ten rules every agent-emitted artifact drafts under |
| [`review-findings.md`](review-findings.md) | The portable structured-findings contract: identity, lineage, anchors, [bounds](review-findings.md#bounds), consumer fallback |
| [`pr-cognitive-aid.md`](pr-cognitive-aid.md) | The portable PR cognitive-aid contract, its fixture, and how downstream renderers pin it |
| [`memory-schema.md`](memory-schema.md) | The memory tree, its frontmatter, and the audit lifecycle |
| [`glossary.md`](glossary.md) | How the repo-root `GLOSSARY.md` is shaped and resolved |
| [`strategy.md`](strategy.md) | How the repo-root `STRATEGY.md` is shaped and who reads it |

## Fixing and contributing

| Doc | Answers |
|---|---|
| [`troubleshooting.md`](troubleshooting.md) | Stuck tasks, wedged reviews, `.flow/` cleanup, uninstall, and the [leftover `.flow/bin/`](troubleshooting.md#i-have-flowbin-from-an-old-install) case |
| [`sync-codex.md`](sync-codex.md) | How the Codex mirror is generated and which guards must stay green |
| [`ci-workflow-example.yml`](ci-workflow-example.yml) | A drop-in GitHub Actions job running `flowctl validate --all` |

**Quick jumps into the CLI reference:** [`flowctl brief`](flowctl.md#brief) · [`flowctl chart`](flowctl.md#chart) · [`flowctl review-backend`](flowctl.md#review-backend) · [`flowctl prime classify`](flowctl.md#prime-classify) · [`flowctl repo-map`](flowctl.md#repo-map) · [`flowctl setup-block`](flowctl.md#setup-block) · [`flowctl validate`](flowctl.md#validate) · [`flowctl spec create`](flowctl.md#spec-create) · [`flowctl show`](flowctl.md#show) · [`flowctl pilot strikes`](flowctl.md#pilot-strikes) · [the deterministic review cap](flowctl.md#deterministic-review-cap)

**Deep links worth knowing:** [tiers](orchestration.md#tiers-what-kind-of-model-a-job-wants) · [review backends](orchestration.md#review-backends-cross-model-review) · [the bridge route](orchestration.md#implementation-offload-the-bridge-route) · [turning the review dial down](running-lean.md#turning-the-dial-none-and-host) · [finding identity and lineage](review-findings.md#identity-and-lineage) · [review bookkeeping authority](architecture.md#review-bookkeeping-authority-and-write-ordering) · [chart projection](tracker-sync.md#chart-lifecycle-projection) · [OpenCode install](platforms.md#opencode) · [backlog mode](../skills/flow-next-pilot/references/backlog-mode.md) · [chart workflow](../skills/flow-next-chart/workflow.md) · [land workflow](../skills/flow-next-land/workflow.md) · [make-pr create and finalize](../skills/flow-next-make-pr/create-and-finalize.md) · [prime](../skills/flow-next-prime/SKILL.md) · [drive](../skills/flow-next-drive/SKILL.md) (consumes `.flow/features/` when present) · [chart resolve](flowctl.md#chart-resolve)

## Notable updates

See [documentation release history](release-history.md) for the accumulated behavior notes and [CHANGELOG](../../../CHANGELOG.md) for releases. Current defaults belong to each subsystem reference.

## Conventions

- **R17 cross-link discipline.** Each doc here is a self-contained reference. Canonical sources (`templates/spec.md`, `scripts/sync-codex.sh`, `STRATEGY.md`, `GLOSSARY.md`) are linked, never re-embedded.
- **Relative paths only.** No absolute `github.com/...` URLs anywhere in this tree - fork-survivable + offline-readable.
- **Length discipline.** Reference shape (tables, lists, schemas first; narrative second). Keep the answer complete; move release history and unrelated detail to their own pages.

## See also

- [`../README.md`](../README.md) - plugin overview, install, workflow narrative.
- [`../../../STRATEGY.md`](../../../STRATEGY.md) - flow-next's strategic intent + active tracks.
- [`../../../GLOSSARY.md`](../../../GLOSSARY.md) - canonical vocabulary (Spec, Task, R-ID, ...).
- [`../../../CONTRIBUTING.md`](../../../CONTRIBUTING.md) - contributor entry point (local dev, adding skills, releasing).
- [`../../../CLAUDE.md`](../../../CLAUDE.md) - repo-level guide for working in this codebase.
