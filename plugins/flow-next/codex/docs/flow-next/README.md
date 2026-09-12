# Flow-Next docs

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>` — and when the written name itself already starts with `flow-next-` (e.g. `/flow-next:flow-next-drive`), the prefix is not doubled: invoke `$flow-next-drive`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts' own syntax and are quoted verbatim — do not convert them.


The offline-resilient reference for flow-next. Every file here is self-contained and readable without a network, and every cross-link is a relative repo path so a fork keeps working.

## Start here by intent

| You want to know | Read |
|---|---|
| What is this, and how do I install it? | [root README](https://github.com/gmickel/flow-next/blob/main/README.md) |
| Which stages does *this* change need? | [`pipeline-variations.md`](pipeline-variations.md) |
| Do I need all of it? | [`running-lean.md`](running-lean.md) |
| What skills exist? | [`skills.md`](skills.md) |
| How do we adopt this as a team? | [`teams.md`](teams.md) |
| Which model does what, which pipeline shape an item takes, and how do I change either? | [`orchestration.md`](orchestration.md) |
| How does *my* harness reach another model? | [`reach/README.md`](reach/README.md) |
| What's every flag on every command? | [`flowctl.md`](flowctl.md) |
| Something is stuck. | [`troubleshooting.md`](troubleshooting.md) |
| This idea is too big to capture yet. | [`../skills/flow-next-chart/SKILL.md`](../../skills/flow-next-chart/SKILL.md) |
| I don't know which stage to run. | [`../skills/flow-next-flow/SKILL.md`](../../skills/flow-next-flow/SKILL.md) (`/flow-next:flow --explain`) |
| Which route does a starting state take? | the flow skill's [`references/route-matrix.md`](../../skills/flow-next-flow/references/route-matrix.md) |

The repo's strategic intent is [`STRATEGY.md`](https://github.com/gmickel/flow-next/blob/main/STRATEGY.md). The vocabulary, with the synonyms to avoid, is [`GLOSSARY.md`](https://github.com/gmickel/flow-next/blob/main/GLOSSARY.md); it is a dictionary rather than an encyclopedia, and the concepts are explained on the pages below. The retired long-form version is archived at [`agent_docs/archive/GLOSSARY-full.md`](https://github.com/gmickel/flow-next/blob/main/agent_docs/archive/GLOSSARY-full.md).

## Understand the system

| Doc | Answers |
|---|---|
| [`running-lean.md`](running-lean.md) | Which layers to switch on at all, what each one costs, and how to get the capability without the standing cost |
| [`pipeline-variations.md`](pipeline-variations.md) | Direct work from a ready spec, optional task planning, refinement and verification choices |
| [`architecture.md`](architecture.md) | The `.flow/` layout, the spec-first task model, and what a spec's [`## Quick commands`](architecture.md#verification-tiers-the-specs-quick-commands) block is for |
| [`self-improving.md`](self-improving.md) | How memory, glossary, decisions, strategy, and the feature map compound through work you already do |
| [`teams.md`](teams.md) | Handover objects, spec-as-PR, parallel work from one spec, the adoption ladder |
| [`platforms.md`](platforms.md) | Per-harness install and caveats for Claude Code, Codex, Droid, Cursor, Grok Build, and OpenCode |

## Run the pipeline

