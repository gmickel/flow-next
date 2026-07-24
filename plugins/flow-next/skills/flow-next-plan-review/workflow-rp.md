# Plan Review Workflow — RepoPrompt Backend

Use only when `BACKEND="rp"` after [workflow.md](workflow.md).

## Critical rules

1. The coordinator does not review the plan.
2. Use `setup-review` exactly once; it atomically selects the window and runs
   Builder.
3. Wait for the actual RepoPrompt response.
4. Never pass `--json` to `chat-send`.
5. Only the first dispatch uses `--new-chat`; all re-reviews stay in that chat.
6. A response file enters context exactly once through a file read.

## Phase 1: Current Plan and Checkpoint

Read the current persisted spec and task specs before Builder. Compose a short
`REVIEW_SUMMARY` from the current plan; user edits override generated history.

```bash
$FLOWCTL show "$SPEC_ID" --json
$FLOWCTL cat "$SPEC_ID"
$FLOWCTL checkpoint save --spec "$SPEC_ID" --json
```

## Phase 2: Atomic Setup and Selection

```bash
eval "$($FLOWCTL rp setup-review --repo-root "$REPO_ROOT" --summary "$REVIEW_SUMMARY" --create)"
if [[ -z "${W:-}" || -z "${T:-}" ]]; then
  echo "<promise>RETRY</promise>"
  exit 0
fi
```

If setup fails, retry terminal and stop. Never run setup twice.

Inspect Builder selection, then add the current spec and every current task spec:

```bash
$FLOWCTL rp select-get --window "$W" --tab "$T"
$FLOWCTL rp select-add --window "$W" --tab "$T" ".flow/specs/${SPEC_ID}.md"
for task_spec in .flow/tasks/${SPEC_ID}.*.md; do
  [[ -f "$task_spec" ]] && $FLOWCTL rp select-add --window "$W" --tab "$T" "$task_spec"
done
[[ -f docs/prd.md ]] && $FLOWCTL rp select-add --window "$W" --tab "$T" docs/prd.md
```

## Phase 3: Build and Send Review Prompt

Use literal unique prompt/response paths in every block that references them.
Variables do not survive tool calls. Compose by redirection; never retype
multi-line command output.

