---
satisfies: [R1, R3, R6]
---
# fn-221-claude-cli-review-backend-claude-p-as-a.1 claude registry entry, stdin runner, hooks and ladder

## Description
Add `BACKEND_REGISTRY["claude"]`, the unavailable-signature predicate, the version probe, the `run_claude_exec` runner (prompt on stdin, fixed argv), and the `_wire_backend_review_hooks` block, so the shared ladder driver resolves and dispatches `claude` like the other CLI backends (R1, R3). Split first because everything else is registry-driven and cannot be exercised until this resolves.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/tests/test_model_resolution.py`, `plugins/flow-next/tests/test_backend_spec.py`, `plugins/flow-next/tests/test_review_prompt_constraints.py`
**Touches:** [plugins/flow-next/scripts/flowctl.py, plugins/flow-next/tests/test_model_resolution.py, plugins/flow-next/tests/test_backend_spec.py, plugins/flow-next/tests/test_review_prompt_constraints.py]

### Approach
- Registry entry beside `cursor` (`flowctl.py:7970-8001`): `models` ranking `claude-fable-5-1`, `claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5` (probed 2026-09-05; comment the date), `efforts` `low|medium|high|xhigh|max`, `default_effort` `high`, `default_model == models[0]`.
- `_CLAUDE_UNAVAILABLE_MARKERS` + `_claude_model_unavailable(stdout_json, stderr)` beside the codex/cursor pair (`flowctl.py:4427-4451`): exactly the epic's R3 predicate: (`is_error` true AND `api_error_status == 404` AND the result text contains "issue with the selected model") OR stderr carries `[claude-code:unrecognized_model]`. A 404 without that text, or that text without a 404, with no stderr tag, is NOT the signature (transport failure, no ladder step, no cache write). Keep the markers a tuple, not a str (the prompt-pin scanner only reads str constants).
- `require_claude()` / `get_claude_version()` as one-liners over `shutil.which("claude")` and `claude --version`, memoised through `_CLI_VERSION_CACHE` (`flowctl.py:8507`).
- `run_claude_exec(prompt, spec, repo_root, ..., session_id=None, diff_range=...)` modelled on `run_cursor_exec` (`flowctl.py:8730-8988`) but: prompt goes to `input=` on stdin; argv is exactly `claude -p --output-format json --permission-mode dontAsk --tools Read Grep Glob --strict-mcp-config` plus `--model <id>` and `--effort <e>` (BOTH omitted at the ladder floor) plus `--resume <sid>` when a session id is passed; never `--allowedTools`, never a Bash, Edit or Write tool name; no argv transport cap and no `prompt_fit` fitter.
- Adapter `_claude_run_exec(prompt, *, session_id, repo_root, spec, resolution_out, args)` beside `_cursor_run_exec` (`flowctl.py:41977`). The primary-versus-optional discriminator is the DISPATCH KIND, never `session_id`: a re-review after fixes goes through `_backend_impl_review` → `_resume_session_from_receipt` → `_dispatch_backend_review` with the prior session id and a NEW base/head, and it is still primary. So `cmd_backend_review` (kinds impl/plan/completion) hands the adapter the captured range it records in the receipt (it already resolves `--base` and HEAD and computes numstat at `flowctl.py:41772`) through an explicit field on `args` (e.g. `args.claude_range = (base, head, receipt_id)`), and the adapter, whenever that field is present, writes `.flow/tmp/claude-review/<receipt-id>-<base7>-<head7>.diff` (the name IS the range identity: a collision means the same range and the same bytes, so `atomic_write`'s replace is a no-op; a changed base at the same head gets its own file) and appends the transport note (no shell is available; the diff for `<base>..<head>` is at that path; read it with Read). `_dispatch_session_pass` (`flowctl.py:37932`: deep pass, validate) sets no range field, so the adapter writes nothing and appends no note; the resumed session already holds the primary's diff and that file stays byte-identical. Never derive the range from the current HEAD inside the adapter.
- Diff-file guards (fixed, not YAGNI): `mkdir -p` the directory, refuse if the directory or the leaf `is_symlink()`, refuse if `Path.resolve()` leaves `<repo>/.flow/tmp`, write through `atomic_write` (`flowctl.py:2765`, temp + replace), fail the dispatch before spawning the CLI on any of those; the receipt-id key keeps concurrent reviews apart and a resumed pass never replaces a file a reviewer may be reading. Parse the single result JSON object (`type == "result"`); a non-JSON or non-result payload, or `is_error` without the signature, is a transport failure. Tail into `_dispatch_review_with_fallback` (`flowctl.py:4639-4738`) with the claude predicate; the ladder steps at most two rungs.
- `_resolve_claude_review_spec(args, task_id, spec_id=None)` beside `_resolve_cursor_review_spec` (`flowctl.py:46685-46728`): strict `--spec` parse that `error_exit`s on a non-claude backend; then `resolve_review_spec("claude", task_id, spec_id=spec_id)`, and coerce ANY resolved non-claude spec to `BackendSpec("claude").resolve()` (Claude ids do not cross over, same rationale as cursor).
- Hooks block in `_wire_backend_review_hooks` (`flowctl.py:42544-42632`): `run_exec`, `resolve_spec: _resolve_claude_review_spec`, `check_probe: get_claude_version`, `resume_modes: ("claude",)`, `track_prior_receipt_model: False`, `require_nonempty_sid: True`, `mint_session_id: False`, `has_sandbox: False`, `include_effort: True`, `extract_review` identity on the `result` text, `display_name: "Claude"`, `cli_label: "claude"`, `no_verdict_label: "Claude"`, `prompt_fit: None` (or the no-op value the driver accepts), `needs_persona_override: True`. Do not set `fanout_draws`.
- Receipt: the generic payload already writes `mode`, `model`, `effort`; pass the JSON `session_id` through so it lands in the receipt and the next round resumes it. `_receipt_model_effort` drops effort at the floor, so the runner must not send `--effort` there either (receipt and argv agree).

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:7899-8017` — registry shapes and the fn-76 invariant comment
- `plugins/flow-next/scripts/flowctl.py:4427-4451` — unavailable-marker predicates to mirror
- `plugins/flow-next/scripts/flowctl.py:8730-8988` — `run_cursor_exec`, `_parse_cursor_result`, `get_cursor_version`
- `plugins/flow-next/scripts/flowctl.py:46685-46728` — `_resolve_cursor_review_spec` (strict parse + coercion to mirror)
- `plugins/flow-next/scripts/flowctl.py:4792-4830` — `_receipt_model_effort` floor semantics
- `plugins/flow-next/scripts/flowctl.py:42544-42632` — hook wiring blocks
- `plugins/flow-next/tests/test_model_resolution.py` — `TestCursorLadder` (derive `CLAUDE_TOP` from the registry)
**Optional:**
- `plugins/flow-next/scripts/flowctl.py:8557-8716` — `run_copilot_exec` stdin branch on Windows (the stdin `input=` pattern)
- `plugins/flow-next/tests/test_prompt_text_pinned.py:245-276` — why the marker tuple is safe

