# Opus 5 conductor dogfood: post-hoc trace analysis of the fn-122 run

## Context

flow-next 3.4.4 (2026-07-24) routed the default planner/conductor recommendation to Claude Opus 5. Same-day field reports (Compound Engineering; Every's week-long Day-0 review) describe a chaining failure mode: arguing with instructions, stopping before work finishes, degraded behavior with elaborate skills, and better results at medium/low effort. The Opus 5 model card's own FrontierCode figures (8.4.A/B) confirm the effort curve first-party: peak at medium (53.4/63.6), degrading through high/xhigh. The open question is NOT effort (settled: medium) but chaining and handover fidelity against flow-next's existing skill prompts.

To answer it without observer bias, the probe run is deliberately vanilla: a fresh Opus 5 @ medium session drives fn-122-harden-verdict-graduate-recurring through the STANDARD minimal pilot/land loop prompt from main, with no extra watch instructions, no self-reporting, nothing the model can perform for. The ONE steering line the prompt carries is a routing pin, not a behavior instruction: all stages run in-host on the session model (no delegate:codex, no grok/cursor implementation bridges) so the CLAUDE.md routing table does not hand the work stage to terra/grok and dilute the sample; reviews stay on the codex backend (cross-family gate unchanged). This spec is the separate, after-the-fact forensic pass over the traces that run leaves behind.

Deliberately unready until the fn-122 probe run has happened.

## Goal

From raw session traces plus on-disk flow-next artifacts, produce an evidence-backed verdict on whether Opus 5 @ medium conducts the full flow-next chain (plan, plan-review, work with worker dispatch, impl reviews, plan-sync, make-pr, land) with clean handovers, and turn that verdict into the routing-prose decision: annotate opus-5 @ medium as measured, or document the failure mode and keep fable-5/opus-4.8 as the conductor for autonomous chains.

## Method

1. Source the traces: session JSONL files under `~/.claude/projects/-Users-gordon-work-flow-next/` whose mtime falls in the probe window. Gotcha (known): the leading-dash dirname breaks naive `find`/`eza` invocations; use `find <path> -name '*.jsonl' -newermt ...` with the path quoted, then `grep`/`jq` per file. Identify the conductor session (pilot/land invocations) and every spawned subagent session.
2. Reconstruct the tick timeline from the conductor trace: each pilot/land invocation, the stage it entered, the terminal verdict line it printed (or failed to print), and wall-clock per tick.
3. Cross-check narration against deterministic artifacts, which are the ground truth: `.flow/specs/fn-122*.md` + task states and evidence JSON, `flowctl pilot-log` entries, review receipts under `.flow/review-receipts/` (verdicts, rounds, models), `flowctl review-rounds attempts`, git log on the fn-122 branch, the PR and its review threads. Every claim in the traces must reconcile with an artifact; unreconciled claims are findings.
4. Verify the routing pin held: no `codex exec` implementation spawns, no grok/cursor write bridges in the conductor or worker traces; workers ran `model: inherit` on the session model. Review receipts SHOULD show the codex backend. A violated pin does not void the run but re-scopes which model each finding attributes to.
5. Classify deviations against the skill contracts (the SKILL.md files are the spec for what SHOULD have happened): stop-early (stage entered, gate never reached), skipped or shortened workflow steps, dropped or serialized-without-cause dispatches, tasks marked done without evidence, review gates bypassed or verdicts misread, instruction drift (doing something the skill forbids), and reprompts needed from the human. Also record the positives: clean handover objects, honest receipts, correct verdict grammar.
6. Compare against a baseline: the most recent comparable conducted run in the traces (e.g. an fn-111..115-era or fn-95 pilot/land arc on the prior conductor) so findings are relative, not absolute.
7. Verdict + routing decision. Output: a findings table (deviation, evidence pointer, severity), a chaining verdict (clean / degraded / broken), and the concrete routing edit this licenses (scaffold + repo CLAUDE.md + docs-site note if warranted). Feed the outcome into the vault Signals entry and the opus-5-dogfood-watch memory (close or escalate).

## Constraints

- The analyst session must NOT be Opus 5 (uncorrelated observer; Fable or cross-family).
- Traces are read-only inputs; no client or personal content leaves the analysis (traces stay local, findings are generic).
- Root-cause discipline: distinguish "Opus 5 disobeyed the skill" from "the skill was ambiguous" - the second is a skill bug we fix regardless of model.

## Acceptance

- [ ] Every pilot/land tick in the probe window reconstructed with its terminal verdict line, cross-checked against pilot-log and receipts.
- [ ] Deviation findings each cite a trace excerpt AND the artifact (or absence) that corroborates it.
- [ ] Explicit chaining verdict (clean / degraded / broken) with the routing edit it licenses, applied or filed as follow-up.
- [ ] Vault Signals entry + opus-5-dogfood-watch memory updated with the outcome.

## Quick commands

```bash
find ~/.claude/projects/-Users-gordon-work-flow-next -name '*.jsonl' -newermt '<probe-start>' | head
.flow/bin/flowctl pilot-log list --json | jq
.flow/bin/flowctl show fn-122-harden-verdict-graduate-recurring --json
ls .flow/review-receipts/ | tail
```
