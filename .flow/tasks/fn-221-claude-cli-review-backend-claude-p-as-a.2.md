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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
