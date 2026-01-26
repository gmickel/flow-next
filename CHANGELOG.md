# Changelog

All notable changes to the gmickel-claude-marketplace.

## [flow-next 0.18.21] - 2026-01-26

### Added

- **Backend spec fields for tasks and epics** — New optional `impl`, `review`, `sync` fields on tasks and `default_impl`, `default_review`, `default_sync` on epics. These fields store preferred AI backend + model specs (e.g., `codex:gpt-5.2-high`, `claude:opus`). Pure storage - flowctl doesn't interpret them; orchestration products like flow-swarm use them to route different tasks to different backends.

- **`flowctl task set-backend`** — Set backend specs on a task: `flowctl task set-backend fn-1.1 --impl codex:gpt-5.2-high --review claude:opus`

- **`flowctl epic set-backend`** — Set default backend specs on an epic: `flowctl epic set-backend fn-1 --impl codex:gpt-5.2-codex`

- **`flowctl task show-backend`** — Query effective backend specs for a task (task + epic levels): `flowctl task show-backend fn-1.1 --json`

**Note:** These fields have no effect on current flow-next/Ralph usage. They enable an upcoming orchestration product where different tasks can use different backends (complex refactors → expensive reasoning models, simple fixes → fast cheap models).

## [flow-next 0.18.20] - 2026-01-26

### Changed

- **Task sizing: M is the sweet spot** — Updated plan skill to prefer M-sized tasks over many S tasks. Sequential S tasks should be combined into M tasks. Added "7+ tasks = look for tasks to combine" heuristic.

- **OAuth example: 4 tasks → 2 tasks** — Task breakdown example now shows combining sequential backend work into one M task + separate frontend S task. Added "over-split" anti-pattern example.

- **Plan review checks for over-splitting** — Added "Task sizing" as review criterion #8: flags 7+ tasks or sequential S tasks that should be combined.

- **Interview balances split vs combine** — Architecture questions now probe both: "can tasks touch disjoint files?" AND "can sequential steps be combined into M-sized tasks?"

## [flow-next 0.18.19] - 2026-01-26

### Changed

- **Memory and Plan-Sync enabled by default** — New projects now have `memory.enabled: true` and `planSync.enabled: true` out of the box. Cross-epic sync remains disabled by default to avoid long Ralph loops. Disable with `flowctl config set memory.enabled false` or `flowctl config set planSync.enabled false`.

## [flow-next 0.18.18] - 2026-01-25

### Fixed

- **Preserve GH-73 COMPLETE handling fix** — PR #74 inadvertently reverted the fix for premature completion in Ralph. Workers should NEVER output `<promise>COMPLETE</promise>` (prompts forbid it); completion is detected via selector returning `status=none`. Restored the ignore-and-log behavior.

### Documentation

- **Improved `--files` guidance in plan-review skills** — Added explanation of how to identify which files to pass (read epic spec, find affected paths) instead of just a hardcoded example.

## [flow-next 0.18.17] - 2026-01-25

### Fixed

- **Filter artifact files using is_task_id() validation** — Replaced weak `"." not in task_id` check with proper `is_task_id()` regex validation. Fixes `KeyError: 'title'` crash when `.flow/tasks/` contains artifact files like `fn-1.2-review.json`. Works with both legacy (`fn-3.1`) and new (`fn-3-sds.1`) ID formats. Thanks to @kirillzh for the contribution!

## [flow-next 0.18.16] - 2026-01-24

### Added

- **Parallelization guidance for task splitting** — Plan skill now includes guidance to minimize file overlap when splitting tasks. Tasks touching disjoint files can be worked in parallel without merge conflicts.

- **Plan-review parallelizability criterion** — Added "Parallelizability" as review criterion #3: flags independent tasks that touch overlapping files.

- **Interview probe for parallel work** — Architecture questions now include "Can this be split so tasks touch disjoint files?"

## [flow-next 0.18.15] - 2026-01-24

### Fixed

- **Restored manual prompt building for RP reviews** — Reverted from the flaky two-step chat approach (`--response-type review` + follow-up) back to the reliable single-chat approach with custom review prompts.

  **Why this was necessary:**
  - The `--response-type review` mode introduced in 0.14.0 delegates prompt construction to RepoPrompt's builder, giving us no control over the exact prompt sent to the reviewer model
  - RP returns its own verdict format (`request-changes`, `approve`, etc.) instead of our `<verdict>SHIP|NEEDS_WORK|MAJOR_RETHINK</verdict>` tags
  - This required a follow-up message just to get the verdict in the correct format, making the flow fragile
  - Versions 0.18.5 through 0.18.12 were all attempts to patch this two-step flow, adding warnings, stronger instructions, and format reminders — none fully resolved the flakiness
  - In autonomous operation (Ralph), this unreliability breaks the review loop entirely when the model skips the follow-up or misparses the builder's verdict

  **What changed:**
  - Removed `--response-type review` from `setup-review` calls
  - Restored Phase 2 manual file selection (explicitly add changed files)
  - Restored Phase 3 `prompt-get` + custom review prompt with full Carmack criteria and verdict requirement baked in
  - Single `chat-send --new-chat` returns verdict directly — no follow-up needed

  **What was preserved:**
  - MAX_REVIEW_ITERATIONS=3 (reduced from 5)
  - Checkpoint save/restore for context compaction recovery
  - Task spec inclusion and syncing in plan-review
  - All flowctl.py improvements (`--chat-id`, `--mode`, etc. remain available)

## [flow-next 0.18.14] - 2026-01-24

### Fixed

- **Codex sandbox on Windows blocking all reads** — Codex CLI's `read-only` sandbox uses Windows AppContainer which blocks ALL shell commands, including file reads. Added `--sandbox` flag to `flowctl codex impl-review` and `flowctl codex plan-review` with `auto` mode that resolves to `danger-full-access` on Windows and `read-only` on Unix. Added `CODEX_SANDBOX` config option for Ralph. Full file contents are now embedded in review prompts to work around sandbox limitations.

### ⚠️ Breaking Change: `--files` required for `flowctl codex plan-review`

`flowctl codex plan-review` now requires `--files` (comma-separated **code** file paths) so the reviewer has concrete repository context (and so Windows can embed file contents when the Codex sandbox blocks reads).

Migration: update any scripts to pass `--files`, e.g. `--files "src/auth.ts,src/config.ts"`.

### Added

- **`--sandbox` flag for codex commands** — Supports `read-only`, `workspace-write`, `danger-full-access`, and `auto` modes
- **`CODEX_SANDBOX` config option for Ralph** — Configure sandbox mode in `scripts/ralph/config.env` (default: `auto`)
- **Exit code 3 for sandbox errors** — flowctl returns exit code 3 for sandbox configuration issues

### Documentation

- flowctl.md: Added `--sandbox` flag documentation for both impl-review and plan-review
- flowctl.md: Documented `--files` requirement for plan-review
- ralph.md: Added `CODEX_SANDBOX` config option with valid values
- ralph.md: Added troubleshooting section for "blocked by policy" errors
- CLAUDE.md: Added Windows sandbox note in Codex section

**Note:** Re-run `/flow-next:setup` or `/flow-next:ralph-init` after plugin update to get sandbox fixes.

## [flow-next 0.18.13] - 2026-01-23

### Fixed

- **Ralph exits early on NEEDS_WORK despite force_retry** — Worker returns `<promise>COMPLETE</promise>` after marking task done. Ralph checked for COMPLETE *after* setting `force_retry=1` for NEEDS_WORK, causing premature exit. Now skips COMPLETE exit when `force_retry=1`.

## [flow-next 0.18.12] - 2026-01-23

### Fixed

- **Agent skipping verdict follow-up** — Added ⚠️ WARNING block after Step 2 explicitly stating RP's verdict is INVALID and Step 4 is MANDATORY. Agent was seeing builder's `request-changes` verdict and jumping to fix loop without sending the follow-up to get our verdict format.

## [flow-next 0.18.11] - 2026-01-23

### Fixed

- **RP uses its own verdict format** — Builder's `response_type=review` returns RP's verdict format (`request-changes`, `approve`, etc.) not ours. Updated instructions to explicitly IGNORE builder verdict and extract verdict ONLY from the follow-up chat response. Added clearer verdict tag requirements with "Do NOT use any other verdict format."

## [flow-next 0.18.10] - 2026-01-23

### Changed

- **Stronger workflow.md references** — Changed "Read workflow.md" to "⚠️ MANDATORY: Read workflow.md BEFORE executing RP backend steps" and "⚠️ STOP: Read workflow.md NOW" to ensure agents follow the link. SKILL.md is a summary; workflow.md has the complete flow.

## [flow-next 0.18.9] - 2026-01-23

### Fixed

- **Missing verdict follow-up step in SKILL.md** — Builder returns review findings but NOT a verdict tag. Added explicit follow-up chat step to request verdict in both impl-review and plan-review SKILL.md files. Without this, Ralph breaks waiting for a verdict that never comes.

## [flow-next 0.18.8] - 2026-01-23

### Fixed

- **plan-review also missing --response-type review** — Same fix as 0.18.7 but for plan-review skill. Updated SKILL.md, workflow.md, and flowctl-reference.md.

## [flow-next 0.18.7] - 2026-01-23

### Fixed

- **impl-review SKILL.md missing --response-type review** — The actual bug was in SKILL.md which agents read. The example setup-review call was missing `--response-type review`, causing RP to use default "clarify" mode instead of "review" mode.

## [flow-next 0.18.6] - 2026-01-23

### Fixed

- **rp-cli builder --type flag** — Use `--type review` (shorthand flag) instead of `response_type=review` (key=value). Turns out both work, but the real issue was SKILL.md - see 0.18.7.

## [flow-next 0.18.5] - 2026-01-23

### Fixed

