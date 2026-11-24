# Flow-Next (preview)

`flow` is the Flow-Next preview plugin beside Flow-Next Classic (`flow-next`). It ships one self-contained skill folder (`skills/flow/`) with playbooks for specs, review, PRs, landing, priming, setup, and porting, plus `skills/flow/scripts/edge` for tracker and forge calls.

## Recommended repo line

Flow works without repository setup, and adding one line to `CLAUDE.md` or `AGENTS.md` makes it reliable, especially for small jobs and on weaker models:

`Use the Flow skill for development work in this repository.`

The `prime` playbook offers to add it. It is one stable sentence and never needs changing.

Separately and optionally, write model and effort preferences in the same file in plain words—for example, "Review with another vendor's model at medium effort" or "Build with a faster model; review on another model family; budget: medium" (`large`, `medium`, or `small`). With nothing stated, review goes to a model from a different family in a fixed order of named defaults listed in the `orchestrate` playbook, and one line in the instruction file overrides it. The plugin reads them and never writes them.

## If you also use Flow-Next Classic

Use one of the two per repository. With both active in the same repository, requests are split between them unpredictably.

- **Claude Code:** enable this plugin per repository, not for your whole user account, and switch Classic off there. In the repository's `.claude/settings.local.json`: `{"enabledPlugins": {"flow@flow-next": true, "flow-next@flow-next": false}}`.
- **Other hosts** have no per-repository switch: install one or the other.
- Add the repo line above. In a repository that carries it, development requests go to this plugin.

## Install

- **Claude Code:** `/plugin marketplace add gmickel/flow-next`, then `/plugin install flow@flow-next`. To enable it for one repository only, run `claude plugin install flow@flow-next --scope local` in that repository.
- **Codex:** `codex plugin marketplace add gmickel/flow-next`, then `codex plugin add flow@flow-next-marketplace`.

From a checkout of this repository:

- **Grok Build:** `grok plugin install ./plugins/flow --trust`.
- **Muse Code:** `muse plugins install ./plugins/flow --scope user`, or `./plugins/flow/install/install.sh muse`.
- **Cursor:** copy `./plugins/flow` to `~/.cursor/plugins/local/flow` and restart, or `--plugin-dir ./plugins/flow` for one session.
- **OpenCode, Antigravity CLI:** `./plugins/flow/install/install.sh <opencode|antigravity>`.
- **Factory Droid:** add this repository as a marketplace and install `flow@flow-next` (not yet tried).

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

## Host notes

- **Codex:** a non-interactive run needs a mode where git writes and the network are allowed. In the workspace-write sandbox it cannot create a branch; an interactive session asks for approval instead.
- **Trackers:** Flow moves a linked issue to in progress, in review and done. If your tracker has more than one "started" state, say which one means in review when you link it.

## Exercised hosts

On Claude Code, Codex, Cursor, OpenCode, Grok, Muse and Antigravity the plugin has taken a real change through a fix, a test and a review by another model. Claude Code has had the most use, including tracker-linked and unattended runs through merge. Factory Droid and Windows have not been tried.
