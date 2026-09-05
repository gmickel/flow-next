# Backend specs — at a glance, spec grammar, env forms

Read this only when you need the per-backend model/effort detail: surfacing a
backend recommendation or override hint to the user, resolving a `--spec` /
`FLOW_REVIEW_BACKEND` value, or explaining the configured backend. The default
review path never needs it — Phase 0 already resolved `$BACKEND`.

## Backend at a glance

When `RP_ELIGIBLE=0`, omit the **rp** line below from any guidance you surface (explicit `--review=rp` still honored):

- **rp** — RepoPrompt (macOS GUI); builder auto-selects context. Primary backend.
- **codex** — Codex CLI (cross-platform); uses OpenAI models (registry default, see [`flowctl.md`](../../../docs/flow-next/flowctl.md#review-backend)). `FLOW_CODEX_MODEL` / `FLOW_CODEX_EFFORT` env vars, or `--spec codex:<model>:xhigh`.
- **copilot** — GitHub Copilot CLI (cross-platform); reaches several model families via a Copilot subscription (availability is org-policy managed — a given install may expose fewer). `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, or `--spec copilot:<model>:xhigh`.
- **cursor** — Cursor CLI (`cursor-agent`, cross-platform); reaches models from several families via a Cursor subscription — ask `cursor-agent --list-models` for the current set. `FLOW_CURSOR_MODEL` env var, or `--spec cursor:<model>`. Cursor folds reasoning effort into the model name — **no effort field**.
- **claude** — Claude Code CLI (`claude -p`, cross-platform); Claude-family reviewer for hosts that cannot dispatch a Claude subagent (registry ranking, ids stated beside a date in [`flowctl.md`](../../../docs/flow-next/flowctl.md#review-backend)). `FLOW_CLAUDE_MODEL` / `FLOW_CLAUDE_EFFORT` env vars, or `--spec claude:<model>:<effort>`; efforts `low|medium|high|xhigh|max`. Grammar `claude[:<model>[:<effort>]]`. Same-family on a Claude Code host — the receipt records it; prefer `codex` or `host` there when family independence matters.
- **host** — Bare-only non-executable selection sentinel; selected mechanics
  live in [../workflow-host.md](../workflow-host.md).

**Spec grammar:** `backend[:model[:effort]]` — `FLOW_REVIEW_BACKEND` and `.flow/config.json review.backend` both accept this. Examples: `codex`, `codex:<model>`, `copilot:<model>:xhigh`, `cursor:<model>` (cursor takes model only — no `:effort`), `claude:<model>:<effort>`, `host` (bare only). Per-task `review` (set via `flowctl task set-backend`) overrides env.

Runnable `FLOW_REVIEW_BACKEND=` / `--spec` invocation examples stay inline in
[../workflow-common.md](../workflow-common.md) § Phase 0 (already loaded on
every review) — this file is the descriptive layer only.