- **rp-cli builder response_type format** — Changed from invalid `--response-type review` to `response_type=review`. Still didn't work - see 0.18.6.

- **Added verdict requirement to review instructions** — The builder review instructions now explicitly request a verdict tag (`<verdict>SHIP|NEEDS_WORK|MAJOR_RETHINK</verdict>`), ensuring consistent verdict output from RP reviews.

- **Fixed cli-reference.md** — Updated rp-cli example to use `--type` shorthand instead of invalid `--response-type` flag.

## [flow-next 0.18.4] - 2026-01-23

### Fixed

- **Ralph now auto-closes epics in unscoped runs** — Previously `maybe_close_epics()` only ran when `EPICS=...` was specified, meaning unscoped Ralph runs would never auto-close epics even when all tasks were done. This blocked downstream epics that depended on them. Now Ralph checks all open epics and closes any with all tasks completed. Thanks to [@VexyCats](https://github.com/VexyCats) for the report!

- **Added `list_open_epics()` helper** — New function to get all non-done epic IDs from flowctl for unscoped runs.

## [flow-next 0.18.3] - 2026-01-23

### Fixed

- **Ralph now enforces receipt verdict** — Previously Ralph only checked that impl-review receipts existed but ignored the `verdict` field. Now Ralph reads the verdict from the receipt file and forces a retry if `NEEDS_WORK`, even if the worker marked the task as done. This fixes issue #70 where NEEDS_WORK verdicts from Codex reviews were being ignored. Thanks to [@VexyCats](https://github.com/VexyCats) for the detailed report!

- **Added `read_receipt_verdict()` helper** — New function in ralph.sh to read the verdict field from receipt JSON files.

## [flow-next 0.18.2] - 2026-01-23

### Changed

- **Expanded `/flow-next:prime` to 8 pillars (48 criteria)** — Now matches Factory.ai's comprehensive assessment:
  - Agent Readiness (Pillars 1-5): Style & Validation, Build System, Testing, Documentation, Dev Environment
  - Production Readiness (Pillars 6-8): Observability, Security, Workflow & Process

- **Two-tier scoring** — Agent Readiness score (determines maturity level, fixes offered) + Production Readiness score (reported only, no fixes). Gives full visibility while keeping remediation focused.

- **3 new scouts** for production readiness:
  - `observability-scout` — Structured logging, tracing, metrics, error tracking, health endpoints
  - `security-scout` — Branch protection, secret scanning, CODEOWNERS, Dependabot (via GitHub API)
  - `workflow-scout` — CI/CD pipelines, PR templates, issue templates, release automation

- **Test verification** — Now runs `pytest --collect-only` (or equivalent) to verify tests actually work, not just that files exist.

- **GitHub API integration** — Uses `gh` CLI to check branch protection, secret scanning status, and repository settings.

## [flow-next 0.18.0] - 2026-01-23

### Added

- **`/flow-next:prime` command** — Agent readiness assessment inspired by Factory.ai's framework. Analyzes your codebase and proposes non-destructive improvements.

- **6 haiku scouts** for fast parallel assessment:
  - `tooling-scout` — Scans linters, formatters, pre-commit hooks, type checking
  - `claude-md-scout` — Analyzes CLAUDE.md/AGENTS.md quality and completeness
  - `env-scout` — Checks .env.example, Docker, devcontainer, setup scripts
  - `testing-scout` — Evaluates test framework, coverage config, test commands
  - `build-scout` — Reviews build system, scripts, CI configuration
  - `docs-gap-scout` — README, ADRs, architecture docs

- **Maturity levels 1-5** — Repositories scored from Minimal (1) to Autonomous (5). Level 3 (Standardized) is the recommended target for most teams.

- **Interactive remediation** — After assessment, offers to fix gaps with user consent via AskUserQuestion. Supports `--report-only` (skip fixes) and `--fix-all` (apply all without asking).

- **Remediation templates** — Built-in templates for common fixes: CLAUDE.md, .env.example, pre-commit hooks, and more.

### Technical Details

The prime workflow:
1. Runs scouts in parallel (fast, ~15-20 seconds)
2. Synthesizes findings into a readiness report with pillar scores
3. Uses AskUserQuestion for each category of improvements
4. Applies approved fixes non-destructively (never overwrites without consent)
5. Offers re-assessment to show improvement

Works for both greenfield and brownfield projects.

## [flow-next 0.17.4] - 2026-01-22

### Fixed

- **Bash `!=` operator in skill markdown** — Version check in `/flow-next:plan` and `/flow-next:interview` was failing with syntax error when Claude Code parsed the bash code blocks. The `!` character was being escaped to `\!` during processing. Rewrote conditionals to avoid `!=` operator. Thanks @clairedotcom for reporting (#68).

## [flow-next 0.17.2] - 2026-01-21

### Fixed

- **Windows compatibility** — `fcntl` import now conditional; was causing `ModuleNotFoundError` on Windows since 0.17.0. File locking gracefully degrades to no-op on Windows (acceptable for single-machine use).

## [flow-next 0.17.1] - 2026-01-21

### Fixed

- **Plan review now includes task specs** — `/flow-next:plan-review` previously reviewed only the epic spec, leaving task specs stale when epic changes occurred during the fix loop. Now both RP and Codex backends include task specs in the review. Reviewers can flag inconsistencies between epic and task specs, and the fix loop instructs the agent to sync affected task specs.

### Added

- **`task set-spec --file`** — Full spec replacement mode for task specs (like `epic set-plan --file`). Supports both file paths and stdin (`-`). Use in plan-review fix loops to sync task specs after epic changes.
- **Consistency checking in review criteria** — Both plan review backends now explicitly check for epic/task consistency: contradicting requirements, misaligned acceptance criteria, stale state/enum references.
- **Task sync instructions in re-review preamble** — When re-reviewing, Codex backend now instructs the agent to sync task specs if epic changes affected them.

### Changed

- **Review prompt expanded** — Plan review now includes `<task_specs>` section with all task spec content (Codex backend). RP backend adds task spec files to selection.
- **Fix loop steps updated** — Both SKILL.md and workflow.md now include task spec sync as explicit step (step 3 in SKILL.md, step 4 in workflow.md) before re-review.
- **Anti-pattern added** — "Updating epic spec without syncing affected task specs" documented as anti-pattern in workflow.md.

### Technical Details

Task specs need syncing when epic changes affect:
- State/enum values referenced in tasks
- Acceptance criteria that tasks implement
- Approach/design decisions tasks depend on
- Lock/retry/error handling semantics
- API signatures or type definitions

## [flow-next 0.17.0] - 2026-01-21

### Added

- **Shared runtime state for parallel worktree execution** — Task runtime state (status, assignee, claim info, evidence) now lives in `.git/flow-state/` instead of the tracked definition files. This enables multiple git worktrees to share task state, unlocking parallel orchestration workflows where different agents work on different tasks simultaneously.

- **StateStore abstraction** — New `LocalFileStateStore` with per-task `fcntl` locking prevents race conditions when multiple processes claim or update tasks concurrently.

- **New commands**:
  - `flowctl state-path` — Shows resolved state directory (useful for debugging)
  - `flowctl migrate-state [--clean]` — Migrates existing repos to the new state model. `--clean` removes runtime fields from tracked JSON files after migration.

- **Checkpoint schema v2** — Checkpoints now include runtime state, enabling full restore across worktrees.

### Changed

- **Merged read path** — All task reads now merge definition + runtime state.
- **Atomic task claiming** — `flowctl start` validates and writes under the same lock, eliminating TOCTOU race conditions.
- **Reset semantics** — `flowctl task reset` now properly clears runtime state (overwrite, not merge).

### Backward Compatibility

**No action required.** Existing repos work without any migration. The merged read path automatically falls back to reading runtime fields from definition files when no state file exists. Migration is only needed if you want to:
- Use parallel worktree orchestration
- Stop tracking runtime state in git (cleaner diffs)

### Technical Details

State directory resolution order:
1. `FLOW_STATE_DIR` environment variable (explicit override)
2. `git --git-common-dir` + `/flow-state` (worktree-aware, shared)
3. `.flow/state` fallback (non-git or old git)

Runtime fields moved to state: `status`, `updated_at`, `assignee`, `claimed_at`, `claim_note`, `evidence`, `blocked_reason`

## [flow-next 0.16.0] - 2026-01-21

### Added

- **Epic-aware planning** — New `epic-scout` subagent runs during `/flow-next:plan` research phase (parallel with other scouts). Scans open epics for dependency relationships and auto-sets `depends_on_epics` when found. No user prompts needed — findings reported at end of planning.
- **Docs-gap detection** — New `docs-gap-scout` subagent identifies documentation that may need updates (README, API docs, ADRs, CHANGELOG, etc.). Adds acceptance criteria to relevant tasks — implementer decides actual content.
- **Cross-epic plan-sync** — Optional mode for plan-sync agent. When `planSync.crossEpic: true`, also checks other open epics for stale references after task completion. **Default: false** (avoids long Ralph loops).
- **New config option** — `planSync.crossEpic` (boolean, default false). Enable via `/flow-next:setup` or `flowctl config set planSync.crossEpic true`.

### Changed

- Plan-sync agent now accepts `CROSS_EPIC` input and has new Phase 4b for cross-epic checking
- Setup workflow shows new cross-epic config option (only asked if plan-sync is enabled)
- `memory-scout` model changed from opus to haiku (task is mechanical grep/read, doesn't need reasoning)

### Notes

- **Re-run `/flow-next:setup`** to get the new config option and update local flowctl
- Cross-epic sync is conservative — only flags clear API/pattern references, not general topic overlap

## [flow-next 0.15.0] - 2026-01-21

### Changed

- **WORKER_TIMEOUT default** — 45min → 1hr (3600s). Timeout is now a safety guard against runaway workers, not flow control. Properly sized tasks shouldn't hit it ([#59](https://github.com/gmickel/gmickel-claude-marketplace/issues/59))
- **MAX_REVIEW_ITERATIONS default** — 5 → 3. Tighter cap; if 3 fix cycles don't pass review, task/spec is likely too big or ambiguous. Let next Ralph iteration start fresh
- **Timeout philosophy** — Docs and comments now clarify: time is arbitrary, `MAX_REVIEW_ITERATIONS` is the real control. One Ralph iteration = impl + review, should complete within single context window

## [flow-next 0.14.4] - 2026-01-21

### Added

- **Version mismatch warning** — `/flow-next:plan` and `/flow-next:interview` now check if local setup is outdated. If `.flow/meta.json` has older `setup_version` than plugin, prints: "Plugin updated to vX.Y.Z. Run /flow-next:setup to refresh local scripts." Non-blocking, continues normally.

## [flow-next 0.14.3] - 2026-01-21

### Changed

- **Setup skips already-configured options** — Re-running `/flow-next:setup` now detects existing config (memory, planSync, review.backend) and skips those questions. Shows current config with `flowctl config set` commands for changing values.
- **Review backend descriptions improved** — RepoPrompt now highlights auto-scoped diffs and ~65% fewer tokens; Codex notes cross-platform + GPT 5.2 High. No "(Recommended)" — user decides based on platform/needs.

## [flow-next 0.14.2] - 2026-01-21

### Fixed

- **Task-level interview guard** — When interviewing a task (fn-N.M) that already has planning content (file refs, sizing, approach), interview now preserves that detail instead of overwriting. Only acceptance criteria can be appended, or user is directed to interview the epic instead.

## [flow-next 0.14.1] - 2026-01-21

### Fixed

- **Interview skill boundary ambiguity** — Interview was creating full implementation plans with tasks, conflicting with `/flow-next:plan`. Now:
  - Interview creates epic with refined requirements only (problem, decisions, edge cases)
  - Interview does NOT create tasks — that's plan's job
  - When interviewing an epic that already has tasks, only the epic spec is updated
  - Clear "NOT in scope" section lists what belongs in plan vs interview

### Changed

- **Epic spec template** — Renamed "Approach" → "Key Decisions" + added "Open Questions" section to clarify interview captures requirements, not implementation approach
- **Input-type routing** — Interview now handles different inputs differently:
  - New idea → create epic stub, suggest `/flow-next:plan`
  - Existing epic with tasks → update epic spec only, don't touch tasks
  - Task ID → update task requirements only
  - File path → rewrite file, suggest `/flow-next:plan <file>`
- **README clarification** — Added explicit "Interview vs Plan boundary" note in "When to Use What" section

Thanks to @tiagoefreitas for the detailed issue report ([#62](https://github.com/gmickel/gmickel-claude-marketplace/issues/62)).

## [flow-next 0.14.0] - 2026-01-21

### ⚠️ Breaking Change: RepoPrompt 1.6.0+ Required

The RepoPrompt (rp) backend for `/flow-next:impl-review` now uses the new **builder review mode** introduced in RepoPrompt 1.6.0. This provides better context discovery and more focused reviews.

**Before upgrading**: Check your RepoPrompt version with `rp-cli --version`. If you're on an older version, update RepoPrompt first or use `--review=codex` as an alternative.

### Changed

- **RP impl-review uses builder review mode** — Instead of manually building review prompts and selecting files, the builder's discovery agent now:
  - Automatically includes git diffs for the commits being reviewed
  - Selects relevant context files with full codebase awareness
  - Produces structured review findings before verdict
  - Lower token usage (~26K vs ~71K) with better coverage

- **New flowctl rp commands**:
  - `--response-type review` on `rp builder` and `rp setup-review`
  - `--chat-id` on `rp chat-send` for conversation continuity
  - `--mode` on `rp chat-send` (chat/review/plan/edit)

- **Simplified RP workflow** — Removed manual file selection (Phase 2) and elaborate prompt building (Phase 3). Builder handles context discovery; follow-up chat requests verdict.

- **Fix loop uses `--chat-id`** — Re-reviews now use explicit chat ID for session continuity instead of relying on tab state.

### Added

- RP 1.6.0 requirement notice in SKILL.md and workflow.md

### Unchanged

- Codex backend — No changes, works as before
- Plan-review — No changes, only impl-review affected
- Receipt format — Compatible with Ralph

## [flow-next 0.13.0] - 2026-01-19

### ⚠️ Significant Planning Workflow Changes

**The Problem:** Plans were doing implementation work. Epic and task specs contained complete function bodies, full interface definitions, and copy-paste ready code blocks. This caused:

1. **Wasted tokens in planning** — Writing code that won't ship
2. **Wasted tokens in review** — Reviewing code that won't ship
3. **Wasted tokens in implementation** — Re-writing essentially the same code
4. **Plan-sync drift** — Implementer does it slightly differently, specs and reality diverge

Real examples from production plans showed 28KB epic specs with complete TypeScript implementations, and task specs that were literally the code to write — nothing left for `/flow-next:work` to do.

**The Solution:** Plans describe WHAT to build and WHERE to look — not HOW to implement.

### Added

- **"The Golden Rule" in SKILL.md** — Explicit guidance on what code belongs in plans vs. what doesn't
  - ✅ Allowed: Signatures, file:line refs, recent/surprising APIs, non-obvious gotchas
  - ❌ Forbidden: Complete implementations, full class bodies, copy-paste snippets (>10 lines)

- **Task sizing with T-shirt sizes** — Observable metrics instead of token estimates

  | Size | Files | Acceptance | Pattern | Action |
  |------|-------|------------|---------|--------|
  | S | 1-2 | 1-3 | Follows existing | ✅ Good |
  | M | 3-5 | 3-5 | Adapts existing | ✅ Good |
  | L | 5+ | 5+ | New/novel | ⚠️ Split |

  - Anchor examples for calibration (S = fix bug, M = new endpoint with tests, L = split it)
  - Good/bad breakdown examples (e.g., "Implement OAuth" → 4 S/M tasks)

- **Plan depth selection** — Users can now choose detail level upfront
  - `--depth=short` | `--depth=standard` (default) | `--depth=deep`
  - Or answer "1a/1b/1c" in setup questions

- **Follow-up options in Step 7** — After plan creation:
  - Go deeper on specific tasks
  - Simplify (reduce detail)
  - Loop until user chooses work/interview/review

- **Expanded examples.md** — Complete rewrite with:
  - Good vs. bad epic spec examples (side by side)
  - Good vs. bad task spec examples
  - Task breakdown examples
  - When code IS appropriate (with specific triggers)

- **"Current year is 2026" note** — Added to docs-scout, practice-scout, github-scout
  - Ensures web searches target recent documentation

- **Stakeholder analysis step** — New Step 2 asks who's affected (end users, developers, operations)
  - Shapes what the plan needs to cover
  - Pure backend refactor needs different detail than user-facing feature

- **Mermaid diagram guidance** — For data model and architecture changes
  - ERD for new tables/schema changes
  - Flowchart for service architecture
  - Examples in examples.md

### Changed

- **Subagent output rules** — All research scouts now have explicit guidance:
  - Show signatures, not full implementations
  - Keep snippets to <10 lines illustrating the pattern shape
  - Focus on "where to look" not "what to write"

- **"When to include code" heuristic** — Instead of asking models to know their knowledge cutoff (they can't), we use observable signals:
  - Docs say "new in version X" or "changed in version Y"
  - API differs from common/expected patterns
  - Recent releases (2025+) with breaking changes
  - Deprecation warnings or migration guides
  - **Anything that surprised you or contradicted expectations**

  This "surprised you" heuristic works because models CAN notice "this is different from what I'd expect" even if they can't reliably say "this is beyond my training data."

- **Default depth is STANDARD** — Balanced detail; short/deep on request

### Technical Notes

This is a behavior change in planning output. Existing `.flow/` data is fully compatible — only new plans will follow the tighter guidelines.

The changes affect:
- `skills/flow-next-plan/SKILL.md` — Golden Rule, depth selection
- `skills/flow-next-plan/steps.md` — Task sizing, complexity, Step 7 options
- `skills/flow-next-plan/examples.md` — Complete rewrite
- `agents/repo-scout.md` — Output rules
- `agents/context-scout.md` — Output rules
- `agents/practice-scout.md` — Output rules, year note
- `agents/docs-scout.md` — Output rules, year note
- `agents/github-scout.md` — Year note

### Feedback Welcome

This is a significant change to the planning philosophy. If you find plans are now too sparse, or the "surprised you" heuristic isn't working well, please open an issue at https://github.com/gmickel/gmickel-claude-marketplace/issues

We'd rather iterate based on real usage than guess at the right balance.

---

### Implementation Review Improvements

**Scenario exploration checklist** — Reviewers now systematically walk through failure scenarios for changed code:

- Happy path (normal operation)
- Invalid inputs (null, empty, malformed)
- Boundary conditions (min/max, empty collections)
- Concurrent access (race conditions, deadlocks)
- Network issues (timeouts, partial failures)
- Resource exhaustion (memory, disk, connections)
- Security attacks (injection, overflow, DoS)
- Data corruption (partial writes, inconsistency)
- Cascading failures (downstream service issues)

**Scope guardrail:** Checklist explicitly scoped to "changed code only" — reviewers flag issues in the changeset, not pre-existing patterns. Reinforces the verdict scope rules added in 0.12.10.

Affects:
- `skills/flow-next-impl-review/workflow.md` (RP backend)
- `scripts/flowctl.py` — `build_review_prompt()` and `build_standalone_review_prompt()` (Codex backend)

## [flow-next 0.12.10] - 2026-01-19

### Changed
- **WORKER_TIMEOUT default increased** - 30min → 45min (2700s) to accommodate complex impl-review loops (#59)
- **Review verdict scope tightened** - Codex impl/plan reviews now focus on issues introduced by the changeset, not pre-existing codebase issues
  - Reviewers may mention tangential issues as "FYI" without affecting verdict
  - Prevents review loops from drifting to unrelated improvements

### Added
- **Iteration tracking in receipts** - Receipts now include `"iteration": N` for debugging timeout/failure patterns
- **Enhanced timeout logging** - Timeouts now log phase, task/epic ID, iteration, and suggest increasing `WORKER_TIMEOUT`

## [flow-next 0.12.9] - 2026-01-18

### Fixed
- **Task jumping on timeout** - Prevent tasks from being skipped when worker times out after `flowctl done` but before receipt write (#57)
  - Reset `done→todo` if receipt missing (ensures `flowctl next` picks it up)
  - Fatal abort if reset fails (prevents silent skipping)
  - Delete corrupted/partial receipts on verification failure
- **Timeout retry handling** - Don't count timeouts against `MAX_ATTEMPTS_PER_TASK` (infrastructure ≠ code failure)
- **Unnecessary retry on proven completion** - Clear `force_retry` when task done + receipt valid

Thanks to @VexyCats for the detailed analysis and logs that identified the root cause.

## [flow-next 0.12.8] - 2026-01-18

### Added
- **MAX_REVIEW_ITERATIONS env var** - Cap fix+re-review cycles within impl-review (default 5) (#57)
- **WORKER_TIMEOUT documentation** - Now documented in config.env template and ralph.md

### Fixed
- **plan command description** - Removed "clear" to avoid collision with /clear command (#56)

## [flow-next 0.12.7] - 2026-01-18

### Fixed
- **Review fix loop no longer prompts user** - plan-review and impl-review now automatically fix all valid issues without asking for confirmation (#55)
  - Goal: production-grade world-class software and architecture
  - Added explicit "Never use AskUserQuestion in this loop" to SKILL.md and workflow.md

## [flow-next 0.12.6] - 2026-01-17

### Added
- **github-scout agent** - Cross-repo code search via `gh` CLI
  - Search public + private GitHub repos
  - Quality tiers: Authoritative (★5k+) → Established (★1k+) → Reference (★100+) → Examples
  - Signals: stars, recency, official repos, fork status
- **Enhanced docs-scout** - Source diving when docs fall short
  - Fetch library source via `gh api`
  - Search GitHub issues for known problems
- **Enhanced practice-scout** - Real-world examples from GitHub
  - Quality heuristics table (stars, recency, official = High weight)
  - Cross-reference pattern (2-3 repos = higher confidence)

### Changed
- Research phase now runs `github-scout` in parallel with other scouts
- Subagent count: 7 → 10

### Docs
- Force update tip in README (issue #54)

## [flow-next 0.12.1] - 2026-01-16

### Fixed
- **Single-task mode respects input** - `/flow-next:work fn-N.M` now stops after completing that task
  - Previously looped to next task after plan-sync (bug in Phase 3f)
  - Phase 1 now tracks SINGLE_TASK_MODE vs EPIC_MODE
  - Phase 3f only loops in EPIC_MODE; SINGLE_TASK_MODE goes to quality phase

## [flow-next 0.12.0] - 2026-01-16

### ⚠️ Migration Required

**Review backend no longer auto-detects.** Users who relied on automatic `which rp-cli` / `which codex` detection will see behavior changes:

**Why this change:**
- LLMs deviated from instructions, checking wrong binaries (`rp`, `repoprompt` instead of `rp-cli`)
- 12+ redundant subprocess calls per session (same detection in every skill)
- Ralph mode already handled this correctly via config—now all skills do too

| Command | Old behavior | New behavior |
|---------|--------------|--------------|
| `/flow-next:plan`, `/flow-next:work` | Auto-detect, pick first available | Asks which backend to use (discovery flow) |
| `/flow-next:impl-review`, `/flow-next:plan-review` | Auto-detect, pick first available | Error if no backend configured |

**To migrate:** Run `/flow-next:setup` once per repo, or pass `--review=rp|codex|none` explicitly.

**Backwards compatible:** All existing `.flow/` data works unchanged. Only review invocation behavior changed.

### Added
- **`flowctl review-backend` command** - Returns explicit `ASK` or configured backend (`rp`/`codex`/`none`)
  - Skills use this instead of complex jq checks
  - LLMs handle explicit string matching better than empty/non-empty checks
  - Reduces LLM deviation on conditional logic

### Changed
- **Remove runtime `which` detection from skills** - Skills no longer auto-detect review backends
  - Removed `which rp-cli` / `which codex` from impl-review, plan-review, work, plan skills
  - Priority order: `--review=X` flag > `FLOW_REVIEW_BACKEND` env > `.flow/config.json` > error
  - Run `/flow-next:setup` to configure preferred backend (one-time)
  - Reduces LLM deviation (agents checking wrong binary names)
  - Reduces subprocess overhead (12+ calls per session)
- **Simplified skill conditionals** - All skills now use `$FLOWCTL review-backend`
  - Check for `ASK` (not configured) vs actual value (configured)
  - No more jq parsing or empty string checks
- **Setup asks review backend** - `/flow-next:setup` now prompts for RepoPrompt/Codex/None
  - Writes to `.flow/config.json` under `review.backend`
  - Shows detection status (detected / not detected) for each option
- **README updated** - Removed "auto-detect" from priority documentation

## [flow-next 0.11.9] - 2026-01-16

### Fixed
- **Task-scoped impl-review** - Reviews now only cover current task's changes, not entire branch
  - Worker captures `BASE_COMMIT` before implementing
  - Passes `--base $BASE_COMMIT` to `/flow-next:impl-review`
  - Diff is `BASE_COMMIT..HEAD` instead of `main..HEAD`
  - Prevents re-reviewing already-shipped code from previous tasks
  - Critical for Ralph mode where all tasks share one branch

## [flow-next 0.11.8] - 2026-01-16

### Added
- **`/flow-next:sync` command** - Manual plan-sync trigger ([#43](https://github.com/gmickel/gmickel-claude-marketplace/issues/43))
  - Sync from task: `/flow-next:sync fn-1.2`
  - Scan whole epic: `/flow-next:sync fn-1`
  - Preview mode: `/flow-next:sync fn-1.2 --dry-run`
  - Ignores `planSync.enabled` config (manual = always run)
  - Works with any source task status (not just done)
- **Dry-run support in plan-sync agent** - Shows proposed changes without writing

### Fixed
- **flowctl tasks/list KeyError** - Task JSON uses `epic` field, not `epic_id`
  - Fixes `flowctl tasks --epic` crash
  - Fixes TUI task fetching on repos with collision-resistant IDs

## [flow-next 0.11.5] - 2026-01-16

### Fixed
- **Ralph hooks check removed** - Remove blocking local hooks check from `ralph.sh` ([#45](https://github.com/gmickel/gmickel-claude-marketplace/issues/45))
  - Plugin hooks work via `hooks/hooks.json` when installed normally
  - The check was blocking ALL users, not just `--plugin-dir` users
  - Test scripts handle the `--plugin-dir` workaround for bug #14410
- **Ralph upgrade support** - `/flow-next:ralph-init` now offers to update existing setup
  - Detects existing `scripts/ralph/` and asks to update
  - Preserves `config.env` and `runs/` during update
  - Existing users: re-run `/flow-next:ralph-init` to get the fix

### Changed
- **Dev guidance** - CLAUDE.md now recommends local marketplace install over `--plugin-dir`
  - `/plugin marketplace add ./` then `/plugin install flow-next@gmickel-claude-marketplace`
  - Hooks work correctly this way (no workaround needed)
- **Setup notes** - `/flow-next:setup` now mentions `/flow-next:ralph-init` for autonomous mode

## [flow-next 0.11.4] - 2026-01-16

### Added
- **Plan-sync agent** - Synchronizes downstream task specs when implementation drifts
  - Opt-in via `flowctl config set planSync.enabled true`
  - Runs after each task completes, compares spec vs actual implementation
  - Updates downstream tasks with accurate names, APIs, data structures
  - Skip conditions: disabled (default), task failed, no downstream tasks
  - Agent uses `disallowedTools: Task, Write, Bash` + prompt-based Edit restriction
- New phase 3e in `/flow-next:work` phases.md (between verify and loop)
- `planSync.enabled` config key in flowctl.py
- Smoke test for planSync config
- **Idempotent `flowctl init`** - Safe to re-run, handles upgrades
  - Creates missing dirs/files without destroying existing data
  - Merges new config keys into existing config.json (deep merge)
  - Old configs without `planSync` now work correctly
- **Config deep merge** - `load_flow_config()` merges with defaults
  - Missing keys automatically get default values
  - Existing user values preserved
- `/flow-next:setup` now uses `AskUserQuestion` for all options at once
  - Memory, Plan-Sync, Docs, Star questions in single UI interaction

## [flow-next 0.11.1] - 2026-01-15

### Fixed
- **flowctl tasks/list commands** - Added guard to skip artifact files lacking required fields (GH-21)

## [flow-next 0.11.0] - 2026-01-15

### Added
- **Worker subagent model** - Each task spawns isolated worker for implementation
  - Prevents context bleed between tasks during `/flow-next:work`
  - Re-anchor info stays with implementation (survives compaction)
  - Worker handles: re-anchor → implement → commit → review → complete
  - Main conversation handles task selection and looping only
  - `disallowedTools: Task` prevents infinite subagent nesting
- **Agent colors** - Visual identification in Claude Code UI
  - worker: blue (#3B82F6), repo-scout: green (#22C55E)
  - context-scout: cyan (#06B6D4), practice-scout: yellow (#EAB308)
  - docs-scout: orange (#F97316), memory-scout: purple (#A855F7)
  - flow-gap-analyst: red (#EF4444), quality-auditor: pink (#EC4899)

### Fixed
- **ralph-init efficiency** - Uses `cp -R` instead of read/Write per file
  - Single bash command copies all templates (including dotfiles)
  - Only edits `config.env` for review backend setting
- **Legacy `deps` key migration** - flowctl now handles both `deps` and `depends_on`
  - `normalize_task()` auto-migrates legacy `deps` to `depends_on`
  - Backwards compatible with older task files

## [flow-next 0.10.0] - 2026-01-15

### Added
- **Stdin support** (`--file -`) for flowctl commands
  - `epic set-plan`, `task set-description`, `task set-acceptance` now accept `-` to read from stdin
  - Enables heredoc usage: `flowctl epic set-plan fn-1 --file - <<'EOF'`
  - Eliminates temp file creation, solves shell escaping issues
- **Combined task set-spec command**
  - `flowctl task set-spec <id> --description <file> --acceptance <file>`
  - Sets both sections in single call (2 atomic writes vs 4)
- **Checkpoint commands** for compaction recovery
  - `flowctl checkpoint save --epic <id>` - Snapshots epic + all tasks to `.flow/.checkpoint-<id>.json`
  - `flowctl checkpoint restore --epic <id>` - Restores from checkpoint
  - `flowctl checkpoint delete --epic <id>` - Removes checkpoint file

### Changed
- Updated skill files to use stdin heredocs and `task set-spec` where applicable
- Plan-review workflow now saves checkpoint before review (recovery point)
- Added smoke tests for stdin, set-spec, and checkpoint commands

## [flow-next 0.9.0] - 2026-01-15

### Added
- **Browser automation skill** - Web testing, form filling, screenshots, scraping via agent-browser CLI
  - Core workflow: snapshot → ref-based interaction (@e1, @e2)
  - Progressive disclosure: main skill + debugging/auth/advanced references
  - Triggers on UI verification, doc lookup, baseline capture, e2e testing
- **Bundled Skills** section in README documenting utility skills

### Fixed
- `install-codex.sh` now auto-discovers all skills (was hardcoded, missing 7 skills)

## [flow-next-tui 0.1.2] - 2026-01-14

### Added
- Support for collision-resistant epic IDs (`fn-N-xxx` format)
  - Updated runs.ts receipt/block/epic parsing
  - Added tests for new ID format

### Fixed
- Resolved oxlint warnings (useless escapes, control-regex disable comments)

## [flow-next 0.8.0] - 2026-01-15

### Added
- **Ralph async control** (GH-14)
  - `flowctl status [--json]` - Show epic/task counts + active Ralph runs
  - `flowctl ralph pause/resume/stop/status [--run <id>]` - Control Ralph runs externally
  - Sentinel file mechanism in ralph.sh (PAUSE/STOP files at iteration boundaries)
  - All exit paths in ralph.sh now write `promise=COMPLETE` marker
- **Task reset command**
  - `flowctl task reset <id> [--cascade]` - Reset done/blocked tasks to todo
  - Clears evidence, claim fields, blocked_reason
  - `--cascade` resets dependent tasks in same epic
- **Epic dependency CLI**
  - `flowctl epic add-dep <epic> <dep>` - Add epic-level dependency
  - `flowctl epic rm-dep <epic> <dep>` - Remove epic-level dependency
- **CI tests** for all new async control commands (40 total, +9 new)

### Fixed
- README Troubleshooting: replaced nonexistent `task set` with `task reset`

## [flow-next 0.7.2] - 2026-01-14

### Added
- **Windows/Git Bash support** (GH-35, thanks @VexyCats)
  - Python detection: prefer `python3`, fallback to `python` (common on Windows)
  - Windows platform detection (`IS_WINDOWS` flag in ralph.sh)
  - Auto-generated flowctl wrapper for NTFS exec bit issues
  - Codex stdin-based prompt passing to avoid Windows CLI length limits (~8191 chars)
- **CI workflow** for cross-platform testing (Linux, macOS, Windows)
  - flowctl.py syntax and basic command tests
  - ralph.sh syntax and Python detection tests

### Changed
- `smoke_test.sh` and `ralph_smoke_test.sh` now use dynamic Python detection

## [flow-next 0.7.1] - 2026-01-14

### Added
- **C# symbol support** in flowctl.py (GH-36, thanks @clairernovotny)
  - Symbol extraction for `.cs` files: classes, interfaces, structs, enums, records, methods
  - Added `*.cs` to git grep reference search patterns

## [flow-next 0.7.0] - 2026-01-14

### Added
- **Collision-resistant epic IDs**: New epics use `fn-N-xxx` format with 3-char alphanumeric suffix
  - Prevents ID collisions when team members create epics simultaneously
  - Cryptographically secure suffix using Python `secrets` module
  - Legacy `fn-N` format still supported (backwards compatible)
  - Example: `fn-1-abc`, `fn-42-z9k`, tasks: `fn-1-abc.1`

### Changed
- Updated TUI to parse new ID format in run discovery
- Updated Ralph receipt parsing for new format
- Updated all error messages to mention both `fn-N` and `fn-N-xxx` formats

### Fixed
- **Codex reviews from `/tmp` dirs**: Added `--skip-git-repo-check` to `codex exec` (GH-33)
  - Fixes "not a git repo" errors when reviewing cloned/temp repos
  - Safe: reviews run with read-only sandbox
- **Ralph Ctrl+C handling**: Signal now properly terminates entire process tree
  - Added cleanup trap for SIGINT/SIGTERM in all modes
  - Fixed `timeout --foreground` detection for proper signal propagation

## [flow-next 0.6.3] - 2026-01-13

### Added
- **Spec file input for `/flow-next:work`**: Pass `.md` files directly to create epic and start work
  - `/flow-next:work docs/my-spec.md` creates epic from file, sets plan, creates task, executes
  - Detection order: task ID > epic ID > .md file > idea text
  - No changes to Ralph or existing workflows

## [flow-next-tui 0.1.1] - 2026-01-13

### Added
- **CI/CD workflow**: `.github/workflows/publish-tui.yml`
  - Triggers on push to main (flow-next-tui/**) or workflow_dispatch
  - Test matrix: ubuntu + macos, lint, test, pack-test
  - npm publish with OIDC trusted publishing (no NPM_TOKEN needed)
  - Version detection: only publishes when version differs from npm
- **Bump script**: `scripts/bump.sh` for semver version management
- Screenshot in README (replaces ASCII layout diagram)

### Changed
- README intro now explains what Flow-Next and Ralph are

## [flow-next 0.6.2] - 2026-01-13

### Added
- **TUI documentation**: Ralph docs now include TUI quickstart with screenshot
- TUI links in README and ralph.md

## [flow-next 0.6.1] - 2026-01-12

### Changed
- Ralph now always outputs stream-json to logs (TUI compatibility)
  - `--watch` flag only controls terminal display, not log format
  - Logs always parseable by TUI regardless of watch mode

### Fixed
- Add `--verbose` to quiet mode (required by Claude CLI for `stream-json` + `--print`)
  - Without this, quiet mode errored: "output-format=stream-json requires --verbose"
- Skip artifact files in `.flow/tasks/` that don't have `id` field (GH-21)
  - Prevents `KeyError` crash when Claude writes temp files like `fn-1.1-evidence.json`
  - Affects: `next`, `list`, `ready`, `show`, `validate` commands
- Ralph now exports `FLOW_REVIEW_BACKEND` based on `PLAN_REVIEW`/`WORK_REVIEW`
  - Skills inside Claude now see consistent backend config
  - Previously skills would re-detect and potentially choose different backend

## [flow-next 0.6.0] - 2026-01-12

### Added
- **Watch mode**: `--watch` flag streams tool calls in real-time with TUI styling (icons, colors)
- **Watch verbose**: `--watch verbose` also streams model text responses
- `watch-filter.py` for stream-json parsing (fail-open pattern, drains stdin on error)
- **Review feedback in receipts**: Codex plan/impl review receipts now include `review` field with full feedback (enables fix loops)
- `FLOW_RALPH_CLAUDE_PLUGIN_DIR` env var for testing with local dev plugin

### Changed
- Codex exec timeout increased 300s → 600s (matches RP timeout)
- Stream-json text extraction for reliable tag parsing in watch mode
- Conditional signal trap (only in watch mode)

### Fixed
- Improved Ctrl+C signal handling in watch mode

## [flow-next 0.5.9] - 2026-01-11

### Fixed
- Worker timeout now triggers retry instead of failing entire Ralph run
- macOS compatibility: detect `timeout`/`gtimeout`, warn if missing
- Python 3.9 compat: use `Optional[int]` not `int|None`

### Changed
- RP timeout configurable via `FLOW_RP_TIMEOUT` env (default 1200s/20min)
- Increased default timeout from 600s to 1200s for large repo context builders

## [flow-next 0.5.8] - 2026-01-11

### Added
- Context gathering prompt for Codex reviews (cross-boundary checks, related patterns)
- Rust, C/C++, Java symbol extraction in `gather_context_hints`
- Extended `find_references` to search `.rs`, `.c`, `.h`, `.cpp`, `.hpp`, `.java` files

### Changed
- Mark flow plugin as legacy with clearer messaging
- Wrap `extract_symbols_from_file` in try/except for graceful failure

## [flow-next 0.5.7] - 2026-01-11

### Changed
- Removed "Experimental" label - flow-next is production-ready
- Updated callouts to show feature maturity (not "New" on old features)
- Moved YOLO warning before Ralph setup section
- Improved safety warning format (bullet points)

### Added
- "vs Anthropic's ralph-wiggum" comparison section explaining architectural differences
- Plain-English re-anchoring explanation in "Why It Works"
- "How to Start" recommended workflow (spec -> interview -> plan -> work)
- Use-case matrix for choosing workflow (manual, review, autonomous)
- "Auto-blocks stuck tasks" feature to features list
- Troubleshooting section with common issues and fixes
- `ralph_once.sh` test step in Ralph Quick Start
- Verdict format documentation (SHIP, NEEDS_WORK, MAJOR_RETHINK)
- Partial run handling in morning review workflow
- Review criteria summary table (plan vs implementation)

### Fixed
- Clarified `/flow-next:setup` benefits with concrete examples
- Removed duplicate "Agents that finish what they start" tagline
- Updated repo description and topics via `gh repo edit`

## [flow-next 0.5.6] - 2026-01-11

### Fixed
- `ralph-init` now detects Codex CLI as fallback (was rp-cli only, defaulted to `none`)
- `ralph-init` asks user to choose if both RepoPrompt and Codex available
- Replace `--mode` with `--review` in all review prompts for consistency
- Review skills (plan-review, impl-review) now parse `--review` argument

### Changed
- Backend selection priority: `--review` arg > env > config > auto-detect

## [flow-next 0.5.5] - 2026-01-11

### Fixed
- Ralph no longer fails on non-zero exit code when task actually succeeded (#11)
- Checks both `task_status=done` and `verdict=SHIP` before treating exit code as failure
- Prevents false failures from transient errors (telemetry, model fallback, etc.)

### Added
- Smoke tests for non-zero exit code handling

### Chores
- ruff format on Python files

## [flow-next 0.5.4] - 2026-01-11

### Fixed
- Remove hardcoded `model: claude-opus-4-5-20251101` from review skills (#9)
- Skills now inherit session's default model, fixing 404 on limited API endpoints

## [flow-next 0.5.3] - 2026-01-11

### Fixed
- plan/work skills skip review question when backend already configured or in Ralph mode
- Checks `FLOW_REVIEW_BACKEND` env and `.flow/config.json` before prompting

## [flow-next 0.5.2] - 2026-01-11

### Fixed
- plan-review and impl-review skills now ask which backend when both available (interactive mode)
- Only prompts when not in Ralph mode (`FLOW_RALPH` not set)

## [flow-next 0.5.1] - 2026-01-11

### Added
- Codex option in plan/work skill setup questions (was missing from interactive flow)

### Fixed
- Plan and work skills now ask about Codex backend when available (not just RepoPrompt)
- Backend detection checks for both `codex` and `rp-cli` availability

## [flow-next 0.5.0] - 2026-01-11

### Added
- **Codex review backend** — cross-platform alternative to RepoPrompt (#5)
  - `flowctl codex plan-review` and `flowctl codex impl-review` commands
  - Uses GPT 5.2 High by default (no user config needed)
  - Session continuity via thread IDs in receipts
  - Context hints from changed files (symbols + references)
  - Same Carmack-level review criteria as RepoPrompt (7 plan + 7 impl)
- Backend selection: `flowctl config set review.backend codex` or `FLOW_REVIEW_BACKEND` env
- Comprehensive smoke tests for codex commands and context hints

### Changed
- Plan review prompts now use plan-specific criteria (was using impl-style criteria)
- Docs recommend RepoPrompt when available, codex as cross-platform alternative

## [flow-next 0.4.3] - 2026-01-11

### Fixed
- Stop hook no longer blocks when `PLAN_REVIEW=none` and `WORK_REVIEW=none` (#8)
- `REVIEW_RECEIPT_PATH` only exported when review is enabled
- Smoke test `write_config()` now properly updates PLAN_REVIEW/WORK_REVIEW on subsequent calls

## [flow-next 0.4.2] - 2026-01-11

### Fixed
- `flowctl done` now stores evidence in task JSON metadata (was only in markdown spec)
- Evidence accessible via `flowctl show <task> --json | jq '.evidence'`

## [flow-next 0.4.1] - 2026-01-11

### Added
- Hook enforcement: `flowctl done` now requires `--evidence-json` and `--summary-file` flags
- Morning review workflow guide in ralph.md

### Fixed
- Evidence field was empty because Claude drifted and skipped --evidence-json flag

## [flow-next 0.4.0] - 2026-01-11

### Changed
- **BREAKING**: `BRANCH_MODE=new` now creates a single run branch (`ralph-<run-id>`) instead of per-epic branches
- All epics work on the same run branch, making cherry-pick/revert of individual epics easy
- branches.json format simplified: `{base_branch, run_branch}` instead of epic mappings

### Fixed
- Fixed duplicate plan reviews when working on multiple epics (stale `.flow/` state across branches)

## [flow-next 0.3.22] - 2026-01-11

### Fixed
- Hook now tracks `flowctl done` with path/variable invocations ($FLOWCTL, .flow/bin/flowctl)

## [flow-next 0.3.21] - 2026-01-11

### Fixed
- ralph-init skill now explicitly tells user to run scripts from terminal

## [flow-next 0.3.20] - 2026-01-11

### Fixed
- Clarified Ralph docs: run scripts from terminal, not inside Claude Code

## [flow-next 0.3.19] - 2026-01-11

### Changed
- Removed verdict display from Ralph UI (too brittle, interfered with prompting)

### Fixed
- Added important notice to e2e notes about uninstalling marketplace plugins before dev testing

## [flow-next 0.3.18] - 2026-01-10

### Added
- `/flow-next:uninstall` command - removes flow-next from project with option to keep tasks
- Ralph UI improvements: elapsed time, progress counters, task titles, git stats, review stats
- `/flow-next:setup` now asks about GitHub starring

### Changed
- Quick start docs now promote `/flow-next:setup` as recommended step

## [flow-next 0.3.17] - 2026-01-10

### Added
- Memory system for persistent learning (opt-in via `flowctl config set memory.enabled true`)
- `flowctl config get/set` commands for project settings
- `flowctl memory init/add/list/search` commands for memory management
- `memory-scout` subagent for retrieving relevant memories during plan/work
- Auto-capture of review feedback to pitfalls.md (Ralph mode only)

### Fixed
- Re-review prompt now instructs reviewer to verify actual code, not just trust summary

## [flow 0.8.4] - 2026-01-10

### Fixed
- Removed incorrect `selected_paths` requirement for re-reviews (files auto-refresh)
- Re-review prompt now instructs reviewer to verify actual code, not just trust summary

## [flow-next 0.3.16] - 2026-01-10

### Changed
- `flowctl epic create` now defaults `branch_name` to epic ID if not specified

## [flow-next 0.3.15] - 2026-01-09

### Changed
- `/flow-next:setup` now detects doc status (missing/current/outdated) before asking
- Only prompts for files that actually need updates

## [flow-next 0.3.14] - 2026-01-09

### Added
- `flowctl list` command - shows all epics with tasks grouped, human-readable + JSON

## [flow-next 0.3.13] - 2026-01-09

### Added
- `flowctl epics` command - list all epics with task counts/progress
- `flowctl tasks` command - list tasks with `--epic` and `--status` filters

### Changed
- Removed misleading `list`/`ls` aliases from `show` command
- Updated all docs to reference new `epics`/`tasks` commands
- Added cross-references between human docs (flowctl.md) and agent docs (usage.md)
- File structure in docs now shows optional `/flow-next:setup` files

## [flow-next 0.3.12] - 2026-01-09

### Changed
- Optimized `/flow-next:setup` to minimize context footprint
  - CLAUDE.md snippet now minimal (~20 lines) with rules + quick commands
  - Full reference moved to `.flow/usage.md` (loaded on demand)
  - Added `<!-- BEGIN/END FLOW-NEXT -->` delimiters for idempotent updates

## [flow-next 0.3.11] - 2026-01-09

### Changed
- Expanded CLAUDE.md/AGENTS.md template with file structure, workflow, and rules
- Improved `flow-next` skill trigger phrases ("show me my tasks", "list epics", etc.)

## [flow-next 0.3.10] - 2026-01-09

### Fixed
- Clarified `/flow-next:setup` idempotency for existing `.flow/` directories
  - Safe to re-run; preserves existing epics/tasks
  - Clear version comparison logic for updates

## [flow-next 0.3.9] - 2026-01-09

### Added
- **`flow-next` skill**: General task management skill for quick operations
  - Triggers on: "add task", "show tasks", "what's ready", etc.
  - Provides flowctl path setup and CLI quick reference
  - Prevents agents from struggling to find/use flowctl
- **`/flow-next:setup` command**: Optional local install for power users
  - Copies flowctl scripts to `.flow/bin/` for CLI access
  - Adds flow-next instructions to CLAUDE.md or AGENTS.md
  - Enables use in non-Claude-Code environments (Codex, Cursor, etc.)
  - Tracks setup version for update detection
  - **Fully optional** - standard plugin usage works without this

### Notes
- Setup is opt-in only; flow-next continues to work via plugin as before
- Re-run `/flow-next:setup` after plugin updates to refresh local scripts

## [flow-next 0.3.7] - 2026-01-09

### Ralph: Autonomous Coding with Multi-Model Review Gates

This release introduces **Ralph**, a production-ready autonomous coding loop that goes beyond simple "code until tests pass" agents. Ralph implements **multi-model review gates** using [RepoPrompt](https://repoprompt.com/?atp=KJbuL4) to send your plans and implementations to a different AI model for review.

**Why Ralph is different:**

- **Two-model review**: Your code is reviewed by a separate model (we recommend GPT-5.2 High), catching blind spots that self-review misses
- **Review loops until SHIP**: No "LGTM with nits" that get ignored—reviews block progress until the reviewer returns `<verdict>SHIP</verdict>`
- **Receipt-based gating**: Every review must produce a receipt proving it ran. No receipt = no progress. This prevents the agent from skipping steps
- **Guard hooks**: Deterministic enforcement of workflow rules—the agent can't drift from the prescribed flow

**Getting started:**

```bash
/flow-next:ralph-init    # Set up Ralph in your repo
scripts/ralph/ralph.sh   # Run the autonomous loop
```

See the [Ralph documentation](plugins/flow-next/docs/ralph.md) for the full guide.

### Technical Details

**Guard hooks** (only active when `FLOW_RALPH=1`):
- Block impl receipts unless `flowctl done` was called
- Block receipts missing required `id` field
- Warn on informal approvals without verdict tags
- Zero impact for non-Ralph users

**Autonomous mode system prompt** ensures the agent follows instructions precisely when running unattended.

---

### Internal changes (0.2.1 → 0.3.7)

<details>
<summary>Click to expand development history</summary>

#### 0.2.8 - Unreleased
- Enforce numeric RepoPrompt window selection + validation before builder
- Clarify builder requires `--window` + `--summary`; no names/ids
- Update plan/impl review rp-cli references + workflow guidance

#### 0.2.7 - Unreleased
- Add epic `branch_name` field + `flowctl epic set-branch` command
- Ralph now writes run-local `progress.txt` per iteration
- Plan guidance enforces one-iteration task sizing and sets epic branch_name
- Work flow requires tests/Quick commands green before impl review

#### 0.2.6 - Unreleased
- Add flowctl rp wrappers; remove direct rp-cli usage in review workflows
- Add skill-scoped Ralph hooks (guard + receipt + optional verbose log)
- Update review skills/commands/docs to use wrappers + Claude Code 2.1.0+ note

#### 0.2.5 - Unreleased
- Align rp-cli refs + option text to `call chat_send` (no rp-cli chat)
- Ralph work prompt no longer double-calls impl review; receipts always any verdict
- Window switch uses git root + explicit -w; add jq + tab rebind guidance
- Docs clarify receipt gating + Ralph mode bans rp-cli chat/codemap/slice

#### 0.2.4 - Unreleased
- Added Ralph-mode rule blocks to plan/impl review + work skills
- Ralph prompts now restate anti-drift rules
- Ralph sets `RALPH_MODE=1` for stricter skill behavior

#### 0.2.3 - Unreleased
- /flow-next:work now hard-requires flowctl done + task status check before commit
- Work workflow requires git add -A (no file lists) to include .flow + ralph artifacts
- Review skills now RETRY if rp-cli chat/codemap/slice are used (enforce call chat_send)
- Ralph forces retry if task status is not done after work iteration

#### 0.2.2 - Unreleased
- Plan/impl review skills now mandate receipt write when `REVIEW_RECEIPT_PATH` is set
- Plan-review guidance now pins correct flowctl command for status updates
- Ralph loop logs per-iteration status, mode, receipt checks
- Flow-next docs add Ralph deep dive and receipt notes

#### 0.2.1 - Unreleased
- Plan/impl review workflows now auto-select RepoPrompt window by repo root
- Review workflows write receipts only when `REVIEW_RECEIPT_PATH` is set
- `plan-review` and `impl-review` command stubs trimmed to route to skills

</details>

## [flow-next 0.2.0] - 2026-01-07

### Added
- **Autonomous mode flags**: All commands now accept flags to bypass interactive questions
  ```bash
  # Interactive (asks questions)
  /flow-next:plan Add caching
  /flow-next:work fn-1

  # Autonomous (flags)
  /flow-next:plan Add caching --research=grep --no-review
  /flow-next:work fn-1 --branch=current --no-review

  # Autonomous (natural language)
  /flow-next:plan Add caching, use context-scout, skip review
  /flow-next:work fn-1 current branch, no review
  ```
  - `/flow-next:plan`: `--research=rp|grep`, `--review=rp|export|none`, `--no-review`
  - `/flow-next:work`: `--branch=current|new|worktree`, `--review=rp|export|none`, `--no-review`
  - `/flow-next:plan-review`: `--mode=rp|export`
  - `/flow-next:impl-review`: `--mode=rp|export`
- Natural language parsing also works ("use context-scout", "skip review", "current branch")
- First step toward fully autonomous Flow-Next operation

### Fixed
- Homepage URL now points to `/apps/flow-next` instead of `/apps/flow`

## [0.8.2] - 2026-01-06

### Changed
- **Re-review messages now require detailed fix explanations**
  - Template includes: what was wrong → what changed → why that approach
  - Plan reviews: section changes summary, trade-offs acknowledged
  - Impl reviews: file-by-file changes summary, architectural decisions
  - Helps reviewer understand HOW fixes were made, not just "trust me"
- **Fixed linebreak escaping in re-review messages**
  - Use raw `call chat_send` with JSON for multi-line messages
  - Bash single quotes don't interpret `\n` - now documented
- Added "Why detailed re-review messages?" explanation to both workflows

## [0.8.1] - 2026-01-06

### Changed
- **RepoPrompt v1.5.62+ now required** for review features
  - New `-t` flag for direct tab targeting (cleaner than `workspace tab` chaining)
  - Progress notifications during builder/chat execution
  - Updated all rp-cli references and examples
- **Re-review loop clarified**: Skip builder on re-reviews—discovery is done
  - Chat already has full context from initial review
  - Just augment selection with any files touched during fixes
  - Continue existing chat, don't start fresh
- Added "Why skip builder on re-reviews?" explanation to both workflows
- Downgrade path: `flow@0.8.0` for users on older RepoPrompt versions

## [0.8.0] - 2026-01-05

### Changed
- **Review workflows now use "Context Over Convenience" approach**
  - Builder prompt simplified to intent only (e.g., "Review implementation of OAuth on current branch")
  - No longer stuffs builder with file lists or module details—let Builder discover context
  - Builder's handoff prompt becomes foundation; review criteria added on top (not replaced)
  - Explicit step to capture and reuse Builder's handoff prompt via `prompt get`
- **New philosophy section** at top of both workflow files
  - Introduces "RepoPrompt's Context Builder" once, then refers to it as "Builder"
- **New anti-patterns**: "Stuffing builder prompt", "Ignoring builder's handoff prompt"
- Phase 1 now composes concise summary (flexible: 1-2 sentences for simple, paragraph for complex epics)
- Phase 2/3 renamed to "Context Discovery & Selection" with clearer 4-step process:
  1. Run builder with intent
  2. Capture handoff prompt
  3. Review and augment selection
  4. Verify final selection
- Builder wait warning now explicitly says "do NOT send another builder command"
- Review criteria condensed (same content, fewer tokens)

### Why This Change
Builder is AI-powered—its strength is discovering related patterns, architectural context, and dependencies the reviewer needs. We already know the changed files/plan file; Builder's job is finding surrounding context. Previous approach was too prescriptive.

## [0.7.7] - 2026-01-04

### Changed
- Renamed `interview` skill to `flow-interview` (pattern consistency)
- Extracted question categories to `questions.md` (like `flow-work` has `phases.md`)
- SKILL.md now references `questions.md` for interview guidelines

## [0.7.6] - 2026-01-03

### Fixed
- Stronger AskUserQuestion requirement with anti-pattern example

## [0.7.5] - 2026-01-03

### Fixed
- Interview skill now explicitly requires AskUserQuestion tool (was outputting questions as text)

## [0.7.4] - 2026-01-03

### Added
- `/flow:interview` command + `interview` skill
  - Deep interview about a spec/bead (40+ questions for complex features)
  - Accepts beads ID or file path
  - Writes refined spec back to source
  - Optional step before `/flow:plan` for thorough requirements gathering

## [0.7.3] - 2026-01-02

### Added
- Codex CLI install script (`scripts/install-codex.sh`)
  - Copies skills and prompts to `~/.codex/`
  - Note: subagents won't run (Codex limitation), core flow still works

## [0.7.2] - 2026-01-02

### Changed
- Review skills now check conversation context before asking mode question
  - If mode already chosen in `/flow:plan` or `/flow:work` setup → use it, don't ask again
  - Only asks when invoked directly without prior context

## [0.7.1] - 2026-01-02

### Changed
- Clarified review mode question: both modes use RepoPrompt for context building, difference is where review happens

## [0.7.0] - 2026-01-01

### Added
- **Export for external review**: Review skills now offer export mode for ChatGPT Pro, Claude web, etc.
  - `/flow:plan` and `/flow:work` setup questions now have 3 review options:
    - `a) Yes, RepoPrompt chat` (default)
    - `b) Yes, export for external LLM`
    - `c) No`
  - Direct `/flow:impl-review` and `/flow:plan-review` ask upfront which mode to use
  - Export mode: same context building, exports to `~/Desktop/` and opens file
  - Uses new RepoPrompt 1.5.61 `prompt export` command

### Changed
- Updated rp-cli references for RepoPrompt 1.5.61:
  - `workspace tabs` shorthand (replaces verbose `call manage_workspaces`)
  - `workspace tab "name"` shorthand for tab selection
  - `prompt export /path.md` for full context export
  - Workflow shorthand flags (`--export-prompt`, `--export-context`)
  - Note: chats are now bound to compose tabs

## [0.6.5] - 2025-12-31

### Fixed
- Remove "Top 3 changes" from review output format
  - Agents were only fixing top 3 instead of ALL Critical/Major/Minor issues
  - Added explicit instruction: list ALL issues, agent will fix all of them
  - Applies to both plan-review and impl-review workflows

## [0.6.4] - 2025-12-31

### Fixed
- Clarified valid reasons to skip a fix in reviews:
  - Reviewer lacked context (missed constraint/related code)
  - Reviewer misunderstood requirement/intent
  - Fix would break something else
  - Conflicts with established patterns
  - Must explain reasoning in re-review message

## [0.6.3] - 2025-12-30

### Fixed
- Strengthened fix-and-re-review loop to require fixing Minor issues
  - Explicit: Critical/Major/Minor MUST be fixed, only Nitpick is optional
  - Added anti-pattern: "Skipping Minor issues"
  - Updated both plan-review and impl-review workflows

## [0.6.2] - 2025-12-30

### Fixed
- Clarified JSON escaping for chat_send in review workflows
  - Message must use `\n` for newlines, not literal line breaks
  - Removed broken heredoc pattern that caused JSON parse errors
  - Added note to keep message concise (chat sees selected files)

## [0.6.1] - 2025-12-30

### Fixed
- Added fix-and-re-review loop to plan/impl review workflows
  - Agents were documenting issues instead of fixing them during re-review
  - Now explicitly instructs to implement all fixes directly
  - Escape hatch for genuine disagreements preserved
  - Updated anti-patterns to flag "documenting instead of fixing"

## [0.6.1] - 2025-12-30

### Added
- Tab isolation docs for parallel agents using rp-cli (#3)
  - `builder` auto-creates isolated compose tabs
  - Chain commands to maintain tab context: `builder "..." && select add && chat`
  - Rebind by tab name for separate invocations
  - Updated: flow-plan-review, flow-impl-review workflows
  - Updated: context-scout agent, rp-explorer skill

## [0.5.16] - 2025-12-29

### Fixed
- Fixed new chat creation in reviews (shorthand `--new-chat` is broken in rp-cli)
  - Initial review now uses `call chat_send {"new_chat": true, ...}` (works)
  - Re-review uses shorthand `chat "..." --mode chat` (continues existing)
  - Updated both workflow.md and rp-cli-reference.md files

## [0.5.15] - 2025-12-29

### Fixed
- Made review-fix-review loop fully automated (no human gates)
  - flow-work Phase 7: explicit "do NOT ask for confirmation"
  - flow-plan Step 5: same fix
  - Removed "ask before closing final tasks" ambiguity
  - Reviews now auto-fix and re-run until "Ship"

## [0.5.14] - 2025-12-29

### Fixed
- Removed redundant "Go ahead to start?" confirmation in flow-work
  - User already consented via setup questions
  - Only ask if something is actually unclear or blocking

## [0.5.13] - 2025-12-29

### Changed
- Replaced AskUserQuestion with text-based questions in flow-plan and flow-work
  - Better for voice dictation users
  - Supports terse replies ("1a 2b") and natural language rambling
  - All questions visible at once
  - Explicit "do NOT use AskUserQuestion tool" instruction

## [0.5.12] - 2025-12-29

### Added
- Issue quality guidelines in review prompts (inspired by OpenAI Codex)
  - impl-review: only flag issues **introduced by this change**
  - Both: cite **actual affected code** (no speculation)
  - Both: specify **trigger conditions** (inputs, edge cases)

## [0.5.11] - 2025-12-29

### Fixed
- Restructured chat command examples so `--new-chat` flags aren't buried

## [0.6.1] - 2025-12-29

### Added
- Chat session targeting for re-reviews
  - `chats list` → get chat IDs and names
  - `--chat-id <id>` → continue specific chat

## [0.5.9] - 2025-12-29

### Fixed
- Clarified new-chat behavior in review workflows

## [0.5.8] - 2025-12-29

### Fixed
- Added prominent "CRITICAL" instruction for chat management in review workflows

## [0.5.7] - 2025-12-29

### Changed
- Merged redundant verify phases in review workflows
  - `flow-plan-review`: Phase 2+3 → "Build Context & Verify Selection"
  - `flow-impl-review`: Phase 3+4 → "Build Context & Verify Selection"
  - Agent now adds all supporting docs found in earlier phases after builder runs
  - Eliminates duplicate "check for PRD" instructions

## [0.5.6] - 2025-12-29

### Changed
- Improved skill descriptions to explicitly mention Beads issue ID support
  - `flow-plan`: now triggers on issue IDs (e.g., bd-123, gno-45)
  - `flow-work`: now triggers on epic/issue IDs for execution

## [0.5.4] - 2025-12-28

### Added
- **New skill: `rp-explorer`** - Token-efficient codebase exploration via rp-cli
  - Deliberate activation: triggers on "use rp", "use repoprompt", explicit requests
  - Includes full rp-cli command reference (progressive disclosure)

### Changed
- `/flow:plan` now asks two setup questions when rp-cli detected:
  - Q1: Research approach (context-scout vs repo-scout)
  - Q2: Auto-review preference
- Updated README with comparison table and SETUP phase diagram

## [0.5.3] - 2025-12-28

### Changed
- Documented cross-model review benefit (GPT-5.2 High, o3 for validation)

## [0.5.2] - 2025-12-28

### Added
- **New agent: `context-scout`** - Token-efficient codebase exploration using RepoPrompt's rp-cli
  - Uses `structure` for code signatures (10x fewer tokens than full files)
  - Uses `builder` for AI-powered file discovery
  - Comprehensive workflow: window setup → explore → summarize

### Changed
- **Improved all 6 agents** with proper configuration and detailed prompts:
  - Added `tools` field - each agent now has only the tools it needs
  - Added `model` field - scouts use `haiku` (fast), analysts use `sonnet` (reasoning)
  - Detailed search/analysis methodologies
  - Structured output formats for consistent, actionable results
  - Clear rules on what to focus on and what to skip

### Technical
- All 6 agents use opus model with full research toolkit: Read/Grep/Glob/Bash/WebSearch/WebFetch
- Explicitly excludes Edit/Write (read-only), Task (no sub-agents), TodoWrite/AskUserQuestion (parent manages)

## [0.5.0] - 2025-12-28

### Added
- **Auto-offer review**: Both `flow-plan` and `flow-work` now detect if rp-cli is installed and offer Carmack-level review
  - `flow-plan`: After writing plan, offers `/flow:plan-review` before next steps
  - `flow-work`: After shipping, offers `/flow:impl-review` with fix-and-iterate loop
- Eliminates need for manual chaining like "then review with /flow:impl-review"

### Changed
- `flow-work`: Branch setup question now in SKILL.md (first thing shown, cannot be skipped)
- Explicit examples of chained instructions in skill inputs

### Fixed
- Review commands now have explicit wait instructions for rp-cli chat responses (1-5+ min timeout)

## [0.4.0] - 2025-12-27

### Added
- **Beads integration**: Optional Beads (`bd`) support for flow skills
  - `flow-plan`: Can create Beads epics/tasks instead of markdown plans
  - `flow-work`: Can accept Beads IDs/titles, track via `bd ready`/`bd update`/`bd close`
  - `flow-plan-review`: Can accept Beads IDs/titles as input
  - `flow-impl-review`: Looks for Beads context during code review
- Graceful fallback to markdown/TodoWrite when `bd` unavailable
- Context recovery guidance per Anthropic's long-running agent best practices

### Technical
- Agent-first design: no rigid detection gates, uses judgment based on context
- Validated against bd v0.38.0
- CLI behavior documented in plan (ID formats, parent linking, scoped ready)

## [0.3.7] - 2024-12-27

### Added
- `/flow:plan-review` command: Carmack-level plan review via rp-cli context builder + chat
- `/flow:impl-review` command: Carmack-level implementation review of current branch changes
- `flow-plan-review` skill: progressive disclosure with workflow.md + rp-cli-reference.md
- `flow-impl-review` skill: progressive disclosure with workflow.md + rp-cli-reference.md

### Technical
- Both review skills use rp-cli for context building and chat-based review
- Shared rp-cli-reference.md for CLI command reference
- Commands are thin wrappers (~15 lines) invoking skills

## [0.2.3] - 2024-12-27

### Fixed
- Use "subagent" terminology consistently (official Claude Code term)

## [0.2.2] - 2024-12-27

### Fixed
- Use namespaced agent names (`flow:repo-scout`, `flow:practice-scout`, etc.) in skill reference files
- Make workflow file references directive ("Read and follow" instead of passive links)

## [0.2.1] - 2024-12-27

### Changed
- **Progressive disclosure for Skills**: SKILL.md files now contain only overview + links to reference files
- `flow-plan`: 117 → 30 lines in SKILL.md, detailed steps moved to `steps.md` and `examples.md`
- `flow-work`: 95 → 27 lines in SKILL.md, phases moved to `phases.md`
- Context usage reduced: ~100-150 tokens per skill at startup instead of 400-700

## [0.2.0] - 2024-12-27

### Added
- `flow-plan` skill: planning workflow logic extracted from command
- `flow-work` skill: execution workflow logic extracted from command

### Changed
- **Commands → Skills refactor**: `/flow:plan` and `/flow:work` are now thin wrappers (~15 lines each) that invoke Skills
- Skills enable auto-triggering based on description matching (e.g., "plan out adding OAuth" triggers `flow-plan`)
- Updated manifests: 1 skill → 3 skills

### Technical
- Commands reduced from ~2.1k and ~2.4k tokens to ~36 and ~38 tokens
- Full logic loads on-demand when skill is triggered

## [0.1.1] - 2024-12-26

### Changed
- Moved commands to `commands/flow/` subdirectory for prefixed naming (`/flow:plan`, `/flow:work`)
- Renamed commands for clarity
- Updated argument hints

### Added
- Semver bump script for version management

## [0.1.0] - 2024-12-26

### Added
- Initial release of Flow plugin
- `/flow:plan` command: research + produce `plans/<slug>.md`
- `/flow:work` command: execute a plan end-to-end
- 5 agents: `repo-scout`, `practice-scout`, `docs-scout`, `flow-gap-analyst`, `quality-auditor`
- `worktree-kit` skill for safe parallel git workspaces
- Issue creation integration (GitHub, Linear, Beads)
- Marketplace structure with plugin manifest
