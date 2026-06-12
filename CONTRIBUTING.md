# Contributing to Flow-Next

Thanks for wanting to make flow-next better. This file is a router, not a manual — the real onboarding lives in `agent_docs/` and stays current because the maintainer's agents use it too.

## Quick orientation

- The repo **is** the flow-next plugin (`plugins/flow-next/`), plus the bundled `flowctl` Python CLI and the Ralph TUI (`flow-next-tui/`).
- Strategic intent: [`STRATEGY.md`](STRATEGY.md). Canonical vocabulary: [`GLOSSARY.md`](GLOSSARY.md). Architecture rules (skill-vs-flowctl split, cross-platform patterns): [`CLAUDE.md`](CLAUDE.md).
- This repo dogfoods itself — work is tracked as specs/tasks under `.flow/` via flow-next. You don't have to use it for a small PR, but reading [the teams guide](plugins/flow-next/docs/teams.md) explains the artefacts you'll see.

## How to contribute

| You want to… | Read |
|---|---|
| Set up local dev, run smoke tests, run the Ralph e2e | [`agent_docs/local-dev.md`](agent_docs/local-dev.md) |
| Add a new `/flow-next:<name>` skill | [`agent_docs/adding-skills.md`](agent_docs/adding-skills.md) — mind the three-edit rule |
| Optimize an existing skill/agent prompt | [`agent_docs/optimizing-skills.md`](agent_docs/optimizing-skills.md) |
| Cut a release (maintainers) | [`agent_docs/releasing.md`](agent_docs/releasing.md) |
| Report a bug / request a feature | [Open an issue](https://github.com/gmickel/flow-next/issues/new/choose) — templates provided |
| Report a security issue | [`SECURITY.md`](SECURITY.md) — private channel, please |

## Ground rules

- **Never hand-edit `plugins/flow-next/codex/**`** — it's a generated mirror. Edit the canonical files under `plugins/flow-next/skills/` / `agents/`, then run `./scripts/sync-codex.sh` and commit the regenerated mirror.
- **Run the gate before pushing:** `bash scripts/ci_test.sh` (vocabulary guard + smoke tests). CI runs the smoke suite on Linux/macOS/Windows — all three must stay green.
- **Version bumps:** pure docs / `agent_docs/` / README changes do **not** bump the plugin version. Changes to skills, agents, hooks, or flowctl do — keep all manifests in lockstep (see [`agent_docs/releasing.md`](agent_docs/releasing.md)).
- **Commits:** [Conventional Commits](https://www.conventionalcommits.org/) (`feat|fix|refactor|docs|chore|test|…`).
- **PR body:** follow [`.github/pull_request_template.md`](.github/pull_request_template.md) — what changed, why, how to test.
- **Big change?** Open an issue first to align on direction — flow-next deliberately holds the line on command count and scope ([`STRATEGY.md`](STRATEGY.md) "Not working on" is real).

## Community

Questions, ideas, show-and-tell: [Discord](https://discord.gg/f3DYq8AAm5) · [@gmickel](https://twitter.com/gmickel).
