---
satisfies: [R2, R5, R6]
---
# fn-221-claude-cli-review-backend-claude-p-as-a.2 flowctl claude subcommands, surface pins, schema regen

## Description
Register `flowctl claude impl-review | plan-review | completion-review | validate | deep-pass` through the five shared parser builders and the generic `cmd_backend_review` driver, pin the new surface, add `test_claude_review_commands.py`, and regenerate the config schema and tracker manifest (R2, the schema half of R5, R6). Split from .1 because the parser sites are a separate sweep with their own pinned tests.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py`, `plugins/flow-next/scripts/hooks/ralph-guard.py` and its tests, `plugins/flow-next/tests/test_claude_review_commands.py` (new), `plugins/flow-next/tests/test_flowctl_surface.py`, `plugins/flow-next/tests/test_review_fanout.py`, `scripts/gen_flow_config_schema.py` and its generated artifact, the tracker manifest
**Touches:** [plugins/flow-next/scripts/flowctl.py, plugins/flow-next/scripts/hooks/ralph-guard.py, plugins/flow-next/tests/**, scripts/gen_flow_config_schema.py, plugins/flow-next/schema/**, plugins/flow-next/scripts/flowctl_tracker/**]

### Approach
- In each of `_add_impl_review_parser`, `_add_plan_review_parser`, `_add_completion_review_parser`, `_add_validate_parser`, `_add_deep_pass_parser` (`flowctl.py:51711-52045`): turn the `else: # cursor` branch into an explicit `elif backend == "cursor"` and add an `elif backend == "claude"` branch shaped like codex (effort help present, no sandbox flag); add `"claude"` to every `func = {...}[backend]` dict.
- `_backend_spec_help()` examples dict: add `claude:claude-opus-5:high`.
- Ralph guard (`plugins/flow-next/scripts/hooks/ralph-guard.py`): extend both the structural and the textual backend recognition so `flowctl claude impl-review|plan-review|completion-review|validate|deep-pass` are treated exactly like the cursor commands (the human-only recovery arguments such as `--force` and counter resets stay blocked under Ralph). Probe first: today `flowctl cursor impl-review fn-1.1 $FLAGS` is blocked and the `claude` spelling passes.
- Subparser block beside `p_cursor` (`flowctl.py:54858-54893`): `p_claude` with the five subcommands; do NOT register the fanout subcommands under it (fn-215 R15, `test_negative_gate`).
- Thin wrappers `cmd_claude_impl_review` / `_plan_review` / `_completion_review` over `cmd_backend_review(args, backend="claude", kind=...)` beside the cursor ones (`flowctl.py:46729-46741`); validate and deep-pass follow the cursor wrappers.
- `scripts/gen_flow_config_schema.py:65-68`: add `claude` to the description prose (full `backend[:model[:effort]]` grammar, like codex); the enum and pattern are generated from the registry. Run the generator and commit the artifact; run `python3 scripts/gen_tracker_manifest.py`.
- `test_claude_review_commands.py`: copy the `_flow_repo()` harness from `test_cursor_review_commands.py` and drive the REAL CLI entry (`flowctl claude impl-review <task> --base <sha> --json`) with `run_claude_exec` stubbed at the subprocess boundary (a fake `claude` that echoes the argv and stdin it received and returns a canned result JSON), not by mock-patching the handler.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl.py:51711-52045` — the five parser builders and their backend branches
- `plugins/flow-next/scripts/flowctl.py:54858-54893` — subparser registration
- `plugins/flow-next/scripts/flowctl.py:46685-46742` — cursor command wrappers
- `plugins/flow-next/tests/test_cursor_review_commands.py` — harness and receipt assertions to mirror
- `plugins/flow-next/tests/test_flowctl_surface.py:102-106` — surface pin
**Optional:**
- `plugins/flow-next/tests/test_review_fanout.py:2061-2075` — the negative gate that must keep passing (add `claude` to its backend tuple)
- `scripts/gen_flow_config_schema.py:468-490` — generated pattern (no edit)

### Key context
- Memory `test-production-path-not-parallel-construction`: invoke the real entry point.
- Memory `windows-path-shims-cannot-observe`: a PATH shim cannot observe spawns on Windows; stub at the Python boundary (`subprocess.run` argument capture) rather than a shell shim so the argv assertions run on all three CI OSes.

### Acceptance
- [ ] `flowctl claude impl-review|plan-review|completion-review|validate|deep-pass --help` all exist; `flowctl claude impl-review-fanout` is an argparse invalid choice
- [ ] Receipt from a stubbed run carries `mode: "claude"`, `model`, `effort`, `session_id` from the payload; argv is the fixed token list with `--tools Read Grep Glob --strict-mcp-config`, no `--allowedTools`, no Bash/Edit/Write token, and the prompt on stdin
- [ ] `deep-pass` and `validate` after a primary review resume the receipt's `session_id` (`--resume <sid>` in the stub's captured argv), write no diff file and append no transport note, and the primary dispatch's file is still present and unchanged when they run, including after HEAD has moved
- [ ] real-command regression: `flowctl claude impl-review <task> --base <sha>` → commit a fix → the same command again on the same receipt: the second run carries `--resume <sid>`, writes a new `<receipt-id>-<base7>-<head7>.diff`, names it in the prompt, and leaves the first file byte-identical
- [ ] Ralph guard tests: literal and expanded (`$FLAGS`) `flowctl claude impl-review ... --force` are blocked under the guard exactly as the cursor spelling is; the plain review command is allowed
- [ ] CLI missing → the shared backend-missing failure naming the install page; malformed payload → RETRY semantics, no verdict
- [ ] `test_flowctl_surface.py` and `test_review_fanout.py::test_negative_gate` updated and green; `test_flow_config_schema_drift` and `test_tracker_distribution` green after regen
- [ ] `cd plugins/flow-next/tests && python3 -m unittest test_claude_review_commands test_flowctl_surface test_review_fanout test_flow_config_schema_drift -q` green; ruff clean
## Acceptance
- [ ] TBD

## Done summary
Registered `flowctl claude impl-review | plan-review | completion-review | validate | deep-pass` through the five shared parser builders (the `else: # cursor` branch is now an explicit `elif`, `claude` added to every func dict and to `_backend_spec_help`), thin `cmd_claude_*` wrappers over `cmd_backend_review` / `_run_validator_pass` / `_run_deep_pass`, and a `p_claude` subparser block with no fan-out subcommands (fn-215 R15). The Ralph guard's `_REVIEW_BACKENDS` now names `claude`, so `flowctl claude <review> ... --force` and argument-position expansions are blocked exactly like the cursor spelling. `scripts/gen_flow_config_schema.py` prose names `claude` with its effort set; the schema artifact and the tracker manifest were regenerated. Review round 1 found `_resolve_session_pass_spec`'s strict foreign-`--spec` rejection was a `backend == "cursor"` special case, so `claude validate|deep-pass --spec codex:...` would have resumed with a foreign model id; it now keys on a `{cursor, claude}` grammar map.

