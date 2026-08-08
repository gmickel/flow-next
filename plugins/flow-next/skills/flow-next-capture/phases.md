# Capture — source-tag taxonomy, confidence tiers, decision tree

This file is the lookup-and-calibration companion to [workflow.md](workflow.md). The workflow drives the phases in order; this file holds the two calibration surfaces every run consumes (source tags, confidence tiers) plus the whole-run decision tree.

Path-specific lookups live one level deep in `references/*.md` and are loaded only when workflow.md's gate at that branch point fires — must-ask case detail, chart-briefing provenance, split proposals, glossary, readiness, rewrite, tracker, autofix. The per-phase `Done when` checklists live at the end of each workflow.md phase (single copy).

| Phase | Goal |
|-------|------|
| **0 — Pre-flight** | Detect duplicates, compaction, idempotency conflict before drafting |
| **1 — Extract conversation evidence** | Build verbatim `## Conversation Evidence` block FIRST |
| **2 — Source-tagged synthesis** | Draft spec sections with per-line tags using the canonical template |
| **3 — Must-ask cases** | Resolve ambiguous-title / untestable-acceptance / scope-conflict |
| **4 — Read-back loop** | Print full draft as ordinary markdown, then short ask; obtain approval |
| **5 — Write via flowctl** | Atomic write of new (or rewritten) spec |
| **6 — Suggested next step** | Print footer with `/flow-next:plan` and `/flow-next:interview` hints |

---

## Source-tag taxonomy (R4)

Every acceptance criterion line, every decision-context line, every scope-bounding line carries one tag. Pure-prose narrative sections carry a section-level note instead (e.g. `<!-- Goal & Context: 70% [user], 30% [inferred] -->`).

| Tag | Meaning | Acceptance test |
|-----|---------|-----------------|
| `[user]` | Verbatim from conversation evidence (exact quote or close paraphrase preserving meaning) | The user said this, in these or similar words. Reasonable people would agree it's the user's stated intent. |
| `[paraphrase]` | User intent restated in spec language (semantic equivalence; no new constraints introduced) | The user expressed this idea, but agent rephrased to match spec conventions. Same content, cleaner wording. |
| `[inferred]` | Agent fill-in (most-scrutinized; user must confirm at read-back) | Agent decided this; user did not state it explicitly. May be a reasonable default, may be wrong. |
| `[strategy:<track>]` | Derived from `STRATEGY.md` content (verbatim or near-verbatim quote of approach / track body) | The criterion follows directly from a populated section in `STRATEGY.md` — the track name appears literal in the tag. Activates only when Phase 0 strategy snapshot is present. |

### Biz-context signal routing (R24)

The nine-category routing table and its rules live **inline at [workflow.md §2.6](workflow.md)**, directly beside the §2.2 drafting step that consumes them — the single copy (proximity is accuracy-load-bearing; do not re-duplicate the table here). Section names in that table are anchors in the canonical template at [`plugins/flow-next/templates/spec.md`](../../templates/spec.md) (per R17 — never re-embed the section list inline), resolved at runtime via the 4-tier discovery cascade described in workflow.md §2.2. The signal-category count the routing produces is the `BIZ_SIGNAL_CATEGORIES` value Phase 6 agent-judges against the R25 threshold (`1 <= n < 3`) for the business-pass suggestion.

### Examples

| Conversation evidence | Acceptance line | Tag |
|-----------------------|-----------------|-----|
| `> user (turn 4): "rate limit must reject 3+ requests per second from a single client"` | `- **R1:** Rate limit rejects ≥3 req/sec from a single client. [user]` | `[user]` |
| `> user (turn 7): "we should write the spec body atomically so partial writes don't corrupt"` | `- **R5:** Spec writes are atomic — partial-write recovery preserves prior state. [paraphrase]` | `[paraphrase]` |
| (no user mention of error format) | `- **R7:** Errors include the request id for trace correlation. [inferred]` | `[inferred]` |
| (STRATEGY.md `### Reliability` track says "we ship for 99.95% uptime") | `- **R9:** Service-level objective: 99.95% uptime measured monthly. [strategy:Reliability]` | `[strategy:Reliability]` |

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
- **`[strategy:<track>]`** is for content the agent imported from `STRATEGY.md` — verbatim or near-verbatim quote from the `approach` line or one of the `### <track-name>` H3 sub-blocks. The track name lives literally in the tag (e.g. `[strategy:Reliability]`). The criterion is treated as load-bearing for the strategy alignment surface; if the spec body contradicts a `[strategy:*]` line, capture refuses to write without `--override-strategy` (see SKILL.md).

A spec with 0 `[inferred]` items is rare and probably means the conversation was unusually thorough. A spec with 30 `[inferred]` items is suspicious — the conversation was probably too thin for capture, and the user should pursue `/flow-next:interview` instead.

Chart D-ID evidence, chart facts, assets, and briefing membership are **never** source-tagged — the four-tag grammar applies only to acceptance criteria this capture pass newly authors. The full provenance-lane rule loads with the chart-briefing gate (workflow.md §0.5b).

---

## Confidence tiers

Used in Phase 3 (must-ask) and Phase 4 (read-back) recommendation bodies. The body carries the confidence; option labels stay neutral so the user isn't anchored on the tier itself.

| Tier | When to use | Example body |
|------|-------------|--------------|
| `[high]` | Agent has strong codebase signal or convention match; recommendation is load-bearing | `Recommended: extend fn-12-oauth-callback — strong title overlap (3 strong matches) + same module. Confidence: [high].` |
| `[judgment-call]` | Slight lean but reasonable people disagree; user's call carries weight | `Recommended: proceed-anyway — overlap is moderate (2 matches), specs may legitimately co-exist. Confidence: [judgment-call].` |
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

## Forbidden behaviors (R10)

The full list lives in [SKILL.md](SKILL.md) — single copy. Branch-specific rows (chart provenance, split, glossary, readiness) repeat at the bottom of the reference their gate loads.

---

## Decision tree (quick reference)

```
Ralph mode? (FLOW_RALPH=1 or REVIEW_RECEIPT_PATH set)
  yes → exit 2 with Ralph-block message (see SKILL.md)
  no  → continue

Compaction signal detected?
  no  → continue
  yes → evidence needed for this capture missing / truncated / summary-only?
          no  → continue; note prior compaction in Phase 4 warnings
          yes → --from-compacted-ok set?
                  no  → refuse with override hint (interactive); exit 2 (autofix)
                  yes → continue

Duplicate detection: ≥2 strong spec-title matches AND --rewrite not set?
  yes → gate → ask: extend / supersede / proceed-anyway / abort (interactive); exit 2 (autofix)
  no  → continue

Prior-capture artifact id detected in conversation AND --rewrite not set?
  yes → gate → ask: rewrite / proceed / abort (interactive); exit 2 (autofix)
  no  → continue

--rewrite target invalid or missing?
  yes → exit 2 with hint
  no  → continue

Extract conversation evidence → draft spec → tag every line.

Must-ask cases: ambiguous title / untestable acceptance / scope-conflict?
  any fired → gate → ask one at a time (interactive); exit 2 (autofix)
  none      → continue

Read-back (print-then-ask): print FULL draft markdown (+ rewrite diff if any)
  as ordinary assistant message, then SHORT ask (pointer + [inferred] tally +
  8+ note + options only — never multi-paragraph content in the ask body).
  interactive: approve / split-as-proposed (only when 2.5 proposed N>1) / edit / abort
  edit cycles: reprint revised draft before each short re-ask
  autofix --yes: print summary and proceed
  autofix without --yes: print summary and exit 0

Approved? Write via flowctl spec create + spec set-plan.

Glossary proposals approved at read-back? (interactive only; gate: total_terms > 0)
  yes → write each via flowctl glossary add (best-effort, never blocks)
  no  → continue

Print next-step footer. Done.
```

In autofix mode, every "ask" branch becomes "exit 2". Capture cannot guess on must-ask cases. Glossary term-adds are never written in autofix — proposals print as suggestions only.
