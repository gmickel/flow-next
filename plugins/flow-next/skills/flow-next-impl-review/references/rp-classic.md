# RepoPrompt Classic-only phases (selection + prompt build)

Read this ONLY when `RP_MODE` is not `ce` (Classic, or an unknown mode that
must be treated as Classic). CE returned the terminal review from the single
`setup-review` call and skips this build entirely.

This file is the Classic prompt build only — the Phase 2 `select-get` /
`select-add` selection loop stays inline in
[../workflow-rp.md](../workflow-rp.md) and runs before you get here.

**Contents**
- [Build combined prompt (file composition)](#build-combined-prompt-file-composition--no-content-re-typing)
- [Return to workflow-rp.md](#return)


### Build combined prompt (file composition — no content re-typing)

**Path-persistence rule:** bash vars do NOT survive across tool calls. Compose these literal unique paths in agent context and type them verbatim in EVERY block that references them (`mktemp` is reserved for paths created and consumed within a single bash block):

- Prompt file: `${TMPDIR:-/tmp}/flow-impl-review-prompt-<task-id-or-branch-slug>-<agent-chosen 4-char suffix>.md`
- Response file: `${TMPDIR:-/tmp}/flow-impl-review-response-<task-id-or-branch-slug>-<suffix>.md`

Build the prompt by deterministic composition — redirect command output into the file, never paste it into a heredoc. Only cheap **scalar** slots (branch, file list, commit summary, focus areas — values you already hold from Phase 1) are filled inline while typing the quoted heredocs below; multi-line command output is always appended via redirection.

```bash
SETUP_FILE="${TMPDIR:-/tmp}/flow-impl-review-setup-<task-id-or-branch-slug>-<suffix>.env"
source "$SETUP_FILE"
PROMPT_FILE="${TMPDIR:-/tmp}/flow-impl-review-prompt-<task-id-or-branch-slug>-<suffix>.md"   # literal path
if [[ "$RP_MODE" == "classic" ]]; then

# 1. Builder handoff — captured via redirection, never re-typed
$FLOWCTL rp prompt-get --window "$W" --tab "$T" > "$PROMPT_FILE"

# 2. Static header (quoted heredoc — no shell expansion; fill the scalar
#    [BRACKET] slots inline while typing this block)
cat >> "$PROMPT_FILE" << 'EOF'

---

## IMPORTANT: File Contents
RepoPrompt includes the actual source code of selected files in a `<file_contents>` XML section at the end of this message. You MUST:
1. Locate the `<file_contents>` section
2. Read and analyze the actual source code within it
3. Base your review on the code, not summaries or descriptions

If you cannot find `<file_contents>`, ask for the files to be re-attached before proceeding.

## Changes Under Review
Branch: [BRANCH_NAME]
Files: [LIST CHANGED FILES]
Commits: [COMMIT SUMMARY]

## Original Spec
EOF

# 3. Task spec — appended via redirection, never re-typed (skip when no task id)
[[ -n "$TASK_ID" ]] && $FLOWCTL show "$TASK_ID" >> "$PROMPT_FILE"

# 4. Review criteria (static, quoted heredoc; [USER'S FOCUS AREAS] is a scalar slot)
cat >> "$PROMPT_FILE" << 'EOF'

## Review Focus
[USER'S FOCUS AREAS]

## Review Criteria

Conduct a John Carmack-level review:

1. **Correctness** - Matches spec? Logic errors?
2. **Simplicity** - Simplest solution? Over-engineering?
3. **DRY** - Duplicated logic? Existing patterns?
4. **Architecture** - Data flow? Clear boundaries?
5. **Edge Cases** - Failure modes? Race conditions?
6. **Tests** - Adequate coverage? Testing behavior?
7. **Security** - Injection? Auth gaps?
8. **Vocabulary** - [Include ONLY when `flowctl glossary list --json` reports `total_terms > 0`: "Canonical vocabulary lives in GLOSSARY.md — flag changes that contradict defined terms." Omit this line otherwise.]

## Code-smell baseline (always-on, judgement calls — repo standards override; skip what tooling enforces)
Beyond correctness, name any of these you spot and quote the hunk (each a heuristic, never a hard violation):
Long Method · Large Class · Long Parameter List · Duplicated Code · Feature Envy (uses another object's data more than its own) · Data Clumps (same values always passed together — wants a type) · Primitive Obsession (bare primitives where a small type belongs) · Speculative Generality.

## Scenario Exploration (for changed code only)

Walk through these scenarios mentally for any new/modified code paths:

- [ ] Happy path - Normal operation with valid inputs
- [ ] Invalid inputs - Null, empty, malformed data
- [ ] Boundary conditions - Min/max values, empty collections
- [ ] Concurrent access - Race conditions, deadlocks
- [ ] Network issues - Timeouts, partial failures
- [ ] Resource exhaustion - Memory, disk, connections
- [ ] Security attacks - Injection, overflow, DoS vectors
- [ ] Data corruption - Partial writes, inconsistency
- [ ] Cascading failures - Downstream service issues

Only flag issues that apply to the **changed code** - not pre-existing patterns.

## Requirements coverage (only if the spec has R-IDs like `- **R1:** ...`)
If R-IDs are present, read the epic's `## Acceptance Criteria` (tolerate legacy `## Acceptance` / `## Acceptance criteria`) and emit:
| R-ID | Status | Evidence |
Status ∈ met / partial / not-addressed / deferred. After the table emit `Unaddressed R-IDs: [...]`. A non-deferred `not-addressed` R-ID forces NEEDS_WORK. If no R-IDs anywhere, skip this block entirely.

## Confidence (pick ONE anchor; no interpolation)
- **100** — definitive from code alone (mechanical: off-by-one, wrong type, swapped args).
- **75** — full path traced; a normal caller hits it; reproducible from the diff.
- **50** — depends on conditions visible but not confirmable here (e.g. can this be null? callers not in diff).
- **25** — needs runtime conditions with no direct evidence.
- **0** — speculative; don't file.
Suppression gate: drop findings below 75, EXCEPT P0 at 50+ (those survive). Emit a `Suppressed findings:` count when any dropped.

## Introduced vs pre-existing
Classify each finding: **introduced** (this diff caused or newly exposed it) or **pre_existing** (already on base, untouched — a finding on an unchanged line is pre_existing by default; confirm with `git blame`/base-file read when cheap).
Verdict gate: only `introduced` findings affect the verdict — a review whose survivors are all `pre_existing` ships. List pre-existing under `## Pre-existing issues (not blocking this verdict)` as `[sev, confidence N, introduced=false] file:line — summary`; never drop them. End with `Classification counts: N introduced, M pre_existing.`

## Protected artifacts
NEVER recommend deleting / gitignoring / removing these committed pipeline paths (flag bad CONTENT inside them, never their existence): `.flow/*`, `.flow/bin/*`, `.flow/memory/*`, `.flow/specs/*.md`, `.flow/tasks/*.md`, `docs/plans/*`, `docs/solutions/*`, `scripts/ralph/*`. Discard any such finding during synthesis; emit a `Protected-path filter:` count when any dropped.

## Output Format

For each surviving `introduced` finding:
- **Severity**: Critical / Major / Minor / Nitpick (P0 / P1 / P2 / P3 accepted)
- **Confidence**: 0 / 25 / 50 / 75 / 100 (one of the five discrete anchors)
- **Classification**: introduced
- **File:Line**: Exact location
- **Problem**: What's wrong
- **Suggestion**: How to fix

Then list each `pre_existing` finding under a separate `## Pre-existing issues (not blocking this verdict)` heading using the compact form `[severity, confidence N, introduced=false] file:line — summary`.

After the findings, add (only when applicable): the `## Requirements coverage` table + `Unaddressed R-IDs:` line, and the `Suppressed findings:` / `Classification counts:` / `Protected-path filter:` tally lines named above.

**REQUIRED**: You MUST end your response with exactly one verdict tag. This is mandatory:
`<verdict>SHIP</verdict>` (no blocking `introduced` findings, all R-IDs met or deferred) or `<verdict>NEEDS_WORK</verdict>` (introduced findings or unaddressed R-IDs to fix) or `<verdict>MAJOR_RETHINK</verdict>` or `<verdict>NEEDS_HUMAN</verdict>`

Do NOT skip this tag. The automation depends on it.
EOF
fi
```

## Return

Return to [../workflow-rp.md](../workflow-rp.md) § "Send to RepoPrompt" once the prompt file is built.
