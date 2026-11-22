# Efficiency audit 2026-11 wave 2: CLI plumbing and multi-turn orchestration speedups

## Goal & Context

Wave 1 removes bugs, unfiltered dumps, and duplicate calls. The next tier of wall-clock and token savings sits in CLI plumbing and multi-turn orchestration overhead: clean 3-draw fan-outs forcing 3 extra coordinator turns, `flow-next-land` burning 10-15 LLM turns and up to 330 GitHub blob API calls per tick, `pilot snapshot` making repo-wide PR listings on scoped runs, `flowctl` `indent=2` inflating every JSON response by 21-29%, `templates/usage.md` dumping 14.2 KB of multi-CLI bridge recipes on every CLI lookup, and `flowctl.py` paying ~300 ms cold AST parse on every invocation (`fn-190`).

Every item in this wave is pure deterministic plumbing or contract-verified output reduction with zero judgment moved into `flowctl` and zero change to quality gates or review standards.

## Architecture & Data Models

Changes extend existing `flowctl` subcommands (`impl-review-fanout`, `pilot snapshot`, `specs`, `preflight`, `anchor`, `review-prompt`, `usage`, `json_output`, and new zero-judgment helpers `land probe`, `forge readiness`, `review-host`) plus their skill callers and Codex mirror. All new helpers follow `STRATEGY.md`: pure zero-judgment plumbing over git, forge CLIs, and `.flow/` receipts. Standing criteria G1, G2, and G4 apply.

## Edge Cases & Constraints

- Zero judgment moves into `flowctl`: auto-finalize on fan-out fires only when every surviving draw has a clean parse, verdict `SHIP`, and zero parsed findings; any finding, parse warning, or non-`SHIP` verdict falls through to the existing coordinator merge step.
- Local `git fetch refs/pull/<PR>/head` in `land` must work for both same-repo and fork PRs (GitHub exposes `refs/pull/<PR>/head` on the base remote) and never trust local checkout state.
- Compact JSON in `json_output` must preserve exact JSON semantics and update only tests that assert literal pretty-printed indentation.
- Host review preserves its fresh-context, tool-enforced read-only, cross-family contract; `review-host` plumbing handles only reservation, receipt, and lease mechanics.
- Final verification gate: `python3 scripts/run_tests_parallel.py`, `uvx ruff@0.16.0 check .`, `./scripts/sync-codex.sh --check`, `python3 scripts/gen_tracker_manifest.py`, and smoke tests for fan-out, `land`, `pilot snapshot`, `deps`, and `usage`.

## Acceptance Criteria

- **R1:** Auto-finalize clean all-`SHIP` zero-finding fan-out rounds inside `impl-review-fanout`: when all surviving draws parse cleanly as `SHIP` with zero findings, `flowctl` finalizes the round, writes the receipt, and emits the terminal verdict in phase 1 (eliminating 3 coordinator turns and 10-25 KB of sidecar reads per clean fan-out). Any non-`SHIP` draw, parsed finding, or parse warning preserves the existing two-phase merge flow unchanged. Errors: partial draw failures with zero surviving `SHIP` draws still refund the reservation as today; failed receipt write returns non-zero without silently claiming `SHIP`.

- **R2:** Bundle `land` probing and switch GitHub spec discovery from the recursive trees API to local `git fetch`:
  - GitHub `land` fetches `refs/pull/<PR>/head` (and base ref when needed) and inspects `.flow/specs/*.json` and `.flow/tasks/` via `git ls-tree` and `git show`, matching `forge-gitlab.md` and `forge-bitbucket.md` (eliminates up to 330 per-blob API calls/tick and `truncated: true` false stops).
  - Add a zero-judgment `flowctl land probe <pr> --json` helper (or bundled script) returning forge, `land` config, PR metadata, checks, `reviewDecision`, unresolved thread count, `behind_by`, matched specs, open children, and stack status in one call (collapsing 10-15 LLM turns per tick).
  - Expose `flowctl forge readiness <pr> --json` so GitLab and Bitbucket `land` ticks stop creating detached worktrees and running full `pilot snapshot` on clean ticks.
  Errors: unreachable remote, unfetchable PR ref, closed/merged PR, or unreadable spec JSON produce the same typed `NEEDS_HUMAN` / `NO_WORK` / `MERGED` stops as today.

- **R3:** Scope `pilot snapshot` to stop redundant network and inventory work:
  - Add `flowctl pilot snapshot --guards-only --json` returning `guards.dirty`, `forge`, `config`, and `sync_active` with zero forge PR listings, candidate scans, or `git ls-remote` calls; update `goal-mode.md` and `issue-start.md` start guards to use it.
  - When `--spec <id>` is passed, populate `current_branch_prs` via branch-scoped `list_prs` (or reuse `selected.pr` when `current == branch`) instead of `list_prs(state="open", limit=1000)`.
  Errors: dirty working tree, missing spec, or forge CLI error preserve existing exit codes and JSON fields.

