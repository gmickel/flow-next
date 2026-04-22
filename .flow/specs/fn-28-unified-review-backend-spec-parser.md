# Unified Review Backend Spec Parser (model + effort)

## Overview

Generalize the review-backend spec vocabulary across all backends. Today `--review=codex:gpt-5.4-high` is documented in argparse help but stored as an opaque string — nothing parses it, nothing threads the model or effort to runtime. Runtime config is env-var only (`FLOW_CODEX_MODEL`, `FLOW_COPILOT_MODEL`, `FLOW_COPILOT_EFFORT`).

This epic introduces a structured `parse_backend_spec()` helper, validates specs on store, threads parsed `(backend, model, effort)` through to `run_codex_exec` / `run_copilot_exec`, and makes per-task / per-epic model pinning actually functional.

Depends on fn-27 landing first (copilot runtime needs to exist before its spec can be validated). Pure refactor + extension once fn-27 is in.

## Scope

- New `parse_backend_spec(spec: str) -> BackendSpec` helper in `flowctl.py`
- New `BackendSpec` typed dict / namedtuple: `{backend, model, effort}` (effort optional for backends that don't support it)
- Per-backend registry of valid models + valid effort levels (validation surface)
- Update `cmd_epic_set_backend` / `cmd_task_set_backend` to validate specs on store (reject unknown backend, unknown model, unknown effort; preserve case)
- Update `cmd_task_show_backend` to display parsed form + source
- Update `cmd_review_backend` to accept and return a spec string (not just bare backend), preserving env-var cascade
- Thread parsed `model` + `effort` through to `run_codex_exec` and `run_copilot_exec`, keeping env-var override behavior
- Update skill-level callers that branch on backend string to accept spec-form input
- Update help text to match implementation
- Update Ralph templates + config to accept spec-form `WORK_REVIEW` / `PLAN_REVIEW` values (e.g. `codex:gpt-5.4:high`, `copilot:claude-opus-4.5:xhigh`)
- Add tests for parser edge cases (empty, unknown backend, unknown model, wrong effort, bare backend, backend+model no effort, full three-part)
- Update docs: CLAUDE.md project guide, plugin READMEs, ralph runbooks

## Approach

### Key Design Decisions

1. **Spec grammar**: `backend[:model[:effort]]` — colon-delimited, three parts max, trailing parts optional.
   - `rp` — backend only
   - `codex` — backend only
   - `codex:gpt-5.4` — backend + model, default effort
   - `codex:gpt-5.4:high` — full spec
   - `copilot:claude-opus-4.5:xhigh` — copilot with its unique `xhigh` effort
   - Rejected: `codex:gpt-5.4-high` (ambiguous — is it model `gpt-5.4-high` or model `gpt-5.4` + effort `high`?). We break from the current aspirational help text because it was never implemented; no migration needed.

2. **Resolution precedence** (most specific wins):
   1. Per-task `review` field (from `.flow/tasks/<id>.json`)
   2. Per-epic `default_review` field (from `.flow/epics/<id>.json`)
   3. `FLOW_REVIEW_BACKEND` env var (can be full spec, e.g. `codex:gpt-5.4:high`)
   4. `.flow/config.json` `review.backend`
   5. `FLOW_CODEX_MODEL` / `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` (backend-specific env var overrides for fields not in the resolved spec)
   6. Backend default

   Rationale: per-task beats per-epic beats session env beats config beats backend-specific env beats hard-coded default. Backend-specific env vars (`FLOW_CODEX_MODEL` etc.) stay for one-off runs without touching spec.

3. **Validation at store time, not runtime.** `cmd_epic_set_backend` and `cmd_task_set_backend` validate the spec against the registry and reject invalid values with a helpful error (`Error: 'codex:gpt-6' is not a valid backend spec. Valid codex models: gpt-5.4, gpt-5.2, ...`). Runtime trusts what's stored.

4. **Backend registry** is a static dict in flowctl.py — no plugin system, no discovery. When a new backend lands, registry grows by one entry.

   ```python
   BACKEND_REGISTRY = {
       "rp": {
           "models": None,  # RP uses window/session, not per-call model
           "efforts": None,
       },
       "codex": {
           "models": {"gpt-5.4", "gpt-5.2", "gpt-5-mini", ...},
           "efforts": {"none", "minimal", "low", "medium", "high", "xhigh"},
           "default_model": "gpt-5.4",
           "default_effort": "high",
           # Caveat: `minimal` passes codex config validation but server-side rejects
           # with 400 when web_search tool is enabled. Safe for flowctl reviews (no
           # web_search enabled), but document the gotcha.
       },
       "copilot": {
           "models": {"claude-sonnet-4.5", "claude-haiku-4.5", "claude-opus-4.5", "claude-sonnet-4", "gpt-5.2", "gpt-5.2-codex", "gpt-5-mini", "gpt-4.1"},
           "efforts": {"low", "medium", "high", "xhigh"},
           "default_model": "gpt-5.2",
           "default_effort": "high",
       },
       "none": {
           "models": None,
           "efforts": None,
       },
   }
   ```

5. **RP gets only `backend` form.** RP doesn't have per-call model or effort (model is determined by the RP window configuration). Spec `rp:anything` rejected. `rp` accepted.

6. **Receipt schema: additive change.** fn-27 already writes `model` + `effort` into receipts. fn-28.3 additionally stamps a new `spec` field (`str(resolved_spec)`) as the canonical round-trippable form. `model` + `effort` remain for backward compatibility; readers tolerant of missing `spec` stay correct. <!-- Updated by plan-sync: fn-28.3 added `spec` field; original claim "unchanged" was aspirational -->

7. **Back-compat**: existing `default_review` / `review` stored values are either bare backend (`codex`, `rp`) or never-parsed strings. Bare backend passes validation unchanged. Any stored string that fails validation falls back to backend-only with a warning — don't crash on old data.

### Parser Shape

```python
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class BackendSpec:
    backend: str
    model: Optional[str] = None
    effort: Optional[str] = None

    @classmethod
    def parse(cls, spec: str) -> "BackendSpec":
        """Parse 'backend[:model[:effort]]'. Raises ValueError on invalid."""
        if not spec or not spec.strip():
            raise ValueError("Empty backend spec")
        parts = spec.split(":")
        if len(parts) > 3:
            raise ValueError(f"Too many ':' separators in spec: {spec!r}")
        backend = parts[0].strip()
        if backend not in BACKEND_REGISTRY:
            raise ValueError(f"Unknown backend: {backend!r}")
        reg = BACKEND_REGISTRY[backend]
        model = parts[1].strip() if len(parts) > 1 else None
        effort = parts[2].strip() if len(parts) > 2 else None
        if model and reg["models"] is None:
            raise ValueError(f"Backend {backend!r} does not accept a model")
        if model and model not in reg["models"]:
            raise ValueError(f"Unknown model for {backend}: {model!r}. Valid: {sorted(reg['models'])}")
        if effort and reg["efforts"] is None:
            raise ValueError(f"Backend {backend!r} does not accept an effort")
        if effort and effort not in reg["efforts"]:
            raise ValueError(f"Unknown effort for {backend}: {effort!r}. Valid: {sorted(reg['efforts'])}")
        return cls(backend=backend, model=model, effort=effort)

    def resolve(self) -> "BackendSpec":
        """Fill in missing model/effort from registry defaults + env vars."""
        reg = BACKEND_REGISTRY[self.backend]
        env_model_key = f"FLOW_{self.backend.upper()}_MODEL"
        env_effort_key = f"FLOW_{self.backend.upper()}_EFFORT"
        model = self.model or os.environ.get(env_model_key) or reg.get("default_model")
        effort = self.effort or os.environ.get(env_effort_key) or reg.get("default_effort")
        return BackendSpec(self.backend, model, effort)
```

### Runtime Integration Points

1. `run_codex_exec(prompt, session_id, sandbox, spec: BackendSpec)` — drop the `model` kwarg in favor of full spec. Internal: `effective_model = spec.model`, `effort = spec.effort`. Env-var fallback moves up into `spec.resolve()`.
2. `run_copilot_exec(prompt, session_id, spec: BackendSpec)` — same shape. Initial fn-27 implementation already accepts model + effort; only wiring changes.
3. Skills (`flow-next-impl-review`, etc.) that pull backend config via `flowctl review-backend` now receive the full spec string — still branch on `.backend` field but pass spec through to `flowctl <backend> impl-review --spec <spec>`.
4. `cmd_*_review` functions (impl/plan/completion, per-backend) accept a `--spec` arg, parse it, resolve, pass to `run_*_exec`.

### Error Handling

- Store-time validation: reject with clear error including valid values. Never silently downgrade.
- Load-time fallback: if stored spec fails to parse (legacy data), warn to stderr and treat as bare backend. Never crash.
- Runtime: env-var overrides for missing fields only — never override explicit spec values.

### Config + Env Var Cascade Example

Task `fn-3.1` has `review: "codex:gpt-5.2"` (model set, effort unset).
Env has `FLOW_CODEX_EFFORT=low`.
Registry default effort for codex: `high`.

Resolved spec: `codex:gpt-5.2:low` (model from task spec, effort from env, since spec didn't set effort).

User running `FLOW_CODEX_MODEL=gpt-5.4 flowctl codex impl-review fn-3.1`:
Resolved spec: `codex:gpt-5.2:low` — task spec wins over env-var model. (Env only fills in *missing* fields.)

To override per-task spec for a session, user must override spec directly: `FLOW_REVIEW_BACKEND=codex:gpt-5.4 ...`.

## Quick Commands

```bash
FLOWCTL=plugins/flow-next/scripts/flowctl

# Validate parser
$FLOWCTL epic set-backend fn-5 --review "codex:gpt-5.4:high"
$FLOWCTL task set-backend fn-5.2 --review "copilot:claude-opus-4.5:xhigh"

# Invalid specs should error clearly
$FLOWCTL epic set-backend fn-5 --review "codex:gpt-6"       # unknown model
$FLOWCTL epic set-backend fn-5 --review "copilot:::::"      # too many separators
$FLOWCTL epic set-backend fn-5 --review "rp:claude-opus"    # rp doesn't take model

# Show resolved spec
$FLOWCTL task show-backend fn-5.2 --json

# Env-var override for a session
FLOW_REVIEW_BACKEND="codex:gpt-5.4:high" $FLOWCTL codex impl-review fn-5.2
```

## Acceptance

- [ ] `parse_backend_spec()` handles all documented forms (bare, backend+model, full three-part)
- [ ] Invalid specs rejected at `epic set-backend` / `task set-backend` with helpful errors listing valid values
- [ ] `FLOW_REVIEW_BACKEND` env var accepts full spec (`codex:gpt-5.4:high`) — not just bare backend
- [ ] Resolution precedence implemented: task > epic > env > config > backend-specific env > default
- [ ] `cmd_task_show_backend` shows both raw stored spec and resolved spec with field-level source tracking
- [ ] `run_codex_exec` honors per-task model + effort from spec, env fills missing fields only
- [ ] `run_copilot_exec` honors per-task model + effort from spec, env fills missing fields only
- [ ] Ralph templates accept spec-form `WORK_REVIEW` / `PLAN_REVIEW` values (`codex:gpt-5.4:high`)
- [ ] Legacy stored values (bare backend, or never-parsed strings) don't crash — warn and fall back to bare backend
- [ ] Help text on `--review` / `--impl` / `--sync` args matches actual parser behavior
- [ ] Tests cover: valid specs, invalid separator count, unknown backend, unknown model, unknown effort, backend that doesn't accept model/effort, precedence ordering, env-var overrides, legacy fallback
- [ ] Docs updated: CLAUDE.md project guide (shows spec grammar), plugin README, ralph runbooks

## Boundaries

- Not adding new backends — this is parser + plumbing only
- Not changing receipt schema (fn-27 already has model + effort fields)
- Not changing the config cascade for bare backend selection (still `FLOW_REVIEW_BACKEND` > `.flow/config.json` > ASK when no spec given)
- Not adding a plugin discovery mechanism — registry is a static dict
- Not adding spec fields beyond model + effort (sandbox / add-dir / etc. stay as env vars for now; can extend later if needed)
- Not migrating legacy stored specs — old values stay; parser tolerates them

## Risks

1. **Stored legacy values that look like specs but fail validation** — e.g., user set `review: "codex:gpt-5.4-high"` before this epic following the help text. Parser rejects. Mitigation: graceful fallback to bare backend with stderr warning; add a one-time migration note in release docs.

2. **Registry drift vs real CLI model catalogs** — e.g., codex adds `gpt-5.5`, our registry doesn't know. User can't use it until flowctl updates. Mitigation: option to bypass validation with `FLOW_SKIP_SPEC_VALIDATION=1` for power users; print warning when used. Or: treat registry as allowlist-with-escape, not hard gate.

3. **Scope creep toward per-task sandbox / add-dir / etc.** — tempting to generalize further. Discipline: only model + effort. Everything else stays as env or hard-coded until a concrete need.

4. **Skill-level wiring churn** — the three review skills (impl, plan, epic) plus Ralph need updates to thread spec through. Large surface even though each change is small. Mitigation: centralize spec resolution in flowctl, skills just pass it through opaquely.

5. **Env-var fallback semantics** — "env only fills missing fields" is subtle. Users may expect `FLOW_CODEX_MODEL` to always win. Mitigation: document clearly; add `flowctl task show-backend --json` output that surfaces every field's source.

## Early proof point

Task **fn-28-unified-review-backend-spec-parser.1** (parser + dataclass + `BACKEND_REGISTRY` + unit tests) validates the grammar: legal specs round-trip; illegal specs raise clean errors; `resolve()` precedence works for all four edge cases (missing model, missing effort, env fills, defaults fill).

If it fails: reconsider the `backend:model:effort` grammar (maybe drop effort from the spec and keep it env-only) before plumbing it into runtime tasks 2-4.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | `parse_backend_spec()` handles bare, backend+model, full three-part | fn-28-unified-review-backend-spec-parser.1 | — |
| R2 | Invalid specs rejected at set-backend with helpful errors | fn-28-unified-review-backend-spec-parser.1, fn-28-unified-review-backend-spec-parser.2 | — |
| R3 | `FLOW_REVIEW_BACKEND` accepts full spec form | fn-28-unified-review-backend-spec-parser.4 | — |
| R4 | Resolution precedence: task > epic > env > config > backend-specific env > default | fn-28-unified-review-backend-spec-parser.1, fn-28-unified-review-backend-spec-parser.3 | — |
| R5 | `cmd_task_show_backend` shows raw + resolved with per-field sources | fn-28-unified-review-backend-spec-parser.2 | — |
| R6 | `run_codex_exec` honors per-task model + effort from spec | fn-28-unified-review-backend-spec-parser.3 | — |
| R7 | `run_copilot_exec` honors per-task model + effort from spec | fn-28-unified-review-backend-spec-parser.3 | — |
| R8 | Ralph templates accept spec-form `WORK_REVIEW` / `PLAN_REVIEW` | fn-28-unified-review-backend-spec-parser.4 | — |
| R9 | Legacy stored values don't crash; graceful fallback to bare backend | fn-28-unified-review-backend-spec-parser.1, fn-28-unified-review-backend-spec-parser.2 | — |
| R10 | Help text on `--review` matches actual parser behavior | fn-28-unified-review-backend-spec-parser.5 | — |
| R11 | Tests cover edge cases | fn-28-unified-review-backend-spec-parser.1 | — |
| R12 | Docs updated (CLAUDE.md grammar block, README) | fn-28-unified-review-backend-spec-parser.5 | — |

## References

- fn-27 (copilot backend — prerequisite): `.flow/specs/fn-27-copilot-review-backend.md`
- fn-2 (codex backend — existing template): `.flow/specs/fn-2.md`
- Current opaque storage: `cmd_epic_set_backend` at `flowctl.py:4206` / `cmd_task_set_backend` at `flowctl.py:4265`
- Current resolution (bare backend only): `cmd_review_backend` at `flowctl.py:2830-2852` (already extended for copilot in fn-27; tuples at lines 2834+2839)
- Current runtime model resolution (env-only): `run_codex_exec` at `flowctl.py:1534`, env-lookup at `:1555`. Sibling `run_copilot_exec` at `flowctl.py:1732` already has `(prompt, session_id, repo_root, model=None, effort=None)` shape that fn-28 generalizes.
- Aspirational help text we're making real: `flowctl.py:8171` (epic impl), `:8174` (epic review), `:8243` (task review)
- flow-swarm's parseBackendSpec reference: `~/work/flow-swarm/docs/adding-backends.md` section 3.3
