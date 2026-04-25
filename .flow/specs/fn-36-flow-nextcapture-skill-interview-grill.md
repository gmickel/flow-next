# /flow-next:capture skill + interview grill-me enhancements

## Overview

Two related improvements to the upstream-of-implementation flow:

1. **`/flow-next:capture`** — new agent-native skill that synthesizes conversation context into a flow-next epic spec. Adapted from upstream `to-prd` (`/tmp/skills/to-prd`). Bridges the gap between free-form discussion (or `/flow-next:prospect` artifact promotion) and the formal `/flow-next:plan` task breakout. Output goes to `.flow/specs/<epic-id>.md` via `flowctl epic create + epic set-plan` — NOT a GitHub issue (we use flowctl epics for tracking).

2. **`/flow-next:interview` enhancements** — fold three high-value patterns from upstream `grill-me` (`/tmp/skills/grill-me`) into the existing interview skill:
   - **Lead-with-recommendation** — every question carries an explicit recommendation + confidence tier
   - **Explore-codebase-before-asking** — investigate before asking; classify questions by who answers
   - **Dependency-ordered branches** — walk decision trees, prune abandoned branches; cap depth at 4

Bundle target: **0.38.0 minor bump** (new skill + new slash command + behavior change to interview).

## Workflow ladder positioning

```
free-form discussion          /flow-next:prospect <focus hint>
       │                              │
       ▼                              ▼
       └──────────┬───────────────────┘
                  │
                  ▼
          /flow-next:capture            ← new (this epic)
       (synthesize conversation
        → epic spec, no questions
        unless must-ask cases)
                  │
                  ▼
          .flow/specs/<id>.md
                  │
        ┌─────────┴────────┐
        ▼                  ▼
  /flow-next:interview   /flow-next:plan
  (refine via Q&A,        (research +
   enhanced this epic)     break into tasks)
        │                  │
        └────────┬─────────┘
                 ▼
         /flow-next:work
```

Capture is **upstream of interview/plan, downstream of free-form discussion or prospect promotion**. It's the automated alternative to the manual `flowctl epic create + set-plan` heredoc documented in `CLAUDE.md:431-462`.

## Architecture (capture skill — agent-native)

```
User: /flow-next:capture                     (interactive default)
       /flow-next:capture mode:autofix        (autofix — accept inferred without asking)
       /flow-next:capture --rewrite <id>      (overwrite existing epic spec — explicit opt-in)
         │
         ▼
    Skill workflow runs in host agent
         │
         ├─ Phase 0: Pre-flight
         │     - Duplicate detection: scan .flow/epics/, run flowctl memory search
         │       on extracted keywords → if similarity > threshold, ask: extend /
         │       supersede / proceed-anyway (hard-error in autofix mode)
         │     - Compaction detection: check conversation for [compacted] markers
         │       or truncated tool results → refuse without --from-compacted-ok
         │     - Idempotency: if --rewrite not passed and conversation has prior
         │       capture artifact id, refuse with hint
         │
         ├─ Phase 1: Extract conversation evidence
         │     Build a verbatim "## Conversation Evidence" block FIRST (raw quotes
         │     from user's recent turns), then draft spec referring to it by line.
         │     Mitigates hallucinated requirements (practice-scout F1.1, F1.2).
         │
         ├─ Phase 2: Source-tagged synthesis
         │     Draft spec sections; tag every acceptance criterion + decision:
         │     - [user] = verbatim from conversation
         │     - [paraphrase] = user intent restated
         │     - [inferred] = agent fill-in (most-scrutinized; user must confirm)
         │     If conversation surfaces a large number of acceptance criteria
         │     (heuristic: 8+), surface this at read-back as a suggestion ("This
         │     looks broad — consider splitting into multiple epics?"). Never
         │     auto-split. User decides.
         │
         ├─ Phase 3: Must-ask cases (interactive only — autofix marks needs-review)
         │     Hard-error if any of these are unresolved without asking:
         │     (a) Epic title genuinely ambiguous from conversation
         │     (b) Acceptance criterion can't be made testable without user judgment
         │     (c) Scope boundary conflicts with existing epic detected in Phase 0
         │     For optional ambiguities, lead with recommendation + confidence tier.
         │
         ├─ Phase 4: Read-back loop (mandatory, even in autofix)
         │     Show full draft (frontmatter + all sections + R-ID list +
         │     [inferred] tally) via AskUserQuestion. User confirms / edits / aborts.
         │     Autofix mode: print to stdout instead of asking, but require
         │     `--yes` flag to actually commit (similar to memory migrate pattern).
         │
         ├─ Phase 5: Write via flowctl
         │     - flowctl epic create --title "<extracted>" --json → returns epic-id
         │     - flowctl epic set-plan <epic-id> --file - --json <<EOF (heredoc)
         │     - Optional: flowctl epic set-branch <epic-id> --branch <slug>
         │
         └─ Phase 6: Suggested next step
             Print: "Spec captured at .flow/specs/<id>.md. Next: /flow-next:plan
             <id> to break into tasks, or /flow-next:interview <id> to refine."
```

**flowctl plumbing:** zero new subcommands. Capture uses existing `flowctl epic create` (`flowctl.py:8215-8278`) + `flowctl epic set-plan` (`flowctl.py:8835-8875`) + `flowctl memory search`. Pure skill change.

## Architecture (interview enhancements — three rules folded)

### Rule 1: Lead-with-recommendation (R17)

**Current state:** `flow-next-interview/SKILL.md:76-93` requires `AskUserQuestion`, groups 2-4 questions, but never specifies a recommendation pattern. Reference language exists in `flow-next-audit/SKILL.md:64` ("Lead with the recommended option and a one-sentence rationale") — copy this verbatim.

**Pattern (per practice-scout F2.1, F2.2):**

```
question.body: "<options summary>. Recommended: <X> — <one-sentence rationale>.
                Confidence: [high | judgment-call | your-call]."
question.options: [neutral labels, no recommendation marker on the option itself]
```

Three confidence tiers:
- **`[high]`** — agent has strong codebase signal or convention match; recommendation is load-bearing
- **`[judgment-call]`** — slight lean but reasonable people disagree; user's call carries weight
- **`[your-call]`** — agent has no signal; "I genuinely don't know — your priority / domain knowledge / preference"

The third tier prevents the "always recommend" failure mode that trains users to defer (F2.2). Recommendation comes AFTER options to reduce anchoring (F2.1).

### Rule 2: Explore-codebase-before-asking (R18)

**Current state:** interview defers ALL codebase work to `/flow-next:plan`. Wasteful when a question is trivially grep-answerable.

**Pattern (per practice-scout F3.1, F3.2):**

Pre-question taxonomy — agent classifies each candidate question:
- **Codebase-answerable** ("what exists / how it's wired / what conventions live here") → use Read/Grep/Glob to answer; log to `## Resolved via Codebase` audit-trail section in the spec
- **User-judgment-required** ("what should exist / what tradeoff to make / what's the priority") → ask via AskUserQuestion

If agent finds itself answering a "should" question via grep, that's the bug.

Spec output gains a new `## Resolved via Codebase` section (separate from `## Asked User`) so reviewers can spot-check assumptions.

### Rule 3: Dependency-ordered branches (R19)

**Current state:** interview asks 40+ questions with no enforced dependency order. User can answer "use PostgreSQL" before "do we need persistence at all" gets asked.

**Pattern (per practice-scout F4.1, F4.2, F4.3):**

- **Cap branch depth at 4** — research shows >4 prior turns rarely improves question quality
- **Discover-as-you-go**, not pre-compute — adapt branch based on prior answers
- **Log abandoned branches** — if user's answer prunes a sub-tree, surface it: "Skipping persistence questions — you said no DB."
- **One question per turn** (already present in interview, reaffirm)

