---
name: flow-next-interview
description: Interview user in-depth about a spec, task, or spec file to extract complete implementation details. Use when user wants to flesh out a spec, refine requirements, or clarify a feature before building. Triggers on /flow-next:interview with Flow IDs (fn-1-add-oauth, fn-1-add-oauth.2, or legacy fn-1, fn-1.2, fn-1-xxx, fn-1-xxx.2) or file paths.
user-invocable: false
---

# Flow interview

Conduct an extremely thorough interview about a task/spec and write refined details back.

**IMPORTANT**: This plugin uses `.flow/` for ALL task tracking. Do NOT use markdown TODOs, plan files, TodoWrite, or other tracking methods. All task state must be read and written via `flowctl`.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Pre-check: Local setup version

If `.flow/meta.json` exists and has `setup_version`, compare to plugin version:
```bash
SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
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
- **Flow spec ID** `fn-N-slug` (e.g., `fn-1-add-oauth`) or legacy `fn-N`/`fn-N-xxx`: Fetch with `flowctl show`, write back with `flowctl spec set-plan`
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

### Parse `--scope=business|technical|both` (fn-44.1 plumbing)

Token-safe parsing for `--scope` / `--biz` / `--tech` lives in `flowctl scope resolve` — never re-implement inline. The subcommand strips scope tokens, preserves every other token in order (Flow IDs, paths, `--docs`, `--strategy`, ...), and emits the resolved scope. Default scope when no scope flag is passed: `technical` (1.0.2 backward-compat).

```bash
# Run BEFORE the --docs / --strategy strip block. Conflict / invalid value
# → non-zero exit; SKILL propagates.
#
# `--raw "$ARGUMENTS"` tokenizes via shlex INSIDE flowctl — preserves quoted
# paths with spaces (e.g., `/flow-next:interview --biz "docs/my spec.md"`).
# Unquoted `$ARGUMENTS` would word-split into broken tokens.
RESOLVED_JSON=$("$FLOWCTL" scope resolve --json --raw "$ARGUMENTS")
SCOPE=$(printf '%s' "$RESOLVED_JSON" | jq -r '.scope')
# `remaining_args` is a JSON array of strings. Re-join with single spaces
# for downstream consumption; downstream code MUST re-tokenize via the
# same safe path (shlex) if it might re-encounter quoted paths.
ARGUMENTS=$(printf '%s' "$RESOLVED_JSON" | jq -r '.remaining_args | join(" ")')
```

The section-write policy for the resolved scope is computed by `flowctl scope write-policy`, called BEFORE any markdown edit. It returns which sections the pass MAY write and which it MUST preserve byte-for-byte (per the fn-44 spec Edge Cases merge contract):

```bash
# Build the current-sections JSON from the existing spec (T2 wires this).
# `flowctl scope write-policy <scope> --current-sections-json -` then emits
# {writable, preserved, decision_context, placeholder_write} as JSON.
WRITE_POLICY=$(echo "$CURRENT_SECTIONS" | "$FLOWCTL" scope write-policy "$SCOPE" --current-sections-json -)
```

The question-bank path for the resolved scope is resolved by `flowctl scope bank`, called when loading the question taxonomy:

```bash
# Resolves to questions-business.md, questions-technical.md, or (for `both`)
# the technical bank path (both-mode reads both banks).
BANK_PATH=$("$FLOWCTL" scope bank "$SCOPE")
```

The full pass-aware behavior (loading the resolved bank, per-section writes that honor the policy, technical-pass-reads-business-sections-first) lives in the "Scope-aware pass behavior" section below. The skill MUST call these subcommands rather than re-implementing parse/policy logic inline.

### Parse `--docs` / `--no-docs` / `--strategy` / `--no-strategy` flags

Strip the four doc-aware override flags from `$ARGUMENTS` before input-type detection so they don't get confused for a Flow ID or path:

```bash
RAW_ARGS="$ARGUMENTS"
DOC_AWARE_FORCE=""        # "" = autodetect, "on" = forced on, "off" = forced off (controls glossary + decisions)
STRATEGY_AWARE_FORCE=""   # "" = autodetect, "on" = forced on, "off" = forced off (controls strategy independently)

# Glossary + decisions: --docs / --no-docs (mutually exclusive; --no-docs wins)
if [[ "$RAW_ARGS" == *"--no-docs"* ]]; then
  DOC_AWARE_FORCE="off"
  RAW_ARGS="${RAW_ARGS//--no-docs/}"
elif [[ "$RAW_ARGS" == *"--docs"* ]]; then
  DOC_AWARE_FORCE="on"
  RAW_ARGS="${RAW_ARGS//--docs/}"
fi

# Strategy: explicit --strategy / --no-strategy always wins. Otherwise --docs / --no-docs cascades.
# Order: explicit pair first (mutually exclusive; --no-strategy wins on conflict), then docs cascade.
if [[ "$RAW_ARGS" == *"--no-strategy"* ]]; then
  STRATEGY_AWARE_FORCE="off"
  RAW_ARGS="${RAW_ARGS//--no-strategy/}"
elif [[ "$RAW_ARGS" == *"--strategy"* ]]; then
  STRATEGY_AWARE_FORCE="on"
  RAW_ARGS="${RAW_ARGS//--strategy/}"
elif [[ "$DOC_AWARE_FORCE" == "off" ]]; then
  # --no-docs alone cascades to strategy: matrix row 3 says all three off.
  STRATEGY_AWARE_FORCE="off"
elif [[ "$DOC_AWARE_FORCE" == "on" ]]; then
  # --docs alone cascades to strategy: matrix row 2 says all three on.
  STRATEGY_AWARE_FORCE="on"
fi

RAW_ARGS=$(printf "%s" "$RAW_ARGS" | tr -s ' ' | sed 's/^ //;s/ $//')
# RAW_ARGS now contains the Flow ID / file path / empty.
```

Each pair is mutually exclusive (the `if/elif` checks the negation first so it wins on conflict). The `--docs` / `--strategy` tokens get left in the residual `RAW_ARGS` after stripping, which surfaces downstream as an unrecognized argument — loud failure beats silent acceptance of conflicting state.

**Flag matrix** — doc-aware flags (rows describe glossary / decisions / strategy gates):

| Flags | Glossary | Decisions | Strategy |
|-------|----------|-----------|----------|
| (default) | autodetect | autodetect | autodetect |
| `--docs` | on | on | on |
| `--no-docs` | off | off | off |
| `--no-docs --strategy` | off | off | on |
| `--docs --no-strategy` | on | on | off |

`--docs` / `--no-docs` cascade to strategy when no explicit `--strategy` / `--no-strategy` is passed (matrix rows 2 + 3). Explicit `--strategy` / `--no-strategy` always wins (matrix rows 4 + 5) and is the only way to drive a different value into strategy than into glossary + decisions. The matrix is the contract.

**Scope x doc/strategy** — the `--scope` axis is orthogonal to the doc-aware matrix above. Each row of this table is a valid combination:

| Scope | Doc-aware default | Pass behavior |
|-------|------------------|---------------|
| `--scope=technical` (default, also `--tech`) | autodetect cascade above runs | tech-owned sections (Architecture / API Contracts / Edge Cases / verifiable AC); preserves biz sections byte-for-byte; reads biz sections when populated, silent when absent |
| `--scope=business` (also `--biz`) | autodetect cascade still runs; doc-awareness does NOT auto-activate from biz pass alone (`R26` adds project-docs investigation independently) | biz-owned sections (Goal & Context / Boundaries / outcome AC / `### Motivation`); preserves tech sections byte-for-byte; writes placeholder `*Pending technical-scope interview pass.*` ONLY under EMPTY tech sections |
| `--scope=both` | autodetect cascade runs | runs biz pass first, then tech pass; same merge contract applies in each phase |

R26 project-docs investigation is gated on `SCOPE=business` (and the biz-pass phase of `both`) — runs BEFORE drafting the first biz question, regardless of doc-aware autodetect state.

### Doc-aware autodetect

Decide whether doc-aware mode (behaviors a-e below) activates. `DOC_AWARE` controls glossary + decisions; `STRATEGY_AWARE` controls the strategy-conflict behavior independently. Each has three paths (forced-on / forced-off / autodetect) per the flag matrix above.

```bash
# DOC_AWARE: glossary + decisions
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

# STRATEGY_AWARE: strategy (independent of DOC_AWARE — autodetects on its own signal)
STRATEGY_AWARE=0
if [[ "$STRATEGY_AWARE_FORCE" == "on" ]]; then
  STRATEGY_AWARE=1
elif [[ "$STRATEGY_AWARE_FORCE" == "off" ]]; then
  STRATEGY_AWARE=0
else
  STRAT_FILLED=$("$FLOWCTL" strategy status --json 2>/dev/null | jq -r '.sections_filled // 0')
  if [[ "${STRAT_FILLED:-0}" -ge 1 ]]; then
    STRATEGY_AWARE=1
  fi
fi
```

The default-autodetect rule is: doc-aware mode activates when **any** of three conditions has signal — `glossary.total_terms > 0` (a) OR a decision entry exists (b) OR `strategy.sections_filled >= 1` (c). The two flag pairs (`--docs` / `--no-docs` and `--strategy` / `--no-strategy`) override (a)+(b) and (c) independently per the matrix above.

**Why `total_terms > 0` and `sections_filled >= 1` rather than `[[ -f <file> ]]`:** `flowctl glossary remove` leaves a `# Glossary` H1 husk after the last term is removed; `flowctl strategy` leaves a frontmatter-plus-H1 husk under the same R18 invariant. Both files are project state, intentionally retained. A presence-only check would false-positive on an empty husk and surface phantom doc-aware questions when no canonical vocabulary / strategic intent is actually defined. `glossary list --json` and `strategy status --json` walk the file and count populated entries; both report zero for a husk.

When `DOC_AWARE=1`, behaviors (a)-(d) below layer onto the standard interview workflow. When `STRATEGY_AWARE=1`, behavior (e) layers on. When both are 0, the interview proceeds exactly as today.

## Detect Input Type

**Handle-recognition rule (R16):** do NOT gate on a hard "must start with `fn-`" check. Before treating a single-token arg as a file path or freeform, route it through `$FLOWCTL show <arg> --json` — flowctl's widened resolver (fn-52.10) maps a tracker key (`wor-17` / `wor-17.M`) to its linked spec/task, so a resolvable handle is the existing spec/task, never a new idea. Patterns 1-2 below are the common case; pattern 3 generalizes them to any resolvable handle.

1. **Flow spec ID pattern**: matches `fn-\d+(-[a-z0-9-]+)?` (e.g., fn-1-add-oauth, fn-12, fn-2-fix-login-bug)
   - Fetch: `$FLOWCTL show <id> --json`
   - Read spec: `$FLOWCTL cat <id>`

2. **Flow task ID pattern**: matches `fn-\d+(-[a-z0-9-]+)?\.\d+` (e.g., fn-1-add-oauth.3, fn-12.5)
   - Fetch: `$FLOWCTL show <id> --json`
   - Read spec: `$FLOWCTL cat <id>`
   - Also get parent spec context: `$FLOWCTL cat <spec-id>`

3. **Resolvable tracker handle**: any single-token arg (not an `.md` path) that `$FLOWCTL show <arg> --json` resolves — e.g. a Linear key `wor-17` (spec) or `wor-17.3` (task). Use the canonical id from the JSON; a `.`-containing handle is a task (fetch parent spec too), otherwise a spec. Treat exactly like patterns 1-2; never re-create.

4. **File path**: a path-like token / `.md` extension that does NOT resolve via `flowctl show`
   - Read file contents
   - If file doesn't exist, ask user to provide valid path

## Interview Process

**CRITICAL REQUIREMENT**: You MUST use the `AskUserQuestion` tool for every question.

- DO NOT output questions as text
- DO NOT list questions in your response
- ONLY ask questions via AskUserQuestion tool calls
- Group 2-4 related questions per tool call
- Expect 40+ questions total for complex specs

**Anti-pattern (WRONG)**:
```
Question 1: What database should we use?
Options: a) PostgreSQL b) SQLite c) MongoDB
```

**Correct pattern**: Call AskUserQuestion tool with question and options.

### Question Format: Lead with Recommendation

Every `AskUserQuestion` body must include the agent's recommended option AND a confidence tier. Mirrors the canonical phrasing in `flow-next-audit/SKILL.md:64` ("Lead with the recommended option and a one-sentence rationale"). Call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded. Fall back to numbered options in plain text only when the tool is unreachable.

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
4. **One `AskUserQuestion` call per turn**, period — never queue multiple tool calls back-to-back. Within that single call you may bundle 2-4 closely-related sub-questions per the existing batching rule above; do NOT pad with loosely-related questions just to hit four. The intent: one focused checkpoint per turn so the user isn't barraged with unrelated decisions in parallel. Use multi-select within a sub-question when options are non-exclusive.

Example flow:

> Q: "Does this feature need persistence?"
> A: "No, ephemeral state is fine."
> [agent prunes the {DB choice, schema design, migration plan} sub-tree]
> Q: "Skipped DB questions — you said ephemeral. Next: how should this state survive page reloads?"

### Investigate Codebase Before Asking

Before every question, classify it via the [questions-shared.md](questions-shared.md) **Pre-Question Taxonomy** (hoisted out of the per-scope banks so both biz and tech reference the same classifier):

- **Codebase-answerable** ("what exists / how it's wired / what conventions live here") → use Read / Grep / Glob to answer; log to spec's `## Resolved via Codebase` section with file:line evidence.
- **Glossary-lookup-answerable** (`DOC_AWARE=1` only) — terms with a canonical entry in the nearest-ancestor `GLOSSARY.md` → silently resolve from the entry; log to spec's `## Glossary Conflicts` section only when the user's wording diverges from canonical AND the term is load-bearing (see behavior (a) below).
- **User-judgment-required** ("what should exist / what tradeoff to make / what priority") → ask via `AskUserQuestion`.

If you find yourself answering a "should" question via grep, that's the bug. Stop and ask the user.

#### Code-versus-assertion contradiction (`DOC_AWARE=1` — behavior (c))

When grep / Read reveals the code disagrees with something the user asserted ("we already have X at path Y" but Y is gone, or "the auth flow uses OAuth" but the code uses API keys), do **not** silently log under `## Resolved via Codebase`. Surface the contradiction as an `AskUserQuestion`:

- **header**: `Code mismatch?`
- **body**: `Code shows <X> at <file:line>; you said <Y>. Recommended: <treat-code-as-source-of-truth | update-spec-to-match-code | revisit-the-area>. Confidence: [<tier>].`
- **options**: frozen — `match-code` (revise spec to align with what's there), `update-code` (treat the assertion as the goal; flag the divergence as a task), `clarify` (user explains; agent re-investigates with new context).

Confidence tier: `[high]` when grep evidence is unambiguous (file does not exist, function signature is clearly different); `[judgment-call]` when interpretation is at play (similar names, partial overlap, recent rename). Never silently pick a side — the user owns the resolution.

The bar for surfacing: a meaningful contradiction that affects spec correctness. If the user says "the validator returns boolean" and grep shows it returns `Result<bool, Error>`, surface. If the user paraphrases a function's role and grep shows the role matches but the implementation differs in unrelated detail, log under `## Resolved via Codebase` and move on.

## Scope-aware pass behavior

The interview runs in one of three scoped modes resolved by `flowctl scope resolve` (above). Each scope writes a different set of sections back to the spec and reads a different set as context. The full merge contract — which sections each pass writes, which it preserves byte-for-byte, and how `## Decision Context` H3 promotion works — is computed by `flowctl scope write-policy` (called BEFORE any markdown edit). The structural canon for sections is `plugins/flow-next/templates/spec.md` (per R17 — never re-embed the section list inline; cross-link the template).

### Compute the write policy

Before writing anything back, build the current-sections-state JSON from the existing spec markdown (or an empty object for new specs) and call `scope write-policy`. The policy result tells you which sections are writable, which are preserved, and how to handle the `## Decision Context` substructure conditional.

**One policy call per pass** — when `SCOPE == both`, compute the biz policy first, run the biz pass, then **recompute** the current-sections state from the post-biz-pass result and compute a fresh technical policy for phase 2. A single pre-edit policy call for `both` cannot correctly decide tech-pass `Decision Context` shape (the biz pass may have promoted FLAT → substructured) or tech-pass placeholder replacement (biz pass may have written `*Pending technical-scope interview pass.*` under empty tech sections that the tech pass must now overwrite).

```bash
# Build CURRENT_SECTIONS by inspecting the existing spec markdown:
#   decision_context_has_h3:    spec has `### Motivation` / `### Implementation Tradeoffs` under `## Decision Context`
#   biz_pass_ran:               spec has populated `## Goal & Context` body OR a `### Motivation` H3
#   tech_sections_have_content: per-tech-section {name: bool} for whether the body has content
#                               beyond the placeholder `*Pending technical-scope interview pass.*`
#
# For a brand-new spec (no markdown yet), CURRENT_SECTIONS='{}' is fine.
CURRENT_SECTIONS='{"decision_context_has_h3": <bool>, "biz_pass_ran": <bool>, "tech_sections_have_content": {"Architecture & Data Models": <bool>, "API Contracts": <bool>, "Edge Cases & Constraints": <bool>}}'

# For SCOPE == business or SCOPE == technical: one call.
WRITE_POLICY=$(printf '%s' "$CURRENT_SECTIONS" | "$FLOWCTL" scope write-policy "$SCOPE" --current-sections-json -)

# For SCOPE == both: TWO calls — biz first, then recompute state + tech.
#
#   BIZ_POLICY=$(printf '%s' "$CURRENT_SECTIONS" | "$FLOWCTL" scope write-policy business --current-sections-json -)
#   # ... run biz pass, write biz sections (in memory or to disk) ...
#   # Rebuild CURRENT_SECTIONS_AFTER_BIZ from the post-biz state — biz_pass_ran=true,
#   # decision_context_has_h3 likely true now (Motivation H3 written), placeholder lines
#   # under empty tech sections counted as "no content" for tech-pass overwrite logic:
#   CURRENT_SECTIONS_AFTER_BIZ='{"decision_context_has_h3": true, "biz_pass_ran": true, "tech_sections_have_content": {"Architecture & Data Models": <still-bool>, ...}}'
#   TECH_POLICY=$(printf '%s' "$CURRENT_SECTIONS_AFTER_BIZ" | "$FLOWCTL" scope write-policy technical --current-sections-json -)
#   # ... run tech pass under TECH_POLICY ...
```

The policy JSON shape:

```json
{
  "scope": "business|technical|both",
  "writable": ["<section names this scope may write>"],
  "preserved": ["<sections this scope MUST preserve byte-for-byte>"],
  "decision_context": {
    "shape": "flat|substructured",
    "writable_h3": ["<H3 names writable when substructured>"],
    "preserved_h3": ["<H3 names preserved byte-for-byte>"],
    "promote_flat_to_implementation_tradeoffs": <bool>
  },
  "placeholder_write": ["<tech sections under biz pass that should get the placeholder line>"]
}
```

### Load the right question bank

Resolve the question-bank file path via `flowctl scope bank`:

```bash
# Resolves to questions-business.md (biz), questions-technical.md (tech), or
# questions-technical.md (both — the technical bank is loaded for the tech
# phase; biz phase loads questions-business.md when it runs).
BANK_PATH=$("$FLOWCTL" scope bank "$SCOPE")
```

When `$SCOPE` is `business` or `both`, load `questions-business.md` for the biz phase questions. When `$SCOPE` is `technical` or `both`, load `questions-technical.md` for the tech phase. Both banks reference `questions-shared.md` for the `Pre-Question Taxonomy` and `Interview Guidelines` blocks — read the shared file first so the classifier applies symmetrically across passes.

### Business pass (`SCOPE == business`, or first phase of `both`)

Run BEFORE the first AskUserQuestion call:

1. **Project-docs investigation (R26)** — see "Investigate Project Docs Before Asking (business pass)" below. Symmetric to the codebase-investigation rule for the tech pass. Items resolved by docs land in `## Resolved via Project Docs`. The user is NOT asked about things the project docs already define.
2. **Draft only user-judgment-required biz questions** — load `questions-business.md` for the question taxonomy. Walk problem framing, target user/persona, success metrics, MVP boundary, business constraints, what-not-to-build, prioritization rationale, business risks, UX expectations.

Per-section write behavior (per the write-policy):

- **Writable biz sections** (`Goal & Context`, `Boundaries`, outcome-AC, `### Motivation` under `## Decision Context`): write/refine from interview answers.
- **Preserved tech sections** (`Architecture & Data Models`, `API Contracts`, `Edge Cases & Constraints`): MUST be preserved byte-for-byte. If a tech section is EMPTY (listed in `placeholder_write`), write the placeholder line `*Pending technical-scope interview pass.*` under its heading so the read-back makes the intentional emptiness visible. If a tech section has content, leave it untouched (refine-mode for a re-run on an already-tech-populated spec).
- **`## Decision Context`** (per `decision_context` shape):
  - When `shape == "substructured"` and `promote_flat_to_implementation_tradeoffs == true` (FLAT body exists from a prior tech-only pass): promote the existing flat body byte-for-byte into a new `### Implementation Tradeoffs` H3 (preserve the prose verbatim — same content, just under a new H3), and write the new `### Motivation` H3 as a sibling.
  - When `shape == "substructured"` and `promote_flat_to_implementation_tradeoffs == false` (H3s already exist): preserve `### Implementation Tradeoffs` byte-for-byte; write/refine ONLY `### Motivation`.
- **`## Acceptance Criteria`**: append outcome-AC R-IDs (R-IDs are append-only across passes per fn-29 rules — never renumber, never replace; take the next unused number).
- **Auxiliary sections** (`Strategy Alignment` / `Strategy Conflicts` / `Glossary Conflicts` / `Conversation Evidence` / `Resolved via Codebase`): preserve byte-for-byte. Biz pass adds `Resolved via Project Docs` only.

### Technical pass (`SCOPE == technical`, default; or second phase of `both`)

Run BEFORE the first AskUserQuestion call:

1. **Read biz sections when populated** — if `## Goal & Context`, `## Boundaries`, `### Motivation` (under `## Decision Context`), or outcome-AC R-IDs are populated, read them as constraint context. Cite them in the interview opener (e.g., "Reading from the existing business layer: target user is X, MVP boundary excludes Y. Tech questions below..."). When biz sections are absent (default solo-dev 1.0.2-shape spec), proceed silently with technical-only questions — no opener about missing biz context.
2. **Codebase investigation** — existing "Investigate Codebase Before Asking" rule applies unchanged. Items resolved via Read/Grep/Glob land in `## Resolved via Codebase`.

Per-section write behavior (per the write-policy):

- **Writable tech sections** (`Architecture & Data Models`, `API Contracts`, `Edge Cases & Constraints`, verifiable-AC): write/refine from interview answers. May overwrite `*Pending technical-scope interview pass.*` placeholder strings.
- **Preserved biz sections** (`Goal & Context`, `Boundaries`): MUST be preserved byte-for-byte.
- **`## Decision Context`** (per `decision_context` shape):
  - When `shape == "flat"` (no H3s exist, no biz pass has run — default zero-flag-tech case on a fresh/legacy spec): write/refine the flat body in place. Do NOT introduce `### Motivation` / `### Implementation Tradeoffs` H3 substructure. Preserves R22 1.0.2 backward compat.
  - When `shape == "substructured"` (`### Motivation` already exists from a prior biz pass, or the existing spec has the substructure): preserve `### Motivation` body byte-for-byte; write/refine ONLY `### Implementation Tradeoffs`.
- **`## Acceptance Criteria`**: append verifiable-AC R-IDs (R-IDs are append-only — never renumber).
- **Auxiliary sections** (`Strategy Alignment` / `Strategy Conflicts` / `Glossary Conflicts` / `Conversation Evidence` / `Resolved via Project Docs`): preserve byte-for-byte. Tech pass adds `Resolved via Codebase` only.

### Both pass (`SCOPE == both`)

Runs biz pass first, then tech pass in the same skill invocation. Each phase enforces its own merge contract:

1. **Phase 1: biz pass** — runs the full biz-pass workflow above. Writes biz sections; preserves any pre-existing tech sections byte-for-byte (with placeholder lines under empty tech sections).
2. **Phase 2: tech pass** — runs the full tech-pass workflow above using the just-written biz output as in-memory context. Reads biz sections, cites them in the opener, writes tech sections, preserves biz sections byte-for-byte.

Auxiliary sections (`Strategy Alignment` / `Strategy Conflicts` / `Glossary Conflicts` / `Conversation Evidence` / `Resolved via Codebase` / `Resolved via Project Docs`) are preserved across both phases — neither phase deletes or rewrites an auxiliary section the other phase wrote.

If the user interrupts between phase 1 and phase 2, the biz sections are written but the tech sections retain placeholder lines. Re-running `--scope=technical` later completes the spec.

### Investigate Project Docs Before Asking (business pass — R26)

Symmetric to the "Investigate Codebase Before Asking" rule for the tech pass (above, under "Interview Process"). When `SCOPE == business` (or the biz phase of `both`), the agent MUST investigate project documentation BEFORE drafting any biz question.

Read — in order, with the bounded reads called out so this doesn't balloon into a multi-hour scan:

1. `README.md` (repo root) — full read.
2. `CHANGELOG.md` (or project-equivalent release notes — `RELEASES.md`, `HISTORY.md`) — full read.
3. `STRATEGY.md` (repo root) — full read.
4. `GLOSSARY.md` (repo root) — full read.
5. `knowledge/decisions/` (or `.flow/memory/knowledge/decisions/` — `flowctl memory list --track knowledge --category decisions --json` enumerates entries) — read the table-of-contents + first paragraph of each of the most-recent 10 entries (NOT full bodies; the first paragraph carries the decision; deeper drill-down is on-demand).
6. `.flow/specs/` index (`flowctl specs --json` lists open specs) — scan titles + status; full-read only specs whose titles plausibly overlap the current spec's domain.
7. `docs/` directory (if present at repo root) — scan filenames; full-read only files whose names plausibly overlap.

Classify biz questions via the **Pre-Question Taxonomy** before asking:

- **Project-docs-answerable** ("what does the strategy say / what does CHANGELOG show we've already shipped / what does GLOSSARY define the canonical term as / what decision did we record for X") → resolve from the docs; log to spec's `## Resolved via Project Docs` section with `path:line` evidence (or `path` + section heading when line numbers are noisy).
- **User-judgment-required** ("what should our success metric be / what's MVP scope / what should we explicitly NOT build") → ask via `AskUserQuestion`.

If you find yourself asking the user a biz question that README/CHANGELOG/STRATEGY already answers, that's the bug. Stop and resolve from docs. Symmetric form of the existing "if you find yourself answering a 'should' question via grep, that's the bug" rule.

The `## Resolved via Project Docs` section is auxiliary and biz-pass-only (parallel to `## Resolved via Codebase` for the tech pass). Preserved across scope changes alongside `Strategy Alignment`, `Strategy Conflicts`, `Glossary Conflicts`, `Conversation Evidence`, and `Resolved via Codebase` — tech pass never deletes or rewrites any auxiliary section the biz pass produced.

## Doc-aware behaviors

Five behaviors layer onto the standard interview workflow when their respective gate is open:

- Behaviors (a)-(d) are gated on `DOC_AWARE=1` (glossary + decisions signal). When `DOC_AWARE=0`, skip them.
- Behavior (e) is gated on `STRATEGY_AWARE=1` (strategy signal). When `STRATEGY_AWARE=0`, skip it.

The two gates are independent (see flag matrix above) — `DOC_AWARE` and `STRATEGY_AWARE` may differ within the same interview session.

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

When a hit passes the load-bearing filter AND the user's wording conflicts with canonical (alias used instead of canonical, or definition contradicts), surface as the **first interview question** via `AskUserQuestion`:

- **header**: `Term mismatch?`
- **body**: `You used "<user-wording>"; GLOSSARY.md defines "<canonical>" as "<one-line definition>". Recommended: <use-canonical | redefine | this-is-different>. Confidence: [<tier>].`
- **options**: frozen — `use-canonical` (the user meant the existing term; spec uses canonical wording), `redefine` (user is updating the term meaning; spec proceeds with new wording, agent will re-write `GLOSSARY.md` via `flowctl glossary add` after the interview), `this-is-different` (the words collide but the concepts differ; spec uses a fresh disambiguating term — capture in `## Glossary Conflicts`).

Confidence tier: `[high]` when the canonical entry is recent and the user's wording cleanly maps to an `avoid` alias; `[judgment-call]` when meaning could plausibly have drifted; `[your-call]` when the term sits in user-domain territory the agent has no purchase on.

**Throttle:** at most one Phase-zero glossary question per interview turn. If multiple terms hit, surface the most load-bearing one first; the rest fold into the natural conversation flow as they come up. Bombarding the user with vocabulary questions before the core spec questions is the failure mode this filter prevents.

### Behavior (b) — Fuzzy-term sharpening

Across the conversation, watch for overloaded language — words the user keeps using whose meaning could plausibly shift between turns ("workflow", "session", "task" when a Flow `task` already has meaning, etc.). When you spot one:

1. Propose a canonical via `AskUserQuestion`:
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

2. **Show the draft via `AskUserQuestion` before writing** — same pattern as `/flow-next:capture` Phase 4 read-back:
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

   The `decisions` category is registered in flowctl's memory schema (Task 1 of the original decisions epic). Optional fields `--decision-status` (default `accepted`), `--superseded-by`, and `--alternatives-considered` are available; pass them when the conversation supplies them and skip otherwise.

4. **On `edit`**, ask one follow-up `AskUserQuestion` for which field changes (title / body / module / tags), capture the revision, re-show the draft, loop. Hard cap at 2 edit cycles before defaulting to `approve` / `skip`.

5. **On `skip`**, do nothing — the choice still appears in spec prose; only the memory entry is suppressed.

**At most one decision write per interview turn.** Even if multiple gate-passing decisions surface, ask one at a time; subsequent asks adapt to the user's energy level for read-back.

### Behavior (e) — Code-versus-strategy contradiction (`STRATEGY_AWARE=1` only)

Parallel structure to behavior (a) — Phase-zero glossary scan. Before drafting the first question batch in a `STRATEGY_AWARE=1` session, run a strategy scan against the user's request.

```bash
"$FLOWCTL" strategy read --json
```

JSON shape (selected fields used here):

```json
{
  "name": "<product-name>",
  "target_problem": "...",
  "approach": "...",
  "tracks": "### track-a\nOne line on track A.\n_Why it serves the approach:_ ...\n\n### track-b\n...",
  "last_updated": "2026-05-01",
  "path": "STRATEGY.md"
}
```

`tracks` is a **raw markdown string** — H3 sub-blocks of the form `### <track-name>` followed by a one-line description and a `_Why it serves the approach:_` line. Parse the H3 names locally. Empty section bodies (any of `target_problem`, `approach`, `tracks`) surface as `""` (empty string), not null — `(.field // "")` style fallbacks keep parsing well-formed when an optional section is missing.

Walk the user's request looking for two patterns:

1. **Track-name mismatch** — the user uses a noun-phrase that names a track-like investment area, but the wording diverges from a canonical track in `STRATEGY.md` (e.g. user says "Initiative" but `tracks` defines "### Track"). Treat the user's wording as a candidate alias for the closest canonical track and surface as a question if load-bearing for the spec.
2. **Direction conflict** — the user describes a goal or constraint that contradicts the `approach` or one of the active tracks (e.g. approach says "we ship CLI tools, not SaaS" but the user is asking the spec to add a managed dashboard service).

For each hit, evaluate the same load-bearing filter as behavior (a): casual passing mention does not trigger; mention that defines behavior or shapes acceptance does.

When a hit passes the filter, surface via `AskUserQuestion`:

- **header**: `Strategy mismatch?`
- **body**: `You said "<user-wording>"; STRATEGY.md (<path>) <track|approach> says "<canonical-wording>". Recommended: <align-with-strategy | flag-as-drift | this-is-different>. Confidence: [<tier>].`
- **options**: frozen — `align-with-strategy` (the user meant the existing track / honors the approach; spec uses canonical wording), `flag-as-drift` (the spec is intentionally pushing back on the strategy; capture in `## Strategy Conflicts` and proceed), `this-is-different` (the words collide but the concepts differ; spec uses a fresh disambiguating term — also capture in `## Strategy Conflicts`).

Confidence tier: `[high]` when the strategy entry is recent and the user's wording cleanly maps to a canonical track or directly contradicts the verbatim approach; `[judgment-call]` when meaning could plausibly have drifted; `[your-call]` when the strategic direction sits in user-domain territory the agent has no purchase on.

**Throttle:** at most one strategy-conflict question per interview turn (parallel to behavior (a)'s glossary throttle). If multiple strategy mismatches hit, surface the most load-bearing one first; the rest fold into the natural conversation flow as they come up. Bombarding the user with strategy-alignment questions before the core spec questions is the failure mode this throttle prevents. Combined with the (a) and (d) throttles, the per-turn doc-aware question budget is **3 max** (1 glossary + 1 decision-record + 1 strategy).

The output of behavior (e) lands in a new spec section, `## Strategy Conflicts`, parallel to `## Glossary Conflicts`. Format: per-line entries with user-wording / canonical-strategy-wording / STRATEGY.md path / resolution-chosen. Lets reviewers see where the spec aligns or pushes back on strategic intent. Strategy conflicts are read-only signal for `/flow-next:sync`'s plan-sync agent — the interview never edits `STRATEGY.md`.

## Question Categories

Question banks are scope-resolved via `flowctl scope bank "$SCOPE"`:

- `SCOPE=technical` (default) → load [questions-technical.md](questions-technical.md).
- `SCOPE=business` → load [questions-business.md](questions-business.md). Covers problem framing, target user/persona, success metrics, MVP boundary, business constraints, what-NOT-to-build, prioritization rationale, business risks, UX expectations.
- `SCOPE=both` → load `questions-business.md` for phase 1 then `questions-technical.md` for phase 2.

Both banks share the `Pre-Question Taxonomy` and `Interview Guidelines` blocks, hoisted to [questions-shared.md](questions-shared.md) — single source of truth referenced by both banks.

## NOT in scope (defer to /flow-next:plan)

- Research scouts (codebase analysis)
- File/line references
- Task creation (interview refines requirements, plan creates tasks)
- Task sizing (S/M/L)
- Dependency ordering
- Phased implementation details
- **Time estimates, deadlines, durations, sprint cadence, "ship before X" framing.** Agents can't estimate their own work and shouldn't push the user into time-based prioritization debates. If the user volunteers a deadline in answer to another question, acknowledge it without cascading into MVP-Scope or What-NOT-to-Build re-asks driven by the time pressure.

## Write Refined Spec

After interview complete, write everything back — **scope depends on input type**.

The canonical spec section structure lives in [`plugins/flow-next/templates/spec.md`](../../templates/spec.md) (the single source of truth — never re-embed the section list inline per R17). The templates below show the additional **interview audit sections** that layer onto the canonical structure; the underlying spec sections (`## Goal & Context`, `## Architecture & Data Models`, ...) come from the template.

Section-write rules from the scope-aware pass behavior (above) MUST be honored — the write-policy result from `flowctl scope write-policy` is the source of truth for which sections this scope writes vs preserves. The `## Decision Context` substructure / FLAT-vs-substructured promotion logic is in the write-policy; do not invent inline.

### For NEW IDEA (text input, no Flow ID)

Create spec with interview output. **DO NOT create tasks** — that's `/flow-next:plan`'s job.

The canonical section layout for the spec body is in [`plugins/flow-next/templates/spec.md`](../../templates/spec.md) — the **template file is the seed** for the canonical 7-section structure (`Goal & Context`, `Architecture & Data Models`, `API Contracts`, `Edge Cases & Constraints`, `Acceptance Criteria`, `Boundaries`, `Decision Context`). `flowctl spec skeleton` is **NOT** the seed here — it returns a 1.0.2-shape skeleton (`Overview` / `Scope` / `Approach` / `Quick commands` / `Acceptance` / `References`) for R22 byte-for-byte backward-compat with the pre-1.1.0 `flowctl spec create` output, which uses different section names than the new canonical template. Reading from `flowctl spec skeleton` here would seed sections the scope-aware write-policy doesn't recognize. Read the template file directly. Fill the scope-owned canonical sections per the write-policy above, then append the auxiliary interview-audit sections below the canonical body (the R21 sync-codex drift guard forbids re-embedding the canonical section sequence in any skill markdown — the template file is the only allowed location).

```bash
$FLOWCTL spec create --title "..." --json

# Build the spec body in-memory:
#   1. Seed from the canonical template FILE (not `flowctl spec skeleton` —
#      that command stays 1.0.2-compatible per R22; its section names
#      (Overview / Scope / Approach / Quick commands / Acceptance / References)
#      don't match the scope-aware write-policy's canonical section names).
#
#      Resolve the template via the 4-tier discovery cascade — first match wins;
#      do not read later tiers once a hit is found:
#        1. <repo_root>/SPEC.md           (user-customized, uppercase preferred)
#        2. <repo_root>/spec.md           (user-customized, lowercase honored)
#        3. .flow/templates/spec.md       (project-local copy from /flow-next:setup)
#        4. ${CLAUDE_PLUGIN_ROOT:-${DROID_PLUGIN_ROOT:-${CODEX_HOME:-$HOME/.codex}}}/templates/spec.md
#                                         (bundled — canonical source of truth)
#
#      Case-insensitive FS handling (macOS APFS, Windows NTFS): SPEC.md and
#      spec.md may resolve to the same inode. Probe via:
#        HITS=$(ls -1 SPEC.md spec.md 2>/dev/null | sort -u | wc -l | tr -d ' ')
#      where 0 → tier 1+2 miss, fall to tier 3; 1 → single hit (or case-insensitive
#      collapse) — use it; 2 → case-sensitive FS with both distinct, prefer
#      SPEC.md and print a stderr warning.
#
#      Walker (bash):
#        REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
#        TEMPLATE_PATH=""
#        HITS=$(ls -1 "$REPO_ROOT/SPEC.md" "$REPO_ROOT/spec.md" 2>/dev/null | sort -u | wc -l | tr -d ' ')
#        if [ "$HITS" = "2" ]; then
#          TEMPLATE_PATH="$REPO_ROOT/SPEC.md"
#          echo "warn: both SPEC.md and spec.md exist at repo root; preferring uppercase." >&2
#        elif [ -f "$REPO_ROOT/SPEC.md" ]; then
#          TEMPLATE_PATH="$REPO_ROOT/SPEC.md"
#        elif [ -f "$REPO_ROOT/spec.md" ]; then
#          TEMPLATE_PATH="$REPO_ROOT/spec.md"
#        elif [ -f ".flow/templates/spec.md" ]; then
#          TEMPLATE_PATH=".flow/templates/spec.md"
#        else
#          TEMPLATE_PATH="${CLAUDE_PLUGIN_ROOT:-${DROID_PLUGIN_ROOT:-${CODEX_HOME:-$HOME/.codex}}}/templates/spec.md"
#        fi
#        TEMPLATE=$(cat "$TEMPLATE_PATH")
#
#      The template contains: frontmatter, the 7 canonical sections
#      (Goal & Context, Architecture & Data Models, API Contracts,
#      Edge Cases & Constraints, Acceptance Criteria, Boundaries,
#      Decision Context) with scope-owner HTML-comment annotations. Fill
#      bodies from interview answers under your scope's writable sections
#      per the write-policy. Frontmatter + HTML-comment scope-owner markers
#      may be stripped from the final spec body — they're authoring guidance,
#      not user-visible spec content.
#   2. Append the auxiliary interview-audit sections (only those that fired):

cat > /tmp/spec.md <<'EOF'
<canonical body from skeleton, with interview-answered prose under each
 writable section per the write-policy — biz pass fills biz-owned sections,
 tech pass fills tech-owned, placeholders under empty other-side sections>

## Resolved via Codebase
(optional — written by the technical pass when codebase-investigation resolved items)
Items the agent answered via Read / Grep / Glob, with file:line evidence. Separate from items the user answered. Lets reviewers spot-check assumptions later.

## Resolved via Project Docs
(optional — written by the business pass per R26 when project-docs investigation resolved items)
Items the agent answered via README / CHANGELOG / STRATEGY / GLOSSARY / knowledge decisions / .flow specs / docs, with `path` or `path:line` evidence. Symmetric to `## Resolved via Codebase` but biz-pass-only.

## Glossary Conflicts
(optional — only when DOC_AWARE=1 surfaced behavior-(a) hits during the interview)
Per-term: user-wording vs. canonical term, the resolution chosen (use-canonical / redefine / this-is-different), file:line of the canonical entry. Lets reviewers see where vocabulary tightened.

## Strategy Conflicts
(optional — only when STRATEGY_AWARE=1 surfaced behavior-(e) hits during the interview)
Per-line: user-wording vs. canonical-strategy-wording (track name or approach), STRATEGY.md path, resolution chosen (align-with-strategy / flag-as-drift / this-is-different). Lets reviewers see where the spec aligns or pushes back on strategic intent. Read-only signal for plan-sync — the interview never edits STRATEGY.md.

## Open Questions
Unresolved items that need research during planning
EOF

$FLOWCTL spec set-plan <id> --file /tmp/spec.md --json
```

Then suggest: "Run `/flow-next:plan fn-N` to research best practices and create tasks."

### For EXISTING SPEC (fn-N that already has tasks)

**First check if tasks exist:**
```bash
$FLOWCTL tasks --spec <id> --json
```

**If tasks exist:** Only update the spec (add edge cases, clarify requirements). **Do NOT touch task specs** — plan already created them.

**If no tasks:** Update spec, then suggest `/flow-next:plan`.

The canonical section layout for the spec body is in [`plugins/flow-next/templates/spec.md`](../../templates/spec.md). Read the existing spec, refine sections under your scope per the write-policy (preserving sections owned by the other scope byte-for-byte), and append/update the auxiliary interview-audit sections. The R21 drift guard forbids re-embedding the canonical section sequence in this skill — read the existing body, do not regenerate from a template.

```bash
# Read existing spec body:
EXISTING=$("$FLOWCTL" cat <id>)

# Refine canonical sections under your scope's writable list (per write-policy)
# while preserving sections owned by the other scope byte-for-byte. Append the
# auxiliary interview-audit sections (only those that fired):

cat > /tmp/spec.md <<'EOF'
<merged body: canonical sections from $EXISTING, with this scope's writable
 sections refined from interview answers, other-scope sections preserved
 byte-for-byte per the write-policy>

## Resolved via Codebase
(optional — written by the technical pass when codebase-investigation resolved items)
Items the agent answered via Read / Grep / Glob, with file:line evidence. Separate from items the user answered.

## Resolved via Project Docs
(optional — written by the business pass per R26 when project-docs investigation resolved items)
Items the agent answered via README / CHANGELOG / STRATEGY / GLOSSARY / knowledge decisions / .flow specs / docs, with `path` or `path:line` evidence.

## Glossary Conflicts
(optional — only when DOC_AWARE=1 surfaced behavior-(a) hits during the interview)
Per-term: user-wording vs. canonical term, the resolution chosen, file:line of the canonical entry.

## Strategy Conflicts
(optional — only when STRATEGY_AWARE=1 surfaced behavior-(e) hits during the interview)
Per-line: user-wording vs. canonical-strategy-wording, STRATEGY.md path, resolution chosen.

## Open Questions
Unresolved items
EOF

$FLOWCTL spec set-plan <id> --file /tmp/spec.md --json
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
- Or suggest interviewing the spec instead: `/flow-next:interview <spec-id>`

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

This is typically a pre-spec doc. After interview, suggest `/flow-next:plan <file>` to create spec + tasks.

## Tracker sync (opt-in) — spec push/pull + merge

**Optional. Runs only when the tracker bridge is active AND `interview` is opted in. With no tracker configured this is a no-op — the interview behaves exactly as today.** After the refined spec is written back (`## Write Refined Spec`), project the enrichment to the linked tracker issue and reconcile two-way (R6): interview enrichment done in flow flows back to the tracker; tracker-side edits fold into the right flow sections. (Skip for the file-input case — there is no flow spec yet.)

```bash
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
   && [ "$($FLOWCTL config get tracker.perEvent.interview --json | jq -r '.value')" != "off" ] \
   && [ "$($FLOWCTL config get tracker.perEvent.interview --json | jq -r '.value')" != "null" ]; then
  # Invoke the flow-next-tracker-sync skill: push/pull/reconcile the spec body
  # (operation follows the perEvent leaf — push | pull | reconcile).
  #   skill: flow-next-tracker-sync   (operation: <leaf> <spec-id>)
  # Unlinked spec → flow-first push (create + link) first, then reconcile
  # (tracker-sync §Phase 3 create-if-unlinked). No-op only if no transport reachable; genuine
  # body conflicts surface scoped (interactive) or queue (Ralph). Best-effort — a
  # tracker failure never blocks the interview write-back.
  :
fi
```

## Mark-ready offer (optional; flow spec inputs only)

After the write-back (and the tracker-sync block above), optionally offer to mark the refined spec ready — the same consent shape and visibility predicate as capture's read-back follow-up (fn-58). Applies ONLY when the input was a flow spec (Detect Input Type patterns 1/3) — task ids and file paths carry no spec readiness.

```bash
READY_STATE=$($FLOWCTL config get tracker.readyState --json 2>/dev/null | jq -r '.value // empty')
READY_ADOPTED=$($FLOWCTL specs --json 2>/dev/null | jq '[.specs[] | select(.ready == true)] | length' 2>/dev/null || echo 0)
# Offer IFF READY_ADOPTED >= 1 AND READY_STATE is empty (probe failures degrade to "don't offer").
```

Both must hold:

- `READY_ADOPTED -ge 1` — readiness is adopted in this repo (≥1 spec already marked ready); non-adopters see no question anywhere. First adoption enters via `flowctl spec ready`, the tracker ceremony, or prime — never via this prompt.
- `READY_STATE` empty — `tracker.readyState` NOT configured. Tracker-authoritative readiness is a one-way pull; never invite a local edit the next sync would silently revert.

When the predicate holds, ask once via `AskUserQuestion` (lead with recommendation):

- **header**: `Mark ready?`
- **body**: `Mark <spec-id> ready for execution? Readiness is adopted in this repo (<READY_ADOPTED> ready spec(s)). Recommended: keep-draft — re-read the refined spec on disk first; readiness is the human gate, not an interview reflex. Confidence: [judgment-call].`
- **options** (frozen): `mark-ready` (run `$FLOWCTL spec ready <spec-id> --json` — idempotent), `keep-draft` (default — no readiness write)

Best-effort: a failed `spec ready` prints a warning and continues — never blocks the interview write-back.

**Interview NEVER auto-resets `ready` on refinement.** The interview edits the spec in place — a previously-blessed spec stays ready unless the human unmarks it. Only `capture --rewrite` (a full re-authoring) resets readiness.

## Completion

Show summary:
- Number of questions asked
- Key decisions captured
- What was written (Flow ID updated / file rewritten)
- Tracker sync: when active and `interview` opted in, whether the spec body was pushed/pulled/reconciled to the linked issue (else a silent no-op)
- Readiness (ONLY when the mark-ready offer fired): marked ready vs kept draft — omit the line entirely otherwise (no readiness noise for non-adopters)
- **Scope mode**: which pass(es) ran — biz / tech / both — and which spec sections were written vs preserved byte-for-byte (cite the write-policy result). For `--scope=business`: project-docs resolutions captured under `## Resolved via Project Docs` (R26).
- Doc-aware mode (when `DOC_AWARE=1` was active): glossary terms added/updated via `flowctl glossary add`, decision entries written via `flowctl memory add --track knowledge --category decisions`, glossary conflicts captured under `## Glossary Conflicts`
- Strategy-aware mode (when `STRATEGY_AWARE=1` was active): strategy conflicts captured under `## Strategy Conflicts` (read-only — interview never edits STRATEGY.md)

Suggest next step based on input type:
- New idea / spec without tasks → `/flow-next:plan fn-N`
- Spec with tasks → `/flow-next:work fn-N` (or more interview on specific tasks)
- Task → `/flow-next:work fn-N.M`
- File → `/flow-next:plan <file>`

## Notes

- This process should feel thorough - user should feel they've thought through everything
- Quality over speed - don't rush to finish
