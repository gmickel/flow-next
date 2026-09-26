# Reach: OpenAI Codex

How this harness obtains a model for a [tier](../orchestration.md#tiers-what-kind-of-model-a-job-wants). Tier names and the routing precedence are defined in [`../orchestration.md`](../orchestration.md#tiers-what-kind-of-model-a-job-wants); this page is only about reach.

## Mechanisms

| Mechanism | Here |
|---|---|
| In-session model | **Yes** - chosen in the harness; the default executor for every unset tier. |
| In-host subagent | **Yes.** Model and effort steering on `spawn_agent` works on both paths since codex-cli 0.146.0 (fn-98, measured 2026-08-03 from the child thread's rollout `turn_context`, never from the child's self-report). Precedence: a role's declared `model` / `model_reasoning_effort` wins over an explicit spawn parameter; where the role declares no model, the explicit parameter applies; with no `agent_type`, the explicit parameter applies and `reasoning_effort` may be set alone; the explicit `model` parameter accepts a shorter list than a role can pin. Two dispatch gotchas: `agent_type` takes the role's `name` (hyphenated), not the `[agents.<key>]` table key; `agent_type` requires `fork_turns: "none"`. A role's `sandbox_mode` is not enforced - a child inherits its parent's sandbox in both directions, so read-only is prompt-only here and containment comes from the parent launch flag (`codex -s read-only`). There is no in-band receipt of the effective model; pin, record what ran, and re-probe out of band. |
| Shell out to another CLI | **Yes.** A fresh non-interactive run of a CLI takes its model and effort on the command line, so nothing can strip them. It works with this harness's own CLI (same family, different model) and with another vendor's. One condition: the parent sandbox must allow spawning a process and reaching the network. Watch (2026-09-14) on the child's own fan-out: openai/codex#33267, a `codex exec` parent unable to decode the result of a child that spawned subagents, is still open upstream and reported on codex-cli 0.144 to 0.145 with the gpt-5.6 family; its minimal repro ran clean 3 of 3 on codex-cli 0.153.4 with gpt-6-astra, and 17 exec-originated spawning runs with 23 spawning child threads in September 2026 returned zero decode errors. A bridged child on a current build may fan out; on a build in the reported range, keep the child prompt flat. |

## What is unavailable

An in-band receipt of the model a subagent ran on, and a role-level sandbox narrowing. Nothing else is missing.

## Degradation

When a tier names a model neither path can reach, the work runs on the session model and the fallback is stated once. A preference is never recorded as if it were an observation.

## Models observed (2026-09-05)

This harness serves GPT-6 Astra (`gpt-6-astra`), released 2026-09-05 and strong at planning, coding, and reviewing. That is one observation on one date; ask the CLI for its current list before pinning the identifier in a shell-out.

The `claude` review backend (`review.backend claude`, observed 2026-09-05) is the packaged Claude-family verdict from this harness: it shells out to `claude -p` (read-only, prompt on stdin) and steps the ranking `claude-fable-5-1` → `claude-opus-5` → `claude-sonnet-5` → `claude-haiku-4-5` (ids probed 2026-09-05 on Claude Code 2.1.260; the CLI lists no models, so the ladder steps that static ranking only), with the same receipt, ladder and fix loop as the `codex` backend - a cross-family review whenever the session model that wrote the diff is another family (this harness's own models are), same-family if a Claude model wrote it.

## Driving unattended

Run `$flow-next-flow --auto` by default. One invocation drives one ready item hop after hop to its draft PR, and the next invocation takes the next item. Under `/goal` (opt-in `[features] goals = true`, CLI >= 0.128.0, no `$skill-in-goal` syntax), write a plain-text objective that runs `flow --auto --tick` once per turn and stops on `PILOT_VERDICT=NO_WORK`. The parent sandbox must allow the stages' subprocesses and network.

## Discover, then invoke

Ask the CLI which models it offers immediately before invoking one, rather than trusting a value stored earlier - that habit is what makes an unreachable identifier a one-line correction instead of a failed run.
