# Efficiency audit 2026-11 wave 1: mechanical fixes and zero-loss prose pruning

## Goal & Context

A full-repository efficiency pass at v9.18.0 audited all 29 skills, 21 agents, 26 command shims, shared references, templates, and `flowctl.py` for wall-clock latency, tool-call waste, unfiltered context dumps, and zero-loss prose duplication. Since the v9.5.0 efficiency wave, `plugins/flow-next/` gained +3,676 / -629 lines across 87 files (GitLab and Bitbucket forge adapters, `flow --from-issue`, idea intake, command review backend, and Antigravity CLI).

This wave collects only zero-risk, behavior-preserving fixes verified line by line against current source: unfiltered 29 KB to 166 KB stdout dumps, post-9.5.0 forge and `pilot snapshot` regressions, two live prompt bugs in `flowctl.py`, slow serial subprocess loops, dead startup blocks, and same-path prose restatements where every kept rule stays on every path that reads it. Anything that moves instructions behind conditional reads, alters review scope, or shifts model judgment lives in Wave 2 or Wave 3.

## Architecture & Data Models

No new subsystems. Edits target existing canonical files under `plugins/flow-next/` (skills, agents, command shims, references, shell helpers, `flowctl.py`, `flowctl_bootstrap.py`) plus regenerated Codex mirror output via `./scripts/sync-codex.sh`. Standing criteria G1, G2, and G4 in `.flow/criteria.md` apply.

## Edge Cases & Constraints

- Every duplicate prose cut keeps an authoritative copy on every execution path that previously read the removed copy. No instruction moves to a file read on fewer paths.
- Shell variables and helper functions do not persist across separate Bash tool calls; per-fence definitions (such as `run_bounded` in `flow-next-prime`) stay intact.
- Items explicitly retained in prior audits (`fn-307`, `fn-308`) stay untouched: iOS commands in `flow-next-drive/references/commands.md`, capture's three in-place gate probes at the steps they gate, refine's post-write-back `specs` read, and `flow-next-work`'s reviewer-overlap text (`fn-260` R3).
- Tests follow G2: assert behavior, parser tokens, or parity rather than sentence wording or frozen char counts.
- Final verification gate: `python3 scripts/run_tests_parallel.py`, `uvx ruff@0.16.0 check .`, `./scripts/sync-codex.sh --check`, shipped-link checks, and conduct-checklist walkthrough on touched skills.

## Acceptance Criteria

- **R1:** Stop unfiltered CLI stdout context dumps across skills and scouts:
  - `flow-next` task-listing and add-task recipes filter to open specs with `jq` (avoiding 165.7 KB `tasks --json` and 84.1 KB `specs --json` dumps on mature repos).
  - `flow-next-capture` duplicate detection pipes `specs --refs --json` through `jq` keeping only `status == "open"`, `summary.branch_only`, and `live != []` (100.7 KB to under 1 KB).
  - `flow-next-refine` (`SKILL.md`, `post-write-back.md`) and `flow-next-flow` (`open-issue-intake.md`) filter `specs --json` to open specs; `post-write-back.md` reuses `$READY_ADOPTED`.
  - `flow-next-deps` replaces `cat "$SPECS_FILE"` (54.8 KB stdout dump) with a one-line count and drops redundant `flowctl detect`.
  - `flow-next-strategy` (`update.md`) drops its immediate second `strategy read` and bounds historical done specs in the `specs --json` projection.
  - `docs-gap-scout` switches `glossary list --json` (29.1 KB) to `--match` (matching `repo-scout`), prunes `find` against `node_modules`/`.git`/`.venv`, and states an output token budget.
  - Unbounded `memory search` callers (`work/phases.md`, `defect-route.md`, `qa/workflow.md`, `why-scout.md`) pass `--limit 10`.
  - `flow-next-qa/SKILL.md` removes the reference link to `docs/flowctl.md` (reducing depth-2 link closure from 808 KB to 95 KB while keeping `gate-selection.md`).
  Errors: missing or empty JSON fields fail open to empty lists as today; existing preflight, deps, and glossary tests remain green.

