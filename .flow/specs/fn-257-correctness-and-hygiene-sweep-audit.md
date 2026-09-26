# Correctness and hygiene sweep (audit wave 3)

## Goal & Context
<!-- scope: business -->
<!-- Goal & Context: 70% [paraphrase], 30% [inferred] -->

The 2026-09-24 efficiency audit found a long tail of small defects across the review, planning, capture, audit, setup, prime and driver skills and in flowctl's error paths. Each one either costs an agent a failed call and a retry, or quietly degrades a result (a wrong review backend, a stale year, a link that does not resolve in an installed plugin). None is large on its own; together they are the friction agents hit most often. This wave fixes them as a batch of small, independent changes, in the smallest correct form. Wave 1 (fn-255) owns the unattended-run bugs; this wave is the rest of the verified small bugs.

## Architecture & Data Models
<!-- scope: technical -->

No new components. Every change edits an existing skill, reference, command shim, agent, test, or an existing flowctl command's argument or error handling. Skill edits follow the canonical-source rule: edit the canonical skill, regenerate the Codex mirror with the sync script.

## API Contracts
<!-- scope: technical -->

- `flowctl` plan-review handler: `--files` becomes optional; when absent the prompt carries no requested-files block.
- `flowctl` commands that currently declare `--base` as required for review diffs: `--base` becomes optional and resolves the repository's default branch when omitted, using flowctl's existing `origin/HEAD`-first resolution (the spec-base helper's candidate order), not `triage-skip`'s `main`/`master` probe.
- `flowctl done` error text for a non-`in_progress` task names the next step (`flowctl start <id>`), keeping `--force` as a secondary mention.
- `flowctl` JSON output to a closed pipe exits quietly instead of printing a `BrokenPipeError` traceback.

## Edge Cases & Constraints
<!-- scope: technical -->

- Every canonical skill change is mirrored through the Codex sync script; the mirror is never hand-edited.
- Tests assert behavior or a minimal token, never prose sentences (G2). Where a fix changes text a test pins by sentence, the test is converted to a structural assertion in the same change.
- Supported hosts that set no plugin-root variable (Cursor) must still resolve every path a changed skill uses.
- Skill prose that is removed or corrected must not leave a dangling reference elsewhere (grep before delete).

## Acceptance Criteria
<!-- scope: both -->

- **R1:** The plan-review and completion-review workflows resolve the per-spec review backend from the spec id the host substitutes literally (impl-review's placeholder pattern), not from `${1:-}`. Errors: an empty or unknown spec id fails with a message naming the missing id instead of silently falling back to the global backend. [paraphrase]
- **R2:** Host-backend impl-review runs a standalone review (no task id): reservation, round accounting and receipt attach are gated on a task id being present, and the standalone path attaches findings through the direct `review-findings attach` form the RP backend already uses. Errors: no error surface beyond the existing attach errors. [paraphrase]
- **R3:** Plan-review no longer requires a derived file list: `--files` is optional in flowctl, and the four backend workflows drop the `## Key files` extraction. Errors: a supplied `--files` entry that does not exist is still rejected as today. [paraphrase]
- **R4:** Plan-review and completion-review receipt defaults are repo-keyed through the same helper impl-review uses (`_review_route_receipt_default` or its spec-scoped equivalent), and host-backend receipts record the reviewed `base` and `head`. Errors: an explicit `REVIEW_RECEIPT_PATH` still wins. [paraphrase]
- **R5:** Review commands that require `--base` accept its omission and resolve the default branch through the existing `origin/HEAD`-first resolution. Completion review's host workflow drops the by-hand receipt-lock and recovery-file steps that `review-findings attach` already performs, and names one owner for completion status. Errors: an unresolvable default branch fails with a message naming `--base`. [paraphrase]
- **R6:** The plan skill states one depth default in one place, and depth is decided before the scout wave; the later step renders the sections for the chosen depth. Errors: no error surface. [paraphrase]
- **R7:** Plan's new-spec path seeds the body from the resolved template (`flowctl spec skeleton`) plus only plan's own additions, so plan never writes the legacy headings fn-220 retired; the plan examples' spec sample carries R-ID acceptance bullets. Errors: no error surface beyond `spec skeleton`'s own. [paraphrase]
- **R8:** Capture's duplicate check compares only against open specs (`status == "open"`), and capture reads `tracker.readyState` and `artifacts.html.enabled` from its single config snapshot. Errors: a missing snapshot key keeps today's default behavior. [paraphrase]
- **R9:** Capture's new-spec write and refine's new-idea write use one atomic `spec create --plan-file` call instead of `spec create` followed by `spec set-plan`; the test that pins the old sequence string is updated. Errors: when a tracker-first mint path cannot pass `--plan-file`, that path keeps the two-call form and the capture failure note stays accurate for it. [paraphrase]
- **R10:** Plan's Route A refine reference no longer tells the agent to pass inline text to `task set-spec` flags that take file paths; plan writes `## Resolved via Research` only when docs-scout or practice-scout actually ran; the stale line/step cross-references found in the audit (capture's R-ID rule pointer, refine's audit pointer, spec-scout's step number, the plan command's argument hint, prospect's list/read verb note, refine's `/flow-next:plan <file>` suggestion) point at what exists. Errors: no error surface. [paraphrase]
- **R11:** No agent or skill hard-codes the current year; scouts and the strategy skill derive it at run time (`date -u +%Y`). Errors: no error surface. [paraphrase]
- **R12:** Every concrete relative markdown link to a shipped file in skills, agents, commands, references, templates and docs resolves in the installed plugin layout, including capture's HTML-lens reference and refine's write-back template links; qa's bare repo-relative paths become plugin-root-relative; worktree-kit resolves its script with the same plugin-root fallback every other skill uses. A unit test resolves those links and fails on a broken one. Errors: external URLs, anchor-only links, illustrative output placeholders and generated-artifact destinations (for example `.flow/artifacts/...` targets written at run time) are out of the test's scope. [paraphrase]
- **R13:** Prospect's authoring snippets run on a stdlib-only interpreter and on hosts without `CLAUDE_PLUGIN_ROOT`: no unconditional `import yaml`, no heredoc/stdin conflict, and plugin-root resolution with the standard fallback. Errors: missing plugin root fails with a message naming the expected path. [paraphrase]
- **R14:** The memory-migrate skill reads the fields flowctl actually returns: `entry_id` from `memory add --json`, the real `memory list-legacy --json` field shapes, and the `decisions` category in its valid track/category pairs. Errors: a failed `memory add` is reported as a failure, not inferred from a missing field. [paraphrase]
- **R15:** Audit's stamping helpers preserve frontmatter fields outside the schema (or the audit prose says "schema fields only" and the three failing entries are handled); the change-since check includes same-day commits; consolidate/replace never leaves a `related_to` pointing at a deleted entry; "Keep" means the same action in every audit file. Errors: a malformed frontmatter entry is reported, not silently skipped. [paraphrase]
- **R16:** Setup's question calls stay within the question tool's limits (at most 4 questions and 4 options per call, headers at most 12 characters); questions gated on values `flowctl init` always sets are removed; Codex installs read the version from the path the Codex installer writes; uninstall removes the `.codex/agents` files setup copies. Errors: no error surface beyond existing setup failures. [paraphrase]
- **R17:** Prime's scouts report findings keyed by the criterion IDs defined in prime's pillars (no invented IDs); Vitest discovery uses `vitest list`, not a full run; the destructive-command scan tokenizes shell text so redirects and punctuation never land in the never-edit list, and deduplicates; a probe timeout terminates the whole process group. Errors: a probe that exceeds its bound reports a timeout finding. [paraphrase]
- **R18:** `flowctl done` warns on unknown evidence keys (allowing `base_commit`) and errors when none of `commits`, `tests`, `prs` is present; its status and assignee checks run inside the task lock (as `start` does), and the same holds for `flowctl block`; when `planSync.enabled` is not `true`, `done` records the `plan-sync - skipped(config: planSync.enabled != true)` stage line itself so no conductor hand-edit is needed. Errors: the unknown-key warning goes to stderr and does not fail the command. [paraphrase]
- **R19:** flowctl error hints name the correct next step ("run `flowctl start <id>` first") before offering `--force`, and a missing task/spec error suggests the listing command; JSON output to a closed pipe exits without a traceback; the pilot-log lock uses the shared `cross_process_lock`; `atomic_write` retries a bounded number of times on a Windows sharing violation; the unreferenced functions and constants the audit listed are deleted. Errors: the Windows retry gives up after its bound and raises the original error. [paraphrase]
- **R20:** The task-management skill uses unique temporary paths for `done` summary and evidence files, and states an explicit exception for writing `.flow/memory/declined/*.md` directly so it no longer contradicts its own "no hand edits under .flow" rule. Errors: no error surface. [paraphrase]
- **R21:** The pilot alias always adds `--auto --tick` when it forwards to flow; the `interview` and `pilot` command shims are removed (their removal was promised for the release after 5.0.0); an already-merged scoped spec ends `flow --auto` with a named `PILOT_VERDICT`; Ralph's zero-task hint names the direct route. Errors: no error surface beyond the existing verdict set. [paraphrase]
- **R22:** Land's tracker touchpoint is described the same way in the land skill and the tracker-sync docs. Errors: no error surface. [paraphrase]
- **R23:** This repository's `.flow/config.json` no longer carries the retired `land.*` keys, so `anchor` and `brief` stop printing the retired-key notice. Errors: no error surface. [inferred]

## Boundaries
<!-- scope: business -->

- [user] "impl-review ... focused on overengineering and slop and yagni": implementation review judges every change against the smallest correct fix; speculative generality, unused parameters, defensive branches for impossible states, duplicated helpers, and prose that restates code are findings.
- "do not let it go into overengineering mode": no new commands, config keys, flags or abstractions beyond those an R-ID names; each fix is the smallest correct edit. [user]
- No behavior change to review verdicts, caps, stall guard or rubric. [inferred]
- Unattended-run correctness bugs (config parse, auto routing, branch fence, review record, locks, ralph-guard) belong to fn-255; RP tally parsing is fn-255's. [paraphrase]
- Output-size reductions (`show`, `specs`, `validate --all`, anchor, "what tasks are there" routed to `brief`) belong to fn-258. [paraphrase]
- New flowctl verbs (prospect write, QA receipt, deps, audit apply, classify snapshot) belong to fn-259. [paraphrase]
- Eval-gated prose moves and description trims belong to fn-260. [paraphrase]

## Decision Context
<!-- scope: both -->

Batched as one spec because every item is small, independent, and verified against the code on 2026-09-24; bundling saves per-spec ceremony without coupling the fixes. R-IDs are grouped by skill area so a worker can take them in any order.

Rejected or narrowed at review (round 1): retiring memory-migrate - `flowctl memory migrate --yes` classifies mechanically and moves originals, so it does not replace the skill's contextual classification (fn-35); the field-read repair is kept instead. Executor retries on 5xx/timeout - fn-139 records the retry predicate as rate-limited-only by design; only the land doc alignment remains. A make-pr retry after the spec-close commit - the routing reference deliberately stops a closed spec without an observed PR for a human; dropped. Default-branch resolution uses the `origin/HEAD`-first helper, not `triage-skip`'s probe. The link test covers concrete shipped-file links only.

## Strategy Alignment

- "The artifact is the contract" and "remember the bitter lesson": fixes remove friction and contradictions rather than adding compensating machinery.
- "flowctl grows only under burden of proof": no new subcommands; only argument defaults, error text and existing helpers change.
- Cross-platform parity track: R12, R13 and R16 close host-specific path gaps (Cursor, Codex).

## Requirement coverage

| R-ID | Task |
|---|---|
| R1 | fn-257.M (TBD - populate via /flow-next:plan) |
| R2 | fn-257.M (TBD - populate via /flow-next:plan) |
| R3 | fn-257.M (TBD - populate via /flow-next:plan) |
| R4 | fn-257.M (TBD - populate via /flow-next:plan) |
| R5 | fn-257.M (TBD - populate via /flow-next:plan) |
| R6 | fn-257.M (TBD - populate via /flow-next:plan) |
| R7 | fn-257.M (TBD - populate via /flow-next:plan) |
| R8 | fn-257.M (TBD - populate via /flow-next:plan) |
| R9 | fn-257.M (TBD - populate via /flow-next:plan) |
| R10 | fn-257.M (TBD - populate via /flow-next:plan) |
| R11 | fn-257.M (TBD - populate via /flow-next:plan) |
| R12 | fn-257.M (TBD - populate via /flow-next:plan) |
| R13 | fn-257.M (TBD - populate via /flow-next:plan) |
| R14 | fn-257.M (TBD - populate via /flow-next:plan) |
| R15 | fn-257.M (TBD - populate via /flow-next:plan) |
| R16 | fn-257.M (TBD - populate via /flow-next:plan) |
| R17 | fn-257.M (TBD - populate via /flow-next:plan) |
| R18 | fn-257.M (TBD - populate via /flow-next:plan) |
| R19 | fn-257.M (TBD - populate via /flow-next:plan) |
| R20 | fn-257.M (TBD - populate via /flow-next:plan) |
| R21 | fn-257.M (TBD - populate via /flow-next:plan) |
| R22 | fn-257.M (TBD - populate via /flow-next:plan) |
| R23 | fn-257.M (TBD - populate via /flow-next:plan) |
