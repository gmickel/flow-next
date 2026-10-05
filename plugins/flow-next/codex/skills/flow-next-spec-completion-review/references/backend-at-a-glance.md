# Backend at a glance (guidance surface)

Read this only when you surface backend guidance to the user — the Phase 0 ASK
branch, a recommendation, or an override hint. Routing itself needs none of it:
`$BACKEND` is already resolved and only that backend's `workflow-<backend>.md`
matters.

- **codex** — Codex CLI (cross-platform); uses OpenAI models (registry default, see [`flowctl.md`](../../../docs/flow-next/flowctl.md#review-backend)). `FLOW_CODEX_MODEL` / `FLOW_CODEX_EFFORT` env vars, or `--spec codex:<model>:xhigh`.
- **copilot** — GitHub Copilot CLI (cross-platform); reaches several model families via a Copilot subscription. `FLOW_COPILOT_MODEL` / `FLOW_COPILOT_EFFORT` env vars, or `--spec copilot:<model>:xhigh`.
- **cursor** — Cursor CLI (`cursor-agent`, cross-platform); reaches models from several families via a Cursor subscription — ask `cursor-agent --list-models` for the current set. `FLOW_CURSOR_MODEL` env var, or `--spec cursor:<model>`. Cursor folds reasoning effort into the model name — **no effort field**.
- **claude** — Claude Code CLI (`claude -p`, cross-platform); Claude-family reviewer for hosts that cannot dispatch a Claude subagent (registry ranking, ids stated beside a date in [`flowctl.md`](../../../docs/flow-next/flowctl.md#review-backend)). `FLOW_CLAUDE_MODEL` / `FLOW_CLAUDE_EFFORT` env vars, or `--spec claude:<model>:<effort>`; efforts `low|medium|high|xhigh|max`. Grammar `claude[:<model>[:<effort>]]`. Same-family on a Claude Code host — the receipt records it; prefer `codex` or `host` there when family independence matters.
- **host** — Bare-only non-executable selection sentinel; selected mechanics
  live in `workflow-host.md`.

**Spec grammar:** `backend[:model[:effort]]` — `FLOW_REVIEW_BACKEND` and `.flow/config.json review.backend` both accept this. Examples: `codex`, `codex:<model>`, `copilot:<model>:xhigh`, `cursor:<model>` (cursor takes model only — no `:effort`), `claude:<model>:<effort>`, `host` (bare only). Per-spec `default_review` (set via `flowctl spec set-backend`) overrides env.

**Spec-form env var (optional):** `FLOW_REVIEW_BACKEND` accepts bare or full spec:

```bash
# FOREGROUND RULE: run this as ONE blocking foreground Bash call (timeout 600s).
# NEVER run_in_background + monitor - a background completion does not resume a subagent context.
FLOW_REVIEW_BACKEND=codex:<model>:xhigh $FLOWCTL codex completion-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
FLOW_REVIEW_BACKEND=copilot:<model> $FLOWCTL copilot completion-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
# Cursor folds effort into the model name (no :<effort>):
FLOW_REVIEW_BACKEND=cursor:<model> $FLOWCTL cursor completion-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
# Claude takes model + effort (low|medium|high|xhigh|max):
FLOW_REVIEW_BACKEND=claude:<model>:high $FLOWCTL claude completion-review "$SPEC_ID" --receipt "$RECEIPT_PATH"
# Or pass spec directly:
$FLOWCTL codex completion-review "$SPEC_ID" --spec "codex:<model>:xhigh" --receipt "$RECEIPT_PATH"
```

Per-spec `default_review` (set via `flowctl spec set-backend`) overrides env.
