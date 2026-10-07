# Flow plan steps

Steps 1-3 run on every input type, including an existing spec that looks like it only needs a refine.

## Task sizing

Every task fits one `/flow-next:work` iteration. Size by what you can observe, not by token estimates:

| Size | Files | Criteria | Pattern | Action |
|------|-------|----------|---------|--------|
| S | 1-2 | 1-3 | follows an existing one | combine with related work |
| M | 3-5 | 3-5 | adapts an existing one | the target |
| L | 5+ | 5+ | new subsystem or architecture | split into M tasks |

- Combine sequential S tasks that touch related code. Seven or more tasks is a ceiling, not a floor: combine trivial sequential S tasks even below it. Finalization (docs, changelog, release notes, CI wiring) is one task, never one per artifact.
- Each task ends in a state its acceptance can check. The task that proves the approach (the early proof point, Step 5) usually comes first in dependency order, so later tasks build on checked ground.
- Keep cohesive work intact. Among equally good splits, prefer disjoint file ownership, and add a dependency only for real ordering. Disjoint files are evidence of independence, not proof: generated outputs, lockfiles, migrations, fixtures and shared services still couple tasks, and that coupling is a dependency. Never split cohesive work to manufacture parallelism.

## Step 0: Initialize

The SKILL.md preflight already ran `init` and wrote the config snapshot at `${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json`. Reuse that literal path; do not repeat `init`, `preflight` or `config get`.

## Step 1: Resolve input and research

**Handle recognition.** Before treating a single-token argument as a new idea, run `$FLOWCTL show <arg> --json`. A tracker key (`wor-17`, `wor-17.2`) resolves to its linked spec or task. If it resolves, use the canonical id and take Route A in Step 5; only a token that does not resolve is a new idea (Route B).

**Existing id** (the input resolved): read [references/existing-id.md](references/existing-id.md) and run its
fetch-and-readiness block once, before research; then apply the Planning choice below.

**Planning choice.** Read the spec's metadata (for a task id, `$FLOWCTL show <spec-id> --json` on its parent). If `no_plan: true` and the spec has exactly one task, marked `implicit_owner: true`, stop with `NEEDS_HUMAN: needs-owner-reconciliation`, naming the owner and the decision needed about its whole-spec scope and existing work; never convert, delete or duplicate the owner, and never prompt under autonomy. Otherwise, for `no_plan: true`, run `$FLOWCTL spec clear-no-plan <spec-id> --json` before creating or changing tasks, and stop if it fails.

**Config and strategy**, from the snapshot:

```bash
jq '{memory_enabled: .value.memory.enabled, scouts_github: .value.scouts.github}' "${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json"
STRATEGY_STATUS_JSON=$(jq -c '.probes.strategy.value // {"exists":false,"sections_filled":0}' "${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json" 2>/dev/null || echo '{"exists":false,"sections_filled":0}')
STRATEGY_FILLED=$(jq -r '.sections_filled // 0' <<< "$STRATEGY_STATUS_JSON" 2>/dev/null || echo 0)
if [[ "$STRATEGY_FILLED" -ge 1 ]]; then
  STRATEGY_JSON=$($FLOWCTL strategy read --json 2>/dev/null || echo '{}')   # name, target_problem, approach, tracks, last_updated: pass verbatim to scouts and plan
  STRATEGY_PRESENT=true
  echo "STRATEGY GATE ACTIVE — STOP. Read references/strategy-alignment.md before continuing."
else
  STRATEGY_PRESENT=false
fi
```

When the strategy sentinel prints, read [`references/strategy-alignment.md`](references/strategy-alignment.md); it owns the two strategy sections Step 5 writes. An absent or empty STRATEGY.md means no strategy sections at all.

**Memory.** When memory is enabled, run the one search in [the direct memory path](references/judge-memory.md), with or without a judge key.

**Declined scope.** List `.flow/memory/declined/` once (one `<concept-slug>.md` per concept) and read any file whose concept the request touches. On a hit, cite it in `## Decision Context`, append this request as a dated line under its `## Prior requests`, and keep that scope out of the plan. Only the user reopens a declined concept: say it was declined, what would change, and wait. No directory means nothing was declined.

**Scouts.** Launch the set for this depth and config in one parallel dispatch:

| Scout | Runs |
|-------|------|
| `flow-next:repo-scout` | always; at SHORT it also carries docs-gap-scout's charter |
| `flow-next:spec-scout` | always |
| `flow-next:docs-gap-scout` | STANDARD and DEEP |
| `flow-next:practice-scout`, `flow-next:docs-scout` | STANDARD and DEEP |
| `flow-next:github-scout` | STANDARD and DEEP, when `scouts.github` |
| `flow-next:flow-gap-analyst` | always (Step 3) |

The set follows depth and config, never your sense of what seems relevant; dropping a scout inside the tier has broken this. SHORT skipping the web scouts is a deliberate trade: the implementer can fetch docs during work.

On a Route A spec, first apply the skip rule in [`flow-next-refine/references/research-scope.md`](../flow-next-refine/references/research-scope.md) to the research scouts it names and record the outcome with its reason; `repo-scout`, `spec-scout` and the gap analyst always run.

When github-scout runs, it alone searches GitHub code; repo-scout stays local and the docs and practice scouts use primary documentation. On a host that does not block on dispatch, start Step 3's gap analyst as soon as the repo-grounded scouts return, reconcile the web findings when they land, and join every scout before Step 5. Blocking hosts run Steps 1, 2, 3 in order.

**Scout model tiers.** Every scout above, and the gap analyst, is a **thinking scout** dispatch. Routing precedence, highest first: an explicit argument in the invocation, the project routing block in the instruction file, the agent definition's default, then the session model. Where a harness cannot honor the agent default, a thinking scout runs on the session model, never a fast one.

Collect: file paths with line refs, code to reuse, similar prior work, project conventions, architecture and data flow, external doc links, spec dependencies in both directions, docs that must change (these go into task acceptance), and DESIGN.md tokens if repo-scout found one.

## Step 2: Scope

- Name who the change affects (users, developers, operators); that sets how much detail the plan needs.
- If you cannot state the open question precisely, that is a chart signal: recommend `/flow-next:chart` and stop. A sharp question that only the human can answer and that would change what gets built belongs to refine, per the when-to-refine rule in [`plan-vs-no-plan.md`](../flow-next-flow/references/plan-vs-no-plan.md).
- Settle a fork the plan hinges on with a throwaway probe when it can be observed, and read the answer back; never park it as an open question or put it to the user. The working rules' limit on experiments decides which probes run.
- Every task traces to an R-ID and every R-ID to the request. A capability nobody asked for is one out-of-scope line in `## Boundaries`. Prefer removing a risk structurally (a closed schema, an inert format, a capability not exposed) over machinery that manages it; a rejected bigger design gets one line in `## Decision Context`. Trimming scope never trims rigor: each R-ID's error cases, Boundaries, coverage, and the containment, permission and concurrency guards a feature needs all stay.
- When a rejection is product judgment (we could build this and choose not to), read [declined-scope.md](../../references/declined-scope.md) and record it.

## Step 3: Gap analysis

Dispatch `flow-next:flow-gap-analyst` with the request and the research findings (Task flow-next:flow-gap-analyst), unless it already started on the non-blocking path in Step 1; then join that dispatch. It is a thinking scout under Step 1's routing. Fold each gap into the plan or list it as an open question.

## Step 4: Sections for the depth

Depth decides which template sections Step 5 fills; a section with nothing to say stays absent.

- **SHORT:** Goal & Context, Acceptance Criteria, Boundaries, plus any other section only where there is content for it.
- **STANDARD:** SHORT plus Architecture & Data Models, Edge Cases & Constraints, Decision Context, and API Contracts when an interface changes.
- **DEEP:** every template section, adding phases, alternatives considered, non-functional targets, an architecture/data-flow diagram, rollout and rollback, docs and metrics, and risks with mitigations in the sections that own them.

At every depth, new tables or schema changes, new services or significant architecture changes, and complex data flow between components get a mermaid diagram of 5-10 nodes in Architecture & Data Models.

## Step 5: Write to .flow

Spec and task prose follows [docs/prose.md](../../docs/prose.md) when present. At STANDARD or DEEP depth, or when unsure how to shape a spec or task, read [`references/examples.md`](references/examples.md) first.

