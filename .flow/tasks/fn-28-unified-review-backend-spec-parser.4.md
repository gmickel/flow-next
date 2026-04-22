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

**`cmd_review_backend`** at `flowctl.py:2830-2852`:
- Replace the hardcoded tuple check. Instead:
  1. Get `env_val` from `FLOW_REVIEW_BACKEND`.
  2. If non-empty, try `BackendSpec.parse(env_val)`. If valid: return `{backend: spec.backend, spec: str(spec), source: "env"}`.
  3. Same for `.flow/config.json review.backend`.
  4. Legacy fallback: if parse fails, try to interpret as bare backend (`env_val in VALID_BACKENDS`). Return bare.
  5. Else `ASK`.
- Output in JSON mode: `{backend, spec, source, model, effort}` where spec is the resolved form.
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
- `ralph.sh`: backend-check gates (lines 1061-1098 area) already handle bare backends. Add: after env export, strip to bare backend for the equality check (`${PLAN_REVIEW%%:*}`). Pass the full spec via the `FLOW_REVIEW_BACKEND` export so flowctl resolves.
- `prompt_plan.md`, `prompt_work.md`, `prompt_completion.md`: show a spec-form example alongside the existing bare-backend examples.

**ralph-guard.py**: no changes needed — it guards tool calls, not spec strings.

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:2830-2852` — `cmd_review_backend` (already accepts bare copilot as of fn-27; task 4 adds spec-form support)
- `plugins/flow-next/skills/flow-next-impl-review/workflow.md` — current invocation comments
- `plugins/flow-next/skills/flow-next-ralph-init/templates/config.env` — current comment block
- `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh:1061-1098` — backend equality checks
- `.flow/specs/fn-28-unified-review-backend-spec-parser.md` §Resolution Precedence

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

(filled in when task completes)

## Evidence

(filled in when task completes)
