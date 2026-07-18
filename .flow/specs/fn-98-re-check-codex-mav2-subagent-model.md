# fn-98 Re-check codex MAv2 subagent model steering fixes (watch, ~2026-07-22)

## Goal & Context
<!-- scope: business -->

Watch stub, not a build spec. As of 2026-07-15, Codex GPT-5.6-Sol / Multi-Agent-V2 builds cannot reliably steer subagent models (openai/codex#32782 agent_type missing from spawn_agent; #33268 role-layer agents silently drop model/effort overrides; #33314 role-profile application unverifiable; #33267 codex exec + MAv2 children return undecodable results; #31814 was the root event, partially fixed by PR #32749). Because of this, fn-97 shipped the Codex-mirror worker pin as OPT-IN (default inherit) and the docs recommend the `codex exec -m` same-family self-bridge as the robust steering route from a Codex host.

Around 2026-07-22, re-check the four open issues and the current codex CLI release.

## Architecture & Data Models
<!-- scope: technical -->

Not applicable - research/doc-refresh stub. If the issues are fixed: consider (a) simplifying the "Known Codex limitation (Jul 2026)" note in orchestration.md + the platforms.md caveat + the usage.md self-bridge line's parenthetical, (b) whether the sync-time worker pin recommendation can be promoted (still opt-in - the prompted-layer principle stands regardless), (c) verifying with a live probe: register a role with developer_instructions + a model pin, spawn from a Sol parent, confirm the child session_meta reports the pinned model.

## API Contracts
<!-- scope: technical -->

None.

## Edge Cases & Constraints
<!-- scope: technical -->

- The prompted-layer principle (no hardcoded model opinions in generated config) survives any upstream fix - only the reliability caveats get removed.
- If issues remain open, refresh the date in the docs notes and re-stub.

## Acceptance Criteria
<!-- scope: both -->

- R1: openai/codex #32782, #33268, #33314, #33267 statuses checked and recorded here with the CLI version tested.
- R2: docs caveats (orchestration.md, platforms.md, usage.md template + dogfood, flow-next.dev orchestration page) updated or re-dated to match reality.
- R3: live probe result recorded if any issue claims a fix.

## Boundaries
<!-- scope: business -->

- NOT re-opening the fn-97 hard-pin decision - opt-in stays regardless (design principle, not a workaround).
- No code changes unless a docs claim is factually stale.

## Decision Context
<!-- scope: both -->

Created 2026-07-15 during fn-97 post-review discussion (maintainer caught the hard pin; research confirmed upstream breakage made it doubly wrong). Full issue digest in the maintainer memory note codex-mav2-subagent-steering-broken.


## Addendum 2026-07-18 (fn-100 R12 dependency)

The interview skill now ships an async fact-scout mode (fn-100 Edit D). On the Codex host the scout dispatch is `spawn_agent` with `agent_type: explorer`, and because MAv2 subagent model steering is the broken surface this spec re-checks, the scout currently INHERITS the session/default model - unpinnable. That is safe today (sol/terra clear the mid-tier floor by default) but not cost-optimal.

- R4: when the re-check finds subagent model/effort steering working, ALSO update the fact-scout guidance for Codex hosts: pin the scout to the cost-optimal capable tier (gpt-5.6-terra at medium was the eval-era candidate) and record the pin syntax in orchestration.md + the Codex mirror wording. Until then the inherit-default behavior stands and needs no caveat beyond this note.


## Status check 2026-07-18 (early, user-requested; R1 partial)

Checked with gh against openai/codex (local codex-cli 0.144.1):

- #32782 CLOSED 07-16 (spawn_agent agent_type exposure; maintainer jif-oai: "will land soon", merged into umbrella #31814 - itself CLOSED 07-17).
- #33268 CLOSED 07-16 (model/reasoning_effort silently dropped - consolidated as duplicate; the substantive fix is PR #32749 "Expose model overrides for multi-agent v2 spawns", MERGED to main 2026-07-13).
- #33314 still OPEN (full-profile verification follow-up; fresh macOS repro 07-16 shows role/model/effort now APPLY in newer builds but the role's sandbox layer is replaced by the parent's - i.e. steering works, profile application incomplete).
- #33267 still OPEN (codex exec MAv2 subagent results unusable in parent turn).
- App-side field report (in #31814): updated Codex app supports specifying subagent models for gpt-5.6-sol and gpt-5.6-terra, NOT gpt-5.6-luna.

Ship vehicle: PR #32749 is on main only - the 0.144.x line ships cherry-picked fixes (0.144.5/6 notes contain no spawn changes); the feature rides 0.145.0 (alpha.23 as of 07-17, no stable yet). Local 0.144.1 predates it, so NO live probe of the fix is possible without an alpha install (not done - R3 pending a stable release).

Disposition: fixed-upstream, unreleased-on-stable. Re-run this spec in full when rust-v0.145.0 STABLE ships: R3 live probe (spawn_agent model+effort override observed end-to-end), then R2 docs updates and R4 (pin the interview fact-scout on Codex hosts, terra@medium candidate) - and note #33314's sandbox-replacement caveat when writing the docs: model steering working does not yet mean full profile application.
