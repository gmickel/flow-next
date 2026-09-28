---
name: flow-next-refine
description: Refine a spec, task, or spec file before building - one question pass for the decisions that would change what gets built, optionally focused by a free-text --scope lens (business, technical, qa, ...), or a read-only research pass (--scope=research) that resolves library versions, changed APIs, and gotchas from external docs into the spec. Use when a named product, authority, or costly-to-reverse technical decision is open, or when the spec names a library or API the repo does not already use. Triggers on /flow-next:refine with Flow IDs (fn-1-add-oauth, fn-1-add-oauth.2, or legacy fn-1, fn-1.2, fn-1-xxx, fn-1-xxx.2) or file paths.
user-invocable: false
---

# Flow refine

Refine a task/spec: ask only the questions whose answers would change what gets built, and write the answers back, or (`--scope=research`) resolve the spec's external-library unknowns from official docs and write them back. The `interview` name remains a forwarding alias for one release.

**`.flow/` is the only task tracker.** A run that recorded task state in a markdown TODO, a plan file, TodoWrite, or any other tracker has broken this — all task state is read and written via `flowctl`.

### Chart boundary

Existing-spec clarification stays **primary**. Interview refines a valid spec with unresolved judgment questions. Do **not** reopen discovery as `/flow-next:chart` unless the answers reveal that the **effort itself is not yet specifiable** - only then route backward to chart. Clear work that never needed a chart stays out of chart. Unsure of the hop: `flow-next:flow-next-flow --explain`.

## Preamble

**CRITICAL: flowctl is BUNDLED — NOT installed globally.** `which flowctl` will fail (expected). Define once; subsequent blocks use `$FLOWCTL`:

```bash
FLOWCTL="${DROID_PLUGIN_ROOT:-${CLAUDE_PLUGIN_ROOT}}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

**Role**: technical interviewer, spec refiner
**Goal**: settle the decisions that would change what gets built and that only the user can make; resolve, record, or leave everything else to implementation

## Input

Full request: $ARGUMENTS

Accepts a Flow spec ID, a Flow task ID, a resolvable tracker handle, a file path, or nothing — recognition rules and the fetch command per type are in "Detect Input Type" below (single copy; the write-back command per type is in `references/write-back.md`).

Examples:
- `/flow-next:refine fn-1-add-oauth`
- `/flow-next:refine fn-1-add-oauth.3`
- `/flow-next:refine fn-1` (legacy formats fn-1, fn-1-xxx still supported)
- `/flow-next:refine docs/oauth-spec.md`
- `/flow-next:refine fn-1-add-oauth --scope=qa` (the same interview, focused on what QA decides)
- `/flow-next:refine fn-1-add-oauth --scope=research` (external-docs pass; no questions)

If empty, ask: "What should I interview you about? Give me a Flow ID (e.g., fn-1-add-oauth) or file path (e.g., docs/spec.md)"

## Setup

### Read the scope lens

`--scope=<value>` is an optional free-text lens: `business`, `technical`, `qa`, `security`, or any other audience. `--biz` means `--scope=business` and `--tech` means `--scope=technical`. Take these tokens out of the arguments before input detection; several values combine into one lens. There is one interview whatever the lens: the lens focuses which open decisions you look for and ask about (a QA lens looks for what QA would decide: what counts as done, which failures matter, what must be testable), and you interpret it from its words. No lens means no filter. Never ask which scope to run.

**`--scope=research` is a different pass and asks no questions.** Skip the doc-aware autodetect and the interview: run Detect Input Type below, then read [`references/research-scope.md`](references/research-scope.md) and follow it. The interview never reads that file.

### Parse `--docs` / `--no-docs` / `--strategy` / `--no-strategy` flags

The four doc-aware override flags must be stripped from `$ARGUMENTS` before input-type detection so they don't get confused for a Flow ID or path. Two force variables carry the result — `""` = autodetect, `"on"` = forced on, `"off"` = forced off:

```bash
RAW_ARGS="$ARGUMENTS"
DOC_AWARE_FORCE=""        # controls glossary + decisions
STRATEGY_AWARE_FORCE=""   # controls strategy independently
```

**When the invocation carried ANY of `--docs` / `--no-docs` / `--strategy` / `--no-strategy`**, STOP and read [`references/doc-aware.md`](references/doc-aware.md) § Flag parsing before proceeding — it holds the strip block (both pairs mutually exclusive, negation wins on conflict), the cascade rules, and the flag matrix that is the contract for each combination. A bare invocation skips it: no flag token is present, so `RAW_ARGS` is `$ARGUMENTS` unchanged (whitespace-normalized) and both force variables stay empty (autodetect).

### Doc-aware autodetect

Decide whether doc-aware mode activates. `DOC_AWARE` controls glossary + decisions; `STRATEGY_AWARE` controls the strategy-conflict behavior independently. Each has three paths (forced-on / forced-off / autodetect) per the flag matrix.

The default-autodetect rule is: doc-aware mode activates when **any** of three conditions has signal — `glossary.total_terms > 0` (a) OR a decision entry exists (b) OR `strategy.sections_filled >= 1` (c). The two flag pairs override (a)+(b) and (c) independently. Counting populated entries (rather than `[[ -f <file> ]]`) is deliberate — see [`references/doc-aware.md`](references/doc-aware.md) § Why counts, not file presence.

```bash
# One preflight bundle for this run. Missing/failed values retain fail-open gates.
REFINE_PREFLIGHT="${TMPDIR:-/tmp}/flow-refine-preflight-<suffix>.json"   # reuse this literal path
"$FLOWCTL" preflight --json > "$REFINE_PREFLIGHT" 2>/dev/null || printf '{}' > "$REFINE_PREFLIGHT"
# DOC_AWARE: glossary + decisions. Probes and parses fail OPEN (|| DOC_AWARE=1).
DOC_AWARE=0
if [[ "$DOC_AWARE_FORCE" == "on" ]]; then
  DOC_AWARE=1
