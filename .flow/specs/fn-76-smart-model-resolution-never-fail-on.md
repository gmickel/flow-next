# fn-76 Smart model resolution for review backends

## Goal & Context

flow-next injects a hardcoded model for every review backend — `BACKEND_REGISTRY[<b>].default_model` plus the `run_*_exec` fallback `effective_model = spec.model or "<hardcoded>"`. This assumes one model is universally available. It is not. Availability varies along three independent axes:

1. **CLI version** — Copilot CLI 1.0.65 dropped `gpt-5.2` ("Model not available").
2. **Subscription tier** — Cursor Pro vs free; Copilot Free/Pro/Business.
3. **Org policy** — Copilot Business/Enterprise can whitelist a subset of models per organization.

When flow-next's guessed default falls outside a given user's intersection, the CLI 400s and the review fails on the happy path. fn-74 hit this twice: **Finding A** (copilot receipts stamped the unavailable `gpt-5.2`) and **T6** (Ralph's `FLOW_COPILOT_MODEL=gpt-5.2`). The static registry `models` set compounds it — a hard parse-time gate that drifts every CLI release and can never reflect per-user entitlement.

Target user: anyone whose Copilot/Cursor plan or org policy lacks flow-next's guessed default. Today they get an opaque failure on the default path with no path forward.

## Architecture & Data Models

Resolution flows: `resolve_review_spec(backend_hint, task_id, return_source)` → `_resolve_<backend>_review_spec` → `run_<backend>_exec`, with `effective_model = spec.model or "<default>"`.

Model-introspection reality (probed in fn-74):
- **cursor-agent** — `cursor-agent models` / `--list-models` returns the **account-available** list; `auto` is a first-class entry ("Auto (current)").
- **copilot** — `--model auto` lets the CLI pick an available model; no scriptable list (only interactive `copilot -i "models"`); BYOK `providers` exist.
- **codex** — `-m/--model`; no list command; omitting `--model` uses the account's configured default.

Layered resolution to add:
- **Probe helper** `flowctl <backend> models` wrapping the CLI list where supported; degrades to `supported:false` elsewhere.
- **Resolution policy**: explicit model (`--spec`/per-task/per-spec/env/config) > stored smart default (setup) > **CLI native/auto default** (never a hardcoded-may-fail model on the unconfigured path).
- **Fail-soft wrapper** around the exec call: detect "model unavailable", retry once with auto/default.
- **Registry `models` set → preference/known list**, not a hard validation gate.

## API Contracts

- `flowctl <backend> models [--json]` → `{supported: bool, models: [{id, current?}]}` from the CLI probe (cursor real list; copilot/codex `supported:false`). Never crashes offline/headless.
- Unconfigured default path: when no model is specified anywhere, the resolved `BackendSpec.model` is `None`/`"auto"` and `run_*_exec` omits `--model` (codex) or passes `auto` (copilot/cursor) — never a hardcoded specific model.
- `run_*_exec` surfaces a distinct **model-unavailable** signal (stderr token / sentinel exit) so the caller can trigger the one-shot fail-soft retry.
- Receipt `model` = the model actually used, parsed from CLI output when determinable, else `"auto"`/`"default"` — never a fabricated name.
- `BackendSpec.parse("<backend>:<unknown-model>")` → warns + accepts on the model axis; effort axis stays strict.

## Edge Cases & Constraints

- Receipt model accuracy under `auto`: parse each backend's output for the resolved model; record `"auto"` when unparseable.
- Effort when model unknown/auto: omit `--effort` (can't know the family's effort support — Claude-family models reject it).
- Fail-soft must not loop: at most one retry with auto/default, then a clear actionable error.
- The `models` probe shells the CLI (network/auth dependent) — degrade to `supported:false`/empty in headless/offline/Ralph runs without crashing.
- Cross-platform: copilot Windows stdin + marker session logic unaffected; codex mirror regenerated.
- Backward-compat: existing `--spec backend:model:effort` and per-task/per-spec `review` behavior unchanged; ONLY the unconfigured-default path changes.

## Acceptance Criteria

- **R1:** When no model is specified anywhere (no `--spec`, no per-task/per-spec `review`, no `FLOW_*_MODEL`, no config model), the review runs on the CLI's native/auto default (copilot `--model auto` or omit; cursor `auto`; codex omit `--model`) — never a hardcoded model that can 400. A user whose plan lacks the old default can run a default review successfully.
- **R2:** `flowctl <backend> models [--json]` returns the CLI's account-available list where supported (cursor) and `supported:false` where not (copilot/codex), without crashing offline/headless.
- **R3:** `/flow-next:setup`, when configuring a backend, uses R2 to discover available models and suggests a strong default from a flow-next preference order ∩ availability, storing the user's choice; where no list exists, it offers `auto` + an explicit-model option.
- **R4:** A configured/explicit model the CLI rejects ("Model not available") triggers exactly one fail-soft retry with the CLI default/auto + a visible warning; the review produces a verdict instead of hard-failing. The unavailable case is detected via a backend-specific signal, not a generic non-zero.
- **R5:** Model validation is lenient — `BackendSpec.parse` accepts an unknown model with a warning (CLI is the source of truth); the effort axis stays strict. The registry `models` set is documentation/preference, not a parse-time reject.
- **R6:** When the resolved model is unknown/auto, `--effort` is omitted (no effort guess on an unknown model family).
- **R7:** The receipt records the model actually used (parsed from CLI output when determinable, else `"auto"`/`"default"`), never a fabricated name.
- **R8:** Tests cover R1–R7 per backend; flowctl byte-parity holds; the codex mirror is regenerated; docs (flowctl.md model-resolution, setup, troubleshooting) updated.

## Boundaries

- NOT changing the review rubric / Carmack-level criteria / receipt schema beyond the `model` field semantics.
- NOT implementing per-spec `default_review` resolution (PR #184 thread T3 — separate `resolve_review_spec` enhancement).
- NOT building BYOK / custom-provider (`copilot providers`) support — note it exists; defer.
- NOT scraping interactive CLI UIs from flowctl for codex/copilot model lists (the setup skill MAY probe interactively as host-agent judgment; flowctl stays deterministic).
- NOT auto-switching models mid-review or A/B-testing.

## Decision Context

Why defer to the CLI's native/auto default on the unconfigured path: it is the only model guaranteed available (it is whatever the user is entitled to), eliminating the entire "Model not available on the happy path" class. We reject keeping a hardcoded `default_model` because it is structurally unable to know per-user entitlement and drifts every CLI release — the direct cause of Finding A + T6 in fn-74.

Trade-off: `auto`/CLI-default may pick a cost-optimized (weaker) model, lowering review quality. We recover quality with Layer 2 (introspect the available set where the CLI allows — cursor does — and pick the strongest, surfaced at setup) and Layer 3 (explicit override always wins). Robust floor (R1) + smart layer (R3) = "never fails, and as strong as the plan allows."

Why lenient validation (R5): the static registry set is authoritative about neither availability (per-user) nor the CLI's current catalog (per-version); a hard gate produces both false rejects (a model the user has) and stale allows (a model the CLI dropped). The CLI is the only authority; flow-next's role is preference + graceful failure, not gatekeeping.

cursor is the only backend with a scriptable, account-aware model list, so it gets the richest treatment (R2/R3 real list); copilot and codex lean on `auto` + fail-soft (R1/R4) until their CLIs expose a list.
