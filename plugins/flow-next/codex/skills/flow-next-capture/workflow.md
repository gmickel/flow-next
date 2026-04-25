# /flow-next:capture workflow

Execute these phases in order. Each gates on the prior. Stop on user-blocking error — never plow through with bad state.

## Preamble

```bash
set -e
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
EPICS_DIR="$REPO_ROOT/.flow/epics"
SPECS_DIR="$REPO_ROOT/.flow/specs"
TODAY="$(date -u +%Y-%m-%d)"
```

`jq` and `python3` (or `python`) must be on PATH. Mode + flags come from the SKILL.md mode-detection block (`MODE` = `interactive` | `autofix`, plus `REWRITE_TARGET`, `FROM_COMPACTED_OK`, `COMMIT_YES`).

If `.flow/` does not exist, print `No .flow/ directory — run \`$FLOWCTL init\` first.` and exit cleanly. Capture has nothing to write into.

The Ralph-block (SKILL.md) runs before this preamble. Phase 0 starts after the Ralph-block and the preamble.

---

## Phase 0: Pre-flight (R5, R6, R8)

**Goal:** catch the three conditions that make capture unsafe BEFORE drafting a spec — duplicate epics, compacted conversation, idempotency conflict. Each has its own decision branch.

### 0.1 — Extract candidate keywords from conversation

Capture's input is the conversation, not `$ARGUMENTS`. Walk the visible user turns and pull:

- **Proper nouns** — capitalized terms used at least twice, excluding sentence-start common words.
- **File paths** — anything matching `[\w./_-]+\.(py|ts|tsx|js|md|json|sh|toml|yaml|yml)` or starting with `src/`, `plugins/`, `scripts/`, `.flow/`.
- **Domain-specific terms** — multi-word phrases the user repeated (e.g. "rate limiter", "OAuth callback", "review walkthrough").
- **Quoted phrases** — anything the user put in `"..."` or `\`...\`` while describing the feature.

Cap the candidate keyword list at the top **10** by frequency. These feed both 0.2 (epic title overlap) and 0.3 (memory search). Strip ordinary English connectors (`the`, `a`, `and`, `or`, `to`, `for`, `with`, `via`).

### 0.2 — Duplicate detection: epic title overlap

```bash
shopt -s nullglob
EPIC_FILES=( "$EPICS_DIR"/*.json )
shopt -u nullglob
```

For each epic JSON, read `id` + `title` + `status`. Skip closed epics (`status: closed`).

For each remaining epic, compute keyword overlap with the conversation keywords. Count **strong matches** — proper nouns / file paths / multi-word phrases that appear in both. Common single English words are not strong matches.

| Strong matches | Action |
|----------------|--------|
| 0-1 | No conflict; skip 0.4 idempotency unless an explicit prior-capture artifact id is detected |
| 2 | **Potential** duplicate — surface at Phase 0.5 with `proceed-anyway` recommended |
| 3+ | **Likely** duplicate — surface at Phase 0.5 with `extend` (or `supersede`) recommended |

Record the matched epic ids + their titles for the Phase 0.5 question.

### 0.3 — Duplicate detection: memory search cross-check

If `flowctl memory list --json` reports memory is initialized, run a cross-check on the top-3 conversation keywords:

```bash
"$FLOWCTL" memory search "<keyword-1>" --json --limit 5 2>/dev/null
"$FLOWCTL" memory search "<keyword-2>" --json --limit 5 2>/dev/null
"$FLOWCTL" memory search "<keyword-3>" --json --limit 5 2>/dev/null
```

Memory hits are advisory — they signal "you may have prior art on this topic" without blocking. Aggregate hit ids + titles for the Phase 4 read-back's "Related context" footnote (when ≥1 hits land). They do **not** trigger the duplicate-detection branch on their own; only epic-title overlap (0.2) does.

If memory is not initialized (`memory list` returns the `Memory not initialized` error), skip this step silently. Memory search is a quality-of-life signal; absence is not blocking.

### 0.4 — Compaction detection (R6)

Scan the visible conversation for any of:

- Literal `[compacted]` markers.
- Truncated tool-result patterns: `<...output too large to include>`, `(output truncated)`, `... (N more lines)`.
- System-summary blocks (e.g. "Earlier in the conversation, the user...").
- Suspicious gaps where a tool call shows no output but later turns reference its result.

If any are detected AND `FROM_COMPACTED_OK` is `0`, refuse:

```text
Error: conversation appears compacted (detected: <markers>). Capture refuses to
synthesize from a compacted transcript — risk of fabricating requirements that
were edited out of the visible context.

Options:
 - Expand context (open a fresh session with the full discussion).
 - Re-run with --from-compacted-ok if you've verified the visible turns
 contain the full intent.
```

In **autofix mode**, exit 2. In **interactive mode**, this is a hard refusal — capture does not offer to "ask the user to confirm anyway" (the user can re-invoke with the flag if they trust the transcript).

If no compaction signal is detected, proceed to 0.5.

### 0.5 — Branch on duplicate (interactive only)

When 0.2 detected ≥2 strong matches AND `REWRITE_TARGET` is empty:

Format the question via `request_user_input`:

- **header**: `Duplicate?`
- **body**: `Found <N> potentially overlapping epic(s): <epic-1> "<title-1>", <epic-2> "<title-2>". Recommended: <extend|proceed-anyway> — <one-sentence rationale>. Confidence: [<tier>].`
- **options** (frozen labels, no recommendation marker on the option itself):
 - `extend <epic-id>` — add criteria to the existing epic (capture exits; skill suggests `--rewrite <id>` rerun)
 - `supersede <epic-id>` — close the old epic and capture this one fresh (capture proceeds; the user closes the old one manually after capture lands)
 - `proceed-anyway` — accept that two epics will live alongside each other (capture proceeds)
 - `abort` — exit cleanly, no write

Recommendation logic:

| Strong match count | Recommended | Confidence |
|--------------------|-------------|------------|
| 3+ | `extend <strongest-id>` | `[high]` |
| 2 | `proceed-anyway` | `[judgment-call]` |

If the user picks `extend`, exit 0 with: `Re-run with --rewrite <epic-id> to overwrite the existing spec, or invoke /flow-next:interview <epic-id> to refine via Q&A.`

If `supersede` or `proceed-anyway`, store the choice and continue to Phase 1.

In **autofix mode**, when 0.2 detected ≥2 strong matches AND `REWRITE_TARGET` is empty:

```text
Error: <N> potentially overlapping epic(s) detected: <epic-1>, <epic-2>.
Capture cannot resolve duplicates in autofix mode.

Options:
 - Re-run with --rewrite <epic-id> to overwrite a specific epic.
 - Re-run interactively (drop mode:autofix) to choose extend / supersede / proceed-anyway.
```

Exit 2.

### 0.6 — Idempotency (R8)

If `REWRITE_TARGET` is set:

- Validate the target exists **and is an epic** (not a task — `flowctl show` accepts both, but capture only writes specs to epic IDs):

 ```bash
 out=$("$FLOWCTL" show "$REWRITE_TARGET" --json) || { echo "Error: --rewrite target $REWRITE_TARGET does not exist. Drop --rewrite to create a new epic, or pick an existing epic id." >&2; exit 2; }
 if echo "$out" | jq -e '.tasks' >/dev/null 2>&1; then
 : # epic — has .tasks array
 else
 echo "Error: --rewrite target $REWRITE_TARGET is a task, not an epic. Pass an epic id (fn-N-slug, no .M suffix)." >&2
 exit 2
 fi
 ```

- If the target is missing or is a task, exit 2 with the appropriate error message above.
- Read the existing spec. Phase 4 read-back will show a diff (existing → proposed) before write.

If `REWRITE_TARGET` is empty, also scan the visible conversation for prior-capture artifact references — patterns like `Spec captured at .flow/specs/<id>.md` from earlier turns. If found:

- **Interactive:** ask via `request_user_input` whether the user wants to (a) `--rewrite <id>` (re-run with the flag), (b) `proceed` (create a new epic anyway, accepting that two specs result), (c) `abort`.
- **Autofix:** exit 2 with: `Error: prior capture artifact <id> detected in conversation. Re-run with --rewrite <id> to overwrite, or interactively to choose. Pass --yes only after picking a path.`

### Done when

- Conversation keywords are extracted (top-10).
- Epic-title overlap scan ran; matches recorded.
- Memory cross-check ran (if memory initialized) and aggregated.
- Compaction check passed (or `--from-compacted-ok` overrode it).
- Idempotency resolution is clear: either `REWRITE_TARGET` is set + validated, or no prior-capture artifact conflict, or the user chose proceed/supersede.

---

## Phase 1: Extract conversation evidence (R3)

**Goal:** build the `## Conversation Evidence` block FIRST. Subsequent phases refer to it by line, not from agent memory of the conversation. This is the audit-trail that makes the source-tagging in Phase 2 verifiable.

### 1.1 — Extract verbatim user turns

Walk recent user turns in order. For each turn that contains spec-relevant content (goals, requirements, decisions, constraints, scope statements, rejected alternatives), emit one line in the evidence block:

```
> user (turn <N>): "<verbatim text>"
```

Rules:

- **Verbatim only** — no rewording. If a turn is too long for one line, split into multiple `> user (turn N, part 1)` / `(turn N, part 2)` lines, each verbatim. Do not summarize.
- **Skip** turns that are pure greetings, off-topic asides, tool-result interpretation by the user, or noise.
- **Include** turns that state intent, give examples, name constraints, reject options, or reference files.
- **Cap** at ~30 lines total. If older spec-relevant turns must be dropped, replace them with one `> [truncated: N earlier turns]` line at the top of the block.

### 1.2 — Optional codebase verification (subagent dispatch — R12)

When the conversation references repo files or modules whose state matters for the spec ("the auth module needs X", "we already have a rate limiter at..."), spawn a **read-only investigation subagent** via the `Task` tool with `subagent_type: Explore` (or `general-purpose` when Explore is unavailable). For clean conversations with no file references, skip this step. ( per repo cross-platform convention.)

Investigation subagents are **read-only**. They must not Edit, Write, Bash beyond Read / Grep / Glob, or git-mutate. Pass `disallowedTools: Edit, Write, Task` when dispatching. Each returns:

```yaml
references_verified:
 - path: src/auth/oauth.ts
 exists: true
 last_modified: "2026-03-12"
references_missing:
 - path: src/legacy/auth_v1.ts
 note: "user mentioned but file not found; possibly already removed"
related_modules_found:
 - path: src/auth/middleware.ts
 relevance: "implements existing OAuth flow user wants to extend"
```

When spawning subagents, include this directive in the task prompt:

> Use Read, Grep, Glob for all file investigation. Do NOT use shell commands (`ls`, `find`, `cat`, `grep`, `bash`) for file operations. This avoids permission prompts and is more reliable. Do NOT edit, create, or delete any files. Return only the structured payload defined in the workflow.

The orchestrator (this skill, on the main thread) merges results into Phase 2's `[inferred]` confidence — verified references can be tagged `[paraphrase]`; unverified or missing files stay `[inferred]` and surface in Phase 4 read-back for explicit user confirmation.

For 1-2 file references, investigate on the main thread — no subagent overhead is worth it.

### 1.3 — Initial title extraction

From the conversation, draft a candidate epic title. Heuristic:

- The shortest noun phrase that captures the goal (e.g. "Rate limit OAuth callbacks", "Audit memory entries", "Capture conversation as spec").
- Avoid verbs at the front (Linear / GitHub epic convention prefers noun phrases).
- 60 chars max.

The title may be `[inferred]` if the conversation never named one explicitly. Phase 3's must-ask case (a) fires when the title is genuinely ambiguous from conversation — multiple plausible titles, none load-bearing.

### Done when

- The `## Conversation Evidence` block is drafted (≤30 lines verbatim user quotes).
- Optional subagent investigation completed; references_verified / missing recorded.
- A candidate epic title is drafted (with confidence — high if user used the phrase, low if agent invented it).

---

## Phase 2: Source-tagged synthesis (R4, R14, R15)

**Goal:** draft the spec body using the CLAUDE.md richer template, with **per-line source tags** so hallucinated content is visible at Phase 4 read-back.

### 2.1 — Source-tag taxonomy

Every acceptance criterion line, every decision-context line, and every scope-bounding line in the spec carries one tag:

| Tag | Meaning | Example |
|-----|---------|---------|
| `[user]` | Verbatim from conversation evidence (exact quote or close paraphrase preserving meaning) | `- **R1:** Rate limit must reject ≥3 requests/sec from a single client. [user] (turn 4)` |
| `[paraphrase]` | User intent restated in spec language (semantic equivalence; no new constraints introduced) | `- **R2:** Spec body is written via heredoc, atomic write. [paraphrase]` |
| `[inferred]` | Agent fill-in (most-scrutinized; user must confirm at read-back) | `- **R7:** Errors include the request id for trace correlation. [inferred]` |

Pure prose sections (Goal & Context narrative, Architecture overview) do not need per-line tags — but the **whole section** carries a section-level tag in a frontmatter-style note: e.g. `<!-- Goal & Context: 70% [user], 30% [inferred] -->`. Phase 4 read-back surfaces this.

### 2.2 — Apply the CLAUDE.md richer template

Draft these sections in order. The first section after frontmatter is **always** `## Conversation Evidence` (Phase 1 output verbatim). Then:

- `## Goal & Context` — why this exists, what problem it solves. Mostly `[user]` / `[paraphrase]`.
- `## Architecture & Data Models` — system design, data flow, key components. **File / component refs are `[inferred]` unless the user explicitly named them in conversation.** If Phase 1.2 verified a reference, tag `[paraphrase]`.
- `## API Contracts` — endpoints, interfaces, input/output shapes. Often `[inferred]` because conversation rarely specifies wire formats. Mark accordingly.
- `## Edge Cases & Constraints` — failure modes, limits, performance reqs. Mix of `[user]` and `[inferred]`.
- `## Acceptance Criteria` — testable; R-IDs (`- **R1:** ...`); each tagged. **R-IDs allocate sequentially from R1** — capture creates fresh epics, no renumber concern.
- `## Boundaries` — explicit out-of-scope. Often `[inferred]` from what the user did NOT say. Surface at read-back as agent-decided defaults.
- `## Decision Context` — why this approach over alternatives. Preserve any rejected alternatives the user mentioned (Linear-pattern: rejected options live in spec history, not flow off-screen).

Followed by:

- `## Requirement coverage` — table mapping each R-ID to "fn-N.M (TBD — populate via /flow-next:plan)" placeholder. Capture ships unbroken-down epics; `/flow-next:plan` does the breakdown later.

### 2.3 — R-ID allocation rules (R15)

- Use the prose prefix format: `- **R1:** ...`, `- **R2:** ...`, etc.
- Allocate sequentially from R1 in creation order. Capture-created epics have never been reviewed → no renumber concern (the renumber-forbidden rule from `flow-next-plan/steps.md:227-262` only applies after a review cycle).
- R-IDs in `## Acceptance Criteria` and `## Requirement coverage` must match.
- Plain markdown prose, not YAML.

### 2.4 — Acceptance-criterion testability check

Every acceptance criterion must be testable in principle. As you draft each one, ask:

- Could a reviewer point at code / behavior / config and say "this is satisfied" or "this is not"?
- Is the criterion specific enough that two engineers would agree on satisfaction?

If a candidate criterion fails the test (e.g. "make it fast", "improve UX"), it triggers Phase 3 must-ask case (b). Either the user clarifies (interactive), or autofix exits 2.

Track `[inferred]` count across all sections (especially in `## Acceptance Criteria` and `## Boundaries`). The count surfaces at Phase 4 read-back.

### 2.5 — Acceptance-criterion volume heuristic (R11)

If Phase 2 produces **8 or more acceptance criteria**, Phase 4 read-back includes a `consider splitting?` option. The skill **never auto-splits**. The user decides:

- Accept the larger epic.
- Edit (drop / reword criteria).
- Approve and run `/flow-next:plan <id>` afterward — plan can break it into multiple stages.

Capture's heuristic: ≥8 R-IDs is the trigger. The 8+ count itself goes into the read-back body.

### Done when

- Every section is drafted with source tags applied.
- R-IDs are allocated sequentially.
- `[inferred]` count is computed.
- 8+ acceptance count flag set if applicable.
- Untestable acceptance candidates flagged for Phase 3 must-ask.

---

## Phase 3: Must-ask cases (R9)

**Goal:** resolve the three hard-error conditions. Interactive: ask one question at a time. Autofix: exit 2 with which case fired.

The must-ask cases are listed in [phases.md](phases.md) with examples. Summary here:

