# /flow-next:capture workflow

Execute these phases in order. Each gates on the prior. Stop on user-blocking error — never plow through with bad state.

**Branch disclosure:** this file is the universal spine — everything every capture run walks. Path-specific machinery (autofix, `--rewrite`, chart briefings, strategy alignment, split proposals, glossary, readiness, tracker, must-ask detail) sits in `references/*.md` behind the gates below. When a gate sentinel prints, STOP and Read the named reference before any further step. When a gate is silent, that path does not exist for this run — read nothing.

## Preamble

```bash
set -e
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
SPECS_DIR="$REPO_ROOT/.flow/specs"
TODAY="$(date -u +%Y-%m-%d)"
```

`jq` and `python3` (or `python`) must be on PATH. Mode + flags come from the SKILL.md mode-detection block (`MODE` = `interactive` | `autofix`, plus `REWRITE_TARGET`, `FROM_COMPACTED_OK`, `COMMIT_YES`, `NO_PLAN_OPT`, `FROM_FLOW`).

If `.flow/` does not exist, print `No .flow/ directory — run \`$FLOWCTL init\` first.` and exit cleanly. Capture has nothing to write into.

**ONE root config snapshot for the whole capture run** — take it once after `.flow/` is confirmed, then derive every later leaf (including the Phase 5.2 mint gate) via `jq` from that file. No further root `config get` on the capture path for values already in the snapshot. Path-persistence: compose a literal path with an agent-chosen 4-char suffix and type it verbatim:

