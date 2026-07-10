> **Status: DEFERRED (2026-07-10).** Kept on the backlog, not actively planned. pilot+land cover the default autonomy path; Ralph v2 (hardened bespoke-per-stage harness) is a future hardening track, revisited when there is demand for fully-planned-spec autonomous runs beyond what pilot/land already give. Linear issue moved to Backlog.

## Conversation Evidence

> user: "it would also be simple to create a ralph mode that builds on pilot/land, put a stub spec for that in our specs maybe if you agree"
> context: 1.14.0 repositioning — pilot+land are the default autonomy path; Ralph is the hardened harness (fully planned specs only, never plans, bespoke per-stage shell logic predating the loops).

## Goal & Context
<!-- Source: 70% [user] / 30% [paraphrase] -->

STUB — not ready; refine via /flow-next:interview before blessing.

Rebuild the Ralph harness on top of the pilot/land tick contracts instead of its bespoke per-stage logic. `ralph.sh` v2 becomes a thin shell loop that spawns a **fresh agent session per iteration**, each session running exactly one `/flow-next:pilot` tick (or `/flow-next:land` tick for the ship segment), with the loop reading the terminal `PILOT_VERDICT=` / `LAND_VERDICT=` line from the session output to decide continue / block / stop. Keeps Ralph's three structural advantages — fresh-session isolation, hook-enforced guardrails (ralph-guard / DCG), receipts on disk — while deleting the duplicated stage-selection/review-loop machinery that pilot now owns. Ralph v2 would also gain what v1 never had: planning (pilot's plan stage) and shipping (land), making the hardened harness cover the full lifecycle.

## Boundaries

- The verdict grammars are the integration contract — Ralph v2 parses terminal lines, never transcript internals. [paraphrase]
- ralph-guard / DCG hooks stay; how they interact with `mode:autonomous` sub-skill dispatch (today explicitly NOT ralph paths) is the core design question — likely a third signal or a guard-profile that wraps autonomous ticks. [inferred]
- Migration story for existing scripts/ralph/ users required; v1 deprecation only after v2 proves out. [inferred]

## Open Questions

- Does FLOW_RALPH remain the session marker when the session runs pilot (which hard-errors under FLOW_RALPH today)? Probably needs a new marker (e.g. FLOW_HARNESS) + pilot/land guard updates.
- Receipts: do verdict lines become receipts on disk (harness writes them), or do the fn-57 sync receipts suffice?
- Per-iteration session spawn cost vs pilot's in-session worker model — measure before committing.

## Acceptance Criteria

- **R1:** STUB — to be defined at interview/planning. Ralph v2 drives pilot/land ticks from a fresh-session shell loop, preserving guard hooks + receipts, replacing bespoke stage logic. [user]
