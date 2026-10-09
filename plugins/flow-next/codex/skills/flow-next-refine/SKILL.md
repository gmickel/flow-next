---
name: flow-next-refine
description: Refine a spec or task before building: one Q&A interview, optionally focused by a scope lens, or a read-only research pass over external docs. Use to refine requirements or read up on a new library.
user-invocable: false
---

# Flow refine

Refine a spec, task, or spec file: settle the decisions that would change what gets built and that only the person can make, then write the answers back. Everything else you resolve by investigation, record, or leave to implementation. `--scope=research` is a separate pass that asks nothing and writes the spec's external-library unknowns back from official docs.

All task state is read and written through `flowctl`; `.flow/` is the only tracker (no markdown TODOs, plan files or TodoWrite).

Refine clarifies a spec that can already be specified. Route back to `/flow-next:chart` only when the answers show the effort itself is not yet specifiable; unsure of the hop, use `$flow-next-flow --explain`.

Read [working-rules.md](../../references/working-rules.md) first unless you already have this run; it holds for every step of this skill.

## Preamble

**flowctl is bundled, not installed globally** (`which flowctl` fails). Define once; later blocks use `$FLOWCTL`:

```bash
FLOWCTL="${CODEX_HOME:-$HOME/.codex}/scripts/flowctl"
[ -x "$FLOWCTL" ] || FLOWCTL="<plugin-root>/scripts/flowctl"   # <plugin-root> = the directory two levels above this skill's SKILL.md file (the harness gave you that file's absolute path when the skill loaded); substitute it literally
[ -x "$FLOWCTL" ] || FLOWCTL=".flow/bin/flowctl"
```

## Input

Full request: $ARGUMENTS

A Flow spec id, a Flow task id, a tracker handle linked to one, or a file path. Examples:

- `/flow-next:refine fn-1-add-oauth` (legacy `fn-1`, `fn-1-xxx` and task ids like `fn-1-add-oauth.3` work too)
- `/flow-next:refine docs/oauth-spec.md`
- `/flow-next:refine fn-1-add-oauth --scope=qa` (the same interview, focused on what QA decides)
- `/flow-next:refine fn-1-add-oauth --scope=research` (external-docs pass; no interview, one write-back approval)

Empty: ask "What should I refine? Give me a Flow ID (e.g. fn-1-add-oauth) or a file path (e.g. docs/spec.md)."

## Setup

**Scope lens.** `--scope=<value>` is an optional free-text lens: `business`, `technical`, `qa`, `security`, or any other audience; `--biz` means `--scope=business` and `--tech` means `--scope=technical`. Take these tokens out of the arguments before detecting the input; several values combine into one lens. There is one interview whatever the lens: interpret the lens from its words and let it focus which open decisions you look for (a QA lens looks for what counts as done, which failures matter, what must be testable). No lens means no filter. Never ask which scope to run. Under a non-technical lens, speak to the person in their words throughout, not only in questions: round openers, the read-back and the completion summary say what was recorded and what is left for engineering, and gloss or leave out source tags, criterion ids, section names and command names.

**Research pass.** With `--scope=research`, skip the doc-aware gate and the interview: detect the input, then read [references/research-scope.md](references/research-scope.md) and follow it. The interview never reads that file.

**Doc flags.** When the arguments carry any of `--docs`, `--no-docs`, `--strategy`, `--no-strategy`, read [references/doc-flags.md](references/doc-flags.md) § Flag parsing before detecting the input; it strips them and sets the two force values used below.

**Doc-aware gate.** Doc-aware mode adds glossary, decision-record and strategy behaviours to the interview. It turns on when the repo has a glossary term, a decision entry, or a filled strategy section (counts, not file presence); the doc flags override. Run once per interview:

```bash
REFINE_PREFLIGHT="${TMPDIR:-/tmp}/flow-refine-preflight-<suffix>.json"   # literal path; reused after the write-back
# One preflight bundle per interview. A failed, missing or empty probe counts as signal (fail open).
"$FLOWCTL" preflight --json > "$REFINE_PREFLIGHT" 2>/dev/null || printf '{}' > "$REFINE_PREFLIGHT"
# DOC_AWARE_FORCE / STRATEGY_AWARE_FORCE keep the "on" / "off" that doc-flags.md § Flag parsing set; unset = autodetect.
GATES="$(jq -er '
  def v(p): if p.status == "ok" then p.value else null end;
  [ (if v(.probes.glossary) == null or v(.probes.decisions) == null
        or (v(.probes.glossary).total_terms // 0) > 0 or (v(.probes.decisions).entry_count // 0) > 0 then 1 else 0 end),
    (if v(.probes.strategy) == null or (v(.probes.strategy).sections_filled // 0) >= 1 then 1 else 0 end)
  ] | join(" ")' "$REFINE_PREFLIGHT" 2>/dev/null)" || GATES="1 1"
DOC_AWARE="${GATES% *}"; STRATEGY_AWARE="${GATES#* }"
case "${DOC_AWARE_FORCE:-}" in on) DOC_AWARE=1 ;; off) DOC_AWARE=0 ;; esac
case "${STRATEGY_AWARE_FORCE:-}" in on) STRATEGY_AWARE=1 ;; off) STRATEGY_AWARE=0 ;; esac
if [ "$DOC_AWARE$STRATEGY_AWARE" != "00" ]; then
  echo "DOC-AWARE GATE ACTIVE (DOC_AWARE=$DOC_AWARE STRATEGY_AWARE=$STRATEGY_AWARE) — STOP. Read references/doc-aware.md before drafting the first question."
fi
```

When the sentinel prints, read [references/doc-aware.md](references/doc-aware.md) and apply the behaviours its gates enable. Otherwise do not read it.

## Detect the input

Route every single-token argument that is not an `.md` path through `$FLOWCTL show <arg> --json` before calling it a file: flowctl resolves spec ids, task ids, and tracker keys linked to them (`wor-17` / `wor-17.3`). Use the canonical id from the JSON.

- **Spec** (`fn-12`, `fn-1-add-oauth`, or a handle that resolves to one): read it with `$FLOWCTL cat <id>`.
- **Task** (`fn-1-add-oauth.3`, or a handle with a `.`): `$FLOWCTL cat <id>`, plus the parent spec with `$FLOWCTL cat <spec-id>`.
- **File path** (does not resolve): read the file; if it does not exist, ask for a valid path.

Keep the text you read: the write-back compares against it.

## Interview

### Ask through the question tool

Every question goes through `plain-text numbered prompt` (load it with `ToolSearch` `select:plain-text numbered prompt` when its schema is not loaded); fall back to numbered plain-text options only when the tool is unreachable. Never print questions as narration ("Question 1: ... Options: a) b) c)").

### The one test

Ask a question only when all three hold: a wrong guess would build the wrong thing or ship behaviour the person would reject; the code, the docs, a quick experiment, or implementation cannot settle it; and it is the answerer's call. A topic on the list below is not a reason to ask.

Check the spec for these, and ask about one only when the spec leaves it unclear and it passes the test: who it is for; what done looks like; what is explicitly out; a constraint the domain implies (a regulation, a contract, a partner commitment); an irreversible data or contract change (a data model, a migration, a public contract); an external interface; a security boundary. A lens adds its audience's open decisions. Under a non-technical lens, leave the technical items on that list (data, migrations, contracts, interfaces, security) to the technical pass and planning, without recording them; ask only a consequence the answerer owns, in their words ("existing customers' exports would change format: acceptable?"). Technical detail, performance, failure modes, concurrency, scale and edge cases qualify only when they pass the test; implementation, review and QA surface the rest. Cosmetic polish (message wording, flag spelling, formatting) never gets its own question: fold it into a related question's options or state it as a default the person can veto at write-back. Refine never asks for success metrics or latency budgets unless the spec is about them.