| Doc | Answers |
|---|---|
| [`worked-example.md`](worked-example.md) | One actual requirement, review finding, correction, and PR handover |
| [`skills.md`](skills.md) | All 31 skills in the published catalog, what triggers each one, and what it does |
| [`spec-template.md`](spec-template.md) | What belongs in a spec, the R-ID rules, and how to customize the scaffold from a root `SPEC.md` |
| [`flowctl.md`](flowctl.md) | The full CLI: every command, flag, JSON shape, and exit code |
| [`orchestration.md`](orchestration.md) | Two routing axes: the pipeline shape per item (six deciders, each printing its reason) and the model per job (four tiers, the routing block, review backends, the bridge route); an unattended field case with 38 landed PRs and a five-rung setup ladder |
| [`reach/README.md`](reach/README.md) | What each harness can actually reach, and how it degrades when it cannot |
| [`../skills/flow-next-flow/auto.md`](../../skills/flow-next-flow/auto.md) | The build loop, `flow --auto`: one ready spec, hop after hop to a draft PR (or one hop under `--tick`), one verdict line |
| [`../skills/flow-next-land/SKILL.md`](../../skills/flow-next-land/SKILL.md) | The ship loop: CI, review convergence, the gated merge, the release tail |
| [`../skills/flow-next-qa/SKILL.md`](../../skills/flow-next-qa/SKILL.md) | The live-app pass (consumes `.flow/features/` navigation when present), and why it may never mark PASS by reading source |
| [`../skills/flow-next-features/SKILL.md`](../../skills/flow-next-features/SKILL.md) | Seed or maintain the committed user-POV drive map that QA and drive reuse for navigation |
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
| [`read-back.md`](read-back.md) | The shared ratification shape for capture, refine, and plan: one draft file, a compact summary, one ask |
| [`strategy.md`](strategy.md) | How the repo-root `STRATEGY.md` is shaped and who reads it |

## Fixing and contributing

