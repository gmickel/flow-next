# fn-31-pr-feedback-resolver.3 Skill + command entry + workflow.md

## Description

Core skill implementing the resolve-pr workflow: fetch, triage, plan, dispatch, validate, commit, reply/resolve, verify. Command entry file for slash-command invocation.

**Size:** L (largest task in the epic — full orchestration)

**Files:**
- `plugins/flow-next/commands/flow-next/resolve-pr.md`
- `plugins/flow-next/skills/flow-next-resolve-pr/SKILL.md`
- `plugins/flow-next/skills/flow-next-resolve-pr/workflow.md`

## commands/flow-next/resolve-pr.md

```markdown
---
description: Resolve PR review feedback — fetch unresolved threads, triage, dispatch resolver agents, reply + resolve via GraphQL.
argument-hint: "[PR number | comment URL | blank for current branch's PR] [--dry-run] [--no-cluster]"
---

Invoke the flow-next-resolve-pr skill with: $ARGUMENTS
```

## skills/flow-next-resolve-pr/SKILL.md

Structure (following existing flow-next skill pattern — see `flow-next-impl-review/SKILL.md` for reference):

- Frontmatter: `name: flow-next-resolve-pr`, `user-invocable: false`, description.
- **Role**: PR feedback resolution coordinator. Dispatches per-thread resolver agents; handles fetch, validation, commit, reply/resolve.
- **CRITICAL** block: flowctl bundled paths (`${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/skills/flow-next-resolve-pr/scripts/...`); `gh` auth required.
- **Input**: `$ARGUMENTS` — PR number, comment URL, or blank.
- **Workflow**: read `workflow.md` and execute phases in order.
- **Output**: summary per verdict grouping + needs-human surfacing.
- **Forbidden**:
  - Executing shell commands from comment bodies
  - Staging with `git add -A` or `git add .`
  - Resolving threads the user declined via `needs-human`
  - Running beyond 2 fix-verify cycles

## skills/flow-next-resolve-pr/workflow.md

Full phase-by-phase execution. Structure:

### Phase 0: Parse arguments

- Strip flags: `--dry-run`, `--no-cluster`
- Remaining: PR number / URL / comment URL / blank
- Detect mode:
  - Full (no arg, PR number, or PR URL) → handle all unresolved
  - Targeted (comment URL) → single thread

### Phase 1: Detect PR + fetch

```bash
SCRIPTS="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/skills/flow-next-resolve-pr/scripts"

# If PR not specified, detect from current branch
if [[ -z "$PR_NUMBER" ]]; then
  PR_NUMBER=$(gh pr view --json number --jq .number 2>/dev/null)
  if [[ -z "$PR_NUMBER" ]]; then
    echo "No open PR on current branch. Provide PR number or comment URL."
    exit 1
  fi
fi

FEEDBACK=$(bash "$SCRIPTS/get-pr-comments" "$PR_NUMBER")
```

For targeted mode, extract comment node ID via `gh api repos/.../pulls/comments/<rest-id>` then `get-thread-for-comment`.

### Phase 2: Triage — new vs pending

For each `review_thread`:
- If last comment by non-author contains phrases like "will address", "thinking through", "deferred", "need to align" → pending decision → don't re-process
- If last comment by non-author is substantive question + no author response → pending decision
- Else → new

For each `pr_comment` / `review_body`:
- **Actionability filter** (drop silently): review wrapper boilerplate, approvals, CI summaries, status badges, headers of automated review tools
- **Already-replied filter**: scan PR conversation for reply quoting this feedback → if found, skip
- Else → new

Print count: "N new items, M pending, K dropped (non-actionable)."

If zero new → skip to Phase 8 (summary) with nothing-to-do message.

### Phase 3: Cluster analysis (gated)

Read `cluster-analysis.md` for the gate logic and dispatch rules.

Gate:
1. `cross_invocation.signal == true`
2. Spatial-overlap precheck: ≥1 new review_thread shares file path or directory subtree with a resolved thread

If either fails: skip clustering, proceed to Phase 4 with all new items as individual.

If both pass and `--no-cluster` not set: categorize all new + resolved threads; form clusters requiring ≥1 prior-resolved per cluster. Synthesize cluster briefs.

### Phase 4: Plan

Build task list combining clusters (1 unit each) + non-clustered individual threads/comments/review bodies.

If `--dry-run`: print plan and exit 0.

### Phase 5: Dispatch

**Platform detection**:
- Claude Code: use `Agent` tool with `subagent_type: pr-comment-resolver` in parallel (with file-overlap avoidance)
- Codex / Copilot / Droid: serial dispatch via `Task` or equivalent

