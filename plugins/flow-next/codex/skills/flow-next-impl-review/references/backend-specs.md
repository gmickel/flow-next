# Backend specs — at a glance, spec grammar, env forms

Read this only when you need the per-backend model/effort detail: surfacing a
backend recommendation or override hint to the user, resolving a `--spec` /
`FLOW_REVIEW_BACKEND` value, or explaining the configured backend. The default
review path never needs it — Phase 0 already resolved `$BACKEND`.

## Backend at a glance

When `RP_ELIGIBLE=0`, omit the **rp** line below from any guidance you surface (explicit `--review=rp` still honored):

- **rp** — RepoPrompt (macOS GUI); builder auto-selects context. Primary backend.
- **codex** — Codex CLI (cross-platform); uses OpenAI models (default `gpt-5.5`). `FLOW_CODEX_MODEL` / `FLOW_CODEX_EFFORT` env vars, or `--spec codex:gpt-5.4:xhigh`.
- **copilot** — GitHub Copilot CLI (cross-platform); supports Claude families through Opus 5 plus GPT-5.x families via a Copilot subscription (availability is org-policy managed — a given install may expose fewer). `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, or `--spec copilot:claude-opus-4.5:xhigh`.
- **cursor** — Cursor CLI (`cursor-agent`, cross-platform); reaches `gpt-5.5-high` (1M-ctx default), the `gpt-5.3-codex` family, `composer-2.5`, and Claude tiers (`claude-opus-5-thinking-high`, `claude-opus-4-8-thinking-high`) via a Cursor subscription. `FLOW_CURSOR_MODEL` env var, or `--spec cursor:gpt-5.5-high`. Cursor folds reasoning effort into the model name — **no effort field**.
- **host** — Bare-only non-executable selection sentinel; selected mechanics
  live in [../workflow-host.md](../workflow-host.md).

**Spec grammar:** `backend[:model[:effort]]` — `FLOW_REVIEW_BACKEND` and `.flow/config.json review.backend` both accept this. Examples: `codex`, `codex:gpt-5.2`, `copilot:claude-opus-4.5:xhigh`, `cursor:gpt-5.5-high` (cursor takes model only — no `:effort`), `host` (bare only). Per-task `review` (set via `flowctl task set-backend`) overrides env.

Runnable `FLOW_REVIEW_BACKEND=` / `--spec` invocation examples stay inline in
[../workflow-common.md](../workflow-common.md) § Phase 0 (already loaded on
every review) — this file is the descriptive layer only.