elif [[ "$DOC_AWARE_FORCE" == "off" ]]; then
  DOC_AWARE=0
else
  # NO pipelines in the probe — capture raw first, rc-checked; parse separately.
  GLOSSARY_RAW="$(jq -ce 'if .probes.glossary.status == "ok" then .probes.glossary.value else error("glossary probe") end' "${TMPDIR:-/tmp}/flow-refine-preflight-<suffix>.json" 2>/dev/null)" || DOC_AWARE=1
  DECISIONS_RAW="$(jq -ce 'if .probes.decisions.status == "ok" then .probes.decisions.value else error("decisions probe") end' "${TMPDIR:-/tmp}/flow-refine-preflight-<suffix>.json" 2>/dev/null)" || DOC_AWARE=1
  if [ "$DOC_AWARE" = "0" ]; then
    TERMS="$(printf '%s' "$GLOSSARY_RAW" | jq -r '.total_terms // 0' 2>/dev/null)" || DOC_AWARE=1
    DECS="$(printf '%s' "$DECISIONS_RAW" | jq -r '.entry_count // 0' 2>/dev/null)" || DOC_AWARE=1
  fi
  if [ "$DOC_AWARE" = "0" ] && { [ "${TERMS:-0}" -gt 0 ] || [ "${DECS:-0}" -gt 0 ]; }; then
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
  STRATEGY_RAW="$(jq -ce 'if .probes.strategy.status == "ok" then .probes.strategy.value else error("strategy probe") end' "${TMPDIR:-/tmp}/flow-refine-preflight-<suffix>.json" 2>/dev/null)" || STRATEGY_AWARE=1
  if [ "$STRATEGY_AWARE" = "0" ]; then
    STRAT_FILLED="$(printf '%s' "$STRATEGY_RAW" | jq -r '.sections_filled // 0' 2>/dev/null)" || STRATEGY_AWARE=1
  fi
  if [ "$STRATEGY_AWARE" = "0" ] && [ "${STRAT_FILLED:-0}" -ge 1 ]; then
    STRATEGY_AWARE=1
  fi
fi

