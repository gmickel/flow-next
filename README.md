<div align="center">

# Flow-Next

[![GitHub stars](https://img.shields.io/github/stars/gmickel/flow-next?style=flat&logo=github&label=Stars&color=2f6f5f)](https://github.com/gmickel/flow-next/stargazers)
[![CI](https://img.shields.io/github/actions/workflow/status/gmickel/flow-next/test-flow-next.yml?branch=main&label=CI%20%C2%B7%203%20OS)](https://github.com/gmickel/flow-next/actions/workflows/test-flow-next.yml)
[![Latest release](https://img.shields.io/github/v/release/gmickel/flow-next?label=Release&color=green)](https://github.com/gmickel/flow-next/releases/latest)
[![Mentioned in Awesome](https://awesome.re/mentioned-badge.svg)](https://github.com/ithiria894/awesome-claude-code-workflows)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

### Agents generate. flow-next proves.

**Implementation got cheap. Reviewing it, verifying it, and keeping a codebase coherent did not.**

</div>

Flow-Next runs inside your coding agent. Give it anything you need to fix, improve, or build. It picks the pipeline for that kind of work, runs it with a different model family reviewing every handover, and stops at a pull request that carries its own evidence.

| You say | What Flow-Next does |
|---|---|
| "This fails: `<pasted stack trace>`" | Reproduces it as a failing test, makes that test the requirement, fixes it, gets the fix reviewed, opens a draft PR. |
| "Add passwordless login" (or the conversation you just had about it) | Captures a spec with numbered acceptance criteria, builds it, reviews it, opens a PR that maps every change to a criterion. |
| "The /reports page takes four seconds, it should take under one" | Measures on a real surface before any edit. The before-and-after numbers are the evidence. |
| "Extract the pricing rules into their own module" | Pins a characterization test first, so the refactor is proven to keep behaviour. |
| "Work ticket WOR-17" | Reads the issue through the access you already have and routes on what it says. |
| "Why does the parser reject empty headers?" | Answers with citations from git history and the project's decision memory. Writes nothing. |
| `/flow-next:flow --auto` | The same pipeline unattended: routes, builds, reviews, opens the PR, and with `--until=merge` babysits CI and review threads and merges when the receipts say so. |

Every stage prints `ran`, `skipped(<reason>)`, or `failed(<reason>)`. The model that wrote the diff never reviews it. Specs, decisions, task state, and receipts live under `.flow/` in your repository and stay readable if you stop using Flow-Next. `flow --explain <anything>` prints the route it would take and why, and writes nothing.

First-class on Claude Code, OpenAI Codex, Factory Droid, Cursor, xAI Grok Build, and OpenCode.

> 📖 **[Documentation: flow-next.dev](https://flow-next.dev)** · 💬 **[Discord](https://discord.gg/f3DYq8AAm5)**

---

## Why this exists

Generating a change is the cheap part. Someone still has to pin down the requirement, keep the implementation aligned with it, check the result, and explain the diff to a reviewer. Flow-Next makes that work repeatable. A spec at `.flow/specs/<id>.md` preserves intent beyond the chat, a fresh worker rereads it before touching code, a second model family reviews the result, and the PR maps every change to a criterion and its evidence. The pipeline proves the change does what was asked and records what it did; it does not prove the codebase stays maintainable.

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

**Cursor, Grok Build, or OpenCode?** [Install](https://flow-next.dev/install/) has the current steps per host, including the Cursor team-marketplace import and Claude Code managed settings for an organisation. Codex installs are per home; set `CODEX_HOME` when you use more than one.

## Start one change

1. Install for your host with the block above, then run `/flow-next:setup` in a project (Codex: `$flow-next-setup`). Setup writes the agent instruction snippet and asks for a review backend once.
2. Say what you have in the agent conversation: `/flow-next:flow <anything>`. Flow reads a pasted error, an idea, a spec id, a branch, or a ticket, picks the smallest sufficient route, runs it, and stops at the next decision that is yours. `/flow-next:flow --explain` prints the route and writes nothing. The optional `/flow-next:chart` stage sits before capture for an idea too big to write down in one pass.
3. Read the PR it opens. Each stage line reads `ran`, `skipped(<reason>)`, or `failed(<reason>)`, and the PR body maps each change to the acceptance criterion it satisfies.

[Your first 30 minutes](https://flow-next.dev/first-30-minutes/) walks the same three steps on a two-file Python example, including the review setup and the output to inspect. You need your agent access, Python 3.11+, and the project's own tools; review and PR plumbing also use `jq` and `gh`.

## Where to read more

The documentation lives at [flow-next.dev](https://flow-next.dev). The repository keeps this page and the reference files the skills read at runtime under [`plugins/flow-next/docs/`](plugins/flow-next/docs/README.md).

- [Introduction](https://flow-next.dev/introduction/): what the pipeline does, stage by stage, and what it refuses to claim.
- [Choosing your route](https://flow-next.dev/choosing-your-route/): which stages a bug, a feature, a refactor, or a performance request takes, and why the direct route is the default.
- [Going autonomous](https://flow-next.dev/autonomy/going-autonomous/): `flow --auto`, `--until=merge`, the strikes ledger, and the stop conditions.
- [For teams](https://flow-next.dev/guides/for-teams/): the spec as the handover object between product, engineering, and the agent, plus the tracker bridge to Linear, GitHub, GitLab, and Jira.
- [Model routing](https://flow-next.dev/guides/model-routing/): four tiers, the routing block in your instruction file, and what each harness can reach.
- [Review backends](https://flow-next.dev/reference/review-backends/): RepoPrompt, Codex, Copilot, Cursor, Claude, and host review, with the cross-family rule.
- [Configuration](https://flow-next.dev/flowctl/configuration/): every `.flow/config.json` key, generated from the schema.
- [Skills](https://flow-next.dev/skills/): all 31 skills and their invocation forms, and the [CLI reference](https://flow-next.dev/flowctl/cli-reference/) for `flowctl`.
- [Changelog](https://flow-next.dev/releases/changelog/): release highlights; [`CHANGELOG.md`](CHANGELOG.md) in this repository is the full record.
- [Discord](https://discord.gg/f3DYq8AAm5) for questions, and [`CONTRIBUTING.md`](CONTRIBUTING.md) for local development and the docs-only rule.

## Where it already runs

Flow-Next's ways of working are coached and run in enterprise engineering organisations worldwide, from CAD and construction software to proptech and education, across modern monorepos, hundred-repo microservice estates, and 30-year-old legacy stacks, on GitHub Enterprise, GitLab, and Jira. A 2-3 hour structured discovery interview reliably produces 8-11 implementation-ready specs with numbered acceptance criteria, boundaries, and task breakdowns; the edge cases surface in the interview instead of the sprint. Receipts, evidence JSON, and review gates are the audit trail enterprise adoption asks for: approval checkpoints and traceability are built in.

The open-source record is linkable, so it speaks in its own words: an outside contributor shipping a correct `flowctl` patch in [PR #95](https://github.com/gmickel/flow-next/pull/95), a feature in [awesome-claude-code-workflows](https://github.com/ithiria894/awesome-claude-code-workflows) for plan-first workflows, Ralph autonomous mode, and receipt-based gating ([#96](https://github.com/gmickel/flow-next/issues/96)), and a [3-OS test matrix](https://github.com/gmickel/flow-next/actions) on every push, because the field runs all three.

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
