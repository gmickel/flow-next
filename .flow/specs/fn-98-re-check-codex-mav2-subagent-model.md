# fn-98 Codex MAv2: steering re-check, docs currency, and the read-only guarantee

*(Originally a watch stub for subagent model steering. Absorbed fn-161 - the Codex read-only guarantee - on 2026-08-03: same host, same generated roles, same `platforms.md` paragraphs, and both investigations closed by the same probe matrix. Keeping them separate guaranteed a conflicting rewrite of one file.)*

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

- **R1:** **DONE (2026-08-03, codex-cli 0.146.0).** #32782 CLOSED, #33268 CLOSED, #31814 CLOSED; #33314 and #33267 OPEN. Recorded with the probe matrix below.
- **R2:** docs caveats (`docs/orchestration.md` x2, `docs/platforms.md`, `templates/usage.md` + `skills/flow-next-setup/templates/model-routing-snippet.md`, the flow-next.dev orchestration page) must stop saying subagent model steering is unreliable, and must instead state: (a) steering works on 0.146.0 via both paths; (b) **a role's `sandbox_mode` is not enforced** - read-only is prompt-only on Codex; (c) the two dispatch gotchas (`agent_type` takes the role's `name`, not the `[agents.<key>]` table key; `agent_type` requires `fork_turns: "none"`); (d) the model-selection precedence rule below. The `codex exec -m` self-bridge stays valid, but is no longer the only reliable route.
- **R3:** **DONE (2026-08-03).** Ten-probe matrix, every verdict read from the child thread's rollout `turn_context`. Steering works on both the role path and the explicit-parameter path.
- **R4:** pin the interview fact-scout on Codex hosts. **Verified implementation (P10):** the mirror's dispatch becomes `spawn_agent` with `agent_type: explorer`, `model: gpt-5.6-terra`, `reasoning_effort: medium`, `fork_turns: "none"`. `explorer` is a Codex **builtin** role that declares no model of its own, so the explicit parameter applies - no new role needs registering. Today it inherits the session model (`sol`/`high`), which is the cost gap. The edit lands in `codex/skills/flow-next-interview/SKILL.md` via a `sync-codex.sh` transform, and that line sits under the fn-100 scout-tier hard-fail guard, so the guard moves with it.
- **R5:** `scripts/sync-codex.sh:1650`'s claim - "Codex enforces read-only via sandbox_mode" - is corrected in place, with the measured evidence cited next to it (child-side `patch_apply_end`: `Success. Updated the following files: A ro-probe.txt`, under a role declaring `sandbox_mode = "read-only"`). A future reader must not be able to re-assert host parity from the comment alone. The same applies to `:1671`, which drops `disallowedTools` on that rationale.
- **R6:** `docs/platforms.md` states the read-only guarantee per host explicitly: **harness-enforced on Claude Code** via `disallowedTools`; **prompt-only on Codex**, where a role can neither narrow nor widen a child's sandbox. It also documents the one lever that does work - containment comes from the **parent process launch flag** (`codex -s read-only`), never from a role. The current text implying uniform coverage is replaced, not annotated.
- **R7:** The repo `CLAUDE.md` cross-platform "Agent permissions" bullet is corrected to match R6. It currently reads as though the `disallowedTools` blacklist translates cleanly to every host.
- **R8:** `sync-codex.sh` validation fails if any emitted role TOML carries a key outside the measured accepted set (`name`, `description`, `model`, `model_reasoning_effort`, `sandbox_mode`, `nickname_candidates`, `developer_instructions`). Rationale: an unrecognized key does not error - Codex warns and **discards the entire role**, so one bad field silently removes all 21 scout roles and turns every scout dispatch into `unknown agent_type`. The schema is undocumented and moved across three CLI releases.
- **R9:** No behavior change on Claude Code, Droid, Cursor or Grok. `sync-codex.sh` runs twice with a clean second diff.

**Framing constraint for R5-R9 (carried from fn-161):** this is truth-in-labelling, **not a security fix**. No CVE framing, no urgency language in CHANGELOG or docs. The realistic failure is a scout that misreads its brief and edits a file - recoverable and visible in git. Nothing routes untrusted input into a scout. The reason to act is that we state a guarantee we do not keep on one host. Equally out of scope: any new abstraction over host permissions, and any change to the canonical agent frontmatter (`readonly: true` / `disallowedTools` are correct on the host that enforces them).


**Model-selection precedence on Codex 0.146.0 (measured, P3/P4b/P4c/P5b/P7b/P9/P10):**