Depth tracking in the question metadata; cap enforced before generating next question.

## Acceptance criteria

### Capture skill (fn-36.1)

- **R1:** New skill at `plugins/flow-next/skills/flow-next-capture/` with `SKILL.md`, `workflow.md`, `phases.md`. Mirrors `flow-next-audit/` structure (frontmatter shape, mode detection, FLOWCTL var fallback, pre-check banner, inline skill — no `context: fork`).
- **R2:** Slash command `/flow-next:capture` registered at `plugins/flow-next/commands/flow-next/capture.md`. Mirrors `commands/flow-next/audit.md` shape (frontmatter `name`, `description`, `argument-hint`; body invokes skill with `$ARGUMENTS`).
- **R3:** Phase 1 extracts a `## Conversation Evidence` block (verbatim user turns) into the spec FIRST, before drafting other sections. Spec body refers to evidence by section reference, not from agent memory of conversation.
- **R4:** Phase 2 source-tags every acceptance criterion + decision-context line with one of `[user]` / `[paraphrase]` / `[inferred]`. Phase 4 read-back surfaces the `[inferred]` count to user.
- **R5:** Phase 0 duplicate-detection: scans `.flow/epics/` for title-keyword overlap + runs `flowctl memory search` on extracted keywords. If similarity > threshold (≥2 strong keyword matches), asks user: extend / supersede / proceed-anyway. Autofix: hard-error.
- **R6:** Phase 0 compaction-detection: checks conversation for `[compacted]` markers or truncated tool-result patterns. Refuses without `--from-compacted-ok` arg. Autofix: hard-error.
- **R7:** Phase 4 read-back loop is **mandatory** — agent shows full draft (frontmatter + all sections + R-ID list + `[inferred]` tally) via `AskUserQuestion` (call `ToolSearch select:AskUserQuestion` first if the schema isn't loaded). Fall back to numbered options in plain text only when the tool is unreachable. Never silently skip the read-back. Autofix mode: print full draft + require explicit `--yes` arg to commit (mirrors `memory migrate --yes` pattern). Canonical uses Claude-native tool name; sync-codex.sh rewrites to `request_user_input` for the Codex mirror per repo convention.
- **R8:** Idempotency: capture refuses to overwrite an existing epic spec without `--rewrite <epic-id>` arg. Without `--rewrite`, conflict triggers Phase 0 duplicate-detection branch (extend / supersede / proceed-anyway).
- **R9:** Must-ask cases: capture is allowed zero questions for clean conversations, but MUST ask when (a) epic title genuinely ambiguous, (b) any acceptance criterion can't be made testable without user judgment, (c) scope conflicts with existing epic. These are hard-error conditions, not soft preferences.
- **R10:** Forbidden behaviors documented in skill: (a) tech-stack mentions unless user stated them (defer to `/flow-next:plan` per spec-kit convention), (b) inventing acceptance criteria not in conversation (must mark `[inferred]` and confirm at read-back), (c) silent overwrite (R8), (d) code snippets or specific file paths (those belong in `/flow-next:plan`).
- **R11:** When Phase 2 surfaces 8+ acceptance criteria, Phase 4 read-back includes a suggestion ("This looks broad — consider splitting into multiple epics?") as one option, never an auto-action. User can accept the split, reject and proceed with the larger epic, or edit. The skill never auto-splits.
- **R12:** Cross-platform subagent dispatch documented (Claude `Task` + `subagent_type: Explore`, Codex `spawn_agent` + `agent_type: explorer`, Droid equivalent). Used for Phase 1 codebase exploration when conversation references files. Mirror table at `flow-next-audit/workflow.md:158-183`.
- **R13:** Ralph-block: skill exits 2 under `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` (capture is human-in-the-loop synthesis). Pattern from `flow-next-prospect/SKILL.md:42-46`.
- **R14:** Capture writes spec using the **CLAUDE.md richer template** (`## Goal & Context` / `## Architecture & Data Models` / `## API Contracts` / `## Edge Cases & Constraints` / `## Acceptance Criteria` / `## Boundaries` / `## Decision Context`), NOT the lighter interview NEW IDEA template. Capture has full conversation context and should produce a complete spec.
- **R15:** All acceptance criteria use R-ID convention (`- **R1:** ...`, `- **R2:** ...`) per repo R-ID rule (`flow-next-plan/steps.md:227-262`). Capture allocates R-IDs sequentially from 1 for new epic.
- **R16:** Spec footer prints "Suggested next step: `/flow-next:plan <epic-id>` (break into tasks) or `/flow-next:interview <epic-id>` (refine via Q&A)."

### Interview enhancements (fn-36.2)

- **R17:** `flow-next-interview/SKILL.md:76-93` extended with lead-with-recommendation pattern: every `AskUserQuestion` body includes options summary, recommended option, one-sentence rationale, confidence tier (`[high]` / `[judgment-call]` / `[your-call]`). Canonical uses Claude-native tool name; sync-codex.sh rewrites to `request_user_input` in the Codex mirror per repo convention. Reference: `flow-next-audit/SKILL.md:62` for canonical phrasing.
- **R18:** `questions.md` gains pre-question taxonomy: agent classifies each candidate question as **codebase-answerable** ("what exists / how wired / what conventions") → use Read/Grep/Glob, log to spec's `## Resolved via Codebase` section; or **user-judgment-required** ("what should / what tradeoff / what priority") → ask via tool. Spec output template (in interview's "Write Refined Spec" phase) extended with `## Resolved via Codebase` section listing items + evidence.
- **R19:** `flow-next-interview/SKILL.md` documents dependency-ordered branch walk: cap branch depth at 4; discover-as-you-go (not pre-compute); when an answer prunes a sub-tree, surface the abandonment ("Skipping persistence questions — you said no DB"). One-question-per-turn invariant reaffirmed.

