## Goal & Context

Grok Build (xAI's `grok` CLI) is listed as a verified-compat host that reads the canonical Claude plugin format directly. Dogfood (2026-07-22, grok-dogfood-330) found it is **undetected** by the flow-next-setup platform cascade and falls through the `else -> codex` catch-all, so it is treated as Codex.

Impact (confirmed): `/flow-next-setup` on Grok wrote the docs snippet to **AGENTS.md** with **`$flow-next-setup`** (Codex command syntax) - but Grok drives with **`/flow-next-setup`** (slash form, like Cursor/Claude) and reads the canonical Claude files, NOT the Codex mirror. So the written guidance tells the agent to invoke commands the wrong way. Setup otherwise ran fine (copy mode, flowctl via `.flow/bin`, model-routing scaffold written). A second, likely-separate symptom: Grok's slash-command menu under-lists flow-next commands ("can't find flow-next-setup / analyse") - probably the fn-124 command-shim structure issue.

Detection is the hard part: `env | grep -iE 'grok|xai'` in a Grok session shows **no host env var** (only `~/.grok/bin` on PATH and shell completions) - unlike Cursor (`CURSOR_AGENT`), Droid (`DROID_PLUGIN_ROOT`), or Claude (`CLAUDE_PLUGIN_ROOT`). So the env-var cascade cannot cleanly catch Grok, and it precedes `codex` only if a positive signal exists.

## Architecture & Data Models

- Grok reads canonical Claude files as-is (no rewrite pass), like Cursor - so its correct treatment is the SLASH-command / Claude-file profile, not the Codex `$`-command / mirror profile. [paraphrase]
- The blocker is a reliable positive discriminator. Candidates to investigate (INVESTIGATION-FIRST task): a Grok-specific env var not matched by the grok/xai grep (widen the probe); a `~/.grok/` marker; the `grok` binary resolving on PATH combined with absence of the other host signals; a version/capability probe. Fragile PATH-substring matching is a last resort. [inferred]

## Acceptance Criteria

- **R1:** INVESTIGATION: determine whether a Grok Build session exposes ANY reliable positive signal (env, marker file, process ancestry) distinguishing it from a bare Codex/other session. Document the finding; if none exists, the spec's later ACs adapt (e.g. a setup question, or accept the limitation with a corrected fallback). [user]
- **R2:** If a signal exists, add a positive `grok` detection rung to the flow-next-setup cascade BEFORE the `else -> codex` fallback, without regressing Claude/Droid/Cursor/Codex classification (fixture matrix incl. Grok, Codex, and Codex-launched-from-a-Grok-shell if that inherits anything). [paraphrase]
- **R3:** On `platform=grok`, setup writes the docs snippet with the correct **`/flow-next-...` slash** command syntax (Claude/Cursor profile) to the right instruction file, NOT the Codex `$flow-next-...` form; copy mode, `.flow/bin/flowctl`, host-aware review menu + model-routing scaffold as for other copy-mode hosts. [user]
- **R4:** Command-discovery gap assessed and either fixed here or explicitly folded into fn-124 (flatten command shims) - confirm whether Grok's under-listing shares the shim-structure root cause. [paraphrase]
- **R5:** Docs updated (platforms.md + flow-next.dev + vault Platforms note): Grok's actual profile (slash commands, canonical files, copy mode, review backends incl. host) and any detection caveat. [paraphrase]
- **R6:** If R1 finds NO reliable signal, ship the honest fallback instead: document that Grok is manually selectable / treated as a slash-command copy-mode host, and correct the wrong-syntax outcome rather than leaving it as codex. [user]

## Boundaries

- Investigation-gated: do NOT hardcode a fragile detector without R1 evidence. [user]
- Command-discovery gap coordinates with fn-124; avoid double-fixing. [user]
- No Ralph on Grok (same posture as Cursor). [inferred]

## Decision Context

### Motivation

- Direct fn-123/dogfood follow-up: Grok is advertised as a verified host but setup mis-shapes its project instructions (Codex `$` syntax) because it is undetected. Correctness gap, higher priority than the fn-125 cost gap. [user]

## Requirement coverage

| R-ID | Task |
|------|------|
| R1 | fn-N.M (TBD - populate via /flow-next:plan) |
| R2 | fn-N.M (TBD - populate via /flow-next:plan) |
| R3 | fn-N.M (TBD - populate via /flow-next:plan) |
| R4 | fn-N.M (TBD - populate via /flow-next:plan) |
| R5 | fn-N.M (TBD - populate via /flow-next:plan) |
| R6 | fn-N.M (TBD - populate via /flow-next:plan) |
