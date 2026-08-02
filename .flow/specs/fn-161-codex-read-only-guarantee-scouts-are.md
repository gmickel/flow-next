# fn-161 Codex read-only guarantee: scouts are declared read-only and are not

## Goal & Context
<!-- scope: business -->

flow-next ships 21 read-only scout agents. Their canonical definitions declare the guarantee twice - `readonly: true` and `disallowedTools: Edit, Write, Task`. On Claude Code that is real: the harness enforces the tool blacklist. On a Codex host it is not. `sync-codex.sh` drops `disallowedTools` as a Claude-only key and substitutes `sandbox_mode = "read-only"` in the generated role, and a comment in the script asserts that this is equivalent:

> `sync-codex.sh:1650` - "Codex enforces read-only via sandbox_mode"

**It does not.** Measured on codex-cli 0.146.0 (fn-98 probe P6): a child spawned from a role declaring `sandbox_mode = "read-only"`, under a `workspace-write` parent, ran at `workspace-write` and completed a write. The child's own rollout carries `patch_apply` with `stdout: "Success. Updated the following files: A ro-probe.txt"`. This is stronger evidence than openai/codex#33314's own reproduction, which explicitly declined to distinguish an enforcement defect from a metadata-reporting one; here the file landed on disk and the actor is attributable from the child-side record.

**This spec is a truth-in-labelling fix first and a hardening fix only if one is available.** The realistic failure today is a scout that misreads its brief and edits a file: annoying, recoverable, visible in git. Nothing routes untrusted input into a scout, and every scout is prompted not to write. The reason to act is that we make a guarantee we do not keep, in a project whose whole pitch is that the process is trustworthy - and a maintainer reading `readonly: true` today will reasonably assume parity across hosts.

Who this is for: anyone running flow-next on Codex, and specifically anyone reasoning about blast radius when deciding what a scout may be pointed at.

## Architecture & Data Models
<!-- scope: technical -->

Three assertion sites, one measured behavior, one candidate mechanism.

**Assertion sites (all currently wrong or misleading on Codex):**

1. `scripts/sync-codex.sh:1650` - the comment claiming `sandbox_mode` enforces read-only.
2. `scripts/sync-codex.sh:1671` - drops `disallowedTools` with the rationale that Codex covers it via `sandbox_mode`.
3. `plugins/flow-next/docs/platforms.md` - the cross-platform matrix presents agent permissions as a solved, uniform concern (`disallowedTools` blacklist "works because both understand Edit, Write, Task"). The same claim appears in the repo `CLAUDE.md` cross-platform section.

**The role schema, as measured (codex-cli 0.146.0).** A generated role accepts exactly: `name`, `description`, `model`, `model_reasoning_effort`, `sandbox_mode`, `nickname_candidates`, `developer_instructions`. A `permissions` key is also accepted and is a **struct**, not a string - `permissions = {}` parses; `permissions = { file_system = "restricted" }` fails with `invalid type: string`; `permissions = { network = false }` fails with `expected struct PermissionProfileToml`. That shape matches the `permission_profile` object already visible in a session's `turn_context`:

```
"permission_profile": {"type": "managed", "file_system": {"type": "restricted", "entries": [...]}}
```

`permissions` is therefore the **only** candidate mechanism for a real restriction. `tools`, `allowed_tools`, `disallowed_tools` are all rejected.

**The failure mode that governs the whole design (probe P11).** An unrecognized key does not fail loudly. Codex emits `warning: Ignoring malformed agent role definition: ... unknown field` and **discards the entire role**. The next dispatch then fails with `Could not spawn subagent: unknown agent_type '<name>'`. Applied to our sync, a single bad key in the emitted schema silently removes **all 21 scout roles**, and every scout dispatch across every skill fails at once. Any change to what we emit must be gated on this, not merely tested for parse success.

## API Contracts
<!-- scope: technical -->

No flowctl surface, no config keys, no new commands. The artifacts are:

- generated role TOMLs under the Codex mirror (`plugins/flow-next/codex/`, and the installed `$CODEX_HOME/agents/*.toml`)
- `scripts/sync-codex.sh` (emission + comments + any new guard)
- prose in `docs/platforms.md`, `docs/orchestration.md`, repo `CLAUDE.md`