Tests: `tests/test_claude_review_commands.py` (new) drives the real CLI entry (`flowctl.main`) with `subprocess.run` / `shutil.which` stubbed at the Python boundary - five-subcommand help + fan-out invalid choice; receipt `mode/model/effort/session_id`; fixed read-only argv (`--tools Read Grep Glob --strict-mcp-config`, no `--allowedTools`/Bash/Edit/Write) with the prompt on stdin naming the diff path and range, and the diff file observed present while the fake CLI runs; the real-command regression (review -> fix commit -> same command on the same receipt: `--resume <sid>`, new `<receipt>-<base7>-<head7>.diff`, first file byte-identical); deep-pass and validate after HEAD moves resuming with `--resume`, writing nothing, no transport note; missing CLI -> exit 2 `claude not found in PATH` before any spawn; not-JSON / wrong-type / `is_error` envelope with verdict text -> exit 2, no receipt, attempt journaled with `failure_class: nonzero_exit` and no verdict; foreign `--spec` rejected before spawn for the primary command and both session passes. Pins updated: `test_flowctl_surface.py` (five leaf paths), `test_review_fanout.py::test_negative_gate` (claude), `test_backend_spec.py` hook-wiring tuple, `test_ralph_guard.py::test_claude_review_dispatch_guarded_exactly_like_cursor` (blocked/allowed shapes, run red before the guard edit).

baseline: red (`test_flow_config_schema_drift` + `test_tracker_distribution` failed pre-edit - the regeneration gates this task owns, inherited from fn-221.1; every other focused module green). After: focused suites green, `python3 scripts/run_tests_parallel.py` green (204 files, 4775 tests), ruff clean; green receipt minted at `.flow/tmp/green-receipts/b0f974aa-unittest.json`. The codex-mirror-related failures task 1 anticipated did not materialise - the full suite is green at this commit; the mirror regen stays with task 3.

Follow-ups (not built): `require_claude()` reports only `claude not found in PATH` (same shape as codex/copilot/cursor; the reviewers flagged R2's "naming the install page" as unmet at the CLI level - a docs/skill-prose pointer or a URL in the message is a task .3/.4 decision). Interleaved commit 6091fed7 on this branch belongs to another agent.

Memory: captured `bug/integration/backend-special-case-in-a-shared-helper-2026-09-05` (a per-backend `== "cursor"` branch in a shared helper is an enumeration site the tuple sweep misses; regenerate the manifest after the last flowctl.py edit).

stage: impl-review - ran [codex fan-out round 1 NEEDS_WORK (1 merged finding) -> fix a3a0f44a -> round 2 NEEDS_WORK (stale manifest) -> a4903242 -> round 3 SHIP]
## Evidence
- Commits: 4584eea068beab87b3da7dd86fac53c32c72b601, a3a0f44a3322e4b027e2ac717b5a32f6360bf801, a49032424a8e6f0ef871c8d9122bf25023cc9519, b0f974aac7bd044c2560d7d78070fb9e0a81a8e0
- Tests: cd plugins/flow-next/tests && python3 -m unittest test_claude_review_commands test_cursor_review_commands test_backend_spec test_model_resolution test_flowctl_surface test_review_prompt_constraints test_review_fanout test_flow_config_schema_drift test_flow_config_schema test_tracker_distribution test_ralph_guard test_startup_bootstrap test_install_codex_legacy_cleanup test_install_opencode -q, python3 scripts/gen_flow_config_schema.py && python3 scripts/gen_tracker_manifest.py, python3 scripts/run_tests_parallel.py, uvx ruff@0.16.0 check .
- PRs:
stage: plan-sync - skipped(config: planSync.enabled != true)
