---
name: flow-next-interview
description: Interview user in-depth about an epic, task, or spec file to extract complete implementation details. Use when user wants to flesh out a spec, refine requirements, or clarify a feature before building. Triggers on /flow-next:interview with Flow IDs (fn-1-add-oauth, fn-1-add-oauth.2, or legacy fn-1, fn-1.2, fn-1-xxx, fn-1-xxx.2) or file paths.
user-invocable: false
---

# Flow interview

Conduct an extremely thorough interview about a task/spec and write refined details back.

**IMPORTANT**: This plugin uses `.flow/` for ALL task tracking. Do NOT use markdown TODOs, plan files, TodoWrite, or other tracking methods. All task state must be read and written via `flowctl`.

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Always use:
```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
$FLOWCTL <command>
```

## Pre-check: Local setup version

If `.flow/meta.json` exists and has `setup_version`, compare to plugin version:
```bash
SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
# Portable: Claude Code uses .claude-plugin, Factory Droid uses .factory-plugin
PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/.codex-plugin/plugin.json"
[[ -f "$PLUGIN_JSON" ]] || PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
if [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" ]]; then
 [[ "$SETUP_VER" = "$PLUGIN_VER" ]] || echo "Plugin updated to v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts (current: v${SETUP_VER})."
fi
```
Continue regardless (non-blocking).

**Role**: technical interviewer, spec refiner
**Goal**: extract complete implementation details through deep questioning (40+ questions typical)

## Input

Full request: $ARGUMENTS

Accepts:
- **Flow epic ID** `fn-N-slug` (e.g., `fn-1-add-oauth`) or legacy `fn-N`/`fn-N-xxx`: Fetch with `flowctl show`, write back with `flowctl epic set-plan`
- **Flow task ID** `fn-N-slug.M` (e.g., `fn-1-add-oauth.2`) or legacy `fn-N.M`/`fn-N-xxx.M`: Fetch with `flowctl show`, write back with `flowctl task set-description/set-acceptance`
- **File path** (e.g., `docs/spec.md`): Read file, interview, rewrite file
- **Empty**: Prompt for target

Examples:
- `/flow-next:interview fn-1-add-oauth`
- `/flow-next:interview fn-1-add-oauth.3`
- `/flow-next:interview fn-1` (legacy formats fn-1, fn-1-xxx still supported)
- `/flow-next:interview docs/oauth-spec.md`

If empty, ask: "What should I interview you about? Give me a Flow ID (e.g., fn-1-add-oauth) or file path (e.g., docs/spec.md)"

## Setup

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT:-$HOME/.codex}}/scripts/flowctl"
```

### Parse `--docs` / `--no-docs` flags

Strip `--docs` / `--no-docs` from `$ARGUMENTS` before input-type detection so they don't get confused for a Flow ID or path:

```bash
RAW_ARGS="$ARGUMENTS"
DOC_AWARE_FORCE="" # "" = autodetect, "on" = forced on, "off" = forced off
if [[ "$RAW_ARGS" == *"--no-docs"* ]]; then
 DOC_AWARE_FORCE="off"
 RAW_ARGS="${RAW_ARGS//--no-docs/}"
elif [[ "$RAW_ARGS" == *"--docs"* ]]; then
 DOC_AWARE_FORCE="on"
 RAW_ARGS="${RAW_ARGS//--docs/}"
fi
RAW_ARGS=$(printf "%s" "$RAW_ARGS" | tr -s ' ' | sed 's/^ //;s/ $//')
# RAW_ARGS now contains the Flow ID / file path / empty.
```

`--docs` and `--no-docs` are mutually exclusive; if the user passes both, `--no-docs` wins (the `if/elif` checks `--no-docs` first). The `--docs` token gets left in the residual `RAW_ARGS` after stripping, which surfaces downstream as an unrecognized argument — loud failure beats silent acceptance of conflicting state.

### Doc-aware autodetect

Decide whether doc-aware mode (behaviors a-d below) activates. Three paths:

1. **Forced on** (`--docs` flag): `DOC_AWARE=1`. Lazy-creates root `GLOSSARY.md` on first term resolution via `flowctl glossary add` (writes to nearest-ancestor or repo root when no ancestor exists).
2. **Forced off** (`--no-docs` flag): `DOC_AWARE=0`. Skip behaviors a-d entirely, even if artifacts exist.
3. **Autodetect** (no flag): activate when `GLOSSARY.md` has at least one defined term OR any decision entry exists.

```bash
DOC_AWARE=0
if [[ "$DOC_AWARE_FORCE" == "on" ]]; then
 DOC_AWARE=1
