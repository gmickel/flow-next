# Smaller default outputs and bundles (audit wave 4)

## Goal & Context
<!-- Goal & Context: 55% [paraphrase], 45% [inferred] -->

The 2026-09-24 efficiency audit measured where flow-next spends agent context on output nobody reads. The largest single item is the worker anchor bundle: 118-161 KB per task in this repository, of which roughly 100 KB is JSON the worker agent is then told to filter or ignore (the full memory index as JSON, the whole glossary, and the spec's review and tracker ledgers). Every worker pays it once per task, and it stays in context for the rest of the worker's turns. Smaller but frequent costs sit in skills that read unbounded listings raw, review workflows that echo multi-kilobyte JSON back into context every round, a model-visible command shim for every skill (the listing is duplicated and each shim costs an extra invocation hop), and reference files loaded on paths that never use them.

This wave cuts those outputs and loads. It changes what flowctl prints and what skills read; it does not move instruction text between files except where an R-ID names a pointer gated on a condition the skill already checks. The user endorsed the wave and asked that review keep it from turning into an overengineering exercise.

## Architecture & Data Models

- The anchor bundle (`flowctl anchor <task> --md`) keeps its fixed section order and fail-open behavior; three sections change content (memory index, glossary, spec record) and one git read changes form.
- One deterministic glossary matcher (term or avoid-alias occurs in a given text, case-insensitive, whitespace-collapsed, the contract the worker agent already describes) serves both the anchor bundle and a new filter on `glossary list`.
- `flowctl show <spec-id> --json` returns a spec record without its two large ledgers, `review_attempts` and `tracker`. Both keep their dedicated readers: `flowctl review-rounds attempts` (per review scope) and `flowctl sync get-state`. The small review bookkeeping fields (reservations, pending rounds, transport failures, hash epoch) have no dedicated reader and stay. Task records from `show <task-id> --json` are unchanged.
- Skill-side changes are projections (a `jq` filter on output the skill already requests) or invocation-name changes; no new skill, agent, or config key.

## API Contracts

- `flowctl anchor <task-id> --md|--json`:
  - `memory_index` section = `flowctl memory list` text form (id, title, module per entry), labeled with that command.
  - `glossary` section = only the glossary entries whose term or avoid-alias occurs in the task's title or description; section omitted-with-reason when none match or the glossary is empty.
  - `spec_show` section = the lean spec record defined below.
  - git state uses a short form (`git status --short --branch`); the branch and `git log -5 --oneline` sections stay.
- `flowctl show <spec-id> --json`: drops `review_attempts` and `tracker`. All other keys (including `review_reservations`, `review_pending_rounds`, `review_transport_failures`, `review_hash_epoch`, `plan_review_status`, `completion_review_status`, `plan_review_rounds`, `impl_review_rounds`, `branch_name`, `tasks`, `status`, `no_plan`, `depends_on_*`, `created_at`) are unchanged.
- `flowctl glossary list [--json] --match <text>`: returns only entries matching `<text>` under the matcher above, same output shape as the unfiltered list.

## Edge Cases & Constraints

- In-repo consumers of `show <spec> --json` read only retained keys today (plan-review and completion-review status, branch name, tasks, status, dependencies, created_at, no_plan). The worker must re-grep skills, agents, templates, the Ralph templates, `flowctl` internals, and tests for any read of a dropped key before shipping, and move such a read to the dedicated reader.
- The anchor bundle's test suite currently asserts the bundle is a verbatim superset of the worker's discrete reads. R1 is a deliberate contract change to that test and to the anchor documentation, not a regression; the replacement asserts each section equals the output of the command it is labeled with.
- Hiding command shims from the model (R6) breaks every model-side invocation that still uses a command-form name. `flow --auto`'s stage dispatch table, flow's land hand-off, work's completion-review call, and the setup-installed prose trigger are known sites; the worker enumerates all of them. User-typed slash commands and `claude -p "/flow-next:..."` prompts (Ralph templates, docs recipes) are user invocations and keep working.
- Non-Claude hosts (Codex, Cursor, Droid, Grok, OpenCode) must be checked: the Codex mirror has no command shims; hosts that load `commands/` directly must not lose a working entry point.
- Setup snippet changes reach existing installs only through setup's managed block refresh.
- Generated mirror: canonical skill edits are followed by `scripts/sync-codex.sh` per the development policy; intentional prompt-text changes update the pinned-prompt test in the same commit.

## Acceptance Criteria

- **R1:** The worker anchor bundle carries the text memory index, only the glossary entries matching the task's title or description, the lean spec record, and short-form git status. On this repository the bundle for a representative task drops from roughly 118-161 KB to roughly 45-70 KB. The anchor's verbatim-superset test is replaced by a per-section "equals its labeled command" test, and the anchor docs describe the new sections. Before merge, the fn-83 worker-anchor comprehension eval is re-run against the new bundle and shows parity with the current bundle; a parity miss blocks the change. Errors: empty or absent glossary → section reports its skip reason; zero matches → same; memory disabled → section omitted as today; any failing section stays fail-open with `(section unavailable: ...)`. [paraphrase]
- **R2:** `flowctl show <spec-id> --json` omits `review_attempts` and `tracker` and keeps every other key. A regression test shows `review-rounds attempts` (per scope) and `sync get-state` still return the omitted data, and no skill, agent, template, internal flowctl caller, or test reads a dropped key from `show`. Errors: no error surface beyond the existing unknown-id error. [paraphrase]
- **R3:** The spec scout and refine's business pass read the spec index through an open-specs projection (id, title, status) instead of the raw `specs --json` dump, and the repo scout reads the glossary through `glossary list --match <request text>`. A test drives `glossary list --match` against a fixture glossary and asserts term hits, avoid-alias hits, case and whitespace insensitivity, and an empty result for no match. Errors: no glossary → the same empty/husk result the unfiltered list returns today. [paraphrase]
- **R4:** The flow-next task skill answers "what tasks are there" with an id/title/status/spec projection of `tasks --json` (or `tasks --spec <id>` for one spec) instead of the raw `specs --json` plus `tasks --json` dumps, and uses `flowctl brief` for "what's next" orientation only, since `brief` deliberately omits blocked and dependency-waiting tasks. It uses `validate --spec <id>` for single-spec validation with repo-wide validation read through a counts-and-errors projection, and the setup-installed Claude and AGENTS snippets name `flowctl brief` as the orientation read where they list `flowctl list`. Errors: no error surface beyond the commands' own. [paraphrase]
- **R5:** Review workflows stop echoing whole JSON payloads: after `review-rounds record` they print only the fields the next step reads (`superseded`, the current attempt's verdict and timestamp, round count), and the fan-out finalize step reads its result through a projection that excludes the merged review body the coordinator just wrote, with the verdict line kept visible. flowctl output shapes are unchanged. Errors: a projection that finds no verdict prints an explicit empty-verdict line so the RETRY path still fires. [paraphrase]
- **R6:** Every command shim under the plugin's commands carries `disable-model-invocation: true`, and every model-side invocation in skills, agents, references, and the setup snippets names the skill id instead of the command form. A test resolves every model-side invocation target to an existing, model-invocable skill. User-typed slash commands keep working on Claude Code, and each other supported host keeps a working entry point for every command. Errors: a host that does not honor the frontmatter keeps today's behavior (no regression, no gain). [paraphrase]
- **R7:** Capture's duplicate-detection memory cross-check no longer reads `memory list --json` to decide whether memory is initialized; it runs its searches and treats the "Memory not initialized" error as the skip signal it already documents. Errors: other search errors stay advisory, as today. [paraphrase]
- **R8:** Plan-review's fix cycle edits the spec file in place and persists it with `spec set-plan <id> --file <spec path>`, never re-emitting the whole spec through stdin, and each cycle saves exactly one checkpoint. Errors: set-plan failure surfaces the existing error and the cycle stops; a user edit made between cycles is preserved because the file on disk is the input. [paraphrase]
- **R9:** Tracker-sync's body-merge, status-sync, and comments-sync references drop every step the facade already performs (by-hand receipts, merge-base and last-synced writes, dependency-block stripping and carry-forward, readback) and the storage recipes for comment dedup that nothing persists (the posted-id and seen-hash sets), keeping the judgment sections (the three-way merge and fold rules, status deadlock and unmapped-state routing, comment content shape). The human-paste rule stays as an agent-side fold rule over the fetched listing: a comment whose normalized body matches a flow marker comment in the same listing is not imported, because the facade receives an already-folded spec and does not filter it. The chart-subject material moves to a reference read only for chart subjects. Tracker behavior is unchanged: the existing tracker test suites stay green and no facade code changes. Errors: no error surface beyond the facade's existing envelopes. [paraphrase]
- **R10:** The features skill reads its seed-mode phases only after it has resolved seed mode, and resolve-pr reads its cluster-analysis rules only when its clustering phase runs; both pointers already name the condition, so no instruction text moves. Errors: no error surface beyond mode detection. [paraphrase]

## Boundaries

- [user] "impl-review ... focused on overengineering and slop and yagni": implementation review judges every change against the smallest correct fix; speculative generality, unused parameters, defensive branches for impossible states, duplicated helpers, and prose that restates code are findings.
- "do not let it go into overengineering mode" [user]. Concretely: no new config keys, no new commands, no flags beyond `glossary list --match`, no retention or pruning machinery, no output-size budgets or truncators. [paraphrase]
- Shortening skill descriptions in the listing is wave 6 (needs a routing eval), not this wave. [paraphrase]
- Deleting the deprecated interview and pilot shims is wave 3. [paraphrase]
- plan-sync's inputs (including its spec index read) are wave 1's plan-sync context fix. [paraphrase]
- New flowctl verbs that take over hand-assembled work (review receipts, admission, tracker rendering) are wave 5. [paraphrase]
- Moving instruction text between files (auto, work, worker, drive splits) is wave 6 and eval-gated. [paraphrase]
- No change to review verdicts, receipt formats, tracker wire behavior, or the product startup path (fn-190 stays deferred). [inferred]

## Decision Context

The measured cost is output volume, and the cheapest fix for most of it is a projection at the reader, so skill-side `jq` projections are preferred over new flowctl surface wherever the skill already makes the call (R3, R4, R5). flowctl changes only where the output itself is the problem for every reader: the anchor bundle, which every worker reads raw, and spec `show`, which about 30 skill sites read raw and whose dropped ledgers already have dedicated readers. For that reason `show` gets no `--full` flag. `glossary list --match` is the one new flag, because the anchor needs the deterministic matcher anyway and the repo scout's by-hand match over a 27 KB dump is the same operation.

Accepted at review round 1: R2 keeps the small review bookkeeping fields because only `review_attempts` and `tracker` have dedicated readers; R4 keeps task listings on a `tasks` projection because `brief` omits blocked and dependency-waiting tasks; R9 keeps the human-paste fold rule because the facade does not filter pasted copies.

Claims narrowed during verification: pruning `.flow/review-fanout/` was dropped (a gitignored 26 MB directory costs no context or wall-clock, and retention would be new machinery). Renaming the "Epic marked done" validate wording was dropped (it is pinned by tests and docs; cosmetic). Moving the prose contract into the prose skill was dropped (its skill records "never copy rule text into this skill"); R6's skill-id switch removes that path's extra hop instead. A `specs --status` flag was dropped in favor of a projection. The docs-gap scout keeps the full glossary because it looks for husks and per-file counts, not term matches.

## Strategy Alignment

- "flowctl grows only under burden of proof": the only new surface is `glossary list --match`, a zero-judgment string match reusing the documented matcher contract.
- "Remember the bitter lesson": R1 changes what every worker reads, so it ships only on the fn-83 eval's parity result rather than on size alone.
- "The artifact is the contract": unchanged. Workers still read spec and task files; only redundant plumbing leaves the bundle.

## Requirement coverage

| R-ID | Task |
|---|---|
| R1 | fn-258.M (TBD - populate via /flow-next:plan) |
| R2 | fn-258.M (TBD - populate via /flow-next:plan) |
| R3 | fn-258.M (TBD - populate via /flow-next:plan) |
| R4 | fn-258.M (TBD - populate via /flow-next:plan) |
| R5 | fn-258.M (TBD - populate via /flow-next:plan) |
| R6 | fn-258.M (TBD - populate via /flow-next:plan) |
| R7 | fn-258.M (TBD - populate via /flow-next:plan) |
| R8 | fn-258.M (TBD - populate via /flow-next:plan) |
| R9 | fn-258.M (TBD - populate via /flow-next:plan) |
| R10 | fn-258.M (TBD - populate via /flow-next:plan) |
