# Flow Plan Steps

**IMPORTANT**: Steps 1-3 (research, gap analysis, depth) ALWAYS run regardless of input type.

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

**Minimize file overlap for parallel work:**

When splitting tasks, design for minimal file overlap. Tasks touching disjoint files can be worked in parallel without merge conflicts.

- ❌ Bad: Task A and B both modify `src/auth.ts`
- ✅ Good: Task A modifies `src/auth.ts`, Task B modifies `src/routes.ts`

List expected files in each task's `**Files:**` field. If multiple tasks must touch the same file, mark dependencies explicitly with `flowctl dep add`.

## Step 0: Initialize .flow

```bash
# Ensure .flow exists (FLOWCTL defined once in SKILL.md preamble)
$FLOWCTL init --json

# ONE root config snapshot for the whole run (fn-110): {"key":null,"value":{<merged config>}}.
# Every later config lookup (readiness, memory/scout gates, tracker leaf, HTML lens)
# derives from this file via jq — no further `config get` calls on the plan path.
# Path-persistence rule: compose the literal path with an agent-chosen 4-char suffix
# and type it verbatim in every later block that reads it.
PLAN_CFG="${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json" # literal path
$FLOWCTL config get --json > "$PLAN_CFG" 2>/dev/null || printf '{"key":null,"value":{}}' > "$PLAN_CFG"
```

## Step 1: Fast research (parallel)

**If input is a Flow ID** (fn-N-slug or fn-N-slug.M, including legacy fn-N/fn-N-xxx): First fetch it with `$FLOWCTL cat <id>` plus ONE `show --json`, captured as `SHOW_JSON` — the readiness soft-check below reads the same capture, so run the fetch and the readiness check in the SAME bash block (vars do not survive across prompt turns; never run a second `show --json` for readiness):

```bash
$FLOWCTL cat <id> # request context (spec body)
SHOW_JSON=$($FLOWCTL show <id> --json) # ONE fetch — request context AND readiness read
echo "$SHOW_JSON" # command substitution hides stdout — bring it into view once
```

**Handle-recognition rule (R16):** do NOT gate the Flow-ID branch on a hard "must start with `fn-`" check. Before treating a single-token arg as a freeform idea, route it through `$FLOWCTL show <arg> --json` — flowctl's widened resolver (fn-52.10) maps a tracker key (`wor-17` / `wor-17.M`) to its linked spec/task. If it resolves (rc 0), use the canonical id from the JSON and take the existing-Flow-ID path (Route A in Step 5); only a non-resolving token becomes a new idea (Route B). So `plan wor-17` refines the linked spec, never creating a duplicate.

**Readiness soft-check (adoption-gated; warn-not-block; fn-58):** runs right after the spec resolves and BEFORE the scout fan-out (warn before spending research tokens on a half-baked spec). Applies ONLY when the input resolved to an existing SPEC (Route A, canonical id without a `.M` suffix) — task ids and freeform ideas (Route B) skip this entirely.

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
 fi
