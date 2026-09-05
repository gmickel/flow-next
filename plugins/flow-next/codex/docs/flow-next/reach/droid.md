# Reach: Factory Droid

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>` — and when the written name itself already starts with `flow-next-` (e.g. `/flow-next:flow-next-drive`), the prefix is not doubled: invoke `$flow-next-drive`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts' own syntax and are quoted verbatim — do not convert them.


How this harness obtains a model for a [tier](../orchestration.md#tiers-what-kind-of-model-a-job-wants). Tier names and the routing precedence are defined in [`../orchestration.md`](../orchestration.md#tiers-what-kind-of-model-a-job-wants); this page is only about reach.

## Mechanisms

| Mechanism | Here |
|---|---|
| In-session model | **Yes** - chosen in the harness; the default executor for every unset tier. |
| In-host subagent | **Yes** - the harness reads flow-next's agent definitions directly. Subagent behavior differs from the canonical host in ways that are not routing (dispatch semantics, timing), so verify a fan-out once rather than assuming parity. |
| Shell out to another CLI | **Yes** - the harness runs shell commands, so any installed, authenticated CLI is reachable. |

## What is unavailable

Nothing structural for routing. The known divergences here are tool and hook naming, which flow-next already absorbs elsewhere and which do not change how a model is reached.

## Degradation

A tier this harness cannot honor runs on the session model and says so once. If a subagent dispatch behaves differently than expected, the work still completes in session - reach degrades, it does not fail.

## Models observed (2026-09-05)

The `claude` review backend (`review.backend claude`, observed 2026-09-05) shells out to `claude -p` (read-only, prompt on stdin) and steps the ranking `claude-fable-5-1` → `claude-opus-5` → `claude-sonnet-5` → `claude-haiku-4-5` (ids probed 2026-09-05 on Claude Code 2.1.260; the CLI lists no models, so the ladder steps that static ranking only). Droid runs the canonical Claude-first plugin, so check the session model's family before treating that verdict as independent: cross-family when the writer is another family, same-family otherwise (the receipt records the model either way).

## Discover, then invoke

Ask the harness and each installed CLI what they currently offer, at the moment of use. A stored answer is the thing that goes stale.
