# Flow-Next docs

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>` — and when the written name itself already starts with `flow-next-` (e.g. `/flow-next:flow-next-drive`), the prefix is not doubled: invoke `$flow-next-drive`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts' own syntax and are quoted verbatim — do not convert them.


The canonical user documentation is [flow-next.dev](https://flow-next.dev). Read it for the introduction, [choosing your route](https://flow-next.dev/choosing-your-route/), [autonomy](https://flow-next.dev/autonomy/going-autonomous/), [teams](https://flow-next.dev/guides/for-teams/), [model routing](https://flow-next.dev/guides/model-routing/), [review backends](https://flow-next.dev/reference/review-backends/), [configuration](https://flow-next.dev/flowctl/configuration/), the [skills catalog](https://flow-next.dev/skills/), and the [changelog](https://flow-next.dev/releases/changelog/). A page that used to live here and is now only on the site is not coming back; a release updates the site.

The files below stay in the repository because something at runtime reads them: a skill, an agent, a template, a hook, the config schema, or a test that pins their content. Every cross-link is a relative repo path so a fork and an offline clone keep working, and `scripts/sync-codex.sh` mirrors this directory into `codex/docs/flow-next/` for Codex installs.

## Runtime reference

| Doc | Who reads it |
|---|---|
| [`prose.md`](prose.md) | Every emission point: 20 skills and 2 agents cite it before drafting a PR body, spec, comment, memory entry, or changelog line |
| [`flowctl.md`](flowctl.md) | `templates/usage.md` and the qa, flow, impl-review, and spec-completion-review skills point at command sections; the surface test checks every documented leaf command exists |
| [`orchestration.md`](orchestration.md) | `templates/usage.md` links the tiers and reach sections; the Cursor host test pins the alias-to-inherit statement |
| [`reach/README.md`](reach/README.md) and the per-harness pages | The worker and work phases resolve the implementer tier through reach; the capture, make-pr, and setup skills read [`reach/codex.md`](reach/codex.md) and [`reach/cursor.md`](reach/cursor.md); the Codex installer test checks the tree |
| [`read-back.md`](read-back.md) | Capture, plan, and refine read it before the first `.flow/` write |
| [`pipeline-variations.md`](pipeline-variations.md) | The flow skill's [`route-matrix.md`](../../skills/flow-next-flow/references/route-matrix.md) and capture's rewrite mode cite it; the routing test scans it as a consumer of the shared routing reference |
| [`skills.md`](skills.md) | The resolve-pr skill and the route matrix cite the backend-split heuristic; the count test pins the 31 skills table |
| [`tracker-sync.md`](tracker-sync.md) | Capture, make-pr, and work read the retro-fire rule; `flowctl_tracker` code and the config schema cite the fn-64 ordering rule |
| [`memory-schema.md`](memory-schema.md) | The qa skill maps bug categories through it |
| [`html-artifacts.md`](html-artifacts.md) | The html-lens references in capture, make-pr, and plan; the fixture-contract test reads it |
| [`pr-cognitive-aid.md`](pr-cognitive-aid.md) | The consumer contract for the PR walkthrough; the fixture-contract test pins it against the make-pr skill copy |
| [`review-findings.md`](review-findings.md) | The structured findings contract; its test pins the schema fields, bounds, and identity grammar |
| [`judge.md`](judge.md) | The setup workflow links it for key handling; the config schema descriptions point at it |
| [`running-lean.md`](running-lean.md) | Seven config schema descriptions point at it for the cost of each optional layer |
| [`spec-template.md`](spec-template.md) | `templates/spec.md` cites it for the scaffold rules and the auxiliary-section list |
| [`teams.md`](teams.md) | `templates/spec.md` cites the symmetric interview pattern; the count test pins the commands table |
| [`architecture.md`](architecture.md) | The `.flow/` layout and the review bookkeeping authority; the chart inventory and review-findings tests read it |
| [`platforms.md`](platforms.md) | The canonical supported-platforms sentence and the platform matrix; the Cursor, Ralph, and tracker distribution tests pin its sections |
| [`troubleshooting.md`](troubleshooting.md) | The land skill's chains reference and the bug report template link into it |
| [`ralph.md`](ralph.md) | The `ralph-guard` hook cites it; the Ralph docs-truth test pins the opt-in and control-surface facts |
| [`sync-codex.md`](sync-codex.md) | The Ralph docs-truth test checks no hook-generation step returns |
| [`glossary.md`](glossary.md) | How the repo-root `GLOSSARY.md` file is shaped, resolved, and edited with `flowctl glossary`; no site page covers the file mechanics yet |
| [`ci-workflow-example.yml`](https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/docs/ci-workflow-example.yml) | `flowctl.md` links it as the drop-in `flowctl validate --all` job; the mirror rewrites its link |

Skill prose lives beside each skill under `../skills/`. The flow conductor is [`flow-next-flow/SKILL.md`](../../skills/flow-next-flow/SKILL.md) (`/flow-next:flow --explain` prints a route without running it), and the optional chart stage is [`flow-next-chart/SKILL.md`](../../skills/flow-next-chart/SKILL.md).

## Conventions

- **Cross-link discipline.** Canonical sources (`templates/spec.md`, `scripts/sync-codex.sh`, `STRATEGY.md`, `GLOSSARY.md`) are linked, never re-embedded.
- **Relative paths only** inside this tree. Links to the site use the full `https://flow-next.dev/...` URL.
- **No mirrored pages.** A page that explains the product to a human belongs on flow-next.dev. A file lands here only when something at runtime reads it, and it leaves when nothing does.

## See also

- [`../README.md`](https://github.com/gmickel/flow-next/blob/main/plugins/flow-next/README.md) - plugin overview.
- [`../../../STRATEGY.md`](https://github.com/gmickel/flow-next/blob/main/STRATEGY.md) - flow-next's strategic intent and active tracks.
- [`../../../GLOSSARY.md`](https://github.com/gmickel/flow-next/blob/main/GLOSSARY.md) - canonical vocabulary (Spec, Task, R-ID, ...).
- [`../../../CONTRIBUTING.md`](https://github.com/gmickel/flow-next/blob/main/CONTRIBUTING.md) - contributor entry point.
- [`../../../agent_docs/releasing.md`](https://github.com/gmickel/flow-next/blob/main/agent_docs/releasing.md) - the release walk, including which documentation surface each step updates.
