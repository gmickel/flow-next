# Unattended-run correctness fixes (audit wave 1)

## Goal & Context
<!-- Goal & Context: 70% [paraphrase], 30% [inferred] -->

The 2026-09-24 efficiency audit of flow-next found a set of bugs that produce a wrong result without raising an error, mostly on paths that run with no human watching: `flow --auto`, land, the rolling work scheduler, review receipts, and the Ralph guard hook. The user reviewed the audit's wave digest and accepted this wave as sensible bug fixes. It goes first because no speed or token work matters while an unattended run can build or merge the wrong spec, publish a SHIP receipt for a NEEDS_WORK review, or commit to the default branch.

Every item was re-checked against the code on main at 6.0.2 when this spec was written. Each fix is the smallest change that removes the wrong outcome, with a behavioral regression test.

## Architecture & Data Models

The fixes are independent and touch separate owners:

- flowctl core: config loading, `review-rounds record`, spec-JSON writers, `triage-skip`, fan-out dispatch metadata.
- flow skill (`flow --auto` instructions): argument parsing, review passthrough, terminal-state routing, backlog dispatch guards.
- work skill and worker agent: the branch step, the rolling SHIP path, host-backend contract, handover paths, Investigation-targets detection.
- plan-sync agent and its two dispatchers (work's plan-sync dispatch and `/flow-next:sync`).
- ralph-guard hook and its bash wrapper.
- flowctl_tracker sync-body push path.

No new subsystem is introduced. Where flowctl changes a command's behavior, the command shape stays the same; only validation and derived fields change.

## API Contracts

- `flowctl review-rounds record ... --output-file F [--receipt-target T --receipt-payload-file P]`: flowctl derives `verdict`, `review`, `suppressed_count`, `introduced_count`, `pre_existing_count` and `unaddressed` from F using its existing parsers (`parse_codex_verdict`, `parse_suppressed_count`, `parse_classification_counts`, `parse_unaddressed_rids` - JSON block first, prose fallback) and writes them into the published receipt. A payload field that disagrees with the derived value is an error (exit 2), not an override. Payload-only fields (`model`, `draws`, `id`, `mode`, `type`, `base`, `head`) pass through unchanged.
- `flowctl config set/get` and every config reader: an unparseable `.flow/config.json` is distinguishable from an absent one.
- `flowctl triage-skip`: unchanged flags; its receipt write becomes atomic.
- Tracker facade `push`: a new conflict subtype `tracker_diverged` on the existing conflict envelope.

## Edge Cases & Constraints

- All supported hosts (Claude Code, Codex, Cursor, Droid, Grok, OpenCode) keep working; skill edits regenerate the Codex mirror through `sync-codex.sh`.
- Receipt consumers (land, `flow --auto`, flow-swarm) see the same receipt fields; values become trustworthy, no field is removed or renamed.
- Lock order stays receipt lock first, then the per-spec review lock, as already documented.
- Plan-sync runs only when `planSync.enabled` is true or through `/flow-next:sync`; its fix affects only those paths.
- The Ralph guard must keep blocking every command it blocks today that is a real violation; only false positives and the bypass change.
- Windows: no new POSIX-only calls.

## Acceptance Criteria

- **R1:** An unparseable `.flow/config.json` is never treated as absent. Readers warn once on stderr naming the file and the parse error (line and column); `flowctl config set` refuses to write and exits non-zero with that message; `flowctl validate` reports a root error. A missing file keeps today's defaults behavior. Regression test: a config with a trailing comma survives `config set` byte-for-byte and `validate` fails. Errors: unreadable file (permissions) → same refusal as a parse error; valid JSON that is not an object → same refusal. [paraphrase]
- **R2:** `flowctl review-rounds record` derives the receipt's `verdict`, `review`, suppressed count, introduced/pre-existing counts and unaddressed R-IDs from the recorded output file with flowctl's existing public parsers, and rejects (exit 2, no state change) a receipt payload whose verdict or counts contradict the output. The RP impl-review and completion-review workflows stop computing these tallies in shell on the recorded (task-scoped) path; the standalone RP path, which does not call `record`, keeps its shell tally but made portable (POSIX awk, no three-argument `match`) and suffix-aware (`R4a`). Regression tests: output NEEDS_WORK + payload SHIP → refused; suffixed R-IDs appear in `unaddressed` from both JSON and prose outputs; the standalone tally runs under a non-GNU awk. Errors: output with no verdict → today's failure-class path unchanged; payload omits the fields → derived values fill them. [paraphrase]
- **R3:** Every read-modify-write of a spec JSON sidecar holds the same per-spec lock the review ledger uses (today 13 writers skip it, including set-branch, tracker sync-state writes, reopen-on-task-change, set-plan, dependency edits, close, ready/no-plan toggles, checkpoint restore and prospect promote), re-reading the file inside the lock. Regression test: concurrent `review-rounds increment` and `spec set-branch` loops lose no reservation or round. Errors: lock wait timeout → existing bounded-wait error, no partial write. [paraphrase]
- **R4:** `flowctl triage-skip` never replaces an open review: the impl-review skill runs triage only when the review route's action is a first-round `fanout`, and triage writes its receipt atomically. Regression test: with an open NEEDS_WORK receipt, a trivial-diff triage leaves the receipt unchanged. Errors: route probe fails → skip triage and run the full review (fail toward review). [paraphrase]
- **R5:** `flow --auto` accepts any spec id flowctl resolves (tracker-key ids included) as its scope argument and ends `NEEDS_HUMAN` with the reason when the argument does not resolve; it passes `--review` to plan, plan-review and work only when the user supplied one, and computes whether review is configured per spec. Regression test (skill contract test on the parser block or a flowctl resolution check): a `wor-17-x` id sets the scope; no `--review=ASK` is ever emitted. Errors: two spec arguments → first wins, second reported, as today. [paraphrase]
- **R6:** `flow --auto` routes a spec whose remaining open tasks are all `blocked` or escalated to `NEEDS_HUMAN` with the block reason instead of re-dispatching work, and takes no strike for it; the backlog-mode dispatch allowlist check runs inline in each dispatch block rather than as a shell function defined in an earlier block. Regression test: route classification for a spec with one done and one blocked task returns a human stop, not `work_planned`. Errors: mixed blocked and ready tasks → work proceeds on the ready ones as today. [paraphrase]
- **R7:** The work skill's branch step branches from the resolved default base (never a hard-coded `main`), checks out an existing branch of the same name instead of failing, and stops with a `BLOCKED:` line and non-zero exit when a git step actually fails. Regression test (scratch repo): existing branch, offline pull, and a default branch named `trunk` each end on the intended branch or a BLOCKED stop, never on the default branch. Errors: the `.flow/` changes the direct route and autonomy already permit before branching are carried as today and never trigger the stop; a checkout conflict with other uncommitted changes → BLOCKED with the git message. [paraphrase]
- **R8:** The Ralph guard stops producing false blocks and closes its bypass: the receipt-write check matches only an actual redirect target, the codex/copilot checks match only the command word of a shell segment, the `done` evidence gate's help exemption matches only a whole `-h`/`--help` token, and SubagentStop neither deletes the session state file nor applies the receipt gate to non-worker subagents. Its bash wrapper exits 0 before interpreter probing when `FLOW_RALPH` is not `1`. Regression tests: `ls …/receipts/*.json`, `grep copilot src/`, a commit message mentioning codex exec pass; `done … --summary-file /tmp/s-helper.md` without evidence is blocked; a scout's SubagentStop leaves state intact. Errors: no error surface beyond today's block messages. [paraphrase]
- **R9:** On the rolling and host-deferred routes, a task that reached SHIP after at least one NEEDS_WORK round gets the same memory auto-capture the worker's own review path runs, performed by the conductor. Errors: memory disabled → no capture, as today; capture failure → warning, never blocks `done`. [paraphrase]
- **R10:** The plan-sync agent can obtain every input its phases read: both dispatchers pass file paths (not embedded JSON bodies) for the glossary, decision and strategy inputs, `/flow-next:sync` sends `COMPLETED_TASK_IDS`, and the agent either receives the task and spec reads it needs as files or is allowed read-only shell access to flowctl. Regression test: the manual sync dispatch prompt contains no inlined glossary/decision JSON. Errors: an input source is empty → the documented empty default path, as today. [paraphrase]
- **R11:** The worker recognizes a task's Investigation targets whether the heading is `##` or the `###` form that task creation's H2-demotion produces. Errors: no error surface beyond detection. [paraphrase]
- **R12:** On the rolling route the `host` review backend has one contract: the host-deferred pointer applies to the single-worker wave path only; the conductor takes the review base from its own record of the task's integrated base, never from a shared temp file; NEEDS_WORK from impl-review is terminal and escalates, matching the rolling scheduler. Errors: no recorded base → derive from the task's evidence; never review with an empty base. [paraphrase]
- **R13:** Worker summary and evidence handover files are always task-unique paths chosen by the conductor, on every route (standard, host-deferred, rolling); the fixed `/tmp/summary.md` and `/tmp/evidence.json` fallbacks are removed from the worker's standard path. Errors: path not provided (direct manual worker run) → the worker picks a task-unique path under `.flow/tmp/` and reports it. [paraphrase]
- **R14:** Review fan-out records the round's identity before dispatch, and finalize/recovery reads the per-draw result files each draw already publishes, so a round whose host call is killed can still finalize the draws that completed. Regression test: a dispatch interrupted after one draw completes can be finalized for that draw. Errors: zero completed draws → the existing single-refund path. [paraphrase]
- **R15:** A body-writing tracker `push` on a linked spec returns a `conflict` with subtype `tracker_diverged` (hint: run reconcile) and writes nothing when the tracker's current body differs from the recorded tracker merge base; with no divergence it behaves as today. `push --status-only` never writes the body and is unaffected. The facade matrix test's push cell uses a remote body equal to the base, and a new cell asserts the conflict. Errors: no recorded base (first push) → today's behavior. [paraphrase]

## Boundaries

- [user] "impl-review ... focused on overengineering and slop and yagni": implementation review judges every change against the smallest correct fix; speculative generality, unused parameters, defensive branches for impossible states, duplicated helpers, and prose that restates code are findings.
- [user] "do not let it go into overengineering mode": no new config keys, flags, commands or abstractions beyond what an R-ID names; a fix that needs more than the named contract goes back to Gordon.
- Not in this wave: `review-rounds record --attach`, a `review-prompt` verb, and other review plumbing verbs (wave 5, fn-259).
- Not in this wave: smaller default outputs, anchor-bundle projection, listing changes (wave 4, fn-258).
- Not in this wave: the small hygiene bugs (plan-review `--files`, `SPEC_ID` placeholders, planning/audit/setup fixes) - wave 3, fn-257.
- Not in this wave: test-suite speed (wave 2, fn-256) and eval- or decision-gated items (wave 6, fn-260).
- No change to review rubric, review cap, stall guard, or parallel-draw merge semantics.

## Decision Context

These fixes remove wrong outcomes on unattended paths, so they come before any efficiency work. R2 derives receipt fields from the recorded output instead of trusting a host-authored payload because the output file is already read and parsed; trusting the payload is what lets a receipt contradict its own review. R3 extends the existing per-spec lock rather than adding a second mechanism. R8 keeps the guard's policy and fixes only its matching. R15 makes push refuse on divergence instead of adding a merge to push: reconcile already owns the three-way merge.

Removed at review as overengineering (round 1): defaulting push's `--flow-file` to the local spec - unrelated to the divergence fix; updating aggregate fan-out metadata after every draw - the per-draw files are already durable.

R8 guard convergence: commands containing grouping syntax (parentheses, backticks) or text the tokenizer cannot read get the base guard's full text rules as a floor, so they are never less strict than before; plain commands use command-word matching, which removes the false blocks and also catches quoting tricks the base text screen missed (`co''dex exec`). Rejected at review (round 7): chasing deliberate obfuscation such as `env -S "codex exec hi"` - the guard is a rail against an agent's accidental direct calls, not an adversarial boundary, and the base screen never was one.

## Strategy Alignment

- Design principle "deterministic machinery is reserved for unattended-trust rails (receipts, rollback, guard shapes, schemas)": R1-R4, R8, R14 and R15 repair exactly those rails.
- "Receipts are the portable product boundary": R2 makes receipt values match the recorded review without changing fields.
- Ralph autonomous mode track (`flow --auto` + land as the default path): R5-R7, R9, R12, R13 remove wrong outcomes on that path.

## Parked unknowns

- Whether tracker `push` is ever meant to overwrite a diverged tracker body (the docs describe reconcile's three-way merge but not push's intent). Resolved by Gordon's call before R15 is implemented; R15 as written assumes it is not.

## Requirement coverage

| R-ID | Task |
|---|---|
| R1 | fn-255.M (TBD - populate via /flow-next:plan) |
| R2 | fn-255.M (TBD - populate via /flow-next:plan) |
| R3 | fn-255.M (TBD - populate via /flow-next:plan) |
| R4 | fn-255.M (TBD - populate via /flow-next:plan) |
| R5 | fn-255.M (TBD - populate via /flow-next:plan) |
| R6 | fn-255.M (TBD - populate via /flow-next:plan) |
| R7 | fn-255.M (TBD - populate via /flow-next:plan) |
| R8 | fn-255.M (TBD - populate via /flow-next:plan) |
| R9 | fn-255.M (TBD - populate via /flow-next:plan) |
| R10 | fn-255.M (TBD - populate via /flow-next:plan) |
| R11 | fn-255.M (TBD - populate via /flow-next:plan) |
| R12 | fn-255.M (TBD - populate via /flow-next:plan) |
| R13 | fn-255.M (TBD - populate via /flow-next:plan) |
| R14 | fn-255.M (TBD - populate via /flow-next:plan) |
| R15 | fn-255.M (TBD - populate via /flow-next:plan) |
