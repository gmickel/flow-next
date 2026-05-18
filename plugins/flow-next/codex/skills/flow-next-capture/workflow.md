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

**Goal:** catch the three conditions that make capture unsafe BEFORE drafting a spec — duplicate specs, compacted conversation, idempotency conflict. Each has its own decision branch.

### 0.1 — Extract candidate keywords from conversation

Capture's input is the conversation, not `$ARGUMENTS`. Walk the visible user turns and pull:

- **Proper nouns** — capitalized terms used at least twice, excluding sentence-start common words.
- **File paths** — anything matching `[\w./_-]+\.(py|ts|tsx|js|md|json|sh|toml|yaml|yml)` or starting with `src/`, `plugins/`, `scripts/`, `.flow/`.
- **Domain-specific terms** — multi-word phrases the user repeated (e.g. "rate limiter", "OAuth callback", "review walkthrough").
- **Quoted phrases** — anything the user put in `"..."` or `\`...\`` while describing the feature.

Cap the candidate keyword list at the top **10** by frequency. These feed both 0.2 (spec title overlap) and 0.3 (memory search). Strip ordinary English connectors (`the`, `a`, `and`, `or`, `to`, `for`, `with`, `via`).

### 0.2 — Duplicate detection: spec title overlap

Scan both `.flow/specs/*.json` (post-1.0 canonical) and `.flow/epics/*.json` (legacy alias dir on unmigrated 0.x repos). Both paths are walked because `flowctl init` (post-1.0) writes only `.flow/specs/`, but pre-migration repos still keep their JSON metadata under `.flow/epics/` until `flowctl migrate-rename` runs.

```bash
shopt -s nullglob
SPEC_FILES=( "$SPECS_DIR"/*.json "$EPICS_DIR"/*.json )
shopt -u nullglob
```

For each spec JSON, read `id` + `title` + `status`. Skip closed specs (`status: closed`).

For each remaining spec, compute keyword overlap with the conversation keywords. Count **strong matches** — proper nouns / file paths / multi-word phrases that appear in both. Common single English words are not strong matches.

| Strong matches | Action |
|----------------|--------|
| 0-1 | No conflict; skip 0.4 idempotency unless an explicit prior-capture artifact id is detected |
| 2 | **Potential** duplicate — surface at Phase 0.5 with `proceed-anyway` recommended |
| 3+ | **Likely** duplicate — surface at Phase 0.5 with `extend` (or `supersede`) recommended |

Record the matched spec ids + their titles for the Phase 0.5 question.

### 0.3 — Duplicate detection: memory search cross-check

If `flowctl memory list --json` reports memory is initialized, run a cross-check on the top-3 conversation keywords:

```bash
"$FLOWCTL" memory search "<keyword-1>" --json --limit 5 2>/dev/null
"$FLOWCTL" memory search "<keyword-2>" --json --limit 5 2>/dev/null
"$FLOWCTL" memory search "<keyword-3>" --json --limit 5 2>/dev/null
```

Memory hits are advisory — they signal "you may have prior art on this topic" without blocking. Aggregate hit ids + titles for the Phase 4 read-back's "Related context" footnote (when ≥1 hits land). They do **not** trigger the duplicate-detection branch on their own; only spec-title overlap (0.2) does.

If memory is not initialized (`memory list` returns the `Memory not initialized` error), skip this step silently. Memory search is a quality-of-life signal; absence is not blocking.

### 0.3b — Strategy snapshot (advisory grounding input)

Read `STRATEGY.md` (when populated) so Phase 2's source-tagging can apply `[strategy:<track>]` to acceptance criteria that follow directly from strategic intent. Husk-vs-presence gate uses `sections_filled >= 1` from `flowctl strategy status --json`, NOT `[[ -f STRATEGY.md ]]`.

```bash
STRATEGY_STATUS_JSON=$("$FLOWCTL" strategy status --json 2>/dev/null || echo '{"exists":false,"sections_filled":0}')
STRATEGY_FILLED=$(jq -r '.sections_filled // 0' <<< "$STRATEGY_STATUS_JSON" 2>/dev/null || echo 0)

if [[ "$STRATEGY_FILLED" -ge 1 ]]; then
 STRATEGY_JSON=$("$FLOWCTL" strategy read --json 2>/dev/null || echo '{}')
 STRATEGY_PRESENT=true
 STRATEGY_NAME=$(jq -r '.name // "(unnamed)"' <<< "$STRATEGY_JSON")
 STRATEGY_PROBLEM=$(jq -r '.target_problem // ""' <<< "$STRATEGY_JSON")
 STRATEGY_APPROACH=$(jq -r '.approach // ""' <<< "$STRATEGY_JSON")
 STRATEGY_TRACKS_RAW=$(jq -r '.tracks // ""' <<< "$STRATEGY_JSON")
 STRATEGY_PATH=$(jq -r '.path // "STRATEGY.md"' <<< "$STRATEGY_JSON")
else
 STRATEGY_PRESENT=false
fi
```

Surface as a "Strategic context:" footnote — 3-5 lines total — when the agent presents Phase 0 results to the user. Format:

```
Strategic context (STRATEGY.md, last updated 2026-04-30):
 Approach: <verbatim approach line, capped to 1-2 sentences>
 Active tracks: <track-name-1>, <track-name-2>, <track-name-3>
```

`STRATEGY_TRACKS_RAW` is a **raw markdown string** with `### <track-name>` H3 sub-blocks. Parse the H3 names locally for the active-tracks list. Empty section bodies (any of `target_problem`, `approach`, `tracks`) surface as `""` — `(.field // "")` style fallbacks in the jq queries above keep parsing well-formed when an optional section is missing.

The strategy snapshot is **input**, not gating: even when `STRATEGY_PRESENT=true`, capture proceeds. Phase 2's source-tagging uses the snapshot to assign `[strategy:<track-name>]` to criteria that quote / paraphrase strategy content. Phase 5 uses it to detect contradictions (see §5.0 below) and refuse the write without `--override-strategy`.

When `STRATEGY_PRESENT=false`, Phase 2 emits no `[strategy:*]` tags and Phase 5's contradiction check is skipped entirely — there is no signal to align to.

### 0.4 — Compaction detection (R6)

Scan the visible conversation for any of:

- Literal `[compacted]` markers.
- Truncated tool-result patterns: `<...output too large to include>`, `(output truncated)`, `... (N more lines)`.
- System-summary blocks (e.g. "Earlier in the conversation, the user...").
- Suspicious gaps where a prompt turn shows no output but later turns reference its result.

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

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.

Format the question via `plain-text numbered prompt`:

- **header**: `Duplicate?`
- **body**: `Found <N> potentially overlapping spec(s): <spec-1> "<title-1>", <spec-2> "<title-2>". Recommended: <extend|proceed-anyway> — <one-sentence rationale>. Confidence: [<tier>].`
- **options** (frozen labels, no recommendation marker on the option itself):
 - `extend <spec-id>` — add criteria to the existing spec (capture exits; skill suggests `--rewrite <id>` rerun)
 - `supersede <spec-id>` — close the old spec and capture this one fresh (capture proceeds; the user closes the old one manually after capture lands)
 - `proceed-anyway` — accept that two specs will live alongside each other (capture proceeds)
 - `abort` — exit cleanly, no write

Recommendation logic:

| Strong match count | Recommended | Confidence |
|--------------------|-------------|------------|
| 3+ | `extend <strongest-id>` | `[high]` |
| 2 | `proceed-anyway` | `[judgment-call]` |

If the user picks `extend`, exit 0 with: `Re-run with --rewrite <spec-id> to overwrite the existing spec, or invoke /flow-next:interview <spec-id> to refine via Q&A.`

If `supersede` or `proceed-anyway`, store the choice and continue to Phase 1.

In **autofix mode**, when 0.2 detected ≥2 strong matches AND `REWRITE_TARGET` is empty:

```text
Error: <N> potentially overlapping spec(s) detected: <spec-1>, <spec-2>.
Capture cannot resolve duplicates in autofix mode.

Options:
 - Re-run with --rewrite <spec-id> to overwrite a specific spec.
 - Re-run interactively (drop mode:autofix) to choose extend / supersede / proceed-anyway.
```

Exit 2.

### 0.6 — Idempotency (R8)

If `REWRITE_TARGET` is set:

- Validate the target exists **and is a spec** (not a task — `flowctl show` accepts both, but capture only writes specs to spec IDs):

 ```bash
 out=$("$FLOWCTL" show "$REWRITE_TARGET" --json) || { echo "Error: --rewrite target $REWRITE_TARGET does not exist. Drop --rewrite to create a new spec, or pick an existing spec id." >&2; exit 2; }
 if echo "$out" | jq -e '.tasks' >/dev/null 2>&1; then
 : # spec — has .tasks array
 else
 echo "Error: --rewrite target $REWRITE_TARGET is a task, not a spec. Pass a spec id (fn-N-slug, no .M suffix)." >&2
 exit 2
 fi
 ```

- If the target is missing or is a task, exit 2 with the appropriate error message above.
- Read the existing spec. Phase 4 read-back will show a diff (existing → proposed) before write.

If `REWRITE_TARGET` is empty, also scan the visible conversation for prior-capture artifact references — patterns like `Spec captured at .flow/specs/<id>.md` from earlier turns. If found:

- **Interactive:** ask via `plain-text numbered prompt` whether the user wants to (a) `--rewrite <id>` (re-run with the flag), (b) `proceed` (create a new spec anyway, accepting that two specs result), (c) `abort`.
- **Autofix:** exit 2 with: `Error: prior capture artifact <id> detected in conversation. Re-run with --rewrite <id> to overwrite, or interactively to choose. Pass --yes only after picking a path.`

### Done when

- Conversation keywords are extracted (top-10).
- Spec-title overlap scan ran (`.flow/specs/` + legacy `.flow/epics/`); matches recorded.
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

From the conversation, draft a candidate spec title. Heuristic:

- The shortest noun phrase that captures the goal (e.g. "Rate limit OAuth callbacks", "Audit memory entries", "Capture conversation as spec").
- Avoid verbs at the front (Linear / GitHub convention prefers noun phrases).
- 60 chars max.

The title may be `[inferred]` if the conversation never named one explicitly. Phase 3's must-ask case (a) fires when the title is genuinely ambiguous from conversation — multiple plausible titles, none load-bearing.

### Done when

- The `## Conversation Evidence` block is drafted (≤30 lines verbatim user quotes).
- Optional subagent investigation completed; references_verified / missing recorded.
- A candidate spec title is drafted (with confidence — high if user used the phrase, low if agent invented it).

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
| `[strategy:<track>]` | Derived from `STRATEGY.md` content (verbatim or near-verbatim from `approach` or a `### <track-name>` H3 sub-block); track name lives literally in the tag | `- **R9:** Service-level objective: 99.95% uptime measured monthly. [strategy:Reliability]` |

Pure prose sections (Goal & Context narrative, Architecture overview) do not need per-line tags — but the **whole section** carries a section-level tag in a frontmatter-style note: e.g. `<!-- Goal & Context: 70% [user], 30% [inferred] -->`. Phase 4 read-back surfaces this.

### 2.2 — Apply the canonical spec template

The canonical section structure lives in [`plugins/flow-next/templates/spec.md`](../../templates/spec.md) — the single source of truth for the section sequence and per-section ownership annotations (per R17 — never re-embed the section list inline; cross-link the template). Walk the template in its declared order and draft each section's body using the source-tag conventions below. Before any template section, prepend `## Conversation Evidence` (Phase 1 output verbatim); after the template, append `## Requirement coverage` (the R-ID → task mapping placeholder).

Source-tag application is per-tag, not per-section:

- **`[user]`** dominates where the conversation gave verbatim content (goal framing, user-stated acceptance, named non-goals, rejected alternatives the user surfaced).
- **`[paraphrase]`** is for spec-language restatements of user intent — preserving meaning, tightening wording.
- **`[inferred]`** covers agent fill-in for completeness (default conventions: error formats, retry policies, observability hooks, file / component refs the user did NOT name). **Untouched by §2.6 biz-routing** — biz destinations only accept `[user]` / `[paraphrase]`.
- **`[strategy:<track>]`** activates only when Phase 0 strategy snapshot was populated.

Auxiliary section rules layered on the template:

- **Phase 1.2 verified references** — if a subagent verified that a user-named file / component actually exists in the codebase, upgrade the tag from `[inferred]` → `[paraphrase]` for that line.
- **Sections without conversation signal stay absent.** Do NOT auto-populate a template section from agent assumptions just because the template has a slot for it. Empty-by-default beats fabricated-by-default.
- **`## Decision Context`** substructure (FLAT vs `### Motivation` / `### Implementation Tradeoffs` per the template's "(A) FLAT" vs "(B) SUBSTRUCTURED" branches) is governed by §2.6 — capture only emits SUBSTRUCTURED when biz-context routing has content for `### Motivation`; otherwise stays FLAT.
- **`## Acceptance Criteria`** R-IDs allocate sequentially from R1 — capture creates fresh specs, no renumber concern. Outcome-AC entries (user-facing "what success looks like") route via biz-context signal category 3 (§2.6); other criteria stay generic.
- **`## Requirement coverage`** appended after the template body — table mapping each R-ID to `fn-N.M (TBD — populate via /flow-next:plan)` placeholders. Capture ships unbroken-down specs; `/flow-next:plan` does the breakdown later.

### 2.3 — R-ID allocation rules (R15)

- Use the prose prefix format: `- **R1:** ...`, `- **R2:** ...`, etc.
- Allocate sequentially from R1 in creation order. Capture-created specs have never been reviewed → no renumber concern (the renumber-forbidden rule from `flow-next-plan/steps.md:227-262` only applies after a review cycle).
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

- Accept the larger spec.
- Edit (drop / reword criteria).
- Approve and run `/flow-next:plan <id>` afterward — plan can break it into multiple stages.

Capture's heuristic: ≥8 R-IDs is the trigger. The 8+ count itself goes into the read-back body.

### 2.6 — Biz-context signal routing (R24) + signal-category count for R25

While drafting §2.2's sections, walk the Phase 1 `## Conversation Evidence` block looking for explicit business-context signals across **nine SIGNAL CATEGORIES** (the counting unit for R25's sparse-suggestion heuristic). For each category that has at least one explicit signal in conversation, route the content to its destination using only `[user]` or `[paraphrase]` source tags. The full routing table with example trigger phrasing lives in [phases.md §Biz-context signal routing](phases.md). Summary:

| # | Signal category | Destination(s) |
|---|-----------------|----------------|
| 1 | Target user / persona | `Goal & Context` |
| 2 | Problem framing / why-now | `Goal & Context` |
| 3 | Success metrics / definition of done | outcome-AC + `## Decision Context > ### Motivation` |
| 4 | MVP scope / "not doing X yet" | `Boundaries` |
| 5 | Business constraints (regulatory, deadlines, budget) | `Goal & Context` OR `## Decision Context > ### Motivation` |
| 6 | What NOT to build / non-goals | `Boundaries` |
| 7 | Prioritization rationale | `## Decision Context > ### Motivation` |
| 8 | Business risks | `Goal & Context` OR `## Decision Context > ### Motivation` |
| 9 | UX expectations | `Goal & Context` |

Rules:

- **Source tags restricted to `[user]` or `[paraphrase]`** for biz-routed content. `[inferred]` never routes to a business destination. If a category has no conversation signal, its destination(s) receive no new content — sections without conversation signal stay absent (no empty-section auto-populate; this is the R22 invariant).
- **One signal can land in multiple destinations** (e.g., a success metric becomes both an outcome-AC R-ID and a `### Motivation` rationale entry) — that still counts as **one** SIGNAL CATEGORY for the R25 threshold. Counting is over R24's nine categories, not over markdown destinations.
- **Decision Context substructure** — capture only ever writes fresh specs (never a rewrite of an existing FLAT body), so there is no FLAT→substructured promotion to handle here (that's `/flow-next:interview`'s merge contract). Decision rule for capture: when category 3, 5, 7, or 8 routes content, write `## Decision Context` as SUBSTRUCTURED — emit the `### Motivation` H3 with the routed content. Leave `### Implementation Tradeoffs` absent (do NOT write the `*Pending technical-scope interview pass.*` placeholder; that's `/flow-next:interview --scope=business`'s responsibility on a rewrite, not capture's). When none of categories 3, 5, 7, 8 carry content, write `## Decision Context` as FLAT — preserves R22 (solo dev with zero biz signals sees no Motivation/Implementation Tradeoffs scaffolding) and matches the canonical template's "(A) FLAT (default, R22 backward-compat)" branch.
- **Constraints / risks (categories 5, 8) pick one destination per signal** — `Goal & Context` when the constraint sets up framing, `### Motivation` when it's the reason behind a trade-off. Don't double-route to both for the same signal.

After §2.2's section drafting completes, compute `BIZ_SIGNAL_CATEGORIES` — the count of distinct categories (out of nine) that received at least one `[user]` or `[paraphrase]` line. This count is Phase 6's input to `flowctl scope suggest`:

```bash
# Set after drafting §2.2's sections. Range: 0..9. Counts CATEGORIES, not destinations.
# Example: a conversation that named a target user, an MVP boundary, and rejected a feature
# (categories 1, 4, 6) sets BIZ_SIGNAL_CATEGORIES=3 even though it touched only two destinations
# (Goal & Context + Boundaries).
BIZ_SIGNAL_CATEGORIES=<int>
```

Worked example — conversation: *"For junior engineers, we need a one-click upgrade flow. MVP is just the install path — no rollback yet. We definitely won't support Windows."*

- Category 1 (target user: "junior engineers") → `Goal & Context` [user]
- Category 4 (MVP boundary: "MVP is just the install path") → `Boundaries` [user]
- Category 6 (non-goals: "won't support Windows") → `Boundaries` [paraphrase]
- `BIZ_SIGNAL_CATEGORIES=3` → R25 suggestion does NOT fire (threshold is `1 <= N < 3`; 3 means the biz layer is adequate). `## Decision Context` stays FLAT (none of categories 3, 5, 7, 8 had content).

Worked example — conversation: *"This is for the ops team. Definitely don't add a UI."*

- Category 1 (target user: "ops team") → `Goal & Context` [user]
- Category 6 (non-goals: "don't add a UI") → `Boundaries` [paraphrase]
- `BIZ_SIGNAL_CATEGORIES=2` → R25 suggestion **fires** (sweet spot — biz signals present but underspecified). `## Decision Context` stays FLAT.

Worked example — conversation: *"add timestamps to log lines"* (purely technical, zero biz signals):

- No category carries content → no biz-routed lines written.
- `BIZ_SIGNAL_CATEGORIES=0` → R25 suggestion does NOT fire (R22 invariant — solo dev who never mentioned biz context sees zero new prompts). `## Decision Context` stays FLAT.

### Done when

- Every section is drafted with source tags applied.
- R-IDs are allocated sequentially.
- `[inferred]` count is computed.
- 8+ acceptance count flag set if applicable.
- Untestable acceptance candidates flagged for Phase 3 must-ask.
- `BIZ_SIGNAL_CATEGORIES` (0..9) computed for Phase 6 R25 dispatch.

---

## Phase 3: Must-ask cases (R9)

**Goal:** resolve the three hard-error conditions. Interactive: ask one question at a time. Autofix: exit 2 with which case fired.

The must-ask cases are listed in [phases.md](phases.md) with examples. Summary here:

| Case | Trigger | Interactive question | Autofix |
|------|---------|----------------------|---------|
| **(a) Ambiguous title** | Multiple plausible titles, none load-bearing in conversation | Ask user to pick title from candidates + offer custom | exit 2 |
| **(b) Untestable acceptance** | Phase 2.4 flagged ≥1 criterion that can't be made testable | Ask per-criterion: drop / reword / clarify | exit 2 |
| **(c) Scope-conflict** | Phase 0.5 went `supersede` or `proceed-anyway`, but the new spec's scope still overlaps the old one's | Ask user how to disambiguate boundaries | exit 2 |

### 3.1 — Interactive question shape

Use `plain-text numbered prompt` with the lead-with-recommendation pattern:

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

Even when multiple must-ask cases fire, ask **one at a time**. Subsequent questions adapt based on prior answers. Multi-question violates the `plain-text numbered prompt` contract and overwhelms users (practice-scout F4.3).

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
5. **Source-tag tally** — total count across the spec, with per-tag breakdown. Format:
 ```
 Source: [user] N · [paraphrase] M · [strategy] K · [inferred] L
 ```
 Followed by the per-section `[inferred]` breakdown (the most-scrutinized class):
 ```
 [inferred] count: 7 total
 - Architecture & Data Models: 3
 - API Contracts: 2
 - Boundaries: 2
 ```
 The `[strategy]` count aggregates all `[strategy:<track>]` lines regardless of track. When Phase 0 strategy snapshot scanned `none` (`STRATEGY_PRESENT=false`), `[strategy] K` reads `[strategy] 0` (or the field is omitted entirely — equivalent in practice).
6. **8+ acceptance-criterion suggestion** (if Phase 2.5 fired):
 ```
 This spec has 11 acceptance criteria — consider splitting into multiple
 specs? You can: approve as-is, edit (drop some), or accept and split via
 /flow-next:plan after capture lands.
 ```
7. **Related context** footnote (if Phase 0.3 found memory hits):
 ```
 Related memory entries (not blocking): bug/runtime-errors/oauth-callback-2025-08-12
 ```
8. **Diff** — if `REWRITE_TARGET` is set, show existing spec → proposed spec diff (unified diff style; only show changed sections in full to keep the read-back navigable).

### 4.2 — Interactive read-back

Use `plain-text numbered prompt`:

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
- **Never auto-split.** The `consider-split` option exits 0 and lets the user decide; it does not call `flowctl spec create` twice.
- **Never edit `--rewrite` target without showing the diff.** The diff is non-optional in rewrite mode.

### Done when

- Interactive: user picked `approve` (proceed to Phase 5), `consider-split` / `abort` (exit 0, no write), or hit the edit-cycle cap.
- Autofix with `--yes`: payload printed, proceeding to Phase 5.
- Autofix without `--yes`: payload printed, exit 0.

---

## Phase 5: Write via flowctl (R14, R15, R16)

**Goal:** atomic write of the new (or rewritten) spec via existing flowctl plumbing.

### 5.0 — Strategy contradiction check (gate; runs before any write)

When the Phase 0 strategy snapshot was populated (`STRATEGY_PRESENT=true`), scan the drafted spec body for contradictions against the active tracks. A contradiction exists when:

1. The spec body has at least one `[strategy:<track>]` line AND the surrounding criterion / decision-context line negates the corresponding track body. Example: track `### CLI-only` says "we ship CLI tools, not SaaS"; spec criterion `[strategy:CLI-only]` reads "ship a managed dashboard service" — direct contradiction.
2. The spec body proposes an investment area that contradicts `approach` directly. Example: approach says "OSS-tools repo, no commercial SaaS"; spec body adds "stripe billing integration as a core feature" without `[strategy:*]` tagging — semantic contradiction even without a tag.

When a contradiction is detected AND `OVERRIDE_STRATEGY` is `0`:

```text
Error: spec contradicts active track "<track>" — pass --override-strategy to proceed.

Detected contradiction:
 Track: <track-name> (STRATEGY.md)
 Track says: "<canonical wording>"
 Spec says: "<conflicting wording>"

Re-run with --override-strategy to write the spec anyway. You'll be prompted to
record the override as a decision entry (the override is exactly the kind of
load-bearing architectural choice the decisions track exists for).
```

In **interactive** mode, refuse with the message above (exit 2) — do NOT prompt the user to override here; require the explicit flag re-run so the override is intentional.

In **autofix** mode, refuse identically (exit 2). Autofix cannot resolve a strategy override.

When `OVERRIDE_STRATEGY=1` AND the snapshot is populated, capture proceeds with the write **AND** prompts the user to record the override as a decision entry. Pattern (mirrors `/flow-next:interview` behavior (d) — three-criteria decision-record gate):

```bash
# Interactive only — autofix never reaches this branch (5.0 exits 2 above when OVERRIDE_STRATEGY=0,
# and OVERRIDE_STRATEGY=1 in autofix is treated as "user already chose to override; record audit
# trail to stderr but don't prompt" — see logging branch below).
```

Use `plain-text numbered prompt` (lead-with-recommendation, `[high]` toward yes):

- **header**: `Record override?`
- **body**: `Override strategy track "<track>" — record as a decision? Recommended: yes — override decisions belong in the decisions track (load-bearing architectural choice). Confidence: [high].`
- **options**: frozen — `yes` (write decision entry), `no` (proceed without recording; audit trail logged to stderr only).

On `yes`, invoke `flowctl memory add` with the override rationale piped via `--body-file -` stdin:

```bash
"$FLOWCTL" memory add \
 --track knowledge \
 --category decisions \
 --title "Override strategy: <track-name>" \
 --module strategy \
 --tags strategy-override \
 --body-file - <<EOF
## Problem
Spec <spec-id> contradicts active track "<track-name>" in STRATEGY.md.

## What was chosen
<concise summary of the override decision>

## Why
<rationale — why the override is the right call given current context>

## Track being overridden
- **<track-name>** (STRATEGY.md): "<canonical track wording>"
- **Spec direction:** "<contradicting wording>"

## Considered alternatives
- Aligning with the strategy track (rejected because: <reason>)
- Updating STRATEGY.md instead of overriding here (rejected because: <reason>)

## Consequences
- This spec ships in tension with track "<track-name>".
- A future `/flow-next:strategy` run should re-evaluate the track; this decision feeds that conversation.
EOF
```

On `no`, proceed without writing the decision. Log an audit-trail line to stderr:

```bash
# On no:
echo "[STRATEGY OVERRIDE]: track=\"<track-name>\" decision-not-recorded spec=<spec-id>" >&2

# On yes (decision was recorded):
echo "[STRATEGY OVERRIDE]: track=\"<track-name>\" decision-recorded=<entry-id> spec=<spec-id>" >&2
```

The audit trail line appears in both interactive (after the user picks) and autofix (when `OVERRIDE_STRATEGY=1` was passed) — it is the minimum durable record that an override happened, surfaceable in CI logs / git hook output later. In autofix mode (where the plain-text numbered prompt is unreachable), the decision-not-recorded variant fires unconditionally.

When `STRATEGY_PRESENT=false`, this entire section is a no-op — there's no strategy snapshot to contradict.

### 5.1 — Build the spec body

The spec body assembled in Phase 2 + revised in Phase 4 edit cycles is the input to `flowctl spec set-plan`. Source tags **stay in the spec body** — they are part of the audit trail and survive into the on-disk spec at `.flow/specs/<id>.md`. Future readers (including `/flow-next:plan` and `/flow-next:interview`) see the tags and can scrutinize.

The frontmatter top of the spec is whatever `flowctl spec create` writes (it generates a placeholder via the spec-create plumbing). `spec set-plan` overwrites the placeholder with the captured body — so the captured body should NOT include a duplicate `# <title>` heading; `set-plan` accepts the body as-is and atomic-writes to `.flow/specs/<id>.md`.

### 5.2 — New-spec branch

```bash
SPEC_TITLE="<chosen title from Phase 3 or Phase 1.3>"

# Create the spec — captures the JSON to extract the allocated id.
SPEC_OUTPUT=$("$FLOWCTL" spec create --title "$SPEC_TITLE" --json)
SPEC_ID=$(printf '%s' "$SPEC_OUTPUT" | jq -r '.id')

if [[ -z "$SPEC_ID" || "$SPEC_ID" == "null" ]]; then
 echo "Error: spec create failed: $SPEC_OUTPUT" >&2
 exit 1
fi

# Write the spec body via heredoc.
"$FLOWCTL" spec set-plan "$SPEC_ID" --file - --json <<EOF
$SPEC_BODY
EOF
```

Use a real heredoc (not `printf`) so embedded markdown formatting and newlines round-trip cleanly. `read_file_or_stdin` in `flowctl.py` handles `--file -` correctly.

### 5.3 — Rewrite branch

When `REWRITE_TARGET` is set:

```bash
SPEC_ID="$REWRITE_TARGET"

# Skip spec create — the spec already exists. Just overwrite the spec body.
"$FLOWCTL" spec set-plan "$SPEC_ID" --file - --json <<EOF
$SPEC_BODY
EOF
```

### 5.4 — Optional branch-name set

If the user named a feature branch in conversation (e.g. "let's call this branch `oauth-rate-limit`"), set it:

```bash
"$FLOWCTL" spec set-branch "$SPEC_ID" --branch "<slug>" --json
```

Skip silently if no branch was named — `spec create` already populated `branch_name` with the spec id, which is a fine default.

### 5.5 — Capture write failures

If `spec create` fails (e.g. `.flow/` corrupted, disk full): exit 1 with the error. The user has not yet committed anything.

If `spec set-plan` fails: the spec JSON sidecar exists but the markdown body is the placeholder. Surface the failure and the rollback option:

```text
Error: spec set-plan failed for <id>. The spec JSON sidecar was created but the
markdown body write failed. To roll back: rm .flow/specs/<id>.json .flow/specs/<id>.md
(or .flow/epics/<id>.json on alias-mode 0.x repos). Or re-run capture with
--rewrite <id> to retry the body write.
```

This mirrors the failure semantics in other flowctl commands — partial-state recovery is on the user, but the error is loud.

### 5.6 — No git commit from this skill

Capture **does not** stage or commit the new spec. The user owns when to commit. The output footer (Phase 6) tells them what to do.

Two reasons:

1. The captured spec often gets edited by `/flow-next:plan` immediately after — committing twice (once for capture, once after plan adds tasks) is noise.
2. Capture changes touch only `.flow/`; users sometimes want to bundle them with adjacent edits.

If a future enhancement adds a `--commit` flag, Phase 5 would gain a "stage + commit" branch, but the default stays "no commit, user owns the staging".

### Done when

- The new (or rewritten) spec is on disk at `.flow/specs/<id>.md`.
- `SPEC_ID` is known for Phase 6.
- Optional branch-name is set if user named one.

---

## Phase 6: Suggested next step (R16)

**Goal:** print the suggested next step. The deliverable is the new spec; this footer tells the user what to do with it.

```text
Spec captured at .flow/specs/<SPEC_ID>.md.

Next:
 /flow-next:plan <SPEC_ID> → research + break into tasks
 /flow-next:interview <SPEC_ID> → refine via Q&A
```

### Biz-suggestion footer (R25)

When the conversation has business-context signals but the business layer is sparse, append a one-line suggestion to refine via `/flow-next:interview --scope=business`. The fire/no-fire decision is delegated to `flowctl scope suggest` (T1) — the skill MUST NOT re-implement the `1 <= N < 3` threshold math inline (skill-vs-flowctl architectural rule from `CLAUDE.md`). Input is `$BIZ_SIGNAL_CATEGORIES` — the count computed in [§2.6](#26--biz-context-signal-routing-r24--signal-category-count-for-r25) over the nine SIGNAL CATEGORIES from R24 (target user / problem framing / success metric / MVP boundary / business constraints / what-not-to-build / prioritization rationale / business risks / UX expectations). The count is over categories, not over markdown destinations.

```bash
# `scope suggest` plain-mode exit codes: 0 = fire, 1 = no-fire. Quiet stdout (`>/dev/null`)
# keeps the shell branch token-free; `--json` is available when richer output is needed.
# Threshold (`1 <= N < 3`) lives in flowctl — capture passes the count, flowctl decides.
# R22 invariant: BIZ_SIGNAL_CATEGORIES=0 → no-fire (exit 1), keeping the solo-dev
# zero-flag default silent.
if "$FLOWCTL" scope suggest --signal-categories-count "$BIZ_SIGNAL_CATEGORIES" >/dev/null; then
 cat <<EOF

This conversation has business-requirements signals; consider
\`/flow-next:interview --scope=business $SPEC_ID\` to deep-refine the
business layer.
EOF
fi
```

The literal suggestion phrasing matches the R25 spec verbatim ("business-requirements signals; consider `/flow-next:interview --scope=business <spec-id>`") so the surface text stays generic — capture does not enumerate which categories triggered the suggestion. Informational only — never a plain-text numbered prompt.

If Phase 4 surfaced 8+ acceptance criteria AND the user picked `approve` (not `consider-split`), append:

```text
Note: this spec has <N> acceptance criteria — /flow-next:plan can stage the
breakdown into multiple sub-specs if needed.
```

If Phase 0.3 found memory hits, append the related-context footer:

```text
Related context (existing memory): <comma-separated entry ids>
Consider reviewing before /flow-next:plan to avoid re-solving documented problems.
```

If `REWRITE_TARGET` was set, the footer prefix changes:

```text
Spec rewritten at .flow/specs/<SPEC_ID>.md.

Next:
 /flow-next:plan <SPEC_ID> → re-plan tasks (existing tasks under the spec
 may need /flow-next:sync to align)
 /flow-next:interview <SPEC_ID> → refine via Q&A
```

### Done when

- Footer is printed.
- Skill exits 0.

---

## Manual smoke (acceptance R3, R4, R5, R6, R7, R8, R24, R25)

The skill itself is markdown — there's no unit-test surface. The validation is invoking `/flow-next:capture` in a real session. Expected behavior:

- Phase 0 walks `.flow/specs/` and the legacy `.flow/epics/` alias dir, runs memory search if memory is initialized, detects compaction, applies idempotency. Branches into duplicate-detection question if ≥2 strong matches; exits cleanly on `abort`.
- Phase 1 emits a `## Conversation Evidence` block with verbatim user quotes (≤30 lines).
- Phase 2 produces a draft with per-line source tags. Every acceptance criterion has one of `[user]` / `[paraphrase]` / `[inferred]`. Biz-context signals (R24) route to their destinations using only `[user]` / `[paraphrase]` tags; categories without conversation signal leave their destinations absent. `BIZ_SIGNAL_CATEGORIES` (0..9) computed for Phase 6.
- Phase 3 fires must-ask cases only when (a) title is genuinely ambiguous, (b) acceptance is untestable, (c) scope-conflict persists. Optional ambiguities are deferred to Phase 4.
- Phase 4 read-back surfaces `[inferred]` count, 8+ split note (if applicable), related-memory footer (if applicable). Interactive: user picks approve / edit / abort. Autofix: print + require `--yes`.
- Phase 5 calls `flowctl spec create` + `spec set-plan` via heredoc.
- Phase 6 prints the next-step footer. Calls `flowctl scope suggest --signal-categories-count "$BIZ_SIGNAL_CATEGORIES"`; on exit 0 (fire), appends the R25 `/flow-next:interview --scope=business` suggestion line. R22 invariant: `BIZ_SIGNAL_CATEGORIES=0` → no-fire → no suggestion.

In autofix without `--yes`, the draft prints and the skill exits 0 — no write, no spec allocated.
In autofix with `--yes`, Phase 4 still prints the draft (substituting for read-back) before Phase 5 writes.

The Ralph-block (SKILL.md) ensures this skill never runs under `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` — capture requires a user at the terminal.
