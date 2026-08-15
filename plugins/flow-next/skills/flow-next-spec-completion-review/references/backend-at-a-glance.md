# Backend at a glance (guidance surface)

Read this only when you surface backend guidance to the user — the Phase 0 ASK
branch, a recommendation, or an override hint. Routing itself needs none of it:
`$BACKEND` is already resolved and only that backend's `workflow-<backend>.md`
matters.

When `RP_ELIGIBLE=0`, omit the **rp** line below from any guidance you surface (explicit `--review=rp` still honored):

- **rp** — RepoPrompt (macOS GUI); builder auto-selects context. Primary backend.
- **codex** — Codex CLI (cross-platform); uses OpenAI models (registry default, see [`flowctl.md`](../../../docs/flowctl.md#review-backend)). `FLOW_CODEX_MODEL` / `FLOW_CODEX_EFFORT` env vars, or `--spec codex:gpt-5.4:xhigh`.
- **copilot** — GitHub Copilot CLI (cross-platform); reaches several model families via a Copilot subscription. `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, or `--spec copilot:claude-opus-4.5:xhigh`.
- **cursor** — Cursor CLI (`cursor-agent`, cross-platform); reaches models from several families via a Cursor subscription — ask `cursor-agent --list-models` for the current set. `FLOW_CURSOR_MODEL` env var, or `--spec cursor:<model>`. Cursor folds reasoning effort into the model name — **no effort field**.
- **host** — Bare-only non-executable selection sentinel; selected mechanics
  live in `workflow-host.md`.

**Spec grammar:** `backend[:model[:effort]]` — `FLOW_REVIEW_BACKEND` and `.flow/config.json review.backend` both accept this. Examples: `codex`, `codex:gpt-5.2`, `copilot:claude-opus-4.5:xhigh`, `cursor:gpt-5.5-high` (cursor takes model only — no `:effort`), `host` (bare only). Per-spec `default_review` (set via `flowctl spec set-backend`) overrides env.
