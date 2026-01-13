# Changelog

All notable changes to the gmickel-claude-marketplace.

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