- **R2:** Fix post-9.5.0 forge, PR, and issue-start call regressions:
  - `flow-next-resolve-pr` and `flow-next-land` stop running full `flowctl pilot snapshot --json` (1.2-4 s, 2 `gh pr list` calls, full spec scan) solely to read `.forge`; they use a fast local forge lookup (`flowctl forge --json` wrapping `repo_forge()`, or a local `git remote get-url origin` fast path with `flowctl` fallback for custom hosts).
  - `flow-next-flow` `issue-start.md` moves `tracker wire read` and `tracker wire comment-list` from Step 1 to the top of Step 3 (only when Step 2 finds no linked spec), and checks `--tick` before re-running the post-capture `pilot snapshot`.
  - `make-pr-preflight.sh`, `make-pr-create.sh`, `make-pr-bitbucket.sh`, and `resolve-pr/scripts/bb-target`: skip `ssh -G` for canonical hosts (`github.com`, `ssh.github.com`, `bitbucket.org`); run `flowctl show --json` once instead of twice; skip `spec closed-in-range` when `depends_on_epics` is empty; skip `git fetch origin main` when `DRY_RUN=1`; collapse repeated `jq` forks over `$SPEC_JSON` into one pass; gate `sleep 1` on PR creation (never `--update`); reuse `$EXISTING` URL and `$TRK_ACTIVE` across create/finalize; honor `BKT_CONTEXT` from env when set.
  - `resolve-pr` scripts and workflow: replace `3 * N` `jq` forks in `get-pr-comments` with a single `jq` pagination index query, accept optional `OWNER/REPO` to skip `gh repo view`, and pass JSON via stdin (avoiding `ARG_MAX`); branch `MODE=targeted` before `get-pr-comments` so targeted mode does not double-fetch and discard the PR; replace the per-file `jq` loop over `.flow/specs/*.json` in `resolve-pr` Phase 4 and `qa/references/spec-from-branch.md` with a single `jq` or `grep -l` pass; combine Phase 8 per-thread reply and resolve into one GraphQL mutation.
  Errors: custom SSH aliases, non-GitHub forges, detached checkouts, empty PRs, and failed API calls preserve existing fail-closed error messages and exit codes.

- **R3:** Fix review-pipeline prompt bugs and mechanical overhead:
  - Delete author-only `## Task Spec Sync Required` (520 B) from `build_rereview_preamble` for `review_type == "plan"` in `flowctl.py`.
  - Add the `if has_ratchet` guard to `build_rereview_preamble` for `review_type == "completion"` (matching `plan` and `impl`) so completion re-reviews do not instruct full requirement re-verification below the Convergence Ratchet.
  - Remove the redundant `## TERMINAL REVIEWER ROLE` block (365 B) from `build_completion_review_prompt` (`completion-review-prompt.md` and `build_review_persona_override` already cover it).
  - On `flow-next-impl-review/SKILL.md`'s CLI fast path, when `ONE_REVIEWER=1` invoke `"$FLOWCTL" "$BACKEND" impl-review` directly instead of the two-phase `impl-review-fanout --draw correctness` merge ceremony.
  - Materialize one shared `.diff` file per CLI fan-out round instead of running `git diff` four times (`flowctl.py`); drop the duplicate `flowctl show` dump in `plan-review/workflow.md`; align stale `"high"` effort fallbacks in `run_codex_exec` and `run_copilot_exec` with the `"medium"` registry default.
  Errors: non-resumed reviews, failed fan-out draws, and explicit `--effort` overrides retain identical behavior and receipt fields.

- **R4:** Fix `flowctl` bootstrap, `memory audit-scan`, and `argparse` startup overhead:
  - `flowctl_bootstrap.py` stops restricting the authenticated `--help` fast path exclusively to Python 3.14; supported Python 3.11+ runtimes whose `argparse` help output matches take the fast path.
  - `cmd_memory_audit_scan` runs `git status --porcelain` once before the entry loop, caches `(module, last_audited)` git log lookups, and batches `.flow/memory/` history into one `git log` pass (falling back to `--follow` only for renamed entries), preserving the exact output schema.
  - Skip `argparse` `gettext.find()` locale lookups when `LANG`/`LC_ALL` is unset or default/C.
  Errors: hash mismatch on static help, git failures, or renamed memory files fall back safely to existing behavior with identical JSON keys.