**Author as files.** Compose each document with the Write tool at a literal path you resolve yourself (for example `/tmp/flow-plan-body-ab12.md`; file tools do not expand `${TMPDIR}`), use the same literal in the Bash call, and revise with Edit, re-running only the affected flowctl call. Never compose a document in a heredoc or stdin pipe; those suit only short payloads. Route B creates the spec with its plan in one `spec create --plan-file` call and every task in one `task create --from-json` call. `spec set-plan`, a single `task create` and `task set-spec` are for editing what already exists.

**Ratify before the first `.flow/` write (interactive only):**

```bash
ACTIVE=0
[ "${AUTONOMOUS:-0}" = "1" ] || [ -n "${FLOW_AUTONOMOUS:-}" ] || ACTIVE=1
if [ "$ACTIVE" = "1" ]; then
  echo "READ-BACK ACTIVE — STOP. Read docs/read-back.md before the first .flow/ write."
fi
```

When it prints, read [docs/read-back.md](../../docs/read-back.md) and follow it before the `spec create` call (Route B) or the `task create --from-json` call (Route A). The draft is both files; waves come from the JSON `deps`; `Recommended next:` is judged from [`plan-vs-no-plan.md`](../flow-next-flow/references/plan-vs-no-plan.md), so a task set with no positive plan signal is named as `work --no-plan` material before anything is written. Under autonomy the creation calls run directly.

**Route A (existing id):** read [`references/route-a-refine.md`](references/route-a-refine.md), follow it, then apply the spec and task rules below.

**Route B (new idea):**

1. Seed the plan from the resolved template: run `$FLOWCTL spec skeleton` once and Write its output to the plan file. The template owns section names, order and guidance; never restate its section list. Replace its `# <spec-id> <Title>` heading with `# <Title>`, fill the Step 4 sections, and replace guidance prose and comments with content.

2. Create the spec. The allocator gate reads the snapshot; an explicit override in the invocation wins:

   ```bash
   PLAN_FILE="/tmp/flow-plan-body-<suffix>.md"   # the exact literal the Write call used
   ACTIVE=0
   # No pipelines in the probe: capture raw first, rc-checked; parse separately.
   SPEC_IDS="$(jq -r '.value.tracker.specIds // "flow"' "${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json" 2>/dev/null)" || ACTIVE=1   # probe error => ACTIVE
   if [ "$ACTIVE" = "0" ]; then
     BRIDGE_RAW="$(jq -ce 'if .probes.tracker.status == "ok" then .probes.tracker.value else error("tracker probe") end' "${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json" 2>/dev/null)" || ACTIVE=1
   fi
   if [ "$ACTIVE" = "0" ]; then
     BRIDGE_ACTIVE="$(printf '%s' "$BRIDGE_RAW" | jq -r '.active // false' 2>/dev/null)" || ACTIVE=1
     [ "$SPEC_IDS" = "tracker" ] && [ "$BRIDGE_ACTIVE" = "true" ] && ACTIVE=1
   fi
   if [ "$ACTIVE" = "1" ]; then
     echo "TRACKER-FIRST GATE ACTIVE — STOP. Read references/tracker-first-mint.md before continuing."
   fi
   # The tracker-first arm runs HERE, only per that reference; it sets SPEC_OUTPUT / IDENTIFIER.

   # The only flow-first creation site, deliberately unconditional. It degrades silently
   # only when nothing was created remotely; if create-first recorded an issue and the
   # mint failed, surface identifier + url + retryKey and STOP instead.
   if [ -z "$SPEC_OUTPUT" ] && [ -z "$IDENTIFIER" ]; then
     SPEC_OUTPUT=$($FLOWCTL spec create --title "<Short title>" --plan-file "$PLAN_FILE" --json)
   fi
   ```

   When the sentinel prints, read [`references/tracker-first-mint.md`](references/tracker-first-mint.md) before continuing. The result is the spec id (`wor-17-slug` tracker-first, `fn-1-add-oauth` flow-first). The branch defaults to the spec id; only for a branch the user named, add `--branch "<custom-branch>"` to `spec create`. Delete the plan file once the spec and any review loop are final.

**Spec content (both routes):**

