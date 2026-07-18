# fn-101 flowctl determinism audit: what still earns deterministic Python

> STUB (2026-07-18, maintainer-requested during the fn-89 rewrite discussion). Not planned, not ready. Interview/plan before building.

## Goal & Context

flowctl.py is ~33k lines of deterministic Python serving a system whose doctrine says "the host agent IS the intelligence; reach for deterministic Python only when there's a real reason" (CLAUDE.md, Architecture). The doctrine has been applied piecemeal - fn-83 killed a deterministic plan-sync skip-gate for judging a judgment question; fn-90 moved a review cap INTO flowctl because prose failed; the fn-89 rewrite just cut a config leaf and a ledger schema as over-determinism. Nobody has swept the whole flowctl surface against the doctrine in one pass.

Audit EVERY flowctl subcommand/surface and classify it:

- **KEEP-DETERMINISTIC** (the real reasons): atomicity/locking (atomic_write, state-store locks), receipts + event-tag audit, schema/enum validation, id allocation + alias resolution, Ralph hook matchers, counters/caps that must survive fresh invocations (review-rounds), git plumbing, anything that must run with no agent in the loop.
- **JUDGMENT-LEAKAGE candidates** (the doctrine's "spot a mistake" list): scoring/classification heuristics, text-munging that approximates reading, stoplists/regexes standing in for comprehension, "fallback engines" for when the LLM could just decide, deterministic proxies for semantic questions.
- **DEAD/VESTIGIAL**: surfaces no skill invokes anymore (grep the fleet for callers; cross-check docs/flowctl.md against reality).

Deliverables: a classification table (subcommand -> class -> caller(s) -> verdict), removal/simplification candidates each with a one-line risk note, and follow-up spec stubs for anything worth acting on. NO code changes in this spec - it is an audit.

## Boundaries / non-goals (draft)

- Audit only; every change ships as its own follow-up spec.
- The keep-deterministic classes above are presumed sound - the burden of proof is on moving something OUT of flowctl, not on keeping it.
- fn-83's do-not-re-attempt decision record binds (no re-litigating the plan-sync skip-gate).

## Open Questions

- Sweep method: one auditor per subcommand family with the doctrine as rubric (the fn-87 fleet-audit shape), or a single deep pass? Cost/quality tradeoff to decide at interview.
- Should docs/flowctl.md drift (documented-vs-real surface) be folded in here or split out?
- Does the audit also cover the ~80 tests for vestigial surfaces (test debt rides along)?
