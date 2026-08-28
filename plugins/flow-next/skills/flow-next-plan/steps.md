# Flow Plan Steps

**Steps 1-3 (research, gap analysis, depth) run on every input type.** A plan that skipped one of them because the input "looked like a refine" has broken this.

**CRITICAL**: If you are about to create:
- a markdown TODO list,
- a task list outside `.flow/`,
- or any plan files outside `.flow/`,

**STOP** and instead:
- create/update tasks in `.flow/` using `flowctl`,
- record details in the spec/task markdown.

## Success criteria

- Plan references existing files/patterns with line refs
- Reuse points are explicit (centralized code called out)
- Acceptance checks are testable
- Tasks are small enough for one `/flow-next:work` iteration (split if not)
- **No implementation code** — specs describe WHAT, not HOW (see SKILL.md Golden Rule)
- Open questions are listed

## Task Sizing Rule

Use **T-shirt sizes** based on observable metrics — not token estimates (models can't reliably estimate tokens).

| Size | Files | Acceptance Criteria | Pattern | Action |
|------|-------|---------------------|---------|--------|
| **S** | 1-2 | 1-3 | Follows existing | Combine with related work |
| **M** | 3-5 | 3-5 | Adapts existing | ✅ **Sweet spot** |
| **L** | 5+ | 5+ | New/novel | ⚠️ Split into M tasks |

**M is the target size** — fits one context window (~80-100k tokens), makes meaningful progress.

**Anchor examples** (calibrate against these):
- **S**: Fix a bug, add config, simple UI tweak → combine if sequential
- **M**: New API endpoint with tests, new component with state → ideal
- **L**: New subsystem, architectural change → split into M tasks

**Combine rule**: Sequential S tasks touching related code → combine into one M task.

**If too large, split it:**
- ❌ Bad: "Implement Google OAuth" (L — new subsystem)
- ✅ Good:
  - "Google OAuth backend (config + passport + routes)" (M)
  - "Add Google sign-in button" (S)

**If too granular (7+ tasks), combine:**
- ❌ Over-split: 4 sequential S tasks for backend setup
- ✅ Better: 1 M task covering the sequential work

**7+ is a ceiling, not a floor — combine trivial sequential S tasks even below it:**
- **Finalization folds into ONE task.** Docs + CHANGELOG + release-notes + CI/test-wiring for a feature are a single S/M task — never a separate task per artifact.
- ❌ Over-split (6 tasks): `…5 "docs + CHANGELOG"` + `…6 "wire tests into CI"` as two S tasks
- ✅ Better: one `"docs + CHANGELOG + CI wiring"` S/M task (CI-wiring is part of a task's Definition of Done, not its own task)

**Expose useful parallelism without harming task quality:**

When splitting tasks, keep cohesive M-sized work intact, then prefer boundaries
with disjoint ownership when the decomposition is otherwise equally good. Avoid
unnecessary dependency edges: dependencies express real ordering, not a
conservative default.

- ❌ Bad: Task A and B both modify `src/auth.ts`
- ✅ Good: Task A modifies `src/auth.ts`, Task B modifies `src/routes.ts`

List expected files in each task's `**Files:**` field. Disjoint file lists are
evidence of a parallel candidate, not proof: generated outputs, lockfiles,
migrations, fixtures, services, and other shared resources can still couple
tasks. If multiple tasks must touch the same file or one consumes another's
output, mark the real dependency explicitly with `flowctl dep add`. Never split
cohesive work merely to manufacture a parallel wave.

## Step 0: Initialize .flow

```bash
# Ensure .flow exists (FLOWCTL defined once in SKILL.md preamble)
$FLOWCTL init --json

# ONE root config snapshot for the whole run (fn-110): {"key":null,"value":{<merged config>}}.
# Every later config lookup (readiness, memory/scout gates, tracker leaf, HTML lens)
# derives from this file via jq — no further `config get` calls on the plan path.
# Path-persistence rule: compose the literal path with an agent-chosen 4-char suffix
# and type it verbatim in every later block that reads it.
PLAN_CFG="${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json"   # literal path
$FLOWCTL config get --json > "$PLAN_CFG" 2>/dev/null || printf '{"key":null,"value":{}}' > "$PLAN_CFG"
```

## Step 1: Fast research (parallel)

**If input is a Flow ID** (fn-N-slug or fn-N-slug.M, including legacy fn-N/fn-N-xxx): First fetch it with `$FLOWCTL cat <id>` plus ONE `show --json`, captured as `SHOW_JSON` — the readiness soft-check below reads the same capture, so run the fetch and the readiness check in the SAME bash block (vars do not survive across tool calls; never run a second `show --json` for readiness):

```bash
$FLOWCTL cat <id>                        # request context (spec body)
SHOW_JSON=$($FLOWCTL show <id> --json)   # ONE fetch — request context AND readiness read
echo "$SHOW_JSON"                        # command substitution hides stdout — bring it into view once
```

**Handle-recognition rule (R16):** do NOT gate the Flow-ID branch on a hard "must start with `fn-`" check. Before treating a single-token arg as a freeform idea, route it through `$FLOWCTL show <arg> --json` - flowctl's widened resolver (fn-52.10) maps a tracker key (`wor-17` / `wor-17.M`) to its linked spec/task. If it resolves (rc 0), use the canonical id from the JSON and take the existing-Flow-ID path (Route A in Step 5); only a non-resolving token becomes a new idea (Route B). So `plan wor-17` refines the linked spec, never creating a duplicate.

**Unshaped oversized freeform (fn-135):** if Route B input is one large idea with unclear boundaries and several consequential unknowns, stop and recommend `/flow-next:chart` (or `/flow-next:guide`) instead of planning through the fog. Ready specs stay on Route A.

**Readiness soft-check (adoption-gated; warn-not-block; fn-58):** runs right after the spec resolves and before the scout fan-out (warn before spending research tokens on a half-baked spec). It applies only when the input resolved to an existing spec (Route A, canonical id without a `.M` suffix) — task ids and freeform ideas (Route B) skip this entirely.

```bash
# Reuses $SHOW_JSON from the Step 1 fetch — SAME bash block (vars die across tool
# calls); do NOT re-run `show --json` here. `ready` is an explicit boolean (fn-58.1).
SPEC_READY=$(jq -r '.ready // false' <<< "$SHOW_JSON")

READINESS_WARN=false
if [[ "$SPEC_READY" != "true" ]]; then
  # Adoption gate (husk-vs-presence pattern, like the STRATEGY guard below): fire only
  # when readiness is in use — any spec marked ready OR tracker.readyState configured.
  # Probe failures degrade to "not adopted" → silence (non-adopters never see this).
  # Derived from the Step 0 root snapshot (same literal path) — NOT a config get call.
  READY_STATE=$(jq -r '.value.tracker.readyState // empty' "${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json" 2>/dev/null)
  READY_ADOPTED=$($FLOWCTL specs --json 2>/dev/null | jq '[.specs[] | select(.ready == true)] | length' 2>/dev/null || echo 0)
  if [[ -n "$READY_STATE" || "$READY_ADOPTED" -ge 1 ]]; then
    READINESS_WARN=true
    echo "READINESS GATE ACTIVE — STOP. Read references/readiness-warn.md before continuing."
  fi
fi
```

When `READINESS_WARN=false`: continue silently — zero behavior change for ready specs and for repos that never adopted readiness. No sentinel prints; load no reference.

When the sentinel prints (`READINESS_WARN=true`), STOP and Read
[`references/readiness-warn.md`](references/readiness-warn.md) before any
further step — it owns the non-interactive stderr line and the two frozen
interactive option sets. Never a hard block (R6).

**Check if memory and github-scout are enabled** (from the Step 0 root snapshot — no config get calls):
```bash
jq '{memory_enabled: .value.memory.enabled, scouts_github: .value.scouts.github}' "${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json"
```

**Check for STRATEGY.md (husk-vs-presence — uses `sections_filled >= 1`, NOT `[[ -f STRATEGY.md ]]`):**
```bash
STRATEGY_STATUS_JSON=$($FLOWCTL strategy status --json 2>/dev/null || echo '{"exists":false,"sections_filled":0}')
STRATEGY_FILLED=$(jq -r '.sections_filled // 0' <<< "$STRATEGY_STATUS_JSON" 2>/dev/null || echo 0)

if [[ "$STRATEGY_FILLED" -ge 1 ]]; then
  STRATEGY_JSON=$($FLOWCTL strategy read --json 2>/dev/null || echo '{}')
  # Pass the parsed STRATEGY.md content into plan-prompt context alongside research findings.
  # `tracks` is a raw markdown string (### <track-name> H3 sub-blocks); empty section bodies
  # are "" not null. The plan prompt sees `name`, `target_problem`, `approach`, `tracks`,
  # `last_updated` verbatim — no paraphrasing. Active tracks shape the Strategy Alignment
  # section in Step 5; conflicts with active tracks surface as drift in Step 5.
  STRATEGY_PRESENT=true
  echo "STRATEGY GATE ACTIVE — STOP. Read references/strategy-alignment.md before continuing."
else
  STRATEGY_PRESENT=false
fi
```

When `STRATEGY_PRESENT=true`, the scouts and the plan-prompt see the strategy content; STOP and Read [`references/strategy-alignment.md`](references/strategy-alignment.md) before any further step — it owns the `## Strategy Alignment` and `## Strategy drift flagged for review` sections Step 5 renders. When `STRATEGY_PRESENT=false` (no STRATEGY.md or husk), the plan skips the `## Strategy Alignment` section and any drift-surfacing entirely (Step 5) — absence is fine, no signal to align to; load no reference.

**Every scout in the depth-appropriate set below runs, in parallel.** The set is keyed on `--depth` — a deterministic, user-signaled tier — never on your judgment of "what seems relevant". A fan-out that dropped a scout because it seemed irrelevant has broken this; that judgment-skip is the anti-pattern.

Only the **three web-research scouts** are depth-tiered — everything else (the codebase-grounding scouts AND the Step-3 `flow-gap-analyst`) runs at EVERY depth, because a missing requirement or an ungrounded plan is bad at any size (worst on the thinnest short specs):

| `--depth` | Web-research scouts (`practice-scout`, `docs-scout`, `github-scout`) | Always-run (both depths) |
|-----------|------|------|
| **SHORT** | **skipped** — pointer-shaped web signal the implementer can re-fetch (WebFetch) during work; a small change is grounded by the codebase scouts | `repo-scout`, `spec-scout`, `memory-scout`, `docs-gap-scout` (honoring `IF …` config gates) + `flow-gap-analyst` (Step 3) |
| **STANDARD / DEEP** | **run** — feature-sized plans need external best-practice / framework-doc / cross-repo signal | same |

Within the chosen tier, every one of that tier's scouts runs (the anti-pattern below still binds — no cherry-picking). The table below lists the full set; on a SHORT plan, run every row except the three web-research scouts. SHORT is often a *fallback* default (the depth question is skipped for configured backends; pilot defaults to short), so the only thing a fallback-short plan loses is the recoverable web-research signal — never a requirement (flow-gap-analyst) or codebase grounding.

---

Run ALL of these scouts in parallel:
| Scout | Purpose | Required |
|-------|---------|----------|
| `flow-next:repo-scout` | Grep/Glob/Read patterns | YES |
| `flow-next:practice-scout` | Best practices + pitfalls | YES |
| `flow-next:docs-scout` | External documentation | YES |
| `flow-next:github-scout` | Cross-repo patterns via gh CLI | IF scouts.github |
| `flow-next:memory-scout` | Project memory entries | IF memory.enabled |
| `flow-next:spec-scout` | Dependencies on open specs | YES |
| `flow-next:docs-gap-scout` | Docs needing updates | YES |

**Anti-pattern**: cherry-picking scouts *within a tier* "because they seem most relevant" — that judgment-skip causes incomplete plans. (This is distinct from the DEPTH tier above: dropping the web-research scouts on a user-chosen SHORT plan is a deterministic, user-signaled tradeoff, not a relevance guess.)

**Scout model tiers.** `repo-scout`, `spec-scout`, `docs-gap-scout`, `docs-scout`,
`practice-scout` and `github-scout` — and Step 3's `flow-gap-analyst` — are
**thinking scout** dispatches: requirement analysis and pattern judgment
degrade badly on a fast model. `memory-scout` — the mechanical inventory
scan — is a **fast scout** dispatch. **Routing precedence, highest first: an explicit argument in the
invocation, then the project routing block in the instruction file, then the
agent definition's own default, then the session model.** Where a harness
cannot honor an agent definition's default, a thinking scout runs on the
SESSION model, never a fast/cheap one; consult the harness's reach page for
what it can do.

Must capture:
- File paths + line refs
- Existing centralized code to reuse
- Similar patterns / prior work
- External docs links
- Project conventions (CLAUDE.md, CONTRIBUTING, etc)
- Architecture patterns and data flow
- Spec dependencies (from spec-scout)
- Doc updates needed (from docs-gap-scout) - add to task acceptance criteria
- DESIGN.md design system tokens (if repo-scout found one)

**Check `.flow/memory/declined/` by concept before proposing scope.** One `ls` (the directory is one file per concept, `<concept-slug>.md`); read any file whose concept the request touches. On a hit: cite the file in `## Decision Context`, append this request to that file's `## Prior requests` as a dated line, and keep the scope out of the plan. **Only the user reopens a declined concept** — say it was declined before, say what would change, and wait; a plan that quietly re-proposes declined scope is the failure this ledger exists to stop. No directory (or an empty one) means nothing was ever declined: continue silently.

**Done when:** every scout in the depth-appropriate set has returned, the capture list above is populated with file paths and line refs, and `.flow/memory/declined/` has been checked for every concept the request touches.

## Step 2: Stakeholder & scope check

Before diving into gaps, identify who's affected:
- **End users** — What changes for them? New UI, changed behavior?
- **Developers** — New APIs, changed interfaces, migration needed?
- **Operations** — New config, monitoring, deployment changes?

This shapes what the plan needs to cover. A pure backend refactor needs different detail than a user-facing feature.

**Before deciding, can you state the open question precisely — not answer it?** If the question itself will not come out sharp, that is an interview or chart signal, not a planning input: planning a fog is how a plan acquires scope nobody asked for. Recommend `/flow-next:interview` (a spec that needs sharpening) or `/flow-next:chart` (an idea that needs shaping) and stop, rather than deciding through the blur.

**An empirically answerable fork gets a throwaway probe, not a question.** When a fork the plan hinges on is something the running code can settle (a behavior, a timing, an output), run the probe and read the answer instead of parking it as an open question or asking the user — the ask is the slow path for a fact the machine already holds.

**Wildly divergent independent opinions mean the framing was underspecified.** When independent inputs (scout reports, review verdicts, consulted models) disagree wildly on the same question, do not average them and do not quietly pick the one you prefer — reframe the question and re-run it; divergence measures the question, not the answerers.

**Scope minimality (YAGNI — binding on the plan you write):**
- Every task must trace to an R-ID, and every R-ID must trace to the REQUEST.
  A capability the request never asked for — an extra command, an export path,
  a detection hook, a config surface — is not scope; it goes into
  `## Boundaries` as explicitly out-of-scope, in one line.
- Prefer the SMALLEST architecture that satisfies the acceptance criteria.
  When you find yourself designing machinery to MANAGE a risk (trust stores,
  consent layers, caps, scanners), first ask whether the risk can be
  ELIMINATED STRUCTURALLY (a closed schema, an inert format, a path proven
  outside the writable root, a capability simply not exposed) — structural
  elimination is usually less code, fewer failure modes, and no new state.
- Rejected bigger designs get ONE line each in `## Decision Context`
  ("rejected X as overkill: <why>"), never tasks.
- **A policy-level rejection also gets a file in `.flow/memory/declined/`.**
  When the rejection is product judgment — we could build this, we are choosing
  not to — write `.flow/memory/declined/<concept-slug>.md` on its FIRST
  refusal: title, the decision in one line, short reasoning, and a
  `## Prior requests` list opened with today's date and this request. The file
  already exists → append the dated line to `## Prior requests` instead; never
  rewrite the decision. **Never write one for scope declined because it already
  exists**, is already planned, or belongs to another spec — that is not a
  refusal, and recording it as one teaches the next planner that shipped
  capability is rejected scope. Size-and-sequencing trims ("not this task",
  "not this milestone") are ordinary YAGNI lines, not ledger entries. The
  ledger file is memory prose written directly, like the rest of
  `.flow/memory/` — it is not a plan artifact and changes nothing about the
  rule that every spec and task goes through `flowctl` into `.flow/`. Its body
  prose follows the artifact prose contract in
  [docs/prose.md](../../docs/prose.md); proceed without it when the doc is
  absent.
- One collection/surface/format now beats N configurable ones later; ship the
  single concrete case the request names.
- This discipline trims SCOPE, never rigor: error/negative-case enumeration
  per AC (the template's negative-cases discipline) is EXEMPT and stays
  complete, as do Boundaries and R-ID coverage. Equally exempt are
  filesystem-identity, permission, and concurrency guards (realpath/symlink
  containment, lock-guarded writes, forced excludes of runtime state) — an
  eliminated guard is not an eliminated feature.

**Done when:** the affected stakeholders are named, and every capability that survived into scope traces to the request (everything else is a one-line `## Boundaries` entry, and any policy-level refusal has its `.flow/memory/declined/` file).

## Step 3: Flow gap check

Run the gap analyst subagent:
- Task flow-next:flow-gap-analyst(<request>, research_findings)

The gap analyst is a **thinking scout** dispatch — Step 1's rule applies.
**Routing precedence, highest first: an explicit argument in the invocation,
then the project routing block in the instruction file, then the agent
definition's own default, then the session model.** Where the harness cannot
honor the agent definition's default, run it on the session model, never a
fast/cheap one.

Fold gaps + questions into the plan.

**Done when:** the analyst has returned, and each gap it raised is either folded into the plan or listed as an open question.

## Step 4: Pick depth

Default to standard unless complexity demands more or less.

**SHORT** (bugs, small changes)
- Problem or goal
- Acceptance checks
- Key context

**STANDARD** (most features)
- Overview + scope
- Approach
- Risks / dependencies
- Acceptance checks
- Test notes
- References
- Mermaid diagram if data model changes

**DEEP** (large/critical)
- Detailed phases
- Alternatives considered
- Non-functional targets
- Architecture/data flow diagram (mermaid)
- Rollout/rollback
- Docs + metrics
- Risks + mitigations

## Step 5: Write to .flow

Plan and task-spec prose follows the artifact prose contract in [docs/prose.md](../../docs/prose.md); proceed without it when the doc is absent.

**Calibration (read first):** before writing task specs, read [`examples.md`](examples.md) — good/bad task-spec shapes, investigation-target formats, T-shirt sizing, and coverage-table examples. It is the few-shot anchor that keeps task specs well-sized and well-shaped; skipping it is why plans drift toward vague or over-split tasks.

**Efficiency note**: Author documents with the **Write tool**, revise them with **Edit** — never compose a document inside a bash heredoc or stdin pipe. A heredoc puts the whole document into the command string, so every revision (review fix loop, interview write-back) re-emits it in full; a Written file is revised span-by-span with Edit at a fraction of the tokens. Heredocs/stdin (`--file -`) stay acceptable only for short transient payloads (≲10 lines). Route B is the ceremony fast path (fn-163): `spec create --plan-file` creates the spec WITH its plan in one call, and ONE `task create --from-json` call materializes every task of the plan (all-or-nothing, one lock). Granular verbs (`spec set-plan`, per-task `task create`, `task set-spec`) remain the tools for editing what already exists (Route A edits, interview write-backs, review fix loops, adding a task later).

**Route A - Input was an existing Flow ID**: the spec-id and task-id edit paths
live in [`references/route-a-refine.md`](references/route-a-refine.md) — read it
now, follow it, then continue with the plan-content and task-authoring rules
below (they bind on both routes). Route B sessions skip that file entirely.

**Route B - Input was text (new idea)**:

1. Compose the plan FIRST, then create spec + plan in ONE call — **tracker-first is the recommended team default** when a tracker is configured (`tracker.specIds=tracker`): the tracker is the distributed allocator, so parallel agents stop colliding on `fn-N`. Route from the Step 0 root config snapshot (fn-110) — **no new `config get`**. Explicit user override in the invocation always wins.

   The plan markdown (step 2's scaffold) is fed to the creation call via `--plan-file` so create + set-plan collapse into one invocation (`--plan-file` validates before id allocation and composes unchanged with the tracker-first flags). **Author-as-file rule:** compose the plan with the **Write tool** at a literal agent-composed path — NOT inside a bash heredoc. Resolve `${TMPDIR:-/tmp}` yourself and type the RESOLVED literal path (e.g. `/tmp/flow-plan-body-ab12.md`) identically in the Write call and the Bash block — file tools do not expand shell variables; the path is literal in both tool calls, so no shell variable crosses calls. If plan review or a fix loop demands revisions, revise this file with **Edit** (span edits) and re-run only the affected flowctl call — never re-emit the document. Delete the file only after the spec (and any revision loop) is finalized; the durable plan lives in `.flow/` via the create call.

   ```
   Write tool -> /tmp/flow-plan-body-<suffix>.md   (full plan markdown — step 2's scaffold; a RESOLVED literal path — substitute your resolved temp dir, never an unexpanded ${TMPDIR} expression)
   ```
   ```bash
   # Creation block references the SAME literal path (no cross-call variable):
   PLAN_FILE="/tmp/flow-plan-body-<suffix>.md"   # the EXACT resolved literal the Write call used
   # ... routing + creation lines below run HERE ...
   # (delete $PLAN_FILE only after the plan is finalized — see author-as-file rule)
   ```

   ```bash
   # Spec-id allocator gate — from the Step 0 root snapshot (literal path; no new config get).
   # NO pipelines in the probe — a failed producer masked by a healthy consumer
   # fails CLOSED. Capture raw first, rc-checked; parse separately.
   ACTIVE=0
   SPEC_IDS="$(jq -r '.value.tracker.specIds // "flow"' "${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json" 2>/dev/null)" || ACTIVE=1   # probe ERROR ⇒ ACTIVE (fail open)
   if [ "$ACTIVE" = "0" ]; then
     BRIDGE_RAW="$($FLOWCTL sync active --json 2>/dev/null)" || ACTIVE=1     # probe ERROR ⇒ ACTIVE
   fi
   if [ "$ACTIVE" = "0" ]; then
     BRIDGE_ACTIVE="$(printf '%s' "$BRIDGE_RAW" | jq -r '.active // false' 2>/dev/null)" || ACTIVE=1   # parse ERROR ⇒ ACTIVE
     [ "$SPEC_IDS" = "tracker" ] && [ "$BRIDGE_ACTIVE" = "true" ] && ACTIVE=1
   fi
   if [ "$ACTIVE" = "1" ]; then
     echo "TRACKER-FIRST GATE ACTIVE — STOP. Read references/tracker-first-mint.md before continuing."
   fi
   # The tracker-first arm (named-issue mint, create-first ceremony, attach + seed)
   # runs HERE, and ONLY per that reference — it assigns SPEC_OUTPUT / IDENTIFIER.

   # SILENT degrade - the ONLY flow-first creation site, deliberately OUTSIDE
   # the branch above. A create-first noop / unreachable transport / failed mint
   # leaves SPEC_OUTPUT unset INSIDE the tracker arm, and an `else` can never run
   # in that case, so the fall-through has to be an unconditional post-check.
   # Bridge inactive / no transport / create-first noop / config flow / override:
   # GUARD: degrade ONLY when nothing was created remotely. If create-first
   # already made and recorded an issue and the MINT then failed, falling back
   # to flow-first would strand that issue as an orphan - surface
   # identifier + url + retryKey and STOP instead (the record makes it resumable).
   if [ -z "$SPEC_OUTPUT" ] && [ -z "$IDENTIFIER" ]; then
     SPEC_OUTPUT=$($FLOWCTL spec create --title "<Short title>" --plan-file "$PLAN_FILE" --json)
   fi
   ```
   When the sentinel prints, STOP and Read
   [`references/tracker-first-mint.md`](references/tracker-first-mint.md) before
   any further step — it owns the tracker-first mint ceremony and its network
   cost. When it does not print, the unconditional post-check above is the whole
   creation path.

   This returns the spec ID (e.g., `wor-17-slug` under tracker-first, or `fn-1-add-oauth` under flow-first). `branch_name` defaults to the spec ID at create time — no follow-up `spec set-branch` call on the create path. Only when the user specified a custom branch, pass it at create: `$FLOWCTL spec create --title "<Short title>" --branch "<custom-branch>" --plan-file "$PLAN_FILE" --json` (`spec set-branch` remains the tool for renaming an existing spec's branch later). Do **not** add a runtime advisory/nag about the id scheme at this mint site (withdrawn R10) — setup owns the one-time question.

2. The plan content (this scaffold is what the Write tool composes into step 1's `$PLAN_FILE`; `spec set-plan` is the Route A / editing path, not part of Route B creation):

   The canonical scaffold lives in [`plugins/flow-next/templates/spec.md`](../../templates/spec.md) — section list, scope-owner annotations, and the `## Decision Context` flat-vs-H3 conditional. At runtime the template is resolved via the 3-tier discovery cascade (first match wins): `<repo_root>/SPEC.md` → `<repo_root>/spec.md` → bundled `${PLUGIN_ROOT}/templates/spec.md`. The bundled file is the canonical source of truth; earlier tiers are user-customized overrides. The full walker (case-insensitive FS probe, both-exist warning, plugin-root fallback) is single-sourced in [`plugins/flow-next/references/spec-template-discovery.md`](../../references/spec-template-discovery.md). Read the resolved template before authoring; never duplicate its section list inline. The plan skill extends that scaffold with the plan-specific sections shown below (Overview, Quick commands, Strategy Alignment, Strategy drift, Early proof point, Requirement coverage).

   ```
   Include: Overview, Scope, Approach, Quick commands (REQUIRED),
   Acceptance Criteria, Early proof point, Requirement coverage, References.
   Conditional sections: ## Strategy Alignment (when STRATEGY_PRESENT=true from Step 1),
   ## Strategy drift flagged for review (when plan scope conflicts with an active track).
   Add mermaid diagram if data model or architecture changes.
   Write tool -> $PLAN_FILE (author-as-file rule — full scaffold below):

   # Spec Title

   ## Overview
   ...

   ## Quick commands
   ```bash
   # At least one smoke test command
   ```

   ## Boundaries / non-goals
   - <what this spec explicitly does NOT cover>

   <!-- ## Strategy Alignment and ## Strategy drift flagged for review go HERE,
        between ## Boundaries / non-goals and ## Decision context, ONLY when
        STRATEGY_PRESENT=true from Step 1 — their shapes and rules live in
        references/strategy-alignment.md. When STRATEGY_PRESENT=false, omit both
        entirely. -->

   ## Decision context
   - <why this approach over alternatives>

   ## Acceptance Criteria
   - **R1:** <testable criterion>. Errors: <enumerated cases, or "no error surface beyond X">
   - **R2:** <testable criterion>. Errors: <cases, or "no error surface beyond X">
   - **R3:** <testable criterion>. Errors: <cases, or "no error surface beyond X">

   ## Early proof point
   Task fn-N-slug.1 validates the core approach (<what it proves>).
   If it fails, re-evaluate <strategy> before continuing with fn-N-slug.2+.

   ## Requirement coverage

   | Req | Description | Task(s) | Gap justification |
   |-----|-------------|---------|-------------------|
   | R1  | <criterion from Acceptance Criteria> | fn-N-slug.1, fn-N-slug.2 | — |
   | R2  | <another criterion> | fn-N-slug.3 | — |
   | R3  | <deferred item> | — | Deferred to fn-M-slug |
   ```

   **Early proof point rules:**
   - Identify which task proves the fundamental approach works
   - One sentence: which task + what it proves
   - One sentence: what to reconsider if it fails
   - Usually the first task in dependency order, but not always

   **Requirement coverage rules:**
   - One row per acceptance criterion or distinct requirement from the spec
   - Every requirement must map to at least one task OR have a gap justification
   - Table goes at the bottom of the spec (after Acceptance Criteria + Early proof point)
   - Keep Req IDs simple (R1, R2...) — they're local to this spec

   **R-ID rule (binding on new specs):**
   - Number acceptance criteria as `R1`, `R2`, `R3`, ... in creation order using the `- **Rn:** ...` prose prefix format shown in the template above.
   - Once a review cycle has run against an R-ID, **never renumber**. Reordering is fine (R1, R3, R5 after R2/R4 deletion is correct).
   - New criteria take the next unused number. Gaps are fine — do not compact.
   - R-IDs in `## Acceptance Criteria` and `## Requirement coverage` must match (same IDs, same meanings).
   - R-IDs are plain markdown prose, not YAML — the reviewer matches them via LLM reasoning, not strict parsing.
   - When `.flow/criteria.md` exists, do not restate its standing criteria (G-IDs) as R-IDs - completion review already judges every G-ID against the spec. Reference a relevant G-ID in prose when useful; write an R only for what this spec adds beyond the standing rule.
   - Each behavioral R-ID enumerates its error/invalid-input/boundary cases inside the bullet (malformed input, missing files, conflicting state, limits), or records "no error surface beyond X"; silence is incomplete. Applies to spec-added R-IDs only — never to standing G-IDs from `.flow/criteria.md`.

   **Spec durability rule:** the spec states **contracts** — types, signatures, behaviors, invariants — and **never file paths or line numbers**. Coordinates rot on the first refactor and every rotted one feeds plan-sync churn. One exception: a decision-rich snippet whose exact location IS the decision. **The tasks you write under this spec are exempt** — `**Files:**` / `**Touches:**` stay a task's job per the task-shape doctrine, and the repo-scout `file:line` refs belong there, in the task spec, not in the spec body.

   **Parked-unknowns consumption:** when the spec carries `## Parked unknowns`, read it before writing anything. Each bullet is one of three things: resolved by this planning pass (move the answer into the canonical section that owns it and DELETE the bullet), turned into scheduled work (it becomes a task; delete the bullet), or still genuinely unknown (leave it parked, verbatim). Never leave a bullet standing next to its own answer. Empty the section out entirely and the heading goes with it.

   **Source-tag consumption:** a capture-authored spec carries provenance tags on its acceptance criteria. Route A sessions handle them per [`references/route-a-refine.md`](references/route-a-refine.md); Route B specs have no tags to consume.

3. Set spec dependencies (from spec-scout findings) — BOTH directions:

   ```bash
   # (a) FORWARD — the new plan depends on an existing spec (spec-scout "Dependencies"):
   $FLOWCTL spec add-dep <new-spec-id> <dependency-spec-id> --json

   # (b) REVERSE — an existing spec depends on the new plan (spec-scout "Reverse Dependencies").
   #     MUST record these too: the edge belongs on the OTHER spec (it can't start until the new
   #     plan lands). Dropping it leaves that spec falsely ready → pilot/backlog picks it up and
   #     builds against infrastructure this plan hasn't shipped yet (silent, worst in autonomous mode).
   $FLOWCTL spec add-dep <other-spec-id> <new-spec-id> --json
   ```

   Report findings at end of planning (no user prompt needed):
   ```
   Spec dependencies set:
   - fn-N-slug → fn-2-add-auth (Auth): Uses authService from fn-2-add-auth.1   [forward]
   - fn-7-notify → fn-N-slug (Notifications): waits for the event system this plan adds   [reverse]
   ```

4. Create ALL child tasks in ONE `task create --from-json` call (fn-163; all-or-nothing under one lock — zero follow-up `task set-spec` on the plan path). Compose the task set with the **Write tool** (author-as-file rule — revisable with Edit if the batch is rejected or the plan is revised, instead of re-emitting the array):
   ```
   Write tool -> /tmp/flow-plan-tasks-<suffix>.json   (ONE bare JSON array; RESOLVED literal path — same string in the flowctl call below):
   [
     {"title": "<Task 1 title>", "description": "<## Description ...>", "acceptance": "<- [ ] ...>", "satisfies": ["R1", "R3"]},
     {"title": "<Task 2 title>", "deps": [1], "description": "...", "acceptance": "...", "satisfies": ["R2"]}
   ]
   ```
   ```bash
   $FLOWCTL task create --spec <spec-id> --from-json "/tmp/flow-plan-tasks-<suffix>.json" --json   # same resolved literal the Write call used
   ```

   Per object: `title` required non-empty; `description`/`acceptance` optional strings (full task-spec markdown — same content the granular `--description-file`/`--acceptance-file` flags take); `satisfies` an array of bare R-ID tokens (grammar `R[1-9][0-9]*[a-z]?`); `deps` an array of task-id strings or **1-based integer indexes of EARLIER entries in the same array** (so intra-plan dependencies need no pre-existing ids); `priority` optional int. Any invalid entry rejects the whole batch with zero writes; `--json` returns the created ids in input order. Omit `deps`/`satisfies` where they don't apply. Granular one-task `task create` (with `--description-file`/`--acceptance-file`/`--satisfies`) remains the tool for ADDING a task to an existing plan later; `task set-spec` is for editing tasks that already exist.

   **Task spec content** (remember: NO implementation code):

   **The artifact split (binding):** the SPEC is the human-facing record of
   what and why. The TASK is the delegation payload — the concrete HOW that
   lets a weaker or cheaper implementer build without re-deriving design
   decisions. Executors ALWAYS receive the task file TOGETHER with the full
   parent spec (the anchor bundle delivers both verbatim), so:
   - NEVER restate spec content in a task — no problem framing, no
     architecture rationale, no re-told acceptance criteria. Reference R-IDs
     and spec sections instead. A restatement is generated twice, delivered
     twice in every anchor, and drifts (plan-sync then has to chase it).
   - DO write the implementation plan: named files, concrete approach and
     ordering, patterns to follow, task-scoped acceptance. That is the task's
     entire job.

   ```markdown
   ---
   satisfies: [R1, R3]
   ---

   ## Description
   [What THIS task builds and why it is split this way — ≤10 lines. The how
   lives in ## Approach; the why-it-matters lives in the parent spec.]

   **Size:** S/M (L tasks should be split)
   **Files:** list expected files. Task files carry the task-specific contract - named files, named test cases, named acceptance - because downstream executors receive the task file as the brief alongside the parent spec.
   **Touches:** [src/auth/**, src/routes/auth.ts] — repo-relative paths/globs this task expects to MODIFY (body line, not frontmatter — the batch create API renders frontmatter from `satisfies` only)

   ## Approach
   - Follow pattern at `src/example.ts:42`
   - Reuse `existingHelper()` from `lib/utils.ts`

   ## Investigation targets
   **Required** (read before coding):
   - `src/auth/oauth.ts` — existing OAuth flow to extend
   - `src/middleware/session.ts:23-45` — session validation pattern

   **Optional** (reference as needed):
   - `src/auth/*.test.ts` — existing test patterns

   ## Design context
   *Only include for frontend tasks when DESIGN.md exists in project.*

   Relevant DESIGN.md sections for this task:
   - **Colors:** Primary (#2665fd) for CTAs, Neutral (#757681) for backgrounds
   - **Components:** Buttons are rounded (8px), primary uses brand blue fill
   - **Do's/Don'ts:** Primary color only for single most important action per screen

   Full design system: `DESIGN.md` (read before implementing UI changes)

   ## Key context
   [Only for recent API changes, surprising patterns, or non-obvious gotchas]

   ## Acceptance
   - [ ] Criterion 1
   - [ ] Criterion 2
   ```

   **Design context rule:** Only add `## Design context` to tasks where Files/Description reference frontend patterns:
   - Extensions: `.jsx`, `.tsx`, `.vue`, `.svelte`, `.css`, `.scss`
   - Directories: `components/`, `pages/`, `views/`, `layouts/`, `styles/`, `app/`
   - Keywords: button, modal, form, layout, responsive, color, font, card, navigation, theme, UI, component

   Backend-only tasks (`api/`, `server/`, `controllers/`, `.py`, `.go`): skip design context.
   When ambiguous: include it (false positive is low-cost, false negative causes inconsistency).

   **Investigation targets rules:**
   - Max 5-7 targets per task (focus, don't flood)
   - Use exact file paths with optional line ranges — not descriptions alone
   - Validate paths exist at plan time (repo-scout already found them)
   - "Required" = must read before implementing. "Optional" = helpful reference
   - Targets come from repo-scout findings in Step 1

   **Refactor-shaped tasks name an equivalence harness.** A task whose job is
   restructuring-without-behavior-change names its behavior pin in the task
   body: a script diffing old-vs-new outputs, or a recorded baseline replayed
   against the new code. "Tests still pass" is not a pin when the tests never
   covered the moved behavior — an unpinned refactor is where silent behavior
   change ships as cleanup.

   **`satisfies` frontmatter rules (optional, additive):**
   - Populate `--satisfies` only when the task obviously advances specific R-IDs from the spec's `## Acceptance Criteria` section.
   - Tasks that do infrastructure, refactoring, shared plumbing, or docs-only work may legitimately have **no** `satisfies` entry — omit the flag entirely.
   - Use bare R-ID tokens (`--satisfies R1,R3`; rendered as `satisfies: [R1, R3]`), not quoted strings.
   - Frontmatter is additive — tasks created without it parse unchanged.

   **`**Touches:**` line rules — write one on EVERY task:**
   - Repo-relative paths/globs the task expects to MODIFY (not merely read),
     authored at plan time from the `**Files:**` analysis and checked at plan
     review. Example: `**Touches:** [src/auth/**, src/routes/auth.ts]`.
   - A BODY line beside `**Files:**`, not YAML frontmatter — the one-call
     `task create --from-json` route renders frontmatter from `satisfies`
     only, so a frontmatter `touches:` would silently land in the body anyway.
   - **Uncertain → declare WIDER, never omit.** A too-wide declaration
     intersects a sibling and sends the wave serial, which is exactly today's
     behavior; an omitted line does the same thing while telling the conductor
     nothing. Since both err toward serial, the wide declaration is strictly
     better: it is the only one that can ever become a wave once the overlap
     turns out to be false. Omit only when a task genuinely cannot name any
     path it will modify.
   - **Why this is worth the line:** wave dispatch is fail-closed on it, so a
     spec whose tasks omit it can never run concurrently no matter how
     independent the tasks are. Measured 2026-08-14: zero of 37 tasks across
     eleven consecutive specs carried the line, so no wave had ever been
     dispatched; a probe wave with the line present ran two tasks in 96s against
     187s serial. A wrong declaration is cheap by construction — workers write
     in isolated workspaces, so an overlap surfaces as a merge conflict at the
     join and costs one serial re-run, never correctness.
   - Inert metadata to flowctl — models read it; no deterministic parsing.

5. Add task dependencies (if not already set via `--deps`):

   **Preferred**: Use `--deps` flag during task creation (step 4). This saves tool calls.

   **Alternative**: Use `dep add` to add dependencies after task creation:
   ```bash
   # Syntax: dep add <dependent-task> <dependency-task>
   # "task B depends on task A" → dep add B A
   $FLOWCTL dep add fn-N.2 fn-N.1 --json
   ```

   Use `dep add` when you need to add dependencies to existing tasks or fix missed dependencies.

   **The spec is never re-fetched after writing** (no post-write `show`/`cat` — you just authored this state; Step 6 validates it, and pilot judges the plan stage from flowctl state, not this skill's stdout). A post-write `show`/`cat` outside the Step 7 fix-loop re-anchor — the one deliberate exception — has broken this.

**Done when:** the spec exists in `.flow/` with its plan body, every task was created in the one `task create --from-json` call, dependencies are recorded in both directions, and no plan artifact was written outside `.flow/`.

## Step 6: Validate

```bash
$FLOWCTL validate --spec <spec-id> --json
```

Fix any errors before proceeding.

**Done when:** `validate` returns clean for the spec, and the execution waves below are derived from the validated DAG.

### Step 6.1: Derive execution waves

After validation, derive dependency-ordered execution waves from the task DAG
you authored:

- Wave 1 contains tasks with no task dependencies.
- Each later wave contains tasks whose dependencies are all in earlier waves.
- Tasks in the same wave are **parallel candidates**, not a promise of
  concurrent execution; `/flow-next:work` still judges shared resources,
  isolation, integration, and host capacity.

Keep the result compact and carry it into the Step 8 summary:

```text
Execution waves:
- Wave 1 (parallel candidates): fn-N.1, fn-N.2
- Wave 2: fn-N.3
```

If review or a Step 8 refinement changes tasks or dependencies, re-run Step 6
and recompute these waves before presenting the final summary.

## Step 6.5: Tracker sync (opt-in) — NO sub-issues; optional body checklist only

```bash
LEAF="$(jq -r '.value.tracker.perEvent.plan' "${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json" 2>/dev/null)"   # leaf from the Step 0 root snapshot (shared gating predicate — work SKILL.md); missing → literal "null", same as the old per-key read
case "$LEAF" in
  pull)      OP="pull" ;;
  push)      OP="push" ;;
  reconcile) OP="reconcile" ;;
  comment)   OP="comment" ;;
  off|null)  OP="off" ;;
  *)         OP="off" ;; # malformed config stays silent
esac
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
   && [ "$OP" != "off" ]; then
  # Load and follow references/tracker-projection.md with <OP> and <spec-id>.
  # Its inline wrapper makes exactly one lifecycle facade call:
  #   "$FLOWCTL" tracker sync "$SPEC_ID" --op "$OP" --event plan <legal file flags>
  # For OP=comment, Plan synthesizes the planning summary named in that reference.
fi
```

Off, unset, inactive, or malformed: skip the reference and continue. This gate
uses the Step 0 snapshot and the existing active probe; it adds no config read
or default-path round trip.

## Step 7: Review (if chosen at start)

When review mode is `none`, skip this step and load no review reference. When a
review mode was selected, load and follow
[`references/selected-review.md`](references/selected-review.md).

## Step 8: Offer next steps

Show spec summary with size breakdown — the validate result plus the derived
execution waves, on every run:

```
Spec fn-N-slug created: "<title>"
Tasks: M total | Sizes: Ns S, Nm M
Execution waves:
- Wave 1 (parallel candidates): fn-N.1, fn-N.2
- Wave 2: fn-N.3
```

Then, under the summary, offer `/flow-next:visual fn-N-slug` in one line as a compact visual digest (task tree, planned file layout, R-ID coverage) for reviewing the plan at a glance — an option the user picks, never run for them.

Then route on interactivity:

```bash
ACTIVE=0
[ "${AUTONOMOUS:-0}" = "1" ] || [ -n "${FLOW_AUTONOMOUS:-}" ] || [ -n "${FLOW_RALPH:-}" ] || [ -n "${REVIEW_RECEIPT_PATH:-}" ] || ACTIVE=1
if [ "$ACTIVE" = "1" ]; then
  echo "NEXT-STEPS MENU ACTIVE — STOP. Read references/next-steps-menu.md before continuing."
fi
```

When the sentinel prints, STOP and Read
[`references/next-steps-menu.md`](references/next-steps-menu.md) before any
further step — it owns the numbered options menu and the go-deeper / simplify
loop, including when Step 8.5 runs relative to that loop.

Under `AUTONOMOUS=1` there is no options menu — run Step 8.5 directly after Step 6/7 complete.

## Step 8.5: HTML render lens (opt-in) — regenerate the spec artifact with the plan layer

```bash
HTML_LENS=$(jq -r 'if .value.artifacts.html.enabled == true then "true" else "false" end' "${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json" 2>/dev/null || echo false)   # from the Step 0 root snapshot — not a config get call
```

When false, unset, or malformed: skip the whole step. Load no reference, write
no artifact, open no session, and print no artifact output. When true, load and
follow [`references/html-render-lens.md`](references/html-render-lens.md).