1. A role's **declared** `model` / `model_reasoning_effort` wins over an explicit spawn parameter (P5b: `agent_type=probe-terra` + explicit `model=sol` ran `terra`).
2. Where the role declares **no** model, the explicit parameter applies (P10: builtin `explorer` + explicit `terra/medium` ran `terra/medium`).
3. With no `agent_type` at all, the explicit parameter applies; `reasoning_effort` may be set alone (P1, P7b).
4. The explicit `model` parameter accepts **only** `gpt-5.6-sol` and `gpt-5.6-terra` (P4c errors on `luna`). A **role** can pin `luna` successfully (P4b) - the role path reaches models the parameter cannot.

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

## Probe matrix 2026-08-03 (codex-cli 0.146.0, disposable `CODEX_HOME`)

Nine probes against a throwaway `CODEX_HOME` with purpose-built roles, so nothing touched the real config. Every verdict below is read from the **child thread's rollout `turn_context`**, not from the child's self-report, and the write test is confirmed on disk.

| # | Setup | Result |
|---|---|---|
| P1 | explicit `model=terra effort=medium`, no `agent_type` | **applied** - child `terra/medium` |
| P2 | no overrides (control) | **inherits** - child `sol/high` |
| P3 | `agent_type=probe-terra`, no explicit model | **role model applied** - child `terra/medium` |
| P4b | `agent_type=probe-luna` | **applied** - child `gpt-5.6-luna` |
| P4c | explicit `model=luna`, no `agent_type` | **hard error**: ``Unknown model `gpt-5.6-luna` for spawn_agent. Available models: gpt-5.6-sol, gpt-5.6-terra`` |
| P5b | `agent_type=probe-terra` **+** explicit `model=sol effort=high` | **role wins** - child ran `terra/medium`; the explicit args were silently ignored |
| P7b | `reasoning_effort=low` only | **applied** - child `sol/low` |
| P8 | depth-2 nested spawn | **works** - grandchild reply returned verbatim (`GRANDCHILD=DEEP`) |
| P6 | role `sandbox_mode="read-only"` under a `workspace-write` parent | **NOT enforced** - child `sandbox=workspace-write`, and the child **actually created the file** (verified on disk) |

**Corrections to earlier entries in this spec.** Two claims made before this matrix were wrong and are retracted:

1. "Role-profile application is unverifiable / the role path is broken" - **false**. P3 and P4b show role-declared model and effort applied end to end. The role path is the *stronger* of the two.
2. "Pin the fact-scout via explicit spawn params rather than a role model" - **backwards**. Explicit params are the weaker path: restricted to `sol`/`terra` (P4c) and silently overridden by the role whenever `agent_type` is set (P5b).

**Two asymmetries worth remembering.** The role path reaches models the direct spawn parameter cannot (`luna` works as a role, errors as a param). And role beats explicit param rather than the reverse - so an `agent_type` dispatch cannot be model-overridden at the call site at all.

**Two dispatch gotchas.**

- `agent_type` must match the role's `name` field (hyphenated, `probe-terra`), NOT the `[agents.<key>]` table key (underscored, `probe_terra`). The first attempt with the table key failed and the agent silently retried with the name.
- `agent_type` is incompatible with a full-history fork: ``Full-history forked agents inherit the parent agent type; omit agent_type, or spawn without a full-history fork.`` Always pass `fork_turns: "none"` alongside `agent_type`.

**The one finding that is a real flow-next defect.** Every generated scout role in the Codex mirror declares `sandbox_mode = "read-only"`. P6 shows that declaration is **not enforced** - the child runs at the parent's `workspace-write` and can write. This is stronger evidence than openai/codex#33314's own repro, which explicitly could not distinguish an enforcement defect from a reporting defect; here the file landed on disk. Consequence: **the read-only guarantee for flow-next scouts does not hold on a Codex host.** It is mitigated only by prompt (`disallowedTools` / instructions), never by the sandbox. Do not describe Codex scouts as sandbox-enforced read-only, and do not rely on the role sandbox as a boundary for anything with real blast radius.

**Net upstream reading.** Model and effort steering is working on both paths. #33267 did not reproduce for plain nested spawns. #33314's model-attestation half is explained by self-report being unreliable; its **sandbox half is real, reproduced here, and is the only part that still affects us**.

### P6 re-verification (same session): the finding holds, on child-side evidence

The first P6 run was under-evidenced - it concluded "the child wrote" from the file existing on disk, which does not attribute the write. An isolated re-run then reported `WRITE=BLOCKED` with no file, which looked like a contradiction. Both were resolved by reading the **child's** rollout rather than the parent's summary:

- **Run 1** (child `role=probe-ro`): the child executed `patch_apply` itself; the record carries `stdout: "Success. Updated the following files:\nA ro-probe.txt"`. The write is the child's, and it succeeded.
- **Run 2** (child `role=probe-ro`): zero `ro-probe` events in the child's rollout - the child never attempted the write, because its role `developer_instructions` say "Reply with the single word ACK. Do nothing else." The parent's `WRITE=BLOCKED` was inferred from an absent result. Nothing was blocked; nothing was tried.

**Confirmed:** a child whose role declares `sandbox_mode = "read-only"`, spawned under a `workspace-write` parent, runs at `workspace-write` and can complete a write. What differed between runs was the child obeying its own instructions, not sandbox enforcement.

**Method note, third instance of the same error in one session.** Self-report is not evidence; a parent's narration of a child is not evidence; a side effect on disk does not attribute itself to an actor. Only the child's own rollout settles any of it. A probe whose role instructions ("do nothing else") conflict with its task prompt also produces non-attempts that read as blocks - keep probe roles permissive and put the task in the prompt.

### Probes P9/P10 (2026-08-03): the fact-scout dispatch, resolved

The Codex mirror instructs `spawn_agent` with `agent_type: explorer`, and no `explorer` role is registered anywhere in the generated config or `~/.codex/agents/`. That looked like a live defect (an unregistered role name would error, as a wrong table key did in P3).

- **P9:** `agent_type: explorer` spawns cleanly - child `role=explorer`, `model=gpt-5.6-sol effort=high`. `explorer` is a **Codex builtin**, not something flow-next registers. **No live bug**; the dispatch works and simply inherits the session model.
- **P10:** `agent_type: explorer` **+** explicit `model=gpt-5.6-terra reasoning_effort=medium` - child ran `terra/medium`. The pin applies.

This also **corrects the generalization drawn from P5b.** "Role always wins over the explicit parameter" is wrong. The rule is: a role's *declared* model wins; where the role declares none, the explicit parameter applies. P5b's custom role declared `terra`, which is why the explicit `sol` lost.

Net: R4 is a one-line dispatch change with no new role to register, and it is measured rather than assumed.


## Investigation record 2026-08-03 (R2 closed, codex-cli 0.146.0)

Resolved by reading the shipped schema and source, then testing live. No part of this is left for implementation.

**Upstream schema (authoritative).** `codex-rs/core/config.schema.json` defines `AgentRoleToml` for the `[agents.<key>]` table (`config_file`, `description`, `nickname_candidates` only). The file that `config_file` points at is described as "a role-specific config layer", so it accepts top-level config keys - which is why `permissions` parsed at all. `permissions` is `BTreeMap<String, PermissionProfileToml>` (`config/src/permissions_toml.rs`): a map of *named profiles*, not a restriction. The selector is the separate root key **`default_permissions`** - "Names starting with `:` refer to built-in profiles". The built-ins are `:read-only`, `:workspace`, `:danger-full-access` (`protocol/src/models.rs:304-310`). `PermissionProfileToml` fields: `description`, `extends`, `filesystem`, `network`, `workspace_roots`.

**Live results.**

| # | Setup | Child sandbox | Write |
|---|---|---|---|
| P6 | role `sandbox_mode="read-only"`, parent `workspace-write` | `workspace-write` | **succeeded** (child `patch_apply_end`: `Success. Updated the following files: A ro-probe.txt`) |
| P12 | role `default_permissions=":read-only"`, parent `workspace-write` | `workspace-write` | **succeeded** (child verified the bytes `57 52 4f 54 45 0a`) |
| P13 | same role, parent launched `-s read-only` | `read-only` | blocked; no file |
| P11 | role with an unrecognized key (`tools`) | n/a | role **silently discarded**; dispatch failed `unknown agent_type` |

**Verdict.** There is no role-level read-only mechanism on 0.146.0. A child's sandbox is inherited from its parent in both directions; a role can neither narrow nor widen it. `default_permissions` in a role file is accepted, parses, and has no effect on a spawned child.

**Consequence.** There is nothing to emit, so the absorbed work is purely R5 (correct the false comment), R6 (state the per-host guarantee and the parent-launch lever), R7 (`CLAUDE.md` parity bullet), R8 (guard the silent-drop mode), R9 (no behavior change elsewhere). Zero uncertainty remains.

**One divergence from upstream worth noting.** openai/codex#33314's 2026-08-01 report describes a `-s read-only` parent producing children that report `workspace-write`. P13 did not reproduce that: the read-only parent produced a read-only child. Their case involved project-local custom roles and `-a never`; ours used a single role and default approvals. Not contradicted, not reproduced - and it does not change this spec's conclusion, which rests on the workspace-write-parent case that flow-next actually runs.