if [ "$DOC_AWARE" = "1" ] || [ "$STRATEGY_AWARE" = "1" ]; then
  echo "DOC-AWARE GATE ACTIVE — STOP. Read references/doc-aware.md before drafting the first question."
fi
```

When the sentinel prints, STOP and **read [`references/doc-aware.md`](references/doc-aware.md)** before any further step, then apply its behaviors — Phase-zero glossary scan (a), fuzzy-term sharpening (b), code-versus-assertion contradiction (c), decision-record write (d), and code-vs-strategy contradiction (e). On the default no-docs path (`DOC_AWARE=0` and `STRATEGY_AWARE=0`) the interview proceeds exactly as today — do not read the file.

## Detect Input Type

**Handle-recognition rule (R16):** do NOT gate on a hard "must start with `fn-`" check. Before treating a single-token arg as a file path or freeform, route it through `$FLOWCTL show <arg> --json` — flowctl's widened resolver maps a tracker key (`wor-17` / `wor-17.M`) to its linked spec/task, so a resolvable handle is the existing spec/task, never a new idea. Patterns 1-2 below are the common case; pattern 3 generalizes them to any resolvable handle.

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

Done when: the argument is classified as exactly one of the four patterns, every non-`.md` single-token arg was routed through `$FLOWCTL show <arg> --json` before that classification, and the target's content (spec body, task + parent spec, or file) is in hand for the interview.

## Interview Process

**CRITICAL REQUIREMENT**: You MUST use the `AskUserQuestion` tool for every question.

- DO NOT output questions as text
- DO NOT list questions in your response
- ONLY ask questions via AskUserQuestion tool calls
- Ask in rounds: each round carries the whole frontier (see Question Order below), split across AskUserQuestion calls of up to 4 questions each

**Anti-pattern (WRONG)**:
```
Question 1: What database should we use?
Options: a) PostgreSQL b) SQLite c) MongoDB
```

**Correct pattern**: Call AskUserQuestion tool with question and options.

### The one test

Ask a question only when all three hold: a wrong guess would build the wrong thing or ship behaviour the user would reject; the code, the docs, a quick experiment, or implementation itself cannot settle it; and it is the answerer's call. Everything else you resolve (Investigate Before Asking below), record, or leave to work. A topic on the check-list below is not a reason to ask.

Check the spec for these, and ask about one only when the spec leaves it unclear and the question passes the test: who it is for; what done looks like; what is explicitly out; a constraint the domain implies (a regulation, a contract, a partner commitment); an irreversible data or contract change (a data model, a migration, a public contract); an external interface; a security boundary. A lens adds its audience's own open decisions to this list. Technical detail, performance and edge cases that implementation, review and QA will surface are left to them.

Stop as soon as no question that passes the test remains. Asking nothing is a good outcome: report "Nothing worth asking; the spec is clear enough to build." and skip the write-back unless investigation resolved something worth recording.

### Question Format: Lead with Recommendation

Every `AskUserQuestion` body must include the agent's recommended option AND a confidence tier. Mirrors the canonical phrasing in `flow-next-audit/SKILL.md` Interaction Principles ("Lead with the recommended option and a one-sentence rationale"). Call `ToolSearch` with `select:AskUserQuestion` first if its schema isn't loaded. Fall back to numbered options in plain text only when the tool is unreachable.

Pattern:

- `question.body`: "<stakes>. <options summary>. Recommended: <X> — <one-sentence rationale>. Confidence: [high | judgment-call | your-call]."
- `question.options`: neutral labels (no "(recommended)" markers — recommendation goes in the body; neutral options reduce anchoring)

### Plain-language question contract (field feedback, eval-validated)

Applies to EVERY question. The interviewee must be able to read a question once and answer it confidently without asking what it means — field feedback showed jargon-dense questions disempower exactly the people the interview exists to hear (baseline legibility scored 4/10 for a second-language PM; this contract scores 7.5+ at ~30% fewer tokens).

- **Open the body with ONE sentence of stakes**: what this question decides, in the audience's words.
- **Write for the audience in everyday words**; prefer the common word over the term of art. A term of art you genuinely need gets a plain-word gloss in ≤1 clause at first use (e.g. "counter-metrics — things we'd hate to make worse").
- **No unexplained acronyms or tool/repo shorthand.** A product question, or any question under a non-technical lens, carries no implementation vocabulary (no schemas, endpoints, config keys).
- **Every option description states its consequence in plain words**: "Choose this if…" / "This means…".
- **Gloss referenced acceptance criteria.** When a question cites a spec R-ID, attach a short plain-words gist at first mention — "R3 (the audit line's required fields)" — never a bare "R3" the interviewee must open the spec to decode. Gist, not quote: pasting full criterion text bloats the question body.

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

**Leading with a recommendation never implies consent.** Distinguish three answer shapes:

- **Explicit answer** (an option picked, or a typed answer) → use it.
- **Explicit delegation** ("you decide", "go with your recommendation") → adopt the recommendation and note it as user-delegated; that is a real decision with a named consenter.
- **Skip / decline / no-signal** (question dismissed, "skip", "I don't know", "not my call", "ask someone else") → the question is unresolved. **A skipped question's recommendation never enters a spec section as decided content.** A spec line that reads as settled while no answer, no explicit delegation, and no `## Open Questions` entry stands behind it has broken this — silently filling skipped questions with assumptions is the exact failure this rule exists to prevent.