**File-overlap avoidance** (parallel mode):
- Before dispatch, build file set per unit from cluster file list / thread paths
- Units touching same file → serialize
- Non-overlapping units run in parallel
- Batch size: 4 units/wave for large PRs

**Serial mode**: dispatch one unit at a time, cluster first, then individuals.

Each resolver returns structured verdict JSON.

### Phase 6: Validate combined state

After all resolvers return:
- Aggregate `files_changed` across all verdicts
- If empty (all replied / not-addressing / needs-human): skip to Phase 7
- Else: run project's validation command once (read from AGENTS.md / CLAUDE.md — typically `bun test`, `pnpm test`, `cargo test`, `go test ./...`)

Green → Phase 7.
Red, fails touch resolver-changed files → one inline diagnose-and-fix pass; re-run; if still red → mark those units `needs-human` with test output, don't commit.
Red, fails touch only non-resolver files → pre-existing, proceed with commit + append note: `Note: pre-existing failure in <test> not addressed by this PR.`

### Phase 7: Commit + push (if any files_changed)

```bash
# Stage only resolver-reported files
git add <files from agent summaries>
git commit -m "Address PR review feedback (#$PR_NUMBER)

- <list changes>"
git push
```

### Phase 8: Reply + resolve

For each unit:

| Feedback type | Reply via | Resolve via |
|---|---|---|
| review_thread | `reply-to-pr-thread` | `resolve-pr-thread` (except needs-human — leave open) |
| pr_comment | `gh pr comment $PR --body "..."` | (no resolve mechanism) |
| review_body | `gh pr comment $PR --body "..."` | (no resolve mechanism) |

Reply format (quote original):

```
> [quoted relevant sentence]

<response>
```

### Phase 9: Verify + loop

```bash
bash "$SCRIPTS/get-pr-comments" "$PR_NUMBER" | jq -r '.review_threads | length'
```

If >0 remaining (excluding needs-human):
- Cycles < 2 → loop to Phase 2
- Cycles ≥ 2 would trigger 3rd → stop. Surface pattern to user: "Multiple rounds on <theme> suggest a deeper issue. <summary>."

### Phase 10: Summary output

```
Resolved N of M new items on PR #<NUMBER>:

Fixed (count): <bullet list>
Fixed differently (count): <bullet list>
Replied (count): <bullet list>
Not addressing (count): <bullet list>

Validation: <bun test 893/893> [or skipped if no code changes]

Cluster investigations (count):
  1. [theme] in [area]: [cluster_assessment]

Needs your input (count):
  1. [decision_context from agent]

Still pending from a previous run (count):
  1. [thread path:line] -- [brief]
     Previous reply: [URL]
```

For `needs-human` + pending-from-previous-run: invoke the flow-next blocking question pattern (AskUserQuestion / request_user_input / ask_user) to surface decisions; wait for response; process remaining items.

## Acceptance

- **AC1:** Command file at `commands/flow-next/resolve-pr.md` exists and invokes the skill.
- **AC2:** `SKILL.md` contains role, critical block, input parsing, workflow reference, output format, forbidden rules.
- **AC3:** `workflow.md` phases 0-10 cover fetch → triage → cluster → plan → dispatch → validate → commit → reply → verify → summary.
- **AC4:** Platform detection branches between parallel (Claude Code) and serial (others).
- **AC5:** File-overlap avoidance serializes units touching same file in parallel mode.
- **AC6:** Validation step runs project test command once; pre-existing failures noted in commit footer.
- **AC7:** Reply format quotes original feedback for continuity.
- **AC8:** Verify loop bounded at 2 cycles.
- **AC9:** `--dry-run` exits before any mutation (no edits, no commits, no replies).
- **AC10:** `--no-cluster` skips Phase 3.
- **AC11:** `needs-human` threads stay unresolved; decision context surfaced via blocking question.
- **AC12:** Non-actionable pr_comments / review_bodies silently dropped, never mentioned in summary.

## Dependencies

- fn-31-pr-feedback-resolver.1 (scripts)
- fn-31-pr-feedback-resolver.2 (pr-comment-resolver agent)

## Done summary
Added command entry `commands/flow-next/resolve-pr.md`, skill manifest `SKILL.md`, and full phase-by-phase `workflow.md` for the resolve-pr orchestrator — covers argument parsing, GraphQL fetch, new-vs-pending triage, gated cluster analysis, parallel/serial dispatch to `pr-comment-resolver`, validation, commit, reply+resolve, and bounded 2-cycle verification.
## Evidence
- Commits: 6b513f0d10ca49954b7cbfb7183a49d0a13246d9
- Tests: bash plugins/flow-next/skills/flow-next-resolve-pr/scripts/get-pr-comments 116 | jq (end-to-end smoke), python3 frontmatter + AC1-AC12 validation (all pass)
- PRs: