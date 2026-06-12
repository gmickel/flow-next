# Codex Mirror Generation (`sync-codex.sh`)

[`../../../scripts/sync-codex.sh`](../../../scripts/sync-codex.sh) generates the pre-built Codex files from canonical `skills/` and `agents/` sources. Output: `plugins/flow-next/codex/{skills/,agents/,hooks.json}` plus mirrored `templates/` and `references/` directories. The script is **idempotent** — running twice produces identical output.

> Read the script's top-of-file comments and stage banners for the authoritative behavior. This doc gives the high-level shape and points at the validation guards.

## When to run

Run after modifying any of:

- `plugins/flow-next/skills/**` — skill workflow files (canonical sources)
- `plugins/flow-next/agents/**` — agent `.md` files (converted to `.toml`)
- `plugins/flow-next/hooks/hooks.json` — hook definitions
- `plugins/flow-next/templates/spec.md` — canonical scaffold mirrored into `codex/templates/` for R20 relative-path resolution
- `plugins/flow-next/references/**` — shared disclosure files (e.g. `html-artifacts.md`) mirrored byte-identical into `codex/references/` (tool-name-agnostic by contract; no rewrite pass touches them)

```bash
./scripts/sync-codex.sh
```

Commit the regenerated `plugins/flow-next/codex/` tree alongside the canonical change. CI runs the same script and fails if the mirror is stale.

## Pipeline shape

The script runs in numbered stages (see banners in [`../../../scripts/sync-codex.sh`](../../../scripts/sync-codex.sh)):

1. **Copy & patch skills** — canonical `skills/` copied to `codex/skills/`, then per-stage transforms applied (Claude-native tool names rewritten to Codex equivalents; `request_user_input` → plain-text numbered prompt per fn-45).
2. **Convert agents** — `agents/*.md` → `codex/agents/*.toml` with per-agent reasoning effort, sandbox mode, model mapping, and nickname candidates.
3. **Generate hooks.json** — derived from canonical `hooks/hooks.json`.
4. **Mirror templates/ + references/** — canonical `templates/spec.md` copied to `codex/templates/` so the R20 4-tier discovery cascade resolves the same relative path in the mirror; canonical `references/` copied byte-identical to `codex/references/` (shared disclosure files are tool-name-agnostic, so no transform applies).
5. **Validation** — counts + drift guards (see below).

## Validation guards

The script's validation block (search for `# ─── Validation ───` in the canonical) enforces the following:

| Guard | What it catches | Failure mode |
|-------|-----------------|--------------|
| Skill / agent count | Mirror lost or gained a file vs source | Build fails |
| TOML required keys | `developer_instructions` missing in any agent | Build fails |
| `hooks.json` valid JSON | Mirror produced unparseable JSON | Build fails |
| Bare `CLAUDE_PLUGIN_ROOT` refs | Skill bash without `${...:-${...}}` fallback | Warning |
| `Task flow-next:` refs | Skill text still references the Claude `Task` form | Build fails |
| `AskUserQuestion` / `ToolSearch` refs | Stage 1 transforms missed a Claude-native tool name | Build fails |
| `request_user_input` refs (R6) | Stage 3 (fn-45) plain-text rewrite incomplete | Build fails |
| R17 forbidden vocabulary | DDD jargon leaked into mirror | Build fails |
| R4 meta-file refs | Early-design `GLOSSARY-MAP.md` / `CONTEXT-MAP.md` survived | Build fails |
| R19 strategy-doc fluff | Rumelt "fluff" tier-1 jargon in strategy skill mirror | Build fails |
| R30 legacy CLI vocabulary | `flowctl epic*` legacy form in fresh prose | Build fails |
| R21 spec-template duplication | Skill markdown enumerates the canonical 7-section sequence (drift hazard) | Build fails |
| `openai.yaml` coverage | `REQUIRED_OPENAI_YAML_SKILLS` missing the required file | Build fails |

Each guard prints `file:line` hits where available so the fix is mechanical: clean canonical first, then re-run sync.

## Plain-text transform (fn-45)

The Codex Default-mode + CLI surface errors on `request_user_input` calls ([openai/codex#10384](https://github.com/openai/codex/issues/10384), [#11536](https://github.com/openai/codex/issues/11536), [#12694](https://github.com/openai/codex/issues/12694)). Stage 3 rewrites canonical `AskUserQuestion` blocks into plain-text numbered prompts in the mirror, appending an `N+1. Other — type your own answer` option so the mirror still offers the freeform-input affordance. The R6 mirror scan re-runs after the rewrite to catch any surviving references.

For the user-facing smoke procedure that validates this transform, see [`../../../agent_docs/local-dev.md`](../../../agent_docs/local-dev.md) (Codex plain-text smoke section).

## R17 cross-link discipline

Memory entry `bug/build-errors/fn-445-review-r17-enforcement-beyond-2026-05-15` confirms: R17 is **review-blocking**. Canonical skill prose never enumerates the spec-template's 7-section sequence; skills cross-link [`../templates/spec.md`](../templates/spec.md) instead. The R21 validation guard catches the structural form (`^## Goal & Context` followed by other canonical headers within 30 lines); reviewer catch is the semantic backstop.

## See also

- [`../../../scripts/sync-codex.sh`](../../../scripts/sync-codex.sh) — canonical pipeline (read the file).
- [`platforms.md`](platforms.md) — Codex-specific install + caveats.
- [`spec-template.md`](spec-template.md) — the canonical scaffold the R21 guard protects.
- [`../../../agent_docs/local-dev.md`](../../../agent_docs/local-dev.md) — local-dev smoke procedure including the Codex plain-text invariant.