If the investigation finds `permissions` enforceable, the contract added is one emitted TOML block per read-only role, and a `sync-codex.sh` guard asserting every role carrying `readonly: true` upstream emits it.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Silent role loss is the dominant risk.** Emitting an unsupported `permissions` shape costs every scout on every Codex host, with a warning most users will not read. The verification must be a live spawn per changed role class, not a parse check.
- **Codex version skew.** The role schema is not documented and has moved repeatedly across 0.144 -> 0.146. Anything emitted must degrade to today's behavior on an older CLI rather than dropping the role. If `permissions` cannot satisfy that, not emitting it is the correct outcome.
- **A parent's live policy may outrank a child's role regardless.** #33314 records both directions of divergence; a narrowed child under a permissive parent may simply not be expressible. Verify against a `workspace-write` parent, which is the realistic flow-next case, not only a read-only one.
- **Self-report and parent narration are not evidence.** fn-98 burned three findings on this. Every verdict here comes from the child thread's own rollout, and a probe must distinguish a genuine block from a non-attempt (a role whose `developer_instructions` conflict with the task prompt produces non-attempts that read as blocks).
- Claude Code, Droid, Cursor and Grok behavior is unchanged by this spec; only the Codex mirror and the cross-host claims move.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** `sync-codex.sh:1650`'s enforcement claim is corrected in place, with the measured evidence (fn-98 P6: child-side `patch_apply` success under a role declaring `sandbox_mode = "read-only"`) cited next to it so a future reader cannot re-assert parity from the comment alone.
- **R2:** A live investigation determines whether `permissions` can express an enforced read-only file system for a spawned child under a `workspace-write` parent on codex-cli 0.146.0. The verdict is recorded in Decision Context with the exact TOML tried and the child-side rollout evidence, whichever way it lands. **A negative result closes this criterion**; it does not block the spec.
- **R3:** If and only if R2 is positive, read-only roles emit the verified `permissions` block, and `sync-codex.sh` gains a guard that fails the build when a canonical agent carrying `readonly: true` would emit a role without it.
- **R4:** `docs/platforms.md` states the guarantee per host explicitly: harness-enforced on Claude Code via `disallowedTools`; on Codex either enforced via `permissions` (if R2 positive) or **prompt-only and not sandbox-enforced** (if negative). The current text implying uniform coverage is replaced, not annotated.
- **R5:** The repo `CLAUDE.md` cross-platform "Agent permissions" bullet is corrected to match R4. It currently reads as though the blacklist translates cleanly to every host.
- **R6:** A regression guard exists for the silent-role-drop failure mode: the sync validation fails if any emitted role TOML contains a key outside the measured accepted set. This protects all 21 roles from a future one-key mistake regardless of how R2 lands.
- **R7:** No user-facing behavior change on Claude Code, Droid, Cursor or Grok. The Codex mirror regenerates idempotently (`sync-codex.sh` twice, clean second diff).

## Boundaries
<!-- scope: business -->

- **Not a security incident and must not be written as one.** No CVE framing, no urgency language in CHANGELOG or docs. The honest register is: we documented a guarantee we do not keep on one host, and we are correcting it.
- **No new abstraction over host permissions.** No capability layer, no per-host permission model, no config keys. If Codex cannot express it, the answer is a documented degradation, not an invention.
- **Not fn-98.** fn-98 owns steering docs currency and the fact-scout pin. This spec owns the read-only guarantee. They edit `platforms.md` for different reasons and should land in an order that avoids a conflicting rewrite of the same paragraph - see Decision Context.
- **No change to the canonical agent frontmatter.** `readonly: true` and `disallowedTools` stay exactly as they are; they are correct on the host that enforces them.
- **Not a scout-behavior audit.** Whether any scout has ever actually written a file is out of scope and is not the justification.

## Decision Context
<!-- scope: both -->

**Why act at all, given low severity.** The guarantee is stated in three places and enforced in one. The cost of leaving it is that a maintainer sizing blast radius on Codex gets a wrong answer from our own documentation, and the cost of fixing it is a comment, a paragraph, and a bounded investigation. That trade is obvious. The counter-argument - that nobody has been bitten - is exactly the argument that keeps latent documentation defects alive.

**Why `permissions` is the only candidate.** Measured: `tools`, `allowed_tools`, `disallowed_tools` are all rejected by the role deserializer, and rejection silently discards the role. `permissions` parses as an empty struct and rejects wrong inner types with a named struct (`PermissionProfileToml`), which means the field is real and typed rather than tolerated. That is a thin but genuine lead, and R2 exists to close it either way rather than to guarantee a fix.

**Why R2 is allowed to fail.** A negative result is a complete outcome here. The spec's value is in R1, R4, R5 and R6 - correcting the claim and preventing the catastrophic-but-silent regression - and those hold regardless. Writing the spec so that only a positive result counts would create pressure to ship a `permissions` block we have not actually verified, which is how the original false claim got written in the first place.

**Why R6 exists even though nothing today emits a bad key.** P11 showed the failure is silent and total: one unrecognized field removes every scout role and turns every dispatch into `unknown agent_type`. The schema is undocumented and has moved across three CLI releases. A guard is cheap; discovering this from a user report is not.

**Sequencing against fn-98.** Both touch `platforms.md`. fn-98's R2 rewrites the model-steering caveat; this spec's R4 rewrites the permissions claim. They are different paragraphs, but landing them concurrently invites a conflicting rewrite. Land fn-98 first (it is further along and its docs edit is larger), then this one on top.

**Evidence source.** All measurements are from the fn-98 probe matrix, 2026-08-03, codex-cli 0.146.0, run against a disposable `CODEX_HOME` so the maintainer's real config was untouched. Probes P6 (sandbox not enforced, child-side `patch_apply` success), P11 (unknown key silently discards the role), and the schema-acceptance sweep that identified `permissions` as the sole typed candidate.