Stop when no question that passes the test remains. Asking nothing is a good outcome: report "Nothing worth asking; the spec is clear enough to build." and skip the write-back unless investigation resolved something worth recording.

### Investigate before asking

Before the first round, read `STRATEGY.md` and search the other project docs for what the spec touches rather than reading them end to end: `README.md`, `CHANGELOG.md`, `GLOSSARY.md`, the decisions track (`$FLOWCTL memory list --track knowledge --category decisions --json`), the titles of open specs (`$FLOWCTL specs --json`), and `docs/` when present. Then sort each candidate question:

- **The code answers it** (what exists, how it is wired, which conventions hold): read and search; log it under `## Resolved via Codebase` with `file:line` evidence.
- **The project docs answer it** (what the strategy says, what shipped, what was decided): log it under `## Resolved via Project Docs` with `path:line` evidence.
- **Running something settles it** (behaviour, timing, layout, output, whether an eval separates two options): run a throwaway experiment in `.flow/tmp/experiments/` and log the question, what ran, what you observed and the decision under `## Resolved via Experiment`. The working rules' limit on experiments decides which run without asking. An inconclusive result (noise larger than the difference) is logged as inconclusive and goes to the person with the data. The experiment is evidence, never product code.
- **It is a judgment** (what should exist, which trade-off, what priority): ask it.

Answering a "should" question by grep is the bug; so is asking something the docs already answer. Use multi-select for options that are not exclusive, and probe answers that contradict each other.

While the person answers a round you may dispatch one read-only fact scout for lookups that gate the next round; before dispatching one, read [references/fact-scouts.md](references/fact-scouts.md). Investigating inline needs nothing from it.

### Rounds over the decision tree

Treat the open decisions as a tree: each decision opens the ones that hang off it. The frontier is every question whose prerequisites are settled. Work in rounds:

1. Each round asks the whole current frontier. A question whose answer depends on another question still open belongs to a later round; never ask a question alongside its own prerequisite.
2. Split the round across `plain-text numbered prompt` calls of up to 4 questions, closest-related together, announced as one round ("Round 2, part 1/2"). Never pad a call to 4 and never hold a frontier question back to smooth pacing.
3. Recompute the frontier from the answers; deeper rounds are discovered, not pre-scripted.
4. When an answer prunes a branch, say so at the next round's opener ("Skipping persistence questions; you said no database.").
5. Go at most 4 rounds down any one branch.
6. If part of a round was never asked (tool error, interruption), ask it before moving on.

Standalone checkpoints (the code-mismatch question, the skipped-items checkpoint, the mark-ready offer, doc-aware prompts that have their own per-round budget in doc-aware.md) sit outside rounds, are never labelled "Round N" and never count against round depth. A doc-aware prompt deferred by that budget is pending for a later round, not dropped.

The interview is done when every decision the tree opened is answered, delegated, parked under `## Open Questions`, or pruned with its branch named.

### Question shape

Write each question so the person can read it once and answer it confidently.

