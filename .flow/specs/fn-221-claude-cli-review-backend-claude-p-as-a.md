## Overview

A team conducting flow-next from OpenAI Codex, Cursor, Grok Build, Factory Droid or OpenCode cannot get a Claude-family review verdict through the packaged review path. The registry offers `rp`, `codex`, `copilot`, `cursor`, `host` and `none`; `host` needs the harness to dispatch a Claude subagent, which Codex cannot, and Copilot's Claude models are the only packaged route. The `claude -p` bridge is documented in `flowctl usage` and `docs/orchestration.md` as an implementation-offload recipe and as "prompting a capability into existence" for a session-model reviewer, so a user can already get a Claude review by describing it. That route has no model ladder, no receipt of the model that ran, no round counter, and no fix-loop integration; it is a different surface every time someone types it.

This spec adds `claude` as a first-class CLI review backend with the same shape as the other CLI backends: a registry entry with an ordered model ranking, a headless runner over `claude -p`, the five review subcommands, one `workflow-claude.md` per review skill, a setup-menu row, mirror rewrites and platform notes. The cross-family rule is unchanged and advisory: from Claude Code the backend is same-family and the receipt says so; from every other harness it is the cross-family verdict that was missing.

## Scope

In: the `claude` registry entry and runner, the five `flowctl claude` subcommands, hook wiring so the shared review driver, receipts, ladder, round counter and fix loop apply unchanged, the three skill workflow files and every backend enumeration in skill prose, the setup menu row, the repo docs that enumerate backends, the config-schema prose, the codex mirror, and the tests.

Out: any change to `host`, the review prompts, the bridge recipes, or the flow-next.dev site (a separate repo edited by another agent during this work).

## Approach

Mirror the newest CLI backend end to end, adjusted for what the live CLI does (probed 2026-09-05 on Claude Code 2.1.260):

- The runner delivers the prompt on **stdin**, not argv: `claude -p` with no positional reads the prompt from stdin, which removes the argv transport cap the cursor and copilot runners carry and removes the hazard of a variadic tool-list flag swallowing a trailing positional. Every argv flag is a fixed token.
- Read-only by construction: the child gets **no shell and no write tool**. `--tools Read Grep Glob` restricts the CLI's available built-in set to those three (unlike `--allowedTools`, which only pre-approves and leaves a user's own `permissions.allow` grants such as `Bash(git:*)` reachable), `--strict-mcp-config` with no `--mcp-config` excludes every configured MCP tool, and `--permission-mode dontAsk` denies anything else without a prompt (the CLI has no `default` mode and no filesystem sandbox). Probed 2026-09-05: under that argv the child reports only Glob, Grep and Read and cannot create a file even with write grants present in user settings. Because the shared review prompt tells the reviewer to run `git diff <range>` itself, the runner materialises that diff to `.flow/tmp/claude-review/<receipt-id>.diff` (gitignored) and the backend's prompt note names the path and the range; the reviewer reads it with `Read`. A path is an identity, not a payload.
- The diff file is written by **every primary dispatch** and never by an optional pass, and the discriminator is the dispatch kind, not session continuity: the three review commands (`impl-review`, `plan-review`, `completion-review`) are primary whether or not they resume a session, and a re-review after fixes resumes the same receipt's session with a new base/head, so it writes a **new file whose name is the full range identity** (`.flow/tmp/claude-review/<receipt-id>-<base7>-<head7>.diff`) and its prompt carries the new path and range; a name collision therefore means the identical range and identical content, so a replacement is a no-op, and a changed base at an unchanged head lands in its own file. `deep-pass` and `validate` (the `_dispatch_session_pass` route) pass no range and write nothing; they resume the session that already read the primary's file, which stays byte-identical. Writes go through `atomic_write` after refusing a symlinked directory or leaf and checking the resolved path stays under `.flow/tmp`. Keying by receipt id, base and head keeps concurrent reviews, successive rounds and a changed base on distinct files.
- Sessions persist and resume: the CLI's `--resume <session-id>` continues a conversation, so re-reviews within a round, `deep-pass` and `validate` resume the primary session exactly as the cursor backend does; session transcripts live in the CLI's own session store on disk. Remaining flags: `--output-format json`, `--model <id>` and `--effort <e>` from the resolved spec.
- The model-unavailable signature is **not an exit code**: an unknown model exits 0 with `is_error: true`, `api_error_status: 404` and a result text starting "There's an issue with the selected model", plus a stderr line tagged `[claude-code:unrecognized_model]`. The unavailable predicate keys on those markers; every other `is_error` payload propagates as a transport failure.
- The effort set is the CLI's own: `low`, `medium`, `high`, `xhigh`, `max`; `default_effort` is `high`. The ranking ships with today's ids (`claude-fable-5-1`, `claude-opus-5`, `claude-sonnet-5`, `claude-haiku-4-5`), `default_model == models[0]` (fn-76), and the docs state ids beside a date only.
- Hook wiring follows the codex shape for effort (`include_effort: True`) and the cursor shape for sessions: `resume_modes: ("claude",)`, `require_nonempty_sid: True` (resume-only, never mint), `mint_session_id: False`, `has_sandbox: False`, `fanout_draws` absent (the first-round three-draw fan-out is codex-only by design, fn-215 R15, pinned by the negative-gate test); `session_id` in the receipt comes from the JSON `session_id` field and is what the next round resumes. `resolve_spec` is an explicit `_resolve_claude_review_spec(args, task_id, spec_id=None)`: strict `--spec` parse that rejects a non-claude backend, and coercion of any resolved foreign-backend spec to the claude default, because Claude model ids do not cross over (the cursor precedent). At the ladder floor the runner omits both `--model` and `--effort`, matching what the receipt records. `needs_persona_override: True` because `claude -p` loads the repo's `CLAUDE.md`, the same ambient-instruction hazard the cursor runner already neutralises.
- Grammar, `review-backend`, `task set-backend`, receipt payload and the fan-out are registry-driven today and need no per-backend code; the work is the registry entry, the hooks, the five parser sites (each of which has an `else: # cursor` branch that must become explicit), and the enumeration sweep. When the cursor backend landed, review went NEEDS_WORK three times, each round on another stale enumeration site, so the sweep is named per file in the tasks.

