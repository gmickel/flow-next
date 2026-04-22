## Description

Add the three Copilot review subcommands (`impl-review`, `plan-review`, `completion-review`) — the workhorses that flowctl skills and Ralph invoke. Mirrors `cmd_codex_*_review` at `flowctl.py:5998-6790`.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`

## Approach

Three new commands, each mirroring the codex counterpart with these adaptations:

- **Resolve model + effort**: read `FLOW_COPILOT_MODEL` (default `claude-opus-4.5`) and `FLOW_COPILOT_EFFORT` (default `high`) at the top of each function, after args parsing. These flow into `run_copilot_exec` and into the receipt.
- **Session UUID**: if prior receipt exists with `mode == "copilot"`, read its `session_id`. Else generate `str(uuid.uuid4())`.
- **Context gathering**: call `gather_context_hints(base_branch)` and `get_embedded_file_contents(files, budget_env_var="FLOW_COPILOT_EMBED_MAX_BYTES")` — same API as codex commands, just the budget env var name changes. (Confirmed landed in task 2: `get_embedded_file_contents` at `flowctl.py:1008` accepts `budget_env_var` kwarg with `FLOW_CODEX_EMBED_MAX_BYTES` default; codex call sites unchanged.)
<!-- Updated by plan-sync: task 2 landed the budget_env_var kwarg at flowctl.py:1008 as specified; no further changes needed there -->
- **Prompt build**: call `build_review_prompt(...)` / `build_rereview_preamble(...)` / `build_completion_review_prompt(...)` / `build_standalone_review_prompt(...)` **unchanged** — XML scaffold + `<verdict>` tag is backend-agnostic (per repo-scout verification).
- **Invoke `run_copilot_exec`** from task 1.
- **Error handling**: match codex patterns (`flowctl.py:6136-6176`). SKIP sandbox-failure branch (copilot has no sandbox concept). Handle:
  - Non-zero exit → unlink stale receipt → `error_exit(f"copilot -p failed: {msg}", code=2)`
  - Missing verdict despite exit 0 → unlink stale receipt → `error_exit(..., code=2)`
  - Timeout → same as non-zero exit path
- **Receipt writing** — same pattern as codex (`flowctl.py:6183-6204` and parallel blocks). Add to the receipt dict:
  - `mode: "copilot"`
  - `session_id: <uuid>`
  - `model: <resolved model>`
  - `effort: <resolved effort>`
  - Everything else (type, id, base, verdict, timestamp, review, iteration if RALPH_ITERATION set, focus if provided) stays the same.
- **Argparse wiring** — extend the `p_copilot` subparser created in task 2 (lives at `flowctl.py:8053`, currently only has `check`) with `impl-review`, `plan-review`, `completion-review` subcommands. Mirror the codex subparser flags at `flowctl.py:7710-7777` exactly (`--base`, `--files`, `--receipt`, `--focus`, etc.). Do NOT recreate the `p_copilot = subparsers.add_parser("copilot", ...)` block — it already exists; just add parsers to the existing `copilot_sub` subparsers object.
<!-- Updated by plan-sync: task 2 landed p_copilot at flowctl.py:8053 with only check subcommand; task 3 extends existing copilot_sub, not creates new -->

## Investigation targets

**Required:**
- `plugins/flow-next/scripts/flowctl.py:5998-6222` — `cmd_codex_impl_review` (master template; note receipt structure at 6183-6204)
- `plugins/flow-next/scripts/flowctl.py:6224-6430` — `cmd_codex_plan_review`
- `plugins/flow-next/scripts/flowctl.py:6574-6790` — `cmd_codex_completion_review`
- `plugins/flow-next/scripts/flowctl.py:6136-6176` — error handling patterns (sandbox branch SKIPPED for copilot)
- `plugins/flow-next/scripts/flowctl.py:6101-6113`, `:6314-6326`, `:6671-6683` — receipt read / session_id threading on re-review

**Optional:**
- `plugins/flow-next/scripts/flowctl.py:1682-1996` — `build_review_prompt` + `build_rereview_preamble` (reused verbatim, confirmed backend-agnostic)
- `.flow/specs/fn-27-copilot-review-backend.md` §Receipt Schema

## Acceptance

- [ ] `flowctl copilot impl-review <task-id> --base <branch> --receipt <path>` runs a live review, writes receipt with verdict + session_id + model + effort
- [ ] Re-invocation with same `--receipt` path resumes the session (`~/.copilot/session-state/<uuid>/` grows new events.jsonl entries)
- [ ] `flowctl copilot plan-review <epic-id> --files <a,b,c> --receipt <path>` same shape
- [ ] `flowctl copilot completion-review <epic-id> --receipt <path>` same shape
- [ ] Receipt JSON parses with required keys: `type, id, mode, verdict, session_id, model, effort, timestamp, review`
- [ ] `mode == "copilot"` on every receipt
- [ ] Error paths: stale receipt gets unlinked on non-zero exit or missing verdict
- [ ] Argparse: `flowctl copilot {impl-review,plan-review,completion-review} --help` shows expected flags
- [ ] `FLOW_COPILOT_MODEL=claude-haiku-4.5 FLOW_COPILOT_EFFORT=low flowctl copilot impl-review ...` is honored in receipt fields
- [ ] `RALPH_ITERATION=3 ...` stamps iteration in receipt (same as codex)

## Done summary

(filled in when task completes)

## Evidence

(filled in when task completes)
