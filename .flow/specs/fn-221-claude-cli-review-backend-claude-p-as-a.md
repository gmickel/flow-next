## Goal & Context

A team conducting flow-next from OpenAI Codex, Cursor, Grok Build, Factory Droid or OpenCode cannot get a Claude-family review verdict through the packaged review path. The registry offers `rp`, `codex`, `copilot`, `cursor`, `host` and `none`; `host` needs the harness to dispatch a Claude subagent, which Codex cannot, and Copilot's Claude models are the only packaged route. The `claude -p` bridge is documented in `flowctl usage` and `docs/orchestration.md` as an implementation-offload recipe and as "prompting a capability into existence" for a session-model reviewer, so a user can already get a Claude review by describing it. That route has no model ladder, no receipt of the model that ran, no three-draw fan-out on the first round, and no fix-loop integration; it is a different surface every time someone types it.

This spec adds `claude` as a first-class CLI review backend with the same shape as `cursor`: a registry entry with an ordered model ranking, a headless runner over `claude -p`, the five review subcommands, one `workflow-claude.md` per review skill, a setup-menu row, mirror rewrites and platform notes. The cross-family rule is unchanged and advisory: from Claude Code the backend is same-family and the receipt says so; from every other harness it is the cross-family verdict that was missing.

## Architecture & Data Models

- `BACKEND_REGISTRY["claude"]` (flowctl.py, beside `cursor`): `models` is an ordered quality ranking, strongest first, with `default_model == models[0]` (the fn-76 invariant); initial ranking `claude-fable-5-1`, `claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5`. `efforts` is the set `claude --effort` accepts (`low`, `medium`, `high`, `max`), `default_effort` `high`. Unknown explicit models warn and are accepted; the effort axis stays strict, as for the other backends.
- `run_claude_exec(prompt, spec, repo_root, ...)` mirrors `run_cursor_exec`: argv is `claude -p <prompt> --output-format json --model <id> --effort <e> --allowedTools <read-only set> --permission-mode default` with stdin from `/dev/null`; the prompt precedes `--allowedTools` because that flag is variadic. The read-only tool set is `Read`, `Grep`, `Glob`, and `Bash(git diff:*)`, `Bash(git log:*)`, `Bash(git show:*)`; never `Edit`, `Write`, or unrestricted `Bash`, since the reviewer reads untrusted diff content. The model-unavailable signature is the CLI's model-not-found error text, captured on the first live probe and encoded as `_CLAUDE_UNAVAILABLE_MARKERS`; the ladder steps down the ranking at most two rungs on that signature only, and the floor omits `--model`. Any other failure propagates unchanged. Version probe `get_claude_version()` from `claude --version` keys the resolution cache like the other CLIs.
- Subcommands `flowctl claude impl-review | plan-review | completion-review | validate | deep-pass` register under one `claude` parser and route through the shared review-dispatch helpers exactly as the `cursor` subcommands do; receipts carry `mode: "claude"`, the resolved `model`, `effort`, and `session_id: null` (no resume; a re-review is a fresh `-p` call carrying the merged prior-finding container, the same convention `host` documents).
- Skills: `workflow-claude.md` in `flow-next-impl-review`, `flow-next-plan-review` and `flow-next-spec-completion-review`, each a copy of the corresponding `workflow-cursor.md` with the backend name, the argv notes, and the receipt fields changed; `SKILL.md` routing tables gain the `BACKEND=claude` row; `references/backend-specs.md` and `backend-at-a-glance.md` gain the grammar line `claude[:<model>[:<effort>]]`. Round-one three-draw fan-out and the fix loop apply as they do to `codex` and `host`.
- Setup: `flow-next-setup` lists `claude` in the review-backend menu when `claude` is on PATH, with the same rp-eligibility gating pattern; `review-backend` resolution and `task set-backend` accept the new value through the registry with no special case.
- Mirror and platforms: `sync-codex.sh` needs no new transform (the backend name is not a Claude-only tool dispatch), but its guards must stay green; `docs/platforms.md` gains one row per harness stating reach (`claude` CLI installed and authenticated) and the same-family caveat on Claude Code; `docs/reach/*.md` each gain one dated line; `docs/orchestration.md` "Route the reviews" and `flowctl.md` gain the backend.
- Tests: `test_claude_review_commands.py` mirrors `test_cursor_review_commands.py` (receipt shape, argv, no `--effort` when floor, read-only tool set present, ladder on the signature, fan-out round counting); `test_model_resolution.py` gains the `claude` ladder cases derived from the registry; `test_backend_spec.py` parses the new grammar; the prompt pins are untouched because the review prompts are shared.

## API Contracts

