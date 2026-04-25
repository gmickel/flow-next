---
satisfies: [R17, R18, R19]
---

## Description

Fold three high-value patterns from upstream `grill-me` (`/tmp/skills/grill-me/SKILL.md`) into the existing `/flow-next:interview` skill. Tight scope: ~50 lines of skill-text additions across 2 files, no new skill, no new slash command, no breaking changes to interview's existing behavior. Interview still does what it always did — just better.

**Size:** S → M (small surface; M because three patterns each need careful prose + at least one example)
**Files:**
- `plugins/flow-next/skills/flow-next-interview/SKILL.md` (extend Interview Process section at lines 76-93)
- `plugins/flow-next/skills/flow-next-interview/questions.md` (extend with codebase-vs-user taxonomy)

## Approach

### Rule 1: Lead-with-recommendation (R17)

**Edit target:** `flow-next-interview/SKILL.md:76-93` (Interview Process section).

Add a new sub-section after the existing "USE AskUserQuestion" block:

```markdown
### Question Format: Lead with Recommendation

Every `AskUserQuestion` body must include the agent's recommended option AND a confidence tier. Canonical skill text uses Claude-native tool name (mirror `flow-next-audit/SKILL.md:62`); sync-codex.sh rewrites to `request_user_input` in the Codex mirror per repo convention. Call `ToolSearch select:AskUserQuestion` first if the schema isn't loaded. Fallback: numbered options in plain text only when the tool is unreachable.

Pattern:

- `question.body`: "<options summary>. Recommended: <X> — <one-sentence rationale>. Confidence: [high | judgment-call | your-call]."
- `question.options`: neutral labels (no "(recommended)" markers — the recommendation goes in the body, anchoring is reduced when options stay neutral)

Confidence tiers:

- `[high]` — strong codebase signal or convention match. Recommendation is load-bearing; user can usually accept.
- `[judgment-call]` — slight lean but reasonable people disagree. User's call carries weight.
- `[your-call]` — agent has no signal. "I genuinely don't know — your priority / domain knowledge / preference."

The third tier is mandatory: skills that always recommend train users to defer (RLHF imitation of human bravado). When the agent has no basis for a recommendation, say so explicitly.

Reference language: `flow-next-audit/SKILL.md:64` ("Lead with the recommended option and a one-sentence rationale").
```

### Rule 2: Explore-codebase-before-asking (R18)

**Edit target:** `flow-next-interview/questions.md` (extend with pre-question taxonomy).

Add a new section near the top of `questions.md`:

```markdown
## Pre-Question Taxonomy

Before asking any question, classify it:

| Category | Who answers | Examples |
|----------|-------------|----------|
| **Codebase-answerable** | Agent (Read/Grep/Glob) | "What persistence layer is used?" / "Where do existing routes live?" / "What's the test framework?" |
| **User-judgment-required** | User (AskUserQuestion) | "Should we add caching?" / "What's the priority for offline support?" / "Is performance or simplicity more important here?" |

**Rule of thumb:**
- "What exists / how is it wired / what conventions live here" → agent investigates, doesn't ask
- "What should exist / what tradeoff to make / what priority" → user decides, agent asks

**If you find yourself answering a "should" question via grep, that's the bug.** Stop and ask the user.

Investigation logging: every question the agent answered via codebase exploration goes into a new `## Resolved via Codebase` section in the spec output (separate from `## Asked User`). This audit trail lets reviewers spot-check assumptions later — especially important when the agent's "I checked" turns out to be "I assumed."
```

Plus update `flow-next-interview/SKILL.md`'s "Write Refined Spec" phase template (lines 117-137) to include the new section:

```diff
 ## Problem
 ## Key Decisions
 ## Edge Cases
+## Resolved via Codebase
+(items the agent answered via Read/Grep/Glob during the interview, with file:line evidence — separate from user-answered items)
 ## Open Questions
 ## Acceptance
```

(Apply to both NEW IDEA and EXISTING EPIC templates in the file.)

### Rule 3: Dependency-ordered branches (R19)

**Edit target:** `flow-next-interview/SKILL.md:76-93` (continue Interview Process section).

Add another sub-section:

```markdown
### Question Order: Walk the Decision Tree

Walk down branches of the decision tree in dependency order. Don't ask about implementation details before establishing whether they're needed.

Concrete rules:

1. **Cap branch depth at 4.** Research shows >4 prior turns rarely improves question quality — drop deeper threads, ask about something else.
2. **Discover-as-you-go**, not pre-compute. Adapt the next question based on prior answers, don't lock a tree before you start.
3. **Surface abandoned branches.** When an answer prunes a sub-tree, say so: "Skipping persistence questions — you said no DB."
4. **One question per turn**, period. Multi-question turns overwhelm users (research-confirmed). Group related options into a SINGLE question with multi-select if needed; don't queue separate questions.

Example flow:

> Q: "Does this feature need persistence?"
> A: "No, ephemeral state is fine."
> [agent prunes the {DB choice, schema design, migration plan} sub-tree]
> Q: "Skipped DB questions — you said ephemeral. Next: how does this state live across page reloads?"
```

### What NOT to change

- Existing interview phases (Setup, Detect Input Type, Question Categories, Write Refined Spec)
- Existing `AskUserQuestion` mandate (the tool is still required for every question)
- Existing question categories in `questions.md`
- Existing 40+-question heuristic for complex specs
- Existing flow ID handling (epic / task / file path / new idea)

These three rules are additive enhancements to **how** questions are asked, not **what** is asked.

## Investigation targets

**Required:**
- `/tmp/skills/grill-me/SKILL.md` — upstream reference (10 lines; the source of these three rules)
- `plugins/flow-next/skills/flow-next-interview/SKILL.md` — full file, especially Interview Process section (lines 76-93)
- `plugins/flow-next/skills/flow-next-interview/questions.md` — current question categories + guidelines (lines 77-85)
- `plugins/flow-next/skills/flow-next-audit/SKILL.md:64` — canonical "lead with the recommended option" phrasing to mirror
- `plugins/flow-next/skills/flow-next-interview/SKILL.md:117-137` — "Write Refined Spec" templates (NEW IDEA and EXISTING EPIC) to extend with `## Resolved via Codebase` section

**Optional:**
- `plugins/flow-next/skills/flow-next-capture/phases.md` — confidence-tier definitions (Task 1 documents these; reuse if helpful for cross-skill consistency)

## Key context

- Don't introduce new mandatory headers in the spec template — `## Resolved via Codebase` should be optional (omit if nothing was resolved that way during interview).
- The `[your-call]` confidence tier is the most novel; without it agents always-recommend, which trains users to defer. Worth a sentence in the rationale.
- Cap branch depth at 4 is a heuristic from elicitation research; tune if it surfaces as too restrictive in real use (deferred to follow-up).
- The "if you find yourself answering a 'should' question via grep, that's the bug" rule is the most actionable signal. Bake it explicitly.
- This task does NOT add a new spec section requirement — `## Resolved via Codebase` is optional, lives alongside existing sections.
- Don't change `flow-next-interview/SKILL.md` line numbers materially. The file has stable structure; insert sub-sections, don't refactor.

## Acceptance

- [ ] `flow-next-interview/SKILL.md` Interview Process section (lines ~76-93) extended with "Question Format: Lead with Recommendation" sub-section. Recommendation goes in question body; options stay neutral. Three confidence tiers (`[high]` / `[judgment-call]` / `[your-call]`) documented with one example each. (R17)
- [ ] `flow-next-interview/SKILL.md` Interview Process section also extended with "Question Order: Walk the Decision Tree" sub-section. Cap depth at 4; discover-as-you-go; surface abandoned branches; one-question-per-turn reaffirmed. (R19)
- [ ] `flow-next-interview/questions.md` extended with "Pre-Question Taxonomy" section near top. Codebase-answerable vs user-judgment-required examples; "if answering 'should' via grep, that's the bug" rule. (R18)
- [ ] `flow-next-interview/SKILL.md` "Write Refined Spec" phase templates (lines ~117-137) updated: both NEW IDEA and EXISTING EPIC templates include optional `## Resolved via Codebase` section between `## Edge Cases` and `## Open Questions`. (R18)
- [ ] No breaking changes to existing interview behavior. Existing phases / categories / Q&A loop intact.
- [ ] No new flowctl subcommands. Pure skill-text changes.
- [ ] Cross-check: re-read full interview SKILL.md + questions.md after edits, verify additions feel natural and don't contradict existing language.


## Done summary

(populated when task completes)

## Evidence

(populated when task completes)
