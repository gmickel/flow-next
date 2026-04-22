## Description

Lift the spec grammar into the top-of-the-cascade surfaces: `FLOW_REVIEW_BACKEND` env var accepts full spec, `cmd_review_backend` returns a spec string, skills relay specs unchanged, Ralph templates document the spec form.

**Size:** M
**Files:**
- `plugins/flow-next/scripts/flowctl.py`
- `plugins/flow-next/skills/flow-next-{impl,plan,epic}-review/workflow.md`
- `plugins/flow-next/skills/flow-next-setup/workflow.md`
- `plugins/flow-next/skills/flow-next-ralph-init/templates/config.env`
- `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh`
- `plugins/flow-next/skills/flow-next-ralph-init/templates/prompt_{plan,work,completion}.md`

## Approach

**`cmd_review_backend`** at `flowctl.py:3193` <!-- Updated by plan-sync: drifted +110 after fn-28.3 added resolve_review_spec + --spec args to 6 cmd_*_review. Current tuple at line 3197 is ("rp", "codex", "copilot", "none") — replace the whole tuple check -->:
- Replace the hardcoded `(env_val in ("rp", "codex", "copilot", "none"))` tuple check. Instead:
  1. Get `env_val` from `FLOW_REVIEW_BACKEND`.
  2. If non-empty, try `parse_backend_spec_lenient(env_val, warn=False)` (from fn-28.2 at `flowctl.py:1918`). Degrades to bare backend on invalid; returns None only if nothing recognizable. If valid: return `{backend: spec.backend, spec: str(spec.resolve()), source: "env", model: resolved.model, effort: resolved.effort}`.
  3. Same for `.flow/config.json review.backend`.
  4. Else `ASK`.
- Note: legacy fallback is already baked into `parse_backend_spec_lenient`. Do not reimplement it here. <!-- plan-sync note: reuse helper instead of duplicating -->
- **Alternative (simpler)**: fn-28.3 added `resolve_review_spec(backend_hint, task_id)` at `flowctl.py:1959` which already cascades env > config > bare hint with the lenient parser. `cmd_review_backend` can largely delegate — but note it currently distinguishes `source` ("env" vs "config" vs "none") which `resolve_review_spec` collapses. You'll likely still need separate env/config lookup for `source` field, but the parsing logic is identical to what's in `resolve_review_spec` lines 2027-2039. <!-- plan-sync note: see how fn-28.3 handled it -->
- `VALID_BACKENDS` (`flowctl.py:1766`) is available if argparse `choices=` is wanted on any new `--backend`-style flag, but the env/config paths should use the lenient parser, not `choices=`.
- Output in JSON mode: `{backend, spec, source, model, effort}` where spec is the resolved form (via `str(resolved)`).
- Output in text mode: `backend` (backward compatible for skills that grep stdout).

**Skills** — the three review workflows (`flow-next-impl-review/workflow.md`, etc.):
- No real logic change — they already invoke `flowctl <backend> <action>`. But update the examples / comments to show spec-form `FLOW_REVIEW_BACKEND`:
  ```
  FLOW_REVIEW_BACKEND=codex:gpt-5.4:xhigh flowctl codex impl-review ...
  FLOW_REVIEW_BACKEND=copilot:claude-opus-4.5 flowctl copilot impl-review ...
  ```
- Mention that per-task `review` (set via `flowctl task set-backend`) overrides env.