- **R5:** Remove dead startup blocks and duplicate `flowctl`/shell calls across hot-path and supporting skills:
  - `flow-next-flow/auto.md`: remove dead `REPO_ROOT`/`TODAY` startup block and define `REPO_ROOT` inside the QA verify fence; point Phase 5 stage-outcome line to `SKILL.md Step 5` (re-gating `gate-selection-more.md`); qualify Done-when `pilot-log` check as `(backlog mode only)`; merge the two adjacent Phase 2 snapshot `jq` blocks; include `headRefName,baseRefName,headRefOid,mergeCommit` in post-`make-pr` `gh pr list` so `tail.md` avoids two extra `gh` calls.
  - `flow-next-work`: remove unused `ready --spec` in `phases.md`, duplicate `tasks --spec` in `multi-task.md`, and duplicate `show`/`set-no-plan` in `no-plan-route.md` when `NO_PLAN=1` already holds `no_plan: true`; guard `spec-less-start.md` `init` with `[ -d .flow ] ||`; reuse `sync active` snapshot from `spec-id-mint.md` when `.flow/config.json` is unchanged; inline the single non-duplicate sentence of stale `autonomous-defaults.md` into `work/SKILL.md` and delete `autonomous-defaults.md`.
  - `capture` / `plan` / `refine`: skip capture readiness gate (§4.2) under `from:goal` and `from:issue`; trust preflight `active: false` in capture Phase 6 when tracker integration did not run; gate capture `memory search` on `memory_enabled`; guard `plan/steps.md` `research-scope.md` check to `STANDARD|DEEP` and combine `init` + legacy leftover check; remove duplicate `STRATEGY.md` read and `config get tracker.perEvent.interview` in `refine`.
  - Scouts and supporting skills: `spec-scout` runs `specs --refs --json` once (dropping the preceding `specs --json`); pass `Year: YYYY` to `docs-scout`, `practice-scout`, and `github-scout` instead of running `date -u +%Y`; `audit` batches `mark-fresh`/`mark-stale` into `memory apply` and drops the second `glossary list`; `features/maintain.md` drops its buggy `memory list` call ahead of `features status` and checks local `git symbolic-ref` before `gh repo view`; `sync` drops duplicate `tasks --spec` on spec-ID inputs and runs Step 5 probes in parallel; `memory-migrate` drops redundant per-entry `memory read`; `prime` folds `features status` and `glossary list` into `prime classify`, deduplicates `security-scout` `gh api`, and consolidates `observability-scout` recursive greps; `setup` folds `features status` into `setup-status`; `quality-auditor` drops redundant `git diff --name-only`; `worker` combines `anchor` and `base_commit`; `plan-sync` uses `git show --stat` instead of hardcoded TS/PY grep; `rules/flow-next.mdc` lists `agy`.
  Errors: every removed call reads a value already in hand or batches into an existing atomic helper; missing snapshots fail open identically to today.

- **R6:** Zero-loss same-path prose pruning (no rules weakened, no text moved to fewer-read files):
  - Slim `commands/refine.md` (~4.0 KB to ~0.6 KB) and `commands/flow.md` (~1.6 KB to ~0.6 KB) to standard thin command shims (backing skills immediately load all flag and route rules; preserve `flow-next-flow` token).
  - Deduplicate intra-file restatements in `flow-next-impl-review/workflow-host.md` (`session_id: null` rationale, cross-family fail-closed rule, routing precedence, and Anti-patterns repeating Critical rules) and replace the duplicated ~4 KB `--interactive` spec inside `optional-phases.md` with a pointer to `walkthrough.md` (loaded on every `--interactive` run).
  - Fold the five CLI `workflow-<backend>.md` files in `flow-next-plan-review` and `flow-next-spec-completion-review` into one CLI fast path inside each `SKILL.md` (matching `flow-next-impl-review/SKILL.md`, keeping `workflow-host.md` separate): eliminates two Read turns and 5-11 KB per CLI plan/completion review while increasing proximity.
  - Deduplicate `flow-next-prospect/workflow.md` (repeated rejection taxonomy, persona table duplicated from `personas.md`, §5.5 markdown format rendered by `flowctl prospect write`, and emit JSON directly in Phase 2 to delete the 60-line inline Python YAML parser).
  - Deduplicate same-path restatements in `flow-next-features/{maintain,seed}.md` against `references/doctor-and-proof.md`, `flow-next-audit/{SKILL,workflow,phases}.md` (all three always load together), and `flow-next-drive/references/{auth,session-management}.md` against `commands.md`; remove the remaining `"since 4.5.1"` version-archaeology string in `flow-next-setup/workflow.md`.
  Errors: no dangling links or missing test-pinned tokens; every rule removed has a verified kept copy on every path that read it.

## Boundaries

- No change to routing decisions, review verdicts, consent gates, review depth, or which stages run.
- No splitting of loaded instruction files into conditional references where an agent could forget to read them (moved to Wave 3 evals).
- No compact-JSON global output format change (Wave 2) and no `flowctl.py` importable-entry launcher changes (`fn-190` / Wave 2).
- Do not touch `flow-next-drive` iOS commands (`fn-292`), `flow-next-prime` per-fence `run_bounded`, `capture` in-place gate probes, or `flow-next-work` reviewer-overlap text (`fn-260` R3).

## Decision Context

Follows the proven wave split from the 2026-09 and 2026-10 audits (`fn-307`, `fn-308`): land zero-risk mechanical fixes, bug fixes, and verified same-path prose cuts on code review alone without blocking them on architectural refactors (Wave 2) or empirical A/B studies (Wave 3). Items with proximity risk (`refine/SKILL.md` split, `optional-phases.md` per-flag split, `backlog-mode.md` merge, `maintain.md` Phase 6 split) were deliberately excluded from Wave 1 and placed in Wave 3.

## Strategy Alignment

Applies `STRATEGY.md` "Agent first" and "Remember the bitter lesson" (delete dead/duplicated prose and redundant calls that tax every run) and "flowctl grows only under burden of proof" (only zero-judgment plumbing like `flowctl forge` and `audit-scan` batching).
