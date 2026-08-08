# Glossary (archived full text)

> Archived 2026-08-09, superseded by the root [`GLOSSARY.md`](../../GLOSSARY.md) vocabulary dictionary; kept for reference, not maintained.

## Spec

The central artefact of flow-next: a specification at `.flow/specs/<id>.md` (markdown body) plus `.flow/specs/<id>.json` (metadata sidecar, post-1.0). Reviewable on its own; cross-model-reviewed; verifiable against prior handovers; frozen at handover. Replaces the term *epic* from the 0.x line.

## Ratchet, not a gate

The doctrine governing what a spec is *for*. A gate decides what you are allowed to do next; a ratchet only stops you sliding back. No spec is required before reading code, prototyping, spiking, or researching — the spec exists so that what the exploration established cannot be silently lost by the next stage, the next person, or the next agent. Distinguishes flow-next from waterfall, which has three properties flow-next lacks: irreversible phases, a plan frozen at minimum knowledge, and lossy handovers. Spec-first asks for more *thought* earlier than a loose ticket does; it does not ask for more *commitment* earlier.

## Prototype-driven capture

Building a deliberately throwaway artefact to answer a design question, then capturing a spec **from** it (`"capture a spec from this prototype — ignore the code quality, I want the intent and the requirements it demonstrates"`). Inverts the assumption that the spec precedes the building. The prototype's *code* fate is a separate decision made at the plan stage against architecture and standards: throwaway evidence, reusable presentation layer, or implementation seed. Scales to variant generation — three radically different takes, react to all three, converge on a fourth — where the rejected options are recorded as evidence rather than discarded.

## Fidelity

How concrete an artefact must be before a question can actually be answered, and therefore the decision rule for when to prototype. Low-fidelity questions ("should the modal have cancel and confirm?") resolve in discussion. High-fidelity questions ("how should this look?", "how should this behave?", "does this state model survive the awkward cases?") resolve only against something running. Fidelity costs tokens, so buy it where being wrong is expensive. A *logic* prototype — a small interactive harness pushing a state machine through hard cases — is the high-fidelity form for backend work; prototyping is not a front-end-only tool.

## Briefing package

A half-formed markdown artefact carrying domain knowledge, product intent, and early technical thinking without being fully worked out - a valid capture input. Two production paths share the same handoff shape:

1. **Cross-functional session** (product, BA, engineering, quality): the group builds the briefing together; interview then challenges it for missing edge cases and unstated decisions instead of the group trying to be exhaustive in a meeting.
2. **Chart exit** (`/flow-next:chart` -> `flowctl chart briefing`): an immutable, versioned package (`B1`, `B2`, ...) under `.flow/charts/` that preserves Outcome, the full decision ledger (including superseded), boundaries, and approved evidence references. Capture ingests it as attributable evidence (chart id, B-ID, cluster, D-ID links, assets), applies normal read-back and source tags only to acceptance criteria it newly authors, then records the link via `chart link-spec`. Draft or forced briefings are never silently capture-ready. A `chart reopen` stales every existing package; the re-brief that follows mints the next B-ID rather than reinstating a staled one (a reopen is a new epoch), so the reversal stays in the ledger and the reopened chart keeps a path to capture.

Capture is the chart handoff into `.flow/specs/`; chart never writes a spec itself.

_Relates to_: Chart, Decision record, D-ID, Supersession

## Chart

