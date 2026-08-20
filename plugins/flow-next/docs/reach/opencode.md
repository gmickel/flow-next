# Reach: OpenCode

How this harness obtains a model for a [tier](../orchestration.md#tiers--what-kind-of-model-a-job-wants). Tier names and the routing precedence are defined in [`../orchestration.md`](../orchestration.md#tiers--what-kind-of-model-a-job-wants); this page is only about reach.

flow-next reaches this harness through the in-repo installer (`scripts/install-opencode.sh` — canonical skills plus generated agents/commands scattered into `~/.config/opencode/`).

## Mechanisms

| Mechanism | Here |
|---|---|
| In-session model | **Yes** — chosen in the harness; the default executor for every unset tier. |
| In-host subagent | **Yes** — dispatch via the Task tool and **name the model in the dispatch itself**, same as Cursor. No research, no config edits, no agent-file authoring: dispatch, and let the harness honor or ignore the request. An ignored request degrades to the session model, stated once. |
| Shell out to another CLI | **Yes** — bash is a first-class OpenCode tool; the standard bridge recipes apply. **Never inside a `host` review** — the host backend forbids subprocesses by rule; a CLI verdict belongs to that CLI's backend. |

## What is unavailable

A native blocking-ask primitive (numbered-prompt fallback applies) and generated-agent `model:` frontmatter (dropped at generation — the dispatch names the model instead). Ralph is not supported.

## Degradation

An unhonored model request degrades to the session model, stated once. That is the shipped default, so the whole pipeline runs either way — only the tier split is lost. For host review specifically, a session-model degradation then hits the fail-closed cross-family check: ask (interactive) or `NEEDS_HUMAN` (autonomous), **never a fallback to another CLI**.
