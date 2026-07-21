# Self-improving through normal work

flow-next gets better as you use it. Four surfaces — memory, glossary, decision records, strategy — compound as side-effects of the workflow you already run. **There is no manual "compound" / "refresh" / "reindex" ceremony, by design**: improvement that depends on remembering an extra command doesn't happen.

> Subsystem details live in the peer docs — [`memory-schema.md`](memory-schema.md), [`glossary.md`](glossary.md), [`strategy.md`](strategy.md). This page is the loop map: where each surface is seeded, grown, read, and pruned.

## The four loops

| Surface | Seeded by | Grows through | Read by | Pruned by |
|---------|-----------|---------------|---------|-----------|
| **Memory** (`.flow/memory/`) | `flowctl memory init` (opt-in) | Worker auto-capture on NEEDS_WORK → SHIP; Ralph writes the same entries autonomously | `memory-scout` during planning; worker re-anchor before each task | `/flow-next:audit` — Keep / Update / Consolidate / Replace / Delete per entry |
| **Glossary** (`GLOSSARY.md`) | `/flow-next:prime` — repo scan, read-back gated | `/flow-next:interview` + `/flow-next:capture` term adds when new vocabulary surfaces | Plan scouts, worker re-anchor, review prompts (task-relevant terms only) | `/flow-next:audit` Phase 0.5 — staleness + alias creep |
| **Decision records** (`.flow/memory/knowledge/decisions/`) | — (accrete from work) | `/flow-next:capture --override-strategy` prompts a record; interview + review cycles capture load-bearing choices | `memory-scout` during planning | `/flow-next:audit` — supersede-not-delete (historical trail preserved) |
| **Strategy** (`STRATEGY.md`) | `/flow-next:strategy` | Drift surfaced read-only by plan / capture / sync — updates stay human-confirmed | `/flow-next:prospect`, plan (`## Strategy Alignment`), interview, capture | `/flow-next:strategy` (the only writer) |

## Memory

Opt-in categorized store (bug / knowledge tracks) that survives context compaction. The write moment is the review loop: when an implementation review goes NEEDS_WORK → SHIP, the worker captures the problem / root cause / fix / prevention as a bug-track entry — in Ralph mode this happens with nobody watching. `memory add` always creates unless the caller passes explicit `--update <id>`; the response emits scored `matches` so the calling skill decides update-vs-create (fn-113). Reads happen where they pay: `memory-scout` feeds planning, the worker re-anchor pulls module-relevant entries before touching code. `/flow-next:audit` is the garbage collector — it walks entries against the current codebase and keeps, updates, consolidates, replaces, or deletes. Schema + lifecycle: [`memory-schema.md`](memory-schema.md).

## Glossary

Wrong-meaning-of-a-normal-word errors get built into plans and code. The glossary loop closes that: `/flow-next:prime` seeds `GLOSSARY.md` from the repo's load-bearing nouns (evidence-backed, read-back before write — never unseen); `/flow-next:interview` and `/flow-next:capture` add terms as new vocabulary surfaces in conversation; plan scouts, the work worker's re-anchor, and review prompts read task-relevant terms (budget-capped — never the whole file); `/flow-next:audit` prunes stale terms and alias creep as part of its normal sweep. File shape + `flowctl glossary` subcommands: [`glossary.md`](glossary.md).

## Decision records

Load-bearing architectural choices land in `knowledge/decisions/` at the moment they're made — e.g. `/flow-next:capture` proposing a decision record when a spec overrides an active strategy track. Audit treats decisions specially: Replace is supersede-not-delete (`decision_status: superseded` + `superseded_by`), so the trail of why stays intact. Schema: [`memory-schema.md`](memory-schema.md).

## Strategy

`STRATEGY.md` is read by the skills that need direction (prospect's candidate filter, plan's `## Strategy Alignment` section, interview/capture conflict surfacing) — and the same reads keep it honest: drift between the doc and what's actually being built is flagged read-only, never auto-superseded. The human stays the editor via `/flow-next:strategy`. File shape + consumers: [`strategy.md`](strategy.md).

## The no-ceremony principle

Each loop's write moment is embedded in a step that already happens - prime runs at onboarding (and its cheap `--classify-only` sweep is re-runnable any time for portfolio triage), interviews and captures happen when specs are born, reviews happen before merge, audits run when memory is consulted and found wanting. Contrast with workflows that require a manual "compound" / "refresh" pass: those degrade silently the day the operator forgets. flow-next's surfaces degrade toward *pruning* (audit removes what's stale) rather than toward *staleness* (nothing added since the last ceremony).

## See also

- [`memory-schema.md`](memory-schema.md) — categorized memory tree, frontmatter schemas, audit lifecycle.
- [`glossary.md`](glossary.md) — `GLOSSARY.md` shape, resolution walk, subcommands.
- [`strategy.md`](strategy.md) — `STRATEGY.md` shape, Rumelt sections, downstream consumers.
- [`../../../STRATEGY.md`](../../../STRATEGY.md) — this repo's own strategy, including the "Self-improving through normal work" track.