A git-native pre-capture decision map for **one oversized or unclear idea** that is too large for a single capture session. Lives at `.flow/charts/<chart-id>.md` + `.json` with child decision records under `.flow/charts/<chart-id>/`. Chart ids share the native `fn-N` allocation domain with specs (one cross-kind counter; a chart and a spec never share an id). Status is `open | done | abandoned`. The unit of work is a **decision** (D-ID), not a build task: plan decomposes work that is already understood; chart makes an effort understandable enough to be worth planning. Optional - skip when intent and boundaries are already stateable and go straight to capture. Never writes under `.flow/specs/` and never sets `ready`; output is a [briefing package](#briefing-package) for `/flow-next:capture`. Prompt-first adaptive loop (ground -> choose one frontier decision -> evidence route -> record -> re-chart); no fixed discovery phase order. Distinct from prospect (plural ranked ideas) and from plan (task decomposition of a ready spec).

_Relates to_: Decision record, D-ID, Frontier (chart), Briefing package, Supersession

## Decision record

One child of a chart: a question whose resolution settles something before build. Body is deliberately minimal (`## Question` only) at `.flow/charts/<chart-id>/<n>.md` with a JSON sidecar holding type, attendance, status, graph edges, claim, answer, assets, and transition notes. Types are the evidence-first routes: `research | probe | eval | prototype | interview | task`. Attendance is derived for five types (`research|probe|eval` -> unattended; `prototype|interview` -> attended); `task` states it explicitly. Status: `open | resolved | superseded | out-of-scope`. Sized to one worker context (~100k tokens), same budget as a task. D-ID/evidence provenance is structural and distinct from acceptance-criterion author tags (`[user]` / `[paraphrase]` / `[inferred]` / `[strategy:<track>]`).

_Relates to_: Chart, D-ID, Supersession, Briefing package

## D-ID

A numbered decision identity under a chart, format `D1`, `D2`, ... locally and canonical external form `<chart-id>.D<n>` (e.g. `fn-140.D2`). Follows the R-ID discipline exactly: allocated sequentially from D1, append-only, never renumbered, never reused; removal or supersession leaves a gap. Load-bearing identity across the ledger, dependent records, the briefing, and the eventual spec that cites it. Human-facing surfaces always pair a D-ID with the decision title and record link.

_Relates to_: Decision record, Chart, R-ID

## Frontier (chart)

Open, unblocked, unclaimed decisions on a chart - the ready set for `/flow-next:chart` work mode. Returned by `flowctl chart frontier <chart-id>`, dependency-ordered; sole selection input for work mode. Same word and shape as the **task frontier** that `/flow-next:work` uses for ready tasks under a planned spec, but a different unit: chart frontier is decisions (D-IDs) that still need judgment or evidence before capture; task frontier is implementation units (`fn-N.M`) that still need a worker. An empty chart frontier is not completion by itself - a chart is briefable only when no open decisions remain (blocked, unblocked, or claimed) and `## Open Questions` is empty.

_Relates to_: Chart, Decision record, D-ID, Task

## Supersession

How a later chart decision invalidates an earlier resolved one without editing history. Resolved decisions are immutable (change history, not a wiki). `flowctl chart resolve <id>.D<n> --supersedes D3` closes the new answer, flips D3 to `superseded`, rewrites D3's ledger line as struck-through with a pointer to the superseding D-ID (line never removed), and walks the `depends_on` closure: open dependents lose claims and receive a premise-invalidated note; resolved dependents keep their records and gain replacement D-IDs for re-evaluation. `--keep-dependents` suppresses the cascade when the dependency was incidental and records that judgment. Superseded decisions appear in the briefing under their own section - the reversals discovery actually paid for.

_Relates to_: Chart, Decision record, D-ID, Briefing package

## Ready

A human-owned boolean on the spec record (default `false`, toggled via `flowctl spec ready` / `spec unready`) marking a spec complete enough to hand to an agent — the entry gate autonomous loops consume. Orthogonal to `status` (`open|done`): a ready spec stays `open` through planning and work. Human-owned or tracker-projected (`tracker.readyState` pulls the configured tracker state onto the local flag, one-way), never agent-inferred. Opt-in and invisible until adopted: the flag is written lazily, non-adopters see no badge, prompts, or warnings anywhere.

## Task

An execution unit under a spec, sized to fit one `/flow-next:work` iteration (~100k tokens fresh context). Tasks declare dependencies (`requires:`) and may declare which spec acceptance criteria they advance (`satisfies: [R1, R3]`). The dependency graph forms execution waves: tasks in the same wave are candidates for parallel work, not a mandate to share a checkout. Implemented by a worker subagent with re-anchored context.

## R-ID

A numbered acceptance criterion in a spec, format `**R1:** ...`, `**R2:** ...`. Renumber-forbidden after the first review cycle: deletions leave gaps, new criteria take the next unused number. R-IDs are the load-bearing identity of a requirement across the spec, the tasks that satisfy it, the commits that reference it, and the PR body coverage table.

## Global criterion (G-ID)

A numbered standing, project-wide acceptance criterion in the user-owned `.flow/criteria.md`, format `- **G1:** ...` - the R-ID grammar with a `G` prefix, lifted from one spec to the whole project. Parsed and validated by `flowctl criteria list` (unique ids, non-empty prose, gaps allowed); judged agentically by the existing spec completion review, which records per-criterion compliance (`met` / `violated` / `n/a`) in the ordinary review receipt's additive `criteria: [{id, status, note?}]` array - no separate auditor, no rule engine. The spec is the unit of compliance; G-IDs are stable identity like R-IDs (never renumber). Absence of the file is a silent no-op everywhere: criteria-less repos pay zero prompt content. Like structured findings (fn-136, see the flow-swarm preparation track in STRATEGY.md), the compliance record is a portable receipt contract that downstream consumers such as flow-swarm can render without importing Flow-Next internals.

_Relates to_: R-ID, Receipt

## Handover object

A named, reviewable artefact that carries context across a step in the agentic SDLC. flow-next defines six handover states: the spec at business-layer completion (#1) and at full completion (#2) — both the **same** `.flow/specs/<spec-id>.md` file at successive layers, NOT two separate specs — then the implementation plan (#3), the working implementation (#4), the cross-model code review (#5), and the PR-as-cognitive-aid (#6). Each is reviewable on its own, cross-model-verified, and frozen at handover. The chain of handovers replaces the standups / refinement / design-review touchpoints that pre-agentic Agile relied on.

## Re-anchoring

Re-reading the spec, the task, and `git log` since branch base before each task starts. Counters context drift in long-running agent sessions per Anthropic guidance. Session-scope: `flowctl brief` is the cold-session re-anchor (one budgeted call: open specs, ready tasks, recent completions, memory index). Task-scope: worker subagents re-anchor on every iteration via a single `flowctl anchor <task-id>` call — one deterministic bundle carrying, verbatim, the same information the discrete reads delivered (task + spec records and bodies, git state, memory/glossary indices, dependency done-summaries); the bundle is a floor, not a ceiling. `/flow-next:work` re-anchors every loop turn.

## Cross-model review

A different model reviews the artefact produced by the first model. Applied at every handover. Backends: RepoPrompt (rp - eligibility-probed, macOS/CLI-gated), Codex CLI (codex), GitHub Copilot CLI (copilot), Cursor `cursor-agent` CLI (cursor), and host-native (host - a fresh read-only subagent pinned to a different model family, no external CLI; fn-123). The disagreement surface between writing model and reviewing model is where the gaps live.

## Feature map

The `.clawpatch/features/*.json` index produced by `clawpatch map` and consumed by flow-next scouts via `flowctl repo-map`. Semantic feature slices across ~20 languages/frameworks (Zod-validated upstream, `schemaVersion: 1`). Wrapped by the opt-in `/flow-next:map` skill; flow-next core (flowctl) never imports or requires clawpatch — when `.clawpatch/` is absent, scouts gracefully fall back to grep/glob.

## features_anchored

Optional scout output field listing feature slices from the feature map that overlap the current scope. Emitted by `repo-scout` when `.clawpatch/features/*.json` is present; omitted when absent. Each entry carries a `last_mapped` timestamp so downstream skills can flag staleness (informational signal, not a block).

## Receipt

A review-layer JSON artefact that gates workflow state transitions. It carries a verdict (`SHIP` / `NEEDS_WORK` / `MAJOR_RETHINK` / `NEEDS_HUMAN`), confidence and classification evidence, and may carry the optional versioned [`findings`](../../plugins/flow-next/docs/review-findings.md) projection. `NEEDS_HUMAN` records a reviewer request for human adjudication; its receipt and status persist before the workflow exits with `ESCALATE:`. The receipt and original reviewer prose remain authoritative handover evidence when that additive projection is absent, stale, invalid, or unsupported. A Green receipt is the gate-layer counterpart, not a review-layer receipt; the sidecar bookkeeping that gates transitions is the Attempts ledger.

_Relates to_: Green receipt, Attempts ledger

## Attempts ledger

The `review_attempts[]` array on the spec sidecar - one row per finalized review reservation (backend, outcome, verdict, output hash, and best-effort the `head_sha` the review observed). The authoritative record of review state: `plan_review_status` / `completion_review_status` are a denormalized read model derived from it, and when the two diverge the ledger wins (issue #279). In-process plan/impl finalize writes attempt + status + SHIP cap reset as one atomic sidecar write; completion review deliberately orders receipt persistence before terminal status (recovery contract), so there the pair is two writes with the ledger authoritative. Full contract: `docs/architecture.md` § Review bookkeeping.

_Relates to_: Receipt, Verdict

## Structured finding

A versioned, portable projection of one issue reported in review prose. Its durable `id` survives review rounds; canonical severity (`P0`-`P3`), confidence, classification, and status values make it renderable without Markdown regexes; an optional anchor binds a safe repository-relative line range to reviewed base/head snapshots. Finding currentness comes only from one unambiguous, head-current receipt lineage tip. Memory may preserve the lesson from a fixed finding, but it never owns the finding's status.

_Relates to_: Receipt, R-ID, Carmack-level review

## Green receipt

The gate-layer counterpart introduced by fn-102: a per-file JSON record at `.flow/tmp/green-receipts/<sha8>-<gate_id>.json` (`{schema, head_sha, gate_id, command_sha256, timestamp}`) proving one exact full-gate command passed at one exact commit. `flowctl gate check` honors an exact full-HEAD match, or an eligible ancestor receipt whose canonical commit SHA, filename SHA, command fingerprint, age, clean worktree, and intervening two-dot diff all satisfy the receipt-only `.flow/**` minus `.flow/bin/**` minus `.flow/config.json` ignore set; otherwise the caller runs the full gate, fail-closed. Skips are always loud (`GATE_SKIPPED:` evidence lines and `Gates:` summary lines). Predicates are purely mechanical: hash, path, and age, never semantic; local gates only, never CI.

_Relates to_: Triage skip, Receipt

## Harden (audit outcome)

The sixth `/flow-next:audit` outcome (fn-122), alongside Keep / Update / Consolidate / Replace / Delete: graduating a memory entry that is correct, **recurring**, and **mechanizable** into an enforced gate — a lint rule, a CI step, or a rule in the substantive `CLAUDE.md` / `AGENTS.md`. The gate is verified live before the lesson is retired; only then is the entry demoted via `flowctl memory mark-hardened` to `status: hardened` with `hardened_into` pointing at the gate. The file stays on disk as a pointer, so provenance survives, and default `memory list` / `search` / `memory-scout` stop surfacing it — the gate enforces the lesson instead of the context window. `flowctl memory mark-fresh` un-graduates when the gate is later removed. Not security hardening; not a synonym for stale. Precedence: correctness (Replace / Delete) > Consolidate > Harden.

_Relates to_: Receipt, Verdict

## Worker subagent

A subagent dispatched by `/flow-next:work` to implement a single task with fresh context. Re-anchors on the spec + task + git state (one `flowctl anchor` bundle — same information as the old discrete reads, one call), implements the task, records evidence (commits + tests + done summary), and exits. In a parallel wave, each worker uses an isolated mutable workspace and returns task-unique handover files; the conductor joins and integrates the wave before review, completion, tracker updates, and plan-sync. Fresh context prevents context bleed. Atomic claims prevent duplicate ownership. Neither substitutes for filesystem and Git isolation.

## Carmack-level review

The strict cross-model review tier flow-next runs by default. References John Carmack review standard. Five confidence anchors (0/25/50/75/100) gate findings; `<75` suppressed except P0 @ 50+; introduced vs pre-existing classification means only introduced findings count toward the verdict.

## Triage skip

A deterministic whitelist pre-check that returns `SHIP` without invoking a review backend, for trivial diffs: lockfile-only / docs-only / release-chore / generated-file-only. `flowctl triage-skip` is the helper. Runs by default on every impl-review invocation (any mode); opt-out via `--no-triage` or `FLOW_RALPH_NO_TRIAGE=1`.

## PR-as-cognitive-aid

A structured PR body synthesizing nine flow-next state streams (spec with R-IDs, per-task done summary + evidence commits, decisions / bug / architecture-patterns memory, glossary changes, strategy alignment, deferred review findings, the diff itself) into a reviewable artefact. Body sections: TL;DR, R-ID coverage table, Critical changes, How to review this PR (trust-calibration coaching block), Review plan (every changed area risk-bucketed into Must review / Spot-check / Safe to skim with a ≤~30% focus budget), Decisions, Memory, Glossary/strategy deltas, Open items. Produced by `/flow-next:make-pr`.

## Ralph

The flow-next hardened autonomous harness. External shell loop drives fresh Claude / Codex sessions per task with cross-model review gates, hook-enforced guardrails (ralph-guard / DCG), and receipt-based proof-of-work. Consumes **fully planned** specs only — it iterates plan-review -> work -> impl-review -> spec-completion-review until the spec ships or the iteration cap is hit; it never runs the planning fan-out (planning stays with the human or pilot). Differentiator from `ralph-wiggum`-style open-loop autonomous agents. The default autonomy path is the pilot + land pipeline — Ralph owns the loop in a shell script, pilot hands the loop to the host's `/loop` / `/goal` primitives. **Deprecated**: a script calling pilot + land under a host loop or `cron` covers the same ground without the scaffold, the guard hooks, or the second receipt plumbing. Nothing is removed and existing installs keep working; new setups should use pilot + land.

## Pilot

The single-tick build-loop conductor (`/flow-next:pilot`): one tick advances one ready spec by one pipeline stage (plan / plan-review / work / `[optional qa]` / make-pr — see [QA stage](#qa-stage-pipelineqa)) and ends with a terminal `PILOT_VERDICT` line; the host's `/loop` or `/goal` owns iteration. Signals autonomy to sub-skills via the `mode:autonomous` token + `FLOW_AUTONOMOUS=1` env (distinct from `FLOW_RALPH`; never activates ralph-guard). Selection consumes the fn-58 `ready` gate; two healthy no-advance ticks clear the spec's `ready` flag (don't-thrash). The default `ready` mode selects only already-ready specs; the opt-in [backlog mode](#backlog-mode-pilotautonomy) widens it to the whole open backlog.

## Backlog mode (`pilot.autonomy`)

Pilot's opt-in wide-autonomy behavior (fn-68), gated by config `pilot.autonomy ∈ {ready (default), backlog}` (per-run override `--backlog` / `--auto`; with the gate off, pilot is byte-for-byte unchanged and `references/backlog-mode.md` is never even read). A backlog tick **enumerates the full open set** — flow specs (`flowctl ready --all`) **plus** tracker issues at the promoted lane (`listOpenIssues`, unioned in by the skill) — selects the top **dep-ordered** actionable item, runs the [triage stage](#triage-stage-backlog-mode) in front of pilot's existing pipeline, and either advances it one stage (`plan → plan-review → work → [qa] → make-pr`) or parks it behind an [async question](#ask-stage--question-valve). It is a **leftward extension of the same single-tick conductor**, not a new skill or altitude: one `/loop`/`/goal` target, one verdict grammar, one mental model; the host primitive still owns repetition. The consent boundary moves from *before* the loop to *inside the loop, on block* — but the load-bearing boundaries hold: it **never authors a spec** (a thin/missing spec is surfaced as a "run `/flow-next:capture` or `/flow-next:interview`" gap, never auto-written), **never sets the `ready` flag** (promotion is the human's board act), and **never merges** (land stays human-gated). Readiness is the human's **explicit signal** (the fn-58 ready gate set OR tracker status exactly at `tracker.readyState`), never an agent-inferred completeness score — un-promoted backlog items are skipped silently.

## Triage stage (backlog mode)

The classify-and-route stage backlog mode runs **in front of** pilot's existing `classify`, on the selected item only. It reads the spec **agentically** (the host's judgment, never a flowctl-computed `triageClass`) and routes by *explicit state first*: **workable** (ready signal + complete spec) → select-and-advance (pilot's existing path); **ready-but-thin / ready-but-ambiguous** (signal present, spec missing or too thin to act on) → [`ask`](#ask-stage--question-valve) (kick back with the gap, never build, never auto-author); **dep-unsatisfied** → `BLOCKED <id> by <dep>` (a state-changing surface of the dep wait); **needs a human decision** → `ask`. A *live* triage always lands on a **state-changing terminal** (`ADVANCED` / `ASKED` / `BLOCKED` / `NEEDS_HUMAN`) so an item can never re-select forever; `TRIAGED <id> <class>` is **diagnostic / `--dry-run` only**. `needs-spec` is always a *promoted* item missing a workable spec — never an un-promoted idea, which is simply skipped.

## Ask stage / question valve

Backlog mode's **async human-in-the-loop valve** — "stuck" becomes a question, not a stall, and never an interactive `AskUserQuestion`. When it cannot safely proceed, the `ask` stage writes each Open Question behind a **stable anchor** `<!-- flow-next:question id=<hash> status=open -->` (`id` hashes **stable fields only** — `subjectId` + blocked-stage + reason code + question slug; the free-prose reason is *outside* the hash so rephrasing never duplicates) and surfaces it where the item lives: a **spec-backed** item parks via the spec's `## Open Questions` section **and** a projected tracker comment; a **tracker-only** item (no spec) parks in the tracker comment alone. Tracker-sync composes the semantic question while deterministic `flowctl tracker` transport projects it across GitHub / GitLab / Jira / Linear; no reachable tracker ⇒ spec-only (when a spec exists) + a one-line "enable X to mirror" note, never a block. Selection **skips any item carrying a `status=open` parked question**, so it is never re-picked. A human answer (flipping the spec anchor to `status=answered`, or a tracker reply carrying `<!-- flow-next:answer id=<hash> -->` matched by `id`) makes the next tick re-triage and proceed. Terminal verdict: `ASKED <id> (<n>)` — a durable park.

## Decision log (`pilot-log`)

The per-tick **factory-metrics substrate** backlog mode writes (fn-68) via `flowctl pilot-log append --id <id> --action <triaged|advanced|asked|blocked|needs-human> --stage <stage|-> [--cost-tokens <n>]`, summarized by `flowctl pilot-log summary --json` → `{tick, id, action, stage, costTokens}` rows. The action enum is **aligned to the verdict grammar**; token cost is **host-reported** (omitted/null when unavailable) — flowctl only stores the row, never measures cost. Rows yield the efficiency readout (% moved with no question / one async answer / parked, and cost per change) and are the substrate a future self-improvement-synthesis spec mines. Stored under `.flow/pilot-runs/` (a sync-runs-style dir, auto-gitignored) — deliberately **NOT** any `receipts/` path the ralph-guard validates.

## Land

The cadence-tick ship loop (`/flow-next:land`): one tick discovers the open PRs the build loop authored (spec `branch_name` match AND the structural authorship probe — see Machine marker; both signals required), walks each through the gate tree (CI tri-state over ALL checks, patience window anchored to the last push, resolve-pr convergence, `land.reviewSignal`), and takes at most one action class per PR — CI fix, resolve dispatch, mechanical rebase, or the gated explicit merge (`gh pr merge --squash --match-head-commit`, never `--auto`) plus the post-merge tail (spec close → tracker touchpoint → release-follow). The one confined exception to the no-auto-merge rule; `/loop`-shaped where pilot is `/goal`-shaped. Ends with a terminal `LAND_VERDICT` line.

## Machine marker

The invisible HTML comment `<!-- flow-next:make-pr spec=<spec-id> base=<base-ref> -->` that `/flow-next:make-pr` emits directly under the visible footer breadcrumb (workflow §2.13b), and that land's authorship probe keys on: the marker must be the final structural line of the PR body with a spec-bound `Generated by ...` breadcrumb directly above it. Prose that merely mentions the token can never form the comment node, so a hand-written PR discussing flow-next never classifies as build-loop-authored (issue #274, 3.11.0). Pre-marker PRs fall back to an anchored single-line match of the complete dated footer. Verbatim forgery of the canonical footer is the documented boundary; the escalation path is attested provenance (classifying on the identity that opened the PR).

_Relates to_: Land, PR-as-cognitive-aid

## QA stage (`pipeline.qa`)

The optional live-app QA pass `/flow-next:qa`, graduated into a config-gated pilot stage (`pipeline.qa`, default **off**). When on, pilot runs one live pass over the complete build at all-tasks-done — `plan -> plan-review -> work -> **qa** -> make-pr` — driving the app the dev already has running during `work`. **Evidence-aware** (subtracts only AC a deterministic re-runnable check already proved; always live-runs every runtime / UI / integration criterion because the worker's self-report is narration, not captured evidence), **surfaced not blocking** (routes on `qa_outcome`, NOT the Ralph-guard `verdict` projection — `SHIP`/`NA`/`BLOCKED` advance, `NEEDS_WORK` still advances to the **draft** PR with findings in a `## Live QA` section + the bug-memory track + a tracker comment), and **augments, never replaces** CI / staging / manual QA. Net-new is one config-key default plus additive `qa_verdict` receipt fields (`head_sha` / `rid_coverage` / `open_p0p1`) — no new flowctl subcommand, no persisted test-case artefact. Idempotent per branch head via the receipt's `head_sha`. See `skills/flow-next-qa/SKILL.md` (fn-72).

## Verdict

The structured tick outcome a loop skill prints for transcript-blind drivers, always the last line of a tick. Pilot: `PILOT_VERDICT=<ADVANCED|NO_WORK|DEFERRED_TO_LAND|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason="<one line>"`; [backlog mode](#backlog-mode-pilotautonomy) **adds `ASKED <id> (<n>)`** (a durable park) and keeps every existing terminal verbatim (drivers grep `DEFERRED_TO_LAND` for the land hand-off, stop on `NO_WORK`); `TRIAGED <id> <class>` is diagnostic / `--dry-run` only, never a live terminal. Land: `LAND_VERDICT=<MERGED|RELEASED|FIXING_CI|AWAITING_REVIEW|RESOLVING|BLOCKED|NEEDS_HUMAN|NO_WORK> prs=<n> pr=<deciding-pr-url|-> reason="<one line>"` (tick verdict = worst severity across PRs). Autonomous resolve-pr runs end with `RESOLVE_PR_VERDICT=<RESOLVED|PENDING|NEEDS_HUMAN> threads=<n> fixed=<n> needs_human=<n>`, which land gates on. Distinct from a review receipt (Ralph's file-based proof-of-work): a verdict lives in the conversation output because `/goal` validators read the transcript, never the filesystem.

## Spec-as-PR

A team workflow where the spec is opened as a draft PR for review BEFORE any code lands. Reviewing a 50-line spec is higher-leverage than reviewing a 500-line implementation. Once merged, the spec is frozen on main; implementation PRs reference the merged spec.

## Frozen-at-handover

The R-ID invariant. Once a spec has been reviewed once, R5 means the same thing forever. A reviewer reading R5 in a six-month-old commit, a new team member reading R5 in the spec, and `/flow-next:make-pr` emitting R5 coverage all refer to the same acceptance criterion. Renumber-forbidden after first review cycle.

## flow-swarm

An in-progress companion product to flow-next that reads `.flow/specs/` directly to coordinate parallel agents across worktrees and consume `/flow-next:make-pr` output. The stable on-disk layout it builds against shipped with 1.0 (fn-43), and the portable contracts it renders from - structured findings (fn-136), criteria compliance (fn-137), the published config schema (fn-138) - are receipts, never Flow-Next internals. Still to migrate on the flow-swarm side: the pre-1.0 `epics` JSON key.

## Tracker

An external issue tracker (Linear, GitHub Issues, GitLab, or Jira) that flow-next *projects* a spec to via `/flow-next:tracker-sync`. The tracker is a **co-editable mirror** — body, status, and comments sync two-way — but it is **projection, not coordination**: the `.flow/specs/<id>.md` spec stays the source of truth and the quality layer, and the tracker never drives flow state or spawns agents. Distinct from `/flow-next:sync` (plan-sync). Contrast OpenAI Symphony, where the tracker *is* the control plane.

## merge-base snapshot

The common-ancestor body the tracker-sync 3-way merge compares against — a **paired** snapshot taken at the last sync point: both a flow-form body and a tracker-form body, plus content hashes (the echo fence). Stored in the spec-JSON `tracker` block (`mergeBaseFlow` / `mergeBaseTracker` / `baseHashFlow` / `baseHashTracker`) and written atomically as a unit (a one-sided update is rejected, so neither half pins to a stale sync point). Advances with `lastSyncedAt` on a real reconcile, never on a no-op echo.

## discovery ceremony

The detect → surface → ask → never-assume flow `/flow-next:tracker-sync` runs before enabling the bridge. It probes six signals (Linear MCP, `LINEAR_API_KEY`, GitHub auth, GitLab auth/`GITLAB_TOKEN`, Jira REST + token — `JIRA_BASE_URL` plus Cloud `JIRA_EMAIL`+`JIRA_API_TOKEN` or DC/Server `JIRA_PAT`), surfaces what is present *and* absent, asks the user, and writes `tracker.*` config **only on confirmation**, with provenance. No signal ⇒ nothing written; the bridge stays off. Resolution model is env > config > ask (mirrors `flowctl review-backend`).

## tracker-key handle

A tracker identifier used as a **resolvable flow id**, the hybrid id model. **Tracker-first** specs are canonically `KEY-N-slug` from a native key (Linear `WOR-17` → `wor-17-slug`, Jira `PROJ-123` → `proj-123-slug`) or a **synthetic** key while `tracker.type` matches (GitHub `#123` → `gh-123-slug`, GitLab `<project>#456` → `gl-456-slug`, project-scoped `iid`). Bare `wor-17` / `gh-123` / `gl-456` (and `.M` task forms) resolve as aliases. **Flow-first** specs keep `fn-NN-slug` and store the tracker display key in `tracker.identifier` as a resolvable alias. Resolution is case-insensitive; **`fn` is the only globally reserved prefix** (`fn-N` allocation counts `fn-*` only; synthetic `gh`/`gl` are reserved only while type is github/gitlab); one tracker team per repo; **ids never rename** on link. `tracker.specIds=tracker` is the team default that routes new mints onto this path.

## dependency projection

Tracker-sync's projection of a spec's local `depends_on_epics` edges into **tracker issue relations** (fn-64) — a `depends_on_epics` edge between two linked specs becomes a **blocked-by** relation between their issues (Linear native relations / GitHub native dependencies / GitLab native `is_blocked_by` issue links / Jira native "is blocked by" issue links — directional and universally available, no licence gate, no `flow:deps` block — else, for GitHub's reduced rung and GitLab on every tier, a provenance-fenced `<!-- flow:deps -->` body block). The relations counterpart to body/status/comments sync: projection, not coordination — flow stays authoritative, the tracker never declares deps back. Runs through deterministic `flowctl tracker relate` transport and the normalized relation adapter pair; idempotent via read-before-write. No transitive/graph expansion — only direct edges project.

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

## Operability ladder

Prime's tiered measure of whether an agent can actually *operate* a repo, scored from executed evidence rather than file existence: tier 1 = the build command actually runs, tier 2 = tests are discoverable and run, tier 3 = the app boots to a ready signal. Tiers are per-surface with a min-deployable headline (a monorepo carries per-member tiers, never one repo tier); a shape whose realistic ceiling is tier 1-2 reports "N/N at ceiling" and is offered a sideways move into observability/drivability instead of a fabricated tier bump. The verdict headline names the current operability tier and the single cheapest move up. Introduced by fn-92.

_Relates to_: Hard gate, Classification

## Hard gate

One of prime's three pass/fail gates that catch the existence-passes-but-execution-fails failure mode: G1 = the detected build command actually runs (or tier >= 1 operability evidence exists), G2 = tests are discoverable when a test framework is claimed, G3 = the agent instruction file's quoted commands resolve and execute. Any failing gate is NAMED in the verdict headline with its error and caps the computed maturity level at 2, so a repo cannot reach a high "readiness level" on existence checks alone. Introduced by fn-92.

_Relates to_: Operability ladder, Classification

## Delivery shape

Axis 5 of prime's classification: the multi-valued kind(s) of thing a repo delivers (web-service, CLI, library, desktop app, prose/docs, and so on). The `flowctl prime classify` emitter emits raw shape markers (bin exports, framework markers, serve/health code, desktop markers, prose ratio); the skill resolves the final shape value(s) from those markers. Delivery shape selects the per-shape playbook and sets the realistic operability-tier ceiling (a library or prose repo honestly tops out below a bootable web service). Introduced by fn-92.

_Avoid_: project type, repo type

_Relates to_: Classification, Operability ladder

## Classification (prime)

Prime's Phase 0.5 five-axis profile of a repo: lifecycle (greenfield / hybrid / brownfield), topology (two independent bits: monorepo, constellation-member), size/legibility band, stack(s), and delivery shape(s), plus an orthogonal `assessment_scope` (repository / workspace-member / constellation-home-base). The deterministic signals come from the `flowctl prime classify --json` emitter (bounded, pure-stdlib, no LLM); the skill layers judgment on top (Axis-5 shape reasoning, final per-axis confidence, bounded clarification asks, playbook selection). Classification parameterizes everything downstream: scout dispatch hints, N/A denominators, report shape, and playbook selection. `--classify-only` prints just this block for cheap portfolio triage. Introduced by fn-92.

_Relates to_: Operability ladder, Delivery shape, Hard gate
