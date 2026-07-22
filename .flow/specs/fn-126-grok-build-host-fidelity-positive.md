## Goal & Context

Grok Build (xAI's `grok` CLI) is a verified-compat host that reads the canonical Claude plugin format directly. Dogfood (2026-07-22, grok-dogfood-330) found it **undetected** by the `/flow-next:setup` platform cascade: it falls through the `else -> codex` catch-all, so setup wrote the docs snippet to `AGENTS.md` with **`$flow-next-setup`** (Codex `$` command syntax) even though Grok drives with **`/flow-next-setup`** (slash) and reads the canonical Claude files, not the Codex mirror. Setup otherwise ran fine (copy mode, flowctl via `.flow/bin`, model-routing scaffold written, AskUserQuestion rendered).

The original spec assumed Grok exposed **no** host signal (so it planned a heavy investigation gate + a manual-host-selection fallback). A follow-up non-interactive probe **disproved that**: there is a clean positive signal. This spec is now small: add a `GROK_AGENT` detection rung + a Grok host profile, mirroring the existing Cursor rung.

## Investigation outcome (RESOLVED — 2026-07-22, non-interactive probe)

Ran a probe script inside a real grok session (`grok --always-approve -m grok-4.5 -p "run probe.sh > /tmp/out"`) and diffed its shell environment against a plain-shell control on the same machine/profile:

- **`GROK_AGENT=1` is set in grok's shell environment** and is ABSENT from the plain-shell control. It is set BY grok (not the user's profile). This is the direct analog of `CURSOR_AGENT` / `CLAUDECODE` / `CLAUDE_PLUGIN_ROOT`.
- Corroborating: the process ancestry from grok's shell shows a `grok` process in the chain (second signal if the env var ever regressed).
- Rejected non-signals (confirmed against the control): `~/.grok/` directory EXISTS on the machine regardless (install dir), and `~/.grok/bin` is on `PATH` regardless (shell profile) — neither distinguishes a grok session. Fable's caution was right; only `GROK_AGENT` survives.
- Test-method caveat: the probe launched grok FROM a Claude Code shell, so grok's env also inherited `CLAUDECODE=1` etc. — a standalone grok session won't have those. Crucially `CLAUDE_PLUGIN_ROOT` (the actual cascade key) did NOT propagate, so the existing Claude rung does not misfire. A standalone-session confirmation is a NEEDS-HUMAN smoke (R1).

## Architecture & Data Models

- Grok reads canonical Claude files AS-IS (like Cursor) and drives with `/flow-next-` slash commands (NOT the Codex `$flow-next-` mirror). So its correct profile is the slash/Claude profile, copy mode, CLAUDE.md docs target.
- `GROK_AGENT=1` is the detection signal; add the rung before `else -> codex`, ordered after the existing higher-precedence host checks (DROID/CLAUDE/CURSOR) so an agent that merely inherited `GROK_AGENT` from a parent grok shell is not misclassified.
- Grok's only NATIVE model family is grok (`grok models` returns just `grok-4.5`). So a native `host` review on Grok is single-family and behaves exactly like Claude Code's: it fails closed (ask / NEEDS_HUMAN) unless the writer is non-Grok. Cross-family review on Grok comes through the bridge backends (`codex`/`cursor`/`copilot`), not a native subagent.

## Acceptance Criteria

- **R1:** Setup adds a positive `elif [ -n "${GROK_AGENT:-}" ]` -> `PLATFORM=grok` rung BEFORE the `else -> codex` fallback and AFTER the DROID/CLAUDE/CURSOR rungs (precedence: a real Droid/Claude/Cursor host that inherited `GROK_AGENT` from a parent grok process still classifies correctly). Investigation evidence (`GROK_AGENT=1`) recorded in the spec. NEEDS-HUMAN smoke: in a STANDALONE grok session (not launched from another agent), `/flow-next:setup` reports platform=grok. [user]
- **R2:** On `PLATFORM=grok`, setup writes the docs snippet with `/flow-next-` slash syntax to `CLAUDE.md` (canonical target), copy mode, `.flow/bin/flowctl`, NO `.codex/agents` copy, NO Ralph offer/registration. A pre-existing wrong Codex `$flow-next-` snippet block is consent-refreshed to the slash form, marker-scoped (text outside the markers untouched). [user]
- **R3:** Grok review-backend menu offers `host` (with the existing fail-closed cross-family caveat) alongside the external backends (rp/codex/copilot/cursor/none); the host-native model-routing scaffold (currently `PLATFORM=cursor`-gated) extends to `platform=grok`, enumerating Grok's available models at setup. Docs state the honest single-family behavior: native `host` on Grok fails closed unless the writer is non-Grok; cross-family comes via bridge backends. [user]
- **R4:** An EXECUTABLE detection test (extract the Step-0 fenced bash, run under fake-env fixtures): `GROK_AGENT=1` -> `grok`; inherited-env / precedence cases classify correctly; no regression to Droid/Claude/Cursor/Codex. `scripts/sync-codex.sh` renders a real Codex host deterministically as `codex` (the mirror cascade carries no Grok rung), enforced by a hard-fail sync guard; sync twice-idempotent. [inferred]
- **R5:** Downstream: `plugins/flow-next/docs/platforms.md` + flow-next.dev + vault `Platforms & Install` note state the Grok profile (GROK_AGENT detection, slash syntax, canonical files, copy mode, review incl. host, no-Ralph). Command-discovery gap validated now that fn-124 (command-shim flatten) has landed — record fixed-by-fn-124 or a linked residual follow-up (no double-fix). CHANGELOG `## [Unreleased]` + docs-site `## Unreleased`; NO version bump (batched). [paraphrase]

## Boundaries

- Positive detection via `GROK_AGENT` — the earlier manual-host-selection / no-signal fallback and its interactive Grok-vs-Codex ask are DROPPED (a reliable signal exists). [user]
- Command-discovery gap coordinates with fn-124 (now landed); validate only, do not re-implement shim flattening. [user]
- No Ralph on Grok (same posture as Cursor). [user]
- Cross-family `host` review keeps its fail-closed contract; do not imply a native cross-family reviewer exists on single-family Grok. [user]

## Decision Context

### Motivation

- Direct fn-123/dogfood follow-up: Grok was advertised as a verified host but setup mis-shaped its instructions (Codex `$` syntax) because it was undetected. The probe found `GROK_AGENT=1`, so the fix is a clean positive rung, not a fallback. Correctness gap; smaller than first planned. [user]
- Grok single-native-family (grok-4.5) means `host` review mirrors the Claude Code semantics already shipped in fn-123. [user]

## Requirement coverage

| R-ID | Task |
|------|------|
| R1 | fn-126-grok-build-host-fidelity-positive.1 |
| R2 | fn-126-grok-build-host-fidelity-positive.1 |
| R3 | fn-126-grok-build-host-fidelity-positive.1 |
| R4 | fn-126-grok-build-host-fidelity-positive.2 |
| R5 | fn-126-grok-build-host-fidelity-positive.3 |
