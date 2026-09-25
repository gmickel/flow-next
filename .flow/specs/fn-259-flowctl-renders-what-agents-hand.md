# flowctl renders what agents hand-assemble (audit wave 5)

## Goal & Context
<!-- Goal & Context: 70% [paraphrase], 30% [inferred] -->

The 2026-09-24 efficiency audit found that the make-pr redesign's lesson generalizes. In make-pr, moving rendering into flowctl and showing one validated skeleton cut output tokens 62%, tool calls 22 to 13, and wall clock 60%. The cost was never the rendered text; it was agents hand-assembling structured output, discovering schemas through repeated validation errors, and spending several tool turns on mechanical lookups that one deterministic call could answer.

This spec applies that lesson to the remaining places where agents still do mechanical work by hand: the `flow --auto` hop classification, land/tail waiting, the rolling scheduler's admission arithmetic and evidence assembly, the review round's prompt and receipt plumbing, the tracker push/pull/reconcile call chains, plan/capture/refine preflight and bulk task authoring, and the prospect, QA, memory-audit, setup and map skills.

Every change keeps judgment with the host agent. flowctl gains only zero-judgment plumbing: rendering, validating, counting, joining state it already reads, and reporting every error in one pass. The user's standing constraints for this wave: "make sure we don't break anything" and "do not let it go into overengineering mode".

## Architecture & Data Models

Three kinds of change, all additive:

- **New read-only snapshot/verb output** that bundles state a skill currently gathers with several calls (hop classification snapshot, preflight bundle, tracker `--prepare`, setup status, rolling admission view).
- **New write verbs that render and validate a skill-authored JSON payload** (prospect artifact, QA receipt, memory audit apply, pilot strike record), replacing inline bash/Python/jq assembly. The skill keeps authoring the judgment fields; flowctl computes derived fields (counts, ids, timestamps, commit lists) and writes atomically.
- **Fewer, cheaper calls inside existing verbs** (tracker push/status call reduction, connection reuse, lazy imports) with unchanged outputs.

Skill prose changes only where a skill switches from hand-assembly to the new verb, or where a wait/dispatch rule is clarified. Wave 1 (fn-255) already makes `flowctl review-rounds record` derive verdict, review body and tallies from the output file; this spec builds on it and does not redo it.

## API Contracts

All shapes below are new and additive; the exact flag spelling is the implementer's, the behavior is the contract.

- `flowctl judge --preset route --spec <id> --json` — when the external judge is unavailable (`no_key`, `disabled`), the response still carries the code-computed lifecycle decision and the PR observation, with `available: false` describing only the judge answers.
- `flowctl pilot snapshot [--spec <id>] --json` — one read returning run guards, the config values `flow --auto` consumes, the spec-aware review backend, ready candidates with chain / other-actor claims / strikes, the selected spec, lifecycle, PR state `{open, merged, merged_head, closed, probe_failed}` (open PRs joined by `branch_name` from one listing), QA freshness, branch name and existence, and the before-dispatch task snapshot.
- `flowctl pilot strikes record <spec> --stage <s> --reason <r> --json` → `{count, unreadied}`; one counter per spec (stage/reason are metadata); unreadies the spec at count 2 (the current skill rule, moved, not changed).
- `flowctl ready --spec <id> --json` gains parsed `touches` and transitive `depends_on` per task; `--admit --in-flight <ids> --cap <n>` returns `{admitted, held: [{id, reason}]}` from the mechanical checks only.
- `flowctl done <task> --range <base>..<head> [--test <cmd>]... [--summary-file -]` — computes `commits` and `base_commit` itself for contiguous task history; stdin summary accepted; explicit evidence lists remain for interleaved histories.
- `flowctl judge --preset tier --task <id> ...` — assembles the tier state from the task and returns `tier_line`, `spawn_model`, `implementer`.
- `flowctl sync active --json` gains the resolved per-event ops map.
- `flowctl review-prompt <kind> <id> --axis <a> --out <path>` — writes the dispatch prompt file flowctl already knows how to build (`build_review_prompt`, `build_rereview_preamble`).
- `flowctl review-rounds record ... --attach` and `review-rounds increment --base <sha> --head <sha>` (diff identity computed in-process); backend review commands default `--receipt` the way fan-out does; fan-out finalize derives task/base/receipt from `--rid`.
- `flowctl review-rounds resume-terminal <spec> --review-type completion --json` → `{action, status, exit}`.
- Fan-out finalize accepts `--merge-plan <file>` (keep/collapse per draw item) and renders the merged document and the survivor count.
- `flowctl tracker sync --op push` without `--body-file` renders the body from the spec; `--status-only` needs no body; `--op pull|reconcile --prepare` writes mode-0600 snapshot files and returns the pre-reduction class, stripped tracker body, base pair and deduped genuine comments.
- `flowctl task create --spec <id> --from-json` reports all item errors in one response with the allowed key list, and accepts `touches`, `description_file`, `acceptance_file`.
- `flowctl validate --spec <id>` checks task `satisfies` ⊆ the spec's R-IDs and reports uncovered R-IDs as warnings; plan's coverage table is rendered from `satisfies`.
- `flowctl preflight --json` — config snapshot plus the gate values plan/capture/refine probe today (strategy status, glossary term count, decision-entry count, tracker active, memory enabled, review backend), each with a per-value probe status.
- `flowctl prospect write --from-json <file> [--skeleton]`, `flowctl qa receipt --from-json <file> [--skeleton]`, `flowctl memory audit-scan --json`, `flowctl memory apply --plan <file>`, `flowctl memory add --check-overlap`, `flowctl setup-status --json`.