```bash
PROMPT_FILE="${TMPDIR:-/tmp}/flow-plan-review-prompt-<spec-id>-<suffix>.md"
$FLOWCTL rp prompt-get --window "$W" --tab "$T" > "$PROMPT_FILE"
cat >> "$PROMPT_FILE" <<'EOF'

---

## IMPORTANT: File Contents
RepoPrompt includes the actual source code of selected files in a `<file_contents>` XML section at the end of this message. You MUST:
1. Locate the `<file_contents>` section
2. Read and analyze the actual source code within it
3. Base your review on the code, not summaries or descriptions

If you cannot find `<file_contents>`, ask for the files to be re-attached before proceeding.

## Plan Under Review
EOF
$FLOWCTL show "$SPEC_ID" >> "$PROMPT_FILE"
cat >> "$PROMPT_FILE" <<'EOF'

## Review Focus
[USER'S FOCUS AREAS]

## Review Scope

You are reviewing:
1. **Spec** - The high-level plan
2. **Task specs** - Individual task breakdowns

**CRITICAL**: Check for consistency between spec and tasks. Flag if:
- Task specs contradict or miss spec requirements
- Task acceptance criteria don't align with spec acceptance criteria
- Task approaches would need to change based on spec design decisions
- Spec mentions states/enums/types that tasks don't account for

## Review Criteria

Conduct a John Carmack-level review:

1. **Completeness** - All requirements covered? Missing edge cases?
2. **Feasibility** - Technically sound? Dependencies clear?
3. **Parallelizability** - Do independent tasks touch disjoint files? Flag overlapping file scopes that will cause merge conflicts.
4. **Clarity** - Specs unambiguous? Acceptance criteria testable?
5. **Architecture** - Right abstractions? Clean boundaries?
6. **Risks** - Blockers identified? Security gaps? Mitigation?
7. **Scope** - Right-sized? Over/under-engineering?
8. **Task sizing** - M tasks preferred. Flag over-splitting: 7+ tasks? Sequential S tasks that should be combined?
9. **Testability** - How will we verify this works?
10. **Consistency** - Do task specs align with spec?
11. **Vocabulary** - [Include ONLY when `flowctl glossary list --json` reports `total_terms > 0`: "Canonical vocabulary lives in GLOSSARY.md — flag specs/tasks that contradict defined terms." Omit this line otherwise.]

**Also explicitly verify (commonly-missed):** a stated **test strategy**; **observability** (logging/metrics/progress) for any async/batch work; each task **sized for one iteration and correctly ordered** by dependency; and stated **non-functional requirements** (performance, security, privacy).

## Protected artifacts
NEVER recommend deleting / gitignoring / removing these committed pipeline paths (flag bad CONTENT inside them, never their existence): `.flow/*`, `.flow/bin/*`, `.flow/memory/*`, `.flow/specs/*.md`, `.flow/tasks/*.md`, `docs/plans/*`, `docs/solutions/*`, `scripts/ralph/*`. Discard any such finding during synthesis; emit a `Protected-path filter:` count when any dropped.

## Output Format

For each issue:
- **Severity**: Critical / Major / Minor / Nitpick
- **Location**: Which task or section (e.g., "fn-1.3 Description" or "Spec Acceptance #2")
- **Problem**: What's wrong
- **Suggestion**: How to fix

After the issues list, emit a `Protected-path filter:` line tallying findings dropped by the protected-path filter (omit when nothing was dropped).

**REQUIRED**: You MUST end your response with exactly one verdict tag. This is mandatory:
`<verdict>SHIP</verdict>` or `<verdict>NEEDS_WORK</verdict>` or `<verdict>MAJOR_RETHINK</verdict>`

Do NOT skip this tag. The automation depends on it.
EOF
```

The four-item quality checklist above is byte-equivalent to B1. Do not broaden
it; the prior broad checklist regressed detection.

Before every dispatch:

```bash
$FLOWCTL review-rounds increment "$SPEC_ID" --kind plan --json
```

Exit 4 / `ESCALATE:` means stop without dispatch. Otherwise run one blocking
foreground call:

```bash
PROMPT_FILE="${TMPDIR:-/tmp}/flow-plan-review-prompt-<spec-id>-<suffix>.md"
RESPONSE_FILE="${TMPDIR:-/tmp}/flow-plan-review-response-<spec-id>-<suffix>.md"
$FLOWCTL rp chat-send --window "$W" --tab "$T" --message-file "$PROMPT_FILE" --new-chat --chat-name "Plan Review: <SPEC_ID>" > "$RESPONSE_FILE"
RP_EXIT=$?
VERDICT="$(tr -d '\r' < "$RESPONSE_FILE" \
  | grep -oE '<verdict>(SHIP|NEEDS_WORK|MAJOR_RETHINK)</verdict>' \
  | tail -n 1 | sed -E 's#</?verdict>##g')"
$FLOWCTL review-rounds record "$SPEC_ID" --kind plan --review-type plan \
  --backend rp --output-file "$RESPONSE_FILE" --exit-code "$RP_EXIT" --json
```

If no verdict exists, the `record` call refunds the reservation and durably
records the transport failure; output `<promise>RETRY</promise>` and stop.
After more than `${MAX_REVIEW_TRANSPORT_FAILURES:-2}` consecutive failures it
exits 5 / `TRANSPORT_UNHEALTHY`: stop for backend repair, never reset the review
counter. Read the response file once for findings; do not echo/cat it.

## Phase 4: Receipt and Status

When `REVIEW_RECEIPT_PATH` is set, write the existing plan-review receipt:

```json
{"type":"plan_review","id":"<spec-id>","mode":"rp","verdict":"<verdict>","timestamp":"<ISO-8601>"}
```

Write latest status after every verdict:

```bash
$FLOWCTL spec set-plan-review-status "$SPEC_ID" --status ship --json
$FLOWCTL review-rounds reset "$SPEC_ID" --kind plan --json
# or
$FLOWCTL spec set-plan-review-status "$SPEC_ID" --status needs_work --json
```

Return the verdict to SKILL.md's shared fix loop.

## Re-review

Only after the current spec and affected task specs are updated:

1. Do not re-add already selected files; RepoPrompt auto-refreshes them.
2. Add only genuinely new files.
3. Increment the deterministic round counter before dispatch.
4. Send `Issues addressed. Please re-review.` in the SAME chat, without
   `--new-chat`; require the same verdict grammar.
5. Overwrite the same response file, parse the verdict, call the same
   `review-rounds record ... --review-type plan` command with the captured
   `rp chat-send` exit code, then read the response once and update
   receipt/status.

## Anti-patterns

- Direct Builder calls, duplicate setup, or hard-coded window ids
- Re-review without `spec set-plan`
- Re-adding already selected files
- Summarizing fixes instead of letting refreshed files speak
- `--new-chat` after the first review
