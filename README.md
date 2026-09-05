<div align="center">

# Flow-Next

[![GitHub stars](https://img.shields.io/github/stars/gmickel/flow-next?style=flat&logo=github&label=Stars&color=2f6f5f)](https://github.com/gmickel/flow-next/stargazers)
[![CI](https://img.shields.io/github/actions/workflow/status/gmickel/flow-next/test-flow-next.yml?branch=main&label=CI%20%C2%B7%203%20OS)](https://github.com/gmickel/flow-next/actions/workflows/test-flow-next.yml)
[![Latest release](https://img.shields.io/github/v/release/gmickel/flow-next?label=Release&color=green)](https://github.com/gmickel/flow-next/releases/latest)
[![Mentioned in Awesome](https://awesome.re/mentioned-badge.svg)](https://github.com/ithiria894/awesome-claude-code-workflows)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

### Agents generate. flow-next proves.

**Implementation got cheap. Reviewing it, verifying it, and keeping a codebase coherent did not.**

Flow-Next is a workflow plugin that runs inside your coding agent. Give it the change you want and the rules your project follows. It turns that intent into specs, implementation, review, and pull requests with evidence. Your specs, decisions, and task state live in your repository.

<img src="assets/flow-next-pipeline.gif" alt="A real pipeline run: pilot plans the spec, cross-model plan review catches a gap and ships, the worker implements with tests, impl review ships, ending on the task receipt" width="860">

*A real recorded run: plan, then cross-model plan review (catches a missing guard, fix, SHIP), then implement plus tests, then impl review SHIP, ending on the receipt. Nothing staged; every frame is live output.*

<sub>The recording drives each tick with `claude -p "..."` (Claude Code's non-interactive / headless mode) so the whole run captures unattended. In normal use you type the prompt or the `/flow-next:...` command in your interactive session: same pipeline, same gates.</sub>

</div>

> 📖 **[Doc index](plugins/flow-next/docs/README.md)** · 👥 **[Teams guide](plugins/flow-next/docs/teams.md)** · 💬 **[Discord](https://discord.gg/f3DYq8AAm5)** · **[Full documentation site: flow-next.dev](https://flow-next.dev)**

---

## Why this exists

Generating a change is only part of the work. Someone still has to clarify the requirement, keep the implementation aligned with it, check the result, and explain the diff to a reviewer.

Flow-Next makes that work repeatable. A spec preserves intent beyond the chat. Focused workers reread it before implementing. Review and live QA examine the result, and the PR connects changes to their requirements and evidence. Start with one change, then adapt the same workflow to a team or an unattended backlog.

The [evidence page](https://flow-next.dev/project/evidence/) covers the measured problem behind this approach, field use, and internal evaluations. [One real change through review](plugins/flow-next/docs/worked-example.md) shows what the workflow produced in this repository.

## What you get

Decide what to build, build it, and verify the result. Describe the workflow in plain language or invoke its skills directly. The host agent runs the process and adapts it to the work.

**Everything reaches your queue already reviewed.**
A different model reviews every plan and every implementation, the loop iterates until SHIP, and a task cannot be marked done without evidence JSON.

**Open a PR that already makes its argument.**
The pull request arrives explaining itself: which acceptance criterion each change satisfies, which decisions still need a human, what deliberately did not change.

**Decide what to build before anyone builds it.**
An idea too big to write down gets charted one decision at a time; a conversation becomes a spec; a product owner and an engineer refine it in their own passes on one file.

**Your team's context lives in the repo.**
A review correction becomes a lesson the next task can read. Specs, decisions, glossary, and memory stay in your repository, available to the next agent and your teammates.

**Prove it in the running app, not by reading the source.**
Live QA drives the app the way a user would, from the spec's own criteria, and files what it finds with screenshots and a verdict you can audit.

**Hand over as much as the receipts have earned.**
One dial from a supervised pair to a loop draining the backlog overnight. The gates do not change as you climb.

**Plan on your best model, implement on a cheaper one.**
Name a model per role once in your `CLAUDE.md`, or say it in the prompt for a single run. Whatever you pick, the model that wrote the diff never reviews it. The pipeline shape per item and the model per job are decided separately, and each decision prints its reason: [orchestration](plugins/flow-next/docs/orchestration.md).

**A way of working, not a tool you bolt on.**
The same rails carry a solo developer on a Sunday and a fifty-person organisation on a rollout. The spec is the handover object, and it reads the same to product, engineering, and the next agent run.

**Your process outlives your agent.**
The same specs, gates, receipts, and task state across harnesses. In a harness that can dispatch subagents, the same routing runs across models in-host with no bridge at all. Specs and task state live under `.flow/`, in Git and available for review. The files remain readable when you stop using Flow-Next.

<details>
<summary><strong>The vocabulary underneath: seven tenets</strong></summary>

| Tenet | What it means |
|---|---|
| **Spec-driven** | Intent survives the chat. The unit of work is the spec, never the ticket, the transcript, or the PR title. One durable document at `.flow/specs/<id>.md`, evolving through layers. Acceptance criteria are prose judged against evidence (unlike ATDD, where a criterion only counts once it exists as an executable test). |
| **Context-fit planning** | Right-sized task slices. Specs decompose into dependency-ordered tasks, each sized to one fresh ~100k-token context window. |
| **Re-anchored work** | Fresh context per task. Every worker subagent re-reads the spec, the task, and git state before touching code: no token bleed, no stale assumptions. |
| **Adversarial gates** | Fix until SHIP. A *different* model (RepoPrompt / Codex / Copilot / Cursor) reviews every plan and every implementation. Different models make different mistakes, and the disagreement surface is where the gaps live. |
| **Receipts** | "Done" means there is proof. Commits, tests, review verdicts, and evidence recorded per task, never narration. |
| **Multi-harness** | One workflow everywhere. First-class on Claude Code, OpenAI Codex, Factory Droid, Cursor, xAI Grok Build, and OpenCode. |
| **Self-improving** | Compounds as you work. Memory, glossary, decision records, and strategy grow as side-effects of the workflow you already run, with no manual "refresh" ceremony, ever. |

</details>

## Where it already runs

Flow-Next's ways of working are coached and run in enterprise engineering organisations worldwide, from CAD and construction software to proptech and education, across modern monorepos, hundred-repo microservice estates, and 30-year-old legacy stacks, on GitHub Enterprise, GitLab, and Jira. A 2-3 hour structured discovery interview reliably produces 8-11 implementation-ready specs with numbered acceptance criteria, boundaries, and task breakdowns; the edge cases surface in the interview instead of the sprint. Receipts, evidence JSON, and review gates are the audit trail enterprise adoption asks for: approval checkpoints and traceability are built in.

Try it on one change that crosses roles. Check whether the spec makes the intended behavior clear, the review catches a concrete defect, and the PR gives the next person enough evidence to decide. Use those handovers to judge which stages your team needs.

The open-source record is linkable, so it speaks in its own words: an outside contributor shipping a correct `flowctl` patch in [PR #95](https://github.com/gmickel/flow-next/pull/95), a feature in [awesome-claude-code-workflows](https://github.com/ithiria894/awesome-claude-code-workflows) for plan-first workflows, Ralph autonomous mode, and receipt-based gating ([#96](https://github.com/gmickel/flow-next/issues/96)), and a [3-OS test matrix](https://github.com/gmickel/flow-next/actions) on every push, because the field runs all three.

> *"I am enjoying your version of all these cool new plugins. So far yours has worked the best."*
> [@patrickmichalina](https://github.com/gmickel/flow-next/issues/5#issuecomment-3734228766)

> *"really enjoying this project, thanks for making it and making it public"*
> [@possibilities](https://github.com/gmickel/flow-next/pull/95), external contributor

> *"it’s been really useful in my workflow."*
> [@raydocs](https://github.com/gmickel/flow-next/issues/4)

---

## Quick start

### Install

<!-- CANONICAL INSTALL BLOCK - change here first.
     Instanced at:
       - plugins/flow-next/docs/platforms.md (platform matrix row + the Factory Droid install fence)
       - https://flow-next.dev/install (site; maintainer-only, per the contributing guide)
     agent_docs/local-dev.md is NOT an instance - it installs the local marketplace (`./`) for
     contributors and intentionally diverges. Keep the user-facing copies as real copies: an
     install command a reader has to click through to is a worse install command. -->

<table>
<tr>
<td><strong>Claude Code</strong></td>
<td><strong>OpenAI Codex</strong></td>
<td><strong>Factory Droid</strong></td>
</tr>
<tr>
<td>

```bash
/plugin marketplace add \
  https://github.com/gmickel/flow-next
/plugin install flow-next
/reload-plugins
/flow-next:setup
```

</td>
<td>

```bash
git clone https://github.com/gmickel/flow-next.git
cd flow-next
./scripts/install-codex.sh flow-next
# For another Codex home (any path you like):
# CODEX_HOME="$HOME/.codex-work" ./scripts/install-codex.sh
# Run once per home.
# then, in your project’s Codex conversation: $flow-next-setup
```

</td>
<td>

```bash
droid plugin marketplace add \
  https://github.com/gmickel/flow-next
# /plugins → install flow-next
```

</td>
</tr>
</table>

Use installation commands in your terminal or the host's plugin interface as shown above. Workflow invocations belong in the agent conversation. Codex uses `$flow-next-<name>`; OpenCode uses `/flow-next-<name>`; the other hosts accept `/flow-next:<name>` (Cursor also accepts the hyphen form).

**Cursor, Grok Build, or OpenCode?** [Install by platform](plugins/flow-next/docs/platforms.md) has the current steps. Codex installs are per home; set `CODEX_HOME` when you use more than one.

**Trying it for the first time?** [Your First 30 Minutes](https://flow-next.dev/first-30-minutes/) includes a two-file Python example, the review setup, and the output to inspect. You need your agent access, Python 3.11+, and the project tools; review and GitHub PR plumbing also use `jq` and `gh`.

### The 5-command happy path

```bash
/flow-next:capture                   # 1. Synthesize conversation → .flow/specs/<id>.md
/flow-next:plan <spec-id>            # 2. Break the spec into dependency-ordered tasks
/flow-next:work <spec-id>            # 3. Execute tasks in fresh-context worker subagents
/flow-next:make-pr <spec-id>         # 4. Render a cognitive-aid PR body (9 input streams)
/flow-next:resolve-pr <PR#>          # 5. Fetch review threads → triage → resolve
```

This is a starting route. You can work a fully understood spec directly, review a risky approach before implementation, or add live QA before the PR. The [route guide](plugins/flow-next/docs/pipeline-variations.md) explains when each stage helps; [running lean](plugins/flow-next/docs/running-lean.md) explains the agent work each layer adds.

### After every update

**Nothing to do.** Nothing is copied into your repo: `flowctl` resolves from the plugin install on every host, the agent guide is pulled live via `flowctl usage`, and the spec template resolves from the bundled copy. Plugin updates land silently. Re-run `/flow-next:setup` only when setup tells you the docs-snippet schema bumped, or to change configuration. If a repo still carries `.flow/bin/` from an older install, delete it; setup offers to, and nothing reads it. Details: [platforms.md](plugins/flow-next/docs/platforms.md).

---

## Compose the pipeline

Start with the established workflow, then shape it in plain language. Choose which stages run, which models do the work, and what must pass before merge. Keep a policy in `CLAUDE.md` or `AGENTS.md` for repeated use, or steer one run in conversation.

| Your situation | What to say |
|---|---|
| A small change you will review | "Work this change directly; I will review the diff." |
| A migration whose approach needs checking | "Plan this migration first, then review the approach with another model family." |
| Ready work between your visits | "Work the ready backlog overnight; stop on unresolved product decisions." |
| A prototype that settled the requirements | "Capture the intent from this prototype, then plan it against our architecture." |
| Several jobs that need different models | "Keep the UI work yourself; send the API plumbing to the implementer tier." |

The host reads the item's state and your instructions, chooses the route, and reports its reason. A stage you invoke keeps its execution and evidence contract; configured review policy applies across the arrangements you choose. [Pipeline variations](plugins/flow-next/docs/pipeline-variations.md) · [Orchestration and model routing](plugins/flow-next/docs/orchestration.md) · [Cookbook](https://flow-next.dev/guides/cookbook/).

### One change through review

In [PR #215](https://github.com/gmickel/flow-next/pull/215), a performance change batched Git searches. Requirement R8 said reference attribution must stay unchanged. Review caught a forced-color Git setting that broke output parsing and dropped references. The correction added `--color=never`; the task recorded the fix and verification, and the PR pointed the human reviewer at that exact change.

[Follow the requirement, correction, and evidence](plugins/flow-next/docs/worked-example.md).

<div align="center">
<img src="assets/flow-next-pr-body.png" alt="PR #215 connects acceptance criteria to tasks and evidence commits, then directs the reviewer to the important changes" width="720">
</div>

The optional [HTML views](plugins/flow-next/docs/html-artifacts.md) present the same spec and PR information for readers who prefer a visual review surface.

## Going autonomous

Pilot advances ready specs toward draft pull requests. Land handles CI, review convergence, and the merge policy you authorized. Your host loop or scheduler calls them repeatedly. The same skills you use interactively do the work.

```text
Work the ready specs overnight. Plan changes with unresolved design risk,
work fully understood changes directly, review with another model family,
and run live QA before opening the PR. Stop on product decisions I need
to make. Use land under this repository's merge policy.
```

[Drive a loop](https://flow-next.dev/autonomy/driving-a-loop/) for your host, or read [unattended operation](https://flow-next.dev/autonomy/unattended-operation/) for isolation, readiness, and stop conditions. [The field case](plugins/flow-next/docs/orchestration.md#field-case-one-paragraph-38-prs-landed) describes a run that landed 38 PRs under one paragraph of policy.

**Existing Ralph installation?** Ralph is deprecated; its [reference](plugins/flow-next/docs/ralph.md) remains available. New setups should use pilot and land.

## Why it works

| What needs to survive | Mechanism |
|---|---|
| Intent across sessions | A durable spec with numbered acceptance criteria |
| Context across tasks | Fresh workers reread the spec, task, and current Git state |
| Review findings | A fix-and-review loop with recorded verdicts |
| Verification | Test evidence and receipts connected to the work |
| Human understanding | A PR that maps requirements to changes and directs review attention |
| Lessons from earlier work | Repository memory read by later tasks |

<a id="what-flow-next-is-not"></a>

## Where it fits

Flow-Next is useful when requirements, coordination, or review deserve a record that outlives a chat. It works inside your coding agent and alongside your repository, tests, CI, and tracker. Use direct edits for disposable work where no durable context matters.

Humans own product decisions, risk tolerance, and production responsibility. The workflow makes those decisions easier to inspect through specs and evidence. Stage selection and model routing remain yours to shape.

## Commands

Use the skill name or describe what you want in the agent conversation. The [skills catalog](plugins/flow-next/docs/skills.md) covers all 32 skills and their invocation forms; the [CLI reference](plugins/flow-next/docs/flowctl.md) covers scripting and state inspection.

| Job | Skills |
|---|---|
| Shape intent | `capture`, `interview`; `chart` for an oversized unclear idea |
| Plan and implement | `plan`, `work` |
| Review and verify | `plan-review`, `impl-review`, `spec-completion-review`, `qa` |
| Open and finish a PR | `make-pr`, `resolve-pr`, `land` |
| Keep work moving | `pilot` |
| Maintain project knowledge | `audit`, `features`, `strategy`, `sync` |

[Guide](plugins/flow-next/skills/flow-next-guide/SKILL.md) recommends a next step when you are unsure where to start. The optional `/flow-next:chart` stage resolves an oversized idea one decision at a time before capture. [Review findings](plugins/flow-next/docs/review-findings.md) keep a defect's identity and history across review rounds.

## Adopting in a team

Start with one repository and one change. Product reviews the goal and acceptance criteria in a shared spec. Engineering adds constraints and reviews the approach. Agents implement the tasks. The reviewer receives a PR connecting the changes to those criteria and their evidence.

After the trial, judge whether the spec surfaced a missed decision, review found useful defects, and the PR reduced investigation work. Add the stages that earn their time. [Team guide](plugins/flow-next/docs/teams.md).

Keep your existing board when the team needs it. The [tracker bridge](plugins/flow-next/docs/tracker-sync.md) projects specs to Linear, GitHub, GitLab, or Jira and reconciles them two-way. Claude Code teams can deploy the plugin through [managed settings](https://flow-next.dev/install/#team--org-wide-deployment-claude-code-managed-settings), with setup once per repository.

## Where to look

| You want to | Website | Repository reference |
|---|---|---|
| Try one change | [First run](https://flow-next.dev/first-30-minutes/) | [Quick start](#quick-start) |
| See an actual review correction | [Worked example](https://flow-next.dev/guides/worked-example/) | [Worked example](plugins/flow-next/docs/worked-example.md) |
| Choose or adapt the workflow | [Routes](https://flow-next.dev/choosing-your-route/) | [Pipeline variations](plugins/flow-next/docs/pipeline-variations.md) |
| Assign models and drive loops | [Orchestration](https://flow-next.dev/guides/model-routing/) | [Orchestration](plugins/flow-next/docs/orchestration.md) |
| Adopt with a team | [For teams](https://flow-next.dev/guides/for-teams/) | [Teams](plugins/flow-next/docs/teams.md) |
| Choose optional layers | [Costs](https://flow-next.dev/understand/what-each-layer-costs/) | [Running lean](plugins/flow-next/docs/running-lean.md) |
| Inspect commands or receipts | [Reference](https://flow-next.dev/reference/) | [Docs index](plugins/flow-next/docs/README.md) |
| Recover or uninstall | [Troubleshooting](https://flow-next.dev/reference/troubleshooting/) | [Troubleshooting](plugins/flow-next/docs/troubleshooting.md) |

## Requirements

Flow-Next is MIT-licensed. You supply access to your coding agent and its providers, plus your project environment. Additional planning, implementation, review rounds, and live QA consume agent usage. There is no Flow-Next account or hosted service to run.

- **Python 3.11+** (or the `py` launcher on Windows): the bundled `flowctl` CLI is pure-stdlib. Launchers skip broken aliases and working interpreters below the supported floor before loading flowctl.
- **`jq`** and **`gh`**: required for the review subsystem and PR plumbing.
- **`bun`** *(optional)*: only needed for the [Ralph TUI](flow-next-tui/).

## Platforms

First-class on Claude Code, OpenAI Codex, Factory Droid, Cursor, xAI Grok Build, and OpenCode.

| Platform | Status |
|---|---|
| Claude Code | First-class (canonical surface) |
| OpenAI Codex (CLI + Desktop) | First-class (mirror at `plugins/flow-next/codex/`, regenerated by `scripts/sync-codex.sh`) |
| Factory Droid | First-class (regex-OR matchers handle `Execute` ↔ `Bash`) |
| Cursor | First-class. **Recommended:** team-marketplace repo import (admin imports this GitHub repo via the Cursor GitHub App; Default Off/On/Required; auto-refresh on push). **Fallback:** local plugin (`./scripts/install-cursor.sh` / `install-cursor.ps1`). Skills, commands, multi-agent, native asks, slash autocomplete verified; Ralph intentionally not built for Cursor ([details](plugins/flow-next/docs/platforms.md#cursor)) |
| Grok Build (xAI) | First-class via Claude Code compatibility: skills, `/flow-next:*` commands, hooks, and **multi-agent flows** (verified). Type **`/flow-next:`** to open the command autocomplete; `/flow-next-` filters the separate hyphen-named skill surface. Ralph intentionally not built ([details](plugins/flow-next/docs/platforms.md#grok-build-claude-code-compatibility)) |
| OpenCode | `./scripts/install-opencode.sh` (see [`docs/platforms.md`](plugins/flow-next/docs/platforms.md#opencode)) |

Detailed install + cross-platform patterns in [`docs/platforms.md`](plugins/flow-next/docs/platforms.md), the canonical home for the tiering sentence above.

> **Upgrading from 0.x?** The 1.0 release renamed the `epic` surface to `spec`; the legacy aliases and automated migration commands were removed in 3.0. Update the plugin, then follow the manual three-step pre-1.0 layout port in [troubleshooting](plugins/flow-next/docs/troubleshooting.md#pre-10-layout-porting).

## Ecosystem

| Project | Platform |
|---|---|
| [flow-next-opencode](https://github.com/gmickel/flow-next-opencode) | OpenCode, superseded by the in-repo installer |
| [FlowFactory](https://github.com/Gitmaxd/flowfactory) | Factory.ai Droid |
| [Ralph TUI](flow-next-tui/) | Cross-platform TUI for Ralph runs |

## Contributing

Bug reports and PRs welcome: start at [`CONTRIBUTING.md`](CONTRIBUTING.md) (local dev, adding skills, the docs-only rule) and [`SECURITY.md`](SECURITY.md) for private disclosure. Questions and show-and-tell: [GitHub Discussions](https://github.com/gmickel/flow-next/discussions). Or come say hi on [Discord](https://discord.gg/f3DYq8AAm5).

Every PR runs the same gate: the full test suite on a 3-OS matrix (Ubuntu / macOS / Windows) plus an offline docs-linkcheck - green CI is the merge floor.

## Also check out

> **[GNO](https://gno.sh)**: local hybrid search for your notes, docs, and code. Long-term memory over your files via MCP.
>
> ```bash
> bun install -g @gmickel/gno && gno mcp install --target claude-code
> ```

---

## License

MIT. See [`LICENSE`](LICENSE).

<div align="center">

Made by [Gordon Mickel](https://mickel.tech) · [@gmickel](https://twitter.com/gmickel) · [gordon@mickel.tech](mailto:gordon@mickel.tech)

[![Author](https://img.shields.io/badge/Author-Gordon_Mickel-orange)](https://mickel.tech)
[![Twitter](https://img.shields.io/badge/@gmickel-black?logo=x)](https://twitter.com/gmickel)

[![Sponsor](https://img.shields.io/badge/Sponsor_this_project-❤-ea4aaa?style=for-the-badge)](https://github.com/sponsors/gmickel)

</div>

<!-- Retained anchors for older links into the expanded tutorial. -->
<a id="how-the-flow-works"></a>