## Quick commands

```bash
cd plugins/flow-next/tests && python3 -m unittest test_claude_review_commands test_cursor_review_commands test_backend_spec test_model_resolution test_flowctl_surface test_review_prompt_constraints -q
./scripts/sync-codex.sh && ./scripts/sync-codex.sh && git status --short plugins/flow-next/codex
python3 scripts/gen_flow_config_schema.py && python3 scripts/gen_tracker_manifest.py && git status --short
```

Full gate once at the end: `python3 scripts/run_tests_parallel.py` plus `uvx ruff@0.16.0 check .`.

## Boundaries / non-goals

- No change to the `host` backend or its fail-closed cross-family rule.
- No implementation-offload route: the backend reviews; the bridge recipes in `flowctl usage` stay the way to have Claude write code from another host.
- No new config keys beyond the backend value; no changes to the review prompts or their pins.
- No first-round three-draw fan-out for `claude`: the fan-out subcommands stay registered under `flowctl codex` only (fn-215 R15); `claude` gets the fix loop and the round counter like `copilot` and `cursor`.
- No new receipt field for family: `mode: "claude"` plus `model` already name the family, and the skills' same-family advisory line reads those.
- No `Bash`, `Edit` or `Write` tool for the reviewer in any form, and no MCP tools; the diff arrives by path.
- No `--list-models` style discovery: the CLI has none; the ladder steps the static ranking only.
- No env scrubbing for nested sessions: `claude -p` runs correctly from inside a Claude Code session (probed), so the runner passes the environment through like the other runners.
- No flow-next.dev edits in this spec; the site follows at release time in the separate repo.

## Strategy Alignment

Active tracks served by this plan:
- **Cross-platform parity** — Codex, Cursor, Grok Build, Droid and OpenCode hosts gain the Claude-family review verdict that only Claude Code could reach through `host`.
- **Spec-driven team patterns** — a Claude review from any host now carries the same receipt, ladder and fix-loop contract as every other backend, so the review record reads the same across a team's harness mix.