elif [[ "$DOC_AWARE_FORCE" == "off" ]]; then
 DOC_AWARE=0
else
 TERMS=$("$FLOWCTL" glossary list --json 2>/dev/null | jq -r '.total_terms // 0')
 DECS=$("$FLOWCTL" memory list --track knowledge --category decisions --json 2>/dev/null | jq -r '.entries | length // 0')
 if [[ "${TERMS:-0}" -gt 0 || "${DECS:-0}" -gt 0 ]]; then
 DOC_AWARE=1
 fi
fi
```

**Why `total_terms > 0` rather than `[[ -f GLOSSARY.md ]]`:** `flowctl glossary remove` leaves a `# Glossary` H1 husk on disk after the last term is removed (the file is project state, intentionally retained). A presence-only check would false-positive on an empty husk and surface phantom doc-aware questions when no canonical vocabulary is actually defined. `glossary list --json` walks the file and counts populated entries; `total_terms == 0` for a husk.

When `DOC_AWARE=1`, the four behaviors below layer onto the standard interview workflow. When `DOC_AWARE=0`, the interview proceeds exactly as today.

## Detect Input Type

1. **Flow epic ID pattern**: matches `fn-\d+(-[a-z0-9-]+)?` (e.g., fn-1-add-oauth, fn-12, fn-2-fix-login-bug)
 - Fetch: `$FLOWCTL show <id> --json`
 - Read spec: `$FLOWCTL cat <id>`

2. **Flow task ID pattern**: matches `fn-\d+(-[a-z0-9-]+)?\.\d+` (e.g., fn-1-add-oauth.3, fn-12.5)
 - Fetch: `$FLOWCTL show <id> --json`
 - Read spec: `$FLOWCTL cat <id>`
 - Also get epic context: `$FLOWCTL cat <epic-id>`

3. **File path**: anything else with a path-like structure or .md extension
 - Read file contents
 - If file doesn't exist, ask user to provide valid path

## Interview Process

**CRITICAL REQUIREMENT**: You MUST use the `request_user_input` tool for every question.

- DO NOT output questions as text
- DO NOT list questions in your response
- ONLY ask questions via request_user_input primitive calls
- Group 2-4 related questions per tool call
- Expect 40+ questions total for complex specs

**Anti-pattern (WRONG)**:
```
Question 1: What database should we use?
Options: a) PostgreSQL b) SQLite c) MongoDB
```

**Correct pattern**: Call request_user_input primitive with question and options.

### Question Format: Lead with Recommendation

Every `request_user_input` body must include the agent's recommended option AND a confidence tier. Mirrors the canonical phrasing in `flow-next-audit/SKILL.md:64` ("Lead with the recommended option and a one-sentence rationale"). Fall back to numbered options in plain text only when the tool is unreachable.

Pattern:

- `question.body`: "<options summary>. Recommended: <X> — <one-sentence rationale>. Confidence: [high | judgment-call | your-call]."
- `question.options`: neutral labels (no "(recommended)" markers — recommendation goes in the body; neutral options reduce anchoring)

Confidence tiers (mandatory — pick one per question):

- `[high]` — strong codebase signal or convention match. Recommendation is load-bearing; user can usually accept.
- `[judgment-call]` — slight lean but reasonable people disagree. User's call carries weight.
- `[your-call]` — agent has no signal. "I genuinely don't know — your priority / domain knowledge / preference."

The `[your-call]` tier is **mandatory** when the agent has no basis for a recommendation. Skills that always recommend train users to defer (RLHF imitation of human bravado). Say so explicitly.

Examples (one per tier):

