# Flow-Next (preview)

`flow` is the preview plugin for Flow-Next alongside Flow-Next Classic (`flow-next`). It ships one skill (`flow`), playbooks for specs, cross-model review, pull requests, landing, priming, setup checks, and porting Classic repos, plus `scripts/edge` for tracker and forge calls.

## Install from a local checkout

- **Claude Code / Factory Droid:** add `./plugins/flow` as a local marketplace (`flow-dev`) and install `flow@flow-dev` (or pass `--plugin-dir ./plugins/flow`).
- **Grok Build:** auto-discovered from Claude Code, or run `grok --plugin-dir ./plugins/flow`.
- **Codex:** add `./plugins/flow` as a local marketplace (`flow-dev`) and install `flow@flow-dev`.
- **Cursor:** copy `./plugins/flow` (excluding `tests/`) to `~/.cursor/plugins/local/flow` and restart Cursor.
- **OpenCode, Muse Code, Antigravity CLI:** run `./plugins/flow/install/install.sh <opencode|muse|antigravity>`. Muse also accepts `muse plugins install ./plugins/flow --scope user`.

## Command spelling

Plain words work on every host ("flow, land PR 412"). Where a host loads stage aliases:

| Host | Spelling |
|---|---|
| Claude Code, Factory Droid, Grok Build | `/flow:go`, `/flow:spec`, `/flow:review`, `/flow:pr`, `/flow:feedback`, `/flow:land`, `/flow:prime`, `/flow:doctor` |
| Cursor | `/flow-go`, `/flow-land`, … (`/flow:` also accepted when typed) |
| Codex | `$flow` or plain words |
| OpenCode, Muse Code, Antigravity CLI | Plain words via the `flow` skill (stage aliases not loaded by copy / Agent Plugins install) |

## Exercised hosts

No host has been installed or run live yet. Checked so far:

- `claude plugin validate`, `muse plugins validate`, and `agy plugin validate` pass on `plugins/flow`.
- `install/install.sh` tested into temporary directories for OpenCode, Muse, and Antigravity (`../../scripts/edge` resolves and `edge.py --help` runs).
- Tracker and forge unit tests pass (`894` tests).