**flow-next-setup**:
- Update the backend-selection question to note spec form in the help text: "You can also write `codex:gpt-5.4:high` for a full spec."
- Default answer: bare backend (most users don't need full spec).

**Ralph templates**:
- `config.env`: extend `PLAN_REVIEW` / `WORK_REVIEW` / `COMPLETION_REVIEW` comment to note spec form: `# e.g. PLAN_REVIEW=codex:gpt-5.4:xhigh or PLAN_REVIEW=copilot:claude-opus-4.5`.
- `ralph.sh`: backend-check gates at lines **1082, 1096, 1119** (plus display-name checks at 228-236) already handle bare backends. Add: after env export, strip to bare backend for the equality check (`${PLAN_REVIEW%%:*}`). Pass the full spec via the `FLOW_REVIEW_BACKEND` export so flowctl resolves. <!-- Updated by plan-sync: actual gate lines verified -->
- **Simpler alternative** (preferred): fn-28.3 added `--spec <spec>` arg to all 6 `cmd_*_review` functions. Ralph can pass `--spec "$PLAN_REVIEW"` directly to the review invocation instead of (or alongside) exporting `FLOW_REVIEW_BACKEND`. The bare-backend equality check still applies for the backend-name gate; the `--spec` flag handles model+effort. <!-- plan-sync note: fn-28.3 --spec exists on all 6 cmds -->
- `prompt_plan.md`, `prompt_work.md`, `prompt_completion.md`: show a spec-form example alongside the existing bare-backend examples.

**Receipt schema awareness** <!-- Updated by plan-sync: fn-28.3 added `spec` field -->:
- Receipts now include a new `spec` field alongside existing `model` + `effort`: `{"mode": "codex", "model": "gpt-5.4", "effort": "high", "spec": "codex:gpt-5.4:high", ...}`.
- `verify_receipt` in ralph.sh does NOT currently inspect model/effort/spec — receipt verification is promise/verdict-based. No ralph.sh changes needed for the new field. If a future step adds spec-based receipt checks, read `spec` (not model/effort) as the canonical form.

**ralph-guard.py**: no changes needed — it guards tool calls, not spec strings.

## Investigation targets

**Required:** <!-- Updated by plan-sync: line numbers reverified post-fn-28.3; drift from task 3's insertions -->
- `plugins/flow-next/scripts/flowctl.py:3193` — `cmd_review_backend` (was 3083 pre-fn-28.3; already accepts bare copilot as of fn-27; task 4 adds spec-form support)
- `plugins/flow-next/scripts/flowctl.py:1715` — `BACKEND_REGISTRY` (source of truth for spec validation)
- `plugins/flow-next/scripts/flowctl.py:1766` — `VALID_BACKENDS` (available as `sorted(BACKEND_REGISTRY.keys())`, added by fn-28.2)
- `plugins/flow-next/scripts/flowctl.py:1918` — `parse_backend_spec_lenient` (use this for env/config reads; returns `Optional[BackendSpec]`, handles legacy fallback, added by fn-28.2)
- `plugins/flow-next/scripts/flowctl.py:1959` — `resolve_review_spec(backend_hint, task_id)` (added by fn-28.3; already implements env > config > bare cascade; consider delegating most of cmd_review_backend to this helper)
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md` — current invocation comments
- `plugins/flow-next/skills/flow-next-ralph-init/templates/config.env` — current comment block
- `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh:1082, 1096, 1119` — backend equality checks (plus 228-236 for display-name branches)
- `.flow/specs/fn-28-unified-review-backend-spec-parser.md` §Resolution Precedence

**Available from fn-28.3** <!-- Added by plan-sync -->:
- `--spec <spec>` CLI flag on all 6 `cmd_*_review` functions (strict parse via `BackendSpec.parse`; grep `def cmd_codex_impl_review` / `def cmd_copilot_impl_review` etc.)
- Private helpers `_resolve_codex_review_spec` / `_resolve_copilot_review_spec` — model for the strict-parse-argv + fallback-to-resolve_review_spec pattern
- Receipt schema now includes `"spec": str(resolved_spec)` field alongside `model` + `effort`

**Optional:**
- `plugins/flow-next/skills/flow-next-setup/workflow.md:150-349` — where backend-selection question lives

## Acceptance

- [ ] `FLOW_REVIEW_BACKEND=codex:gpt-5.2:medium flowctl review-backend --json` returns `{backend: "codex", spec: "codex:gpt-5.2:medium", model: "gpt-5.2", effort: "medium", source: "env"}`
- [ ] Legacy `FLOW_REVIEW_BACKEND=codex` still returns `{backend: "codex", spec: "codex", ...}` with resolved defaults
- [ ] Text-mode `flowctl review-backend` still prints just `codex` / `copilot` / `rp` (back-compat for skill grep)
- [ ] `.flow/config.json` with `review.backend: "copilot:claude-haiku-4.5"` resolves correctly at runtime
- [ ] Ralph workflow: `PLAN_REVIEW=codex:gpt-5.4:xhigh bash ralph.sh` routes to codex backend and passes full spec through `FLOW_REVIEW_BACKEND`
- [ ] `ralph.sh` equality checks still work (`${PLAN_REVIEW%%:*}` extracts bare backend for the check)
- [ ] `config.env` comment documents spec form with at least one codex + one copilot example
- [ ] Review skill workflows show a spec-form example in their invocation block
- [ ] No edits to generated codex mirror files (task 5 regens)

## Done summary
cmd_review_backend now accepts spec form (codex:gpt-5.4:xhigh) from FLOW_REVIEW_BACKEND and .flow/config.json via parse_backend_spec_lenient; JSON mode returns full {backend, spec, model, effort, source} and text mode still prints bare backend for skill grep back-compat. Six review skill files (impl/plan/epic x SKILL+workflow), flow-next-setup workflow, and all Ralph templates (config.env, ralph.sh, prompt_{plan,work,completion}.md) now document the spec grammar and pass full spec through FLOW_REVIEW_BACKEND while keeping equality/gate checks on the bare backend (extracted via ${VAR%%:*}).
## Evidence
- Commits: 59eeb68bcee06cdd068d8456338e51c392417a8f
- Tests: python3 -m unittest discover -s plugins/flow-next/tests (112 pass, +14 new), plugins/flow-next/scripts/smoke_test.sh (67 pass), bash -n plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh (syntax OK), manual: FLOW_REVIEW_BACKEND=codex:gpt-5.4:xhigh flowctl review-backend --json returns full spec + model + effort + source (env), manual: text mode still prints bare 'codex' for skill grep back-compat, manual: legacy FLOW_REVIEW_BACKEND=codex still resolves to codex:gpt-5.4:high, manual: bash ${VAR%%:*} extracts bare backend from both spec and bare forms
- PRs: