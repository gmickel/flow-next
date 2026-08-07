# /flow-next:capture workflow

Execute these phases in order. Each gates on the prior. Stop on user-blocking error — never plow through with bad state.

## Preamble

```bash
set -e
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SPECS_DIR="$REPO_ROOT/.flow/specs"
TODAY="$(date -u +%Y-%m-%d)"
```

`jq` and `python3` (or `python`) must be on PATH. Mode + flags come from the SKILL.md mode-detection block (`MODE` = `interactive` | `autofix`, plus `REWRITE_TARGET`, `FROM_COMPACTED_OK`, `COMMIT_YES`).

If `.flow/` does not exist, print `No .flow/ directory — run \`$FLOWCTL init\` first.` and exit cleanly. Capture has nothing to write into.

**ONE root config snapshot for the whole capture run (fn-110)** — take it once after `.flow/` is confirmed, then derive every later leaf (including the Phase 5.2 mint gate) via `jq` from that file. No further root `config get` on the capture path for values already in the snapshot. Path-persistence: compose a literal path with an agent-chosen 4-char suffix and type it verbatim:

```bash
CAPTURE_CFG="${TMPDIR:-/tmp}/flow-capture-config-<suffix>.json" # literal path
"$FLOWCTL" config get --json > "$CAPTURE_CFG" 2>/dev/null || printf '{"key":null,"value":{}}' > "$CAPTURE_CFG"
```

The Ralph-block (SKILL.md) runs before this preamble. Phase 0 starts after the Ralph-block and the preamble.

---

## Phase 0: Pre-flight (R5, R6, R8)

**Goal:** catch the three conditions that make capture unsafe BEFORE drafting a spec — duplicate specs, incomplete relevant evidence after compaction, idempotency conflict. Each has its own decision branch.

### 0.1 — Extract candidate keywords from conversation

Capture's input is the conversation, not `$ARGUMENTS`. Walk the visible user turns and pull:

- **Proper nouns** — capitalized terms used at least twice, excluding sentence-start common words.
- **File paths** — anything matching `[\w./_-]+\.(py|ts|tsx|js|md|json|sh|toml|yaml|yml)` or starting with `src/`, `plugins/`, `scripts/`, `.flow/`.
- **Domain-specific terms** — multi-word phrases the user repeated (e.g. "rate limiter", "OAuth callback", "review walkthrough").
- **Quoted phrases** — anything the user put in `"..."` or `\`...\`` while describing the feature.

Cap the candidate keyword list at the top **10** by frequency. These feed both 0.2 (spec title overlap) and 0.3 (memory search). Strip ordinary English connectors (`the`, `a`, `and`, `or`, `to`, `for`, `with`, `via`).

### 0.2 — Duplicate detection: spec title overlap

Scan `.flow/specs/*.json` for title overlap. (Pre-1.0 `.flow/epics/` repos: port first per `.flow/usage.md` "Pre-1.0 layout porting".)

```bash
shopt -s nullglob
SPEC_FILES=( "$SPECS_DIR"/*.json )
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

Scan the visible conversation for compaction signals:

- Literal `[compacted]` markers.
- Truncated tool-result patterns: `<...output too large to include>`, `(output truncated)`, `... (N more lines)`.
- System-summary blocks (e.g. "Earlier in the conversation, the user...").
- Suspicious gaps where a prompt turn shows no output but later turns reference its result.

These signals are **advisory, not an automatic refusal**. A conversation may have been compacted earlier while the feature or decision being captured is fully present in later visible user turns. A historical system-summary block, `[compacted]` marker, or unrelated truncated tool result alone does not make the capture source incomplete.

For each signal, judge whether it removed evidence **relevant to this capture**:

- **Proceed normally** when the requested feature / decision is fully stated or fully restated in visible user turns, including when those turns occur after the latest compaction. Record `Prior compaction detected; relevant capture evidence remains visible.` in the Phase 4 read-back warnings.
- **Treat evidence as incomplete** when a relevant requirement exists only in a system summary, a relevant user turn or tool result is truncated / missing, later turns depend on a relevant unavailable result, or the evidence block cannot support the draft without guessing what disappeared.
- When uncertain whether a gap is relevant, treat the evidence as incomplete. `--from-compacted-ok` is the explicit user override for that uncertainty.

If relevant evidence is incomplete AND `FROM_COMPACTED_OK` is `0`, refuse:

```text
Error: relevant conversation evidence appears incomplete after compaction
(detected: <markers and relevant gaps>). Capture refuses to synthesize while
requirements needed for this spec may be missing.

Options:
 - Restate or restore the missing relevant requirements in visible user turns.
 - Re-run with --from-compacted-ok if you've verified the remaining context
 contains the full intent despite the identified gaps.
```

In **autofix mode**, exit 2. In **interactive mode**, this is a hard refusal — capture does not offer to "ask the user to confirm anyway" (the user can restate the missing material or re-invoke with the flag if they trust the transcript).

If no compaction signal is detected, or signals exist but the relevant evidence remains fully visible, proceed to 0.5.

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

### 0.5b — Chart briefing admission (fn-135)

When the conversation or `$ARGUMENTS` names a chart briefing input — a path matching `.flow/charts/*-briefing*.md`, an explicit B-ID (`B1`, `B2`, …), or a chart id whose sidecar lists briefings — resolve it before drafting:

```bash
# Example probes (agent-owned paths; type literal paths, never shell vars across prompt turns):
# Read the briefing markdown, and the chart sidecar for status of that B-ID:
# .flow/charts/<chart-id>.json -> briefings[].id / .status (final|draft|stale)
# .flow/charts/<chart-id>-briefing.md
# .flow/charts/<chart-id>-briefing-<k>.md # multi-cluster
```

**Refuse (ordinary capture, fail closed):**

- Briefing `status: draft` (forced incomplete briefing) — never treat a forced draft as final.
- Briefing `status: stale` (after `chart reopen` or supersession of linked D-IDs).

```text
Error: chart briefing <B> is <draft|stale> and is refused for ordinary capture.
Unresolved / invalidated items: <named D-IDs or parked questions from the briefing>.
A forced draft can never be promoted to final.

To proceed anyway, re-run with an explicit risk override that names those D-IDs;
capture will read back the risk and still leave the briefing draft/stale in provenance.
```

**Explicit risk override:** the user must name the unresolved or invalidated D-IDs. The agent reads back the exact risk (print-then-ask) before any write. The override never rewrites the briefing status to final and never erases the draft/stale flag from evidence recorded in the spec.

**Decline** (user aborts): record nothing in `produced_specs[]`; the chart remains resumable.

When no chart briefing is in play, this step is a silent no-op.

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
- Spec-title overlap scan ran (`.flow/specs/`); matches recorded.
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

When the conversation references repo files or modules whose state matters for the spec ("the auth module needs X", "we already have a rate limiter at..."), spawn a **read-only investigation subagent** via the `Task` tool with `subagent_type: Explore` (or `general-purpose` when Explore is unavailable; on hosts with neither builtin — e.g. Cursor — the host's generic subagent dispatch with Edit/Write disallowed). For clean conversations with no file references, skip this step. ( per repo cross-platform convention.)

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

### 1.2b — Chart briefing evidence (when admitted)

When Phase 0.5b admitted a chart briefing (final, or draft/stale under explicit risk override), extract into the evidence surface (and later into `## Decision Context` / evidence sections of the draft):

- Chart id, B-ID, cluster key (if multi-spec / cluster file), briefing path(s).
- Each cluster D-ID with title, gist, and record link from the briefing.
- Shared-context D-IDs (attributable evidence; not automatic acceptance requirements).
- Approved asset references (kind/reference/display) listed on those decisions.
- If override: the named unresolved/invalidated D-IDs and the risk read-back text.

These are **structural evidence references**. Do **not** attach acceptance-criterion source tags (`[user]` / `[paraphrase]` / `[inferred]` / `[strategy:<track>]`) to D-ID lines, chart facts, assets, or briefing membership. Preserve them as navigable links.

Also check for an already-linked identity (retry recovery):

```bash
# From chart sidecar produced_specs[]: match briefing + cluster (+ optional spec).
# If a linked entry already exists for this B-ID+cluster, record SPEC_ID_EXISTING
# and skip minting a duplicate in Phase 5 — link-spec the existing spec instead.
```

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

The canonical section structure lives in [`plugins/flow-next/templates/spec.md`](../../templates/spec.md) — the single source of truth for the section sequence and per-section ownership annotations (per R17 — never re-embed the section list inline; cross-link the template). At runtime the template is resolved via the 4-tier discovery cascade (first match wins): `<repo_root>/SPEC.md` → `<repo_root>/spec.md` → `.flow/templates/spec.md` → bundled `${PLUGIN_ROOT}/templates/spec.md`. The bundled file is the canonical source of truth; earlier tiers are user-customized overrides. Walk the resolved template in its declared order and draft each section's body using the source-tag conventions below. Before any template section, prepend `## Conversation Evidence` (Phase 1 output verbatim); after the template, append `## Requirement coverage` (the R-ID → task mapping placeholder).

Source-tag application is per-tag, not per-section — and **only on content capture newly authors**:

- **`[user]`** dominates where the conversation gave verbatim content (goal framing, user-stated acceptance, named non-goals, rejected alternatives the user surfaced).
- **`[paraphrase]`** is for spec-language restatements of user intent — preserving meaning, tightening wording.
- **`[inferred]`** covers agent fill-in for completeness (default conventions: error formats, retry policies, observability hooks, file / component refs the user did NOT name). **Untouched by §2.6 biz-routing** — biz destinations only accept `[user]` / `[paraphrase]`.
- **`[strategy:<track>]`** activates only when Phase 0 strategy snapshot was populated.

**Chart provenance separation (fn-135 / R49):** chart decision provenance is structural (D-ID, answer gist, assets, briefing membership). Preserve those as evidence links in `## Decision Context` (and conversation-evidence footnotes). Never source-tag D-ID evidence. Never retag an existing criterion authored by an earlier pass. A criterion derived from an unattended resolved D-ID is **not** automatically `[user]` — apply the four-tag grammar only to acceptance criteria this capture pass newly authors, judged against conversation + briefing context. Shared-context D-IDs do not become duplicated acceptance requirements across output specs unless each target's read-back independently confirms that guarantee. **No verified/inferred fact or decision grammar** (fn-148 closed STOPPED with no verdict — licenses nothing here).

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
- When `.flow/criteria.md` exists, do not restate its standing criteria (G-IDs) as R-IDs - completion review already judges every G-ID against the spec. Reference a relevant G-ID in prose when useful; write an R only for what this spec adds beyond the standing rule.

### 2.4 — Acceptance-criterion testability check

Every acceptance criterion must be testable in principle. As you draft each one, ask:

- Could a reviewer point at code / behavior / config and say "this is satisfied" or "this is not"?
- Is the criterion specific enough that two engineers would agree on satisfaction?

If a candidate criterion fails the test (e.g. "make it fast", "improve UX"), it triggers Phase 3 must-ask case (b). Either the user clarifies (interactive), or autofix exits 2.

Track `[inferred]` count across all sections (especially in `## Acceptance Criteria` and `## Boundaries`). The count surfaces at Phase 4 read-back.

### 2.5 — Spec-count heuristic (R11): how many specs is this?

Epics, briefing packages, and multi-feature requests arrive as one conversation but often land best as 1..n specs. After drafting the criteria, judge the count:

**Tripwire (when to compute):** 8+ acceptance criteria, OR the criteria visibly serve more than one independently shippable outcome. Below the tripwire, skip this section entirely — normal captures see nothing.

**Counting rule:** count business and technical requirements only. Standing criteria (G-IDs from `.flow/criteria.md`) and process requirements (tests green, docs updated, mirror synced) never count — they ride along with any spec.

**Split criterion — independence, not size.** The count trips the check; the partition comes from shippability:

- Would a stakeholder accept this cluster of criteria on its own?
- Do the clusters touch disjoint surfaces?
- Does one cluster depend on infrastructure another builds? A dependency seam is a natural spec boundary.

A large-but-cohesive set (12 criteria, one subsystem, one outcome) is ONE spec — say so in the read-back note and move on. Never pad N to look thorough.

**When the partition yields N>1, compute `SPLIT_PROPOSAL`:** per proposed spec — a short title, the criteria allocated to it, and the dependency edges between the proposed specs (`B depends on A`). Each proposed spec must be self-contained and independently reviewable; one spec = one PR = one completion review judging every R-ID, which is why oversized specs degrade review quality.

The proposal surfaces at the Phase 4 read-back (allocation printed in full, one-line note in the ask). The skill **never auto-splits** — the user decides.

### 2.6 — Biz-context signal routing (R24) + signal-category count for R25

While drafting §2.2's sections, walk the Phase 1 `## Conversation Evidence` block looking for explicit business-context signals across **nine SIGNAL CATEGORIES** (the counting unit for R25's sparse-suggestion heuristic). For each category that has at least one explicit signal in conversation, route the content to its destination using only `[user]` or `[paraphrase]` source tags. This is the full routing table (the single copy — it lives here, beside the drafting step that consumes it):

| # | Signal category | Destination(s) | Trigger phrasing in conversation |
|---|-----------------|----------------|-----------------------------------|
| 1 | Target user / persona | `Goal & Context` | "for X users", "the operator does Y", "junior devs need…" |
| 2 | Problem framing / why-now | `Goal & Context` | "the pain is X", "this came up because Y", "we need this because…" |
| 3 | Success metrics / definition of done | outcome-AC (`Acceptance Criteria`) **and** `## Decision Context > ### Motivation` | "we win if X", "good enough means Y", "the metric is…" |
| 4 | MVP scope / "not doing X yet" | `Boundaries` | "MVP is just X", "not Y yet", "ship narrow first" |
| 5 | Business constraints (regulatory, deadlines, budget) | `Goal & Context` OR `## Decision Context > ### Motivation` (pick whichever is most coherent in context — usually `Goal & Context` for context-setting constraints; `Motivation` when the constraint is the reason for the trade-off) | "GDPR requires", "deadline is Q3", "no infra spend", "EU-resident-only" |
| 6 | What NOT to build / non-goals | `Boundaries` | "definitely NOT X", "out of scope", "don't want Y" |
| 7 | Prioritization rationale | `## Decision Context > ### Motivation` | "more important than X", "we'd rather Y over Z", "speed beats robustness here" |
| 8 | Business risks | `Goal & Context` OR `## Decision Context > ### Motivation` (same disambiguation as constraints) | "if this leaks we lose X", "reputational damage", "can't roll back" |
| 9 | UX expectations | `Goal & Context` | "errors should be friendly", "loading must feel instant", "accessibility floor" |

Rules:

- **Source tags restricted to `[user]` or `[paraphrase]`** for biz-routed content. `[inferred]` never routes to a business destination. If a category has no conversation signal, its destination(s) receive no new content — sections without conversation signal stay absent (no empty-section auto-populate; this is the R22 invariant).
- **One signal can land in multiple destinations** (e.g., a success metric becomes both an outcome-AC R-ID and a `### Motivation` rationale entry) — that still counts as **one** SIGNAL CATEGORY for the R25 threshold. Counting is over R24's nine categories, not over markdown destinations.
- **Categories 1, 2, 9 (target user / problem framing / UX) collapse into `Goal & Context` prose.** Per-line tags inside the narrative are not required, but the section-level tag breakdown (e.g., `<!-- Goal & Context: 80% [user], 20% [paraphrase] -->`) must reflect them.
- **Category 4 ("MVP scope / not doing X yet") and Category 6 ("what NOT to build") both route to `Boundaries`** but stay counted separately for R25 (different signal-source patterns: "MVP is narrow" vs "definitely not X").
- **Decision Context substructure** — capture only ever writes fresh specs (never a rewrite of an existing FLAT body), so there is no FLAT→substructured promotion to handle here (that's `/flow-next:interview`'s merge contract). Decision rule for capture: when category 3, 5, 7, or 8 routes content, write `## Decision Context` as SUBSTRUCTURED — emit the `### Motivation` H3 with the routed content. Leave `### Implementation Tradeoffs` absent (do NOT write the `*Pending technical-scope interview pass.*` placeholder; that's `/flow-next:interview --scope=business`'s responsibility on a rewrite, not capture's). When none of categories 3, 5, 7, 8 carry content, write `## Decision Context` as FLAT — preserves R22 (solo dev with zero biz signals sees no Motivation/Implementation Tradeoffs scaffolding) and matches the canonical template's "(A) FLAT (default, R22 backward-compat)" branch.
- **Constraints / risks (categories 5, 8) pick one destination per signal** — `Goal & Context` when the constraint sets up framing, `### Motivation` when it's the reason behind a trade-off. Don't double-route to both for the same signal.

After §2.2's section drafting completes, compute `BIZ_SIGNAL_CATEGORIES` — the count of distinct categories (out of nine) that received at least one `[user]` or `[paraphrase]` line. This count is Phase 6's input to the R25 fire/no-fire judgment (agent-owned; no flowctl helper):

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

### 2.7 — New-vocabulary scan (glossary term-add proposals)

Capture joins `/flow-next:interview` as a glossary writer. Gate first — same husk-aware autodetect as interview's doc-aware mode (`total_terms`, never `[[ -f ]]` — a `# Glossary` husk must not open the gate):

```bash
GLOSSARY_TERMS=$("$FLOWCTL" glossary list --json 2>/dev/null | jq -r '.total_terms // 0')
```

- `GLOSSARY_TERMS == 0` (absent, husk, or flowctl error) → **silent skip**: `GLOSSARY_PROPOSALS` stays empty, nothing downstream changes. Bootstrap is `/flow-next:prime`'s job, never capture's.
- `GLOSSARY_TERMS > 0` → scan the conversation evidence for genuinely NEW project vocabulary. A term qualifies when ALL hold:
 1. **Used repeatedly** — appears in ≥2 user turns (or once + load-bearing for an acceptance criterion).
 2. **Project-specific** — a coined noun / flow / distinction, not generic English ("receipt gate" yes; "function" no).
 3. **Absent from the glossary** — no existing entry matches on `term` or `avoid` aliases (case-insensitive, whitespace-collapsed — the `_glossary_term_matches` contract; do not reinvent matching logic).

Collect at most **5** proposals (`GLOSSARY_PROPOSALS`), each with a one-line definition drawn from how the user actually used the term. Proposals surface at Phase 4 read-back; writes happen only in Phase 5.8 after consent.

### Done when

- Every section is drafted with source tags applied.
- R-IDs are allocated sequentially.
- `[inferred]` count is computed.
- 8+ acceptance count flag set if applicable.
- Untestable acceptance candidates flagged for Phase 3 must-ask.
- `BIZ_SIGNAL_CATEGORIES` (0..9) computed for Phase 6 R25 dispatch.
- `GLOSSARY_PROPOSALS` collected (≤5; empty when the glossary gate is closed).

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

### 4.1 — Materialize the draft + print-then-ask emission

**Path-persistence rule:** bash vars do NOT survive across prompt turns — and that applies to the draft path itself. Compose a **literal unique path in agent context** — `${TMPDIR:-/tmp}/flow-capture-draft-<working-title-slug>-<agent-chosen 4-char suffix>.md` — and use that literal path verbatim in the Write call here AND in Phase 5's `spec set-plan <id> --file <path>` call. Never carry the path in a shell variable across prompt turns; `mktemp` is reserved for paths created and consumed within a single bash block. (No spec id exists yet on the new-spec branch — the working-title slug keeps the path readable; uniqueness comes from the suffix.)

Write the full draft to that path via the **Write tool** — exactly once (the file is what Phase 5 hands to `spec set-plan --file`; do NOT re-author it into a Phase-5 heredoc). The Write is plumbing, not the user-facing read-back.

The **draft file** contains the spec body (what `spec set-plan` consumes — no duplicate `# <title>` heading, per §5.1):

1. The `## Conversation Evidence` block (Phase 1).
2. Every section drafted in Phase 2, with source tags visible.
3. The `## Acceptance Criteria` R-ID list — bulleted, source tags shown.

**Print-then-ask contract (interactive — R13):** question bodies render as collapsed plain text (no markdown, no newlines) on every host, so multi-paragraph drafts/diffs/criteria lists inside `plain-text numbered prompt` are unreadable. Skills that show a draft/diff for approval MUST:

1. **Print the FULL draft markdown as an ordinary assistant message FIRST** (the user-visible read-back — real markdown, real newlines). When `REWRITE_TARGET` is set, also print the existing → proposed **diff** (unified style; changed sections in full) as ordinary markdown in the same message or a second message immediately after the draft — never only inside the ask.
2. **Then** issue a **short** `plain-text numbered prompt` whose body is only: one-line pointer to the printed draft above + compact `[inferred]` tally / warnings + recommendation + options. **Never embed multi-paragraph drafts, diffs, or criteria lists in the ask body.**

The **summary payload** (metadata about the draft — never a re-emission of it) is what rides in the short ask (interactive) or prints to stdout (autofix):

1. `title` + candidate `branch_name`.
2. **Source-tag tally** — compact one-liner. Format:
 ```
 Source: [user] N · [paraphrase] M · [strategy] K · [inferred] L
 ```
 Optional one-line per-section `[inferred]` breakdown when L > 0 (keep short — tallies, not the criteria prose):
 ```
 [inferred] count: 7 total (Architecture 3 · API 2 · Boundaries 2)
 ```
 The `[strategy]` count aggregates all `[strategy:<track>]` lines regardless of track. When Phase 0 strategy snapshot scanned `none` (`STRATEGY_PRESENT=false`), `[strategy] K` reads `[strategy] 0` (or the field is omitted entirely — equivalent in practice).
3. **Spec-count note** (if Phase 2.5 fired) — one short clause, e.g. `11 criteria across 2 independent outcomes — split proposed, allocation printed above.` or `12 criteria, one cohesive outcome — single spec recommended.` When `SPLIT_PROPOSAL` has N>1, the printed read-back message (Step A) includes the full proposal block after the draft: per-spec titles, allocated criteria, dependency edges.
4. **Related context** footnote (if Phase 0.3 found memory hits) — one short clause, e.g. `Related memory: bug/runtime-errors/oauth-callback-2025-08-12.`
5. **Rewrite-mode pointer** (if `REWRITE_TARGET` is set) — one short clause, e.g. `Rewrite diff printed above.` (the full diff is already in the ordinary message; never paste it into the ask).
6. **Glossary term-add proposals** (only when Phase 2.7 collected any) — compact one-liner of term names; full definitions live in the printed draft message (or a short glossary block printed above the ask), never multi-paragraph in the ask body:
 ```
 New glossary terms proposed: <term>, <term> (definitions in draft above).
 ```

### 4.2 — Interactive read-back

**Step A — print first.** Emit the full draft markdown (and rewrite diff when applicable) as an ordinary assistant message. Full criteria, source tags, and section bodies live here — never only inside the ask.

**Step B — short ask.** Use `plain-text numbered prompt`:

- **header**: `Read-back`
- **body** (SHORT — pointer + tally/warnings + recommendation only; no multi-paragraph content):
 1. One-line pointer: `Full draft printed above.` (rewrite: `Full draft + rewrite diff printed above.`)
 2. Compact summary payload from §4.1 (source-tag tally, 8+ note, related-memory footnote, rewrite pointer, glossary term names) — tallies and one-liners only.
 3. **The recommendation — no self-blessing rule (overrides lead-with-recommendation):** when the draft carries ≥1 `[inferred]` item, do NOT recommend approve — the agent never pre-blesses its own guesses. Lead neutrally instead: `Recommended: check the <N> guessed item(s) marked [inferred] in the draft above before choosing — approve only if they match your intent. Confidence: [<tier>].` Only a zero-`[inferred]` draft may carry `Recommended: approve — <one-sentence rationale>. Confidence: [<tier>].`
- **options** (frozen — each description states its consequence in plain words, "Choose this if…"):
 - `approve` — proceed to Phase 5 write as ONE spec ("this becomes the spec and work can start from it")
 - `split-as-proposed` (only when Phase 2.5 proposed N>1) — Phase 5 runs the create ceremony once per proposed spec and records the dependency edges (§5.2b); "you get N linked specs exactly as printed above"
 - `edit` — revise specific sections (loops back to Phase 2 for those sections)
 - `abort` — exit 0, no write ("draft is thrown away, nothing saved")

 When a `SPLIT_PROPOSAL` with N>1 exists, the recommendation may lead with `split-as-proposed` — proposing structure is not self-blessing content (the no-self-blessing rule above still governs `[inferred]` content): `Recommended: split-as-proposed — <N> independently shippable outcomes (allocation printed above). Confidence: [<tier>].`

Confidence tier (attaches to whichever recommendation the rule above produced):

- `[high]` — `[inferred]` count is low (≤2) and no user-facing claims contradict the conversation evidence.
- `[judgment-call]` — `[inferred]` count is moderate (3-6) or some `[inferred]` items are load-bearing (e.g. core acceptance criteria).
- `[your-call]` — `[inferred]` count is high (7+) or rewrite-mode with substantive divergence from existing spec.

**Never** put full criteria lists, section bodies, unified diffs, or multi-paragraph glossary definitions in the ask body — they render as collapsed plain text. The printed message is the ratification surface.

**Glossary term-add consent (only when `GLOSSARY_PROPOSALS` is non-empty AND the user picked `approve`).** One follow-up question via `plain-text numbered prompt` — the read-back options above stay frozen; this is a separate ask (short — definitions already printed above if present):

- **header**: `Glossary?`
- **body**: `Add <N> new term(s) to GLOSSARY.md? <comma-separated terms>. Definitions in the draft printed above. Recommended: add — they surfaced repeatedly in this conversation. Confidence: [judgment-call].`
- **options**: `add-all`, `pick` (follow-up multi-select / serial yes-no per term), `skip`

Record the approved subset for Phase 5.8. `skip` → no glossary writes; the spec write proceeds regardless of this answer.

**Mark-ready consent (only when the user picked `approve` AND the target-aware readiness predicate holds).** Probe only after `approve`, before any Phase 5 write changes the rewrite target's state:

```bash
READY_STATE=""
READY_ADOPTED=0
REWRITE_WAS_READY=false
READINESS_PROBES_OK=true

READY_STATE_RAW=$("$FLOWCTL" config get tracker.readyState --json 2>/dev/null) || READINESS_PROBES_OK=false
if [[ "$READINESS_PROBES_OK" == true ]]; then
 READY_STATE=$(printf '%s' "$READY_STATE_RAW" | jq -r '.value // empty' 2>/dev/null) || READINESS_PROBES_OK=false
fi

READY_SPECS_RAW=$("$FLOWCTL" specs --json 2>/dev/null) || READINESS_PROBES_OK=false
if [[ "$READINESS_PROBES_OK" == true ]]; then
 READY_ADOPTED=$(printf '%s' "$READY_SPECS_RAW" | jq '[.specs[] | select(.ready == true)] | length' 2>/dev/null) || READINESS_PROBES_OK=false
fi

if [[ -n "$REWRITE_TARGET" && "$READINESS_PROBES_OK" == true ]]; then
 REWRITE_RAW=$("$FLOWCTL" show "$REWRITE_TARGET" --json 2>/dev/null) || READINESS_PROBES_OK=false
 if [[ "$READINESS_PROBES_OK" == true ]]; then
 REWRITE_WAS_READY=$(printf '%s' "$REWRITE_RAW" | jq -r '.ready // false' 2>/dev/null) || READINESS_PROBES_OK=false
 fi
fi

READY_OFFER=false
if [[ "$READINESS_PROBES_OK" == true && -z "$READY_STATE" ]]; then
 if [[ -n "$REWRITE_TARGET" ]]; then
 [[ "$REWRITE_WAS_READY" == true ]] && READY_OFFER=true
 elif [[ "$READY_ADOPTED" =~ ^[0-9]+$ && "$READY_ADOPTED" -ge 1 ]]; then
 READY_OFFER=true
 fi
fi
# Probe failures degrade to READY_OFFER=false (don't offer).
```

The shared tracker gate must hold, then the branch-specific gate applies:

- `READY_STATE` empty — `tracker.readyState` is NOT configured. Readiness is a one-way tracker→local pull when the tracker is authoritative; never invite a local edit the next sync would silently revert.
- **New capture:** offer only when `READY_ADOPTED >= 1`. Readiness is adopted in this repo (≥1 spec already marked ready). First adoption enters via `flowctl spec ready`, the tracker ceremony, or prime — never via this prompt. Non-adopters see no question anywhere (R7-style invisibility).
- **Rewrite:** offer only when `REWRITE_WAS_READY` is `true`. For a rewrite, an unrelated ready spec never triggers this question. The question is consent to restore the target's own readiness after §5.3 resets it; a draft target remains a draft without another interruption.

When `READY_OFFER=true`, one follow-up question via `plain-text numbered prompt` — the read-back options above stay frozen; this is a separate ask (same shape as the glossary consent):

- **header**: `Mark ready?`
- **body, new capture**: `Make this new spec eligible for Pilot or another autonomous driver once written? Readiness is adopted in this repo (<READY_ADOPTED> ready spec(s)). Recommended: keep-draft — choose mark-ready only when you want autonomous execution eligibility now. Confidence: [judgment-call].`
- **body, rewrite**: `Rewriting <REWRITE_TARGET> resets its readiness. Mark it ready again after writing the approved revision so Pilot or another autonomous driver may select it? Recommended: keep-draft — choose mark-ready only when you want autonomous execution eligibility now. Confidence: [judgment-call].`
- **options** (frozen): `mark-ready` (Phase 5.9 runs `spec ready` after the write), `keep-draft` (default — no readiness write)

Record the answer for Phase 5.9. `keep-draft` → no readiness write; the spec write proceeds regardless of this answer.

### 4.3 — Edit branch

If user picks `edit`:

- Ask which sections (offer multi-select if the platform supports it; otherwise serial single-select).
- For each section, re-run Phase 2's drafting logic for that section only, with the user's correction context as additional input.
- Apply the revisions to the §4.1 draft file via the **Edit tool** (deltas only — never rewrite the whole file via Write).
- Re-tally `[inferred]` count.
- **Print-then-ask again:** **Read the FULL draft file**, then **print the full revised draft as an ordinary assistant message** (one full emission per edit cycle — the Edit render shows only the delta and is NOT a full read-back). The full-file Read also satisfies the Edit tool's read-before-edit requirement for the next cycle.
- Re-issue the short §4.2 ask (pointer + tally + options only). Loop until user picks `approve` or `abort`.

Hard cap at **3 edit cycles**. If the user is still editing on the 4th cycle, surface: `You've gone through 3 edit cycles. Capture's read-back loop isn't deep refinement — consider /flow-next:interview <id> after capture lands for iterative Q&A.` Offer `approve as-is` / `abort` only (still print the current draft first if it changed).

### 4.4 — Autofix read-back

Autofix paths are unchanged by the interactive print-then-ask contract (no user to ask). The §4.1 Write materializes the draft file; print the **summary payload** (§4.1 items — tally, 8+ note, related memory, rewrite diff, glossary suggestions) to stdout. Then:

- If `COMMIT_YES=0`, exit 0 with: `Draft written to <literal draft path> (content in the Write render above). Re-run with --yes to commit (in autofix mode, --yes substitutes for the interactive read-back approval).`
- If `COMMIT_YES=1`, proceed to Phase 5.

Autofix never offers `edit` — there's no user to ask. The Write + `--yes` pattern mirrors `flowctl memory migrate --yes` and is the documented autofix-substitute for read-back approval.

**Autofix + split proposal:** autofix never multiplies artifacts. When Phase 2.5 proposed N>1, autofix writes ONE spec and records the proposal inside it — `## Decision Context` gains an `### Split proposal (unactioned)` H3 carrying the per-spec titles, criteria allocation, and edges — plus a one-line stdout note: `Split proposal (N specs) recorded in Decision Context — act on it via /flow-next:interview <id> or manual spec create + add-dep.`

**Autofix + glossary proposals:** the summary payload's glossary block prints as suggestions (`Suggested glossary adds — review and add via flowctl glossary add "<term>" --definition-file -`), but autofix **never writes terms** — not even with `--yes` (`--yes` consents to the spec write, not to vocabulary changes). Phase 5.8 is interactive-only.

**Autofix + readiness:** autofix **never writes readiness** — not even with `--yes` (Phase 5.9 is interactive-only). When the §4.2 target-aware predicate yields `READY_OFFER=true` AND the spec gets written (`--yes`), Phase 6 appends a one-line suggestion: `Mark ready when blessed: flowctl spec ready <SPEC_ID>`. Without `--yes` nothing is suggested (no spec id exists). Predicate fails → silence — including non-adopters, tracker-authoritative repos, and draft rewrite targets made visible only by an unrelated ready spec.

### 4.5 — Forbidden in Phase 4

- **Never silently skip the read-back.** Even if `[inferred]` count is 0, interactive mode prints the full draft then asks; autofix still materializes the draft file before any `.flow/` write. The user might still want to reject for reasons unrelated to inference.
- **Never embed multi-paragraph drafts, diffs, or criteria lists in the `plain-text numbered prompt` body.** Print-then-ask only (R13).
- **Never auto-split.** N specs are written only through the user picking `split-as-proposed`; `approve` writes exactly one spec, and autofix never splits (§4.4).
- **Never edit `--rewrite` target without printing the diff** as ordinary markdown before the short ask. The diff is non-optional in rewrite mode.
- **Never write glossary terms here.** Phase 4 collects consent only; the writes happen in Phase 5.8, after the spec write.
- **Never write readiness here.** Phase 4 collects the mark-ready consent only; the write happens in Phase 5.9, after the spec write. Never offer the question outside the target-aware predicate: no `tracker.readyState`, plus adopted local readiness for a new capture or an already-ready target for a rewrite.

### Done when

- Interactive: full draft (and rewrite diff when applicable) printed as ordinary markdown, then user picked `approve` (proceed to Phase 5), `consider-split` / `abort` (exit 0, no write), or hit the edit-cycle cap. Edit cycles re-print the revised draft before each short ask. On approve, the glossary and mark-ready consents (when their gates fired) are recorded for Phase 5.8/5.9.
- Autofix with `--yes`: draft Written, summary payload printed, proceeding to Phase 5.
- Autofix without `--yes`: draft Written, summary payload printed, exit 0.

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

### 5.1 — The spec body is the §4.1 draft file

The approved draft file from §4.1 (revised in-place by Phase 4 edit cycles) IS the input to `flowctl spec set-plan --file <literal draft path>` — never re-authored into a heredoc. Source tags **stay in the spec body** — they are part of the audit trail and survive into the on-disk spec at `.flow/specs/<id>.md`. Future readers (including `/flow-next:plan` and `/flow-next:interview`) see the tags and can scrutinize.

The frontmatter top of the spec is whatever `flowctl spec create` writes (it generates a placeholder via the spec-create plumbing). `spec set-plan` overwrites the placeholder with the captured body — so the captured body should NOT include a duplicate `# <title>` heading; `set-plan` accepts the body as-is and atomic-writes to `.flow/specs/<id>.md`.

### 5.2 — New-spec branch

**Tracker-first is the recommended team default** when a tracker is configured (`tracker.specIds=tracker`): the tracker is the distributed allocator, so parallel captures stop colliding on `fn-N`. Route from the preamble root config snapshot (fn-110) — **no new `config get`**. Explicit user override in the invocation always wins. Do **not** nag about the id scheme at this mint site (withdrawn R10).

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
SPEC_TITLE="<chosen title from Phase 3 or Phase 1.3>"

# From the preamble root snapshot (literal path; no new config get).
SPEC_IDS=$(jq -r '.value.tracker.specIds // "flow"' "${TMPDIR:-/tmp}/flow-capture-config-<suffix>.json" 2>/dev/null)
BRIDGE_ACTIVE=$("$FLOWCTL" sync active --json 2>/dev/null | jq -r '.active // false')

if [ "$SPEC_IDS" = "tracker" ] && [ "$BRIDGE_ACTIVE" = "true" ]; then
 # Named existing issue in the request → mint from that key, THEN attach + seed.
 # SPEC_OUTPUT=$("$FLOWCTL" spec create --tracker-first --tracker-identifier "<KEY|#N|project#iid>" --title "$SPEC_TITLE" --json)
 # Minting stores the identifier but NOT the durable tracker.id, so this branch
 # MUST also run the fetch/attach/seed ceremony (tracker-sync steps.md Phase 2b)
 # exactly like the fresh-idea branch below. Skipping it leaves the spec
 # effectively unlinked: a later lifecycle touchpoint sees no tracker.id, takes
 # the Phase 3 create-if-unlinked path, and creates a SECOND remote issue
 # instead of linking the one the user named.
 # Fresh idea → create-first first (tracker-sync steps.md Phase 2d), then mint + attach + seed:
 # skill: flow-next-tracker-sync (operation: create-first, title: "$SPEC_TITLE", body: "<draft seed>")
 # → {id, identifier, url}; on noop / no transport → SILENT fall-through to flow-first below
 # SPEC_OUTPUT=$("$FLOWCTL" spec create --tracker-first --tracker-identifier "$IDENTIFIER" --title "$SPEC_TITLE" --json)
 # then attach + seed merge base per tracker-sync steps.md Phase 2d "Enabled caller sequence"
 # Network cost (honest, conditional): when tracker.perEvent.capture is already active,
 # tracker-first REORDERS that existing remote write; when the leaf is off (default — a
 # bridge-active repo can have every lifecycle event disabled), tracker-first adds an
 # EARLIER remote write that flow-first would not have made.
 :
fi

# SILENT degrade - the ONLY flow-first creation site, deliberately OUTSIDE
# the branch above. A create-first noop / unreachable transport / failed mint
# leaves SPEC_OUTPUT unset inside the tracker branch, and an `else` arm can
# never run in that case, so the promised fall-through has to be an
# unconditional post-check.
#
# GUARD: degrade ONLY when nothing was created remotely. If create-first
# already made and recorded an issue and the tracker-keyed MINT then failed
# (e.g. preflight found a mixed-history collision), falling back to flow-first
# would strand that issue as an orphan with no local spec pointing at it.
# In that case surface identifier + url + retryKey and STOP - the recovery
# record makes the run resumable, a silent fn-N spec does not.
if [ -z "$SPEC_OUTPUT" ] && [ -z "$IDENTIFIER" ]; then
 SPEC_OUTPUT=$("$FLOWCTL" spec create --title "$SPEC_TITLE" --json)
fi
SPEC_ID=$(printf '%s' "$SPEC_OUTPUT" | jq -r '.id')

if [[ -z "$SPEC_ID" || "$SPEC_ID" == "null" ]]; then
 echo "Error: spec create failed: $SPEC_OUTPUT" >&2
 exit 1
fi

# Write the spec body from the §4.1 draft file — type the literal path verbatim
# from agent context (path-persistence rule: never a shell variable across prompt turns).
"$FLOWCTL" spec set-plan "$SPEC_ID" --file "${TMPDIR:-/tmp}/flow-capture-draft-<working-title-slug>-<suffix>.md" --json

# Chart handoff (fn-135) — ONLY after successful create + set-plan.
# Order is load-bearing: never link-spec before the spec body exists.
# On retry: if produced_specs already has this B-ID+cluster identity, discover
# that entry and link the existing spec instead of minting another (Phase 1.2b).
if [[ -n "$CHART_ID" && -n "$BRIEFING_ID" ]]; then
 # Subcommand tokens stay LITERAL on the command line (the Ralph guard blocks
 # a variable in either of the two tokens after the launcher); only arguments
 # come from the array.
 LINK_ARGS=("$CHART_ID" --briefing "$BRIEFING_ID" --spec "$SPEC_ID" --decisions "$CHART_DECISIONS" --json)
 [[ -n "$CLUSTER_KEY" ]] && LINK_ARGS+=(--cluster "$CLUSTER_KEY")
 "$FLOWCTL" chart link-spec "${LINK_ARGS[@]}"
fi

# Run anchor for Phase 6's sync check — written at the write step, BEFORE the
# 5.7 dispatch, so it lower-bounds this run's receipts.
date -u +%Y-%m-%dT%H:%M:%SZ > "${TMPDIR:-/tmp}/flow-capture-anchor-${SPEC_ID}"
```

The draft file round-trips embedded markdown and newlines byte-exact — `read_file_or_stdin` in `flowctl.py` handles `--file <path>` directly. No re-authoring: the approved content is consumed from disk, exactly as the user read it back.

**Chart handoff retry rules (fn-135 R50):**

- Capture decline / abort: call nothing; no `produced_specs[]` entry; chart stays resumable.
- Partial multi-spec: record only successful `link-spec` calls; resume the failed cluster without duplicating the first.
- Interruption after `spec create` / `spec set-plan` but before `link-spec`: on retry, discover the existing B-ID+cluster identity (chart sidecar `produced_specs[]` or matching specs) and link that same spec — never mint a second.

### 5.2b — Split branch (interactive `split-as-proposed` only)

Run the §5.2 new-spec ceremony once per proposed spec, in dependency order (dependencies first):

- **Each spec gets its own complete body**: its allocated criteria renumbered from R1, the Phase 2 sections that serve those criteria, a per-spec slice of `## Conversation Evidence`, and a short `## Decision Context` note naming the sibling specs and the shared origin. Specs are handover objects — never write "see the other spec" in place of content a worker needs.
- Write each body to its own literal draft path (same path-persistence rule as §4.1) and hand it to that spec's `spec set-plan --file`.
- **After all creates, record the edges**: `"$FLOWCTL" spec add-dep <dependent-id> <dependency-id> --json` per proposed edge.
- §5.4–§5.10 (branch name, tracker sync, glossary, readiness, HTML lens) run per created spec exactly as for a single create; the Phase 4 mark-ready answer applies to all created specs or none.
- Phase 6 lists every created id plus the dependency edges.

Autofix never reaches this branch (§4.4 records the proposal instead).

### 5.3 — Rewrite branch

When `REWRITE_TARGET` is set:

```bash
SPEC_ID="$REWRITE_TARGET"

# Skip spec create — the spec already exists. Overwrite the spec body from the
# §4.1 draft file (literal path typed verbatim, per the path-persistence rule).
"$FLOWCTL" spec set-plan "$SPEC_ID" --file "${TMPDIR:-/tmp}/flow-capture-draft-<working-title-slug>-<suffix>.md" --json

# Readiness reset — runs AFTER set-plan: a failed rewrite must not downgrade a
# blessed spec (Codex review, PR #170 P2). A rewrite is a full re-authoring; any
# prior blessing no longer applies once the new body lands. Unconditional call:
# the toggle is idempotent (fn-58.1) — a never-ready spec is a silent no-op (no
# write, no updated_at bump), so this does NOT turn every rewritten draft into a
# readiness-adopter. Announce, never confirm — --rewrite already carried the
# consent.
READY_RESET=$("$FLOWCTL" spec unready "$SPEC_ID" --json | jq -r '.changed // false')

# Run anchor for Phase 6's sync check — REQUIRED on the rewrite path: created_at
# is the spec's ORIGINAL creation time here (an earlier run), so an old
# `event: capture` receipt would false-OK the check and the retro-fire would
# never fire (Codex review, PR #169 P2).
date -u +%Y-%m-%dT%H:%M:%SZ > "${TMPDIR:-/tmp}/flow-capture-anchor-${SPEC_ID}"
```

When `READY_RESET=true` (the spec WAS ready), Phase 6's rewrite footer carries a one-line reset announcement. When `false`, no readiness line is printed — never announce a reset that didn't happen (zero noise for never-ready specs).

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
markdown body write failed. To roll back: rm .flow/specs/<id>.json .flow/specs/<id>.md.
Or re-run capture with --rewrite <id> to retry the body write.
```

This mirrors the failure semantics in other flowctl commands — partial-state recovery is on the user, but the error is loud.

### 5.6 — No git commit from this skill

Capture **does not** stage or commit the new spec. The user owns when to commit. The output footer (Phase 6) tells them what to do.

Two reasons:

1. The captured spec often gets edited by `/flow-next:plan` immediately after — committing twice (once for capture, once after plan adds tasks) is noise.
2. Capture changes touch only `.flow/`; users sometimes want to bundle them with adjacent edits.

If a future enhancement adds a `--commit` flag, Phase 5 would gain a "stage + commit" branch, but the default stays "no commit, user owns the staging".

### 5.7 — Tracker sync (opt-in) — spec push/pull + merge

**Optional. Runs only when the tracker bridge is active AND `capture` is opted in. With no tracker configured this is a no-op — capture behaves exactly as today.** After the spec is on disk, project the captured/enriched body to the linked (or freshly linked) tracker issue and reconcile two-way (R6): a flow-first capture pushes the body out; a tracker-first spec (one already linked) reconciles the new capture content against the issue via the agentic 3-way merge.

```bash
LEAF="$("$FLOWCTL" config get tracker.perEvent.capture --json | jq -r '.value')"
case "$LEAF" in
 pull) OP="pull" ;;
 push) OP="push" ;;
 reconcile) OP="reconcile" ;;
 comment) OP="comment" ;;
 off|null) OP="off" ;;
 *) OP="off" ;; # malformed config stays silent
esac
if [ "$("$FLOWCTL" sync active --json | jq -r '.active')" = "true" ] \
 && [ "$OP" != "off" ]; then
 # Invoke the inline flow-next-tracker-sync wrapper. It prepares the approved
 # operation-specific 0600 input files, then makes exactly one lifecycle call:
 # "$FLOWCTL" tracker sync "$SPEC_ID" --op "$OP" --event capture <legal file flags>
 # For OP=comment, Capture synthesizes the comment content by name: a compact
 # created/updated-spec summary plus the captured context. The 0600
 # --body-file FIRST line is `evidence=<sha256-of-current-spec-file>`; delete
 # the file after the call. No content travels in argv.
 # No reachable transport is best-effort; genuine body conflicts surface scoped
 # (interactive) or queue (Ralph, though capture itself is Ralph-blocked).
 :
fi
```

Best-effort — a tracker failure never blocks the capture. The skill emits its own receipt, event-tagged `--event capture` — the tag Phase 6's end-of-run `sync check` audits.

### 5.8 — Glossary term-adds (consent-gated; interactive only)

Runs only when Phase 4.2's glossary consent approved ≥1 term (which implies `GLOSSARY_TERMS > 0` — the Phase 2.7 gate — and interactive mode; autofix never reaches here). For each approved term:

```bash
"$FLOWCTL" glossary add "<term>" --definition-file - --json <<EOF
<one-line definition from the read-back, as approved>
EOF
```

Same call site as interview's behavior (b) — `glossary add` is a case-insensitive upsert; stdin keeps quoted phrasing intact. Best-effort: a failed add prints a warning and continues — never blocks the capture (the spec is already on disk). Report `Glossary: added N term(s) (<terms>)` for the Phase 6 footer.

### 5.9 — Mark-ready write (consent-gated; interactive only)

Runs only when Phase 4.2's mark-ready consent recorded `mark-ready` (which implies the target-aware predicate held — adopted local readiness for a new capture or a ready rewrite target, no `tracker.readyState` — and interactive mode; autofix never reaches here):

```bash
"$FLOWCTL" spec ready "$SPEC_ID" --json
```

Idempotent plumbing (fn-58.1) — re-running is a silent no-op. Best-effort: a failed write prints a warning and continues — never blocks the capture (the spec is already on disk). Report `Readiness: marked ready` for the Phase 6 footer; on `keep-draft` (or when the question never fired) report nothing — zero footer noise outside the consent path.

### 5.10 — HTML render lens (opt-in) — spec artifact + link line

```bash
HTML_LENS=$("$FLOWCTL" config get artifacts.html.enabled --json | jq -r 'if .value == true then "true" else "false" end')
```

When `HTML_LENS != true` (off or unset): **skip entirely** — do not read the reference, write no artifact, print no artifact output. The one-line gate read above is the only cost.

When `HTML_LENS = true`: **read [`references/html-lens.md`](references/html-lens.md)** and follow it — the spec-artifact generation, the disclosure-reference load, the link-line write, and the Lavish companion. (Split out of the always-loaded workflow.md so the default run never pays for it.)

### Done when

- The new (or rewritten) spec is on disk at `.flow/specs/<id>.md`.
- `SPEC_ID` is known for Phase 6.
- Optional branch-name is set if user named one.
- When the tracker bridge is active and `capture` is opted in, the spec body was pushed/pulled/reconciled to the linked issue (5.7); otherwise this step was a silent no-op.
- Approved glossary term-adds written (5.8); skipped silently when none were proposed or approved.
- Mark-ready write applied iff consented (5.9); rewrite branch reset readiness via idempotent `unready` with `READY_RESET` recorded for Phase 6 (5.3).
- HTML render lens (5.10): with `artifacts.html.enabled` true, `.flow/artifacts/<SPEC_ID>/spec.html` regenerated per the disclosure reference, the spec's marker link line replaced in place (exactly one), and the pre-publish checklist passed; with the mode off/unset, 5.10 was a silent no-op beyond the single config read.

---

## Phase 6: Suggested next step (R16)

**Goal:** print the suggested next step. The deliverable is the new spec; this footer tells the user what to do with it.

**Tracker-sync end-of-run check - runs BEFORE the footer.** Read-only audit: did the capture touchpoint (5.7) actually fire (receipt-backed)? It runs independently of 5.7, so a wholesale-skipped facade call is still caught. With no tracker configured, `sync check` exits silently in constant time; the footer slot then reads `n/a (bridge inactive)` and nothing else changes. (Capture is Ralph-blocked, so there is no stdout-routing concern; the slot prints where the footer prints.)

```bash
# --since: the run anchor written at the Phase-5 write step (5.2/5.3). Fallback:
# created_at — valid for FRESH captures only (spec created this run). The rewrite
# path MUST have the anchor: created_at is the ORIGINAL creation time there, so
# any old `event: capture` receipt would false-OK the check (Codex review,
# PR #169 P2). A Phase-6 "now" would postdate the 5.7 receipt (false-MISSING);
# updated_at can be bumped by §5.9's ready-toggle after 5.7 — neither is safe.
ANCHOR_FILE="${TMPDIR:-/tmp}/flow-capture-anchor-${SPEC_ID}"
if [[ -f "$ANCHOR_FILE" ]]; then
 SINCE="$(cat "$ANCHOR_FILE")"
else
 SINCE="$("$FLOWCTL" show "$SPEC_ID" --json | jq -r '.created_at')"
fi

"$FLOWCTL" sync check "$SPEC_ID" --events capture --since "$SINCE" --json
# Empty output → bridge inactive → slot = `n/a (bridge inactive)`. Otherwise
# `.missing` empty → slot = `OK`; non-empty → retro-fire (below).
```

**Retro-fire on MISSING — exactly ONE cycle, never blocking:**

1. Record the retro-fire start anchor and echo it (the re-check needs it as `--since`): `date -u +%Y-%m-%dT%H:%M:%SZ`
2. Invoke the **inline flow-next-tracker-sync wrapper directly**. Re-resolve the operation with 5.7's complete `off | pull | push | reconcile | comment` mapping. For `comment`, Capture re-synthesizes the created/updated-spec summary plus captured context in a mode `0600` body file. The wrapper prepares the other legal operation inputs, makes exactly one `flowctl tracker sync <spec-id> --op <op> --event capture <legal file flags>` call, and deletes the temporary files. NEVER invoke this check block as a wrapper.
3. Re-check with `--since` = the step-1 anchor:
 `"$FLOWCTL" sync check "$SPEC_ID" --events capture --since "<retro-fire-start>" --json`
4. Record the final state in the footer slot. Still MISSING after the one cycle is a recorded, visible outcome — never a second retro-fire, never a block (the spec is already on disk; a tracker hiccup must not become a hard stop). Recovery guidance lives in the receipt note + `docs/tracker-sync.md`.

Then the footer. `Tracker sync:` is a REQUIRED line with exactly four states — an explicit `n/a` proves the check ran; an absent line is a skipped check:

```text
Spec captured at .flow/specs/<SPEC_ID>.md.
Tracker sync: <OK | MISSING:capture → retro-fired → OK | MISSING:capture (retro-fire failed: <reason>) | n/a (bridge inactive)>

Next:
 /flow-next:plan <SPEC_ID> → research + break into tasks
 /flow-next:interview <SPEC_ID> → refine via Q&A
```

When Phase 5.8 wrote terms, append one line after `Tracker sync:`: `Glossary: added N term(s) (<comma-separated terms>)`. Omit entirely otherwise (including every autofix run).

When Phase 5.9 marked the spec ready, append one line after `Tracker sync:`: `Readiness: marked ready`. Omit entirely otherwise — `keep-draft`, predicate-not-met, and every non-consented run print no readiness line.

When Phase 5.10 wrote the render lens, append one line after `Tracker sync:`: `Artifact: .flow/artifacts/<SPEC_ID>/spec.html (render lens — regenerable; markdown is the record)`. Omit entirely when the mode is off/unset (zero artifact-related output) or when generation failed (5.10's stderr note already reported it).

Autofix only: when the §4.2 target-aware predicate yields `READY_OFFER=true` and the spec was written (`--yes`), append `Mark ready when blessed: flowctl spec ready <SPEC_ID>` (suggestion only — autofix never writes readiness).

### Biz-suggestion footer (R25)

When the conversation has business-context signals but the business layer is sparse, append a one-line suggestion to refine via `/flow-next:interview --scope=business`. The R25 business-pass suggestion fires when the captured conversation names 1-2 distinct R24 signal categories (the same `1 <= n < 3` rule), agent-judged. Input is `$BIZ_SIGNAL_CATEGORIES` — the count computed in [§2.6](#26--biz-context-signal-routing-r24--signal-category-count-for-r25) over the nine SIGNAL CATEGORIES from R24 (target user / problem framing / success metric / MVP boundary / business constraints / what-not-to-build / prioritization rationale / business risks / UX expectations). The count is over categories, not over markdown destinations. R22: `BIZ_SIGNAL_CATEGORIES=0` → no-fire (solo-dev silence). Count `>= 3` → no-fire (biz layer adequately filled).

```bash
# R25 threshold is host-agent judgment (fn-113; former flowctl helper removed).
# Fire when 1 <= BIZ_SIGNAL_CATEGORIES < 3; otherwise stay silent.
if [ "$BIZ_SIGNAL_CATEGORIES" -ge 1 ] && [ "$BIZ_SIGNAL_CATEGORIES" -lt 3 ]; then
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

If `REWRITE_TARGET` was set, the footer prefix changes (the `Tracker sync:` line stays mandatory):

```text
Spec rewritten at .flow/specs/<SPEC_ID>.md.
Readiness: spec rewritten — readiness reset to draft (re-bless when ready)
Tracker sync: <same four states>

Next:
 /flow-next:plan <SPEC_ID> → re-plan tasks (existing tasks under the spec
 may need /flow-next:sync to align)
 /flow-next:interview <SPEC_ID> → refine via Q&A
```

The `Readiness:` announcement line appears ONLY when §5.3's reset actually changed the flag (`READY_RESET=true`). Never-ready specs print no readiness line — an announcement is not a confirmation prompt, and it must not claim a reset that didn't happen.

### Done when

- End-of-run `sync check` ran (`--events capture`, `--since` = the Phase-5 run anchor, falling back to `created_at` for fresh captures); any MISSING touchpoint was retro-fired exactly once and re-checked.
- Footer is printed with the mandatory four-state `Tracker sync:` line (explicit `n/a (bridge inactive)` when no tracker is configured).
- Skill exits 0.

---

## Manual smoke (acceptance R3, R4, R5, R6, R7, R8, R24, R25)

The skill itself is markdown — there's no unit-test surface. The validation is invoking `/flow-next:capture` in a real session. Expected behavior:

- Phase 0 walks `.flow/specs/`, runs memory search if memory is initialized, detects compaction, applies idempotency. Branches into duplicate-detection question if ≥2 strong matches; exits cleanly on `abort`.
- Phase 1 emits a `## Conversation Evidence` block with verbatim user quotes (≤30 lines).
- Phase 2 produces a draft with per-line source tags. Every acceptance criterion has one of `[user]` / `[paraphrase]` / `[inferred]`. Biz-context signals (R24) route to their destinations using only `[user]` / `[paraphrase]` tags; categories without conversation signal leave their destinations absent. `BIZ_SIGNAL_CATEGORIES` (0..9) computed for Phase 6.
- Phase 3 fires must-ask cases only when (a) title is genuinely ambiguous, (b) acceptance is untestable, (c) scope-conflict persists. Optional ambiguities are deferred to Phase 4.
- Phase 4 materializes the draft ONCE via the Write tool to a literal unique path (§4.1), then **print-then-ask** (interactive): prints the FULL draft markdown (and rewrite diff when applicable) as an ordinary assistant message, then a SHORT `plain-text numbered prompt` (one-line pointer + `[inferred]` tally/warnings + options only — never multi-paragraph drafts/diffs/criteria lists in the ask body). Interactive: user picks approve / edit / abort; edit cycles revise via the Edit tool + full-file Read + **reprint the revised draft** before each short re-ask; on approve with proposals, one follow-up `Glossary?` consent question; on approve with `READY_OFFER=true`, one follow-up `Mark ready?` consent question (default keep-draft). New captures set `READY_OFFER` only when ≥1 spec is ready and no `tracker.readyState` is configured; rewrites set it only when the target itself was ready and no `tracker.readyState` is configured. Autofix: Write + summary payload printed + require `--yes` (unchanged; no interactive ask); proposals print as suggestions, never written; readiness never written.
- Phase 5 calls `flowctl spec create` + `spec set-plan --file <literal draft path>` (consumes the §4.1 draft file — no heredoc re-authoring). Approved term-adds written via `flowctl glossary add` (5.8, interactive only). Consented mark-ready written via `flowctl spec ready` (5.9, interactive only). Rewrite branch (5.3) runs idempotent `spec unready` unconditionally; `READY_RESET` gates the Phase 6 announcement. With no glossary (or a husk), 2.7/4.x/5.8 are silent no-ops; with readiness un-adopted, 4.2's mark-ready question / 5.9 / all readiness footer lines are silent no-ops — zero behavior change. With `artifacts.html.enabled` true, 5.10 regenerates `.flow/artifacts/<id>/spec.html` per the disclosure reference and leaves exactly one `<!-- flow-next:artifact-link -->` line in the spec md; off/unset, 5.10 is a single config read and nothing else.
- Phase 6 prints the next-step footer. Agent-judges the R25 threshold (`1 <= BIZ_SIGNAL_CATEGORIES < 3`); on fire, appends the `/flow-next:interview --scope=business` suggestion line. R22 invariant: `BIZ_SIGNAL_CATEGORIES=0` → no-fire → no suggestion.

In autofix without `--yes`, the draft is Written and the skill exits 0 — no `.flow/` write, no spec allocated.
In autofix with `--yes`, the §4.1 Write + `--yes` substitutes for the interactive print-then-ask approval before Phase 5 writes.

The Ralph-block (SKILL.md) ensures this skill never runs under `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` — capture requires a user at the terminal.
