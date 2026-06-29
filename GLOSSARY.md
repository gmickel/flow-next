# Glossary

## Spec

The central artefact of flow-next: a specification at `.flow/specs/<id>.md` (markdown body) plus `.flow/specs/<id>.json` (metadata sidecar, post-1.0). Reviewable on its own; cross-model-reviewed; verifiable against prior handovers; frozen at handover. Replaces the term *epic* from the 0.x line.

## Ready

A human-owned boolean on the spec record (default `false`, toggled via `flowctl spec ready` / `spec unready`) marking a spec complete enough to hand to an agent — the entry gate autonomous loops consume. Orthogonal to `status` (`open|done`): a ready spec stays `open` through planning and work. Human-owned or tracker-projected (`tracker.readyState` pulls the configured tracker state onto the local flag, one-way), never agent-inferred. Opt-in and invisible until adopted: the flag is written lazily, non-adopters see no badge, prompts, or warnings anywhere.

## Task

An execution unit under a spec, sized to fit one `/flow-next:work` iteration (~100k tokens fresh context). Tasks declare dependencies (`requires:`) and may declare which spec acceptance criteria they advance (`satisfies: [R1, R3]`). Implemented by a worker subagent with re-anchored context.

## R-ID

A numbered acceptance criterion in a spec, format `**R1:** ...`, `**R2:** ...`. Renumber-forbidden after the first review cycle: deletions leave gaps, new criteria take the next unused number. R-IDs are the load-bearing identity of a requirement across the spec, the tasks that satisfy it, the commits that reference it, and the PR body coverage table.

## Handover object