### Key context
- Probed 2026-09-05 (Claude Code 2.1.260): a bad `--model` EXITS 0; the signature lives in the JSON (`is_error`, `api_error_status`, result text) and on stderr (`[claude-code:unrecognized_model]`). Exit code is not a signal.
- `--permission-mode` has no `default`; `dontAsk` is the headless choice. The CLI has no filesystem sandbox. `--allowedTools` only PRE-APPROVES: a user's own `permissions.allow` (this machine grants `Bash(git:*)`) stays reachable under it. `--tools Read Grep Glob` RESTRICTS the available built-in set; probed 2026-09-05: the child reports only Glob, Grep, Read and cannot create a file. `--strict-mcp-config` with no `--mcp-config` excludes MCP tools.
- `claude -p --resume <session-id>` continues a session; keep session persistence on (do not pass `--no-session-persistence`).
- `claude -p` with no positional reads the prompt from stdin; alias ids (`sonnet`) resolve to full ids in `modelUsage`.

### Acceptance
- [ ] `BackendSpec.parse("claude:claude-opus-5:xhigh")` resolves; an unknown effort raises naming the five accepted values; an unknown model warns and is accepted; `test_backend_spec.py` key-list pin includes `claude` and gains `test_claude_default_model` / `test_claude_effort_set` derived from the registry
- [ ] `test_model_resolution.py` `TestClaudeLadder`: steps on the full JSON signature, steps on the stderr tag, caches per version, floors without `--model`, never steps more than twice; negative fixtures: `is_error` + 404 without the selected-model text, and the selected-model text without a 404, both without the stderr tag, are transport failures with no ladder step and no cache write
- [ ] `test_review_prompt_constraints.py` hook-wiring pins list `run_claude_exec` / `get_claude_version`
- [ ] argv asserted as a fixed token list: `--tools` followed by exactly `Read Grep Glob`, `--strict-mcp-config` present, no `--allowedTools`, no Bash/Edit/Write token; prompt asserted on stdin; the diff file exists at `.flow/tmp/claude-review/<receipt-id>.diff` with the reviewed range's content before the stub runs
- [ ] adapter-boundary regression (the subcommands arrive in task 2): call `_claude_run_exec` with a range field and no session, then with the same receipt id, a session id and a new head: the second call carries `--resume <sid>`, writes a new `<receipt-id>-<base7>-<head7>.diff`, its stdin prompt names the new path and range, and the first file is byte-identical; a third call with the same head and a different base writes a third file and leaves the other two untouched
- [ ] an optional pass (`session_id` set, no range field) carries `--resume <sid>`, writes no file and appends no transport note, including after HEAD has moved
- [ ] guards: a symlinked `.flow/tmp/claude-review` directory or a symlinked leaf fails before spawn; a write is atomic (no partial file observable); two receipt ids write two files
- [ ] `_resolve_claude_review_spec`: explicit `--spec codex:...` exits 2; a configured `review.backend cursor:<model>` default coerces to the claude default; `claude:<model>:<effort>` from a per-task pin is honoured
- [ ] floor: argv has neither `--model` nor `--effort`, and the receipt records no effort
- [ ] `cd plugins/flow-next/tests && python3 -m unittest test_model_resolution test_backend_spec test_review_prompt_constraints -q` green; `uvx ruff@0.16.0 check plugins/flow-next/scripts/flowctl.py` clean
## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
