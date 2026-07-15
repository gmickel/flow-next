# fn-96 Setup self-heal: silent flowctl + usage.md re-copy on version drift

## Goal & Context
<!-- scope: business -->

Flow-Next copies its runtime into each repo as **snapshot files, not live links**: `.flow/bin/flowctl` (+ `flowctl.cmd`, `flowctl.py`), `.flow/usage.md`, and `.flow/templates/spec.md`. A plugin upgrade refreshes the plugin but leaves those copies frozen at whatever version last ran `/flow-next:setup`. The worst symptom is a hard break: a skill calls a `flowctl` subcommand/flag the stale local binary doesn't have yet. This repo itself sat at `setup_version` 2.6.0 against a 2.12.x plugin for weeks unnoticed.

fn-95 (shipped 2.12.4) fixed **surfacing** — an interactive once-per-version blocking ack, an autonomous `SETUP_STALE` verdict line. It did not fix the **mechanism**: the user still has to manually re-run setup to stop things breaking.

This spec silently self-heals the byte-identical internal snapshots so staleness never surfaces as a broken flag, and reframes the manual re-run as *feature adoption* (refresh the CLAUDE.md model-routing scaffold, adopt new setup capabilities) rather than break-fix.

**Key premise established this session:** `.flow/usage.md` is an **agent-facing internal reference** (flowctl help, the `.flow/` file map, orchestration bridge recipes — line 1: "Task tracking for AI agents"). It is NOT a user-customization surface — the user-tunable model-routing table/rules live in `CLAUDE.md`/`AGENTS.md` via the marker-fenced scaffold, a separate surface. So usage.md is safe to overwrite exactly like `flowctl.py`. `.flow/templates/spec.md` is the same: setup already `cp`s it unconditionally (Step 4, no gate); the customization surface is a repo-root `SPEC.md` via the cascade. All three self-heal identically.

## Architecture & Data Models
<!-- scope: technical -->

**Self-heal set (byte-identical internal snapshots setup copies unconditionally):**
- `.flow/bin/flowctl`, `.flow/bin/flowctl.cmd`, `.flow/bin/flowctl.py` (+ `chmod +x` on the bash launcher)
- `.flow/usage.md`
- `.flow/templates/spec.md`

