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

The flow-next autonomous overnight loop. External shell loop drives fresh Claude / Codex sessions per task with cross-model review gates and receipt-based proof-of-work. Iterates plan-review -> work -> impl-review -> spec-completion-review until the spec ships or the iteration cap is hit. Differentiator from `ralph-wiggum`-style open-loop autonomous agents. Contrast `/flow-next:pilot`: the in-session, host-driven single-tick conductor — Ralph owns the loop in a shell script; pilot hands the loop to the host's `/loop` / `/goal` primitives.

## Pilot

The single-tick build-loop conductor (`/flow-next:pilot`): one tick advances one ready spec by one pipeline stage (plan / plan-review / work / make-pr) and ends with a terminal `PILOT_VERDICT` line; the host's `/loop` or `/goal` owns iteration. Signals autonomy to sub-skills via the `mode:autonomous` token + `FLOW_AUTONOMOUS=1` env (distinct from `FLOW_RALPH`; never activates ralph-guard). Selection consumes the fn-58 `ready` gate; two healthy no-advance ticks clear the spec's `ready` flag (don't-thrash).

## Verdict

The structured tick outcome pilot prints for transcript-blind drivers: `PILOT_VERDICT=<ADVANCED|NO_WORK|BLOCKED|NEEDS_HUMAN> spec=<id> stage=<stage> reason="<one line>"`, always the last line of a tick. Distinct from a review receipt (Ralph's file-based proof-of-work): a verdict lives in the conversation output because `/goal` validators read the transcript, never the filesystem.

## Spec-as-PR

A team workflow where the spec is opened as a draft PR for review BEFORE any code lands. Reviewing a 50-line spec is higher-leverage than reviewing a 500-line implementation. Once merged, the spec is frozen on main; implementation PRs reference the merged spec.

## Frozen-at-handover

The R-ID invariant. Once a spec has been reviewed once, R5 means the same thing forever. A reviewer reading R5 in a six-month-old commit, a new team member reading R5 in the spec, and `/flow-next:make-pr` emitting R5 coverage all refer to the same acceptance criterion. Renumber-forbidden after first review cycle.

## flow-swarm

An in-progress companion product to flow-next that reads `.flow/specs/` directly to coordinate parallel agents across worktrees and consume `/flow-next:make-pr` output. The on-disk layout flow-swarm expects is what fn-43 (epic->spec rename) produces. Reference target for the v1.0 migration carrot.

## Tracker

An external issue tracker (Linear first, GitHub Issues next) that flow-next *projects* a spec to via `/flow-next:tracker-sync`. The tracker is a **co-editable mirror** — body, status, and comments sync two-way — but it is **projection, not coordination**: the `.flow/specs/<id>.md` spec stays the source of truth and the quality layer, and the tracker never drives flow state or spawns agents. Distinct from `/flow-next:sync` (plan-sync). Contrast OpenAI Symphony, where the tracker *is* the control plane.

## merge-base snapshot

The common-ancestor body the tracker-sync 3-way merge compares against — a **paired** snapshot taken at the last sync point: both a flow-form body and a tracker-form body, plus content hashes (the echo fence). Stored in the spec-JSON `tracker` block (`mergeBaseFlow` / `mergeBaseTracker` / `baseHashFlow` / `baseHashTracker`) and written atomically as a unit (a one-sided update is rejected, so neither half pins to a stale sync point). Advances with `lastSyncedAt` on a real reconcile, never on a no-op echo.

## discovery ceremony

The detect → surface → ask → never-assume flow `/flow-next:tracker-sync` runs before enabling the bridge. It probes four signals (Linear MCP, `LINEAR_API_KEY`, GitHub auth, a Jira host), surfaces what is present *and* absent, asks the user, and writes `tracker.*` config **only on confirmation**, with provenance. No signal ⇒ nothing written; the bridge stays off. Resolution model is env > config > ask (mirrors `flowctl review-backend`).

## tracker-key handle

A tracker identifier (e.g. `WOR-17`) used as a **resolvable flow id**, the hybrid id model. **Tracker-first** specs are canonically `wor-17-slug` (tasks `wor-17-slug.M`); bare `wor-17` / `wor-17.M` resolve as aliases. **Flow-first** specs keep `fn-NN-slug` and store `WOR-17` in `tracker.identifier` as a resolvable display alias. Resolution is case-insensitive (`show wor-17`, `work wor-17` resolve); the native `fn-` scheme is reserved (`fn-N` allocation counts `fn-*` only); one tracker team per repo; **ids never rename** on link.
