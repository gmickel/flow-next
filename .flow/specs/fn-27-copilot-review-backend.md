# Copilot Review Backend

## Overview

Add GitHub Copilot CLI as third review backend alongside RepoPrompt and Codex. Gives users another cross-platform alternative for multi-model review quality gates, with access to Claude (Sonnet/Opus/Haiku 4.5) and GPT-5.2 model families via GitHub Copilot's routing.

Mirrors the shape of `fn-2` (Codex Review Backend) — clean parallel to `flowctl codex` subcommands, same receipt schema, same skill branching pattern.

Runtime configuration (model + effort) is via env vars, matching Codex's current behavior. Unified inline `backend:model:effort` spec parsing is **deferred to fn-28** so both backends can be retrofitted symmetrically in one pass.

## Scope

- New `flowctl copilot` command group (check, impl-review, plan-review, completion-review)
- Extend `cmd_review_backend` to accept `copilot` as valid backend value (alongside `rp|codex|none`)
- Update skills to branch on `copilot` backend (impl-review, plan-review, epic-review)
- Update Ralph templates for `copilot` option
- Update `ralph-guard.py` hook for copilot call patterns (block direct `copilot` without wrapper, block `--continue` which conflicts with parallel usage)
- Add copilot backend smoke tests
- Reuse existing `build_review_prompt`, `build_rereview_preamble`, `get_embedded_file_contents`, `gather_context_hints` unchanged (backend-agnostic)

## Approach

### Key Design Decisions

1. **Text mode, not JSONL** — `--output-format text -s` gives clean final answer (~400 bytes for a response vs ~19 KB of JSONL with reasoning deltas). We extract verdict via same `<verdict>SHIP</verdict>` regex used for Codex. Verified by flow-swarm's existing copilot adapter (`~/work/flow-swarm/src/lib/backends/copilot.ts`).

2. **Client-generated session UUIDs** — `copilot --resume=<uuid>` creates-or-resumes: passing a fresh UUID starts a new session with that exact ID; passing an existing one resumes. So flowctl generates `uuid.uuid4()`, stores in receipt, passes on re-review. No stdout parsing needed for session ID extraction. Empirically verified: context carries across `--resume` runs.

3. **Prompt via temp file, not `-p "$(cat ...)"` inline** — write prompt to `.flow/tmp/copilot-prompt-<uuid>.txt`, shell-expand to env var, `rm` file, `exec copilot`. Pattern lifted from `flow-swarm/src/lib/backends/copilot.ts:138-149`. Handles huge prompts (>155 KB tested clean on macOS), avoids shell-escaping hell, works around Windows 8191-char ARG_MAX limit, and leaves PID = copilot (not `sh`).

4. **Session continuity via `--resume=<uuid>`** — matches Codex pattern. First review generates UUID, stores in receipt. Re-review reads receipt UUID, passes to `--resume`.

5. **Config priority**: env var (`FLOW_REVIEW_BACKEND=copilot`) > `.flow/config.json` `review.backend` > ASK. Same cascade as existing backends.

6. **Runtime model + effort via env vars** — `FLOW_COPILOT_MODEL`, `FLOW_COPILOT_EFFORT`. Matches Codex's current approach (`FLOW_CODEX_MODEL`). Inline `--review=copilot:claude-opus-4.5:xhigh` spec parsing is intentionally **out of scope here**; fn-28 will add that for all backends uniformly. Storing `--review=copilot` (backend-only) at epic/task level works today as opaque metadata, same as codex.

### Flag Mapping (Codex → Copilot)