| Doc | Answers |
|---|---|
| [`troubleshooting.md`](troubleshooting.md) | Stuck tasks, wedged reviews, `.flow/` cleanup, uninstall, and the [leftover `.flow/bin/`](troubleshooting.md#i-have-flowbin-from-an-old-install) case |
| [`sync-codex.md`](sync-codex.md) | How the Codex mirror is generated and which guards must stay green |
| [`ci-workflow-example.yml`](https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/docs/ci-workflow-example.yml) | A drop-in GitHub Actions job running `flowctl validate --all` |

**Quick jumps into the CLI reference:** [`flowctl brief`](flowctl.md#brief) · [`flowctl chart`](flowctl.md#chart) · [`flowctl review-backend`](flowctl.md#review-backend) · [`flowctl prime classify`](flowctl.md#prime-classify) · [`flowctl repo-map`](flowctl.md#repo-map) · [`flowctl setup-block`](flowctl.md#setup-block) · [`flowctl validate`](flowctl.md#validate) · [`flowctl spec create`](flowctl.md#spec-create) · [`flowctl show`](flowctl.md#show) · [`flowctl pilot strikes`](flowctl.md#pilot-strikes) · [the deterministic review cap](flowctl.md#deterministic-review-cap)

**Deep links worth knowing:** [tiers](orchestration.md#tiers-what-kind-of-model-a-job-wants) · [review backends](orchestration.md#review-backends-cross-model-review) · [the bridge route](orchestration.md#implementation-offload-the-bridge-route) · [turning the review dial down](running-lean.md#turning-the-dial-none-and-host) · [finding identity and lineage](review-findings.md#identity-and-lineage) · [review bookkeeping authority](architecture.md#review-bookkeeping-authority-and-write-ordering) · [chart projection](tracker-sync.md#chart-lifecycle-projection) · [OpenCode install](platforms.md#opencode) · [backlog mode](../../skills/flow-next-flow/references/backlog-mode.md) · [chart workflow](../../skills/flow-next-chart/workflow.md) · [land workflow](../../skills/flow-next-land/workflow.md) · [make-pr create and finalize](../../skills/flow-next-make-pr/create-and-finalize.md) · [prime](../../skills/flow-next-prime/SKILL.md) · [drive](../../skills/flow-next-drive/SKILL.md) (consumes `.flow/features/` when present) · [chart resolve](flowctl.md#chart-resolve)

## Notable updates

- **`flow --auto`, the unattended driver (5.1.0)** - `/flow-next:flow --auto [<spec-id>]` drives a ready spec through its whole route in one invocation, hop after hop, classifying each hop from the same routing reference attended flow reads, and ends with the `PILOT_VERDICT` line drivers already parse; `--tick` runs one hop for hosts without stable long sessions. Pilot's rails (strikes ledger, dirty-tree refusal, PR probe, never merge, decision log) move across unchanged; `/flow-next:pilot` stays one release as an alias for `flow --auto --tick`; `pipeline.qa=auto` now takes effect unattended; `pipeline.chainStages` is deprecated. Enable: nothing - `/flow-next:flow --auto`. Details: [the auto workflow](../../skills/flow-next-flow/auto.md), [orchestration](orchestration.md), [CHANGELOG](https://github.com/gmickel/flow-next/blob/main/CHANGELOG.md).

- **A bare `/flow-next:flow` proceeds to the next best step (5.0.1)** - with no argument, flow resolves the item this conversation last touched, then the spec matching the current branch, then asks to capture intent no spec holds yet, then picks the next open spec by judgement with an inline pick on ties, then asks what to work on; the same release stops gate receipts failing on a stray `.git` above the working tree by honouring `GIT_CEILING_DIRECTORIES`. Enable: nothing - `/flow-next:flow` with no argument. Details: [the flow workflow](../../skills/flow-next-flow/workflow.md), [CHANGELOG](https://github.com/gmickel/flow-next/blob/main/CHANGELOG.md).

- **Flow, the attended conductor (5.0.0)** - `/flow-next:flow <anything>` reads what you have, picks the smallest sufficient route from the shared routing reference, runs it, and stops at the next decision that is yours; `--explain` prints the route without running it and replaces the retired guide router. Describe the request without naming a skill and flow picks it up: the route matrix covers eleven worked variants, including refactoring, performance, hill climb, investigation, and prototype; a stage's pick (a prospect candidate, a chart briefing's split) is asked inline and the run continues, stopping only on a decision that ends it. Direct execution is the default for a ready spec and plan needs a positive signal; `pipeline.qa` gains `auto`; capture, refine, and plan share one read-back shape. `/flow-next:interview` is renamed `/flow-next:refine` (the alias forwards for one release), `refine --scope=research` reads the docs first and writes `## Resolved via Research`, and the read-only `why-scout` answers why questions from the investigation row. Details: [pipeline variations](pipeline-variations.md), [the flow skill](../../skills/flow-next-flow/SKILL.md), [read-back](read-back.md).

- **Optional task decomposition (4.18.0)** - a ready cohesive spec can run through Flow-Next work with its full acceptance contract and configured verification. Use `/flow-next:work <id> --no-plan`; add planning on a positive signal, where a plan was asked for, separate people implement, delivery is staged across several PRs, or the implementer is routed to another tier. Details: [pipeline variations](pipeline-variations.md#no-plan-route).

- **Managed review execution (4.17.0)** - compatible hosts can run reviews through their selected provider accounts while Flow-Next owns the review and receipt. Enable: update Flow-Next and use the host's managed review integration; standalone CLI behavior is unchanged. Details: [orchestration.md](orchestration.md#review-backends-cross-model-review).

See [documentation release history](release-history.md) for the accumulated behavior notes and [CHANGELOG](https://github.com/gmickel/flow-next/blob/main/CHANGELOG.md) for releases. Current defaults belong to each subsystem reference.

## Conventions

- **R17 cross-link discipline.** Each doc here is a self-contained reference. Canonical sources (`templates/spec.md`, `scripts/sync-codex.sh`, `STRATEGY.md`, `GLOSSARY.md`) are linked, never re-embedded.
- **Relative paths only.** No absolute `github.com/...` URLs anywhere in this tree - fork-survivable + offline-readable.
- **Length discipline.** Reference shape (tables, lists, schemas first; narrative second). Keep the answer complete; move release history and unrelated detail to their own pages.

## See also

- [`../README.md`](https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/README.md) - plugin overview, install, workflow narrative.
- [`../../../STRATEGY.md`](https://github.com/gmickel/flow-next/blob/main/STRATEGY.md) - flow-next's strategic intent + active tracks.
- [`../../../GLOSSARY.md`](https://github.com/gmickel/flow-next/blob/main/GLOSSARY.md) - canonical vocabulary (Spec, Task, R-ID, ...).
- [`../../../CONTRIBUTING.md`](https://github.com/gmickel/flow-next/blob/main/CONTRIBUTING.md) - contributor entry point (local dev, adding skills, releasing).
- [`../../../CLAUDE.md`](https://github.com/gmickel/flow-next/blob/main/CLAUDE.md) - repo-level guide for working in this codebase.