- Plan adds these sections to the template:
  - `## Quick commands` (required): at least one smoke-test command in a bash fence, focused on the code the tasks change.
  - `## Strategy Alignment` and `## Strategy drift flagged for review`: only when `STRATEGY_PRESENT=true`, per the strategy reference.
  - `## Resolved via Research`: only when docs-scout or practice-scout ran, in the shape `flow-next-refine/references/research-scope.md` defines, with `plan` as the provenance and one sub-block per research scout that ran. When Step 1 skipped them because the section was present, keep it byte for byte. Their findings also go into the task bodies.
  - `## Early proof point`, after Acceptance Criteria: `Task <spec-id>.1 validates the core approach (<what it proves>). If it fails, re-evaluate <strategy> before continuing with <spec-id>.2+.` Name the task that proves the approach, usually the first in dependency order.
  - `## Requirement coverage`, last, rendered after task creation (Step 6).
- **R-IDs:** acceptance criteria use `- **R1:** <testable criterion>. Errors: <enumerated error, invalid-input and boundary cases, or "no error surface beyond X">`. Number in creation order; once any review has run, never renumber, and a new criterion takes the next unused number (gaps are fine). When `.flow/criteria.md` exists, reference its G-IDs rather than restating them, and write an R only for what this spec adds.
- **Durability:** the spec states contracts (types, signatures, behaviors, invariants), never file paths or line numbers, except a snippet whose exact location is the decision. Paths and `file:line` refs belong in the tasks.
- **Parked unknowns:** when the spec has `## Parked unknowns`, resolve each bullet by moving its answer into the owning section, turn it into a task, or leave it verbatim if still unknown. Delete resolved bullets, and the heading when empty.

**Spec dependencies**, from spec-scout, in both directions:

```bash
$FLOWCTL spec add-dep <new-spec-id> <dependency-spec-id> --json   # forward: this plan needs an existing spec
$FLOWCTL spec add-dep <other-spec-id> <new-spec-id> --json        # reverse: an existing spec needs this plan
```

A dropped reverse edge leaves the other spec falsely ready, and `flow --auto` would build it against work that has not shipped. List the edges set, marked `[forward]` or `[reverse]`, in the final summary.

**Tasks.** Write the whole set as one JSON array, then create it in one call (all or nothing):

```
Write tool -> /tmp/flow-plan-tasks-<suffix>.json
[
  {"title": "<Task 1 title>", "description": "<## Description ...>", "acceptance": "<- [ ] ...>", "satisfies": ["R1", "R3"]},
  {"title": "<Task 2 title>", "deps": [1], "description": "...", "acceptance": "...", "satisfies": ["R2"]}
]
```
```bash
$FLOWCTL task create --spec <spec-id> --from-json "/tmp/flow-plan-tasks-<suffix>.json" --json
```

Per object: `title` is required; `description` and `acceptance` are markdown (or `description_file` / `acceptance_file`, relative to the JSON file); `satisfies` lists bare R-IDs; `deps` lists task ids or 1-based indexes of earlier entries; `priority` and a single-line `touches` are optional. An invalid entry rejects the whole batch and names every invalid item; `--json` returns the ids in input order. To fix a missed dependency later: `$FLOWCTL dep add <dependent-task> <dependency-task> --json`.

**Task content.** Executors always receive the task together with the full parent spec, so a task never restates the spec's framing, rationale or acceptance criteria; it references R-IDs and spec sections. The task's job is the implementation plan:

```markdown
## Description
[What this task builds and why it is split this way, 10 lines at most.]

**Size:** S/M
**Files:** `src/auth/google.ts`, `src/routes/auth.ts`
**Touches:** [src/auth/**, src/routes/auth.ts]

## Approach
- Follow the pattern at `src/auth/local.ts:10-35`
- Reuse `validateEnv()` from `src/config/env.ts`

## Investigation targets
**Required** (read before coding):
- `src/routes/auth.ts:50-80` — route registration to extend

**Optional** (reference as needed):
- `src/auth/local.test.ts` — test patterns

## Key context
[Only a recent API change, a surprising pattern, or a non-obvious gotcha.]

## Acceptance
- [ ] Task-scoped, testable criterion
```

