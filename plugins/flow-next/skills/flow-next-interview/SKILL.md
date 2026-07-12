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

Compare `.flow/meta.json` `setup_version` to the plugin version; on mismatch, escalate once per plugin version. Fail-open throughout: a missing `jq`, `.flow/meta.json`, or plugin manifest silently continues.

```bash
SETUP_VER=$(jq -r '.setup_version // empty' .flow/meta.json 2>/dev/null)
PLUGIN_JSON="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
PLUGIN_VER=$(jq -r '.version' "$PLUGIN_JSON" 2>/dev/null || echo "unknown")
VERSION_ACK=$(jq -r '.version_ack // empty' .flow/meta.json 2>/dev/null)
if [[ -n "$SETUP_VER" && "$PLUGIN_VER" != "unknown" && "$SETUP_VER" != "$PLUGIN_VER" ]]; then
  if [[ "${FLOW_RALPH:-}" == "1" || -n "${REVIEW_RECEIPT_PATH:-}" \
        || "${FLOW_AUTONOMOUS:-}" == "1" || "${ARGUMENTS:-}" == *mode:autonomous* \
        || "$VERSION_ACK" == "$PLUGIN_VER" ]]; then
    echo "Local setup v${SETUP_VER} differs from plugin v${PLUGIN_VER}. Run /flow-next:setup to refresh local scripts." >&2
  else
    echo "FLOW_SETUP_ASK ${SETUP_VER} ${PLUGIN_VER}"
  fi
fi
```

If the block printed a `FLOW_SETUP_ASK` line, before proceeding ask the user with AskUserQuestion (local setup differs from the plugin; refresh now?), offering exactly the options **Refresh now**, **Remind me next version**, **Skip this run**, then continue the skill whichever is chosen:
- **Refresh now**: pause and have the user run `/flow-next:setup` in this session (do not run setup yourself), then continue once it finishes.
- **Remind me next version**: record the acknowledgement so this version is not re-asked (only a later plugin version re-arms it), then continue. Run this self-contained write (fail-open: on any error, continue anyway):
  ```bash
  PJ="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/.claude-plugin/plugin.json"
  PV=$(jq -r '.version' "$PJ" 2>/dev/null)
  [[ -n "$PV" && "$PV" != "null" ]] && rm -f .flow/meta.json.tmp && jq --arg v "$PV" '.version_ack = $v' .flow/meta.json > .flow/meta.json.tmp && mv .flow/meta.json.tmp .flow/meta.json
  ```
- **Skip this run**: continue without writing anything; the next invocation asks again.

Any other output (the one-line differs notice, or nothing) is non-blocking: continue.

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

Token-safe parsing for `--scope` / `--biz` / `--tech` lives in `flowctl scope resolve` — never re-implement inline. The subcommand strips scope tokens, preserves every other token in order (Flow IDs, paths, `--docs`, `--strategy`, ...), and emits the resolved scope plus a `defaulted` flag. The resolver's fallback when no scope flag is passed is `technical` (1.0.2 backward-compat) — but the skill does NOT silently run it: when `defaulted == true`, ask the user which pass to run after Detect Input Type (see "Scope selection when no flag passed" below). `technical` applies only when that question cannot be asked.

```bash
# Run BEFORE the --docs / --strategy strip block. Conflict / invalid value
# → non-zero exit; SKILL propagates.
#
# `--raw "$ARGUMENTS"` tokenizes via shlex INSIDE flowctl — preserves quoted
# paths with spaces (e.g., `/flow-next:interview --biz "docs/my spec.md"`).
# Unquoted `$ARGUMENTS` would word-split into broken tokens.
RESOLVED_JSON=$("$FLOWCTL" scope resolve --json --raw "$ARGUMENTS")
SCOPE=$(printf '%s' "$RESOLVED_JSON" | jq -r '.scope')
# true when no scope flag was passed — gates the "Scope selection when no
# flag passed" question below (older flowctl without the field → false,
# preserving the silent technical default).
SCOPE_DEFAULTED=$(printf '%s' "$RESOLVED_JSON" | jq -r '.defaulted // false')
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
| `--scope=technical` (resolver fallback, also `--tech`) | autodetect cascade above runs | tech-owned sections (Architecture / API Contracts / Edge Cases / verifiable AC); preserves biz sections byte-for-byte; reads biz sections when populated, silent when absent |
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

## Scope selection when no flag passed

Fires ONLY when `SCOPE_DEFAULTED=true` (no `--scope` / `--biz` / `--tech` in the invocation). An explicit scope flag always wins and skips this section entirely.

Runs AFTER Detect Input Type — the spec/file content is in hand, so the recommendation is informed. Ask ONE `AskUserQuestion` (same blocking primitive as every interview question; the tool-unreachable fallback under "Question Format" applies):

- **header**: `Interview scope`
- **body**: `Which interview pass should run? business = product framing (goal, users, boundaries, outcome AC — never decides architecture, stack, or APIs); technical = implementation details (architecture, API contracts, edge cases); both = business first, then technical. Recommended: <X> — <one-sentence rationale from the target's current state>. Confidence: [judgment-call].`
- **options** (frozen): `business`, `technical`, `both`