| Case | Trigger | Interactive question | Autofix |
|------|---------|----------------------|---------|
| **(a) Ambiguous title** | Multiple plausible titles, none load-bearing in conversation | Ask user to pick title from candidates + offer custom | exit 2 |
| **(b) Untestable acceptance** | Phase 2.4 flagged ≥1 criterion that can't be made testable | Ask per-criterion: drop / reword / clarify | exit 2 |
| **(c) Scope-conflict** | Phase 0.5 went `supersede` or `proceed-anyway`, but the new epic's scope still overlaps the old one's | Ask user how to disambiguate boundaries | exit 2 |

### 3.1 — Interactive question shape

Use `request_user_input` with the lead-with-recommendation pattern:

- **header**: short tag (`Title?`, `Criterion R3`, `Boundary?`)
- **body**: `<Context — what's ambiguous and why>. Recommended: <X> — <one-sentence rationale>. Confidence: [<tier>].`
- **options**: frozen neutral labels (no recommendation markers on the options themselves)

Confidence tier rules (see [phases.md](phases.md) §Confidence tiers):

- `[high]` — agent has strong codebase signal or convention match
- `[judgment-call]` — slight lean but reasonable people disagree
- `[your-call]` — agent has no signal; user's domain knowledge / priority decides

The third tier matters: it prevents the "always recommend" failure mode that trains users to defer.

### 3.2 — Optional ambiguities (not must-ask)

For optional ambiguities — the spec has `[inferred]` content the user might want to scrutinize but it's not blocking — do NOT ask in Phase 3. Surface them in the Phase 4 read-back's `[inferred]` tally; the user can pick `edit` if they want to revise.

Phase 3 only fires for the three hard-error cases. Asking too many questions defeats capture's purpose.

### 3.3 — One question per turn

Even when multiple must-ask cases fire, ask **one at a time**. Subsequent questions adapt based on prior answers. Multi-question violates the `request_user_input` contract and overwhelms users (practice-scout F4.3).

### Done when

- All must-ask cases resolved (interactive) or exited 2 (autofix).
- Spec draft updated with user-chosen title / reworded criteria / disambiguated boundaries.

---

## Phase 4: Read-back loop (R7, R11) — MANDATORY

**Goal:** show the user the full draft before write. Even in autofix mode (`--yes` is the read-back substitute).

### 4.1 — Build the read-back payload

Construct the full draft including:

1. Frontmatter (`title`, candidate `branch_name`).
2. The `## Conversation Evidence` block (Phase 1).
3. Every section drafted in Phase 2, with source tags visible.
4. The `## Acceptance Criteria` R-ID list — bulleted, source tags shown.
5. **`[inferred]` tally** — total count across the spec, with per-section breakdown:
 ```
 [inferred] count: 7 total
 - Architecture & Data Models: 3
 - API Contracts: 2
 - Boundaries: 2
 ```
6. **8+ acceptance-criterion suggestion** (if Phase 2.5 fired):
 ```
 This spec has 11 acceptance criteria — consider splitting into multiple
 epics? You can: approve as-is, edit (drop some), or accept and split via
 /flow-next:plan after capture lands.
 ```
7. **Related context** footnote (if Phase 0.3 found memory hits):
 ```
 Related memory entries (not blocking): bug/runtime-errors/oauth-callback-2025-08-12
 ```
8. **Diff** — if `REWRITE_TARGET` is set, show existing spec → proposed spec diff (unified diff style; only show changed sections in full to keep the read-back navigable).

### 4.2 — Interactive read-back

Use `request_user_input`:

- **header**: `Read-back`
- **body**: `Draft: <inline full draft above>. [N] criteria are [inferred]. <8+ split note if applicable>. Recommended: approve — <one-sentence summary of confidence>. Confidence: [<tier>].`
- **options** (frozen):
 - `approve` — proceed to Phase 5 write
 - `edit` — revise specific sections (loops back to Phase 2 for those sections)
 - `consider-split` (only when Phase 2.5 fired) — exits 0; suggests user re-invokes capture with a narrower scope, or runs `/flow-next:plan` afterward to stage the breakdown
 - `abort` — exit 0, no write

Confidence tier for the recommendation:

- `[high]` — `[inferred]` count is low (≤2) and no user-facing claims contradict the conversation evidence.
- `[judgment-call]` — `[inferred]` count is moderate (3-6) or some `[inferred]` items are load-bearing (e.g. core acceptance criteria).
- `[your-call]` — `[inferred]` count is high (7+) or rewrite-mode with substantive divergence from existing spec.

