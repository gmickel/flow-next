# Reach: OpenCode

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>` — and when the written name itself already starts with `flow-next-` (e.g. `/flow-next:flow-next-drive`), the prefix is not doubled: invoke `$flow-next-drive`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts' own syntax and are quoted verbatim — do not convert them.


How this harness obtains a model for a [tier](../orchestration.md#tiers-what-kind-of-model-a-job-wants). Tier names and the routing precedence are defined in [`../orchestration.md`](../orchestration.md#tiers-what-kind-of-model-a-job-wants); this page is only about reach.

flow-next reaches this harness through the in-repo installer (`scripts/install-opencode.sh` - canonical skills plus generated agents/commands scattered into `~/.config/opencode/`).

## Mechanisms

| Mechanism | Here |
|---|---|
| In-session model | **Yes** - chosen in the harness; the default executor for every unset tier. |
| In-host subagent on a pinned model | **Yes, via an agent definition** - OpenCode subagents take their model from their own agent file (`model:` frontmatter) or inherit the invoker's; there is **no dispatch-time model parameter** (verified live on 1.18.19, and it matches OpenCode's docs). To reach a tier's model, dispatch a user-defined subagent pinned to it - check the subagent roster for one before degrading. |
| Shell out to another CLI | **Yes** - bash is a first-class OpenCode tool; the standard bridge recipes apply. **Never inside a `host` review** - the host backend forbids subprocesses by rule; a CLI verdict belongs to that CLI's backend. |

## Pinning a tier's model (one user file, config-time)

Write an agent definition once and restart OpenCode (agent files load at startup):

```markdown
# ~/.config/opencode/agents/reviewer.md
---
description: Fresh-context cross-family reviewer pinned to <provider/model>. Dispatch for flow-next host-backend reviews when the routing block's reviewer tier names this model. Read-only by permission.
mode: subagent
model: <provider/model>       # ask `opencode models` for current ids
permission:
  edit: deny
  write: deny
  task: deny
---

Follow the review instructions in the dispatch prompt exactly, including the output format and the verdict tag. Report the model you are running as in your first line.
```

This is OpenCode's native pin surface - the equivalent of writing a routing-block line, not extra machinery. Verified live (1.18.19): with the routing block naming the same model, the conductor matched the roster agent unhinted, the harness honored the pin, and the receipt recorded the real reviewer model.

## What is unavailable

A dispatch-time model override (prose requests in a Task dispatch are ignored - the subagent inherits the session model), a native blocking-ask primitive (numbered-prompt fallback applies), and generated-agent `model:` frontmatter (dropped at generation; the user-defined pin above is the mechanism). Ralph is not supported.

## Degradation

No pinned agent for the tier's model → the subagent inherits the session model, stated once. That is the shipped default, so the whole pipeline runs either way - only the tier split is lost. For host review specifically, a session-model reviewer is the session grading itself: the fail-closed cross-family check fires - ask (interactive) or `NEEDS_HUMAN` (autonomous), **never a fallback to another CLI**. Verified live (1.18.19): the degraded reviewer self-reported the substitution and the conductor asked instead of shipping the verdict silently.

## Models observed (2026-09-05)

The `claude` review backend (`review.backend claude`, observed 2026-09-05) is the CLI route for a Claude-family verdict from here - it shells out to `claude -p` (read-only, prompt on stdin) and steps the ranking `claude-fable-5-1` → `claude-opus-5` → `claude-sonnet-5` → `claude-haiku-4-5` (ids probed 2026-09-05 on Claude Code 2.1.260; the CLI lists no models, so the ladder steps that static ranking only), cross-family when the session model is another family. It is its own backend, never a subprocess inside a `host` review.
