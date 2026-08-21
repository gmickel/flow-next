# Reach: OpenAI Codex

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts's own syntax and are quoted verbatim — do not convert them.


How this harness obtains a model for a [tier](../orchestration.md#tiers--what-kind-of-model-a-job-wants). Tier names and the routing precedence are defined in [`../orchestration.md`](../orchestration.md#tiers--what-kind-of-model-a-job-wants); this page is only about reach.

## Mechanisms

| Mechanism | Here |
|---|---|
| In-session model | **Yes** — chosen in the harness; the default executor for every unset tier. |
| In-host subagent | **Yes, but model selection on the spawn path is not dependable** on current builds: an explicit per-spawn model or effort can be dropped silently, and whether a role profile was applied is not verifiable from inside the run. Treat a subagent's model as best-effort and record what actually ran. |
| Shell out to another CLI | **Yes**, and this is the dependable way to steer a model here — a fresh non-interactive run of a CLI takes its model and effort on the command line, so nothing can strip them. It works with this harness's own CLI (same family, different model) and with another vendor's. Two conditions: the parent sandbox must allow spawning a process and reaching the network, and the child prompt stays flat — a child that fans out subagents of its own can return a result the parent cannot decode. |

## What is unavailable

Dependable per-spawn model steering. Nothing else is missing; the shell-out route covers the same intent.

## Degradation

When a tier cannot be honored on the spawn path, the work runs on the session model (or via a shelled-out run, when one is available) and the fallback is stated once. A preference is never recorded as if it were an observation.

## Discover, then invoke

Ask the CLI which models it offers immediately before invoking one, rather than trusting a value stored earlier — that habit is what makes an unreachable identifier a one-line correction instead of a failed run.
