# Capture — phase reference, must-ask cases, source-tag taxonomy, confidence tiers

This file is the lookup-and-calibration companion to [workflow.md](workflow.md). The workflow drives the phases in order; this file is what you re-read when a specific case fires.

---

## Phase reference

| Phase | Goal | Done-when |
|-------|------|-----------|
| **0 — Pre-flight** | Detect duplicates, compaction, idempotency conflict before drafting | Conversation keywords extracted; epic-title overlap scanned; memory cross-check (if memory initialized); compaction passed (or `--from-compacted-ok`); idempotency resolved (`REWRITE_TARGET` validated, or no prior-capture artifact, or user picked supersede/proceed) |
| **1 — Extract conversation evidence** | Build verbatim `## Conversation Evidence` block FIRST | ≤30-line block of `> user (turn N): "..."` lines drafted; optional file-reference subagent results merged; candidate title proposed |
| **2 — Source-tagged synthesis** | Draft spec sections with per-line tags using CLAUDE.md richer template | Every section drafted; R-IDs allocated sequentially from R1; `[inferred]` count computed; 8+ acceptance flag set if applicable; untestable criteria flagged for Phase 3 |
| **3 — Must-ask cases** | Resolve ambiguous-title / untestable-acceptance / scope-conflict | Interactive: user resolved each fired case; autofix: exit 2 with which case fired |
| **4 — Read-back loop** | Show full draft + `[inferred]` tally; obtain approval | Interactive: `approve` / `consider-split` / `abort`; autofix `--yes`: payload printed; autofix without `--yes`: payload printed + exit 0 |
| **5 — Write via flowctl** | Atomic write of new (or rewritten) epic | `.flow/specs/<id>.md` exists; `EPIC_ID` known |
| **6 — Suggested next step** | Print footer with `/flow-next:plan` and `/flow-next:interview` hints | Footer printed; skill exits 0 |

---

## Must-ask cases (R9)

The three hard-error conditions that fire in Phase 3. Interactive asks; autofix exits 2.

### Case (a) — Ambiguous title

**Trigger:** Phase 1.3 candidate title is `[inferred]` AND the conversation supports multiple plausible titles, none load-bearing.

**Why hard-error:** an ambiguous title leads to bad epic ids, bad branch names, bad git history. The cost of asking is one question; the cost of guessing wrong is renaming the epic later.

**Examples:**

- Conversation: "let me think about this rate limiting problem... maybe we need throttling... or queue depth... or per-tenant quotas". Candidate titles: `Rate limiting`, `Request throttling`, `Per-tenant quotas`. None of those is load-bearing in the conversation. → must-ask.
- Conversation: "the OAuth callback is broken when X happens". Candidate title: `Fix OAuth callback X bug`. Specific. → no must-ask.

**Interactive question shape:**

- header: `Title?`
- body: `Conversation supports multiple titles. Recommended: <X> — <one-sentence rationale>. Confidence: [<tier>]. (Other plausible: <Y>, <Z>.)`
- options: `<X>`, `<Y>`, `<Z>`, `custom`

**Autofix:** exit 2 with: `Must-ask (a): epic title genuinely ambiguous from conversation. Candidates: <X>, <Y>, <Z>. Re-run interactively to choose.`

### Case (b) — Untestable acceptance

**Trigger:** Phase 2.4 flagged ≥1 acceptance criterion that fails the testability check. A criterion is testable if a reviewer can point at code / behavior / config and say "satisfied" or "not satisfied" with two engineers agreeing.

**Why hard-error:** untestable acceptance criteria turn into "done when the user feels good", which never closes. Capture's purpose is producing a usable spec; vague acceptance defeats that.

**Examples:**

- Untestable: `- **R3:** Make it fast.` (fast how?)
- Untestable: `- **R4:** Improve UX.` (improve how — measured how?)
- Testable: `- **R3:** Median p95 latency under 200ms for the OAuth callback path.`
- Testable: `- **R4:** Form errors render inline within 100ms of input blur.`

**Interactive question shape (per-criterion):**

- header: `Criterion R<n>`
- body: `"<criterion>" can't be made testable as written. Recommended: <reword candidate> — <rationale>. Confidence: [<tier>]. (Or drop / clarify in your own words.)`
- options: `<reword candidate>`, `drop`, `clarify`

If user picks `clarify`, follow-up question accepts free text → re-run testability check on the new wording.

