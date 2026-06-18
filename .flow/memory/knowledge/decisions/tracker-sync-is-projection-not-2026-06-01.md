---
title: "Tracker sync is projection, not coordination (Linear-first)"
date: "2026-06-01"
track: knowledge
category: decisions
module: strategy
tags: [strategy-override, tracker-sync, linear]
applies_when: "Tracker sync is projection, not coordination (Linear-first)"
---

## Problem
Spec fn-52 (tracker sync bridge) is in tension with STRATEGY.md, which positions flow-next AGAINST Jira/Linear's human cadence ("the spec has to carry the full weight upstream"). Syncing specs to Linear superficially reintroduces the tracker coupling the product exists to escape.

## What was chosen
Build the tracker sync bridge as PROJECTION / visibility, not coordination. The `.flow/specs/<id>.md` spec stays the single source of truth and the quality layer; the tracker (Linear first, GitHub next) is a co-editable mirror for teams that must live in it. "Not coordination" means the tracker never drives flow state or spawns agents (Symphony's control-plane model) — it does NOT mean one-way: body, status, and comments all sync two-way. flow-next stays where specs are authored/enriched and the agent loop is executed.

## Why
- The real, lived demand is Linear-native teams (the workunits/Sapient team; the OpenAI-Symphony/Linear ecosystem). A projection bridge is an adoption on-ramp: "keep your tracker for stakeholder visibility; flow-next drives the spec."
- Framed as projection, the bridge COMPLEMENTS the strategy thesis (spec carries the weight upstream) instead of contradicting it — the tracker is a downstream mirror, not a competing source of truth.
- Contrasts cleanly with OpenAI Symphony (Linear = canonical finite-state-machine that spawns agents; thin per-issue WORKFLOW.md). flow-next's pitch becomes "Symphony, but with real specs + re-anchoring + receipts."

## Considered alternatives
- Tracker as control plane (Linear drives flow state / spawns agents, Symphony-style) — rejected: rebuilds the Jira/Linear coupling flow-next set out to replace, and breaks the spec-as-source-of-truth invariant. (Note: this is distinct from two-way body sync, which is fine — the tracker mirrors the spec text without driving the agent loop.)
- One-way body sync (body flows a single direction to dodge merge) — rejected: traps flow-side enrichment (capture/interview/plan) and starves the tracker-first flow where a vague PM issue is pulled in, fleshed out, and must sync back. The agent harness can do a semantic 3-way merge, so one-way is unnecessary.
- Not syncing at all — rejected: leaves Linear-native teams (real demand) unserved; manual sync (workunits today) has no reconciliation and loses data on concurrent edits.

## Consequences
- Body, status, and comments all sync two-way. Body reconciliation is agentic (host-agent semantic 3-way merge against a `lastSyncedAt` merge-base snapshot, translating between flow's structured spec and the tracker's free-form issue); only genuine contradictions surface for a human, and in Ralph mode they queue while confident merges proceed.
- Linear-first ordering accepts the headless/Codex/cron MCP-availability caveat as a documented constraint (GitHub-via-gh is the headless-robust path, shipped second).
- A future /flow-next:strategy run should fold this into an explicit track; this decision feeds that conversation.
- **fn-66 (FLOW-15) refines the status projection, not the projection-vs-coordination stance.** Two of the two-way status states are now evidence-gated: `In Review` is **actively projected** at make-pr (an open PR is the In Review lifecycle rung, projected unconditionally whenever the bridge is active), and terminal `Done` is **gated on a GitHub-confirmed `MERGED` probe** for the spec branch — local Flow completion (`done` + completion-review `ship`) is necessary, never sufficient, and `land.merged` is the sole Done driver (active-by-default when the bridge is active). This keeps the tracker an honest mirror of reality ("In Review" / "shipped") without making it a control plane: flow still drives state, the merge probe is read-only evidence, and a human's manual board edit still wins per the who-wins tiebreak. Projection-not-coordination is unchanged; the projection is just more lifecycle-accurate.

## Future extension (NOT in fn-52): board-triggered per-spec executor
A Symphony-shaped trigger layer can sit on top of the fn-52 sync bridge — but it is a SEPARATE strategy decision (it makes the tracker a trigger, revisiting projection-not-coordination).
- Trigger is PER-SPEC, not Ralph. Ralph = open multi-spec backlog loop (operator-started). This is event-driven: a board status flip (`→ Ready`) fires a bounded run on the ONE linked spec, then exits — Symphony's one-issue→one-runner→PR shape with flow-next's richer lifecycle.
- Reuses Ralph's per-spec machinery (plan/work/review/make-pr stage runners, receipts, gates, re-anchoring) minus the multi-spec loop, plus a webhook trigger + status-flip. Not a new engine.
- Conditional/idempotent pipeline: no tasks → plan; planned, no impl → work; implemented → impl-review + spec-completion-review; passing → make-pr (STOP — human reviews the PR, never auto-merge); qa later (needs fn-51 flow-next-drive + qa skill).
- Each transition flips board status via the sync bridge (R7): Ready → Planning → In Progress → In Review → PR Open → (QA) → Done.
- Config-driven: which status means "go" + status→stage map (Linear workflow states differ per team; rides on fn-52 R1/R7).
- Implementation can be light: Linear webhooks (not a polling daemon) → a tiny handler (any language / serverless / GitHub Action) → invoke flowctl/skills on the linked spec. Elixir/Rust/Go only if Symphony-scale concurrency is wanted.