- `[high]`: "Where should the new validator live? Recommended: `src/utils/validation.ts` — three sibling validators (`validateEmail`, `validatePhone`, `validateUrl`) already live there and the test suite imports from that module. Confidence: [high]." Options: `src/utils/validation.ts`, `src/validators/`, `new module`.
- `[judgment-call]`: "Cache TTL for the rate-limiter? Recommended: 60s — short enough that drift stays bounded, long enough that the cache earns its keep. Confidence: [judgment-call]." Options: `30s`, `60s`, `300s`, `no cache`.
- `[your-call]`: "What error code should we return when the upstream API times out? Recommended: none — this depends on what callers expect and I don't see existing convention to copy. Confidence: [your-call]." Options: `502`, `503`, `504`, `408`.

### Question Order: Walk the Decision Tree

Walk down branches of the decision tree in dependency order. Don't ask about implementation details before establishing whether they're needed.

Concrete rules:

1. **Cap branch depth at 4.** Research shows >4 prior turns rarely improves question quality — drop deeper threads, ask about something else. Heuristic; revisit if too restrictive in real use.
2. **Discover-as-you-go**, not pre-compute. Adapt the next question based on prior answers. Don't lock a tree before you start.
3. **Surface abandoned branches.** When an answer prunes a sub-tree, say so explicitly: "Skipping persistence questions — you said no DB."
4. **One `request_user_input` call per turn**, period — never queue multiple tool calls back-to-back. Within that single call you may bundle 2-4 closely-related sub-questions per the existing batching rule above; do NOT pad with loosely-related questions just to hit four. The intent: one focused checkpoint per turn so the user isn't barraged with unrelated decisions in parallel. Use multi-select within a sub-question when options are non-exclusive.

Example flow:

> Q: "Does this feature need persistence?"
> A: "No, ephemeral state is fine."
> [agent prunes the {DB choice, schema design, migration plan} sub-tree]
> Q: "Skipped DB questions — you said ephemeral. Next: how should this state survive page reloads?"

### Investigate Codebase Before Asking

Before every question, classify it via the [questions.md](questions.md) **Pre-Question Taxonomy**:

- **Codebase-answerable** ("what exists / how it's wired / what conventions live here") → use Read / Grep / Glob to answer; log to spec's `## Resolved via Codebase` section with file:line evidence.
- **Glossary-lookup-answerable** (`DOC_AWARE=1` only) — terms with a canonical entry in the nearest-ancestor `GLOSSARY.md` → silently resolve from the entry; log to spec's `## Glossary Conflicts` section only when the user's wording diverges from canonical AND the term is load-bearing (see behavior (a) below).
- **User-judgment-required** ("what should exist / what tradeoff to make / what priority") → ask via `request_user_input`.

If you find yourself answering a "should" question via grep, that's the bug. Stop and ask the user.

#### Code-versus-assertion contradiction (`DOC_AWARE=1` — behavior (c))

When grep / Read reveals the code disagrees with something the user asserted ("we already have X at path Y" but Y is gone, or "the auth flow uses OAuth" but the code uses API keys), do **not** silently log under `## Resolved via Codebase`. Surface the contradiction as an `request_user_input`:

- **header**: `Code mismatch?`
- **body**: `Code shows <X> at <file:line>; you said <Y>. Recommended: <treat-code-as-source-of-truth | update-spec-to-match-code | revisit-the-area>. Confidence: [<tier>].`
- **options**: frozen — `match-code` (revise spec to align with what's there), `update-code` (treat the assertion as the goal; flag the divergence as a task), `clarify` (user explains; agent re-investigates with new context).

Confidence tier: `[high]` when grep evidence is unambiguous (file does not exist, function signature is clearly different); `[judgment-call]` when interpretation is at play (similar names, partial overlap, recent rename). Never silently pick a side — the user owns the resolution.

The bar for surfacing: a meaningful contradiction that affects spec correctness. If the user says "the validator returns boolean" and grep shows it returns `Result<bool, Error>`, surface. If the user paraphrases a function's role and grep shows the role matches but the implementation differs in unrelated detail, log under `## Resolved via Codebase` and move on.

## Doc-aware behaviors (`DOC_AWARE=1` only)

When `DOC_AWARE=1`, four behaviors layer onto the standard interview workflow. When `DOC_AWARE=0`, skip this entire section.

### Behavior (a) — Phase-zero glossary scan

Before drafting the first question batch, run a glossary scan against the user's request.

```bash
"$FLOWCTL" glossary list --json
```

JSON shape:

```json
{
 "groups": [
 {
 "path": "GLOSSARY.md",
 "entries": [
 { "term": "Worker", "definition": "...", "avoid": ["consumer"], "relates_to": ["Queue"] }
 ],
 "count": 1
 }
 ],
 "file_count": 1,
 "total_terms": 1
}
```

For each defined term across `groups[].entries`, scan the user's request for occurrences. Term match is **case-insensitive whitespace-collapsed** — the same rule as `flowctl glossary read` (see `_glossary_term_matches` in `flowctl.py:401`). Do NOT reinvent matching logic; the canonical contract is "lowercase both sides, collapse runs of whitespace to single space, compare equal." Alias hits via `entries[].avoid`: if the user wrote `consumer` and the entry's `avoid` list contains `consumer`, that's a canonical-mismatch hit on `Worker`.

For each hit, evaluate one filter before surfacing:

- **Is the term load-bearing for this spec?** Casual passing mention does not trigger; mention that defines behavior or shapes acceptance does. The user wrote "the worker fetches the queue" mid-sentence about deployment — passing mention, no question. The user wrote "we need a new kind of worker that processes batches" — load-bearing, surface.

When a hit passes the load-bearing filter AND the user's wording conflicts with canonical (alias used instead of canonical, or definition contradicts), surface as the **first interview question** via `request_user_input`:

- **header**: `Term mismatch?`
- **body**: `You used "<user-wording>"; GLOSSARY.md defines "<canonical>" as "<one-line definition>". Recommended: <use-canonical | redefine | this-is-different>. Confidence: [<tier>].`
- **options**: frozen — `use-canonical` (the user meant the existing term; spec uses canonical wording), `redefine` (user is updating the term meaning; spec proceeds with new wording, agent will re-write `GLOSSARY.md` via `flowctl glossary add` after the interview), `this-is-different` (the words collide but the concepts differ; spec uses a fresh disambiguating term — capture in `## Glossary Conflicts`).

Confidence tier: `[high]` when the canonical entry is recent and the user's wording cleanly maps to an `avoid` alias; `[judgment-call]` when meaning could plausibly have drifted; `[your-call]` when the term sits in user-domain territory the agent has no purchase on.

**Throttle:** at most one Phase-zero glossary question per interview turn. If multiple terms hit, surface the most load-bearing one first; the rest fold into the natural conversation flow as they come up. Bombarding the user with vocabulary questions before the core spec questions is the failure mode this filter prevents.

### Behavior (b) — Fuzzy-term sharpening

Across the conversation, watch for overloaded language — words the user keeps using whose meaning could plausibly shift between turns ("workflow", "session", "task" when a Flow `task` already has meaning, etc.). When you spot one:

1. Propose a canonical via `request_user_input`:
 - **header**: `Sharpen "<term>"?`
 - **body**: `You've used "<term>" in <count> turns. I'm reading it as "<agent's working definition>" but want to lock it in. Recommended: <X> — <one-sentence rationale>. Confidence: [<tier>].`
 - **options**: 2-4 candidate canonical wordings + `none-of-these` (user provides their own).

2. On user-pick, build the resolved entry and write it to the nearest-ancestor `GLOSSARY.md` via `flowctl glossary add`:

 ```bash
 "$FLOWCTL" glossary add "<term>" --definition-file - --json <<EOF
 <user-resolved one-line or short paragraph definition>
 EOF
 ```

 Use `--definition-file -` (stdin) so multi-sentence definitions and quoted phrasing round-trip cleanly. `glossary add` is upsert — case-insensitive match replaces the existing entry in full; new terms append at the end of the file. If the user picked `redefine` in behavior (a), this is the same call site (one path, one upsert).

3. The next question can re-read the glossary. There is no in-memory cache to invalidate — re-read on every doc-aware turn that needs canonical lookup. The cost is one stat + one file read per turn; sub-millisecond at typical sizes.

**When to skip behavior (b):** if a term is single-use, or if the user volunteered a clear definition the first time they used it, or if the conversation is short enough (≤6 turns) that consolidation buys nothing yet. The behavior triggers when overloading is real and persistent, not on every undefined word.

### Behavior (d) — Decision-record write (three-criteria gate)

When the interview surfaces a choice the user is making — not just a fact about the system, a real **decision** — evaluate the three-criteria gate before drafting a memory entry.

**The three-criteria gate** (all three must hold):

1. **Hard-to-reverse** — undoing this later costs more than redoing it now. Schema choices, public API shapes, integration boundaries qualify; cosmetic preferences and easily-toggled flags do not.
2. **Surprising-without-context** — a future maintainer reading the result without history would ask "why this and not the obvious thing?". Anything that follows the standard pattern of the surrounding code is not surprising.
3. **Real trade-off** — there was a genuine alternative that lost. If there was no real alternative, it isn't a decision; it's a fact.

If any of the three fails, do NOT write a decision entry. Note the choice in the spec's prose body (e.g. `## Decision Context`) and move on. The bar exists because the decisions store decays fast when filled with non-decisions.

When all three hold:

1. **Draft the entry** in agent memory (do not write yet). Shape:
 - **Title** (1 line, ≤80 chars): the decision in noun-phrase form (e.g. "Nearest-ancestor walk for glossary lookup").
 - **Body** (1-3 sentences floor; longer when warranted):
 - 1 sentence on what was chosen.
 - 0-1 sentences on why.
 - Optional `## Considered Options` block listing rejected alternatives with one-line reasons each.
 - Optional `## Consequences` block listing what this commits the project to.
 - **Module** (optional): the file or subsystem the decision shapes.
 - **Tags** (optional): comma-separated, e.g. `glossary,resolution,walk`.

2. **Show the draft via `request_user_input` before writing** — same pattern as `/flow-next:capture` Phase 4 read-back:
 - **header**: `Write decision?`
 - **body**: `Drafted decision entry: <title>. Body: <one-line summary>. Recommended: approve — <one-sentence rationale why all three gate criteria hold>. Confidence: [<tier>].`
 - **options**: frozen — `approve` (write), `edit` (user revises title / body / module / tags via follow-up), `skip` (do not write; the choice stays in spec prose only).

 Show the full body inline in the question or in the message preceding it; the user must be able to read what they're approving. Never write silently — even when the gate cleanly passes, the user owns the final write.

3. **On `approve`**, call:

 ```bash
 "$FLOWCTL" memory add \
 --track knowledge \
 --category decisions \
 --title "<title>" \
 --module "<module>" \
 --tags "<tags>" \
 --body-file - <<EOF
 <body markdown>
 EOF
 ```

 The `decisions` category is registered in flowctl's memory schema (Task 1 of this epic). Optional fields `--decision-status` (default `accepted`), `--superseded-by`, and `--alternatives-considered` are available; pass them when the conversation supplies them and skip otherwise.

4. **On `edit`**, ask one follow-up `request_user_input` for which field changes (title / body / module / tags), capture the revision, re-show the draft, loop. Hard cap at 2 edit cycles before defaulting to `approve` / `skip`.

5. **On `skip`**, do nothing — the choice still appears in spec prose; only the memory entry is suppressed.

**At most one decision write per interview turn.** Even if multiple gate-passing decisions surface, ask one at a time; subsequent asks adapt to the user's energy level for read-back.

## Question Categories

Read [questions.md](questions.md) for all question categories and interview guidelines.

## NOT in scope (defer to /flow-next:plan)

- Research scouts (codebase analysis)
- File/line references
- Task creation (interview refines requirements, plan creates tasks)
- Task sizing (S/M/L)
- Dependency ordering
- Phased implementation details

## Write Refined Spec

After interview complete, write everything back — **scope depends on input type**.

### For NEW IDEA (text input, no Flow ID)

Create epic with interview output. **DO NOT create tasks** — that's `/flow-next:plan`'s job.

```bash
$FLOWCTL epic create --title "..." --json
$FLOWCTL epic set-plan <id> --file - --json <<'EOF'
# Epic Title

## Problem
Clear problem statement

## Key Decisions
Decisions made during interview (e.g., "Use OAuth not SAML", "Support mobile + web")

## Edge Cases
- Edge case 1
- Edge case 2

## Resolved via Codebase
(optional — omit if nothing was resolved this way during the interview)
Items the agent answered via Read / Grep / Glob, with file:line evidence. Separate from items the user answered. Lets reviewers spot-check assumptions later.

## Glossary Conflicts
(optional — only when DOC_AWARE=1 surfaced behavior-(a) hits during the interview)
Per-term: user-wording vs. canonical term, the resolution chosen (use-canonical / redefine / this-is-different), file:line of the canonical entry. Lets reviewers see where vocabulary tightened.

## Open Questions
Unresolved items that need research during planning

## Acceptance
- [ ] Criterion 1
- [ ] Criterion 2
EOF
```

Then suggest: "Run `/flow-next:plan fn-N` to research best practices and create tasks."

### For EXISTING EPIC (fn-N that already has tasks)

**First check if tasks exist:**
```bash
$FLOWCTL tasks --epic <id> --json
```

**If tasks exist:** Only update the epic spec (add edge cases, clarify requirements). **Do NOT touch task specs** — plan already created them.

**If no tasks:** Update epic spec, then suggest `/flow-next:plan`.

```bash
$FLOWCTL epic set-plan <id> --file - --json <<'EOF'
# Epic Title

## Problem
Clear problem statement

## Key Decisions
Decisions made during interview

## Edge Cases
- Edge case 1
- Edge case 2

## Resolved via Codebase
(optional — omit if nothing was resolved this way during the interview)
Items the agent answered via Read / Grep / Glob, with file:line evidence. Separate from items the user answered.

## Glossary Conflicts
(optional — only when DOC_AWARE=1 surfaced behavior-(a) hits during the interview)
Per-term: user-wording vs. canonical term, the resolution chosen, file:line of the canonical entry.

## Open Questions
Unresolved items

## Acceptance
- [ ] Criterion 1
- [ ] Criterion 2
EOF
```

### For Flow Task ID (fn-N.M)

**First check if task has existing spec from planning:**
```bash
$FLOWCTL cat <id>
```

**If task has substantial planning content** (description with file refs, sizing, approach):
- **Do NOT overwrite** — planning detail would be lost
- Only ADD new acceptance criteria discovered in interview:
 ```bash
 # Read existing acceptance, append new criteria
 $FLOWCTL task set-acceptance <id> --file /tmp/acc.md --json
 ```
- Or suggest interviewing the epic instead: `/flow-next:interview <epic-id>`

**If task is minimal** (just title, empty or stub description):
- Update task with interview findings
- Focus on **requirements**, not implementation details

```bash
$FLOWCTL task set-spec <id> --description /tmp/desc.md --acceptance /tmp/acc.md --json
```

Description should capture:
- What needs to be accomplished (not how)
- Edge cases discovered in interview
- Constraints and requirements

Do NOT add: file/line refs, sizing, implementation approach — that's plan's job.

### For File Path

Rewrite the file with refined spec:
- Preserve any existing structure/format
- Add sections for areas covered in interview
- Include edge cases, acceptance criteria
- Keep it requirements-focused (what, not how)

This is typically a pre-epic doc. After interview, suggest `/flow-next:plan <file>` to create epic + tasks.

## Completion

Show summary:
- Number of questions asked
- Key decisions captured
- What was written (Flow ID updated / file rewritten)
- Doc-aware mode (when `DOC_AWARE=1` was active): glossary terms added/updated via `flowctl glossary add`, decision entries written via `flowctl memory add --track knowledge --category decisions`, glossary conflicts captured under `## Glossary Conflicts`

Suggest next step based on input type:
- New idea / epic without tasks → `/flow-next:plan fn-N`
- Epic with tasks → `/flow-next:work fn-N` (or more interview on specific tasks)
- Task → `/flow-next:work fn-N.M`
- File → `/flow-next:plan <file>`

## Notes

- This process should feel thorough - user should feel they've thought through everything
- Quality over speed - don't rush to finish
