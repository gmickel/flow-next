<div align="center">

# Flow-Next

[![GitHub stars](https://img.shields.io/github/stars/gmickel/flow-next?style=flat&logo=github&label=Stars&color=2f6f5f)](https://github.com/gmickel/flow-next/stargazers)
[![CI](https://img.shields.io/github/actions/workflow/status/gmickel/flow-next/test-flow-next.yml?branch=main&label=CI%20%C2%B7%203%20OS)](https://github.com/gmickel/flow-next/actions/workflows/test-flow-next.yml)
[![Latest release](https://img.shields.io/github/v/release/gmickel/flow-next?label=Release&color=green)](https://github.com/gmickel/flow-next/releases/latest)
[![Mentioned in Awesome](https://awesome.re/mentioned-badge.svg)](https://github.com/ithiria894/awesome-claude-code-workflows)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

### Faster than your agent alone. And better.

**Agents generate. Flow-Next proves.**

</div>

Flow-Next is a workflow plugin for your coding agent. Hand it a bug, an idea, a ticket or a slow page, and it takes the work all the way to a pull request. It picks the route that kind of work needs, builds the change, gets it reviewed by another model family when the risk calls for it, and hands you something you can check instead of something you have to trust.

It's also fast now. On the same model, the working change comes back in about the time your agent takes on its own, often less, and a large feature in about half the time. The result is better than the plain agent's before any review runs, and review and live QA widen that gap.

| You say | What Flow-Next does |
|---|---|
| "This fails: `<pasted stack trace>`" | Turns the failure into a failing test, fixes the cause, and shows you the test going from red to green. |
| "Add passwordless login" (or the conversation you just had about it) | Writes a spec with numbered acceptance criteria, builds it, has it reviewed, and opens a PR that maps every change to a criterion when you ask for one. |
| "The /reports page takes four seconds, it should take under one" | Measures the real page before touching anything. The before-and-after numbers are the evidence. |
| "Extract the pricing rules into their own module" | Pins the current behaviour with a characterization test first, so the refactor has to keep it. |
| "Work ticket WOR-17" | Reads the issue with the access you already have and routes on what it says. |
| "Why does the parser reject empty headers?" | Answers from git history and the project's decision memory, with citations. Writes nothing. |
| `/flow-next:flow --auto` | The same thing with nobody watching. It never stops to ask, keeps fixing until the reviewer signs off, and writes every call it made on your behalf into the PR. Add `--until=merge` and it also watches CI and review threads and merges the PR when your checks allow it. |

Every stage prints `ran`, `skipped(<reason>)` or `failed(<reason>)`, so you can see what happened and what didn't. The model that wrote a diff never reviews it. Specs, decisions, task state and receipts live under `.flow/` in your repository and stay readable if you stop using Flow-Next. `flow --explain <anything>` shows the route it would take, and why, without running it.

It runs on Claude Code, OpenAI Codex, Factory Droid, Cursor, xAI Grok Build and OpenCode.

> 📖 **[Documentation: flow-next.dev](https://flow-next.dev)** · 💬 **[Discord](https://discord.gg/f3DYq8AAm5)**

---

## How much faster, and how much better

I measured this over more than 170 full end-to-end runs against plain Claude Code on the same model, each case run several times. Hidden tests the agent never sees check every result, and a blind judge scores the handoff. Speed is time to the working change, before any review or QA.

| Task | Speed on the work | Quality | What the quality stages did |
|---|---|---|---|
| Large feature | **up to 1.9x** faster | **+25%** | Plain Claude Code shipped a data-integrity bug in every run. Flow-Next's reviewers caught it every time, before the pull request. |
| Held-out large feature (Rust) | **1.2x** faster | **+48%** | Four real bugs fixed, including a race condition. Flow-Next passed every hidden test; plain Claude Code failed one run in three. |
| Hard bug | **about 2x** faster | **+9%** | Found the real cause and fixed it there, instead of loosening the flaky test. |
| Simple bug | **1.2x** faster | **+10%** | No review needed. The gain comes from how it works: a failing test first, a fix at the cause, then a check that it works for the user. |
| Small feature | **1.1-1.3x** faster | **+8%** | The reviewer caught a setup check the new option broke. Fixed before handoff. |

Unattended, with `--until=merge`, a large feature went from spec to a merged pull request with nobody watching and no stops, in about half the time plain Claude Code took to build it. The [evidence page](https://flow-next.dev/project/evidence/) has the method and the rest of the numbers.

---

## Why this exists

Writing the code got cheap. Everything around it didn't: pinning down what was actually asked, keeping the build aligned with it, checking the result, and explaining the diff to whoever reviews it. That work is where agent-written code quietly goes wrong, and it's the part I wanted to make repeatable.

So the spec lives in `.flow/specs/<id>.md` instead of a chat that scrolls away. The build reads it before it touches code. When the risk calls for it, a model from another family checks the change, because a model reviewing its own work shares its own blind spots. And the PR shows which criterion each change satisfies and what proves it. It can't promise that the codebase stays easy to maintain. That still takes people who care about it.

---

## Install

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
# then, in your project's Codex conversation: $flow-next-setup
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

**Cursor, Grok Build, or OpenCode?** [Install](https://flow-next.dev/install/) has the current steps per host, including the Cursor team-marketplace import and Claude Code managed settings for an organisation. Codex installs are per home; set `CODEX_HOME` when you use more than one.

## Start one change

1. Install for your host with the block above, then run `/flow-next:setup` in a project (Codex: `$flow-next-setup`). Setup writes the agent instruction snippet and asks once which reviewer you want.
2. Tell it what you have: `/flow-next:flow <anything>`. A pasted error, an idea, a spec id, a branch or a ticket all work. Flow picks the smallest route that does the job, runs it, and stops at the next decision that's yours. For an idea too big to write down in one go, the optional `/flow-next:chart` stage comes first.
3. Read what it hands back. The stage lines say what ran and what was skipped and why. Say "open the PR" when you want one; its body maps each change to the acceptance criterion it satisfies.

[Your first 30 minutes](https://flow-next.dev/first-30-minutes/) walks through the same three steps on a two-file Python example, review setup and all. You need your agent, Python 3.11+ and the project's own tools; review and PR steps also use `jq` and `gh`.

## Land a pull request

`/flow-next:land <PR>` works one named PR to the finish: it resolves review feedback and CI failures, then squash merges it once you've authorized the merge. make-pr commits the finished spec and task statuses before it opens the PR, so the merge carries them to your base branch. Land checks every spec on the PR's branch and merges only when all of them are closed.

Land takes one PR at a time. To land several, pick the open PRs whose branch carries a closed spec, and run land on each one with your merge authorization. It never sweeps the repository for PRs on its own.

If you want a stricter bar before merging, set it in your instruction file, in branch protection, or with `land.mergeVerdictCommand`. The [troubleshooting guide](plugins/flow-next/docs/troubleshooting.md) covers landing and manual rebases, and the [upgrade notes](plugins/flow-next/docs/flowctl.md#landing-upgrade) cover major versions.

## Where to read more

The full documentation is at [flow-next.dev](https://flow-next.dev). This repository keeps this page and the reference files the skills read while they run, under [`plugins/flow-next/docs/`](plugins/flow-next/docs/README.md).

- [Introduction](https://flow-next.dev/introduction/): what each stage does, and what Flow-Next refuses to claim.
- [Choosing your route](https://flow-next.dev/choosing-your-route/): which stages a bug, a feature, a refactor or a performance request gets, and why the direct route is the default.
- [Evidence & evals](https://flow-next.dev/project/evidence/): the benchmark against a plain agent, the research behind verification, and our own evals, including the ones that killed a feature.
- [Going autonomous](https://flow-next.dev/autonomy/going-autonomous/): `flow --auto`, `--until=merge`, the Decisions list and when a run stops.
- [For teams](https://flow-next.dev/guides/for-teams/): the spec as the handover between product, engineering and the agent, plus the tracker bridge to Linear, GitHub, GitLab and Jira.
- [Model routing](https://flow-next.dev/guides/model-routing/): send each job to the model or harness that fits it, from one block in your instruction file.
- [Review backends](https://flow-next.dev/reference/review-backends/): Codex, Copilot, Cursor, Claude and host review, and why the reviewer must come from another family.
- [Configuration](https://flow-next.dev/flowctl/configuration/): every `.flow/config.json` key, generated from the schema.
- [Skills](https://flow-next.dev/skills/): every skill and how to call it, and the [CLI reference](https://flow-next.dev/flowctl/cli-reference/) for `flowctl`.
- [Changelog](https://flow-next.dev/releases/changelog/): release highlights. [`CHANGELOG.md`](CHANGELOG.md) here is the full record.
- [Discord](https://discord.gg/f3DYq8AAm5) for questions, and [`CONTRIBUTING.md`](CONTRIBUTING.md) for local development and the docs-only rule.

## Where it already runs

The engineering methodology built on Flow-Next is coached and run in engineering organisations around the world: CAD and construction software, proptech, education. That covers modern monorepos, estates of a hundred microservices and 30-year-old legacy stacks, on GitHub Enterprise, GitLab and Jira. Teams running it report a 3x speed-up on average across the whole R&D organisation, from discovery to merged code, at a higher quality of output: more than 1,000 developers across a private-equity portfolio. An hour-long discovery interview typically produces 8 to 11 specs ready to build, with numbered acceptance criteria, boundaries and task breakdowns, and the edge cases come up in the interview instead of mid-sprint. Receipts, evidence and review gates give you the approval checkpoints and the trail back from each change to its requirement.

The open-source side you can check for yourself: an outside contributor's correct `flowctl` patch in [PR #95](https://github.com/gmickel/flow-next/pull/95), a listing in [awesome-claude-code-workflows](https://github.com/ithiria894/awesome-claude-code-workflows) for plan-first workflows and receipt-based gating ([#96](https://github.com/gmickel/flow-next/issues/96)), and a [test matrix on three operating systems](https://github.com/gmickel/flow-next/actions) on every push, because people run it on all three.

> *"I am enjoying your version of all these cool new plugins. So far yours has worked the best."*
> [@patrickmichalina](https://github.com/gmickel/flow-next/issues/5#issuecomment-3734228766)

> *"really enjoying this project, thanks for making it and making it public"*
> [@possibilities](https://github.com/gmickel/flow-next/pull/95), external contributor

> *"it’s been really useful in my workflow."*
> [@raydocs](https://github.com/gmickel/flow-next/issues/4)

## License

MIT. See [`LICENSE`](LICENSE).

<div align="center">

Made by [Gordon Mickel](https://mickel.tech) · [@gmickel](https://twitter.com/gmickel) · [gordon@mickel.tech](mailto:gordon@mickel.tech)

[![Author](https://img.shields.io/badge/Author-Gordon_Mickel-orange)](https://mickel.tech)
[![Twitter](https://img.shields.io/badge/@gmickel-black?logo=x)](https://twitter.com/gmickel)

[![Sponsor](https://img.shields.io/badge/Sponsor_this_project-❤-ea4aaa?style=for-the-badge)](https://github.com/sponsors/gmickel)

</div>