Derive the recommendation from the target's current state:

- Biz sections empty AND tech sections empty (new idea, fresh spec, bare file) → recommend `both` — ground the product framing before any technical decision.
- Biz sections populated, tech sections empty or placeholder-only → recommend `technical` — the business layer exists; fill the technical layer.
- Tech sections populated, biz sections absent (1.0.2-shape solo spec) → recommend `technical` — refine in place.

Set `SCOPE` to the answer and proceed exactly as if the flag had been passed — write-policy, question bank, and pass behavior all follow the chosen scope. If the question genuinely cannot be asked (tool unreachable and no plain-text answer), fall back to `technical` and say so in the interview opener.

Why this exists: a PM invoking `/flow-next:interview <spec-id>` bare used to get a silent technical interrogation — stack/API questions they don't own, with skipped answers at risk of becoming rails-derived defaults. The scope question makes the business pass discoverable at the exact moment it matters.

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

- `question.body`: "<stakes>. <options summary>. Recommended: <X> — <one-sentence rationale>. Confidence: [high | judgment-call | your-call]."
- `question.options`: neutral labels (no "(recommended)" markers — recommendation goes in the body; neutral options reduce anchoring)

### Plain-language question contract (fn-90-adjacent field feedback, eval-validated)

Applies to EVERY question, both scopes. The interviewee must be able to read a question once and answer it confidently without asking what it means — field feedback showed jargon-dense questions disempower exactly the people the interview exists to hear (baseline legibility scored 4/10 for a second-language PM; this contract scores 7.5+ at ~30% fewer tokens).

- **Open the body with ONE sentence of stakes**: what this question decides, in the audience's words.
- **Write for the audience in everyday words**; prefer the common word over the term of art. A term of art you genuinely need gets a plain-word gloss in ≤1 clause at first use (e.g. "counter-metrics — things we'd hate to make worse").
- **No unexplained acronyms or tool/repo shorthand.** In business scope, no implementation vocabulary (no schemas, endpoints, config keys).
- **Every option description states its consequence in plain words**: "Choose this if…" / "This means…".

Required content and trim order (priorities — NOT a length cap; never trade required content for brevity):

- **ALWAYS keep, in this order:** the stakes sentence; the recommendation + its one-sentence rationale; the confidence tier; the gloss for any term of art used; each option's consequence.
- **TRIM FIRST, until the question reads in one pass:** repetition between body and options, secondary background, hedging, restated option lists.
- **Target shape** (calibration, not a ceiling): a body around 40-60 words with option descriptions around a dozen words each is what "done" usually looks like — reach it by trimming the trim-first list, never by dropping required content.

Confidence tiers (mandatory — pick one per question):

- `[high]` — strong codebase signal or convention match. Recommendation is load-bearing; user can usually accept.
- `[judgment-call]` — slight lean but reasonable people disagree. User's call carries weight.
- `[your-call]` — agent has no signal. "I genuinely don't know — your priority / domain knowledge / preference."

The `[your-call]` tier is **mandatory** when the agent has no basis for a recommendation. Skills that always recommend train users to defer (RLHF imitation of human bravado). Say so explicitly.

Examples (one per tier):

- `[high]`: "This decides where the new validation code lives so the next person can find it. Recommended: `src/utils/validation.ts` — three sibling validators already live there and the tests import from that module. Confidence: [high]." Options: `src/utils/validation.ts`, `src/validators/`, `new module` — each description says what choosing it means (e.g. "This means it sits beside the three existing validators").
- `[judgment-call]`: "This decides how long the rate-limiter remembers a result before re-checking (the cache TTL — time-to-live). Recommended: 60 seconds — short enough that stale answers stay rare, long enough to be worth caching. Confidence: [judgment-call]." Options: `30s`, `60s`, `300s`, `no cache` — with plain consequences ("Choose this if freshness matters more than speed").
- `[your-call]`: "This decides what error callers see when the upstream service times out. Recommended: none — it depends on what your callers expect and I found no existing convention to copy. Confidence: [your-call]." Options: `502`, `503`, `504`, `408`.

### Skipped Questions Are Not Answers

Leading with a recommendation NEVER implies consent. Distinguish three answer shapes:

- **Explicit answer** (an option picked, or a typed answer) → use it.
- **Explicit delegation** ("you decide", "go with your recommendation") → adopt the recommendation and note it as user-delegated; that is a real decision with a named consenter.
- **Skip / decline / no-signal** (question dismissed, "skip", "I don't know", "not my call", "ask someone else") → the question is UNRESOLVED. NEVER write the recommendation into a spec section as decided content — silently filling skipped questions with assumptions is the exact failure this rule exists to prevent.

For every skipped question:

1. Park it under `## Open Questions` with an owner hint and the agent's unconfirmed leaning: `**<question>** — skipped during interview; leaning <X>, unconfirmed. *(owner: engineering | product)*`
2. A skipped user-judgment question STAYS user-judgment-required — never demote it to codebase-/docs-answerable to backfill an answer (see the Pre-Question Taxonomy in [questions-shared.md](questions-shared.md)).
3. Keep a running skip count for the write-back checkpoint below and the Completion summary.

**Write-back consent checkpoint** — when the skip count is ≥1, ask ONE `AskUserQuestion` BEFORE writing the spec back:

- **header**: `Skipped items`
- **body**: `<N> question(s) were skipped during this interview. Recommended: park-open — record them under ## Open Questions with my unconfirmed leanings; nothing skipped becomes a decision. Confidence: [high].`
- **options** (frozen): `park-open` (default — Open Questions entries only), `fill-assumptions` (write the agent's recommendation into the relevant spec section, each marked inline `*(assumed — unconfirmed)*`, plus one Open Questions entry pointing at the markers for later ratification), `re-ask` (walk the skipped questions once more — answers and explicit delegations resolve normally; anything skipped again parks per park-open)

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

### Auxiliary-sections rule (applies to every pass)

The auxiliary sections — `Strategy Alignment` / `Strategy Conflicts` / `Glossary Conflicts` / `Conversation Evidence` / `Resolved via Codebase` / `Resolved via Project Docs` — are preserved byte-for-byte across passes and scope changes: no pass deletes or rewrites an auxiliary section another pass wrote. Each pass only ADDS its own: the biz pass adds `Resolved via Project Docs`; the tech pass adds `Resolved via Codebase`.

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
- **Auxiliary sections**: preserve byte-for-byte per the auxiliary-sections rule above; biz pass adds `Resolved via Project Docs` only.

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
- **Auxiliary sections**: preserve byte-for-byte per the auxiliary-sections rule above; tech pass adds `Resolved via Codebase` only.

### Both pass (`SCOPE == both`)

Runs biz pass first, then tech pass in the same skill invocation. Each phase enforces its own merge contract:

1. **Phase 1: biz pass** — runs the full biz-pass workflow above. Writes biz sections; preserves any pre-existing tech sections byte-for-byte (with placeholder lines under empty tech sections).
2. **Phase 2: tech pass** — runs the full tech-pass workflow above using the just-written biz output as in-memory context. Reads biz sections, cites them in the opener, writes tech sections, preserves biz sections byte-for-byte.

Auxiliary sections are preserved across both phases per the auxiliary-sections rule above.

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

The `## Resolved via Project Docs` section is auxiliary and biz-pass-only (parallel to `## Resolved via Codebase` for the tech pass). Preserved across scope changes per the auxiliary-sections rule above.

## Doc-aware behaviors — loaded on demand

**GATE:** when `DOC_AWARE=1` **or** `STRATEGY_AWARE=1` (set by the `--docs` / `--strategy` flags or the doc-aware autodetect in Setup), **read [`references/doc-aware.md`](references/doc-aware.md)** and apply its behaviors — Phase-zero glossary scan (a), fuzzy-term sharpening (b), decision-record write (d), and code-vs-strategy contradiction (e). On the default technical-scope, no-docs path (`DOC_AWARE=0` and `STRATEGY_AWARE=0`) skip it entirely — do not read the file. (Split out of the always-loaded SKILL.md so the default interview does not pay ~2.5k tokens for behaviors it never runs.)

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

## Write Refined Spec — templates loaded at completion

At the Completion step, **read [`references/write-back.md`](references/write-back.md)** for the spec-write template matching the input type — NEW IDEA (text, no Flow ID), EXISTING SPEC (`fn-N` with tasks), Flow Task (`fn-N.M`), or File Path — plus the shared `## Resolved via Codebase / Project Docs`, `## Glossary/Strategy Conflicts`, and `## Open Questions` section templates. Only the one matching branch runs; the file is loaded once, at write-time, not held through the Q&A.

## Tracker sync (opt-in) — spec push/pull + merge

**Optional. Runs only when the tracker bridge is active AND `interview` is opted in. With no tracker configured this is a no-op — the interview behaves exactly as today.** After the refined spec is written back (`## Write Refined Spec`), project the enrichment to the linked tracker issue and reconcile two-way (R6): interview enrichment done in flow flows back to the tracker; tracker-side edits fold into the right flow sections. (Skip for the file-input case — there is no flow spec yet.)

```bash
LEAF="$($FLOWCTL config get tracker.perEvent.interview --json | jq -r '.value')"   # read the leaf ONCE (shared gating predicate — work SKILL.md)
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
   && [ "$LEAF" != "off" ] && [ "$LEAF" != "null" ]; then
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
- Skipped questions (ONLY when ≥1): count + disposition from the write-back checkpoint (parked under `## Open Questions` / filled as `*(assumed — unconfirmed)*` / re-asked) — omit the line entirely when nothing was skipped
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
