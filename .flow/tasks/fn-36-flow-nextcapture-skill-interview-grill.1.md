---
satisfies: [R1, R2, R3, R4, R5, R6, R7, R8, R9, R10, R11, R12, R13, R14, R15, R16]
---

## Description

Create the `/flow-next:capture` skill — markdown files + slash command. Adapted from upstream `to-prd` (`/tmp/skills/to-prd/SKILL.md`), but flow-next-shaped: output goes to `.flow/specs/<id>.md` via `flowctl epic create + epic set-plan`, NOT a GitHub issue. Hard guardrails against hallucination from practice-scout findings (source-tagged criteria, mandatory read-back, duplicate detection, compaction detection).

This is the **skill-side** of fn-36. Task 2 folds grill-me enhancements into the existing interview skill. Task 3 lands docs + website + version bump.

**Size:** M (heavy on workflow + phase doc; modest acceptance count)
**Files:**
- `plugins/flow-next/skills/flow-next-capture/SKILL.md` (new — frontmatter, mode detection, interaction principles, FLOWCTL var, pre-check banner, references)
- `plugins/flow-next/skills/flow-next-capture/workflow.md` (new — Phases 0–6 with "Done when" gates)
- `plugins/flow-next/skills/flow-next-capture/phases.md` (new — phase reference + must-ask cases lookup + forbidden-behaviors list)
- `plugins/flow-next/commands/flow-next/capture.md` (new — slash command pass-through, mirror prospect/audit)

## Approach

### `SKILL.md` shape

Mirror `flow-next-audit/SKILL.md` exactly. Frontmatter:
- `name: flow-next-capture`
- `description: <one paragraph>` — trigger phrases ("capture spec", "lock down what we discussed", "make a spec from this conversation", "/flow-next:capture", "convert conversation to epic"); arg syntax (`mode:autofix` token + `--rewrite <id>` + `--from-compacted-ok` + `--yes`)
- `user-invocable: false` (consistent with audit/prospect)
- `allowed-tools: AskUserQuestion, Read, Bash, Grep, Glob, Write, Edit, Task` (same as audit)

Body sections:
1. **What this is** — agent-native synthesis from conversation; no codex/copilot subprocess; flowctl provides epic create + set-plan only
2. **Mode detection** — parse `$ARGUMENTS` for `mode:autofix` token + `--rewrite <id>` + `--from-compacted-ok` + `--yes` flag. Strip and apply.
3. **Inline skill (no `context: fork`)** — mandatory because Phase 4 read-back uses `AskUserQuestion`
4. **FLOWCTL var fallback** — `FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"`
5. **Pre-check banner** — copy from `flow-next-audit/SKILL.md:84-94` (setup-version banner)
6. **Interaction principles** — lead-with-recommendation pattern from audit:64; one-question-per-turn
7. **Forbidden behaviors** — copy from `phases.md` (R10 list)
8. **Reference workflow.md + phases.md**

### `workflow.md` shape

Document Phases 0-6 with "Done when" gates per phase. Reference `flow-next-audit/workflow.md` structure.

**Phase 0 — Pre-flight**

Three checks; abort/branch if any fails.

a) **Duplicate detection** (R5):
- Extract candidate keywords from conversation (proper nouns, capitalized terms, file paths). Cap at top-10 by frequency.
- Scan `.flow/epics/*.json` for title-keyword overlap (≥2 strong matches = potential duplicate).
- Run `flowctl memory search "<top-3 keywords>" --json` for related context.
- If duplicate detected: ask via `AskUserQuestion` — `[extend / supersede / proceed-anyway]`. Lead with recommendation based on overlap strength (high overlap → suggest extend; partial → proceed-anyway).
- Autofix mode: hard-error with stderr message + epic-id list. User must rerun without autofix or with explicit `--rewrite <id>` / `--proceed-anyway`.

b) **Compaction detection** (R6):
- Scan conversation for `[compacted]` markers, truncated tool-result patterns (`<...output too large to include>`, partial JSON), or system-summary blocks.
- If detected without `--from-compacted-ok` arg: refuse with stderr message explaining the risk + the flag to override.

c) **Idempotency** (R8):
- If conversation contains a prior capture artifact id (look for `Spec captured at .flow/specs/<id>.md` from earlier in conversation): refuse without `--rewrite <id>` arg.
- If `--rewrite <id>` provided: read existing spec, present diff at Phase 4, write only on confirm.

