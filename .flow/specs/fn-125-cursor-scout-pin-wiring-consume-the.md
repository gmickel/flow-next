## Goal & Context

fn-123 (3.3.0) scaffolds an AGENTS.md model-routing block on Cursor with a **read-only scouts** pin (e.g. `composer-2.5-fast`) alongside the host-review pin. Dogfood (2026-07-22, cursor-dogfood-330, session model Terra): the **host-review pin is consumed** (a plan review + a work review both resolved cross-family to Opus 4.8 per the routing table), but the **scout pin is inert** - `/flow-next:plan` scouts (`repo-scout`, `context-scout`, etc.) all ran on the session model (Terra), not `composer-2.5-fast`.

Root cause: scout agents carry `model:` frontmatter (haiku/sonnet aliases) which Cursor IGNORES (documented degrade, fn-123 R8), and NO skill consumes the AGENTS.md scout pin at dispatch. The plan skill references `model-routing` only for the `host` review backend, never for scout dispatch. So the scaffolded scout-pin row is decorative on alias-ignoring hosts. This is a COST gap, not correctness: scouts on the session model are correct, just pricier than the cheap slug the table promises.

The host-review path is the proven template: it reads the AGENTS.md pin and passes it as the caller-side subagent model (Cursor honors in-prompt/caller-side pins even though it ignores frontmatter). Scout dispatch needs the same treatment.

## Acceptance Criteria

- **R1:** On a host that ignores agent-frontmatter `model:` (Cursor; detect via the same signal as the routing degrade), read-only-scout dispatch reads the AGENTS.md model-routing "read-only scouts" pin and passes it as the spawned subagent's model - so scouts run on the cheap pinned slug, not the session model. [user]
- **R2:** The wiring lives where scouts are dispatched (`/flow-next:plan`, `/flow-next:prime`, and any other scout-dispatching skill) or in a shared reference they all cite; canonical prose stays portable (Claude Code keeps native frontmatter tiering unchanged - this path is only for alias-ignoring hosts). [paraphrase]
- **R3:** When the routing block is absent or the pinned slug is unavailable, dispatch degrades cleanly to the session model (never blocks) - unlike the host-review pin, scout pins are cost-optimization and MAY degrade. [user]
- **R4:** Alternative accepted if simpler: if reliable per-scout caller-side pinning across every scout dispatch is too invasive, DROP the scout-pin row from the setup scaffold instead and document that scout tiering degrades to session-model inherit on alias-ignoring hosts - do not ship a decorative pin that is never honored. Decide in plan/review. [user]
- **R5:** sync-codex twice-idempotent; focused tests cover the consume-or-drop decision; no Claude Code behavior change. [paraphrase]

## Boundaries

- COST optimization only - the correctness invariant (scouts are read-only, review is cross-family) is unaffected. [user]
- Does NOT touch the host-review pin path (already works). [user]
- No new flowctl surface; skill-prose + scaffold decision only. [paraphrase]

## Decision Context

### Motivation

- Direct fn-123 follow-up found by dogfooding: the scaffold promises a cheap scout pin that the pipeline never applies on Cursor. Either honor it or stop advertising it. [user]

## Requirement coverage

| R-ID | Task |
|------|------|
| R1 | fn-125-cursor-scout-pin-wiring-consume-the.2 |
| R2 | fn-125-cursor-scout-pin-wiring-consume-the.2 |
| R3 | fn-125-cursor-scout-pin-wiring-consume-the.3 |
| R4 | fn-125-cursor-scout-pin-wiring-consume-the.1 |
| R5 | fn-125-cursor-scout-pin-wiring-consume-the.4 |
