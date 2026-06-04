---
satisfies: [R2, R6, R7]
---

## Description
Author the core delegation mechanics in `references/codex-delegation.md` and wire them into the worker's Phase 2: the lifted `codex exec` invocation, the structured `--output-schema` result contract, the timeout-free background-launch + poll loop, and the per-batch effort model (gpt-5.5/medium floor + risk escalation). This is the **early proof point that BLOCKS fn-55.4–.6** — it must demonstrate that `codex exec` actually drives a task's implementation and returns a parseable result JSON, with MCP servers isolated so `--output-schema` isn't silently dropped.

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-work/references/codex-delegation.md`, `plugins/flow-next/agents/worker.md` (Phase 2 delegation hook)

## Approach
- Lift the invocation verbatim: `FLOW_DELEGATE_CODEX=1 codex exec --ignore-user-config -m gpt-5.5 -c 'model_reasoning_effort="medium"' $SANDBOX_FLAG --output-schema <schema> -o <result> - < <prompt>`. `$SANDBOX_FLAG` derives from `work.delegateSandbox` (yolo → `--dangerously-bypass-approvals-and-sandbox`; full-auto → `-s workspace-write`). Never emit deprecated `--full-auto`. The inline `FLOW_DELEGATE_CODEX=1` prefix is part of the ralph-guard canonical shape (consumed in fn-55.5) — keep it in the command string.
- **Always pass `-m`/`-c` explicitly** from `work.delegateModel`/effective effort. There is NO "defer to `~/.codex/config.toml`" path — `--ignore-user-config` ignores user codex config (MCP isolation wins), so model/effort must come from flow config.
- **MCP isolation (load-bearing):** `--output-schema` is silently dropped when MCP tools are active (openai/codex#15451). Use `--ignore-user-config` (skips `~/.codex/config.toml` incl. `[mcp_servers]`; we pass `-m`/`-c` explicitly so losing user model defaults is fine). **Prove empirically at build** that no MCP servers load (a project-level `.codex/config.toml` may still inject them). `--output-schema` is MANDATORY — NO runtime `--json` JSONL fallback (it would bypass the ralph-guard canonical shape + the poll/classify contract). If isolation can't be made reliable, fix it at build or the feature does not ship.
- Cross-check the flag shape against the existing proven review-path invocation at `flowctl.py:2841-2853` (same `-c 'model_reasoning_effort="..."'` quoting, stdin `-`, default model fallback `gpt-5.5`); this task adds `--output-schema` + `-o` + `--ignore-user-config`, which that path lacks — pin against `codex --version`.
- Result schema lifted verbatim (`{status, files_modified, issues, summary, verification_summary}`, `additionalProperties:false`).
- **Background-launch via the Bash `run_in_background` tool parameter** (not shell `&`), then poll the result file in **separate foreground** calls: `test -s "$RESULT_FILE" && jq -e . "$RESULT_FILE" >/dev/null` before `DONE` (non-empty alone accepts a touched/partial file).
- Per-batch effort: pick proportional to risk (medium default; high for auth/session/payments/migrations/external-API/retry-fallback; xhigh for architectural/cross-cutting), floor `effective_effort = max(picked, work.delegateEffort)`, emit `-c 'model_reasoning_effort="<value>"'`, never literal `"default"`, enum `none|low|medium|high|xhigh`.
- Wire into `worker.md` Phase 2: when the host-passed delegate flag is set, read this reference and delegate the current task's implementation; Phase 3 commit / Phase 4 review / Phase 5 done are untouched here.
- Scratch dir `.flow/tmp/codex-<task-id>/` (already gitignored).

## Investigation targets
**Required**:
- `plugins/flow-next/agents/worker.md:106-135` — Phase 2 Implement (+ `BASE_COMMIT` capture L108-113) / Phase 3 commit boundary
- `plugins/flow-next/scripts/flowctl.py:2841-2853` — existing proven `codex exec` invocation (flag shape, quoting, `-c model_reasoning_effort`, stdin `-`)
- `.flow/specs/fn-55-optional-codex-implementation.md` — API Contracts (invocation, MCP-isolation, schema, bg+poll) to lift verbatim
- `.flow/.gitignore` — confirms `tmp/` ignored (scratch dir)
**Optional**:
- `plugins/flow-next/skills/flow-next-impl-review/workflow-codex.md` — house style for a codex-backed mechanics reference

## Acceptance
- [ ] `references/codex-delegation.md` contains the verbatim-lifted invocation (inline `FLOW_DELEGATE_CODEX=1` prefix, `--ignore-user-config`, gpt-5.5/medium defaults, **always-explicit `-m`/`-c` from flow config — no defer-to-user-config path**, sandbox-flag derivation, `--output-schema` + `-o`, stdin `-`), the result schema JSON, and the bg-launch+poll snippet with the `jq -e` parse check.
- [ ] The reference states the MCP-isolation mechanism (`--ignore-user-config`, #15451) with `--output-schema` MANDATORY (no JSONL fallback), and the `--full-auto`-deprecated note (emit `-s workspace-write`).
- [ ] Per-batch effort logic documented: risk→effort mapping, `effective_effort = max(picked, config)` floor, emit `-c`, never literal `"default"`, enum `none|low|medium|high|xhigh`.
- [ ] **Early-proof demonstration** (manual smoke, `codex` installed + consent): one real task delegated via the bg-launch+poll loop produces a non-empty, JSON-parseable `result-batch-*.json` validating against the schema — with `--ignore-user-config` confirmed to suppress MCP-driven schema drop (incl. a project-level `.codex/config.toml` check). Recorded in the task evidence / local-dev smoke notes. **fn-55.4 does not start until this passes.**
- [ ] `worker.md` Phase 2 reads the reference + delegates only when the host flag is set; with the flag unset, Phase 2 is unchanged.
- [ ] Background launch uses the `run_in_background` Bash parameter (verified in the reference prose), not shell `&`.

## Done summary
_(pending implementation)_

## Evidence
_(pending implementation)_