- `flowctl config set review.backend claude[:<model>[:<effort>]]`, `FLOW_REVIEW_BACKEND=claude...`, `--review=claude`, and `flowctl task set-backend <task> --review claude:<model>` all resolve through the registry.
- `flowctl claude impl-review <task-id> [--base <sha>] [--model <id>] [--effort <e>] --json` and the four siblings emit the same JSON envelope as the `cursor` commands: `success`, `verdict`, `model`, `effort`, `receipt`, `resolution` (happy path or ladder record).
- Receipt schema: identical to `cursor` receipts with `mode: "claude"`; consumers (convergence ratchet, pilot, land, make-pr's verification block) need no change.
- Errors: `claude` not on PATH → the same "backend CLI missing" failure the other CLI backends raise, naming the install page; unauthenticated CLI → the CLI's own error propagates unchanged; a malformed `--output-format json` payload → `<promise>RETRY</promise>` semantics as for the other backends, never a self-issued verdict.

## Edge Cases & Constraints

- Same-family review on Claude Code: allowed, receipt records the family, the skills' cross-family advice line names it as correlated; no fail-closed behaviour (that is `host`'s contract, not this one).
- The variadic `--allowedTools` flag swallows trailing positionals: the runner places the prompt first and every test asserts argv order.
- Windows: the CLI launcher is `claude.cmd`; reuse the existing launcher-resolution helper the cursor and copilot runners use.
- Ralph mode: the backend works under `FLOW_RALPH=1` like the other CLI backends; no new hook matcher is needed because the runner is a subprocess, not a tool call.
- No bridge inside a bridge: when the host itself is `claude -p` (Ralph on Claude Code), the backend still works, but the skills' guidance prefers `codex` or `host` there for family independence.
- Effort names differ from codex (`max` instead of `xhigh`); the spec grammar passes them through untranslated and the registry validates.

## Acceptance Criteria

- **R1:** `review.backend claude`, the spec form `claude:<model>:<effort>`, `--review=claude`, and per-task `set-backend` all resolve through `BACKEND_REGISTRY["claude"]` with `default_model == models[0]`; `flowctl review-backend` prints `claude` for a configured repo. Errors: an unknown effort is rejected at parse time with the accepted set named; an unknown model warns and is accepted.
- **R2:** `flowctl claude impl-review`, `plan-review`, `completion-review`, `validate` and `deep-pass` exist, dispatch `claude -p` with the prompt before `--allowedTools`, a read-only tool set, `--output-format json`, stdin from `/dev/null`, and write receipts with `mode: "claude"`, `model`, `effort`, `session_id: null`. Errors: CLI missing → the shared backend-missing failure naming the install page; malformed JSON → RETRY, never a verdict.
- **R3:** The resolution ladder steps down the ranking at most twice on the captured model-unavailable signature, caches per CLI version, and floors by omitting `--model`; any other failure propagates unchanged. Errors: covered by the ladder tests derived from the registry.
- **R4:** Each of the three review skills carries `workflow-claude.md` and a routing-table row, `backend-specs.md` and `backend-at-a-glance.md` carry the grammar, and the first-round three-draw fan-out and fix loop run for `claude` as for `codex`. Errors: none beyond the skills' existing malformed-verdict handling.
- **R5:** Setup offers `claude` in the review menu when the CLI is on PATH; `platforms.md`, the reach pages, `orchestration.md` "Route the reviews", and `flowctl.md` document the backend and the same-family caveat on Claude Code; `sync-codex.sh` twice yields a clean mirror. Errors: none.
- **R6:** `test_claude_review_commands.py` covers R2 and R3 by driving the real command path with a stubbed CLI; `test_backend_spec.py` covers R1; the full parallel suite and ruff are green. Errors: none.

## Boundaries

- No change to the `host` backend or its fail-closed cross-family rule.
- No implementation-offload route: the backend reviews; the bridge recipes in `flowctl usage` stay the way to have Claude write code from another host.
- No new config keys beyond the backend value; no changes to the review prompts or their pins.
- Model ids in the ranking are examples verified on the day of the change and are expected to rotate; the docs state ids only beside a date.

## Quick commands

- `cd plugins/flow-next/tests && python3 -m unittest test_claude_review_commands test_cursor_review_commands test_backend_spec test_model_resolution -q`
- `./scripts/sync-codex.sh && ./scripts/sync-codex.sh && git status --short plugins/flow-next/codex`

## Decision Context

A packaged backend rather than a documented prompt because the prompt route already works and that is exactly why it hides the gap: it gives a verdict with no ladder, no model in the receipt, no fan-out and no fix-loop integration, so two teams asking for "a Claude review" from Codex get two different review surfaces. Mirroring `cursor` rather than `codex` because `cursor` is the newer registry shape (ranking plus a list-models fallback) and its runner already handles a CLI that has no resume; `claude -p` has none either. Same-family use stays allowed and recorded instead of refused because refusal is `host`'s job and a Claude Code user who wants a fresh-process Claude second opinion is making a legitimate, receipted choice. The ranking ships with today's ids under a date because every other backend does; the ladder, not the list, is the durable part.