## Decision context

- A packaged backend rather than a documented prompt because the prompt route already works and that is exactly why it hides the gap: it gives a verdict with no ladder, no model in the receipt, no round counter and no fix-loop integration, so two teams asking for "a Claude review" from Codex get two different review surfaces.
- Mirror the CLI-backend shape (cursor for the runner, session resume and skill files, codex for the effort axis) rather than invent a new one; the CLI resumes by session id, so the session hooks take the cursor resume-only shape.
- Stdin transport over argv: probed on the live CLI, it is the simpler path and eliminates two hazards (argv cap, variadic flag) instead of managing them. Rejected an argv path with a size fitter as the symptom of the wrong transport.
- Same-family use stays allowed and recorded instead of refused because refusal is `host`'s job and a Claude Code user who wants a fresh-process Claude second opinion is making a legitimate, receipted choice.
- The unavailable predicate reads the JSON `is_error` payload and the stderr tag because the CLI exits 0 on a bad model; an exit-code ladder would never step.
- `--tools` rather than `--allowedTools`: the latter pre-approves without restricting, so a user's own `Bash(git:*)` grant would survive it, and a pre-approved `git diff` still permits `git diff --output=<workspace-file>`; the CLI has no filesystem sandbox, so read-only is enforced by making the three read tools the only tools that exist for the child, and delivering the diff by path. Rejected a deny-pattern list for dangerous flags as an enumeration race.
- Resume over fresh calls: the CLI resumes by session id, so the deep pass and validator run against the session that already holds the reviewed diff, the contract the shared deep-pass prompt assumes; a fresh-call design would have handed the deep pass only the primary findings.
- Rejected reading the routing block's `reviewer` tier inside the backend: model resolution stays the spec grammar and the registry, as for every CLI backend; the routing block steers the host's choice of backend spec, not the backend's internals.

## Acceptance Criteria

