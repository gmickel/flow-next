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

## Addendum 2026-07-18 (second - post fn-89 Tier B probe)

The fn-89 live probe (codex-cli 0.144.1, `codex exec` surface) confirmed the plain spawn fork-join primitive works TODAY: sol spawned a child, collab Wait joined, and the parent read the child's reply back verbatim (CHILD_SAID echo probe, 15.7k tok). Consequences for this spec:

- **Decoupling:** fn-89's Codex path no longer waits on this spec - Tier B (isolated-but-awaited, session-model inheritance) is live without steering. This spec is now purely (a) cost optimization - pin runners/fact-scouts to terra instead of inheriting sol - and (b) docs currency.
- **R3 probe harness exists:** reuse the fn-89 echo probe with model/effort params added and the child asked to report its model id. Recipe: `codex exec -m gpt-5.6-sol -s workspace-write --skip-git-repo-check "<spawn one subagent pinned to gpt-5.6-terra effort medium; child replies with its model id; parent ends with CHILD_MODEL=<id>>"`. One command, deterministic parse of the terminal line.
- **Local-config gotcha (fold into R2 docs):** `--enable multi_agent_v2` errors with `agents.max_threads cannot be set when features.multi_agent_v2 is enabled` (-32600) against this machine's config - while the plain run (no enable flag) spawned fine, proving MAv2 is already default-active for sol. Docs guidance: never force-enable the feature flag; it is default-on for sol and force-enabling collides with `agents.max_threads` configs.
- **#33267 scope narrowed:** the blanket "exec-surface results unusable" caveat is too broad - simple task-prompt spawns return results fine; the breakage evidently concerns richer shapes (output schemas / fork_turns / custom profiles). R2's docs updates should narrow the caveat accordingly.

## Status check 2026-07-23 (Codex CLI 0.145.0 stable)

The stable release this watch was waiting for is installed locally (`codex-cli 0.145.0`). Upstream state:

- #32782 and #33268 remain closed; PR #32749 remains merged.
- #33314 remains OPEN (updated 2026-07-22).
- #33267 remains OPEN (updated 2026-07-22).

Live R3 probe, run from this repository:

```text
parent: gpt-5.6-sol, high
requested child: gpt-5.6-terra, medium
terminal result: CHILD_MODEL=gpt-5.6-sol
```

The child override was not honored end to end. The probe did successfully spawn and join a child, so the defect remains specifically model/effort steering rather than basic fork/join. Disposition: keep the inheritance-safe behavior and the `codex exec -m` self-bridge guidance; do not pin the interview fact-scout through `spawn_agent`. Re-check only after #33314 reports a released fix or a later Codex release explicitly claims full profile/model application.

## Status check 2026-08-03 (Codex CLI 0.146.0) - STEERING WORKS; prior finding was a false negative

**R1 - upstream state.** Local `codex-cli 0.146.0`.

| Issue | State | Last update | Subject |
|---|---|---|---|
| #32782 | CLOSED | 2026-07-16 | `spawn_agent` `agent_type` exposure |
| #33268 | CLOSED | 2026-07-16 | model / `reasoning_effort` silently dropped |
| #31814 | CLOSED | 2026-07-15 | umbrella: cannot specify subagent models |
| #33314 | OPEN | 2026-08-01 | full-profile application + verifiable effective-config receipt |
| #33267 | OPEN | 2026-07-27 | `codex exec` MAv2 results undecodable in parent turn |

**R3 - live probe, and the correction it forces.** Parent `gpt-5.6-sol` @ high, requested child `gpt-5.6-terra` @ medium.

- Child self-report: `CHILD_MODEL=gpt-5.6-sol` - identical to the 2026-07-23 result.
- Parent rollout `spawn_agent` call carried `"model":"gpt-5.6-terra","reasoning_effort":"medium"` - the override was emitted.
- **Child thread rollout `turn_context`: `model=gpt-5.6-terra, effort=medium`**, and the child rollout contains four `gpt-5.6-terra` mentions and zero `sol`. Child session `019fc4bb-d10f-7ae1-b58c-78311e786b3c`, `thread_source=subagent`, `agent_path=/root/report_model`.
- **Control run** (identical prompt, NO override): child `turn_context` = `model=gpt-5.6-sol, effort=high`. The field tracks the request rather than echoing a constant, which is what makes the positive result load-bearing.

**Verdict: model and reasoning-effort steering via `spawn_agent` works on 0.146.0.** The 2026-07-23 status check recorded "the child override was not honored end to end" from the child's self-report. That was a **false negative**: a model cannot reliably name its own model id - the Codex base instructions themselves say "You are Codex, an agent based on GPT-5", so `gpt-5.6-sol` was a plausible-sounding guess, not a routing observation. **Never verify routing by asking the model; read the host record.**

**What the two OPEN issues actually are - neither blocks model steering.**

- **#33314 is about sandbox/permission profile application and the absence of an in-band receipt**, not model selection. The 2026-08-01 macOS repro (same 0.146.0) shows a `read-only` parent spawning children that report `workspace-write`, and separately that the children could not attest their own model or effort. That second half is the same self-report defect this check just diagnosed - the information exists in the rollout, just not in-band.
- **#33267 concerns richer exec-surface shapes** (malformed `encrypted_content` blocks under `fork_turns: "none"` with routed custom roles). Plain task-prompt spawns return results fine; both probes here joined and returned cleanly.

**Consequences for flow-next.**

1. **R2 docs are now factually stale.** The "Known Codex limitation (Jul 2026)" note in `orchestration.md`, the `platforms.md` caveat, and the `usage.md` self-bridge parenthetical all state that subagent model steering is unreliable. On 0.146.0 it is not. The `codex exec -m` self-bridge stays a valid route, but it is no longer the *only* reliable one.
2. **R4 is unblocked.** The interview fact-scout on Codex hosts can be pinned (`gpt-5.6-terra` @ medium remains the cost-optimal candidate) instead of inheriting the session model.
3. **Verification carries a real cost.** There is no in-band receipt - confirming an effective pin means reading `~/.codex/sessions/**/rollout-*.jsonl` for the child thread's `turn_context`. Nothing in flow-next should attempt runtime verification of a pin; pin and trust, and re-probe out of band when a Codex release lands.
4. **Sandbox inheritance stays untrustworthy (#33314).** A pinned child does not reliably inherit a narrowed sandbox. Do not use a role's `sandbox_mode` as a security boundary for anything flow-next spawns.
5. `gpt-5.6-luna` remains `multi_agent_version: "v1"` and cannot be selected by a V2 parent (open ask on #31814, 2026-08-01).

**Disposition:** re-check complete, R1 and R3 satisfied. R2 and R4 are now real work - docs currency across four properties plus the fact-scout pin - and should be planned rather than absorbed into this stub.