```bash
CAPTURE_CFG="${TMPDIR:-/tmp}/flow-capture-config-<suffix>.json"   # literal path
"$FLOWCTL" config get --json > "$CAPTURE_CFG" 2>/dev/null || { printf '{"key":null,"value":{}}' > "$CAPTURE_CFG"; echo "[CAPTURE]: config snapshot empty — flowctl unreachable; snapshot-derived gates degrade to defaults" >&2; }
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

Scan `.flow/specs/*.json` for title overlap. (Pre-1.0 `.flow/epics/` repos: port first per `flowctl usage` "Pre-1.0 layout porting".)

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

Memory hits are advisory — they signal "you may have prior art on this topic" without blocking. Aggregate hit ids + titles for the capture summary's "Related context" footnote (when ≥1 hits land). They do **not** trigger the duplicate-detection branch on their own; only spec-title overlap (0.2) does.

If memory is not initialized (`memory list` returns the `Memory not initialized` error), skip this step silently. Memory search is a quality-of-life signal; absence is not blocking.

### 0.3b — Strategy gate (advisory grounding input)

```bash
ACTIVE=0
# NO pipelines in the probe — capture raw first, rc-checked; parse separately.
RAW="$("$FLOWCTL" strategy status --json 2>/dev/null)" || ACTIVE=1     # probe ERROR ⇒ ACTIVE (fail open)
if [ "$ACTIVE" = "0" ]; then
  VAL="$(printf '%s' "$RAW" | jq -r '.sections_filled // 0' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
  [ "${VAL:-0}" -ge 1 ] 2>/dev/null && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
  echo "GATE ACTIVE — STOP. Read references/strategy-alignment.md before continuing."
fi   # default branch: bare no-op — NO link, NO read path
```

When the sentinel prints, read [references/strategy-alignment.md](references/strategy-alignment.md) and execute its §0.3b snapshot (it also owns the Phase 5.0 contradiction gate that runs before any write). When the gate is silent, `STRATEGY_PRESENT=false`: Phase 2 emits no `[strategy:*]` tags and Phase 5's contradiction check is skipped entirely — there is no signal to align to.

### 0.4 — Compaction detection (R6)

Scan the visible conversation for compaction signals:

- Literal `[compacted]` markers.
- Truncated tool-result patterns: `<...output too large to include>`, `(output truncated)`, `... (N more lines)`.
- System-summary blocks (e.g. "Earlier in the conversation, the user...").
- Suspicious gaps where a tool call shows no output but later turns reference its result.

These signals are **advisory, not an automatic refusal**. A conversation may have been compacted earlier while the feature or decision being captured is fully present in later visible user turns. A historical system-summary block, `[compacted]` marker, or unrelated truncated tool result alone does not make the capture source incomplete.

For each signal, judge whether it removed evidence **relevant to this capture**:

- **Proceed normally** when the requested feature / decision is fully stated or fully restated in visible user turns, including when those turns occur after the latest compaction. Record `Prior compaction detected; relevant capture evidence remains visible.` in the capture summary warnings.
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

### 0.5 — Duplicate branch gate

**Silent overwrite is never an option (R8) — when 0.2 found matches, the branch below runs before anything is drafted.** A capture that reaches Phase 1 with ≥2 strong matches unresolved has broken this.

- **0-1 strong matches** and no prior-capture artifact id in the conversation → no branch; continue to 0.5b.
- **≥2 strong matches AND `REWRITE_TARGET` empty** → GATE ACTIVE — STOP. Read [references/duplicate-branch.md](references/duplicate-branch.md) and run its §0.5 branch (interactive: `extend` / `supersede` / `proceed-anyway` / `abort`; autofix: exit 2) before continuing. It also owns the §0.6 prior-capture-artifact branch below. When unsure whether the matches are strong, treat the gate as ACTIVE.

### 0.5b — Chart briefing gate

When the conversation or `$ARGUMENTS` references a chart briefing input — a path matching `.flow/charts/*-briefing*.md`, an explicit B-ID (`B1`, `B2`, …), or a chart id whose sidecar lists briefings — GATE ACTIVE: STOP and Read [references/chart-briefing.md](references/chart-briefing.md) before drafting. It owns admission (draft/stale fail closed; explicit risk override naming the unresolved D-IDs), evidence extraction, the provenance-separation rule, and the `chart link-spec` handoff + retry rules for Phase 5.

When no chart briefing is in play, this step is a silent no-op — read nothing.

### 0.6 — Idempotency (R8)

- **`REWRITE_TARGET` set** → GATE ACTIVE — STOP. Read [references/rewrite-mode.md](references/rewrite-mode.md) and run its §0.6 target validation (exists, and is a spec not a task — otherwise exit 2) before continuing. That reference also governs the rewrite behavior in Phases 4, 5 and 6; read it once here.
- **`REWRITE_TARGET` empty** → scan the visible conversation for prior-capture artifact references (patterns like `Spec captured at .flow/specs/<id>.md` from earlier turns). If found, run the §0.6 branch in `references/duplicate-branch.md` (interactive asks rewrite / proceed / abort; autofix exits 2). If none found, continue.

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
- **User-typed only** — every evidence line quotes something the USER actually typed. Agent narration, tool output, and capture's own process conclusions are never emitted as user turns. After Phase 0's duplicate scan, agents have fabricated a turn like "This is a NEW spec. Do not rewrite <ids>. Do NOT mark ready. Do NOT implement." — that sentence is skill process state, not conversation evidence; emitting it (or any process formula) as a `> user (turn N)` line has broken this.
- **Skip** turns that are pure greetings, off-topic asides, tool-result interpretation by the user, or noise.
- **Include** turns that state intent, give examples, name constraints, reject options, or reference files.
- **Cap** at ~30 lines total. If older spec-relevant turns must be dropped, replace them with one `> [truncated: N earlier turns]` line at the top of the block.

### 1.2 — Optional codebase verification (subagent dispatch — R12)

- **No repo-file / module references in the conversation** (or only 1-2, investigated on the main thread) → skip; read nothing.
- **The conversation references repo files or modules whose state matters for the spec** ("the auth module needs X", "we already have a rate limiter at...") → GATE ACTIVE — STOP. Read [references/codebase-verification.md](references/codebase-verification.md) and run its read-only investigation-subagent dispatch before drafting.

Whichever path ran, the orchestrator (this skill, on the main thread) merges results into Phase 2's `[inferred]` confidence — verified references can be tagged `[paraphrase]`; unverified or missing files stay `[inferred]` and surface in saved-spec summary for user review.

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
- When 0.5b's chart gate fired, its §1.2b evidence extraction ran (chart id / B-ID / cluster / D-IDs / assets, untagged).

---

## Phase 2: Source-tagged synthesis (R4, R14, R15)

**Goal:** draft the spec body using the CLAUDE.md richer template, with **per-line source tags** so hallucinated content is visible in the capture summary.

Spec prose follows the artifact prose contract in [docs/prose.md](../../docs/prose.md); proceed without it when the doc is absent.

### 2.1 — Source-tag taxonomy

Every acceptance criterion line, every decision-context line, and every scope-bounding line in the spec carries one tag: `[user]` / `[paraphrase]` / `[inferred]` / `[strategy:<track>]`. The four-tag table — meanings, acceptance tests, worked examples, when-to-use-which — is the single copy in [phases.md](phases.md) §Source-tag taxonomy.

Pure prose sections (Goal & Context narrative, Architecture overview) do not need per-line tags — but the **whole section** carries a section-level tag in a frontmatter-style note: e.g. `<!-- Goal & Context: 70% [user], 30% [inferred] -->`. saved-spec summary surfaces this.

### 2.2 — Apply the canonical spec template

The canonical section structure lives in [`plugins/flow-next/templates/spec.md`](../../templates/spec.md) - the single source of truth for the section sequence and per-section ownership annotations (per R17 - never re-embed the section list inline; cross-link the template). At runtime the template is resolved via the 3-tier discovery cascade (first match wins): `<repo_root>/SPEC.md` → `<repo_root>/spec.md` → bundled `${PLUGIN_ROOT}/templates/spec.md`. The bundled file is the canonical source of truth; earlier tiers are user-customized overrides. Walk the resolved template in its declared order and draft each section's body using the source-tag conventions below. Before any template section, prepend `## Conversation Evidence` (Phase 1 output verbatim); after the template, append `## Requirement coverage` only on a planned route (rule below; §2.8 judges the route first).

Source-tag application is per-tag, not per-section — and **only on content capture newly authors**:

- **`[user]`** only where the tagged content is findable in the Phase 1 evidence block (goal framing, user-stated acceptance, named non-goals, rejected alternatives the user surfaced). A close restatement is `[paraphrase]`, never `[user]`.
- **`[paraphrase]`** is for spec-language restatements of user intent — preserving meaning, tightening wording.
- **`[inferred]`** covers agent fill-in for completeness (default conventions: error formats, retry policies, observability hooks, file / component refs the user did NOT name). **Untouched by §2.6 biz-routing** — biz destinations only accept `[user]` / `[paraphrase]`.
- **`[strategy:<track>]`** activates only when Phase 0 strategy snapshot was populated.

When 0.5b's chart gate fired, apply that reference's provenance-separation rule: chart D-ID evidence is structural and is never source-tagged, and existing criteria are never retagged.

Auxiliary section rules layered on the template:

- **Phase 1.2 verified references** — if a subagent verified that a user-named file / component actually exists in the codebase, upgrade the tag from `[inferred]` → `[paraphrase]` for that line.
- **Sections without conversation signal stay absent.** Do NOT auto-populate a template section from agent assumptions just because the template has a slot for it. Empty-by-default beats fabricated-by-default.
- **`## Decision Context`** substructure (FLAT vs `### Motivation` / `### Implementation Tradeoffs` per the template's "(A) FLAT" vs "(B) SUBSTRUCTURED" branches) is governed by §2.6 — capture only emits SUBSTRUCTURED when biz-context routing has content for `### Motivation`; otherwise stays FLAT.
- **`## Acceptance Criteria`** R-IDs allocate sequentially from R1 — capture creates fresh specs, no renumber concern. Outcome-AC entries (user-facing "what success looks like") route via biz-context signal category 3 (§2.6); other criteria stay generic.
- **`## Requirement coverage`** appended after the template body only when no direct route is recorded for this capture (`NO_PLAN_OPT=0`, and under `FROM_FLOW=1` the §2.8 judgment resolved to plan): a table mapping each R-ID to `fn-N.M (TBD - populate via /flow-next:plan)` placeholders for plan to fill. On the direct route (R6a) the section is omitted: the single implicit owner task work mints is the coverage, and make-pr builds its table from that task's `satisfies` list. Capture never writes tasks on either route.
- **`## Parked unknowns`** (optional) — fog the conversation left genuinely open. One bullet per item, each naming what would resolve it, each passing the fog-or-ticket test: decidable now → decide it in the section that owns it; resolvable by scheduled work → it is a task for `/flow-next:plan`, not fog; genuinely unknown → park it. No fog → no section. This is the honest home for "we did not settle this", and it is not a dumping ground for everything the conversation did not spell out — `[inferred]` fill-in stays tagged fill-in.

**Spec durability rule.** The drafted spec states **contracts** — types, signatures, behaviors, invariants — and **never file paths or line numbers**; coordinates rot on the first refactor and feed plan-sync churn downstream. One exception: a decision-rich snippet whose exact location IS the decision. When Phase 1.2 verified a user-named file or component, that verification upgrades the source tag; it does not license pasting the path into the spec body as a contract. **Tasks are exempt and unchanged** — `**Files:**` / `**Touches:**` are a task's job, and capture writes no tasks.

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

Track `[inferred]` count across all sections (especially in `## Acceptance Criteria` and `## Boundaries`). The count surfaces in the capture summary.

### 2.5 — Spec-count gate (R11)

**Tripwire:** 8+ acceptance criteria, OR the criteria visibly serve more than one independently shippable outcome.

- **Below the tripwire** → skip entirely; normal captures see nothing here and read nothing.
- **At or above it** → GATE ACTIVE — STOP. Read [references/split-proposal.md](references/split-proposal.md) and run its §2.5 counting rule + independence partition to decide 1 vs N specs (it also owns the Phase 4 `split-as-proposed` option, the §5.2b split branch, and the Phase 6 split footer). Capture **never auto-splits** — the user decides.

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
- **Category 4 ("MVP scope / not doing X yet") and Category 6 ("what NOT to build") both route to `Boundaries`** but stay counted separately for R25 (different signal-source patterns: "MVP is narrow" vs "definitely not X"). **Tie-break:** a single clause matching more than one category counts ONCE, in the most specific category it matches — never double-counted toward the R25 threshold.
- **Decision Context substructure** — capture only ever writes fresh specs (never a rewrite of an existing FLAT body), so there is no FLAT→substructured promotion to handle here (that's `/flow-next:refine`'s merge contract). Decision rule for capture: when category 3, 5, 7, or 8 routes content, write `## Decision Context` as SUBSTRUCTURED — emit the `### Motivation` H3 with the routed content. Leave `### Implementation Tradeoffs` absent (do NOT write the `*Pending technical-scope interview pass.*` placeholder; that's `/flow-next:refine --scope=business`'s responsibility on a rewrite, not capture's). When none of categories 3, 5, 7, 8 carry content, write `## Decision Context` as FLAT — preserves R22 (solo dev with zero biz signals sees no Motivation/Implementation Tradeoffs scaffolding) and matches the canonical template's "(A) FLAT (default, R22 backward-compat)" branch.
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

### 2.7 — Glossary gate (new-vocabulary scan)

```bash
ACTIVE=0
RAW="$("$FLOWCTL" glossary list --json 2>/dev/null)" || ACTIVE=1     # probe ERROR ⇒ ACTIVE (fail open)
if [ "$ACTIVE" = "0" ]; then
  VAL="$(printf '%s' "$RAW" | jq -r '.total_terms // 0' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
  [ "${VAL:-0}" -gt 0 ] 2>/dev/null && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
  echo "GATE ACTIVE — STOP. Read references/glossary-terms.md before continuing."
fi   # default branch: bare no-op — NO link, NO read path
```

When the sentinel prints, read [references/glossary-terms.md](references/glossary-terms.md) and run its §2.7 scan (it also owns the §5.8 `Glossary?` consent and the §5.8 write). When the gate is silent — no glossary, a `# Glossary` husk, or `total_terms == 0` — `GLOSSARY_PROPOSALS` stays empty and nothing downstream changes; seeding an empty glossary is `/flow-next:prime`'s job, never capture's.

### 2.8 - Route judgment (one read, one decision)

Once the criteria are drafted, read [`plan-vs-no-plan.md`](../flow-next-flow/references/plan-vs-no-plan.md) and judge the drafted spec against it once; read [`route-matrix.md`](../flow-next-flow/references/route-matrix.md) as well when the spec is not a plain ready spec (unresolved product or authority questions, design risk wanting an independent assessment). Record the result in agent context as `ROUTE_DIRECT=1` (direct) or `ROUTE_DIRECT=0` (a positive plan signal, or interview / plan-review first). It feeds the §2.2 coverage rule, the saved-spec `Recommended next:` summary line, §5.9b under `FROM_FLOW=1`, and the Phase 6 closer. Re-judge only when an edit cycle changes the criteria. The judgment is printed on every path; the field write in §5.9b depends on how the run was invoked.

### Done when

- Every section is drafted with source tags applied.
- R-IDs are allocated sequentially.
- `[inferred]` count is computed.
- 8+ acceptance count flag set if applicable.
- Untestable acceptance candidates flagged for Phase 3 must-ask.
- `BIZ_SIGNAL_CATEGORIES` (0..9) computed for Phase 6 R25 dispatch.
- `GLOSSARY_PROPOSALS` collected (≤5; empty when the glossary gate is closed).
- `ROUTE_DIRECT` judged (§2.8); `## Requirement coverage` present only on a planned route.

---

## Phase 3: Must-ask cases (R9)

**Goal:** resolve the three hard-error conditions. Interactive: ask one question at a time. Autofix: exit 2 with which case fired.

| Case | Trigger | Interactive question | Autofix |
|------|---------|----------------------|---------|
| **(a) Ambiguous title** | Multiple plausible titles, none load-bearing in conversation | Ask user to pick title from candidates + offer custom | exit 2 |
| **(b) Untestable acceptance** | Phase 2.4 flagged ≥1 criterion that can't be made testable | Ask per-criterion: drop / reword / clarify | exit 2 |
| **(c) Scope-conflict** | Phase 0.5 went `supersede` or `proceed-anyway`, but the new spec's scope still overlaps the old one's | Ask user how to disambiguate boundaries | exit 2 |

**Gate:** when ANY row above fires → GATE ACTIVE — STOP. Read [references/must-ask-cases.md](references/must-ask-cases.md) for that case's trigger detail, examples, exact question shape, and autofix error text before asking or exiting. When no case fires, read nothing and continue to Phase 4.

### 3.1 — Optional ambiguities (not must-ask)

For optional ambiguities — the spec has `[inferred]` content the user might want to scrutinize but it's not blocking — do NOT ask in Phase 3. Surface them in the capture summary's `[inferred]` tally; the user can pick `edit` if they want to revise.

Phase 3 only fires for the three hard-error cases. Asking too many questions defeats capture's purpose.

### Done when

- All must-ask cases resolved (interactive) or exited 2 (autofix).
- Spec draft updated with user-chosen title / reworded criteria / disambiguated boundaries.

---

## Phase 4: Prepare the write

The interactive capture request authorizes saving the spec after pre-flight and material questions are resolved. Do not ask for generic approval to write. Autofix keeps its separate `--yes` gate.

### 4.1 — Materialize and check the body

Write the complete body once to a literal unique path, `${TMPDIR:-/tmp}/flow-capture-draft-<working-title-slug>-<4-char suffix>.md`. Use that exact path in Phase 5's `spec set-plan --file`; never re-author the body in a heredoc. The body opens with `# <title>`, followed by `## Conversation Evidence` and the template sections.

Before any write, every per-line `[user]` tag must be findable in the verbatim user evidence. Retag a close restatement as `[paraphrase]`, an unsupported inference as `[inferred]`, and recompute the tally. Section-level breakdown notes remain informational. Material unknowns use Phase 3's questions; inferred content never becomes user-approved merely because it is saved.

If the split rule proposed N>1, resolve the explicit choice per [references/split-proposal.md](references/split-proposal.md). One spec needs no split question. A requested `--rewrite` uses [references/rewrite-mode.md](references/rewrite-mode.md), including the diff and protection of intervening user edits.

### 4.2 — Snapshot readiness before writing

Readiness is a separate follow-up after the spec exists. Capture the target-aware predicate now, before a rewrite resets the old ready flag. This step asks nothing and writes nothing:

```bash
ACTIVE=0
RAW="$("$FLOWCTL" config get tracker.readyState --json 2>/dev/null)" || ACTIVE=1
if [ "$ACTIVE" = "0" ]; then
  VAL="$(printf '%s' "$RAW" | jq -r '.value // empty' 2>/dev/null)" || ACTIVE=1
  [ -z "$VAL" ] && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
  echo "GATE ACTIVE — STOP. Read references/mark-ready.md before continuing."
fi   # default branch: bare no-op — NO link, NO read path
```

When the sentinel prints, read [references/mark-ready.md](references/mark-ready.md) and compute its §4.2 predicate only. Retain that snapshot for §5.9; do not probe the rewritten target as if it were its pre-write state. When the gate is silent, `tracker.readyState` is configured: no local readiness offer or write.

### 4.3 — Editor and correction handling

This handling runs from §5.6a after the spec has been saved. Open the actual spec file, never the temporary synthesis copy. When the editor is chosen, wait for the user to return, then re-read the full saved spec before any subsequent operation. Preserve user edits; do not overwrite them from the temporary file or infer that an edit is approval to execute.

For a correction supplied in chat, append the user's requirement or rejection verbatim to `## Conversation Evidence` first. Before agent-authored replacement, apply the source-tag checks, Phase 3 material-question checks, and the applicable §5.0 strategy contradiction check to the corrected body, then edit only the affected sections through the normal spec write plumbing.

After either editor changes or chat corrections, recheck source-tag findability, recompute the tally, and re-judge the recommended route when criteria changed. Preserve the user's substantive edits; unsupported source tags use the existing taxonomy rather than claiming user approval. Direct editor changes also pass the applicable §5.0 strategy check before tracker/readiness or other follow-ups: preserve the saved file and surface a new conflict rather than rolling it back. Show only the diff and updated tally; the full spec prints only on request.

There is no re-approval loop. `continue` leaves the saved spec in place; stopping the review also leaves it in place. Deletion needs an explicit request. A later capture invocation still follows the duplicate/rewrite checks rather than minting a replacement for an editor round.

### 4.4 — Autofix write gate

In autofix mode, follow [references/autofix-mode.md](references/autofix-mode.md), already loaded at mode detection: materialize the draft, print its summary, and write only with `--yes`. Without it, exit 0 with the draft path and no spec allocation. No interactive editor or consent questions run.

### Done when

- The body is materialized with verified source tags, any split choice is settled, and pre-rewrite readiness is captured when applicable.
- Interactive proceeds to Phase 5 without an approve-and-write question.
- Autofix proceeds only with `--yes`; otherwise the draft-only terminal has been reported.

---

## Phase 5: Write via flowctl (R14, R15, R16)

**Goal:** atomic write of the new (or rewritten) spec via existing flowctl plumbing.

### 5.0 — Strategy contradiction check

When Phase 0.3b's gate fired, run §5.0 from `references/strategy-alignment.md` **before any write** — it refuses a spec that contradicts an active track unless `--override-strategy` was passed, and records the override as a decision. When that gate was silent, there is no strategy snapshot to contradict and this step does not exist.

### 5.1 — The spec body is the §4.1 draft file

The source-checked draft file from §4.1 IS the input to `flowctl spec set-plan --file <literal draft path>` — never re-authored into a heredoc. Source tags **stay in the spec body** — they are part of the audit trail and survive into the on-disk spec at `.flow/specs/<id>.md`. Future readers (including `/flow-next:plan` and `/flow-next:refine`) see the tags and can scrutinize.

`spec set-plan` replaces the ENTIRE markdown file with the supplied body — the create-time placeholder (including its `# <title>` heading) does not survive. The captured body must therefore OPEN with a single `# <title>` heading of its own (verified live: a body without one ships a heading-less spec).

### 5.2 — New-spec branch

```bash
SPEC_TITLE="<chosen title from Phase 3 or Phase 1.3>"

# Tracker-first mint gate (distributed id allocation). Probe raw, rc-checked; parse separately.
ACTIVE=0
RAW="$("$FLOWCTL" sync active --json 2>/dev/null)" || ACTIVE=1     # probe ERROR ⇒ ACTIVE (fail open)
if [ "$ACTIVE" = "0" ]; then
  VAL="$(printf '%s' "$RAW" | jq -r '.active' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
  [ "$VAL" = "true" ] && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
  echo "GATE ACTIVE — STOP. Read references/tracker-integration.md before continuing."
fi   # default branch: bare no-op — NO link, NO read path

# SILENT degrade - the ONLY flow-first creation site, deliberately an
# unconditional post-check outside the tracker-first branch (rationale + the
# orphan-issue GUARD live in references/tracker-integration.md §5.2).
if [ -z "$SPEC_OUTPUT" ] && [ -z "$IDENTIFIER" ]; then
  SPEC_OUTPUT=$("$FLOWCTL" spec create --title "$SPEC_TITLE" --json)
fi
SPEC_ID=$(printf '%s' "$SPEC_OUTPUT" | jq -r '.id')

if [[ -z "$SPEC_ID" || "$SPEC_ID" == "null" ]]; then
  echo "Error: spec create failed: $SPEC_OUTPUT" >&2
  exit 1
fi

# Write the spec body from the §4.1 draft file — type the literal path verbatim
# from agent context (path-persistence rule: never a shell variable across tool calls).
"$FLOWCTL" spec set-plan "$SPEC_ID" --file "${TMPDIR:-/tmp}/flow-capture-draft-<working-title-slug>-<suffix>.md" --json

# Run anchor for Phase 6's sync check — written at the write step, BEFORE the
# 5.7 dispatch, so it lower-bounds this run's receipts.
date -u +%Y-%m-%dT%H:%M:%SZ > "${TMPDIR:-/tmp}/flow-capture-anchor-${SPEC_ID}"
```

When the tracker gate above printed, read [references/tracker-integration.md](references/tracker-integration.md) and run its §5.2 tracker-first mint (and, later in this phase, its §5.7 touchpoint) around the flow-first post-check. When the gate is silent, `spec create` mints `fn-N` locally and nothing tracker-related happens anywhere in this run.

The draft file round-trips embedded markdown and newlines byte-exact — `read_file_or_stdin` in `flowctl.py` handles `--file <path>` directly. No re-authoring: the synthesized content is consumed from disk without a second rendering.

When Phase 0.5b's chart gate fired, run that reference's §5.2 chart handoff — `chart link-spec` **only after** a successful `spec create` + `spec set-plan`, with its retry rules.

### 5.2b — Split branch

Reached only when the user picked `split-as-proposed` at §4.1; the ceremony lives in `references/split-proposal.md` §5.2b (compose all N bodies → run §5.2 once per spec in dependency order → `spec add-dep` per edge → summarize the saved specs). Autofix never reaches this branch.

### 5.3 — Rewrite branch

Reached only when `REWRITE_TARGET` is set; the ceremony lives in `references/rewrite-mode.md` §5.3 (skip `spec create`, `set-plan` the draft over the existing body, idempotent `spec unready` reset after set-plan, run anchor).

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

### 5.6a — Saved-spec review (interactive only)

After the spec body is written, read [docs/read-back.md](../../docs/read-back.md) for capture's saved-spec summary and editor offer. Print the title, criteria count, source tally, relevant warnings, recommended route, and actual spec path before asking. Include the rewrite diff when applicable; a full body prints only on request. For a split, show one summary per saved spec and offer the editor once for the set after all bodies and edges exist.

Use `AskUserQuestion` for one short editor question: `open in editor` opens the saved file(s); `continue` leaves them as written. Free text requests a correction. Apply §4.3 to editor/correction rounds, then continue the remaining authorized follow-ups without generic re-approval. Skip an already-answered editor offer, and honor a request to leave the spec for later review. The summary itself is always reported.

Saving or viewing the spec does not authorize marking ready, implementation, a commit, or an external write. Existing explicit instructions and configured tracker authority remain in force; do not manufacture a new confirmation for them.

### 5.7 — Tracker sync touchpoint (opt-in)

Runs only when §5.2's tracker gate fired: execute `references/tracker-integration.md` §5.7 (leaf-resolved push / pull / reconcile / comment, best-effort, `--event capture` receipt). With no tracker configured this step does not exist — capture behaves exactly as it always has.

### 5.8 — Glossary term-adds (consent-gated; interactive only)

When §2.7 found glossary proposals, ask the separate `Glossary?` question in [references/glossary-terms.md](references/glossary-terms.md), unless already answered. Write only the consented terms through its §5.8 call site. Autofix never writes terms.

### 5.9 — Mark-ready write (consent-gated; interactive only)

Use the §4.2 snapshot to offer the separate `Mark ready?` question per [references/mark-ready.md](references/mark-ready.md), only when eligible and not already answered by the user. `mark-ready` authorizes its write; `keep-draft` leaves readiness unchanged. Autofix never writes readiness.

### 5.9b - No-plan write

Runs on two paths and no other: `NO_PLAN_OPT=1` (`--no-plan` on the invocation - the explicit opt-in, in interactive AND autofix mode), or `FROM_FLOW=1` with the §2.8 judgment `ROUTE_DIRECT=1` (the plan-versus-no-plan rule, applied because flow dispatched the run). A user invocation without the flag never sets the field, whatever §2.8 judged: the recommendation prints, the write does not happen. After the spec write:

```bash
# Capture raw first, rc-checked; parse separately (one normalized line either way —
# a non-task failure keeps its real reason instead of being misreported as the
# task refusal).
if ! NO_PLAN_OUT="$("$FLOWCTL" spec set-no-plan "$SPEC_ID" --json 2>&1)"; then
  NO_PLAN_REASON="$(printf '%s' "$NO_PLAN_OUT" | jq -r '.error // empty' 2>/dev/null | head -1)"
  [ -z "$NO_PLAN_REASON" ] && NO_PLAN_REASON="$(printf '%s' "$NO_PLAN_OUT" | head -1)"
  echo "no_plan not set: ${NO_PLAN_REASON:-unknown error} — field left unchanged"
fi
```

Best-effort like §5.8/§5.9: a refusal (the verb refuses when the spec already has tasks — reachable only on a `--rewrite` of a planned spec) or failure prints the one-line notice and the run continues; the spec write is never rolled back. A fresh capture has no tasks yet, so a draft that merely implies multiple tasks still sets cleanly — the set-time refusal guards task presence only.

### 5.10 — HTML render lens (opt-in) — spec artifact + link line

```bash
ACTIVE=0
RAW="$("$FLOWCTL" config get artifacts.html.enabled --json 2>/dev/null)" || ACTIVE=1   # probe ERROR ⇒ ACTIVE (fail open)
if [ "$ACTIVE" = "0" ]; then
  VAL="$(printf '%s' "$RAW" | jq -r 'if .value == true then "true" else "false" end' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
  [ "$VAL" = "true" ] && ACTIVE=1
fi
if [ "$ACTIVE" = "1" ]; then
  echo "GATE ACTIVE — STOP. Read references/html-lens.md before continuing."
fi   # default branch: bare no-op — NO link, NO read path
```

When the sentinel prints, read [references/html-lens.md](references/html-lens.md) and follow it — the spec-artifact generation, the disclosure-reference load, the link-line write, and the Lavish companion. When the gate is silent (off or unset): **skip entirely** — write no artifact, print no artifact output. The one-line gate read above is the only cost.

### Done when

- The new (or rewritten) spec is on disk at `.flow/specs/<id>.md`.
- `SPEC_ID` is known for Phase 6.
- Optional branch-name is set if user named one.
- When the tracker bridge is active and `capture` is opted in, the spec body was pushed/pulled/reconciled to the linked issue (5.7); otherwise this step was a silent no-op.
- Approved glossary term-adds written (5.8); skipped silently when none were proposed or approved.
- Mark-ready write applied iff separately consented (5.9); rewrite branch reset readiness via idempotent `unready` with `READY_RESET` recorded for Phase 6 (5.3).
- No-plan write applied iff `--no-plan` was passed, or `from:flow` with a direct judgment (5.9b); skipped silently otherwise, with the refusal notice printed when the set was refused.
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

**Retro-fire on MISSING:** when `.missing` is non-empty, run `references/tracker-integration.md` § Phase 6 — exactly ONE cycle, never blocking, then record the final state in the footer slot. When the check is empty or `.missing` is empty, no retro-fire exists.

Then the footer. `Tracker sync:` is a REQUIRED line with exactly four states — an explicit `n/a` proves the check ran; an absent line is a skipped check:

```text
Spec captured at .flow/specs/<SPEC_ID>.md.
Tracker sync: <OK | MISSING:capture → retro-fired → OK | MISSING:capture (retro-fire failed: <reason>) | n/a (bridge inactive)>

Recommended next: /flow-next:<stage> <SPEC_ID> — <one-clause reason>; <named alternative when it applies>

Next:
  /flow-next:work <SPEC_ID> --no-plan → execute the cohesive spec
  /flow-next:plan-review <SPEC_ID> → assess the spec design
  /flow-next:plan <SPEC_ID>      → research + break into tasks
  /flow-next:refine <SPEC_ID> → refine via Q&A
  /flow-next:visual <SPEC_ID>    → compact visual digest — review the spec at a glance
```

The `Recommended next:` line is MANDATORY every run. It prints the §2.8 judgment from [`plan-vs-no-plan.md`](../flow-next-flow/references/plan-vs-no-plan.md) in that file's shape, with the spec id filled in (re-judge only when an edit cycle changed the criteria). When signals conflict, recommend `/flow-next:flow --explain <SPEC_ID>`. This is an informational recommendation with a reason, never a readiness write or permission to execute.

**Host command form:** print every copy-pasteable flow-next command here in the spelling this host invokes — the flat `/flow-next-<name>` form when the resolved plugin root carries `.flow-next-opencode-manifest` (an OpenCode install — the same signal setup's host detection uses); on any other or indeterminate host, exactly as spelled here.

Optional lines appended after `Tracker sync:`, each owned by the reference whose gate fired - `Glossary: added N term(s) (…)` (§5.8), `Readiness: marked ready` (§5.9), `No-plan: field set (flow --auto/work take the direct route)` (§5.9b, on `--no-plan` or the rule under `from:flow` - or the refusal notice when the set was refused), `Artifact: .flow/artifacts/<SPEC_ID>/spec.html (render lens - regenerable; markdown is the record)` (§5.10). Omit each entirely otherwise - zero noise outside the consented / enabled path.

The rewrite footer variant (prefix `Spec rewritten at …`, readiness-reset announcement, re-plan hint) lives in `references/rewrite-mode.md`; the split footer (one block per created spec + shared dependency-edge line) lives in `references/split-proposal.md`.

### Biz-suggestion footer (R25)

When the conversation has business-context signals but the business layer is sparse, append a one-line suggestion to refine via `/flow-next:refine --scope=business`. The R25 business-pass suggestion fires when the captured conversation names 1-2 distinct R24 signal categories (the same `1 <= n < 3` rule), agent-judged. Input is `$BIZ_SIGNAL_CATEGORIES` — the count computed in [§2.6](#26--biz-context-signal-routing-r24--signal-category-count-for-r25) over the nine SIGNAL CATEGORIES from R24 (target user / problem framing / success metric / MVP boundary / business constraints / what-not-to-build / prioritization rationale / business risks / UX expectations). The count is over categories, not over markdown destinations. R22: `BIZ_SIGNAL_CATEGORIES=0` → no-fire (solo-dev silence). Count `>= 3` → no-fire (biz layer adequately filled).

```bash
# R25 threshold is host-agent judgment (former flowctl helper removed).
# Fire when 1 <= BIZ_SIGNAL_CATEGORIES < 3; otherwise stay silent.
if [ "$BIZ_SIGNAL_CATEGORIES" -ge 1 ] && [ "$BIZ_SIGNAL_CATEGORIES" -lt 3 ]; then
  cat <<EOF

This conversation has business-requirements signals; consider
\`/flow-next:refine --scope=business $SPEC_ID\` to deep-refine the
business layer.
EOF
fi
```

The literal suggestion phrasing matches the R25 spec verbatim ("business-requirements signals; consider `/flow-next:refine --scope=business <spec-id>`") so the surface text stays generic — capture does not enumerate which categories triggered the suggestion. Informational only — never a blocking prompt.

If Phase 0.3 found memory hits, append the related-context footer:

```text
Related context (existing memory): <comma-separated entry ids>
Consider reviewing before /flow-next:plan to avoid re-solving documented problems.
```

### Done when

- End-of-run `sync check` ran (`--events capture`, `--since` = the Phase-5 run anchor, falling back to `created_at` for fresh captures); any MISSING touchpoint was retro-fired exactly once and re-checked.
- Footer is printed with the mandatory four-state `Tracker sync:` line (explicit `n/a (bridge inactive)` when no tracker is configured).
- Skill exits 0.

---

Maintainer validation (not part of a run): [references/manual-smoke.md](references/manual-smoke.md).
