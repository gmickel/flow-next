# 9.18.0 last fixes: legacy fan-out rows, criteria section end, Antigravity setup text

## Goal & Context

<!-- Source: 10% user / 70% [paraphrase] / 20% [inferred] -->

The third audit of everything since 9.17.0 confirmed that the command runner and the fan-out executor now match 9.17.0, so the process-handling machinery is gone. It still returned NEEDS_WORK on a handful of small, unrelated defects. This spec fixes the ones that hold up so 9.18.0 can ship. Each is a few lines.

The unattended failures the first two prevent: a receipt that names no reviewer after an upgrade, and a compliance record that says a standing criterion was met when the reviewer's output contradicted itself.

## Acceptance Criteria

- **R1:** Finalizing a fan-out whose primary draw's pending row carries no command label, which is every pending row written by 9.17.0, behaves as 9.17.0 did: a surviving draw on the same backend supplies the session and the receipt keeps that draw's `command:<label>` spec. The same-label rule applies only when the primary's label is known. A receipt is never written with an empty label or a bare `command` spec. [paraphrase]
  Errors: no surviving draw → no session, as today.
- **R2:** The per-criterion section of a review ends only at a recognized tally line or tally block. Any other fenced block inside the section keeps the earlier behaviour, where an ambiguous section yields no criteria, so conflicting records for one criterion can never be recorded as a single status. [paraphrase]
  Errors: a tally line written in bold is recognized the same way the tally parser recognizes it.
- **R3:** The documented Antigravity review wrapper, and its mirror copy, gives `agy` a deadline derived from the request's budget and never longer than it; the wrapper's own stop stays as the backstop. [paraphrase]
  Errors: no error surface.
- **R4:** On Antigravity, setup never suggests the Host reviewer, since host review fails closed there; with no review CLI installed it points to installing one or choosing none. [paraphrase]
  Errors: other hosts' wording is unchanged.
- **R5:** Two setup observations from the audit are checked on Antigravity and fixed only if they reproduce: that the instruction snippet written for Antigravity shows skill ids where the platform guide promises slash commands, and that a saved "CLAUDE.md only" answer can leave setup silent when no snippet exists at all. Each is a wording change in the setup skill and its checklist if real. [paraphrase]
  Errors: one that does not reproduce is recorded as such and left alone.

## Boundaries

- No stricter YAML handling in the Antigravity bundle builder. The audit's case, a restriction written with YAML's explicit-key form, cannot occur in the agent files this repository ships, and the builder only ever reads those. [inferred]
- No change to the command runner, the fan-out executor, the ladders or any receipt field. [inferred]
- No new stage, verb, config key or check. [inferred]

## Decision Context

These are independent small defects, not a design problem, so they are fixed in one short change with a focused review. The area that caused the earlier rounds is confirmed back at 9.17.0 behaviour by all three audit draws.