**Autofix:** exit 2 with: `Must-ask (b): <N> criteria failed testability check: <list>. Re-run interactively to reword or drop.`

### Case (c) — Scope-conflict with existing epic

**Trigger:** Phase 0.5 went `supersede` or `proceed-anyway` (user accepted a duplicate-ish epic), AND the new epic's drafted scope (Phase 2) still substantively overlaps the existing epic's scope on a load-bearing axis (same module + same problem domain, even if framed differently).

**Why hard-error:** if the new epic is "in addition to" the old one, the boundaries between them must be explicit. Otherwise the next time someone runs `/flow-next:plan`, both epics fight over the same tasks.

**Examples:**

- Old epic: `OAuth callback rate limiter` (in progress, 2 tasks done). New conversation: "we need rate limiting on the API". User picks `proceed-anyway`. New scope drafted as "all API endpoints" — explicit superset of old. → must-ask: how do the two epics carve up the rate-limit space?
- Old epic: `OAuth callback rate limiter`. New conversation: "we need rate limiting on the GraphQL endpoint". New scope: GraphQL only. → no must-ask. Boundaries are clear.

**Interactive question shape:**

- header: `Boundary?`
- body: `Old epic <id> "<title>" overlaps new epic on <axis>. Recommended: <X> (carve out <bound>) — <rationale>. Confidence: [<tier>].`
- options: `carve-by-module`, `carve-by-feature`, `mark-old-as-subsumed`, `keep-overlap-and-let-plan-resolve`

**Autofix:** exit 2 with: `Must-ask (c): scope conflict with existing epic <id>. Re-run interactively to disambiguate.`

---

## Source-tag taxonomy (R4)

Every acceptance criterion line, every decision-context line, every scope-bounding line carries one tag. Pure-prose narrative sections carry a section-level note instead (e.g. `<!-- Goal & Context: 70% [user], 30% [inferred] -->`).

| Tag | Meaning | Acceptance test |
|-----|---------|-----------------|
| `[user]` | Verbatim from conversation evidence (exact quote or close paraphrase preserving meaning) | The user said this, in these or similar words. Reasonable people would agree it's the user's stated intent. |
| `[paraphrase]` | User intent restated in spec language (semantic equivalence; no new constraints introduced) | The user expressed this idea, but agent rephrased to match spec conventions. Same content, cleaner wording. |
| `[inferred]` | Agent fill-in (most-scrutinized; user must confirm at read-back) | Agent decided this; user did not state it explicitly. May be a reasonable default, may be wrong. |

### Examples

| Conversation evidence | Acceptance line | Tag |
|-----------------------|-----------------|-----|
| `> user (turn 4): "rate limit must reject 3+ requests per second from a single client"` | `- **R1:** Rate limit rejects ≥3 req/sec from a single client. [user]` | `[user]` |
| `> user (turn 7): "we should write the spec body atomically so partial writes don't corrupt"` | `- **R5:** Spec writes are atomic — partial-write recovery preserves prior state. [paraphrase]` | `[paraphrase]` |
| (no user mention of error format) | `- **R7:** Errors include the request id for trace correlation. [inferred]` | `[inferred]` |

### Section-level tags

For prose sections (Goal & Context, Architecture & Data Models when written as narrative):

```markdown
## Goal & Context

<!-- Source-tag breakdown: 70% [user] / 20% [paraphrase] / 10% [inferred] -->

The OAuth callback path currently has no rate limiting, which means a misbehaving
client can drive 10+ requests/sec... [the rest of the prose; tag breakdown above
tells the reader what's verbatim vs synthesized]
```

The breakdown is informational at read-back. Phase 4's `[inferred]` tally counts both per-line tags and section-level inferred percentages.

### When to use which

- **`[user]`** is for content the user can read and recognize as their own words. Acceptance criteria and rejected alternatives benefit most from this tag.
- **`[paraphrase]`** is for spec-language restatements where the meaning is preserved but the wording is the agent's. Most decision-context and architecture-overview content lands here.
- **`[inferred]`** is for content the user did not state but the agent decided was necessary for a complete spec. **Defaults are `[inferred]`** — error-format conventions, status code choices, retry policies, observability hooks. Surface them at read-back so the user can keep / edit / drop.

A spec with 0 `[inferred]` items is rare and probably means the conversation was unusually thorough. A spec with 30 `[inferred]` items is suspicious — the conversation was probably too thin for capture, and the user should pursue `/flow-next:interview` instead.

