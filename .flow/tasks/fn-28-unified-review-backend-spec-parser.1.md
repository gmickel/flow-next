## Description

Add the parser + data model + registry that unify backend spec vocabulary across codex/copilot/rp/none. This is the early proof point — everything downstream plumbs through this module. No call sites wired yet; that's task 3.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` + new test file

## Approach

Inside `flowctl.py`, add a new section (suggested location: right after the existing codex helpers block, around line 1700 once fn-27 has landed):

- **`BackendSpec` dataclass** — frozen dataclass with fields `(backend: str, model: Optional[str], effort: Optional[str])`.
  - `.parse(spec: str) -> BackendSpec` classmethod: splits on `:`, max 3 parts, validates against registry. Raises `ValueError` on invalid.
  - `.resolve() -> BackendSpec` method: fills missing fields from env vars (`FLOW_<BACKEND>_MODEL`, `FLOW_<BACKEND>_EFFORT`) then registry defaults.
  - `.__str__()` serializes back to `backend:model:effort` form (omit trailing None parts).

- **`BACKEND_REGISTRY`** — module-level dict:
  - `"rp"` → `{models: None, efforts: None}` (bare-backend only)
  - `"codex"` → `{models: {"gpt-5.4", "gpt-5.2", "gpt-5-mini", ...}, efforts: {"none","minimal","low","medium","high","xhigh"}, default_model: "gpt-5.4", default_effort: "high"}`
  - `"copilot"` → `{models: {"claude-sonnet-4.5","claude-haiku-4.5","claude-opus-4.5","claude-sonnet-4","gpt-5.2","gpt-5.2-codex","gpt-5-mini","gpt-4.1"}, efforts: {"low","medium","high","xhigh"}, default_model: "gpt-5.2", default_effort: "high"}`
  - `"none"` → `{models: None, efforts: None}`
  - Include a brief docstring noting the `minimal` effort caveat for codex (server-side rejects when `web_search` tool enabled — safe for flowctl's review use case).

- **Validation rules**:
  - Empty/whitespace spec → ValueError with "Empty backend spec"
  - >3 colons → ValueError
  - Unknown backend → ValueError with "Unknown backend: X. Valid: [...]"
  - Model on backend that doesn't accept one (rp/none) → ValueError
  - Unknown model → ValueError with sorted valid-list
  - Effort on backend that doesn't accept one → ValueError
  - Unknown effort → ValueError with sorted valid-list

- **Unit tests** — new file `plugins/flow-next/tests/test_backend_spec.py` (or matching existing test location). Cover:
  - Valid: bare `codex`, `codex:gpt-5.4`, `codex:gpt-5.4:xhigh`, `copilot:claude-opus-4.5:xhigh`, `copilot:gpt-5.2`, `rp`, `none`
  - Invalid: `""`, `"foo"`, `"codex:"`, `"codex:gpt-5.4:high:extra"`, `"codex:gpt-99"`, `"copilot:xhigh-is-not-a-model"`, `"rp:opus"` (rp rejects model), `"codex:gpt-5.4:bogus-effort"`
  - `resolve()` with env var set (model from env, effort from spec) and unset (both from defaults)
  - Case sensitivity: backend names lowercase; be explicit about whether we accept uppercase
  - String round-trip: `BackendSpec.parse(s).__str__()` matches `s` when all fields present

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:2830-2852` — `cmd_review_backend` (already accepts copilot as of fn-27) (understand the cascade we're extending)
- `plugins/flow-next/scripts/flowctl.py:1555` — current `FLOW_CODEX_MODEL` resolution pattern (to be replaced by `BackendSpec.resolve()`)
- `.flow/specs/fn-28-unified-review-backend-spec-parser.md` — spec includes the parser shape in §Parser Shape
- `.flow/specs/fn-27-copilot-review-backend.md` — for the copilot model catalog and default

**Optional:**
- `~/work/flow-swarm/docs/adding-backends.md` §3.3 — reference for how flow-swarm's TS `parseBackendSpec` works
- Existing test patterns in the repo (search for `test_*.py` or `*_test.py`)

## Acceptance

- [ ] `BackendSpec.parse("codex:gpt-5.4:xhigh")` returns `BackendSpec(backend="codex", model="gpt-5.4", effort="xhigh")`
- [ ] `BackendSpec.parse("rp").resolve()` returns unchanged (no model/effort)
- [ ] `BackendSpec.parse("rp:opus")` raises ValueError
- [ ] `BackendSpec.parse("codex:gpt-99")` raises ValueError with valid-models list in message
- [ ] `BACKEND_REGISTRY` has exactly four keys; codex effort set is `{none,minimal,low,medium,high,xhigh}`; copilot effort set is `{low,medium,high,xhigh}`
- [ ] `resolve()` honors `FLOW_CODEX_MODEL` / `FLOW_COPILOT_EFFORT` for missing fields; does NOT override explicit spec values
- [ ] `str(BackendSpec("codex", "gpt-5.4", "xhigh"))` == `"codex:gpt-5.4:xhigh"`
- [ ] `str(BackendSpec("codex"))` == `"codex"` (no trailing colons)
- [ ] Unit tests pass; coverage includes every invalid-input branch listed above
- [ ] No call sites wired yet (task 3 does that); adding the module doesn't regress existing commands

## Done summary

(filled in when task completes)

## Evidence

(filled in when task completes)
