# Self-improving through normal work

> **Codex install note:** when YOU run a flow-next command on THIS Codex install, invoke it as `$flow-next-<name>` (or pick it from the skills dropdown) wherever this page writes `/flow-next:<name>` — and when the written name itself already starts with `flow-next-` (e.g. `/flow-next:flow-next-drive`), the prefix is not doubled: invoke `$flow-next-drive`. Passages describing OTHER hosts (Claude Code `claude -p` / `/loop` examples, Grok, Cursor, OpenCode sections) document those hosts' own syntax and are quoted verbatim — do not convert them.


flow-next gets better as you use it. Memory, glossary, decision records, strategy, and the feature map compound as side-effects of the workflow you already run. **There is no manual "compound" / "refresh" / "reindex" ceremony, by design**: improvement that depends on remembering an extra command doesn't happen.

> Subsystem details live in the peer docs - [`memory-schema.md`](memory-schema.md), [`glossary.md`](glossary.md), [`strategy.md`](strategy.md), [`../skills/flow-next-features/SKILL.md`](../../skills/flow-next-features/SKILL.md). This page is the loop map: where each surface is seeded, grown, read, and pruned.

## The compounding loops

| Surface | Seeded by | Grows through | Read by | Pruned by |
|---------|-----------|---------------|---------|-----------|
| **Memory** (`.flow/memory/`) | `flowctl memory init` (opt-in) | Worker auto-capture on NEEDS_WORK → SHIP; Ralph writes the same entries autonomously | `memory-scout` during planning; worker re-anchor before each task | `/flow-next:audit` - Keep / Update / Consolidate / Replace / Delete / Harden per entry |
| **Glossary** (`GLOSSARY.md`) | `/flow-next:prime` - repo scan, read-back gated | `/flow-next:interview` + `/flow-next:capture` term adds when new vocabulary surfaces | Plan scouts, worker re-anchor, review prompts (task-relevant terms only) | `/flow-next:audit` Phase 0.5 - staleness + alias creep |
| **Decision records** (`.flow/memory/knowledge/decisions/`) | - (accrete from work) | `/flow-next:capture --override-strategy` prompts a record; interview + review cycles capture load-bearing choices | `memory-scout` during planning | `/flow-next:audit` - supersede-not-delete (historical trail preserved) |
| **Strategy** (`STRATEGY.md`) | `/flow-next:strategy` | Drift surfaced read-only by plan / capture / sync - updates stay human-confirmed | `/flow-next:prospect`, plan (`## Strategy Alignment`), interview, capture | `/flow-next:strategy` (the only writer) |
| **Feature map** (`.flow/features/`) | `/flow-next:features` (seed when the directory is absent) | Maintain pass: source readers + one live drive of every feature | `/flow-next:qa` and `flow-next-drive` (navigation, preconditions, gotchas) | `/flow-next:features` maintain - `clean` / `changed` / `blocked` |

## Memory

Opt-in categorized store (bug / knowledge tracks) that survives context compaction. The write moment is the review loop: when an implementation review goes NEEDS_WORK → SHIP, the worker captures the problem / root cause / fix / prevention as a bug-track entry - in Ralph mode this happens with nobody watching. `memory add` always creates unless the caller passes explicit `--update <id>`; the response emits scored `matches` so the calling skill decides update-vs-create (fn-113). Reads happen where they pay: `memory-scout` feeds planning, the worker re-anchor pulls module-relevant entries before touching code. `/flow-next:audit` is the garbage collector - it walks entries against the current codebase and keeps, updates, consolidates, replaces, deletes, or **hardens**. Harden closes the loop from memory to enforced gate: a lesson that is correct, recurring, and mechanizable stops riding the context window and becomes a lint rule, a CI step, or an instruction-file rule, verified live before the entry is demoted to a pointer at it. Schema + lifecycle: [`memory-schema.md`](memory-schema.md).

## Glossary

Wrong-meaning-of-a-normal-word errors get built into plans and code. The glossary loop closes that: `/flow-next:prime` seeds `GLOSSARY.md` from the repo's load-bearing nouns (evidence-backed, read-back before write - never unseen); `/flow-next:interview` and `/flow-next:capture` add terms as new vocabulary surfaces in conversation; plan scouts, the work worker's re-anchor, and review prompts read task-relevant terms (budget-capped - never the whole file); `/flow-next:audit` prunes stale terms and alias creep as part of its normal sweep. File shape + `flowctl glossary` subcommands: [`glossary.md`](glossary.md).