### Rollup (fn-36.3)

- **R20:** Docs updated. **All workflow-pathway-mentioning surfaces** must reflect the spec's ASCII diagram pathways (free-form → capture, prospect → capture, prospect → plan-direct via promote, capture → interview, capture → plan, capture → interview → plan, all terminating at work):
  - `README.md` (root) — commands table includes `/flow-next:capture`; workflow-sequence prose mentions reflect the new pathways
  - `CHANGELOG.md` — new `[flow-next 0.38.0]` block above 0.37.0 with Added/Changed/Notes covering capture skill + interview enhancements
  - `plugins/flow-next/README.md` — count update (Fifteen → Sixteen commands, line ~1620); commands table row for capture (line ~1624, workflow-ordered after interview); flags table (line ~1669); interview subsection extension (lines ~1726-1739) for grill-me enhancements; **"Choose Your Flow" workflow ladder table** (lines ~280-298) extended to cover all spec-diagram pathways; **"Prospect vs Spec vs Interview vs Plan" explainer** extended with a Capture entry; **mermaid lifecycle diagram** (lines ~826-851) extended with capture node showing all three entry points and both downstream branches
  - `CLAUDE.md` — commands list (line ~27, after audit); "Creating a spec" section (lines ~431-466) — add capture as automated alternative to manual heredoc
  - `.flow/usage.md` — no update needed (capture adds no flowctl subcommands; interview enhancements have no flowctl surface)
- **R21:** Website: `~/work/mickel.tech/app/apps/flow-next/page.tsx` — `commands` array entry for capture (after interview, line ~566); `lede` count update (Eleven → Twelve verbs, line ~1034); FAQ lifecycle update (lines ~128-130) covering prospect → capture → interview/plan flow
- **R22:** `scripts/sync-codex.sh` regenerates `plugins/flow-next/codex/skills/flow-next-capture/` and updates `flow-next-interview/` mirror after enhancements
- **R23:** `scripts/bump.sh minor flow-next` lands version bump 0.37.0 → 0.38.0 across `.claude-plugin/marketplace.json`, `plugins/flow-next/.claude-plugin/plugin.json`, `plugins/flow-next/.codex-plugin/plugin.json`