fi
```

When `READINESS_WARN=false`: continue silently — zero behavior change for ready specs and for repos that never adopted readiness.

When `READINESS_WARN=true`:

- **Non-interactive / Ralph / autonomous** (any non-interactive marker: `FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH` set, `FLOW_AUTONOMOUS=1`, or the `mode:autonomous` token parsed in SKILL.md — treat the marker *family* as the gate, not a rigid two-var list): auto-proceed with ONE stderr line, never block:
 ```bash
 echo "[READINESS]: spec <id> not marked ready — proceeding (non-interactive)" >&2
 ```
- **Interactive**: ask ONE question (MUST ask via the plain-text numbered prompt described below; lead with recommendation; default proceed — planning is non-destructive and often part of getting a spec ready). The option set splits by tracker mode:

**Ask the user via plain text.** Render the options below as a numbered list `1.` … `N.`, followed by a final option `N+1. Other — type your own answer`. Print the question, then the numbered list, then **stop and wait for the user's next message before continuing**. Parse the reply as: a bare number `1`–`N+1` → that option; the literal text of an option label → that option; free text after `Other` → custom answer.
 - **`tracker.readyState` NOT configured** (local readiness):
 - **header**: `Spec not ready`
 - **body**: `<spec-id> is not marked ready (readiness is in use in this repo). Recommended: proceed — planning is non-destructive and refining a draft is normal. Confidence: [high].`
 - **options** (frozen): `proceed` (default — continue to research), `mark-ready-then-proceed` (run `$FLOWCTL spec ready <id> --json`, then continue), `abort` (exit 0 — no spec or task changes made; re-run /flow-next:plan once the spec is blessed)
 - **`tracker.readyState` configured** (tracker-authoritative readiness — one-way pull; NEVER offer local mark-ready, the next sync would silently revert it):
 - **header**: `Spec not ready`
 - **body**: `<spec-id> is not marked ready; readiness projects from the tracker (state: <readyState>). Recommended: proceed — planning is non-destructive. Confidence: [high].`
 - **options** (frozen): `proceed` (default — continue to research), `abort` (exit 0 — no spec or task changes made), `update-tracker-state-then-rerun` (exit 0 with guidance: move the linked issue to "<readyState>" on the board, pull via /flow-next:tracker-sync, re-run /flow-next:plan)

Never a hard block — `abort` / `update-tracker-state-then-rerun` are user choices, not skill-imposed stops (R6).

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
else
 STRATEGY_PRESENT=false
fi
```

When `STRATEGY_PRESENT=true`, the scouts and the plan-prompt see the strategy content. When `STRATEGY_PRESENT=false` (no STRATEGY.md or husk), the plan skips the `## Strategy Alignment` section and any drift-surfacing entirely (Step 5) — absence is fine, no signal to align to.

**Based on user's choice in SKILL.md setup:**

---

**CRITICAL: run every scout in the DEPTH-appropriate set below, in parallel. The set is keyed on `--depth` (a DETERMINISTIC, user-signaled tier), NOT on your judgment of "what seems relevant" — that judgment-skip is the anti-pattern.**

Only the **three web-research scouts** are depth-tiered — everything else (the codebase-grounding scouts AND the Step-3 `flow-gap-analyst`) runs at EVERY depth, because a missing requirement or an ungrounded plan is bad at any size (worst on the thinnest short specs):

| `--depth` | Web-research scouts (`practice-scout`, `docs-scout`, `github-scout`) | Always-run (both depths) |
|-----------|------|------|
| **SHORT** | **skipped** — pointer-shaped web signal the implementer can re-fetch (WebFetch) during work; a small change is grounded by the codebase scouts | `repo-scout`/`context-scout`, `spec-scout`, `memory-scout`, `docs-gap-scout` (honoring `IF …` config gates) + `flow-gap-analyst` (Step 3) |
| **STANDARD / DEEP** | **run** — feature-sized plans need external best-practice / framework-doc / cross-repo signal | same |

Within the chosen tier you MUST run ALL of that tier's scouts (the anti-pattern below still binds — no cherry-picking). The tables below list the full set; on a SHORT plan, run every row EXCEPT the three web-research scouts. **NOTE:** SHORT is often a *fallback* default (the depth question is skipped for configured backends; pilot defaults to short), so the only thing a fallback-short plan loses is the recoverable web-research signal — never a requirement (flow-gap-analyst) or codebase grounding.

---

**If user chose context-scout (RepoPrompt)**:

Run ALL of these scouts in parallel:
| Scout | Purpose | Required |
|-------|---------|----------|
| the `context_scout` agent | RepoPrompt AI file discovery | YES |
| the `practice_scout` agent | Best practices + pitfalls | YES |
| the `docs_scout` agent | External documentation | YES |
| the `github_scout` agent | Cross-repo patterns via gh CLI | IF scouts.github |
| the `memory_scout` agent | Project memory entries | IF memory.enabled |
| the `spec_scout` agent | Dependencies on open specs | YES |
| the `docs_gap_scout` agent | Docs needing updates | YES |