### 4.3 — Edit branch

If user picks `edit`:

- Ask which sections (offer multi-select if the platform supports it; otherwise serial single-select).
- For each section, re-run Phase 2's drafting logic for that section only, with the user's correction context as additional input.
- Re-tally `[inferred]` count.
- Re-show the read-back. Loop until user picks `approve` or `abort`.

Hard cap at **3 edit cycles**. If the user is still editing on the 4th cycle, surface: `You've gone through 3 edit cycles. Capture's read-back loop isn't deep refinement — consider /flow-next:interview <id> after capture lands for iterative Q&A.` Offer `approve as-is` / `abort` only.

### 4.4 — Autofix read-back

Print the full read-back payload (4.1) to stdout as a markdown block. Then:

- If `COMMIT_YES=0`, exit 0 with: `Draft printed above. Re-run with --yes to commit (in autofix mode, --yes substitutes for the interactive read-back approval).`
- If `COMMIT_YES=1`, proceed to Phase 5.

Autofix never offers `edit` — there's no user to ask. The print-then-rerun-with-yes pattern mirrors `flowctl memory migrate --yes` and is the documented autofix-substitute for read-back approval.

### 4.5 — Forbidden in Phase 4

- **Never silently skip the read-back.** Even if `[inferred]` count is 0, show the draft. The user might still want to reject for reasons unrelated to inference.
- **Never auto-split.** The `consider-split` option exits 0 and lets the user decide; it does not call `flowctl epic create` twice.
- **Never edit `--rewrite` target without showing the diff.** The diff is non-optional in rewrite mode.

### Done when

- Interactive: user picked `approve` (proceed to Phase 5), `consider-split` / `abort` (exit 0, no write), or hit the edit-cycle cap.
- Autofix with `--yes`: payload printed, proceeding to Phase 5.
- Autofix without `--yes`: payload printed, exit 0.

---

## Phase 5: Write via flowctl (R14, R15, R16)

**Goal:** atomic write of the new (or rewritten) epic via existing flowctl plumbing.

### 5.1 — Build the spec body

The spec body assembled in Phase 2 + revised in Phase 4 edit cycles is the input to `flowctl epic set-plan`. Source tags **stay in the spec body** — they are part of the audit trail and survive into the on-disk spec at `.flow/specs/<id>.md`. Future readers (including `/flow-next:plan` and `/flow-next:interview`) see the tags and can scrutinize.

The frontmatter top of the spec is whatever `flowctl epic create` writes (it generates a placeholder via `create_epic_spec`). `epic set-plan` overwrites the placeholder with the captured body — so the captured body should NOT include a duplicate `# <title>` heading; `set-plan` accepts the body as-is and atomic-writes to `.flow/specs/<id>.md`.

### 5.2 — New-epic branch

```bash
EPIC_TITLE="<chosen title from Phase 3 or Phase 1.3>"

# Create the epic — captures the JSON to extract the allocated id.
EPIC_OUTPUT=$("$FLOWCTL" epic create --title "$EPIC_TITLE" --json)
EPIC_ID=$(printf '%s' "$EPIC_OUTPUT" | jq -r '.id')

if [[ -z "$EPIC_ID" || "$EPIC_ID" == "null" ]]; then
 echo "Error: epic create failed: $EPIC_OUTPUT" >&2
 exit 1
fi

# Write the spec body via heredoc.
"$FLOWCTL" epic set-plan "$EPIC_ID" --file - --json <<EOF
$SPEC_BODY
EOF
```

Use a real heredoc (not `printf`) so embedded markdown formatting and newlines round-trip cleanly. `read_file_or_stdin` in `flowctl.py` handles `--file -` correctly.

### 5.3 — Rewrite branch

When `REWRITE_TARGET` is set:

```bash
EPIC_ID="$REWRITE_TARGET"

# Skip epic create — the epic already exists. Just overwrite the spec.
"$FLOWCTL" epic set-plan "$EPIC_ID" --file - --json <<EOF
$SPEC_BODY
EOF
```

### 5.4 — Optional branch-name set

If the user named a feature branch in conversation (e.g. "let's call this branch `oauth-rate-limit`"), set it:

```bash
"$FLOWCTL" epic set-branch "$EPIC_ID" --branch "<slug>" --json
```

Skip silently if no branch was named — `epic create` already populated `branch_name` with the epic id, which is a fine default.

### 5.5 — Capture write failures

If `epic create` fails (e.g. `.flow/` corrupted, disk full): exit 1 with the error. The user has not yet committed anything.

If `epic set-plan` fails: the epic JSON exists but the spec is the placeholder. Surface the failure and the rollback option:

```text
Error: epic set-plan failed for <id>. The epic JSON was created but the spec
write failed. To roll back: rm .flow/epics/<id>.json .flow/specs/<id>.md
(if it exists). Or re-run capture with --rewrite <id> to retry the spec write.
```

This mirrors the failure semantics in other flowctl commands — partial-state recovery is on the user, but the error is loud.

### 5.6 — No git commit from this skill

Capture **does not** stage or commit the new spec. The user owns when to commit. The output footer (Phase 6) tells them what to do.

Two reasons:

1. The captured spec often gets edited by `/flow-next:plan` immediately after — committing twice (once for capture, once after plan adds tasks) is noise.
2. Capture changes touch only `.flow/`; users sometimes want to bundle them with adjacent edits.

If a future enhancement adds a `--commit` flag, Phase 5 would gain a "stage + commit" branch, but the default stays "no commit, user owns the staging".

### Done when

- The new (or rewritten) epic spec is on disk at `.flow/specs/<id>.md`.
- `EPIC_ID` is known for Phase 6.
- Optional branch-name is set if user named one.

---

## Phase 6: Suggested next step (R16)

**Goal:** print the suggested next step. The deliverable is the new spec; this footer tells the user what to do with it.

```text
Spec captured at .flow/specs/<EPIC_ID>.md.

Next:
 /flow-next:plan <EPIC_ID> → research + break into tasks
 /flow-next:interview <EPIC_ID> → refine via Q&A
```

If Phase 4 surfaced 8+ acceptance criteria AND the user picked `approve` (not `consider-split`), append:

```text
Note: this epic has <N> acceptance criteria — /flow-next:plan can stage the
breakdown into multiple sub-epics if needed.
```

If Phase 0.3 found memory hits, append the related-context footer:

```text
Related context (existing memory): <comma-separated entry ids>
Consider reviewing before /flow-next:plan to avoid re-solving documented problems.
```

If `REWRITE_TARGET` was set, the footer prefix changes:

```text
Spec rewritten at .flow/specs/<EPIC_ID>.md.

Next:
 /flow-next:plan <EPIC_ID> → re-plan tasks (existing tasks under the epic
 may need /flow-next:sync to align)
 /flow-next:interview <EPIC_ID> → refine via Q&A
```

### Done when

- Footer is printed.
- Skill exits 0.

---

## Manual smoke (acceptance R3, R4, R5, R6, R7, R8)

The skill itself is markdown — there's no unit-test surface. The validation is invoking `/flow-next:capture` in a real session. Expected behavior:

- Phase 0 walks `.flow/epics/`, runs memory search if memory is initialized, detects compaction, applies idempotency. Branches into duplicate-detection question if ≥2 strong matches; exits cleanly on `abort`.
- Phase 1 emits a `## Conversation Evidence` block with verbatim user quotes (≤30 lines).
- Phase 2 produces a draft with per-line source tags. Every acceptance criterion has one of `[user]` / `[paraphrase]` / `[inferred]`.
- Phase 3 fires must-ask cases only when (a) title is genuinely ambiguous, (b) acceptance is untestable, (c) scope-conflict persists. Optional ambiguities are deferred to Phase 4.
- Phase 4 read-back surfaces `[inferred]` count, 8+ split note (if applicable), related-memory footer (if applicable). Interactive: user picks approve / edit / abort. Autofix: print + require `--yes`.
- Phase 5 calls `flowctl epic create` + `epic set-plan` via heredoc.
- Phase 6 prints the next-step footer.

In autofix without `--yes`, the draft prints and the skill exits 0 — no write, no epic allocated.
In autofix with `--yes`, Phase 4 still prints the draft (substituting for read-back) before Phase 5 writes.

The Ralph-block (SKILL.md) ensures this skill never runs under `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` — capture requires a user at the terminal.