## Early proof point

Task fn-36.1 ships the capture skill files. Manual proof: invoke `/flow-next:capture` in a real session and verify (a) Phase 1 evidence extraction works, (b) Phase 4 read-back surfaces `[inferred]` count, (c) Phase 5 successfully creates an epic via flowctl. If the synthesis pattern produces hallucinated criteria not in the source conversation, revisit the source-tagging discipline (R4) before fn-36.2.

## Risks

| Risk | Mitigation |
|------|------------|
| Capture hallucinates requirements not in conversation | Source-tagging (R4) + read-back loop (R7) + `[inferred]` count surfaced |
| Capture overwrites an existing epic silently | Idempotency check (R8); `--rewrite <id>` required to overwrite; duplicate detection (R5) before create |
| Verbatim drift even with explicit instructions | Conversation evidence block FIRST (R3), spec refers to it; not synthesized from memory |
| Capture creates duplicate of existing epic | Phase 0 duplicate detection via `.flow/epics/` scan + `flowctl memory search` (R5) |
| Compacted conversation produces wrong spec | Phase 0 compaction detection refuses without `--from-compacted-ok` (R6) |
| Capture asks zero questions when it should ask | Must-ask cases hard-error (R9): ambiguous title / untestable acceptance / scope-conflict |
| Interview recommendation anchors user away from right answer | Confidence tiers explicit (R17): `[high]` / `[judgment-call]` / `[your-call]` — third tier breaks the always-recommend habit |
| Interview over-explores codebase, asks no questions | Pre-question taxonomy (R18): codebase answers "what exists", user answers "what should" — clear separation prevents agent from grepping its way to a "should" answer |
| Interview's stale codebase exploration when code changes mid-flight | `## Resolved via Codebase` section captures evidence at exploration time; on commit, agent re-verifies if HEAD differs (per practice-scout F3.3) — deferred to follow-up if too costly |
| Dependency-tree pre-computation too rigid | Discover-as-you-go (R19); cap depth at 4; surface abandoned branches |

## Boundaries

- Not adding flowctl subcommands. Capture uses existing `epic create` + `epic set-plan` + `memory search`.
- Not changing the epic-spec template format. Capture writes the same shape `flowctl epic set-plan` accepts (CLAUDE.md:431-462).
- Not auto-committing capture changes. User decides when to stage; the audit-trail (`## Resolved via Codebase`, `[inferred]` tags) lives in the spec itself.
- Not replacing `/flow-next:interview`. Capture is for "I've talked enough, lock it down"; interview is for "I need to be challenged on this." Both are legitimate.
- Not replacing `/flow-next:plan`. Capture produces a spec; plan researches + breaks the spec into tasks. Distinct phases.
- Not adding new memory entries automatically. Capture reads existing memory (for duplicate detection) but doesn't write new memory entries — that's the audit/work skills' domain.
- Not running under autonomous Ralph by default. Capture requires conversation context and user confirmation; both unavailable in autonomous loops.

## Decision context

**Why a new skill instead of extending `/flow-next:plan`?** Plan takes a feature description as input and produces tasks. Capture's input is *conversation history* (a fundamentally different shape) and output is a *spec, not tasks*. Forcing both into one skill would conflate distinct phases and force users to either describe their feature in one shot (loses conversation richness) or give plan a synthesis-mode flag (clutter). Cleaner: capture is a separate phase, output feeds plan.

**Why upstream of interview, not downstream?** Interview asks Q&A to refine an existing target (epic / task / file path). Capture's prerequisite is conversation, not a target. Sequence: conversation → capture → spec → (optional) interview → plan → work. Interview becomes the "I want to challenge this spec" step rather than the "build the spec from scratch" step.

**Why source-tag every acceptance criterion?** Practice-scout F1.1 found ~30% of intended requirements get missed by LLM elicitation, and bots fabricate confident answers. Distinguishing `[user]` / `[paraphrase]` / `[inferred]` makes the failure mode visible at read-back. User can reject `[inferred]` items they didn't actually agree to. Without tagging, hallucinations are invisible.

**Why mandatory read-back even in autofix?** Practice-scout F1.4: requirements-elicitation literature shows skipping read-back caps recall at 73%. The cost (one extra question or one printed draft + `--yes` flag) is trivial compared to writing a wrong spec. Worth making non-negotiable.

**Why fold grill-me into existing interview skill, not separate skill?** Three small enhancements (~50 lines of skill text total) don't warrant a new top-level command. Folding keeps the user-facing surface stable: `/flow-next:interview` does what it always did, just better. Fewer slash commands, cleaner mental model.

**Why bundle into 0.38.0 not split into two epics?** New skill + interview enhancement are conceptually paired (both upstream-of-implementation flow). Single CHANGELOG entry, single tag, single PR — better signal than two consecutive minor bumps.

**Why no flowctl plumbing changes?** Capture is pure skill; uses existing `epic create`, `epic set-plan`, `memory search`. Interview enhancements are pure skill changes. flowctl stays clean.

## Follow-ups (not in this epic)

- Capture's compaction-detection heuristic could become a flowctl helper (`flowctl session compaction-status --json`) if pattern proves general
- Interview's stale-exploration HEAD re-check (practice-scout F3.3) — deferred unless it surfaces as a real problem
- Consider a `/flow-next:capture --extend <id>` mode that adds new criteria to an existing epic from new conversation context (vs. `--rewrite` which overwrites)
- Tag `[NOT DISCUSSED — confirm or defer]` for missing-section detection (success metrics, rollback plan, out-of-scope) — could grow into capture's read-back checklist later

## Tasks

Three tasks. Fits one branch + one PR.

1. fn-36.1 — Capture skill files + slash command (`flow-next-capture/SKILL.md`, `workflow.md`, `phases.md` + `commands/flow-next/capture.md`)
2. fn-36.2 — Interview enhancements (lead-with-recommendation + explore-codebase-before-asking + dependency-ordered branches; folded into `flow-next-interview/SKILL.md` + `questions.md`)
3. fn-36.3 — Rollup: docs + website + codex mirror + version bump 0.38.0

## Requirement coverage

| Req | Description | Task(s) |
|-----|-------------|---------|
| R1, R2 | Skill files + slash command | fn-36.1 |
| R3, R4 | Conversation evidence + source-tagging | fn-36.1 |
| R5, R6 | Pre-flight: duplicate + compaction detection | fn-36.1 |
| R7 | Read-back loop (mandatory) | fn-36.1 |
| R8 | Idempotency / `--rewrite` flag | fn-36.1 |
| R9 | Must-ask cases | fn-36.1 |
| R10 | Forbidden behaviors | fn-36.1 |
| R11 | Suggest split when 8+ criteria (never auto) | fn-36.1 |
| R12 | Cross-platform subagent dispatch | fn-36.1 |
| R13 | Ralph-block | fn-36.1 |
| R14 | Spec uses CLAUDE.md richer template | fn-36.1 |
| R15 | R-ID allocation | fn-36.1 |
| R16 | Suggested-next-step footer | fn-36.1 |
| R17 | Lead-with-recommendation pattern | fn-36.2 |
| R18 | Explore-codebase-before-asking taxonomy | fn-36.2 |
| R19 | Dependency-ordered branches | fn-36.2 |
| R20 | Docs (CHANGELOG, README, CLAUDE.md) | fn-36.3 |
| R21 | Website (mickel.tech feature card + count + FAQ) | fn-36.3 |
| R22 | Codex mirror sync | fn-36.3 |
| R23 | Version bump 0.38.0 | fn-36.3 |