**If user chose repo-scout (default/faster)** OR rp-cli unavailable:

Run ALL of these scouts in parallel:
| Scout | Purpose | Required |
|-------|---------|----------|
| the `repo_scout` agent | Grep/Glob/Read patterns | YES |
| the `practice_scout` agent | Best practices + pitfalls | YES |
| the `docs_scout` agent | External documentation | YES |
| the `github_scout` agent | Cross-repo patterns via gh CLI | IF scouts.github |
| the `memory_scout` agent | Project memory entries | IF memory.enabled |
| the `spec_scout` agent | Dependencies on open specs | YES |
| the `docs_gap_scout` agent | Docs needing updates | YES |

**Anti-pattern**: cherry-picking scouts *within a tier* "because they seem most relevant" — that judgment-skip causes incomplete plans. (This is distinct from the DEPTH tier above: dropping the web-research scouts on a user-chosen SHORT plan is a deterministic, user-signaled tradeoff, not a relevance guess.)

Must capture:
- File paths + line refs
- Existing centralized code to reuse
- Similar patterns / prior work
- External docs links
- Project conventions (CLAUDE.md, CONTRIBUTING, etc)
- Architecture patterns and data flow (especially with context-scout)
- Spec dependencies (from spec-scout)
- Doc updates needed (from docs-gap-scout) - add to task acceptance criteria
- DESIGN.md design system tokens (if repo-scout found one)

## Step 2: Stakeholder & scope check

Before diving into gaps, identify who's affected:
- **End users** — What changes for them? New UI, changed behavior?
- **Developers** — New APIs, changed interfaces, migration needed?
- **Operations** — New config, monitoring, deployment changes?

This shapes what the plan needs to cover. A pure backend refactor needs different detail than a user-facing feature.

## Step 3: Flow gap check

Run the gap analyst subagent:
- Use the flow_gap_analyst agent(<request>, research_findings)

Fold gaps + questions into the plan.

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

**Calibration (read first):** before writing task specs, read [`examples.md`](examples.md) — good/bad task-spec shapes, investigation-target formats, T-shirt sizing, and coverage-table examples. It is the few-shot anchor that keeps task specs well-sized and well-shaped; skipping it is why plans drift toward vague or over-split tasks.

**Efficiency note**: Use stdin (`--file -`) with heredocs to avoid temp files where a command accepts stdin. On the create path, `task create --description-file --acceptance-file --satisfies` writes the whole task spec (sections + frontmatter) in ONE call — no follow-up `task set-spec`. `task set-spec` remains the tool for editing tasks that already exist (Route A edits, interview write-backs, review fix loops).

**Route A - Input was an existing Flow ID**:

1. If spec ID (fn-N-slug or legacy fn-N/fn-N-xxx):
 ```bash
 # Use stdin heredoc (no temp file needed)
 $FLOWCTL spec set-plan <id> --file - --json <<'EOF'
 <plan content here>
 EOF
 ```
 - Create/update child tasks as needed

2. If task ID (fn-N-slug.M or legacy fn-N.M/fn-N-xxx.M):
 ```bash
 # Combined set-spec: description + acceptance in one call
 # Write to temp files only if content has single quotes — unique per-task paths
 # (path-persistence rule: literal agent-composed paths, never shared fixed names)
 $FLOWCTL task set-spec <id> --description "${TMPDIR:-/tmp}/flow-plan-desc-<task-id>.md" --acceptance "${TMPDIR:-/tmp}/flow-plan-acc-<task-id>.md" --json
 ```

**Route B - Input was text (new idea)**:

1. Create spec:
 ```bash
 $FLOWCTL spec create --title "<Short title>" --json
 ```
 This returns the spec ID (e.g., fn-1-add-oauth). `branch_name` defaults to the spec ID at create time — no follow-up `spec set-branch` call on the create path. Only when the user specified a custom branch, pass it at create: `$FLOWCTL spec create --title "<Short title>" --branch "<custom-branch>" --json` (`spec set-branch` remains the tool for renaming an existing spec's branch later).

2. Write spec (use stdin heredoc):

 The canonical scaffold lives in [`plugins/flow-next/templates/spec.md`](../../templates/spec.md) — section list, scope-owner annotations, and the `## Decision Context` flat-vs-H3 conditional. At runtime the template is resolved via the 4-tier discovery cascade (first match wins): `<repo_root>/SPEC.md` → `<repo_root>/spec.md` → `.flow/templates/spec.md` → bundled `${PLUGIN_ROOT}/templates/spec.md`. The bundled file is the canonical source of truth; earlier tiers are user-customized overrides. The full walker (case-insensitive FS probe, both-exist warning, plugin-root fallback) is single-sourced in [`plugins/flow-next/references/spec-template-discovery.md`](../../references/spec-template-discovery.md). Read the resolved template before authoring; never duplicate its section list inline. The plan skill extends that scaffold with the plan-specific sections shown below (Overview, Quick commands, Strategy Alignment, Strategy drift, Early proof point, Requirement coverage).

 ```bash
 # Include: Overview, Scope, Approach, Quick commands (REQUIRED),
 # Acceptance Criteria, Early proof point, Requirement coverage, References
 # Conditional sections: ## Strategy Alignment (when STRATEGY_PRESENT=true from Step 1),
 # ## Strategy drift flagged for review (when plan scope conflicts with an active track)
 # Add mermaid diagram if data model or architecture changes
 $FLOWCTL spec set-plan <spec-id> --file - --json <<'EOF'
 # Spec Title

 ## Overview
 ...

 ## Quick commands
 ```bash
 # At least one smoke test command
 ```

 ## Boundaries / non-goals
 - <what this spec explicitly does NOT cover>

 ## Strategy Alignment
 <!-- Include this section ONLY when STRATEGY_PRESENT=true from Step 1.
 When STRATEGY_PRESENT=false (no STRATEGY.md or husk: sections_filled == 0),
 skip this section entirely. -->

 Active tracks served by this plan:
 - **<track-name>** — <one line on how this plan advances the track>
 - **<track-name>** — <one line>

 <!-- If the plan serves no active strategy track, replace the bulleted list with: -->
 _No active strategy track served — review for drift._

 ## Strategy drift flagged for review
 <!-- Include this block ONLY when the plan scope conflicts with an active track.
 Mirrors plan-sync's "Decision overrides flagged for review" convention
 (agents/plan-sync.md). Read-only — the plan skill never auto-supersedes
 STRATEGY.md; the user (or `/flow-next:strategy`) decides whether to revise. -->

 - **<track-name>**: <one line on how this plan diverges from the track's stated direction>. Review for revision via `/flow-next:strategy`.

 ## Decision context
 - <why this approach over alternatives>

 ## Acceptance Criteria
 - **R1:** <testable criterion>
 - **R2:** <testable criterion>
 - **R3:** <testable criterion>

 ## Early proof point
 Task fn-N-slug.1 validates the core approach (<what it proves>).
 If it fails, re-evaluate <strategy> before continuing with fn-N-slug.2+.

 ## Requirement coverage

 | Req | Description | Task(s) | Gap justification |
 |-----|-------------|---------|-------------------|
 | R1 | <criterion from Acceptance Criteria> | fn-N-slug.1, fn-N-slug.2 | — |
 | R2 | <another criterion> | fn-N-slug.3 | — |
 | R3 | <deferred item> | — | Deferred to fn-M-slug |
 EOF
 ```

 **`## Strategy Alignment` rules (active iff STRATEGY_PRESENT=true from Step 1):**
 - Section sits between `## Boundaries / non-goals` and `## Decision context` in the template above.
 - List active tracks (`### <track-name>` blocks parsed from the strategy snapshot's `tracks` raw markdown string) that this plan advances.
 - When the plan serves NO active track, render the placeholder `_No active strategy track served — review for drift._` literally — do not omit the section.
 - Skip the entire section when STRATEGY_PRESENT=false. Husk-vs-presence: gated on `sections_filled >= 1`, NOT `[[ -f STRATEGY.md ]]`.

 **`## Strategy drift flagged for review` rules (conditional on conflict detection):**
 - Mirrors plan-sync's "Decision overrides flagged for review" surface (`agents/plan-sync.md` Phase 6 summary).
 - Bulleted list with track name + plan-decision divergence + `Review for revision via /flow-next:strategy.` line per item.
 - Read-only — the plan skill never edits STRATEGY.md, never marks a track superseded, never auto-supersedes anything. Surface for human review only.
 - Omit the heading entirely when no drift detected. Empty drift block is silent, not `_(none)_`.

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

 **R-ID rule (MANDATORY for new specs):**
 - Number acceptance criteria as `R1`, `R2`, `R3`, ... in creation order using the `- **Rn:** ...` prose prefix format shown in the template above.
 - Once a review cycle has run against an R-ID, **never renumber**. Reordering is fine (R1, R3, R5 after R2/R4 deletion is correct).
 - New criteria take the next unused number. Gaps are fine — do not compact.
 - R-IDs in `## Acceptance Criteria` and `## Requirement coverage` must match (same IDs, same meanings).
 - R-IDs are plain markdown prose, not YAML — the reviewer matches them via LLM reasoning, not strict parsing.

 **Source-tag consumption (Route A refine of a capture-authored spec):** `/flow-next:capture` tags each acceptance criterion with its provenance — `[user]` (verbatim), `[paraphrase]` (user-grounded), `[inferred]` (the agent filled a gap), `[strategy:<track>]`. capture invests real machinery in these *so plan can scrutinize them* — do not plan an `[inferred]` criterion as established fact. When the spec carries source tags:
 - `[user]` / `[paraphrase]` / `[strategy:*]` → user- or strategy-grounded; plan normally.
 - `[inferred]` → **unconfirmed**. Route it through the Step-1 scouts (does the codebase actually support/need it?). A scout-confirmed inference becomes a normal criterion (drop the tag); an **unconfirmed** one moves to `## Open Questions` (or renders as a `⚠️ unconfirmed inference` coverage-table row) rather than being silently planned as a requirement. This closes capture→plan: the provenance capture records is otherwise dropped at the one consumer built to read it.

3. Set spec dependencies (from spec-scout findings) — BOTH directions:

 ```bash
 # (a) FORWARD — the new plan depends on an existing spec (spec-scout "Dependencies"):
 $FLOWCTL spec add-dep <new-spec-id> <dependency-spec-id> --json

 # (b) REVERSE — an existing spec depends on the new plan (spec-scout "Reverse Dependencies").
 # MUST record these too: the edge belongs on the OTHER spec (it can't start until the new
 # plan lands). Dropping it leaves that spec falsely ready → pilot/backlog picks it up and
 # builds against infrastructure this plan hasn't shipped yet (silent, worst in autonomous mode).
 $FLOWCTL spec add-dep <other-spec-id> <new-spec-id> --json
 ```

 Report findings at end of planning (no user prompt needed):
 ```
 Spec dependencies set:
 - fn-N-slug → fn-2-add-auth (Auth): Uses authService from fn-2-add-auth.1 [forward]
 - fn-7-notify → fn-N-slug (Notifications): waits for the event system this plan adds [reverse]
 ```

4. Create child tasks — ONE `task create` call per task writes title, deps, description, acceptance, AND `satisfies:` frontmatter at create time (fn-110; zero follow-up `task set-spec` on the plan path):
 ```bash
 # For each task. Write description and acceptance to UNIQUE per-task temp files
 # (path-persistence rule: literal agent-composed paths; write + consume in one
 # bash block), then:
 $FLOWCTL task create --spec <spec-id> --title "<Task title>" \
 --deps <dep1>,<dep2> \
 --description-file "${TMPDIR:-/tmp}/flow-plan-desc-<task-id>.md" \
 --acceptance-file "${TMPDIR:-/tmp}/flow-plan-acc-<task-id>.md" \
 --satisfies R1,R3 --json
 ```

 Omit `--deps` for tasks with no dependencies, and `--satisfies` for tasks that advance no specific R-IDs. `--satisfies` takes a comma list of bare R-ID tokens (`R1,R3` — grammar `R[1-9][0-9]*[a-z]?`; duplicates and malformed tokens error before anything is written) and renders the `satisfies:` YAML frontmatter block. `task set-spec` is NOT part of the create path — it is for editing tasks that already exist.

 **TIP**: Use `--deps` to declare dependencies inline when creating tasks. Tasks must exist before being referenced, so create in dependency order.

 **Task spec content** (remember: NO implementation code):
 ```markdown
 ---
 satisfies: [R1, R3]
 ---

 ## Description
 [What to build, not how to build it]

 **Size:** S/M (L tasks should be split)
 **Files:** list expected files. Task files must carry the full contract - named files, named test cases, named acceptance - because downstream executors receive the task file AS the brief (plan-time knowledge reaches them through the task file, no other channel).

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
 - Validate paths exist at plan time (repo-scout/context-scout already found them)
 - "Required" = must read before implementing. "Optional" = helpful reference
 - Targets come from repo-scout/context-scout findings in Step 1

 **`satisfies` frontmatter rules (optional, additive):**
 - Populate `--satisfies` only when the task obviously advances specific R-IDs from the spec's `## Acceptance Criteria` section.
 - Tasks that do infrastructure, refactoring, shared plumbing, or docs-only work may legitimately have **no** `satisfies` entry — omit the flag entirely.
 - Use bare R-ID tokens (`--satisfies R1,R3`; rendered as `satisfies: [R1, R3]`), not quoted strings.
 - Frontmatter is additive — tasks created without it parse unchanged.

5. Add task dependencies (if not already set via `--deps`):

 **Preferred**: Use `--deps` flag during task creation (step 4). This saves prompt turns.

 **Alternative**: Use `dep add` to add dependencies after task creation:
 ```bash
 # Syntax: dep add <dependent-task> <dependency-task>
 # "task B depends on task A" → dep add B A
 $FLOWCTL dep add fn-N.2 fn-N.1 --json
 ```

 Use `dep add` when you need to add dependencies to existing tasks or fix missed dependencies.

 Do NOT re-fetch the spec after writing (no post-write `show`/`cat` — you just authored this state; Step 6 validates it, and pilot judges the plan stage from flowctl state, not this skill's stdout). The Step 7 fix-loop re-anchor is the deliberate exception.

## Step 6: Validate

```bash
$FLOWCTL validate --spec <spec-id> --json
```

Fix any errors before proceeding.

## Step 6.5: Tracker sync (opt-in) — NO sub-issues; optional body checklist only

**Optional. Runs only when the tracker bridge is active AND `plan` is opted in. With no tracker configured this is a no-op — planning behaves exactly as today.** When opted in, planning projects the spec to the tracker issue. **If the spec is not yet linked (e.g. you started straight from `/flow-next:plan`, no `/flow-next:capture`), the tracker-sync skill flow-first-pushes — it creates the issue + links it — then reconciles** (tracker-sync §Phase 3 "create-if-unlinked"); an active bridge therefore never silently leaves a planned spec untracked. Planning **never auto-creates tracker sub-issues per task** — tasks stay flow-local (R3, Grain); the spec ↔ one-issue grain holds. The only optional task-level effect is rendering the task list as a **checklist inside the issue body** (off by default; a body-format concern owned by the merge engine).

```bash
LEAF="$(jq -r '.value.tracker.perEvent.plan' "${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json" 2>/dev/null)" # leaf from the Step 0 root snapshot (shared gating predicate — work SKILL.md); missing → literal "null", same as the old per-key read
if [ "$($FLOWCTL sync active --json | jq -r '.active')" = "true" ] \
 && [ "$LEAF" != "off" ] && [ "$LEAF" != "null" ]; then
 # Invoke the flow-next-tracker-sync skill to push/reconcile the spec body
 # (which MAY render the task list as a body checklist — never sub-issues).
 # skill: flow-next-tracker-sync (operation: <leaf> <spec-id>)
 # Unlinked spec → flow-first push (create + link) first, then reconcile
 # (tracker-sync §Phase 3 create-if-unlinked). No-op only if no transport reachable.
 :
fi
```

**Never** create one tracker issue per task. The grain is one spec ↔ one issue; tasks are flow-local. Best-effort — a tracker failure never blocks planning.

## Step 7: Review (if chosen at start)

If user chose "Yes" to review in SKILL.md setup question:
1. Invoke `/flow-next:plan-review` with the spec ID
2. If review returns "Needs Work" or "Major Rethink":
 - **Re-anchor EVERY iteration** (do not skip):
 ```bash
 $FLOWCTL show <spec-id> --json
 $FLOWCTL cat <spec-id>
 ```
 - **Immediately fix the issues** (do NOT ask for confirmation — user already consented)
 - Re-run `/flow-next:plan-review`
3. Repeat until review returns "Ship"

**No human gates here** — the review-fix-review loop is fully automated.

**Why re-anchor every iteration?** Per Anthropic's long-running agent guidance: context compresses, you forget details. Re-read before each fix pass.

## Step 8: Offer next steps

Show spec summary with size breakdown and offer options:

```
Spec fn-N-slug created: "<title>"
Tasks: M total | Sizes: Ns S, Nm M

Next steps:
1) Start work: `/flow-next:work fn-N-slug`
2) Refine via interview: `/flow-next:interview fn-N-slug`
3) Review the plan: `/flow-next:plan-review fn-N-slug`
4) Go deeper on specific tasks (tell me which)
5) Simplify (reduce detail level)
```

If user selects 4 or 5:
- **Go deeper**: Ask which task(s), then add more context/research to those specific tasks
- **Simplify**: Remove non-essential sections, tighten acceptance criteria, merge small tasks

Loop back to options after changes until user selects 1, 2, or 3.

**On loop exit (user picked 1, 2, or 3):** run Step 8.5 BEFORE dispatching the chosen next step or finishing — never on first arrival at this menu. Options 4/5 mutate tasks; generating earlier would render a lens the user is still editing.

Under `AUTONOMOUS=1` there is no options menu — run Step 8.5 directly after Step 6/7 complete.

## Step 8.5: HTML render lens (opt-in) — regenerate the spec artifact with the plan layer

**Gated on `artifacts.html.enabled` — this check is the ONLY addition when the mode is off.**

```bash
HTML_LENS=$(jq -r 'if .value.artifacts.html.enabled == true then "true" else "false" end' "${TMPDIR:-/tmp}/flow-plan-config-<suffix>.json" 2>/dev/null || echo false) # from the Step 0 root snapshot — not a config get call
```

When `HTML_LENS != true` (off or unset): **skip this entire step.** Load no reference file, write no artifact, open no session, print no artifact-related output — the gate read above is the only cost.

When `HTML_LENS = true`:

1. **Load the disclosure reference** [`plugins/flow-next/references/html-artifacts.md`](../../references/html-artifacts.md) (relative cross-link — resolves from this skill dir in every install layout, same shape as the spec-template link). It owns ALL design and generation rules — hard rules, design contract, spec-lens content, DAG discipline, Lavish flow, pre-publish checklist. Never duplicate its rules here; follow it top to bottom.
2. **Regenerate the artifact** at the SAME fixed path capture uses (reference §1.3) — one pathway, state-dependent (reference §4): tasks now exist, so the lens renders the plan layer too (task dependency DAG with critical path, R-ID → task coverage matrix, plan dials).

 ```bash
 mkdir -p ".flow/artifacts/<spec-id>"
 # Host agent regenerates .flow/artifacts/<spec-id>/spec.html per the reference.
 ```
3. **Late-mutation rule:** if anything after this generation mutates tasks in the same plan session (e.g. the chosen option 3's `/flow-next:plan-review` fix loop, or the user re-opening go-deeper/simplify), regenerate before the final output — same path, never a second file.
4. **Update the artifact link line in the spec markdown** per reference §1.4: replace the `<!-- flow-next:artifact-link -->` marker line in place (capture usually wrote it; insert once after the H1 if absent). Link target follows ignore status (reference §4):

 ```bash
 if git check-ignore --no-index -q ".flow/artifacts/<spec-id>/spec.html"; then
 LINK_MODE=local # file ignored (dir, glob, or exact-path rule) → local-open guidance, never a blob link that 404s
 # --no-index: an already-tracked artifact still honors a later ignore rule
 else
 LINK_MODE=repo # tracked → repo-relative link
 fi
 # Idempotency check — exactly one marker line after EVERY run. Non-fatal
 # (best-effort contract below): warn and continue, never abort planning.
 MARKER_COUNT=$(grep -c 'flow-next:artifact-link' ".flow/specs/<spec-id>.md" || true)
 if [ "${MARKER_COUNT:-0}" -ne 1 ]; then
 echo "warn: artifact link line check failed (${MARKER_COUNT:-0} markers in .flow/specs/<spec-id>.md) — link needs manual fix" >&2
 fi
 ```
5. **Run the reference's pre-publish checklist (§8)**, including the self-containment self-check grep (§2) — it must print `OK: self-contained` before the output may claim the artifact.
6. **Lavish session — interactive runs only** (reference §7). The guard is in the snippet, not just prose — open and poll sit INSIDE it:

 ```bash
 LAVISH_OK=true
 [[ "${AUTONOMOUS:-0}" == "1" || -n "${FLOW_AUTONOMOUS:-}" || -n "${FLOW_RALPH:-}" || -n "${REVIEW_RECEIPT_PATH:-}" ]] && LAVISH_OK=false
 if [[ "$LAVISH_OK" == "true" ]] && command -v lavish-axi >/dev/null 2>&1; then
 lavish-axi "$(pwd)/.flow/artifacts/<spec-id>/spec.html" # absolute path — sessions key on it
 # ...then poll for feedback in the background via `lavish-axi poll` — ONLY inside this guard
 fi
 ```

 Each drained annotation maps to an edit of the spec/task markdown (never the HTML), then the lens regenerates at the same path. `lavish-axi` absent → plain artifact, zero mention of Lavish, never an error.

 **Non-interactive runs generate only** (any non-interactive marker: `AUTONOMOUS=1`, `FLOW_AUTONOMOUS=1`, `FLOW_RALPH=1`, `REVIEW_RECEIPT_PATH` set — treat the marker *family* as the gate, not a rigid var list; a marker the family implies but the snippet misses still means `LAVISH_OK=false`): never open a session, never poll; at most one stderr line noting pending prompts.
7. **Name the artifact in the final output:** append `Artifact: .flow/artifacts/<spec-id>/spec.html (render lens — regenerable; markdown is the record)` to the plan summary. Omit entirely when the mode is off/unset.

Best-effort: artifact generation failure is non-fatal — skip the link-line update, print one stderr note, never block planning (the plan is already on disk; markdown is the record).