**Phase 1 — Extract conversation evidence** (R3)

Build the `## Conversation Evidence` block FIRST. Extract verbatim user turns relevant to the spec:
- User messages that state goals, requirements, decisions, or constraints
- Cap evidence at ~30 lines (truncate older turns; mark with `[truncated]`)
- Format: `> user (turn N): "<verbatim>"` per line

This block lives in the spec as a permanent audit trail. Subsequent phases refer to it by line, not from agent memory of conversation.

**Phase 2 — Source-tagged synthesis** (R4)

Draft each section of the spec with per-line source tags:
- `[user]` — verbatim from conversation evidence (exact quote or close paraphrase)
- `[paraphrase]` — user intent restated in spec language (semantic equivalence)
- `[inferred]` — agent fill-in (most-scrutinized; user must confirm at read-back)

Apply the CLAUDE.md richer template (R14):
- `## Goal & Context` — why this exists, what problem it solves
- `## Architecture & Data Models` — system design, data flow (mark file/component refs `[inferred]` unless user named them)
- `## API Contracts` — endpoints, interfaces, input/output shapes
- `## Edge Cases & Constraints` — failure modes, limits, performance reqs
- `## Acceptance Criteria` — testable; R-IDs (`- **R1:** ...`); each tagged with source. If 8+ criteria emerge, surface a "consider splitting into multiple epics?" option at read-back — never auto-split (R11).
- `## Boundaries` — explicit out-of-scope (often `[inferred]` from what user DIDN'T say)
- `## Decision Context` — why this approach; preserve rejected alternatives if user mentioned any (Linear pattern from docs-scout)

Plus `## Conversation Evidence` block (Phase 1) as the FIRST section after frontmatter.

**Forbidden in capture (R10):**
- Tech-stack mentions unless user stated them (defer to `/flow-next:plan` per spec-kit convention)
- Inventing acceptance criteria not in conversation (must mark `[inferred]` and confirm at read-back)
- Code snippets or specific file paths (those belong in `/flow-next:plan` task specs)
- Silent overwrite of existing spec (R8 idempotency)

**Phase 3 — Must-ask cases** (R9, interactive only — autofix marks needs-review)

Hard-error if any of these are unresolved without asking:
- (a) Epic title genuinely ambiguous from conversation (multiple plausible titles, none load-bearing)
- (b) Any acceptance criterion can't be made testable without user judgment (e.g., "make it fast" — fast how?)
- (c) Scope boundary conflicts with existing epic detected in Phase 0

For optional ambiguities (not in must-ask set), use lead-with-recommendation pattern:
- `question.body`: "<options summary>. Recommended: <X> — <one-sentence rationale>. Confidence: [high|judgment-call|your-call]."
- `question.options`: neutral labels

**Phase 4 — Read-back loop** (R7, mandatory even in autofix)

Show the full draft via `AskUserQuestion`:
- Frontmatter (title, branch hint)
- All sections in order
- R-ID list with source tags
- `[inferred]` count tally + list

Question shape:
- header: "Read-back"
- body: "<full draft>. [N] criteria are [inferred] — confirm before write?"
- options: `[approve / edit / abort]`

If user picks `edit`: prompt for which sections; loop back to Phase 2 for those sections.
If user picks `abort`: skill exits 0, no write.

Autofix mode: print full draft to stdout, require `--yes` flag to commit (mirror `memory migrate --yes` pattern). Without `--yes`, exit 0 with a "draft printed; rerun with --yes to commit" hint.

**Phase 5 — Write via flowctl** (R14, R15, R16)

```bash
EPIC_ID=$(flowctl epic create --title "<title>" --json | jq -r .id)
flowctl epic set-plan "$EPIC_ID" --file - --json <<EOF
<spec body>
EOF
```

Optional: `flowctl epic set-branch "$EPIC_ID" --branch "<slug>" --json` if user named a branch in conversation.

R-IDs (R15): allocate sequentially from R1 within the new epic (capture creates fresh epics, no renumber concern).

**Phase 6 — Suggested next step** (R16)

Print:
```
Spec captured at .flow/specs/<epic-id>.md.
Next:
  /flow-next:plan <epic-id>      → research + break into tasks
  /flow-next:interview <epic-id> → refine via Q&A
```

### `phases.md` shape

Phase reference table + must-ask cases lookup + forbidden behaviors list. Lift from `flow-next-audit/phases.md` structure.

Sections:
- **Phase reference** — one-line summary of each phase + Done-when
- **Must-ask cases** (R9) — three hard-error conditions with examples
- **Forbidden behaviors** (R10) — the four items above with rationale
- **Source-tag taxonomy** (R4) — `[user]` / `[paraphrase]` / `[inferred]` with one example each
- **Confidence tiers** (for must-ask Phase 3 questions): `[high]` / `[judgment-call]` / `[your-call]` — examples per tier

### `commands/flow-next/capture.md`

Minimal slash-command pass-through. Mirror `commands/flow-next/audit.md` exactly. Frontmatter (`name`, `description`, `argument-hint`); body invokes the skill with `$ARGUMENTS`.

Argument-hint string: `[mode:autofix] [--rewrite <epic-id>] [--from-compacted-ok] [--yes]`

### Subagent dispatch (R12)

Phase 1 evidence extraction is main-thread (small token budget). When conversation references repo files that need verification, spawn read-only investigation via host primitive:
- Claude Code: `Task` tool with `subagent_type: Explore`, `disallowedTools: Edit, Write, Task`
- Codex: `spawn_agent` with `agent_type: explorer`
- Droid: equivalent (verify at impl time)
- Fallback: main-thread Read/Grep/Glob

Mirror the cross-platform table at `flow-next-audit/workflow.md:158-183`.

### Ralph-block (R13)

Skill exits 2 under `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH` set. Pattern from `flow-next-prospect/SKILL.md:42-46`:

```bash
if [[ -n "${REVIEW_RECEIPT_PATH:-}" || "${FLOW_RALPH:-}" == "1" ]]; then
  echo "Error: /flow-next:capture requires conversation context + user confirmation; not compatible with Ralph mode." >&2
  exit 2
fi
```

## Investigation targets

**Required:**
- `/tmp/skills/to-prd/SKILL.md` — upstream reference (the synthesis pattern we're adapting)
- `plugins/flow-next/skills/flow-next-audit/SKILL.md` — closest in-repo reference for skill structure
- `plugins/flow-next/skills/flow-next-audit/workflow.md` — phase shape + cross-platform subagent dispatch table (lines 158-183)
- `plugins/flow-next/skills/flow-next-audit/phases.md` — outcome lookup style
- `plugins/flow-next/skills/flow-next-prospect/SKILL.md` — Ralph-block pattern (lines 42-46), pre-check banner
- `plugins/flow-next/commands/flow-next/audit.md` — slash command pass-through pattern
- `plugins/flow-next/scripts/flowctl.py:8215-8278` — `cmd_epic_create` (returns epic-id; capture invokes via shell)
- `plugins/flow-next/scripts/flowctl.py:8835-8875` — `cmd_epic_set_plan` (heredoc-friendly via `read_file_or_stdin`)
- `CLAUDE.md:431-462` — canonical "Creating a spec" heredoc template (capture replicates this shape)
- `plugins/flow-next/skills/flow-next-plan/steps.md:227-262` — R-ID convention rules

**Optional:**
- `plugins/flow-next/skills/flow-next-prospect/workflow.md` — multi-phase skill workflow pattern with persona seeding (capture's analog: source-tag taxonomy)
- `/tmp/skills/grill-me/SKILL.md` — adjacent to capture (Task 2 folds these into interview); reference for interaction-style only

## Key context

- Skill files are markdown — no Python, no shell, no testing. The "test" is invoking the skill in a real session post-merge.
- Mode detection MUST live in SKILL.md so the host agent finds it on first read.
- The slash command file is just the trigger — actual workflow lives in `skills/flow-next-capture/`.
- `AskUserQuestion` shape: header ≤12 chars, question ≤80 chars (recommendation goes IN the body, not a separate field), 2-4 options. (Source: docs-scout.)
- Capture creates fresh epics — no R-ID renumber concern. Allocate sequentially from R1.
- `[inferred]` count is the audit-trail signal — surface it prominently at read-back. High `[inferred]` count → user should scrutinize harder OR rerun capture after more conversation.
- Phase 0 duplicate detection threshold: ≥2 strong keyword matches (proper nouns, file paths, domain-specific terms — not common English words). Tune if false-positive rate too high in real use.
- Forbidden tech-stack mentions: capture says "needs persistence" not "uses PostgreSQL" unless user explicitly chose PostgreSQL. Defer choice to `/flow-next:plan` (spec-kit pattern).
- One question per turn. Multi-question violates AskUserQuestion contract and overwhelms users (practice-scout F4.3).

## Acceptance

- [ ] `plugins/flow-next/skills/flow-next-capture/SKILL.md` exists with valid frontmatter (`name: flow-next-capture`, `description`, `user-invocable: false`, `allowed-tools`), mode detection (parse `mode:autofix`, `--rewrite <id>`, `--from-compacted-ok`, `--yes`), interaction principles, FLOWCTL var fallback, pre-check banner, forbidden-behaviors list, references to workflow.md + phases.md.
- [ ] `plugins/flow-next/skills/flow-next-capture/workflow.md` documents Phases 0-6 with "Done when" criteria per phase.
- [ ] `plugins/flow-next/skills/flow-next-capture/phases.md` documents must-ask cases (R9), forbidden behaviors (R10), source-tag taxonomy (R4), confidence tiers (R17 reference).
- [ ] `plugins/flow-next/commands/flow-next/capture.md` exists, invokes the skill with `$ARGUMENTS`, mirrors audit command shape.
- [ ] Phase 1 evidence-extraction documented: agent extracts verbatim user turns into a `## Conversation Evidence` block as the FIRST spec section after frontmatter. (R3)
- [ ] Phase 2 source-tagging documented: every acceptance criterion + decision-context line gets one of `[user]` / `[paraphrase]` / `[inferred]`. (R4)
- [ ] Phase 0 duplicate-detection documented: scan `.flow/epics/`, run `flowctl memory search`, ≥2 strong keyword matches → ask user (interactive) or hard-error (autofix). (R5)
- [ ] Phase 0 compaction-detection documented: refuses without `--from-compacted-ok` arg. (R6)
- [ ] Phase 4 read-back loop documented as MANDATORY: full draft + `[inferred]` count + confirm via blocking-question; autofix mode prints draft + requires `--yes`. (R7)
- [ ] Phase 0 idempotency documented: `--rewrite <id>` required to overwrite existing epic spec. (R8)
- [ ] Must-ask cases (R9) documented in phases.md: ambiguous title / untestable acceptance / scope-conflict.
- [ ] Forbidden behaviors (R10) documented: no tech-stack, no invented acceptance, no code/file paths, no silent overwrite.
- [ ] Phase 4 read-back uses `AskUserQuestion` (Claude-native; sync-codex.sh rewrites to `request_user_input` for Codex mirror per repo convention). Schema-load via `ToolSearch select:AskUserQuestion` if needed. Plain-text numbered options as fallback when tool unreachable. NO inline cross-platform table in the canonical skill text. (R7)
- [ ] When Phase 2 emits 8+ acceptance criteria, Phase 4 read-back includes a "consider splitting into multiple epics?" option — never auto-action. User decides. (R11)
- [ ] Cross-platform subagent dispatch (R12) documented in workflow.md mirroring `flow-next-audit/workflow.md:158-183`.
- [ ] Ralph-block (R13) documented + verified in SKILL.md (exits 2 under `FLOW_RALPH=1` or `REVIEW_RECEIPT_PATH`).
- [ ] Spec template (R14) documented as CLAUDE.md richer template (Goal/Architecture/API Contracts/Edge Cases/Acceptance/Boundaries/Decision Context), NOT interview NEW IDEA template.
- [ ] R-ID allocation (R15) documented: sequential from R1 within new epic; reference `flow-next-plan/steps.md:227-262`.
- [ ] Suggested-next-step footer (R16) documented in Phase 6.
- [ ] No code in skill files. Markdown only. No Python, no bash beyond illustrative snippets in workflow descriptions (subagent dispatch examples, flowctl invocations).
- [ ] Cross-check: invoking `/flow-next:capture` in a fresh session loads the skill cleanly (no syntax errors, frontmatter parses). Test by reading SKILL.md back via flowctl-style validation if available.


## Done summary

(populated when task completes)

## Evidence

(populated when task completes)