- **R1:** `review.backend claude`, the spec form `claude:<model>:<effort>`, `--review=claude`, and per-task `set-backend` all resolve through `BACKEND_REGISTRY["claude"]` with `default_model == models[0]` and efforts `low|medium|high|xhigh|max`; `flowctl review-backend` prints `claude` for a configured repo. Errors: an unknown effort is rejected at parse time with the accepted set named; an unknown model warns and is accepted.
- **R2:** `flowctl claude impl-review`, `plan-review`, `completion-review`, `validate` and `deep-pass` exist, dispatch `claude -p` with the prompt on stdin, `--output-format json`, `--permission-mode dontAsk`, `--tools Read Grep Glob`, `--strict-mcp-config`, no `--allowedTools`, no Bash or write tool, the resolved `--model`/`--effort`, and `--resume <session_id>` on a deep pass, validate or same-round re-review; every primary dispatch (the three review commands, resumed or not) writes the reviewed diff to `.flow/tmp/claude-review/<receipt-id>-<base7>-<head7>.diff`, one file per distinct range, (atomic, symlink-refusing, contained under `.flow/tmp`) and names it in the prompt note, while `deep-pass` and `validate` write nothing and reuse the primary's file; receipts carry `mode: "claude"`, `model`, `effort`, and `session_id` from the JSON payload. Errors: CLI missing → the shared backend-missing failure naming the install page; `is_error: true` that is not the model signature, or a payload that is not the result JSON → transport failure with RETRY semantics, never a verdict; a symlinked scratch directory or leaf, a resolved path outside `.flow/tmp`, or a failed diff write → the dispatch fails before the CLI is spawned.
- **R3:** The resolution ladder steps down the ranking at most twice on the model-unavailable signature, which is exactly: (`is_error` true AND `api_error_status` 404 AND the result text names the selected model) OR the `[claude-code:unrecognized_model]` stderr tag; a 404 without that text, or that text without a 404, with no stderr tag, is a transport failure; caches per CLI version, and floors by omitting both `--model` and `--effort` (the receipt records no effort at the floor); any other failure propagates unchanged. Errors: an exit-0 error payload without the signature is a transport failure, not a ladder step.
- **R4:** Each of the three review skills carries `workflow-claude.md` and a routing-table row, every backend enumeration in their `SKILL.md`, `workflow-common.md`, `backend-specs.md` and `backend-at-a-glance.md` names `claude` with its grammar and the same-family advisory line for Claude Code hosts, the operational consumers outside those skills (the work, plan and pilot skills' backend lists, the work `REVIEW_MODE` enum, the impl-review optional-phases backend case arms, and the `REVIEW_MODE` enum the codex-mirror generator emits from its own heredoc) accept `claude`, the Ralph guard recognises `flowctl claude ...` review commands exactly as it recognises the cursor ones (so `--force` and the other human-only recovery arguments are blocked for `claude` too), and the fix loop and round counter run for `claude` as for `cursor`. Errors: none beyond the skills' existing malformed-verdict handling.
- **R5:** Setup offers `claude` in the review menu when the CLI is on PATH; `orchestration.md` "Route the reviews", `flowctl.md` (subcommand roster, config table, ladder section, a `### claude` subsection), `platforms.md` (reach plus the same-family caveat on Claude Code), each `docs/reach/*.md` page, `templates/usage.md`, `troubleshooting.md`'s signature explainer, the root `README.md` adversarial-gates row, and the config-schema description prose document the backend; `sync-codex.sh` twice yields a clean mirror. Errors: none.
- **R6:** `test_claude_review_commands.py` drives the real command path with a stubbed runner (receipt shape, stdin transport and fixed argv, `--tools` carrying exactly the three read tools and no `--allowedTools`, the diff file present with the reviewed range before the primary dispatch, a primary review followed by a fix commit and a re-review on the same receipt delivering a new diff file for the new range with the original untouched, a changed base at an unchanged head landing in its own file, a deep pass after HEAD moves resuming with `--resume` and writing nothing, a symlinked scratch path refused before spawn, the exact unavailable predicate with its two negative fixtures, the Ralph guard blocking `flowctl claude impl-review ... --force`, foreign `--spec` rejected and foreign configured defaults coerced, `--model` and `--effort` both omitted at the floor with the receipt matching, ladder on the signature only, exit-0 error payload without the signature is a transport failure, fan-out subcommands rejected by argparse); `test_model_resolution.py` and `test_backend_spec.py` derive the `claude` cases from the registry; the surface and hook-wiring pins list the new commands; the full parallel suite and ruff are green. Errors: none.

## Early proof point

Task fn-221-claude-cli-review-backend-claude-p-as-a.1 validates the core approach (the registry entry plus a stdin-transport runner steps the ladder on the probed signature and returns a parsed verdict through the shared driver). If it fails, re-evaluate the stdin transport and the signature markers before continuing with .2 onward.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1  | Registry entry and grammar resolution | fn-221-claude-cli-review-backend-claude-p-as-a.1 | — |
| R2  | Five subcommands, argv/stdin shape, receipts, error handling | fn-221-claude-cli-review-backend-claude-p-as-a.2 | — |
| R3  | Ladder on the probed signature, cache, floor | fn-221-claude-cli-review-backend-claude-p-as-a.1 | — |
| R4  | Skill workflow files and enumeration sweep | fn-221-claude-cli-review-backend-claude-p-as-a.3 | — |
| R5  | Setup menu, repo docs, schema prose, mirror | fn-221-claude-cli-review-backend-claude-p-as-a.3, fn-221-claude-cli-review-backend-claude-p-as-a.4 | — |
| R6  | Tests and the full gate | fn-221-claude-cli-review-backend-claude-p-as-a.1, fn-221-claude-cli-review-backend-claude-p-as-a.2 | — |

## References

- Prior backend additions: fn-74 (cursor), fn-76 (ranking invariant and ladder), fn-90 (cursor convergence), fn-123/fn-126 (host cross-family rule).
- Memory: `bug/integration/adding-a-review-backend-sweep-all-2026-06-29` (sweep every enumeration site), `knowledge/workflow/audit-sync-codexsh-during-planning-for-2026-04-30`, `bug/test-failures/test-production-path-not-parallel-construction-2026-05-21`, `knowledge/best-practices/windows-path-shims-cannot-observe-2026-08-11`.