A named, reviewable artefact that carries context across a step in the agentic SDLC. flow-next defines six handover states: the spec at business-layer completion (#1) and at full completion (#2) — both the **same** `.flow/specs/<spec-id>.md` file at successive layers, NOT two separate specs — then the implementation plan (#3), the working implementation (#4), the cross-model code review (#5), and the PR-as-cognitive-aid (#6). Each is reviewable on its own, cross-model-verified, and frozen at handover. The chain of handovers replaces the standups / refinement / design-review touchpoints that pre-agentic Agile relied on.

## Re-anchoring

Re-reading the spec, the task, and `git log` since branch base before each task starts. Counters context drift in long-running agent sessions per Anthropic guidance. Worker subagents re-anchor on every iteration; `/flow-next:work` re-anchors every loop turn.

## Cross-model review

A different model reviews the artefact produced by the first model. Applied at every handover. Backends: RepoPrompt (rp), Codex CLI (codex), GitHub Copilot CLI (copilot). The disagreement surface between writing model and reviewing model is where the gaps live.

## Feature map

The `.clawpatch/features/*.json` index produced by `clawpatch map` and consumed by flow-next scouts via `flowctl repo-map`. Semantic feature slices across ~20 languages/frameworks (Zod-validated upstream, `schemaVersion: 1`). Wrapped by the opt-in `/flow-next:map` skill; flow-next core (flowctl) never imports or requires clawpatch — when `.clawpatch/` is absent, scouts gracefully fall back to grep/glob.

## features_anchored

Optional scout output field listing feature slices from the feature map that overlap the current scope. Emitted by `repo-scout` and `context-scout` when `.clawpatch/features/*.json` is present; omitted when absent. Each entry carries a `last_mapped` timestamp so downstream skills can flag staleness (informational signal, not a block).

## Receipt

A JSON artefact that gates Ralph state transitions. `flowctl impl-review` writes a receipt at `.flow/review-receipts/<branch>.json` with verdict (`SHIP` / `NEEDS_WORK` / `MAJOR_RETHINK`), confidence anchors, introduced vs pre-existing finding counts, and the deferred / suppressed counts. Ralph reads receipts to decide loop progression.

## Worker subagent

A subagent dispatched by `/flow-next:work` to implement a single task with fresh context. Re-anchors the spec + task + git state, implements the task, records evidence (commits + tests + done summary), and exits. The fresh context per task is what enables N tasks to run in parallel without context-bleed.

## Carmack-level review

The strict cross-model review tier flow-next runs by default. References John Carmack review standard. Five confidence anchors (0/25/50/75/100) gate findings; `<75` suppressed except P0 @ 50+; introduced vs pre-existing classification means only introduced findings count toward the verdict.

## Triage skip

A deterministic whitelist pre-check that returns `SHIP` without invoking a review backend, for trivial diffs: lockfile-only / docs-only / release-chore / generated-file-only. `flowctl triage-skip` is the helper. On by default in Ralph mode; opt-out via `--no-triage` or `FLOW_RALPH_NO_TRIAGE=1`.

## PR-as-cognitive-aid

A structured PR body synthesizing nine flow-next state streams (spec with R-IDs, per-task done summary + evidence commits, decisions / bug / architecture-patterns memory, glossary changes, strategy alignment, deferred review findings, the diff itself) into a reviewable artefact. Body sections: TL;DR, R-ID coverage table, Critical changes, Decisions, Memory, Glossary/strategy deltas, Open items, Where to look. Produced by `/flow-next:make-pr`.

## Ralph

The flow-next hardened autonomous harness. External shell loop drives fresh Claude / Codex sessions per task with cross-model review gates, hook-enforced guardrails (ralph-guard / DCG), and receipt-based proof-of-work. Consumes **fully planned** specs only — it iterates plan-review -> work -> impl-review -> spec-completion-review until the spec ships or the iteration cap is hit; it never runs the planning fan-out (planning stays with the human or pilot). Differentiator from `ralph-wiggum`-style open-loop autonomous agents. The default autonomy path is the pilot + land pipeline; reach for Ralph when a run outlasts a session or prose guardrails aren't enough — Ralph owns the loop in a shell script, pilot hands the loop to the host's `/loop` / `/goal` primitives.

## Pilot

The single-tick build-loop conductor (`/flow-next:pilot`): one tick advances one ready spec by one pipeline stage (plan / plan-review / work / `[optional qa]` / make-pr — see [QA stage](#qa-stage-pipelineqa)) and ends with a terminal `PILOT_VERDICT` line; the host's `/loop` or `/goal` owns iteration. Signals autonomy to sub-skills via the `mode:autonomous` token + `FLOW_AUTONOMOUS=1` env (distinct from `FLOW_RALPH`; never activates ralph-guard). Selection consumes the fn-58 `ready` gate; two healthy no-advance ticks clear the spec's `ready` flag (don't-thrash). The default `ready` mode selects only already-ready specs; the opt-in [backlog mode](#backlog-mode-pilotautonomy) widens it to the whole open backlog.

## Backlog mode (`pilot.autonomy`)

Pilot's opt-in wide-autonomy behavior (fn-68), gated by config `pilot.autonomy ∈ {ready (default), backlog}` (per-run override `--backlog` / `--auto`; with the gate off, pilot is byte-for-byte unchanged and `references/backlog-mode.md` is never even read). A backlog tick **enumerates the full open set** — flow specs (`flowctl ready --all`) **plus** tracker issues at the promoted lane (`listOpenIssues`, unioned in by the skill) — selects the top **dep-ordered** actionable item, runs the [triage stage](#triage-stage-backlog-mode) in front of pilot's existing pipeline, and either advances it one stage (`plan → plan-review → work → [qa] → make-pr`) or parks it behind an [async question](#ask-stage--question-valve). It is a **leftward extension of the same single-tick conductor**, not a new skill or altitude: one `/loop`/`/goal` target, one verdict grammar, one mental model; the host primitive still owns repetition. The consent boundary moves from *before* the loop to *inside the loop, on block* — but the load-bearing boundaries hold: it **never authors a spec** (a thin/missing spec is surfaced as a "run `/flow-next:capture` or `/flow-next:interview`" gap, never auto-written), **never sets the `ready` flag** (promotion is the human's board act), and **never merges** (land stays human-gated). Readiness is the human's **explicit signal** (the fn-58 ready gate set OR tracker status exactly at `tracker.readyState`), never an agent-inferred completeness score — un-promoted backlog items are skipped silently.

## Triage stage (backlog mode)

The classify-and-route stage backlog mode runs **in front of** pilot's existing `classify`, on the selected item only. It reads the spec **agentically** (the host's judgment, never a flowctl-computed `triageClass`) and routes by *explicit state first*: **workable** (ready signal + complete spec) → select-and-advance (pilot's existing path); **ready-but-thin / ready-but-ambiguous** (signal present, spec missing or too thin to act on) → [`ask`](#ask-stage--question-valve) (kick back with the gap, never build, never auto-author); **dep-unsatisfied** → `BLOCKED <id> by <dep>` (a state-changing surface of the dep wait); **needs a human decision** → `ask`. A *live* triage always lands on a **state-changing terminal** (`ADVANCED` / `ASKED` / `BLOCKED` / `NEEDS_HUMAN`) so an item can never re-select forever; `TRIAGED <id> <class>` is **diagnostic / `--dry-run` only**. `needs-spec` is always a *promoted* item missing a workable spec — never an un-promoted idea, which is simply skipped.

## Ask stage / question valve

Backlog mode's **async human-in-the-loop valve** — "stuck" becomes a question, not a stall, and never an interactive `AskUserQuestion`. When it cannot safely proceed, the `ask` stage writes each Open Question behind a **stable anchor** `<!-- flow-next:question id=<hash> status=open -->` (`id` hashes **stable fields only** — `subjectId` + blocked-stage + reason code + question slug; the free-prose reason is *outside* the hash so rephrasing never duplicates) and surfaces it where the item lives: a **spec-backed** item parks via the spec's `## Open Questions` section **and** a projected tracker comment; a **tracker-only** item (no spec) parks in the tracker comment alone. Projection is transport-blind across GitHub / GitLab / Jira / Linear via tracker-sync's adapter; no transport ⇒ spec-only (when a spec exists) + a one-line "enable X to mirror" note, never a block. Selection **skips any item carrying a `status=open` parked question**, so it is never re-picked. A human answer (flipping the spec anchor to `status=answered`, or a tracker reply carrying `<!-- flow-next:answer id=<hash> -->` matched by `id`) makes the next tick re-triage and proceed. Terminal verdict: `ASKED <id> (<n>)` — a durable park.

## Decision log (`pilot-log`)

The per-tick **factory-metrics substrate** backlog mode writes (fn-68) via `flowctl pilot-log append --id <id> --action <triaged|advanced|asked|blocked|needs-human> --stage <stage|-> [--cost-tokens <n>]`, summarized by `flowctl pilot-log summary --json` → `{tick, id, action, stage, costTokens}` rows. The action enum is **aligned to the verdict grammar**; token cost is **host-reported** (omitted/null when unavailable) — flowctl only stores the row, never measures cost. Rows yield the efficiency readout (% moved with no question / one async answer / parked, and cost per change) and are the substrate a future self-improvement-synthesis spec mines. Stored under `.flow/pilot-runs/` (a sync-runs-style dir, auto-gitignored) — deliberately **NOT** any `receipts/` path the ralph-guard validates.

## Land

The cadence-tick ship loop (`/flow-next:land`): one tick discovers the open PRs the build loop authored (spec `branch_name` match AND the make-pr breadcrumb — both signals required), walks each through the gate tree (CI tri-state over ALL checks, patience window anchored to the last push, resolve-pr convergence, `land.reviewSignal`), and takes at most one action class per PR — CI fix, resolve dispatch, mechanical rebase, or the gated explicit merge (`gh pr merge --squash --match-head-commit`, never `--auto`) plus the post-merge tail (spec close → tracker touchpoint → release-follow). The one confined exception to the no-auto-merge rule; `/loop`-shaped where pilot is `/goal`-shaped. Ends with a terminal `LAND_VERDICT` line.

## QA stage (`pipeline.qa`)

The optional live-app QA pass `/flow-next:qa`, graduated into a config-gated pilot stage (`pipeline.qa`, default **off**). When on, pilot runs one live pass over the complete build at all-tasks-done — `plan -> plan-review -> work -> **qa** -> make-pr` — driving the app the dev already has running during `work`. **Evidence-aware** (subtracts only AC a deterministic re-runnable check already proved; always live-runs every runtime / UI / integration criterion because the worker's self-report is narration, not captured evidence), **surfaced not blocking** (routes on `qa_outcome`, NOT the Ralph-guard `verdict` projection — `SHIP`/`NA`/`BLOCKED` advance, `NEEDS_WORK` still advances to the **draft** PR with findings in a `## Live QA` section + the bug-memory track + a tracker comment), and **augments, never replaces** CI / staging / manual QA. Net-new is one config-key default plus additive `qa_verdict` receipt fields (`head_sha` / `rid_coverage` / `open_p0p1`) — no new flowctl subcommand, no persisted test-case artefact. Idempotent per branch head via the receipt's `head_sha`. See `skills/flow-next-qa/SKILL.md` (fn-72).

## Verdict

The structured tick outcome a loop skill prints for transcript-blind drivers, always the last line of a tick. Pilot: `PILOT_VERDICT=<ADVANCED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason="<one line>"`; [backlog mode](#backlog-mode-pilotautonomy) **adds `ASKED <id> (<n>)`** (a durable park) and keeps every existing terminal verbatim (drivers grep `DEFERRED_TO_LAND` for the land hand-off, stop on `NO_WORK`); `TRIAGED <id> <class>` is diagnostic / `--dry-run` only, never a live terminal. Land: `LAND_VERDICT=<MERGED|RELEASED|FIXING_CI|AWAITING_REVIEW|RESOLVING|BLOCKED|NEEDS_HUMAN|NO_WORK> prs=<n> pr=<deciding-pr-url|-> reason="<one line>"` (tick verdict = worst severity across PRs). Autonomous resolve-pr runs end with `RESOLVE_PR_VERDICT=<RESOLVED|PENDING|NEEDS_HUMAN> threads=<n> fixed=<n> needs_human=<n>`, which land gates on. Distinct from a review receipt (Ralph's file-based proof-of-work): a verdict lives in the conversation output because `/goal` validators read the transcript, never the filesystem.

## Spec-as-PR

A team workflow where the spec is opened as a draft PR for review BEFORE any code lands. Reviewing a 50-line spec is higher-leverage than reviewing a 500-line implementation. Once merged, the spec is frozen on main; implementation PRs reference the merged spec.

## Frozen-at-handover

The R-ID invariant. Once a spec has been reviewed once, R5 means the same thing forever. A reviewer reading R5 in a six-month-old commit, a new team member reading R5 in the spec, and `/flow-next:make-pr` emitting R5 coverage all refer to the same acceptance criterion. Renumber-forbidden after first review cycle.

## flow-swarm

An in-progress companion product to flow-next that reads `.flow/specs/` directly to coordinate parallel agents across worktrees and consume `/flow-next:make-pr` output. The on-disk layout flow-swarm expects is what fn-43 (epic->spec rename) produces. Reference target for the v1.0 migration carrot.

## Tracker

An external issue tracker (Linear, GitHub Issues, GitLab, or Jira) that flow-next *projects* a spec to via `/flow-next:tracker-sync`. The tracker is a **co-editable mirror** — body, status, and comments sync two-way — but it is **projection, not coordination**: the `.flow/specs/<id>.md` spec stays the source of truth and the quality layer, and the tracker never drives flow state or spawns agents. Distinct from `/flow-next:sync` (plan-sync). Contrast OpenAI Symphony, where the tracker *is* the control plane.

## merge-base snapshot

The common-ancestor body the tracker-sync 3-way merge compares against — a **paired** snapshot taken at the last sync point: both a flow-form body and a tracker-form body, plus content hashes (the echo fence). Stored in the spec-JSON `tracker` block (`mergeBaseFlow` / `mergeBaseTracker` / `baseHashFlow` / `baseHashTracker`) and written atomically as a unit (a one-sided update is rejected, so neither half pins to a stale sync point). Advances with `lastSyncedAt` on a real reconcile, never on a no-op echo.

## discovery ceremony

The detect → surface → ask → never-assume flow `/flow-next:tracker-sync` runs before enabling the bridge. It probes six signals (Linear MCP, `LINEAR_API_KEY`, GitHub auth, GitLab auth/`GITLAB_TOKEN`, Jira REST + token — `JIRA_BASE_URL` plus Cloud `JIRA_EMAIL`+`JIRA_API_TOKEN` or DC/Server `JIRA_PAT`), surfaces what is present *and* absent, asks the user, and writes `tracker.*` config **only on confirmation**, with provenance. No signal ⇒ nothing written; the bridge stays off. Resolution model is env > config > ask (mirrors `flowctl review-backend`).

## tracker-key handle

A tracker identifier (e.g. `WOR-17`) used as a **resolvable flow id**, the hybrid id model. **Tracker-first** specs are canonically `wor-17-slug` (tasks `wor-17-slug.M`); bare `wor-17` / `wor-17.M` resolve as aliases. **Flow-first** specs keep `fn-NN-slug` and store `WOR-17` in `tracker.identifier` as a resolvable display alias. Resolution is case-insensitive (`show wor-17`, `work wor-17` resolve); the native `fn-` scheme is reserved (`fn-N` allocation counts `fn-*` only); one tracker team per repo; **ids never rename** on link.

## dependency projection

Tracker-sync's projection of a spec's local `depends_on_epics` edges into **tracker issue relations** (fn-64) — a `depends_on_epics` edge between two linked specs becomes a **blocked-by** relation between their issues (Linear native relations / GitHub native dependencies / GitLab native `is_blocked_by` issue links / Jira native "is blocked by" issue links — directional and universally available, no licence gate, no `flow:deps` block — else, for GitHub's reduced rung and GitLab on every tier, a provenance-fenced `<!-- flow:deps -->` body block). The relations counterpart to body/status/comments sync: projection, not coordination — flow stays authoritative, the tracker never declares deps back. Runs through the transport-blind `projectDepRelations` hook + the normalized `setIssueRelation` / `listIssueRelations` adapter pair; idempotent via read-before-write. No transitive/graph expansion — only direct edges project.

## provenance ledger

The per-spec `depRelations` list (in the `.flow/specs/<id>.json` `tracker` block, atomic write) that records **which** dependency relations tracker-sync created — so projection is idempotent and removals are provably-ours-only. Each entry is `{key, dep_spec, from_tracker_id, to_tracker_id, type, source, updatedAt}`, where `key` is an opaque hash of the directed issue pair (never a raw issue key inline — trackers auto-linkify keys even inside HTML comments). A relation **not** in the ledger (native trackers) / **outside** the `<!-- flow:deps -->` fenced block (GitHub's fenced fallback; GitLab's block on every tier) is never removed: a human's manual relation is safe by construction. Mirrors the merge-base hash-provenance shape, minus its paired-snapshot constraint.

## completed-blocker rule

The tracker-sync semantics for a dependency whose **local** dep spec is `done` (→ its issue Done/Closed): the projected blocked-by relation stays **visible** on the tracker (preserving the real historical ordering on the board) but does **NOT** feed back into Flow `ready=true` gating — readiness already treats done deps as satisfied, and dependency projection must not regress that. Keys off the *local* dep-spec status (flow is authoritative), never a remote fetch.

## render lens

A regenerable human-review artifact (HTML) derived from a markdown source of truth; never the storage format, always re-derivable. flow-next ships two: the spec artifact and the PR artifact, both living at fixed deterministic paths under `.flow/artifacts/<spec-id>/` (never timestamped — Lavish keys annotation sessions on the absolute path). Every lens is self-contained single-file HTML (inline CSS/JS, zero external requests), carries a staleness stamp in its footer, and is never parsed back as state — regeneration always overwrites the same file.

## HTML artifact mode

The opt-in feature (2.0.0+) that makes participating skills (capture, plan, make-pr) emit render lenses alongside their markdown output. Activated via `flowctl config set artifacts.html.enabled true` (OFF by default, offered once by `/flow-next:setup`); when active, skills load the shared disclosure reference at `plugins/flow-next/references/html-artifacts.md` — the single carrier of all generation rules and the anti-slop design contract. With the mode off, skills load nothing extra: zero token cost, zero behavior change. Markdown and tracker-sync remain the sole source of truth.

## spec artifact

The spec's render lens at `.flow/artifacts/<spec-id>/spec.html`. ONE generation pathway with state-dependent rendering: spec-only view before tasks exist (capture workflow §5.10 — the business-review surface) and the added plan layer (task dependency DAG with critical path, R-ID → task coverage matrix) once tasks exist (plan Step 8.5 — after the refinement loop exits). Links back from the spec markdown via the idempotent `<!-- flow-next:artifact-link -->` marker line (replaced in place, repo-relative target). The only artifact that enters the Lavish annotate loop.

## PR artifact

The PR's render lens at `.flow/artifacts/<spec-id>/pr.html`, emitted by `/flow-next:make-pr` Phase 1.5. A **read-only review instrument**: diff-derived (never from commit messages), verified against the spec's R-ID export before publishing — mismatches render as visibly flagged rows, warn-in-artifact, never blocking. Committed narrowly (`chore(flow): pr artifact <spec-id>`, artifact file only) so the PR body's SHA-pinned blob link resolves; never enters the annotate loop — review conversation belongs to the code host.

## Lavish (lavish-axi)

An optional detect-on-PATH companion (npm: `lavish-axi`) for annotating spec artifacts in the browser — never wrapped, bundled, or required (same shape as clawpatch/`/flow-next:map`). Feedback is pull-only and session-spanning: annotations queue in the global `~/.lavish-axi/state.json` (not per-workspace), survive agent death, and any later agent session drains them via the `lavish-axi poll` CLI, mapping each annotation to a markdown-source edit followed by lens regeneration. Sessions key on the absolute artifact path (different worktrees = separate sessions); the local server idle-stops after ~30 min and `lavish-axi <file>` resumes it — absence or idle-stop is invisible because the artifact is a self-contained static page. Autonomous contexts never open a session and never poll.
