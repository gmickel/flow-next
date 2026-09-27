# Scout model pins: Opus on Claude, gpt-6 on Codex

## Conversation Evidence

> user (turn 1): "honestly, move all to opus 5.5, do we have anything IN flow-next that makes the scouts use haiku for our users"
> user (turn 2): "yea small spec that we'll do after these two and bake it into the release"
> user (turn 2, part 2): "the codex pins have to change too, gpt-6-luna is out, pointless using the old one."
> user (turn 2, part 3): "the issue with model: inherit is if the user is using fable for planning for example"
> user (turn 3): "this is fine until the new sonnet comes out this week, which we can note into our memory to recheck mid week."
> user (turn 4): "leave copilot on haiku, carry on"
> user (turn 5): "https://github.com/gmickel/flow-next/issues/486 might be something we can add to that small spec, looks simple"
> user (turn 5, part 2): "also mark it ready and make sure it's done after these two get through"

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 30% [user], 50% [paraphrase], 20% [inferred] -->

Flow-next's bundled agents choose their own model through their agent definitions, and those choices are what users actually run with. Today the prime scouts and memory-scout are pinned to Haiku, and most research scouts, the gap analyst and plan-sync are pinned to Sonnet. On the Codex side the mirror generator translates those pins into last-generation models (gpt-5.6-luna for the fast tier, gpt-5.6-terra for the intelligent tier). The codex review backend's triage judge (the cheap pre-filter that decides whether a diff merits a full review) also defaults to gpt-5.6-luna. Codex now serves gpt-6-astra, gpt-6-sol and gpt-6-luna, so "pointless using the old one". [paraphrase]

The maintainer wants every scout on Opus. Pinning to the current Opus is chosen over following the session model (`inherit`) because a user who plans on Fable would otherwise pay Fable prices for every scout fan-out. [paraphrase] This is an interim choice: a new Sonnet is expected this week, and the pin choice is rechecked when it lands. [paraphrase]

Target user: every flow-next user whose sessions dispatch the bundled scouts, on Claude Code or through the Codex mirror. [inferred]

## Architecture & Data Models
<!-- scope: technical -->

- **Claude agent definitions.** Every bundled scout, the flow gap analyst and plan-sync that is pinned to `haiku` or `sonnet` moves to `opus`. The `opus` alias follows the current Opus release, so the pin needs no bump when Opus moves. Agents that already inherit (the worker, the PR comment resolver) and the quality auditor (already `opus`) are unchanged. [paraphrase]
- **Codex mirror baselines.** The generator's fast-tier baseline moves from gpt-5.6-luna to gpt-6-luna, and its intelligent-tier baseline from gpt-5.6-terra to gpt-6-sol (no gpt-6-terra is served). After the Claude change every mapped agent resolves to the intelligent tier, so the fast baseline stays current but may have no default consumer. The committed mirror is regenerated from the generator, never hand-edited. [paraphrase]
- **Codex triage judge.** The codex review backend's triage-judge baseline moves from gpt-5.6-luna to gpt-6-luna, keeping its current effort. The copilot backend's triage judge stays on claude-haiku-4.5. [paraphrase]
- **Codex reviewer fallback ranking.** gpt-6-sol joins the codex backend's model ranking directly after gpt-6-astra, so a withheld astra steps down to the same generation first. [inferred]
- **Resumed codex reviews keep their model (issue #486, reported by @TechupBusiness).** A codex review resumes its reviewer session for every fix-loop re-review, validator pass and deep pass, and today the resume sends effort, sandbox and project-doc settings but no model, on the assumption that a session keeps the model of its original dispatch. Since codex-cli 0.154 a resumed session runs on the model in Codex's own config instead, so a review pinned to one model silently re-reviews on another while the receipt still records the pin. The resume re-pins the model the original dispatch actually ran, whether it was named explicitly or resolved through the fallback ladder. [paraphrase]
- **Pins that assert these values** (the mirror floor check, model-resolution baselines) move with the change in the same commit. [inferred]

## Edge Cases & Constraints
<!-- scope: technical -->

- A Codex CLI too old to serve the gpt-6 family: the existing reviewer fallback ladder applies; the mirror pins are preferences a user can override by environment at regeneration time, as today. [inferred]
- An explicit user routing preference (instruction-file routing block or explicit invocation argument) still wins over the agent default, exactly as today. [inferred]
- Cost: Opus scouts cost more than Haiku scouts for users on cheaper plans. The docs that price optional layers state the new default honestly. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** No bundled Claude agent definition pins `haiku` or `sonnet`; every previously Haiku- or Sonnet-pinned scout, the flow gap analyst and plan-sync pin `opus`, and no agent that pinned a model before now inherits the session model. [paraphrase]
- **R2:** The Codex mirror generator's baselines are gpt-6-luna (fast) and gpt-6-sol (intelligent), the committed mirror matches a clean regeneration byte for byte, and no generated Codex agent names a gpt-5.6 model. [paraphrase]
- **R3:** The codex review backend's triage judge defaults to gpt-6-luna; the copilot backend's triage judge still defaults to claude-haiku-4.5. [paraphrase]
- **R4:** The codex reviewer fallback ranking lists gpt-6-sol immediately after gpt-6-astra. [inferred]
- **R5:** User-facing docs that name scout models or per-tier defaults (reach pages, orchestration and running-lean guidance, and the flow-next.dev pages that repeat them) state the new defaults, and the CHANGELOG entry for the release names the baseline bump. [inferred]
- **R6:** The full test suite passes with the pins that assert model values updated to the new defaults. [inferred]
- **R7:** Every resumed codex review turn (re-review, validator, deep pass) runs on the model the session's original dispatch used, for explicit pins and ladder-resolved models alike; a regression test asserts the resume invocation carries that model, and the release notes credit the reporter of issue #486. Errors: if the original dispatch model is unknown, the resume behaves as today rather than guessing. [paraphrase]

## Boundaries
<!-- scope: business -->

- Scouts are not switched to `inherit`: a Fable planning session must not make every scout Fable. [paraphrase]
- The copilot triage judge stays on Haiku. [user]
- No new routing mechanism, config key or model-selection logic; this changes default pins only. [inferred]

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

Haiku-pinned scouts and last-generation Codex models give users weaker scouting than the models they already have access to, and the maintainer wants the strongest current defaults ("move all to opus 5.5"). [paraphrase] Opus rather than `inherit` bounds cost for Fable sessions. [paraphrase] The choice is explicitly interim until the new Sonnet ships; a recheck around 2026-09-30 decides whether Sonnet replaces Opus as the scout pin. [paraphrase]

Delivery order: after fn-265 and fn-266 (recorded as dependencies), shipped in the 6.4.0 release. [paraphrase] Issue #486 is folded in because it is the same concern, a model pin that silently does not hold, and the fix is small. [paraphrase]

## Strategy Alignment

Serves **Cross-platform parity**: the Claude pins and the Codex mirror move together, and the mirror stays generated from one source. [strategy:Cross-platform parity]

## Strategy Conflicts

None found.