- **R4:** Enrich `specs --json` and `preflight --json`, and compact `json_output`:
  - Include `depends_on_epics` (already loaded in memory by `cmd_specs`) in `specs --json` and remove the per-spec `flowctl show` loop from `flow-next-deps/SKILL.md` (cuts ~20+ cold spawns to 1 without adding a new graph engine).
  - Add `ready_count` and `open_count` to `flowctl preflight --json`, drop duplicate `probes.config`, and emit glossary summary metadata (count and file paths) by default instead of dumping 23.6 KB of raw definitions; update `capture`, `refine`, `plan`, and `chart` callers accordingly.
  - Switch `json_output()` in `flowctl.py` from `indent=2` to compact JSON (`separators=(",", ":")`) for a 21-29% token reduction across all `--json` outputs.
  Errors: missing config/glossary degrades fail-open as today; `refine` doc-aware still loads needed glossary terms cleanly; all JSON contract tests pass.

- **R5:** Split `templates/usage.md` (17.8 KB) into a lean CLI cheatsheet (~3.6 KB) and `flowctl usage --orchestration` (~14.2 KB):
  - `flowctl usage` prints only the CLI cheatsheet and lifecycle workflow; `flowctl usage --orchestration` prints the multi-CLI bridge and model-steering recipes.
  - Update `flowctl_bootstrap.py` fast path, `rules/flow-next.mdc`, and bridge references (`worker-bridge.md`, `CLAUDE.md`/`AGENTS.md` setup snippet) to point bridge lookups at `flowctl usage --orchestration`.
  Errors: missing template file returns the existing error message and non-zero exit; `--help` documents `--orchestration`.

- **R6:** Deduplicate inline spec bodies, batch host review prompts, and share fetched issue payloads:
  - Add `--no-spec-body` to `flowctl anchor` and use it in `flow-next-work/phases.md` when the inline path already read the spec body in the same context (removes 3x verbatim spec-body duplication on `flow` -> `work --no-plan`).
  - Add `--axes <csv>` to `flowctl review-prompt` so `workflow-host.md` generates all three axis prompts in one `flowctl` invocation instead of three.
  - Allow `issue-start.md` and `open-issue-intake.md` to pass their fetched issue JSON file path into `flow-next-capture` so capture skips a second remote `tracker wire read`.
  Errors: missing or invalid issue JSON file falls back to live `tracker wire read`; invalid `--axes` values reject with non-zero exit.

- **R7:** Idle-deadline streaming `Popen` for Codex reviews and host-review reserve/record plumbing:
  - Replace blocking `subprocess.run` in `run_codex_exec` with idle-deadline streaming `Popen` so wedged processes fail fast on prolonged silence while active long reviews survive past 600 s without abandoning 2700 s leases.
  - Extract duplicated host-review reservation, base-branch resolution, lease, and receipt-recording bash boilerplate from the three `workflow-host.md` files into `flowctl review-host prepare` and `flowctl review-host record` helpers.
  Errors: idle timeout and total-timeout exits run the refund/cleanup path cleanly; missing cross-family pin still fails closed.

- **R8:** Bound `plan-sync` and `quality-auditor` context reads:
  - `agents/plan-sync.md` filters accepted decision entries by module/tags/file overlap before calling `memory read`, and caps cross-spec `cat` reads to specs overlapping touched modules or explicit dependencies.
  - `agents/quality-auditor.md` excludes lockfiles, generated files, and `.flow/` state files from its `git diff` command so neither parallel Opus subagent ingests ignored diff noise.
  Errors: empty filter result skips cleanly with no error surface; `git diff` pathspec exclusions never hide source or test changes.

- **R9:** Coordinate with `fn-190` (`flowctl` importable `.pyc` entry + lazy subparser dispatch):
  - At 60.4K lines, cold `flowctl.py` startup is ~300-358 ms vs ~70 ms cached `.pyc` (~30 ms with lazy subparsers). Either ship `fn-190` as part of this wave or explicitly defer it in Decision Context if the 8-site launcher graph is kept separate.
  Errors: no error surface beyond `fn-190`'s own Windows/POSIX launcher and bytecode-invalidation contract.

## Boundaries

- No behavioral changes that alter review catch rate, routing decisions, or what a model reads from skill prose (Wave 3 evals).
- No new graph engine in `flowctl` for `deps` (R4 only exposes `depends_on_epics` already loaded by `cmd_specs`).
- No removal of cross-family, read-only, or no-embed review contracts.

## Decision Context

These changes require Python/shell plumbing updates and contract tests rather than simple text edits, so they are separated from Wave 1. Every item is deterministic and testable with unit and smoke tests without needing stochastic LLM evals.

## Strategy Alignment

Follows `STRATEGY.md` "flowctl grows only under burden of proof" (every added verb or flag is pure zero-judgment plumbing replacing multi-turn agent shell assembly, matching the `fn-139` tracker facade and `fn-259` snapshot pattern) and "The artifact is the contract" (identities and bounded payloads over redundant body dumps).