## Edge Cases & Constraints

- Existing callers keep working: no existing flag, output field, exit code or file format changes unless an R-ID names it. New output fields are additive (receipts are the portable product boundary).
- A skill that switches to a new verb ships in the same release as the verb; the installed consumer layout (plugin cache, Codex mirror, `.flow/bin` copies) carries both together.
- Deterministic replacements must reproduce what the hand path produced for the same input (render parity), or name the intended difference.
- Tracker changes must not add network calls, weaken the compare-and-swap reads, or change conflict semantics; the rendered push body must be byte-stable for an unchanged spec.
- The admission view never overrides the host: hidden-coupling or doubt still holds a task.
- Hosts that block on dispatch keep today's plan scout order.

## Acceptance Criteria

- **R1:** Non-breaking rollout: every new verb or flag is additive; existing command outputs and exit codes are byte-for-byte unchanged unless an R-ID below names the change; the Codex mirror and tracker manifest are regenerated (sync run twice, idempotent); each changed skill ships with the verb it calls in the same release; full suite, Ruff and the OS smoke matrix are green. Errors: a skill calling a verb absent from the installed flowctl is a release-blocking test failure, not a runtime fallback. [user] "make sure we don't break anything"
- **R2:** `judge --preset route` returns the code-computed lifecycle decision and PR observation whenever it can compute them, independent of external-judge availability; `available` describes only the judge answers. Test: with no `TYPESAFE_API_KEY`, the route decision is present. Errors: PR probe failure → `pr_probe_failed: true` with no lifecycle guess. [paraphrase]
- **R3:** `flow --auto` classifies each hop from one `pilot snapshot` call instead of the multi-call host sequence, and joins open PRs from one listing during selection; the TMPDIR config-snapshot ceremony it replaces is removed from the skill. Test: snapshot output for a fixture repo equals the fields the skill previously gathered. Errors: snapshot failure → the hop ends `NEEDS_HUMAN` with the error, never a host re-derivation. [paraphrase]
- **R4:** `pilot strikes record` replaces the skill's jq/mv strike-ledger writes with identical semantics: one cumulative counter per spec, with stage, reason and timestamp recorded as metadata of the latest strike; unready at 2; cleared on advance. Errors: unknown spec → non-zero with message; concurrent records serialize under the existing lock. [paraphrase]
- **R5:** The flow tail's land wait uses the soonest of land's reported remaining patience, a bounded CI-check watch for pending checks, or the caller interval; it names the wait mechanism; states whether `--until=merge` waives patience; and ends `DEFERRED_TO_LAND` after a bounded number of no-progress ticks on human-review states. Errors: no remaining-time report → caller interval. [paraphrase]
- **R6:** Backlog mode performs its read-only tracker operations (list-open, comment-list, relation-list) with `flowctl tracker wire` directly; reconcile and question keep the tracker-sync skill. Errors: no error surface beyond the wire verbs' existing envelopes. [paraphrase]
- **R7:** make-pr's preflight/close and push/create/stack-link shell blocks move into bundled scripts invoked by path, logic unchanged; the existing make-pr measurement harness shows no increase in median tool calls and a decrease in output tokens on its fixture. Errors: script failure keeps today's exit/verdict mapping. [paraphrase]
- **R8:** The rolling route's quiesce full gate writes a gate receipt on green, so the later Phase 4 gate check at the same HEAD skips; rolling 3d defines "focused integrated verify" as the task's focused Quick commands on the integrated target and states the wave-join full-gate step applies only at quiesce on this route. Test: a green quiesce followed by gate check at the same SHA reports a receipt hit. Errors: red gate writes no receipt. [paraphrase]
- **R9:** The baseline handoff rule accepts `.flow/`-only commits between baseline and dispatch (as gate receipts already do), and the rolling route runs one baseline at the spec base before its first admission batch and hands it to that batch. Errors: a non-`.flow/` commit in between invalidates the handoff. [paraphrase]
- **R10:** `ready --json` exposes parsed `touches` and transitive dependencies; `--admit` returns admitted/held with reasons from the mechanical checks (dependency closure, Touches presence and disjointness, always-serial set, cap). The rolling scheduler uses it per admission event; the host keeps its hold override. Errors: a task with no Touches line is held with reason `touches-missing`, never admitted. [paraphrase]
- **R11:** `done --range` computes the commit list and base itself for a task whose history is one contiguous range, and accepts repeatable `--test` and a stdin summary; the worker uses it on the standard path. On the rolling route, where a task's implementation and review-fix commits can interleave with other tasks' integrations, the conductor keeps passing an explicit normalized commit list. Existing `--evidence`/`--evidence-json` keep working. Errors: a range whose commits are not reachable from HEAD → non-zero with the offending SHA. [paraphrase]
- **R12:** `judge --preset tier --task <id>` assembles the tier state from the task file; `sync active --json` returns the per-event ops map so touchpoint gating reads it once per run. Errors: unknown task → non-zero; inactive tracker → empty map. [paraphrase]
- **R13:** The review findings parser reports the first failing block and reason, fan-out dispatch output shows each draw's parse status, the inline `·`-joined label form parses, and a SHIP output reporting zero introduced findings is recognized as a valid container that keeps its parsed pre-existing items and prior-finding lineage (never discarded, never bypassing prior-resolution rules). Test: the six real non-parsing draw shapes from the audit parse or fail with a named reason. Errors: no error surface beyond the parse-status field. [paraphrase]
- **R14:** Host review rounds use `review-prompt` for per-axis prompt files, `record --attach` to publish in the same call, and `increment --base/--head` for diff identity without a temp diff file; backend review commands default their receipt path; fan-out finalize derives task, base and receipt from `--rid`. Host prompts then match the codex path's prompt text. Errors: a missing reservation still fails exactly as today. [paraphrase]
- **R15:** `review-rounds resume-terminal` replaces completion review's Step 0.5 shell state machine, returning `{action, status, exit}` with the same decisions for every existing state. Test: each state the shell machine handled maps to the same action. Errors: unknown state → non-zero, never a default action. [paraphrase]
- **R16:** Fan-out finalize accepts a keep/collapse merge-plan JSON from the coordinator and renders the merged document and the NEEDS_WORK survivor count itself; the coordinator no longer counts survivors by hand. The keep/collapse decision stays the coordinator's. Errors: a plan referencing a missing draw item → non-zero listing the ids. [paraphrase]
- **R17:** flowctl renders the Flow-to-tracker body deterministically; push no longer requires an agent-authored body; status-only push needs none; an unchanged spec renders byte-identical, so push reports a no-op. The tracker-to-Flow fold and conflicts stay with the agent. The renderer accepts every spec body `validate` accepts today, including legacy headings, and adds no new heading requirement. Errors: no error surface beyond the existing push envelope. [paraphrase]
- **R18:** A tracker push makes at most 4 network calls on the recorded 7-call path: merge evidence is computed once, the transaction's parent read and readback feed update and status, and the Linear id probe folds into the first comment page. Outputs and receipts unchanged. Test: the facade call-count matrix. Errors: no error surface beyond existing envelopes. [paraphrase]
- **R19:** `tracker sync --op pull|reconcile --prepare` returns the pre-reduction class, stripped tracker body, base pair and genuine comments (marker comments and their hash matches excluded) from one call; noop/echo/flow-only classes need no agent judgment. Errors: snapshot files are mode 0600 and removed by the following facade call or on expiry. [paraphrase]
- **R20:** Chart projection skips a decision child update when title and body are unchanged; relation projection resolves config, link type and own-issue guard once per call and runs per-dependency probes within the existing concurrency cap; tracker HTTP calls reuse one connection per host per process. Errors: no error surface beyond existing envelopes. [paraphrase]
- **R21:** Bulk task create reports every invalid item in one response with the allowed key list, accepts `touches` (rendered as the task's Touches line) and per-item `description_file`/`acceptance_file`. Existing valid input produces identical task files. Errors: file keys resolve relative to the JSON file; a missing file is an item error. [paraphrase]
- **R22:** `validate --spec` warns when a task's `satisfies` names an R-ID absent from the spec and lists R-IDs no task satisfies; plan renders its Requirement coverage table from `satisfies` instead of predicting task ids. Warnings only; existing specs keep validating. Errors: no error surface beyond the warnings list. [paraphrase]
- **R23:** A `preflight` call returns the config snapshot plus the gate values plan, capture and refine probe before scouting, including refine's decision-entry presence; those skills use it instead of their serial probe blocks. Errors: each value carries its own probe status, and each consumer keeps its current failure behavior (refine's doc/strategy awareness fails open to active; capture's snapshot degrades to defaults). [paraphrase]
- **R24:** Plan dispatches flow-gap-analyst as soon as the repo-grounded scouts return, on hosts where dispatch is non-blocking; SHORT plans fold docs-gap-scout's charter into repo-scout; github-scout alone owns GitHub code search when enabled. Blocking hosts keep today's order. Errors: no error surface. [paraphrase]
- **R25:** `prospect write --from-json` allocates the id, computes survivor/rejected counts and rate, renders, validates and writes atomically, reporting all errors at once; the skill shows its skeleton once and stops importing flowctl internals. Errors: invalid payload → all item errors listed, nothing written. [paraphrase]
- **R26:** `qa receipt --from-json` writes the QA receipt and prior-finding carry-over from outcome, findings and coverage payloads, replacing the skill's inline receipt assembly; under `NO_PROMPT` QA resolves its target and accounts before scenario derivation, so a missing target ends BLOCKED early. Errors: invalid payload → all errors listed, nothing written. [paraphrase]
- **R27:** `memory audit-scan --json` returns per-entry frontmatter, schema errors, recurrence counts, module existence/change since last audit and hardened-rule presence; `memory apply --plan` applies stamps, field sets, moves and removals and re-points references from a host-authored plan. The audit skill authors only judgment fields. Errors: a plan entry for an unknown id → reported, others applied atomically per entry. [paraphrase]
- **R28:** `memory add --check-overlap` returns overlap matches without writing, so features and QA fold a rediscovered bug with one `--update` instead of create-then-delete. Errors: no error surface beyond `memory add`'s. [paraphrase]
- **R29:** `setup-status --json` returns in one read-only call what setup's serial probes gather; setup records declined optional questions so a steady re-run asks nothing. Errors: a missing or unreadable state file → treated as first run. [paraphrase]
- **R30:** The map skill's argument parsing, version check, init and invocation move into a bundled script invoked by path; the skill keeps only the summary judgment. Errors: script exit codes map to today's skill outcomes. [paraphrase]
- **R31:** flowctl imports its single-use modules (HTTP client, socket, ipaddress, secrets, uuid, html) at their call sites and compiles rarely used regexes lazily; startup time drops with no behavior change. Test: suite green; import-time measurement recorded in the PR. Errors: no error surface. [inferred]

## Boundaries

- [user] "impl-review ... focused on overengineering and slop and yagni": implementation review judges every change against the smallest correct fix; speculative generality, unused parameters, defensive branches for impossible states, duplicated helpers, and prose that restates code are findings.
- [user] "do not let it go into overengineering mode": no new config keys, no feature flags, no compatibility shims, no new abstractions beyond the verbs named above; a verb that needs judgment to produce its output is out of scope.
- Wave 1 (fn-255) correctness fixes, including `review-rounds record` deriving verdict/review/tallies, are not redone here. [paraphrase]
- Wave 3 (fn-257) small bug fixes and Wave 4 (fn-258) output diets (lean `show`, anchor projection, listing hygiene) are out of scope. [paraphrase]
- Reached-path prose splits, review rubric/cap/scoping, and product-side flowctl startup (fn-190) are out of scope (Wave 6, fn-260). [paraphrase]
- Resolve-pr GraphQL batching, a flowctl autonomy classifier, and caching the rolling dispatch probe are not built (see Decision Context). [inferred]

## Decision Context

The make-pr series showed the cost sits in authoring round trips and instruction volume, not in rendered output; the measured fix was flowctl rendering from a small agent-authored payload plus one skeleton. Each R-ID applies that same shape to one remaining hand-assembly site, and each new verb is limited to derivation, rendering, validation and joins the skill already performs mechanically. The admission view (R10) and merge-plan render (R16) stop at mechanical checks; the host keeps the decisions.

Dropped at verification: resolve-pr thread replies already go through a per-thread bundled script, and batching them into one aliased mutation saves about a second per thread, too little for a new code path. A flowctl autonomy classifier would unify roughly 30 environment checks but has no measured cost. Caching the rolling dispatch probe per host and version risks a stale answer after a host update for a saving of a few seconds per run.

## Strategy Alignment

- Design principle "flowctl grows only under burden of proof": every verb here is zero-judgment plumbing (render, validate, count, join already-read state); R1 and the Boundaries exclude any verb that decides. Reviewers should reject a verb that encodes judgment.
- "Receipts are the portable product boundary": receipt changes are additive fields only (R1).
- Tracker determinism track: R17-R20 continue the fn-139-141 extraction of repeatable tracker machinery from prose into `flowctl_tracker/`.

## Parked unknowns

- Land's head-bound spec selection: `spec closed-in-range --head <sha>` after fetching the PR head would replace about 82 s of per-blob API reads per land call, but it reads a fetched commit rather than GitHub's tree. Needs Gordon's decision on whether a fetched head is acceptable to land's authority model.
- Plan's per-scout tier-judge call (about 1 s each, before every scout) could exempt thinking scouts or run once per wave; fn-247 R11 decided the current shape. Needs Gordon's decision before any change.
- A `flowctl deps --json` graph command would replace the deps skill's per-spec calls (about 79 s here) and fix its 10-level cap, but conflicts with the recorded "no new graph engine" rule. Needs Gordon's decision.

## Requirement coverage

| R-ID | Task |
|---|---|
| R1 | fn-259.M (TBD - populate via /flow-next:plan) |
| R2 | fn-259.M (TBD - populate via /flow-next:plan) |
| R3 | fn-259.M (TBD - populate via /flow-next:plan) |
| R4 | fn-259.M (TBD - populate via /flow-next:plan) |
| R5 | fn-259.M (TBD - populate via /flow-next:plan) |
| R6 | fn-259.M (TBD - populate via /flow-next:plan) |
| R7 | fn-259.M (TBD - populate via /flow-next:plan) |
| R8 | fn-259.M (TBD - populate via /flow-next:plan) |
| R9 | fn-259.M (TBD - populate via /flow-next:plan) |
| R10 | fn-259.M (TBD - populate via /flow-next:plan) |
| R11 | fn-259.M (TBD - populate via /flow-next:plan) |
| R12 | fn-259.M (TBD - populate via /flow-next:plan) |
| R13 | fn-259.M (TBD - populate via /flow-next:plan) |
| R14 | fn-259.M (TBD - populate via /flow-next:plan) |
| R15 | fn-259.M (TBD - populate via /flow-next:plan) |
| R16 | fn-259.M (TBD - populate via /flow-next:plan) |
| R17 | fn-259.M (TBD - populate via /flow-next:plan) |
| R18 | fn-259.M (TBD - populate via /flow-next:plan) |
| R19 | fn-259.M (TBD - populate via /flow-next:plan) |
| R20 | fn-259.M (TBD - populate via /flow-next:plan) |
| R21 | fn-259.M (TBD - populate via /flow-next:plan) |
| R22 | fn-259.M (TBD - populate via /flow-next:plan) |
| R23 | fn-259.M (TBD - populate via /flow-next:plan) |
| R24 | fn-259.M (TBD - populate via /flow-next:plan) |
| R25 | fn-259.M (TBD - populate via /flow-next:plan) |
| R26 | fn-259.M (TBD - populate via /flow-next:plan) |
| R27 | fn-259.M (TBD - populate via /flow-next:plan) |
| R28 | fn-259.M (TBD - populate via /flow-next:plan) |
| R29 | fn-259.M (TBD - populate via /flow-next:plan) |
| R30 | fn-259.M (TBD - populate via /flow-next:plan) |
| R31 | fn-259.M (TBD - populate via /flow-next:plan) |