| Codex | Copilot |
|---|---|
| `codex exec -` (stdin prompt) | `copilot -p "$PROMPT"` (prompt from env var after temp-file expansion) |
| `codex exec resume <thread_id>` | `copilot --resume=<uuid>` |
| `--model gpt-5.4` | `--model claude-opus-4.5` (default) |
| `-c model_reasoning_effort=high` | `--effort high` (also supports `xhigh`) |
| `--sandbox workspace-write` | `--allow-all-tools --no-ask-user --add-dir <repo>` |
| `--json` | `--output-format text -s` (text mode chosen; see decision #1) |
| `--skip-git-repo-check` | (not needed — reviews always in repo) |

### Session Continuity (Re-review Loop)

Same pattern as Codex, but we control session IDs client-side:

1. **First review**: generate `uuid.uuid4()`, pass `copilot --resume=<uuid> -p ...`, store UUID in receipt.
2. **Receipt**: `{"session_id": "8f1c0bb5-...", "mode": "copilot", ...}` — same shape as Codex.
3. **Re-review**: read `session_id` from receipt → `copilot --resume=<session_id> -p <rereview_prompt>`.

**Never use `--continue`** (resumes most recent session) — conflicts with parallel reviews or multiple projects. Same rule as `codex exec --last` exclusion.

### Command Structure

```bash
flowctl copilot check                              # Verify copilot installed + auth
flowctl copilot impl-review <task> --base <br>     # Impl review via copilot -p
flowctl copilot plan-review <epic> --files a,b,c   # Plan review via copilot -p
flowctl copilot completion-review <epic>           # Completion review via copilot -p
```

### Invocation Template

```bash
PROMPT_FILE=.flow/tmp/copilot-prompt-$UUID.txt
# (flowctl writes prompt file, then:)
PROMPT="$(cat "$PROMPT_FILE")"
rm -f "$PROMPT_FILE"
exec copilot --resume="$UUID" -p "$PROMPT" \
  --output-format text -s \
  --model "$MODEL" --effort "$EFFORT" \
  --allow-all-tools --no-ask-user \
  --add-dir "$REPO_ROOT" \
  --disable-builtin-mcps --no-custom-instructions \
  --log-level error
```

### Prompt Structure (unchanged from Codex)

Reuses `build_review_prompt` verbatim — XML scaffold is backend-agnostic:

```
<context_hints>...</context_hints>
<diff_summary>...</diff_summary>
<diff_content>...</diff_content>
<embedded_files>...</embedded_files>
<spec>...</spec>
<review_instructions>
[Carmack prompt]
Output <verdict>SHIP</verdict> or <verdict>NEEDS_WORK</verdict> or <verdict>MAJOR_RETHINK</verdict>.
</review_instructions>
```

### Exit Code Handling

| Code | Meaning | Handling |
|---|---|---|
| `0` | Success | Parse verdict from stdout, write receipt |
| `1` | CLI-level error (bad flag/model, no auth) | Capture stderr, error out with clear message, clear receipt |
| `130`/`143` | SIGINT / SIGTERM | Interrupted, no receipt |

No `result` JSONL event in text mode — we rely on process exit code + verdict regex. If verdict missing despite exit 0: treat as failed review (matches Codex pattern).

### Receipt Schema (matches Codex)

```json
{
  "type": "impl_review",
  "id": "fn-1.2",
  "mode": "copilot",
  "base": "main",
  "verdict": "SHIP",
  "session_id": "8f1c0bb5-5989-4b2d-b286-b15f55b4a360",
  "model": "claude-opus-4.5",
  "effort": "high",
  "timestamp": "2026-04-22T10:30:00Z",
  "review": "<full review output text>"
}
```

`model` + `effort` fields are always populated (from env var or default) so fn-28 can later validate inline-spec behavior without receipt schema churn.

### Environment Variables

| Var | Default | Purpose |
|---|---|---|
| `FLOW_REVIEW_BACKEND` | (unset) | Set to `copilot` to select backend |
| `FLOW_COPILOT_MODEL` | `claude-opus-4.5` | Override model |
| `FLOW_COPILOT_EFFORT` | `high` | Reasoning effort (low/medium/high/xhigh) |
| `FLOW_COPILOT_EMBED_MAX_BYTES` | `512000` | File embedding budget (mirrors `FLOW_CODEX_EMBED_MAX_BYTES`) |

### Model Catalog (copilot-specific — no `gpt-5.4`)

Verified via `copilot --help` and live probe: `claude-sonnet-4.5` (copilot default), `claude-haiku-4.5`, `claude-opus-4.5`, `claude-sonnet-4`, `gpt-5.2`, `gpt-5.2-codex`, `gpt-5-mini`, `gpt-4.1`.

We default to `claude-opus-4.5` for reviews (best quality; matches the intent of Codex's `gpt-5.4` high-quality default).

## Quick Commands

```bash
# Run smoke tests
cd /tmp && /Users/gordon/work/gmickel-claude-marketplace/plugins/flow-next/scripts/smoke_test.sh

# Test copilot check (copilot CLI must be installed + authed)
FLOWCTL=plugins/flow-next/scripts/flowctl
$FLOWCTL copilot check --json

# Manual probe of a live review
FLOW_REVIEW_BACKEND=copilot FLOW_COPILOT_MODEL=claude-haiku-4.5 FLOW_COPILOT_EFFORT=medium \
  $FLOWCTL copilot impl-review fn-1.2 --base main
```

## Acceptance

- [ ] `flowctl copilot check` returns availability + version + default model, and does a trivial live probe to confirm auth
- [ ] `flowctl copilot impl-review` sends review, extracts verdict, writes receipt with session_id + model + effort
- [ ] `flowctl copilot plan-review` sends plan review, extracts verdict, writes receipt
- [ ] `flowctl copilot completion-review` sends completion review, extracts verdict, writes receipt
- [ ] Session continuity works (re-review uses `copilot --resume=<stored-uuid>`, model remembers prior feedback)
- [ ] `cmd_review_backend` recognizes `copilot` as valid backend value (env + config sources)
- [ ] `--review=copilot` (backend-only, no suffix) is accepted as opaque metadata at epic/task set-backend — same as codex today
- [ ] `FLOW_COPILOT_MODEL` and `FLOW_COPILOT_EFFORT` env vars honored at runtime
- [ ] Skills (impl-review, plan-review, epic-review) branch correctly on `copilot` backend
- [ ] Ralph templates include `copilot` option; Ralph works with `PLAN_REVIEW=copilot WORK_REVIEW=copilot`
- [ ] `ralph-guard.py` validates copilot calls (blocks direct `copilot` without flowctl wrapper, blocks `--continue`)
- [ ] Prompt temp-file pattern handles large (>100 KB) prompts without shell errors
- [ ] Graceful fallback when copilot CLI unavailable or unauthed (`flowctl copilot check` non-zero)
- [ ] Smoke tests pass with copilot backend
- [ ] Docs updated: `plugins/flow-next/README.md` cross-model reviews section, `CLAUDE.md` project guide, `plans/ralph-e2e-notes.md`, `plans/ralph-getting-started.md`
- [ ] RepoPrompt remains primary, Codex + Copilot are both listed as cross-platform alternatives

## Boundaries

- **Inline `backend:model:effort` spec parsing is fn-28, not this epic.** Runtime config here is env-var only (matches codex's current state). The stored `default_review` / `review` metadata remains an opaque string. fn-28 will generalize the parser across all backends in one coherent pass.
- Not adding BYOK support (`COPILOT_PROVIDER_BASE_URL` and friends) — out of scope v1; users can set those env vars themselves if desired.
- Not implementing JSONL parsing — text mode is sufficient for reviews (see design decision #1). If future needs emerge (token accounting in receipts), add as a follow-up epic behind `FLOW_COPILOT_VERBOSE=1`.
- Not adding Copilot's `--agent` custom agents mechanism — reviews use direct prompts.
- Not attempting to disable `session.skills_loaded` / `session.mcp_servers_loaded` event noise — only matters in JSON mode which we don't use.
- Not updating the Codex plugin — this is a Claude Code plugin feature; Codex-plugin parity can follow if needed.

## Risks

1. **Copilot CLI auth state** — non-interactive check limited to `copilot --version`. Auth failures surface at first real invocation (exit 1 with stderr message). Mitigation: `flowctl copilot check` should attempt a trivial `-p "ok" --model claude-haiku-4.5 -s` probe to confirm auth works, not just binary presence.
2. **Org policies** — some orgs block third-party MCPs; emits harmless `session.warning` on every run (only visible in JSON mode, irrelevant to text mode). No mitigation needed.
3. **Model behavior variance** — different models may interpret Carmack prompt differently than Claude/GPT via Codex. Mitigation: re-use the exact same prompt scaffold; extract verdict via regex; treat missing verdict as failed review (same as Codex today).
4. **Windows ARG_MAX** — `-p "$(cat ...)"` with huge embeds could blow the 8191-char limit. Mitigation: temp-file + shell-var pattern already handles this (prompt never appears on the command line; it's in an env var loaded from a file).
5. **Premium-request cost** — Copilot charges per-request (claude-haiku-4.5 ≈ 0.33 requests per turn, opus-4.5 higher). Receipts should note model used so cost tracking is visible. Not in scope as automation, but document the trade-off.

## References

- Existing Codex implementation: `plugins/flow-next/scripts/flowctl.py:1522-1894` (`run_codex_exec`, `build_review_prompt`, `build_rereview_preamble`), `:5998-6770` (`cmd_codex_{impl,plan,completion}_review`)
- Existing RP implementation: `plugins/flow-next/scripts/flowctl.py:2474-2726`
- Backend selection cascade: `cmd_review_backend` at `flowctl.py:2679-2702`
- fn-2 spec (Codex backend template): `.flow/specs/fn-2.md`
- fn-28 spec (follow-up: unified backend spec parser): `.flow/specs/fn-28-*.md`
- flow-swarm copilot adapter (prompt temp-file pattern, text-mode choice): `~/work/flow-swarm/src/lib/backends/copilot.ts`
- flow-swarm adding-backends guide: `~/work/flow-swarm/docs/adding-backends.md`
- GitHub Copilot CLI programmatic reference: https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-programmatic-reference
- Copilot CLI command reference: https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-command-reference