## Decision records

Load-bearing architectural choices land in `knowledge/decisions/` at the moment they're made - e.g. `/flow-next:capture` proposing a decision record when a spec overrides an active strategy track. Audit treats decisions specially: Replace is supersede-not-delete (`decision_status: superseded` + `superseded_by`), so the trail of why stays intact. Schema: [`memory-schema.md`](memory-schema.md).

## Strategy

`STRATEGY.md` is read by the skills that need direction (prospect's candidate filter, plan's `## Strategy Alignment` section, interview/capture conflict surfacing) - and the same reads keep it honest: drift between the doc and what's actually being built is flagged read-only, never auto-superseded. The human stays the editor via `/flow-next:strategy`. File shape + consumers: [`strategy.md`](strategy.md).

## Feature map

A committed user-POV drive directory (`.flow/features/`, beside `.flow/memory/`) that records how a user reaches each user-facing feature, how an agent drives it, and which traps waste a verification run. QA and drive stop re-deriving navigation; the spec still supplies this run's ACs/R-IDs, and live captured evidence remains the only SHIP basis.

**Seeded once** by `/flow-next:features` when `.flow/features/` is absent (or with explicit init intent): interview the repo, prove each route with one live drive, write the index plus one four-H2 file per proven feature. Nothing undriven lands.

**Grows through** the audit-shaped maintain pass on the same command when the map is present: index hygiene, one read-only source reader per feature (concurrent; readers never drive, never edit), reconcile (merge recipes into as few app states as practical, spot-check cited drift, sweep recent churn for unmapped user-facing surfaces - a concrete source path is required before calling one missing), one live pass covering every feature even when source looks clean, then triage. Wrong user-POV description is doc drift: fix the map. Working behavior the harness cannot drive is a harness gap: fix it and re-drive before shipping. Broken app behavior is a product bug: report it, keep it out of the PR. Edit scope is the map directory and harness scripts it owns - never product code.

**Read by** `/flow-next:qa` and `flow-next-drive` when the directory exists (existence check only; no config key). Absent map: both behave as they do today. A QA run that finds a stale route files it as a `feature-map-drift` memory tag for the next maintain pass; it never edits the map mid-run.

**Pruned by** that same maintain pass. Outcomes are `clean` (no branch, no PR), `changed` (one PR of proven map/harness corrections only), or `blocked` (names what blocked). Cadence belongs to the human or their host loop - never a pilot stage, land tail, or Ralph iteration.

This is a user-POV drive map. The code-POV `/flow-next:map` index is a different layer; both stay. Skill: [`../skills/flow-next-features/SKILL.md`](../../skills/flow-next-features/SKILL.md).

## The no-ceremony principle

Each loop's write moment is embedded in a step that already happens - prime runs at onboarding (and its cheap `--classify-only` sweep is re-runnable any time for portfolio triage), interviews and captures happen when specs are born, reviews happen before merge, audits run when memory is consulted and found wanting. The feature map is the deliberate exception: its consumption is ambient (QA and drive read it, and QA files drift signals, during work that already happens), but its maintain pass is human-cadenced - the operator or their host loop invokes `/flow-next:features`, never a pipeline stage. The drift memos QA leaves mean a forgotten cadence degrades loudly (the next maintain pass finds a queue), not silently. Contrast with workflows that require a manual "compound" / "refresh" pass: those degrade silently the day the operator forgets. flow-next's surfaces degrade toward *pruning* (audit, and the feature-map maintain pass, remove what's stale) rather than toward *staleness* (nothing added since the last ceremony).

## See also

- [`memory-schema.md`](memory-schema.md) - categorized memory tree, frontmatter schemas, audit lifecycle.
- [`glossary.md`](glossary.md) - `GLOSSARY.md` shape, resolution walk, subcommands.
- [`strategy.md`](strategy.md) - `STRATEGY.md` shape, Rumelt sections, downstream consumers.
- [`../skills/flow-next-features/SKILL.md`](../../skills/flow-next-features/SKILL.md) - seed/maintain the committed user-POV drive map.
- [`../../../STRATEGY.md`](https://github.com/gmickel/flow-next/blob/main/STRATEGY.md) - this repo's own strategy, including the "Self-improving through normal work" track.
