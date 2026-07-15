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