For every skipped question:

1. Park it under `## Open Questions` with an owner hint and the agent's unconfirmed leaning: `**<question>** — skipped during interview; leaning <X>, unconfirmed. *(owner: engineering | product)*`
2. A skipped user-judgment question STAYS user-judgment-required — never demote it to codebase-/docs-answerable to backfill an answer (see Investigate Before Asking below).
3. Keep a running skip count for the write-back checkpoint below and the Completion summary.

**Write-back consent checkpoint** — when the skip count is ≥1, ask ONE `AskUserQuestion` BEFORE writing the spec back:

- **header**: `Skipped items`
- **body**: `<N> question(s) were skipped during this interview. Recommended: park-open — record them under ## Open Questions with my unconfirmed leanings; nothing skipped becomes a decision. Confidence: [high].`
- **options** (frozen): `park-open` (default — Open Questions entries only), `fill-assumptions` (write the agent's recommendation into the relevant spec section, each marked inline `*(assumed — unconfirmed)*`, plus one Open Questions entry pointing at the markers for later ratification), `re-ask` (walk the skipped questions once more — answers and explicit delegations resolve normally; anything skipped again parks per park-open)

### Question Order: Rounds over the Decision Tree

Map the interview as a **design tree**: every decision branches into the decisions that hang off it. The **frontier** is every question whose prerequisites are already settled — the questions you can ask NOW without guessing at answers you haven't heard yet. Work the tree in **rounds**: ask the whole frontier, wait for answers, recompute, repeat.

Concrete rules:

1. **Each round asks the entire current frontier.** A question whose answer depends on another question still open in this round belongs to a *later* round, not this one — never ask a question alongside its own prerequisite.
2. **Split the frontier across `AskUserQuestion` calls of up to 4 questions each**, grouped by topic (closest-related together), announced as one round ("Round N — part 1/2"). Never pad a call to reach 4; never hold a genuine frontier question back to a later round just to smooth pacing.
   **A frontier slot is earned** by passing the one test. Failure modes, concurrency, scale, portability, and testing qualify only when they pass it; implementation, review, and QA surface the rest. Pure-cosmetic polish (message wording, label/flag spelling, visual formatting) does not get its own question: fold it into a related question's options, or carry it as a stated default the user can veto at write-back.
   Standalone checkpoint questions (the code-mismatch question, the write-back consent checkpoint, the mark-ready offer) sit outside rounds — never labeled "Round N", never counted against round depth. Doc-aware meta-questions keep their own per-round budget (references/doc-aware.md): a meta-question deferred by that budget is pending for a later round, not dropped — the one sanctioned hold-back.
3. **Recompute the frontier after each round.** Answers reshape the tree — settled decisions unblock their dependents; adapt the next round to what you heard. Don't lock the whole tree before you start: deeper rounds are discovered from answers, not pre-scripted.
4. **Surface abandoned branches.** When an answer prunes a sub-tree, say so explicitly at the next round's opener: "Skipping persistence questions — you said no DB."
5. **Cap branch depth at 4 rounds** down any one branch. Research shows >4 prior turns rarely improves question quality — drop deeper threads, ask about something else. Heuristic; revisit if too restrictive in real use.
6. **Finish the round before recomputing.** If a later part of a round never got asked (tool error, interruption), ask the missed part first — never silently drop frontier questions and move on.

Example flow:

> Round 1 (frontier: persistence?, auth model?, error surface?) — asked together in one call.
> A: "No persistence — ephemeral is fine. API-key auth. Errors: existing JSON convention."
> [agent prunes the {DB choice, schema design, migration plan} sub-tree]
> Round 2 opener: "Skipping DB questions — you said ephemeral." (frontier now: reload survival?, key-tier limits? — the questions those answers unblocked)

Done when: the frontier is empty — every decision the tree opened is answered, explicitly delegated, parked under `## Open Questions`, or pruned with its abandoned branch named at a round opener — and every part of every round was actually asked (a part lost to a tool error is re-asked, never dropped).

### Investigate Before Asking

Before drafting the first round, read `STRATEGY.md` (repo root) and search the other project docs for what the spec touches rather than reading them end to end: `README.md`, `CHANGELOG.md`, `GLOSSARY.md`, the decisions track (`$FLOWCTL memory list --track knowledge --category decisions --json`), the titles of open specs (`$FLOWCTL specs --json`), and a `docs/` directory when there is one. Then classify every question before asking it:

- **Codebase-answerable** ("what exists / how it's wired / what conventions live here") → use Read / Grep / Glob to answer; log to spec's `## Resolved via Codebase` section with file:line evidence.
- **Project-docs-answerable** ("what does the strategy say / what have we already shipped / what did we decide about X") → resolve from the docs; log to spec's `## Resolved via Project Docs` section with `path:line` evidence.
- **Glossary-lookup-answerable** (`DOC_AWARE=1` only) — terms with a canonical entry in the nearest-ancestor `GLOSSARY.md` → silently resolve from the entry; log to spec's `## Glossary Conflicts` section only when the user's wording diverges from canonical AND the term is load-bearing (behavior (a) in [`references/doc-aware.md`](references/doc-aware.md)).
- **Experiment-answerable** — a fork that running something can settle (behaviour, timing, layout, output, performance, whether an eval separates two options) → run a throwaway experiment in `.flow/tmp/experiments/` instead of asking; log it to spec's `## Resolved via Experiment` section with the question, what was run, what was observed, and the decision it settled. The ask is the slow path: a question the user must relay back to the machine costs a round-trip the experiment answers in seconds. Safety predicate: an experiment runs automatically only when it is read-only or fully disposable (a scratch copy, a throwaway environment). One that needs live or shared state, credentials, the network, or a destructive command — a migration, a deployment, a write API — goes to the blocking question path. An inconclusive result (noise larger than the difference) is logged as inconclusive and the question goes to the user with the data attached. The experiment is evidence, never product code: discard it or fold its numbers into the spec.
- **User-judgment-required** ("what should exist / what tradeoff to make / what priority") → ask via `AskUserQuestion`.

If you find yourself answering a "should" question via grep, that's the bug. Stop and ask the user. Asking the user something the project docs already answer is the same bug in the other direction. Don't ask obvious questions, group related ones (multi-select for non-exclusive options), and probe answers that contradict each other.

**Divergent independent answers mean the question was underspecified.** When independent sources (scouts, docs, probes) return wildly divergent answers to the same question, do not average them and do not quietly pick a favorite — reframe the question more precisely and re-run it; divergence is a signal about the framing, not a vote to be tallied.

**Async fact-scouts (optional, rounds mode):** while the user answers the current round you MAY dispatch ONE read-only fact-scout subagent to resolve codebase lookups that gate NEXT-round questions. Before dispatching one, read [`references/fact-scouts.md`](references/fact-scouts.md) — the brief contract, scout tier, digest discipline, and the never-block rule are binding. Not dispatching a scout needs no reading: investigate inline as usual.

## Where answers go

Each answer is written into the section it belongs in, whatever the lens: a target user goes to `## Goal & Context`, an out-of-scope call to `## Boundaries`, a contract to `## API Contracts`, a testable commitment to `## Acceptance Criteria`, a rationale to `## Decision Context`. The section structure lives in `plugins/flow-next/templates/spec.md` (never re-embed the section list inline; cross-link the template). A section the project added through its own repo-root `SPEC.md` is a section like any other: an answer that belongs there goes there.

Every section no answer belongs in comes back byte-for-byte, and the read-back names every section this session changed, so a person refining their own layer sees any change outside it. Keep the layout the spec already has: when `## Decision Context` carries `### Motivation` / `### Implementation Tradeoffs` sub-headings (older refine runs and capture write them), put a rationale under the one it fits and never add or remove sub-headings to restructure the section.

### Auxiliary sections

The auxiliary sections — `Strategy Alignment` / `Strategy Conflicts` / `Glossary Conflicts` / `Conversation Evidence` / `Resolved via Codebase` / `Resolved via Project Docs` / `Resolved via Experiment` / `Resolved via Research` / `Parked unknowns` — come back byte-for-byte: refine never deletes or rewrites an entry an earlier session wrote. It only adds its own entries to `Resolved via Codebase`, `Resolved via Project Docs` and `Resolved via Experiment`, below any already there. `Resolved via Research` belongs to the research pass, the one writer allowed to replace it (under `--force`).

`Parked unknowns` is the one auxiliary section refine may take FROM, and only in the one way described in [`references/write-back.md`](references/write-back.md) § Parked unknowns: a bullet this session resolved graduates into the canonical section that owns it and is deleted here. Every other bullet comes back byte-for-byte, and no bullet this session did not resolve is rewritten, reordered, or reworded.

### Declined-scope ledger

When the user declines a feature or scope **as product judgment** — we could build this, we are choosing not to — record it in `.flow/memory/declined/<concept-slug>.md` on the FIRST such refusal: title, the decision in one line, short reasoning, then `## Prior requests` opened with today's date and the request that just came in. File already there → append the dated line to `## Prior requests` and leave the decision untouched. Agent-written prose, like the rest of `.flow/memory/` — no flowctl verb. The entry body follows the artifact prose contract in [docs/prose.md](../../docs/prose.md); proceed without it when the doc is absent.

**Never write one for scope declined because it already exists**, is already planned, or lives in another spec. That is an answer, not a refusal, and filing it teaches the next planner that shipped capability is rejected scope. A skipped question is not a decline either — skips go to `## Open Questions` per the skip contract.

### Acceptance-criteria rule

`## Acceptance Criteria` R-IDs are **append-only** across sessions — never renumber, never replace; take the next unused number. Source-tag each criterion this session appends (`[user]` = the human answering in this session, `[paraphrase]`, `[inferred]`, `[strategy:<track>]`); never tag or retag a criterion an earlier session wrote — see `references/write-back.md` § Source tags on acceptance criteria.

**Record an answer at the precision the user gave it.** A preference ("performance matters here") goes to `## Decision Context` as guidance, not an acceptance criterion. A number or measurable commitment becomes a criterion only when the user stated it; your recommended options never become thresholds. Refine does not ask for success metrics or latency budgets unless the spec is about them.

## Spec-count check (split proposal)

Interviews grow specs - and an epic-shaped input sometimes turns out to be more than one spec. Before the write-back, when the refined criteria set trips the spec-count tripwire, read [`spec-count.md`](../flow-next-flow/references/spec-count.md) (it owns the tripwire, what counts, and the independence partition) and propose a split only when its partition yields more than one spec.

Present the concrete allocation as ordinary printed markdown (per-spec titles, allocated criteria, dependency edges), then one short `AskUserQuestion`: `keep-single` (default) / `split-as-proposed` / `adjust`. On split: create each sibling via one `spec create --plan-file` (self-contained body; allocated criteria renumbered from R1 in the NEW spec), remove the moved criteria from the source spec's write-back, and record edges via `spec add-dep`. **Renumbering guard:** criteria a review cycle has already judged are never moved or renumbered — for those, keep them in place and record the proposal in `## Decision Context` instead. Autonomous/receipt-driven runs never split — record the proposal in `## Decision Context` as `### Split proposal (unactioned)`.

## NOT in scope (defer to /flow-next:plan)

- Research scouts (codebase analysis)
- File/line references
- Task creation (interview refines requirements, plan creates tasks)
- Task sizing (S/M/L)
- Dependency ordering
- Phased implementation details
- **Time estimates, deadlines, durations, sprint cadence, "ship before X" framing.** Agents can't estimate their own work and shouldn't push the user into time-based prioritization debates. If the user volunteers a deadline in answer to another question, acknowledge it without cascading into MVP-Scope or What-NOT-to-Build re-asks driven by the time pressure.

## Write Refined Spec — templates loaded at completion

At the Completion step, **read [`references/write-back.md`](references/write-back.md)** for the spec-write template matching the input type — NEW IDEA (text, no Flow ID), EXISTING SPEC (`fn-N` with tasks), Flow Task (`fn-N.M`), or File Path — plus the shared `## Resolved via Codebase / Project Docs / Experiment`, `## Glossary/Strategy Conflicts`, and `## Open Questions` section templates. Only the one matching branch runs; the file is loaded once, at write-time, not held through the Q&A.

## Post-write-back options (tracker sync, mark ready)

Both are conditional. Probe once after the write-back; each sentinel names the section to read.

```bash
# Tracker sync (opt-in): projects the enrichment to the linked issue and reconciles
# two-way. Skip entirely for the file-input case — there is no flow spec yet.
TRACKER_GATE=0
LEAF_RAW="$(jq -ce 'if .probes.config.status == "ok" then {value: .value.tracker.perEvent.interview} else error("config probe") end' "${TMPDIR:-/tmp}/flow-refine-preflight-<suffix>.json" 2>/dev/null)" || TRACKER_GATE=1
ACTIVE_RAW="$(jq -ce 'if .probes.tracker.status == "ok" then .probes.tracker.value else error("tracker probe") end' "${TMPDIR:-/tmp}/flow-refine-preflight-<suffix>.json" 2>/dev/null)" || TRACKER_GATE=1
if [ "$TRACKER_GATE" = "0" ]; then
  LEAF="$(printf '%s' "$LEAF_RAW" | jq -r '.value' 2>/dev/null)" || TRACKER_GATE=1
  ACTIVE="$(printf '%s' "$ACTIVE_RAW" | jq -r '.active' 2>/dev/null)" || TRACKER_GATE=1
fi
if [ "$TRACKER_GATE" = "0" ] && [ "${ACTIVE:-false}" = "true" ] \
   && [ -n "${LEAF:-}" ] && [ "${LEAF:-null}" != "null" ] && [ "${LEAF:-off}" != "off" ]; then
  TRACKER_GATE=1
fi
if [ "$TRACKER_GATE" = "1" ]; then
  echo "TRACKER-SYNC GATE ACTIVE — STOP. Read references/post-write-back.md#tracker-sync before continuing."
fi

# Mark-ready offer (flow spec inputs only — task ids and file paths carry no spec readiness).
READY_GATE=0
READY_STATE_RAW="$(jq -ce 'if .probes.config.status == "ok" then {value: .value.tracker.readyState} else error("config probe") end' "${TMPDIR:-/tmp}/flow-refine-preflight-<suffix>.json" 2>/dev/null)" || READY_GATE=1
SPECS_RAW="$("$FLOWCTL" specs --json 2>/dev/null)" || READY_GATE=1
if [ "$READY_GATE" = "0" ]; then
  READY_STATE="$(printf '%s' "$READY_STATE_RAW" | jq -r '.value // empty' 2>/dev/null)" || READY_GATE=1
  READY_ADOPTED="$(printf '%s' "$SPECS_RAW" | jq '[.specs[] | select(.ready == true)] | length' 2>/dev/null)" || READY_GATE=1
  if [ "$READY_GATE" = "0" ] && [ "${READY_ADOPTED:-0}" -ge 1 ] && [ -z "${READY_STATE:-}" ]; then
    READY_GATE=1
  fi
fi
if [ "$READY_GATE" = "1" ]; then
  echo "MARK-READY GATE ACTIVE — STOP. Read references/post-write-back.md#mark-ready-offer before continuing."
fi
```

When a sentinel prints, STOP and Read the named section of [`references/post-write-back.md`](references/post-write-back.md) before any further step. With no tracker configured and readiness unadopted, neither fires and the interview behaves exactly as today.

**Interview never auto-resets `ready` on refinement.** A run that leaves a previously-ready spec unready without the human unmarking it has broken this. The interview edits the spec in place — a previously-blessed spec stays ready unless the human unmarks it. Only `capture --rewrite` (a full re-authoring) resets readiness.

## Completion

Show summary:
- Number of questions asked — when it is zero, say "Nothing worth asking; the spec is clear enough to build."
- Skipped questions (ONLY when ≥1): count + disposition from the write-back checkpoint (parked under `## Open Questions` / filled as `*(assumed — unconfirmed)*` / re-asked) — omit the line entirely when nothing was skipped
- Key decisions captured
- What was written (Flow ID updated / file rewritten)
- Tracker sync: when active and the `tracker.perEvent.interview` leaf opted in (the leaf keeps its name; refine reads it), whether the spec body was pushed/pulled/reconciled to the linked issue (else a silent no-op)
- Readiness (ONLY when the mark-ready offer fired): marked ready vs kept draft — omit the line entirely otherwise (no readiness noise for non-adopters)
- **Sections changed**: every section this session wrote, and that the rest came back byte-for-byte; the lens, when one was given. Project-docs and experiment resolutions captured under `## Resolved via Project Docs` / `## Resolved via Experiment`, one line each with its decision. For `--scope=research`: the number of items written under `## Resolved via Research` with their sources, or the printed skip reason.
- Doc-aware mode (when `DOC_AWARE=1` was active): glossary terms added/updated via `flowctl glossary add`, decision entries written via `flowctl memory add --track knowledge --category decisions`, glossary conflicts captured under `## Glossary Conflicts`
- Strategy-aware mode (when `STRATEGY_AWARE=1` was active): strategy conflicts captured under `## Strategy Conflicts` (read-only — interview never edits STRATEGY.md)

Done when: every line above is either printed or absent because its stated ONLY-when condition did not hold — the question count and the sections-changed line are unconditional and always appear.

Suggest next step based on input type:
- New idea / spec without tasks → recommend `/flow-next:work fn-N --no-plan` for a ready cohesive spec. Use `/flow-next:plan fn-N` when dependencies, ownership, staged delivery, or execution constraints make decomposition useful; use `/flow-next:plan-review fn-N` for independent design review. Risk or multiple files alone do not require decomposition.
- Spec with tasks → `/flow-next:work fn-N` (or more interview on specific tasks)
- Task → `/flow-next:work fn-N.M`
- File → `/flow-next:capture` to turn the refined document into a spec
- Any of the above → also offer a compact visual digest for reviewing the refined result at a glance — `/flow-next:visual fn-N` for a spec input, `/flow-next:visual fn-N.M` for a task input, `/flow-next:visual <file-path>` for the file input (an option the user picks, never run for them).

**Host command form:** print every copy-pasteable flow-next command here in the spelling this host invokes — the flat `/flow-next-<name>` form when the resolved plugin root carries `.flow-next-opencode-manifest` (an OpenCode install — the same signal setup's host detection uses); on any other or indeterminate host, exactly as spelled here.