---

## Confidence tiers

Used in Phase 3 (must-ask) and Phase 4 (read-back) recommendation bodies. The body carries the confidence; option labels stay neutral so the user isn't anchored on the tier itself.

| Tier | When to use | Example body |
|------|-------------|--------------|
| `[high]` | Agent has strong codebase signal or convention match; recommendation is load-bearing | `Recommended: extend fn-12-oauth-callback — strong title overlap (3 strong matches) + same module. Confidence: [high].` |
| `[judgment-call]` | Slight lean but reasonable people disagree; user's call carries weight | `Recommended: proceed-anyway — overlap is moderate (2 matches), epics may legitimately co-exist. Confidence: [judgment-call].` |
| `[your-call]` | Agent has no signal; user's domain knowledge / priority / preference decides | `Recommended: <none> — I don't have enough context to recommend. Pick what fits your priority. Confidence: [your-call].` |

The `[your-call]` tier exists deliberately. Always recommending trains users to defer; sometimes the honest answer is "I don't know — you pick". Don't hide that under `[judgment-call]`.

### Pairing recommendations with options

- `[high]`: recommendation strongly informs the default — but the option label still doesn't carry it. Body says "recommended", options stay neutral.
- `[judgment-call]`: recommendation is a lean. The body explains the lean and the trade-off; the user picks.
- `[your-call]`: skip the "recommended" pattern entirely. Body lists options with their trade-offs, no preference. Options stay neutral as always.

### What the recommendation IS NOT

- It is not a vote.
- It is not a binding default that fires if the user doesn't reply within a timeout (capture has no timeout — `AskUserQuestion` is blocking).
- It is not a marker that should appear ON the option label (anchoring research: F2.1).

---

## Forbidden behaviors (R10) — recap

The full list lives in [SKILL.md](SKILL.md). Quick reference:

| Forbidden | Why |
|-----------|-----|
| Tech-stack mentions the user did not state | Capture writes intent; `/flow-next:plan` writes implementation. Spec-kit convention. |
| Inventing acceptance criteria not in conversation | Source-tagging exists to make this visible. Pure `[inferred]` acceptance must surface at read-back for explicit user confirmation. |
| Code snippets / specific file paths in spec body | Those belong in `/flow-next:plan` task specs after research lands. Capture's output is high-level. |
| Silent overwrite of existing epic | Idempotency requires `--rewrite <id>`. Without it, Phase 0 conflict-detection branches into extend / supersede / proceed-anyway. |
| Auto-splitting an 8+ acceptance epic | Phase 4 surfaces the option; the user decides. Capture never auto-actions a split. |
| Setting `context: fork` | Blocking-question tools must stay reachable. |
| Calling `flowctl epic create` before Phase 4 approval | Phase 5 is the only write phase. |
| `git add -A` from this skill | Stage only `.flow/epics/<id>.json` + `.flow/specs/<id>.md` (and `.flow/meta.json` if mutated). Capture does NOT commit by default — user owns staging. |

---

## Decision tree (quick reference)

```
Ralph mode? (FLOW_RALPH=1 or REVIEW_RECEIPT_PATH set)
  yes → exit 2 with Ralph-block message (see SKILL.md)
  no  → continue

Compaction detected without --from-compacted-ok?
  yes → refuse with overrides hint (interactive); exit 2 (autofix)
  no  → continue

Duplicate detection: ≥2 strong epic-title matches AND --rewrite not set?
  yes → ask: extend / supersede / proceed-anyway / abort (interactive); exit 2 (autofix)
  no  → continue

Prior-capture artifact id detected in conversation AND --rewrite not set?
  yes → ask: rewrite / proceed / abort (interactive); exit 2 (autofix)
  no  → continue

--rewrite target invalid or missing?
  yes → exit 2 with hint
  no  → continue

Extract conversation evidence → draft spec → tag every line.

Must-ask cases: ambiguous title / untestable acceptance / scope-conflict?
  any fired → ask one at a time (interactive); exit 2 (autofix)
  none      → continue

Read-back: show full draft + [inferred] tally + 8+ note + diff (if rewrite).
  interactive: approve / edit / consider-split / abort
  autofix --yes: print and proceed
  autofix without --yes: print and exit 0

Approved? Write via flowctl epic create + epic set-plan.

Print next-step footer. Done.
```

In autofix mode, every "ask" branch becomes "exit 2". Capture cannot guess on must-ask cases.