**NOT self-healed (genuine user surfaces, keep setup's merge gate):** the `CLAUDE.md`/`AGENTS.md` model-routing block (marker-fenced merge) and a repo-root `SPEC.md` (byte-compare Keep-mine/Overwrite gate). These require human judgment; self-heal never touches them.

**Where it lives.** The self-heal `cp` block is added to the shared `## Pre-check: Local setup version` block that already exists in 17 SKILL.md files (capture, audit, land, interview, memory-migrate, make-pr, pilot, prime, plan, resolve-pr, prospect, ralph-init, strategy, qa, sync, work, tracker-sync). It runs **inside the existing `SETUP_VER != PLUGIN_VER` branch** — the same branch fn-95's compare already gates — and executes **before** the surfacing (ask / echo / verdict) logic.

**Cost.** Zero added work on the version-match hot path: the `cp`s live behind the existing rare mismatch branch. On mismatch, cost is bounded local file copies (~1.3MB flowctl.py, milliseconds). Everything fail-open: a missing plugin root, unreadable source, or read-only `.flow/` continues the skill silently.

**setup_version is NOT bumped by self-heal.** Self-heal fixes the mechanical snapshots but does not run the full ceremony (CLAUDE.md scaffold refresh, SPEC.md offer, tracker prompt). Leaving `setup_version` stale keeps fn-95's once-per-version ask armed — which is now the *calm feature-adoption prompt* ("new version, refresh scaffold / adopt features?") instead of a break-fix alarm, because nothing is broken anymore. `version_ack` still suppresses re-nagging.

**Concurrency.** Two skills self-healing at once both `cp` identical bytes to the same targets; a racing double-copy is harmless (same content). No temp-file/atomic-rename ceremony needed; keep it a direct `cp`, fail-open.

## API Contracts
<!-- scope: technical -->

No new flowctl subcommand, no flag, no schema change. Pure skill-prose + bash addition inside the pre-check block. Copy source is `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` (the cross-platform fallback the pre-check already uses); targets are the fixed `.flow/` paths above. `sync-codex.sh` regenerates the Codex mirror (the added `cp` lines carry verbatim; only the surrounding `AskUserQuestion` prose is rewritten, unchanged by this spec).

## Edge Cases & Constraints
<!-- scope: technical -->

- **Fail-open everywhere.** Any `cp`/`chmod` error (missing source, read-only `.flow`, missing plugin root env) must not interrupt or fail the skill — swallow and continue, exactly as the surrounding pre-check already does.
- **No plugin root** (`CLAUDE_PLUGIN_ROOT`/`DROID_PLUGIN_ROOT` unset, e.g. Cursor) — the source path is unresolvable; self-heal is a silent no-op, skill continues. (Cursor already resolves flowctl via `.flow/bin`; its update path is the one-shot installer, unaffected.)
- **Symlinked `.flow/`** (common — see 2.5.0 learnings): `cp` follows into the real target; harmless.
- **Dual-copy invariant** (`plugins/flow-next/scripts/flowctl.py` == `.flow/bin/flowctl.py`) is unaffected — self-heal copies FROM the plugin scripts dir, the canonical side.
- **usage.md gate removal** must not break `/flow-next:uninstall` (still removes `.flow/usage.md`) nor the dogfood parity test (`.flow/usage.md` still byte-matches the template).

## Acceptance Criteria
<!-- scope: both -->

- R1: The shared `## Pre-check: Local setup version` block, inside its existing `SETUP_VER != PLUGIN_VER` branch and before any surfacing output, silently re-copies `flowctl`, `flowctl.cmd`, `flowctl.py`, `.flow/usage.md`, and `.flow/templates/spec.md` from the plugin root to `.flow/`, and `chmod +x .flow/bin/flowctl`. Present and identical across all 17 pre-check skills.
- R2: Self-heal is fully fail-open: missing plugin root, unreadable source, or read-only `.flow/` continues the skill with no error and no interruption; on the version-match path it adds no work at all.
- R3: Self-heal does NOT write `setup_version` or `version_ack`; fn-95's once-per-version ask and the autonomous `SETUP_STALE` line are unchanged and still fire for the human-gated remainder.
- R4: Setup's `.flow/usage.md` handling is simplified to an **unconditional overwrite** (matching how `templates/spec.md` is already copied); the Keep-mine/Overwrite/abort question for usage.md is removed. Uninstall and the dogfood parity test still pass.
- R5: Cross-platform: copies use the `${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}` fallback; the Windows `flowctl.cmd` is included; the Codex mirror is regenerated via `sync-codex.sh` and carries the `cp` lines verbatim.
- R6: A test asserts the self-heal copy lines are present in the pre-check block of all 17 skills (or of the canonical source if the block is de-duplicated), and that setup no longer emits the usage.md Keep-mine prompt.
- R7: Docs updated in the same workstream — repo: README "after every update" section, `docs/troubleshooting.md`, `docs/architecture.md` snapshot-copy note (self-heal now covers the internal snapshots; manual re-run = adopt scaffold/features). flow-next.dev: `install.mdx` (top callout + `## Updating`), `skills/setup.mdx` ("Why scripts, not symlinks"). Both changelogs get an `## Unreleased` / docs-site entry.

## Boundaries
<!-- scope: business -->

- **In:** silent self-heal of the byte-identical internal snapshot set; usage.md gate simplification; the docs reframe (self-heal + feature-adoption); Codex mirror regen; tests.
- **Out — explicitly deferred:** the changelog-delta "here's what's new since your setup_version, re-run to adopt" itemized pitch. Worthwhile but separable; leave fn-95's generic ask as-is for now. Capture as a follow-up if wanted.
- **Out:** any change to detection cost/posture, receipts schema, or a new flowctl subcommand. No auto-*running* of setup from another skill (self-heal copies files; it does not execute the ceremony). No touching CLAUDE.md/AGENTS.md model-routing block or repo-root SPEC.md. No `setup_version` bump on self-heal. No plugin version bump in this spec's commits (batched per CLAUDE.md; land under `## Unreleased`).

## Decision Context
<!-- scope: both — conditionally substructured -->

- **Why usage.md can be silently overwritten (reversing the earlier hash proposal).** An earlier idea guarded usage.md with a provenance hash (silent-update only if untouched). That was unnecessary once we confirmed usage.md is internal (agent-facing reference, line 1 "Task tracking for AI agents") with no user-customization surface — the user knob is the CLAUDE.md/AGENTS.md scaffold, separately gated. No hash, no per-file logic: treat usage.md exactly like flowctl.py.
- **Why version-string compare, not byte-`cmp`.** The gate is fn-95's existing `setup_version != plugin_version` check — three tiny jq reads. Never `cmp` a 1.3MB file on the hot path; a version mismatch reliably means the snapshots are from a different plugin build, which is exactly when to re-copy.
- **Why NOT bump setup_version.** Self-heal only refreshes mechanical snapshots, not the full ceremony (scaffold/SPEC.md/tracker). Bumping would falsely claim a full setup ran and would silently suppress fn-95's adoption prompt. Leaving it stale is correct: nothing breaks (self-heal handled that), and the once-per-version ask becomes a calm feature-adoption nudge.
- **Why include templates/spec.md.** Setup already copies it unconditionally (no gate) — it is the same byte-identical-internal category as flowctl/usage.md, and excluding it would leave one snapshot drifting while the others self-heal. Consistency.
- **Relationship to fn-95.** Complementary, not a reopen. fn-95 (done, released 2.12.4) surfaces the mismatch; fn-96 heals the mechanical half so the surfaced remainder is purely opt-in feature adoption.