- **Touches** goes on every task, as a body line beside `**Files:**` (the batch call renders frontmatter from `satisfies` only): the repo-relative paths or globs the task will modify. When unsure, declare wider rather than omit it: work runs tasks concurrently only when their declared Touches are disjoint, a missing line always runs serially, and a too-wide one costs at most a serial run. Omit it only when a task truly cannot name a path it will modify.
- **satisfies** lists the R-IDs a task obviously advances. Infrastructure, refactoring, plumbing or docs-only tasks may have none.
- **Investigation targets:** at most 5-7, exact paths from repo-scout with optional line ranges, checked to exist at plan time, split into Required and Optional.
- **Design context:** when DESIGN.md exists and a task changes UI (components, pages, styles, layout, theme), add `## Design context` with the DESIGN.md tokens, components and do's and don'ts it needs, and a pointer to `DESIGN.md`. Skip backend-only tasks; when in doubt, include it.
- **Refactors:** a task that restructures without changing behavior names its equivalence harness in the body: a script diffing old and new outputs, or a recorded baseline replayed against the new code. "Existing tests pass" is not a pin when those tests never covered the moved behavior.

After writing, do not re-fetch the spec with `show` or `cat`; you authored this state and Step 6 validates it. The Step 7 fix-loop re-anchor is the only exception.

## Step 6: Validate

```bash
$FLOWCTL validate --spec <spec-id> --coverage --json
```

Fix validation errors. Every requirement maps to at least one task or carries a gap justification. Replace the spec's `## Requirement coverage` table with the returned `requirement_coverage` markdown (derived from the tasks' `satisfies`); keep any gap justification you wrote for an uncovered row, since the renderer labels it `Uncovered` until you supply one.

Derive execution waves from the task DAG: wave 1 holds tasks without dependencies, and each later wave holds tasks whose dependencies are all in earlier waves. Tasks in one wave are parallel candidates, not a promise; `/flow-next:work` still judges shared resources and capacity. If review or Step 8 changes tasks or dependencies, re-run this step.

## Step 6.5: Tracker sync (opt-in)

```bash
LEAF="$(jq -r '.value.tracker.perEvent.plan' "${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json" 2>/dev/null)"
case "$LEAF" in
  pull)      OP="pull" ;;
  push)      OP="push" ;;
  reconcile) OP="reconcile" ;;
  comment)   OP="comment" ;;
  off|null)  OP="off" ;;
  *)         OP="off" ;; # malformed config stays silent
esac
if [ "$(jq -r '.probes.tracker.value.active // false' "${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json")" = "true" ] \
   && [ "$OP" != "off" ]; then
  echo "TRACKER ACTIVE (op=$OP): read and follow references/tracker-projection.md"
  # Load and follow references/tracker-projection.md with <OP> and <spec-id>.
  # Its inline wrapper makes one lifecycle facade call, chosen as that file says
  # (a reconcile classified flow-only with no genuine comments becomes a push
  # with no body inputs):
  #   "$FLOWCTL" tracker sync "$SPEC_ID" --op "$OP" --event plan <legal file flags>
fi
```

Off, unset, inactive or malformed: skip [`references/tracker-projection.md`](references/tracker-projection.md) and continue. Tasks never become tracker issues.

## Step 7: Review

When review mode is `none`, skip this step. Otherwise read and follow [`references/selected-review.md`](references/selected-review.md).

## Step 8: Summary and next steps

Print the summary on every run:

```
Spec <spec-id> created: "<title>"
Tasks: M total | Sizes: Ns S, Nm M
Execution waves:
- Wave 1 (parallel candidates): <spec-id>.1, <spec-id>.2
- Wave 2: <spec-id>.3
Spec dependencies set:
- <spec-id> → fn-2-add-auth (Auth): uses authService   [forward]
```

Under it, offer `/flow-next:visual <spec-id>` in one line as a compact visual digest of the plan; the user picks it, never run it for them.

```bash
ACTIVE=0
[ "${AUTONOMOUS:-0}" = "1" ] || [ -n "${FLOW_AUTONOMOUS:-}" ] || ACTIVE=1
if [ "$ACTIVE" = "1" ]; then
  echo "NEXT-STEPS MENU ACTIVE — STOP. Read references/next-steps-menu.md before continuing."
fi
```

When it prints, read [`references/next-steps-menu.md`](references/next-steps-menu.md); it owns the menu and its recommendation line. Under autonomy there is no menu.
