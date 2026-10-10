# work routes and records an explicitly named implementer

## Goal & Context

A person or a calling program that names the implementer's model on a flow or work invocation ("use claude-sonnet-5-5 for the implementation") should get that model for the worker as a guarantee, and be able to see afterwards which model did the work. [paraphrase]

Plain words already reach work: in MergeFoundry's pass 8 (agent-evals `studies/lead-placement-2026-10`, 2026-10-10; plain Claude Code, Opus 5.5 at medium, flow-next 8.5.0, `/flow-next:flow --auto fn-1 use claude-sonnet-5-5 for the implementation`, three draws), flow wrote the request into its call to work every time and the worker ran on Sonnet in 3 of 3. No forwarding flags are needed. [paraphrase]

The guarantee is missing. work's tier step (`flowctl judge --preset tier`) never turns an explicit implementer into the spawn model: with `--explicit-model claude-sonnet-5-5 --can-spawn-model` it returns `spawn_model: null` and `Tier: session (jev moderate 0.83) (explicit IMPLEMENTER preserved)`, and without a Jev key `Tier: session (jev-unavailable(no_key))`, which does not mention the model at all (reproduced 2026-10-10). The three Sonnet spawns came from the agent adding the model on its own. The record is also wrong: two of three done summaries said `Tier: session` while Sonnet did the work, and no draw recorded the model that actually ran. [paraphrase]

<!-- Source: 0% user / 85% [paraphrase] / 15% [inferred] -->

## Architecture & Data Models

- **The tier step owns the spawn decision for a worker.** An explicit invocation model is the highest rung, above the Jev tier and the routing block's fast model, as the routing precedence already states. [paraphrase]
- **Reach decides the channel, not whether the choice holds.** Native spawn reach puts the model on the worker spawn; bridge-only reach leaves the native spawn alone and hands the model to the worker's bridged-implementer path; neither falls back to the session model under the existing unreachable-preference rule. [inferred]
- **The actual model is evidence, never a copy of the request.** It comes from host execution metadata or the bridge command that ran, as the tier step's instructions already require. [paraphrase]

## Acceptance Criteria

- **R15:** Given an explicit implementer and native spawn reach, the tier step returns that model as the spawn model, and the tier line names it as the explicit implementer, with or without a Jev key. With bridge-only reach it returns no spawn model, keeps the implementer for the worker's bridge path, and the tier line says the model is reached over the bridge. Errors: with neither reach, the tier line names the explicit model and says it was unreachable, and the worker runs on the session model as today. [paraphrase]
- **R16:** After the worker returns, the task's done evidence records the model that actually ran whenever the host or the bridge reports it, next to the requested one, so a run that used a different model than requested is visible. When the host reports no model, the done evidence says the actual model was not reported, and never copies the requested model in its place. No error surface beyond that. [paraphrase]
- **R17:** A run that names no implementer gets the same tier step result and tier line as today. No error surface. [inferred]

R1 to R14 belonged to the earlier draft of this spec (flags and a routing line for flow to forward per-tier routing). They were dropped on 2026-10-10 after pass 8 showed plain words already reach work; the numbers are not reused. [paraphrase]

## Boundaries

- No new flow arguments, no routing line and no forwarding step; flow already carries a plain-words implementer request to work. [paraphrase]
- The review backend and reviewer model are out of scope; `--review=` and the review receipt's model field are unchanged. [inferred]
- Flow never chooses a model by itself; automatic selection stays deferred in fn-240. [inferred]

## Decision Context

MergeFoundry asked on 2026-10-10 for flow to forward per-tier model routing to the stages it runs, and the earlier draft of this spec added exact flags, a fixed-format routing line and a refusal verdict for it. Gordon held that against flow-next's agent-first, low-machinery approach and asked for evidence first. Pass 8 showed the words already arrive; what fails is the tier step's routing guarantee and the record of what ran. MergeFoundry agreed to drop the flags and the routing line: it reads each subagent's model from the provider stream itself (`claude -p` stream-json events carry it), so it needs only the two things this spec keeps. Gordon approved the shrink the same day. [paraphrase]

## Strategy Alignment

- "Agent first": the person or program says it in words, the agent passes it on, and the deterministic step that turns it into a spawn parameter does what it already claims to do. No form, flag or label is added. [inferred]

## Strategy Conflicts

None found.

## Parked unknowns

- What Claude Code's subagent result exposes about the model that ran; R16's "not reported" path covers a host that exposes nothing. Resolved by reading a worker result during the build. [inferred]
- Reviewer and scout tiers, Codex hosts and low effort were not tested in pass 8; whether plain words reach them is unmeasured, and nothing here changes them. [paraphrase]
