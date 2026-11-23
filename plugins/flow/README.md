# Flow-Next (preview)

`flow` is the Flow-Next preview plugin beside Flow-Next Classic (`flow-next`). It ships one self-contained skill folder (`skills/flow/`) with playbooks for specs, review, PRs, landing, priming, setup, and porting, plus `skills/flow/scripts/edge` for tracker and forge calls.

## Install from a local checkout

- **Claude Code:** `claude --plugin-dir ./plugins/flow` for a session (local marketplace `flow-dev` not yet run).
- **Factory Droid:** local marketplace `flow-dev` (`./plugins/flow`) and `flow@flow-dev` (not yet tried).
- **Grok Build:** `grok plugin install ./plugins/flow --trust`.
- **Codex:** copy `./plugins/flow/skills/flow` into Codex's `skills/` directory (local marketplace `flow-dev` not yet run).
- **Cursor:** `--plugin-dir ./plugins/flow` for a session, or copy `./plugins/flow` (excluding `tests/`) to `~/.cursor/plugins/local/flow` and restart.
- **Muse Code:** `muse plugins install ./plugins/flow --scope user`, or `./plugins/flow/install/install.sh muse`.
- **OpenCode, Antigravity CLI:** `./plugins/flow/install/install.sh <opencode|antigravity>` (copies `skills/flow`, plus `plugin.json` for Antigravity; other directories stay untouched).

## Recommended repo line

Flow works without repository setup, and adding one line to `CLAUDE.md` or `AGENTS.md` makes it reliable, especially for small jobs and on weaker models:

`Use the Flow skill for development work in this repository.`

The `prime` playbook offers to add it. It is one stable sentence and never needs changing.

Separately and optionally, write model and effort preferences in the same file in plain words—for example, "Review with another vendor's model at medium effort" or "Build with a faster model; review on another model family; budget: medium" (`large`, `medium`, or `small`). With nothing stated, review goes to a model from a different family in a fixed order of named defaults listed in the `orchestrate` playbook, and one line in the instruction file overrides it. The plugin reads them and never writes them.

## If Flow is not being picked up

- Add the sentence above to `CLAUDE.md` or `AGENTS.md`.
- Name it in the request ("flow, fix the login bug").
- Check which model the harness picked; an old or small default model is the usual cause.
- On Muse, trust the workspace, or it does not read the repo's instruction file.

## Command spelling

Plain words work on every host. Where a host loads stage aliases:

| Host | Spelling |
|---|---|
| Claude Code, Factory Droid, Grok Build | `/flow:go`, `/flow:spec`, `/flow:review`, `/flow:pr`, `/flow:feedback`, `/flow:land`, `/flow:prime`, `/flow:doctor` |
| Cursor | `/flow-go`, `/flow-land`, … (`/flow:` also accepted) |
| Codex | `$flow` or plain words |
| OpenCode, Muse Code, Antigravity CLI | Plain words via `flow` |

## Exercised hosts

On Claude Code, Codex, Cursor, OpenCode, Grok, Muse, and Antigravity, the skill loaded from an isolated install and opened its playbooks on a small test repo. No real install has been made, no work has been taken end to end on any host, and Factory Droid has not been tried.