- **Body:** one sentence of stakes (what this decides, in the audience's words), then the recommendation with a one-sentence rationale, then one confidence tier: `<stakes>. Recommended: <X> — <why>. Confidence: [high | judgment-call | your-call].`
- **Options:** neutral labels, no "(recommended)" marker. Each description says what choosing it means ("Choose this if…", "This means…").
- **Plain words.** Prefer the common word; a term of art you genuinely need gets a short gloss at first use ("counter-metrics — things we'd hate to make worse"). No unexplained acronyms or repo shorthand. A product question, or any question under a non-technical lens, carries no implementation vocabulary (schemas, endpoints, config keys). A cited criterion gets a short gist: "R3 (the audit line's required fields)", never a bare "R3".
- **Length:** never drop the stakes, recommendation, tier, gloss or option consequences. Trim repetition, background and hedging first; a body of about 40-60 words is usually right.

Tiers: `[high]` when the code or a convention gives strong signal and the person can usually accept; `[judgment-call]` when you lean one way but reasonable people disagree; `[your-call]` when you have no basis. Use `[your-call]` whenever that is true and say so ("I found no convention to copy; this depends on what your callers expect"). Always recommending trains people to defer.

Example: "This decides how long the rate limiter remembers a result before checking again. Recommended: 60 seconds — short enough that stale answers stay rare, long enough to be worth caching. Confidence: [judgment-call]." Options `30s`, `60s`, `300s`, `no cache`, each with its plain consequence.

### Skipped questions are not answers

A recommendation never implies consent. Four answer shapes:

- **An answer** (an option or typed text): use it.
- **Delegation** ("you decide", "go with your recommendation"): adopt the recommendation and note it as delegated by the person.
- **Someone else's call** ("not my call", "engineering decides"): park it under `## Open Questions` as `**<question>** — for <owner> to decide; leaning <X>. *(owner: engineering | product)*`. It is not a skip.
- **A skip** (dismissed, "skip", "I don't know"): the question stays open. Its recommendation never enters a spec section as decided content.

Park each skip under `## Open Questions` as `**<question>** — skipped during refine; leaning <X>, unconfirmed. *(owner: engineering | product)*`. A skipped judgment question stays a judgment question; never backfill it by grep. Keep a skip count.

With one or more skips: read [references/skipped-items.md](references/skipped-items.md) and ask its checkpoint before the write-back.

### Out of scope

Refine settles requirements; plan and work own the rest. No task creation, sizing, dependency ordering, phased implementation or file references. No time estimates, deadlines, durations or "ship before X" framing; when the person volunteers a deadline, acknowledge it without re-asking scope because of it.

## Where answers go

Write each answer into the section it belongs in, whatever the lens: a target user in `## Goal & Context`, an out-of-scope call in `## Boundaries`, a contract in `## API Contracts`, a testable commitment in `## Acceptance Criteria`, a rationale in `## Decision Context`. The sections come from the resolved template ([templates/spec.md](../../templates/spec.md), or the repo's own `SPEC.md`); a section the project added is a section like any other.

- **Everything else comes back byte-for-byte**, and the read-back names every section this session changed. Keep the layout the spec has: when `## Decision Context` carries `### Motivation` / `### Implementation Tradeoffs`, put a rationale under the one it fits and never add or remove sub-headings.
- **Auxiliary sections** (`Strategy Alignment`, `Strategy Conflicts`, `Glossary Conflicts`, `Conversation Evidence`, `Resolved via Codebase`, `Resolved via Project Docs`, `Resolved via Experiment`, `Resolved via Research`, `Parked unknowns`) come back byte-for-byte. Refine only appends its own entries to the three `Resolved via` sections it owns (Codebase, Project Docs, Experiment). `Resolved via Research` belongs to the research pass. The one thing refine may take out is a `Parked unknowns` bullet this session resolved; write-back.md says how.
- **Precision.** Record an answer at the precision given: a preference ("performance matters here") goes to `## Decision Context` as guidance; a number becomes a criterion only when the person stated it. Your recommended options never become thresholds.
- **Acceptance criteria** are append-only: never renumber or replace an R-ID; take the next unused number. Leave criteria an earlier session wrote exactly as they are. For the criteria you add, the person's own words stay untagged and anything else carries a tag (write-back.md § Source tags).

When the person declines a feature as product judgment (we could build it and choose not to), read [declined-scope.md](../../references/declined-scope.md) and record it.

Before the write-back on a spec (a task or a plain file never splits), when the refined criteria reach 8 or more or visibly serve more than one independently shippable outcome, read [references/split.md](references/split.md).

## Write-back

At completion, read [references/write-back.md](references/write-back.md) and run the branch for the input type (spec, task, or file). It holds the write pattern, the read-back approval, the source tags, and the flowctl call per branch.

## After the write-back

Refine never changes readiness: a spec that was ready stays ready unless the person unmarks it (only `capture --rewrite` resets it).

For a spec or task input (not a file path), probe the two optional offers:

```bash
REFINE_PREFLIGHT="${TMPDIR:-/tmp}/flow-refine-preflight-<suffix>.json"   # the same literal path as Setup
# Tracker sync: bridge active and tracker.perEvent.interview set to anything but off. Fails open.
TRACKER="$(jq -er '
  def v(p): if p.status == "ok" then p.value else null end;
  if .probes.config.status != "ok" or v(.probes.tracker) == null
     or (v(.probes.tracker).active == true and ((.value.tracker.perEvent.interview // "off") != "off"))
  then "open" else "closed" end' "$REFINE_PREFLIGHT" 2>/dev/null)" || TRACKER=open
[ "$TRACKER" = open ] && echo "TRACKER-SYNC GATE ACTIVE — STOP. Read references/post-write-back.md#tracker-sync before continuing."
# Mark-ready: readiness adopted (a spec is already ready) and tracker.readyState unset. Fails open.
SPECS_RAW="$("$FLOWCTL" specs --json 2>/dev/null)" && READY_ADOPTED="$(printf '%s' "$SPECS_RAW" | jq '[.specs[] | select(.ready == true)] | length' 2>/dev/null)" || READY_ADOPTED=""
READY_STATE="$(jq -er 'if .probes.config.status == "ok" then (.value.tracker.readyState // "") else error("config probe") end' "$REFINE_PREFLIGHT" 2>/dev/null)" || READY_STATE="?"
if [ -z "$READY_ADOPTED" ] || [ "$READY_STATE" = "?" ] || { [ "$READY_ADOPTED" -ge 1 ] && [ -z "$READY_STATE" ]; }; then
  echo "MARK-READY GATE ACTIVE — STOP. Read references/post-write-back.md#mark-ready-offer before continuing."
fi
```

When a sentinel prints, read the named section of [references/post-write-back.md](references/post-write-back.md) before continuing. With no tracker and readiness not adopted, neither fires.

## Completion

Print a summary:

- **Questions asked.** At zero: "Nothing worth asking; the spec is clear enough to build."
- **Skipped** (only with skips): the count and the checkpoint's outcome (parked, filled as assumed, or re-asked).
- **Key decisions** captured.
- **Written:** the id updated or the file rewritten.
- **Sections changed:** every section this session wrote, and that the rest came back byte-for-byte; the lens, when one was given; each `Resolved via Project Docs` / `Resolved via Experiment` entry in one line with its decision. For `--scope=research`: the items written under `## Resolved via Research` with their sources, or the printed skip reason.
- **Tracker sync** (only when the gate fired): whether the spec was pushed, pulled, reconciled or commented.
- **Readiness** (only when the mark-ready offer fired): marked ready or kept draft.
- **Doc-aware** (only when active): glossary terms added (`flowctl glossary add`), decision entries written (`flowctl memory add --track knowledge --category decisions`), and entries under `## Glossary Conflicts` / `## Strategy Conflicts` (refine never edits `STRATEGY.md`).

The question count and the sections-changed line always appear.

Next step by input:

- Spec without tasks → print the `Recommended next:` line from [plan-vs-no-plan.md](../flow-next-flow/references/plan-vs-no-plan.md) (direct by default; plan only on its positive signals); use `$flow-next-plan-review fn-N` for an independent design review.
- Spec with tasks → `$flow-next-plan-review fn-N` when this session changed the spec body (its tasks predate the change), otherwise `$flow-next-work fn-N` (or more refine on specific tasks).
- Task → `$flow-next-work fn-N.M`.
- File → `$flow-next-capture` to turn the refined document into a spec.
- Any of these → offer a compact digest of the result: `$flow-next-visual fn-N` for a spec input, `$flow-next-visual fn-N.M` for a task input, `$flow-next-visual <file-path>` for the file input (an option, never run for them).

Print each command in the spelling this host invokes: the flat `/flow-next-<name>` form when the plugin root carries `.flow-next-opencode-manifest` (an OpenCode install), otherwise exactly as written here.
