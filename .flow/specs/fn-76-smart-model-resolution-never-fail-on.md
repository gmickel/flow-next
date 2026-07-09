# fn-76 Smart model resolution — never fail on the default

## Goal & Context

flow-next injects a hardcoded model on every review backend's unconfigured path (`BACKEND_REGISTRY[<b>].default_model` + the `run_*_exec` fallback `spec.model or "<hardcoded>"`). A hardcoded default is structurally unable to know per-user, per-plan, per-org, per-CLI-version availability — fn-74 hit it twice (Finding A, T6), and the GPT-5.6 launch (2026-07-10) reproduced it live: `gpt-5.6-sol` worked on cursor, 400'd on codex CLI < 0.144 ("requires a newer version of Codex"), and was rejected by copilot 1.0.65 — three answers for one model string on one machine.

The fix is one principle: **when the user specified nothing, defer to the CLI's own default** — it is whatever the account is entitled to, so it cannot be unavailable. Explicit choices keep working exactly as today.

## Architecture & Data Models

Small, surgical, entirely in flowctl.py (dual-copied):

1. **Registry:** `default_model` → `None` (codex/copilot) / `"auto"` (cursor). The `models` sets stay as documentation/preference — see (3).
2. **Exec fallbacks:** `run_codex_exec` omits `--model` when `spec.model` is `None`; `run_copilot_exec` passes `--model auto` (probed in fn-74: lets the CLI pick); `run_cursor_exec` passes `--model auto` (first-class list entry). No other exec changes.
3. **Lenient model validation:** `BackendSpec.parse` accepts an unknown model with a stderr warning instead of rejecting — the CLI is the availability authority; the registry set becomes preference/documentation (kills the every-model-launch release treadmill, e.g. 2.10.3). The effort axis stays strict.
4. **Effort guard:** when the resolved model is `None`/`auto`, omit `--effort`/effort suffixes (can't know the family's effort support).
5. **Receipt honesty:** receipts record the model actually used when parseable from CLI output, else the literal `"auto"`/`"default"` — never a fabricated concrete name.

## API Contracts

- Unconfigured path (no `--spec`, no per-task/per-spec `review`, no `FLOW_*_MODEL`, no config model): resolved `BackendSpec.model` is `None` (codex/copilot) or `"auto"` (cursor); the exec argv contains no hardcoded model string.
- Explicit model anywhere in the precedence chain: byte-identical behavior to today.
- `BackendSpec.parse("<backend>:<unknown-model>")`: accepted + one-line warning. Effort parsing unchanged (strict).
- Receipt `model` field: actual model when determinable, else `"auto"`/`"default"`.

## Edge Cases & Constraints

- Effort-folded cursor model ids (`gpt-5.6-sol-high`): `auto` carries no effort — nothing to strip.
- Ralph/headless: no behavior change (resolution is pure string logic; no new probes, no network).
- The 2.10.3 interim (cursor default `gpt-5.6-sol-high`) is REPLACED by `auto` on the unconfigured path; users who want a pinned strong model set it explicitly (setup/docs show how).
- Backward-compat: stored explicit specs (`review.backend`, per-task `review:`) resolve unchanged.

## Acceptance Criteria

- [ ] **R1:** With no model configured anywhere, each backend's exec argv carries no hardcoded model (codex: `--model` absent; copilot/cursor: `auto`) — asserted by deterministic unit tests on argv construction (mocked exec), per backend.
- [ ] **R2:** `BackendSpec.parse` warns-and-accepts unknown models (effort stays strict); the registry `models` sets no longer parse-time-reject; covered by unit tests.
- [ ] **R3:** Effort is omitted when the model is `None`/`auto`; receipts record actual-or-`"auto"`, never a fabricated name; unit-tested.
- [ ] **R4:** Full suite + smoke green; flowctl dual-copy byte-parity; Codex mirror regenerated; docs updated (flowctl.md model-resolution paragraph + troubleshooting "model not available" entry now points at explicit-pin guidance).

## Boundaries

- Out (deferred, were fn-76 R2-R4 in the fat version): a `flowctl <backend> models` probe command; `/flow-next:setup` model-discovery ceremony; fail-soft retry on model-unavailable for *explicitly configured* models (a clear CLI error + re-pick is acceptable; retry machinery is not worth its weight until field evidence says otherwise).
- Out: BYOK/custom providers; mid-review model switching; review rubric/receipt schema changes beyond the `model` field semantics.

## Decision Context

Why defer to the CLI default on the unconfigured path: it is the only model guaranteed available (it IS the user's entitlement), eliminating the "model not available on the happy path" class entirely. We reject keeping a hardcoded `default_model` because it is structurally unable to know per-user entitlement and drifts every CLI release — the direct cause of fn-74's Finding A + T6.

Trade-off accepted: `auto`/CLI-default may pick a weaker model than a curated pin. Recovery is the explicit layer (per-task `review:`, `review.backend`, env) — which always wins and is documented; the probe/setup-discovery layer from the original fat spec is deferred until wanted.

**Slimming decision (2026-07-10):** original spec carried a models-probe CLI, setup integration, and fail-soft retry (8 R-IDs). Cut to 4: with native defaults the unconfigured path cannot model-fail, so the retry protects only explicit misconfiguration (clear error suffices), and the probe/setup layer is quality-of-life, not the never-fail property. Everything kept is deterministically smoke-testable at the argv layer — no live CLI calls in the gate.

**Interim quick fix shipped 2.10.3 (2026-07-10, GPT-5.6 launch):** cursor default bumped to the live-verified `gpt-5.6-sol-high`; `gpt-5.6-sol` added to codex's accepted set (explicit use, CLI ≥ 0.144) — but codex/copilot DEFAULTS deliberately stayed `gpt-5.5` because live probes showed both reject `gpt-5.6-sol` on current CLIs (codex 0.142: "requires a newer version of Codex"; copilot 1.0.65: "not available"). That probe result is this spec's thesis demonstrated live. This spec supersedes the interim: the cursor pin gives way to `auto`.
