## Conversation Evidence

> user: "you didn't link the pr properly, tracker sync didn't work somehow"
> user: "why did it not happen before, i had similar issues in codex in another project"
> user (relaying a Codex session in another project, GNO-3): "you also didn't do it on the work steps, you also didn't link the pr etc etc, help me understand if my prompting in the skills was wrong or was this a one-off thing"
> [Codex agent's diagnosis, shared by user]: "Not your prompting. Mostly my execution miss. ... these hooks are prose/checklist obligations, not executable gates. The skill says 'invoke tracker-sync' but the actual snippet body is `:`. That makes it agent-discipline-dependent. ... The durable fix is to make flow-next-work / flow-next-make-pr call a real flowctl sync lifecycle ... or equivalent wrapper, so missing tracker sync is observable and receipts are required before final."
> user: "do we have issues with our tracker-sync stuff"
> user: "yes capture it"
> user: "this is not just for linear right, but for all trackers?"

> [agent investigation this session, confirming the diagnosis against the code]: make-pr §4.6a (the PR↔issue `Ref <identifier>` line) IS deterministic bash that appends to the body before `gh pr create` (workflow.md:1341-1343) — the miss there was execution-fidelity (the agent hand-rolled `gh pr create` and skipped it). The lifecycle hooks — `work.firstClaim → In Progress` (phases.md:210), `work.done → comment` (:282), make-pr §5.6 enhancement — are executable GATES wrapping a `:` no-op whose only body is a prose comment ("invoke the flow-next-tracker-sync skill"). On the MCP rung (no `LINEAR_API_KEY`), flowctl has no MCP access, so the action is inherently agent-driven and can't be a pure flowctl call.

> user (2026-06-09, re-scoping review): "i forgot about it as i was wary of adding more determinism, but this might make sense if it's a light touch that doesn't introduce a ton of overhead, and no overhead for users that don't user the sync-tracker stuff" ... "minimal but effective solution"
> user (2026-06-09): "push it to linear, it should be a blocker of the other ones we just did" [fn-58/59/60 — the loop-orchestration chain]
> [agent re-review 2026-06-09, against flowctl + skills]: receipt plumbing already ships — `flowctl sync receipt` (status enum `pushed|pulled|merged|updated|diverged|queued|errored|noop`, `--transport`, `--note`, guard-safe `.flow/sync-runs/`), emitted by the tracker-sync skill per run. Two gaps: receipts carry NO event field, and NOTHING reads them back (no check/audit command). The failure mode was reproduced live this session: capture ran with `perEvent.capture: reconcile` active and silently skipped the touchpoint — no skill run, no receipt, no signal.

> user (2026-06-09, glossary review — Package B): "pack it into fn-57, i agree that it should be in prime, after all that is what prime is for. then if interview writes it, perhaps capture should do too? i think also that we dont need a separate skill for refreshing, our strategy should always be the system gets better as you use it natuarlly (not like calling compound manually in their variant)"
> user: "this may need better documentation ... perhaps more information about self-improving, a separate page on flow-next.dev, there are a couple of things here right, our memory, glossary and others perhaps" ... "perhaps this should be stated as one of our goals in STRATEGY.md, ie. self improving through normal work" ... "bake all this into fn-57"
> [agent glossary review 2026-06-09, against the code]: GLOSSARY.md + `flowctl glossary {add,list,read,remove}` ship since fn-38 (0.39.0); writers today: interview (doc-aware behaviors), audit (staleness + alias-creep prune), sync. Two gaps vs the "CONCEPTS.md" pattern: (a) no repo-seeded bootstrap — the glossary starts empty and accretes only via interviews; (b) the read surface excludes plan scouts / work worker / reviews — exactly where wrong-concept errors get built (live exhibit: the agent conflated Spec vs Plan this session; the distinction is IN GLOSSARY.md, but nothing in the plan path read it).
> user (2026-06-09, hero): "self-improving should probably also be one of the main taglines in the hero of flow-next.dev" [current pillars: Spec-driven / Context-fit plan / Re-anchored work / Adversarial gates / Multi-harness] "...there, but may need redesigning so it all fits, may need to add more there later too, like the loop stuff, use frontend design plugin for doing that work (say that in fn-57)"

## Goal & Context
<!-- scope: business -->

<!-- Source-tag breakdown: 55% [user] / 25% [paraphrase] / 20% [inferred] -->

flow-next's tracker-sync bridge (fn-52, shipped) wires lifecycle touchpoints — claim a task → move the issue In-Progress, finish a task → post a comment, open a PR → link it to the issue. In real use these touchpoints **silently don't fire**: a PR opened without its issue link, work steps that never moved the tracker. [user] It has happened on more than one host — both a Claude session and a Codex session in a separate project (GNO-3) hit it [user] — so it is **not a prompting problem and not model-specific** [paraphrase]. Root cause: the lifecycle hooks are **prose/checklist obligations, not executable gates** — the skill says "invoke the tracker-sync skill" but the actual snippet body is a `:` no-op, making them agent-discipline-dependent, and nothing fails when they are skipped. [paraphrase] When an agent is driving the loud gates (tests, review, PR-create — which fail visibly), the quiet tracker side-effects get dropped. [inferred] This spec makes the tracker lifecycle **observable and forcing** so a configured-but-didn't-fire touchpoint is a detectable gap, not a silent one. [paraphrase]/[inferred]

This is **tracker-agnostic — for ALL trackers, not just Linear**: Linear and GitHub today (and any future adapter), via the bridge's transport-blind adapter interface. [user] The Linear symptoms surfaced it, but the weakness is in the shared lifecycle-hook layer that every adapter routes through. [inferred]

**Package B (added 2026-06-09): self-improving glossary.** The same principle — *the system gets better as you use it, through normal work, never via a manual ceremony* [user] — applied to project vocabulary: `/flow-next:prime` seeds GLOSSARY.md from the repo, `/flow-next:capture` joins `/flow-next:interview` as a writer, the plan/work read path actually consumes it, and the self-improving surfaces (memory, glossary, decisions, strategy) get a dedicated docs page + a STRATEGY.md track. [user]/[paraphrase]

## Architecture & Data Models
<!-- scope: technical -->

The split is the existing flow-next architecture rule (mechanical → deterministic/flowctl + receipts; judgment → skill), applied to the tracker hooks — with one deliberate narrowing: **flowctl never mutates the tracker; it only audits.** All tracker mutations stay agent-driven through the tracker-sync skill on every transport. [user]/[inferred]

Receipt plumbing already ships (`flowctl sync receipt` — status enum, `--transport`, `--note`, guard-safe `.flow/sync-runs/`; the tracker-sync skill emits one per run). The minimal delta is four pieces, tracker-agnostic because they live in the shared receipt/lifecycle layer every adapter routes through: [inferred]

- **`--event <perEvent-key>` on `sync receipt`** — tags each receipt with the lifecycle touchpoint it served (`work.firstClaim`, `work.done`, `work.completionReview`, `capture`, `makePr`, ...). The existing `noop` status + `--note` already expresses skipped-with-reason; no enum widening. [inferred]
- **`flowctl sync check <spec-id> --events <triggered-this-run>`** — a new **read-only, local-only** audit: bridge inactive → silent constant-time exit (the zero-overhead path); active → for each triggered + configured event, verify a matching receipt exists; print `OK` / `MISSING:<event>` lines. It runs independently of the touchpoints, so a wholesale-skipped dispatch block is still caught. [paraphrase]/[inferred]
- **End-of-skill check + retro-fire** — work (end-of-run summary), capture (final phase), and make-pr (final output) each add one `sync check` call; on `MISSING` the skill retro-fires the missed touchpoint via the tracker-sync skill, re-checks, and surfaces the result in the summary it already prints. The summary line is the forcing function. [inferred]
- **make-pr fidelity repair** — after `gh pr create`, deterministically verify the §4.6a ref line landed in the PR body (`gh pr view --json body`) and repair via `gh pr edit` when absent — mechanical, no judgment; `gh` is already a make-pr prereq. [inferred]

**Agent-only transports** (e.g. Linear's MCP rung — flowctl can't call it) need no special case: mutation is agent-driven everywhere, and the audit only reads local receipts. **Judgment ops** — the agentic 3-way body reconcile/merge — stay a skill for every tracker; this spec does not touch them. [inferred]

### Check semantics (resolved at planning — fn-52 research + gap analysis)

- **MISSING predicate:** an event is `MISSING` iff it **triggered this run** AND its `tracker.perEvent` leaf is enabled AND the bridge is active AND **no receipt with a matching `event` field and `timestamp ≥ --since` exists**. Linkage is NOT a precondition — an unlinked spec triggers create-if-unlinked, so a never-linked spec with no receipt is exactly the miss this catches.
- **Any-status clears:** any event-matching receipt ≥ `--since` clears MISSING regardless of status (`noop`/`errored`/`queued` included). The check asserts the touchpoint *ran*; the receipt's own status carries success/failure detail.
- **Run-scoping (`--since`):** receipts accumulate forever in `.flow/sync-runs/`; without a lower bound, prior-run receipts cause false passes. Bash state does NOT survive across skill tool calls, so each skill derives `--since` from an on-disk anchor: work → earliest `claimed_at` among tasks worked this run; capture → the spec's `created_at`; make-pr → the PR's `createdAt` (or branch-push time). Timestamps parse via the existing `_parse_iso_ts` helper (3.8-safe `Z` handling) — never bare `fromisoformat`.
- **Triggered-set contract:** the calling skill derives `--events` from what occurred: ≥1 task claimed → `work.firstClaim`; ≥1 task done → `work.done`; completion-review ran → `work.completionReview`; spec captured → `capture`; PR created → `makePr`. Configured-but-not-triggered events are never MISSING.
- **Summary slot vocabulary (the forcing function):** the skill's final summary template carries a mandatory `Tracker sync:` field — `OK` | `MISSING:<event> → retro-fired → OK` | `MISSING:<event> (retro-fire failed: <reason>)` | `n/a (bridge inactive)`. An explicit `n/a` proves the check ran; an absent field is visible as a skipped check.
- **Retro-fire:** bounded to exactly ONE cycle — check → dispatch tracker-sync once for the missed event → re-check (against a fresh `--since` = retro-fire start) → record final state. The retro-fire invokes the tracker-sync skill directly and NEVER the end-of-skill check wrapper (no recursion). Still-MISSING after one cycle is a recorded state + visible line, never a block.
- **Output routing:** under Ralph, check/summary lines go to **stderr** (make-pr's stdout is reserved for `PR_URL=`; work's stdout stays clean for harness parsing).

### Package B — self-improving glossary (added 2026-06-09)

GLOSSARY.md + `flowctl glossary {add,list,read,remove}` already ship (fn-38). Today's writers: interview (doc-aware add), audit (staleness/alias-creep prune as part of its normal sweep), sync. Package B completes the compounding loop with **prompting only — zero new flowctl, zero new skills**: [user]/[inferred]

- **Seed (prime):** `/flow-next:prime` gains a glossary-bootstrap step — when GLOSSARY.md is absent or a husk (`glossary list --json` `total_terms == 0`), scan the repo for the load-bearing nouns/flows/distinctions, propose terms WITH evidence (file refs), read-back, write via `flowctl glossary add`. When populated, prime reports term-coverage as a readiness signal but never rewrites. Prime is the repo-readiness ceremony — this is what prime is for. [user]
- **Add (capture joins interview):** capture's synthesis already detects vocabulary conflicts (`## Glossary Conflicts` spec section); it now also OFFERS to add genuinely new project terms surfaced by the conversation, at read-back, via `flowctl glossary add` — mirroring interview's doc-aware behaviors, gated on the same husk-aware autodetect. [user]
- **Read (plan/work consume it):** the plan scouts (repo-scout / context-scout) include relevant `glossary list` terms in their research payload; the work worker's re-anchor reads task-relevant terms; review prompts reference the glossary when populated. The wrong-meaning-of-a-normal-word failure hits planning and implementation — exactly where the glossary was invisible. [inferred]
- **Prune (already shipped):** audit's existing sweep stays the refresh mechanism. **No separate refresh/compound skill, ever** — improvement happens through normal use, not a manual ceremony. [user]

## Quick commands

```bash
# Smoke: zero-overhead path (bridge inactive repo) — must print nothing, exit 0
.flow/bin/flowctl sync check fn-57 --events capture --since 2026-06-09T00:00:00Z

# Smoke: receipt round-trip with event tag
.flow/bin/flowctl sync receipt fn-57 --status noop --transport none --event capture --note smoke
.flow/bin/flowctl sync check fn-57 --events capture --since 2026-06-09T00:00:00Z --json

# Glossary plumbing (existing — Package B is prompting only)
.flow/bin/flowctl glossary list --json | jq '.total_terms'

# Tests
cd plugins/flow-next && python3 -m unittest discover -s tests -p "test_sync_check.py" -v
```

## Edge Cases & Constraints
<!-- scope: technical -->

- **Bridge inactive / event opted-out** is a legitimate `skipped` (no-op), not a failure — must read as a clean receipt, never an error. [inferred]
- **Execution-fidelity gap (make-pr §4.6a):** the ref-append is already deterministic but an agent that hand-rolls `gh pr create` bypasses it — the forcing function must catch "PR opened but no issue link" even when the skill's own bash wasn't run literally. [inferred]
- **Best-effort, never blocking the primary work:** a tracker failure must stay non-fatal (the PR is already open; the task is already done) — observability must not turn a tracker hiccup into a hard stop. [inferred]
- **Ralph-safe:** receipts + any queue behavior must preserve the autonomous-loop invariants. [inferred]
- **Pre-`--event` receipts** carry no event field — the check only counts receipts whose `event` matches; `event: null` receipts never satisfy an event-specific check. [inferred]
- **`gh pr edit --body` replaces the whole body** (no append flag) — the §4.6b repair is read-modify-write: fetch LIVE body, whole-line `grep -qixF` match (shared with §4.6a), append-only, re-check the 65,536-char cap, non-fatal. [inferred]
- **Glossary bootstrap is consent-gated:** prime proposes with read-back; never writes terms unseen. Husk-aware (`total_terms == 0`, not `[[ -f ]]`) — the same R18 invariant interview uses. [inferred]
- **Glossary read-path additions are budget-capped:** scouts/worker include only task-relevant terms (matched against the request/task text), never the whole glossary — the read path must not bloat context. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Sync receipts are **event-tagged**: `flowctl sync receipt` gains `--event <perEvent-key>` (free-form string, NOT a `choices=` enum — the perEvent key set is an open extension point), and every tracker-sync invocation from a lifecycle touchpoint records which event it served. The existing status enum + `--note` express skipped/errored — no enum widening. [paraphrase]
- **R2:** A new **read-only** `flowctl sync check <spec-id> --events <csv> --since <iso> [--json]` compares the events that triggered during a run against config + receipts per the Check semantics above and reports `OK` / `MISSING:<event>` per touchpoint; **work, capture, and make-pr run it before their final summary, retro-fire any `MISSING` touchpoint via the tracker-sync skill (one cycle), re-check, and surface the outcome in a mandatory summary slot** — a missing tracker side-effect is caught in-run, not discovered later by the user. [paraphrase]
- **R3:** flowctl gains **no tracker-mutation code** — all status / comment / link mutations stay agent-driven through the tracker-sync skill on every transport; the only deterministic additions are the read-only audit and the make-pr ref verify/repair. [user]
- **R4:** The make-pr **PR↔issue link reliably fires on a real `/flow-next:make-pr` run for whichever tracker is active** — the execution-fidelity gap (agent hand-rolls `gh pr create` and skips the deterministic ref-append) is closed by a deterministic post-create verify (`gh pr view --json body` contains the ref when the bridge is active + linked) with `gh pr edit` repair when absent. [user]/[inferred]
- **R5:** On any **agent-only transport** (e.g. Linear's MCP rung — flowctl can't call it) where the op is inherently agent-driven, the forcing function is the **receipt gate** (the agent must record the event receipt), since the op cannot be a pure flowctl call. [inferred]
- **R6:** The **agentic 3-way body merge stays a skill** — for every tracker — this spec hardens only the mechanical status / comment / link touchpoints, not the judgment-bearing reconcile. [inferred]
- **R7:** The hardening is **tracker-agnostic**: it lives in the shared receipt / lifecycle-hook layer and applies uniformly to **every adapter — Linear, GitHub, and any future tracker** — never Linear-only. [user]
- **R8:** **Zero overhead when the bridge is inactive or the event is opted out**: `sync check` exits silently in constant time — no output, no receipts, no prompts; non-tracker users see no change anywhere in their workflow. [user]
- **R9:** Docs updated — `tracker-sync.md` (receipt/check lifecycle, retro-fire, MISSING-recovery guidance), `flowctl.md` (`sync check`, `--event`), and `linear-mcp.md` **corrected**: the claude.ai Linear MCP returns identifiers, never UUIDs, so first-link requires the GraphQL rung (`LINEAR_API_KEY`); site changelog entry + plugin version bump. [user]/[inferred]
- **R10:** `/flow-next:prime` seeds GLOSSARY.md from the repo when it is absent or a husk — proposes the load-bearing terms with file-ref evidence, read-back before write, writes via `flowctl glossary add`; on a populated glossary it reports coverage and never rewrites. [user]
- **R11:** `/flow-next:capture` joins interview as a glossary writer — new project vocabulary surfaced by the conversation is offered as term-adds at read-back (consent-gated, husk-aware autodetect, same gating shape as interview's doc-aware mode). [user]
- **R12:** The glossary read path widens to where wrong-concept errors get built: plan scouts (repo-scout / context-scout) include task-relevant glossary terms in their research payload; the work worker's re-anchor reads task-relevant terms; review prompts reference the glossary when populated. Budget-capped — relevant terms only, never the whole file. [paraphrase]/[inferred]
- **R13:** A dedicated **"self-improving" docs page** ships on flow-next.dev (+ a git-docs counterpart) covering the surfaces that compound through normal use — memory (bug/knowledge tracks, Ralph auto-capture), glossary (prime seeds / interview + capture add / audit prunes), decision records, strategy (drift surfacing) — with both navbars + changelog updated per the two-sources rule. [user]
- **R14:** STRATEGY.md gains **"self-improving through normal work"** as a stated direction (track or approach line): the system gets better as you use it; no manual compound/refresh ceremonies. [user]
- **R15:** The flow-next.dev **hero pillar grid gains a "Self-improving" pillar** (alongside Spec-driven / Context-fit plan / Re-anchored work / Adversarial gates / Multi-harness), with the grid **redesigned so six pillars fit and the layout stays extensible** for future additions (e.g. the loop chain); the redesign is executed **with the frontend design plugin**. [user]

## Boundaries
<!-- scope: business -->

- **NOT** a rewrite of the tracker-sync bridge (fn-52, shipped) — a reliability hardening of its lifecycle hooks. [inferred]
- **NOT** making the body reconcile deterministic — that legitimately stays an agentic skill. [user: "make ... call a real flowctl sync lifecycle ... or equivalent wrapper" applies to the mechanical parts]
- **NOT** building tracker mutations (GraphQL/gh status, comment, attach ops) into flowctl — the original draft's deterministic-transport idea is deliberately cut per the maintainer's light-touch constraint; mutation stays in the skill. [user]
- **NOT** hook-based enforcement — no PreToolUse/Stop machinery; the forcing function is the end-of-skill check + visible summary line. [user]
- **NOT** changing the opt-in / opt-out config model (`perEvent`, default-on-after-ceremony) — only how reliably the opted-in events fire and are observed. [inferred]
- **v1 wires the check + retro-fire into work, capture, and make-pr only** — `resolvePr` / `interview` / `plan` touchpoints keep their existing receipt-only behavior (their receipts still gain `--event` tags); `qa` self-posts via fn-53.4 and is out of scope here. [inferred]
- **NO separate glossary refresh/compound skill** — improvement happens through normal use (prime seeds, interview/capture add, audit prunes, plan/work read); never a manual ceremony the user must remember to run. [user]
- **NO new flowctl glossary plumbing** — Package B is prompting over the existing `glossary {add,list,read,remove}` surface. [inferred]
- Tracker side-effects stay **best-effort / non-fatal** to the primary work loop — observability adds a receipt, never a hard block on a tracker failure. [inferred]

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation

A bridge whose lifecycle hooks silently no-op erodes the whole value proposition — the user believes the tracker mirrors flow state, but PRs land unlinked and issues never move, and the user only finds out by accident (as happened on FLOW-5 and in the GNO-3 Codex session). [user]/[inferred] Making the hooks observable + forcing converts "did the agent remember?" into a checkable property, the same way Ralph's receipts make autonomous state transitions auditable. [paraphrase]/[inferred]

This also hardens the layer the autonomous loop chain (fn-58 readiness projection, fn-59 pilot, fn-60 land) rides on — which is why it blocks that chain. [user]

Package B shares the motivation at the vocabulary layer: agents pick the wrong meaning of a normal-looking word and build a correct-looking implementation around the wrong concept (reproduced live this session — Spec vs Plan, a distinction GLOSSARY.md already defines but nothing in the plan path read). Seeding + widening the read path turns the glossary from a passive file into part of the working loop — and the unifying principle for both packages is **self-improving through normal work**. [user]/[inferred]

### Implementation Tradeoffs
<!-- scope: technical -->

Receipts alone cannot close the loop — they are written *by* the tracker-sync skill, and the observed failure mode is the dispatch block being skipped wholesale (reproduced live 2026-06-09: capture ran with `perEvent.capture: reconcile` active and silently skipped the touchpoint — no skill run, no receipt, no signal). Hence the check must run independently of the touchpoints, at end-of-skill. The original draft's "deterministic mutations via gh/GraphQL transports" was cut deliberately: it builds per-tracker mutation surface into flowctl, duplicates the skill, and contradicts the light-touch constraint — the audit is read-only; the mutations stay agentic. Check + retro-fire converts "did the agent remember?" into "the skill cannot finish without either receipts or a visible `MISSING` line." [user]/[inferred]

Package B deliberately rejects the manual-ceremony model (a "compound/refresh" command the user must invoke): seeding lives in prime because prime IS the repo-readiness ceremony; adds live in the authoring skills (interview, capture) because that is where new vocabulary surfaces; pruning stays in audit's existing sweep. All prompting — no new flowctl, no new skills, no new commands to remember. [user]

## Strategy Alignment

Active tracks served by this plan:
- **Ralph autonomous mode** — receipt-gated observability extends the proof-of-work discipline to tracker side-effects; required hardening under the loop chain (fn-58/59/60).
- **Spec-driven team patterns** — a tracker that reliably mirrors flow state is the team-facing surface of the handover-object chain; canonical vocabulary in the working loop is what keeps multi-agent teams consistent.
- **Cross-platform parity** — the check is flowctl plumbing + skill prose; sync-codex.sh mirrors it to Codex unchanged.

R14 additionally PROPOSES a new track ("self-improving through normal work") — formalizing a direction the memory/glossary/decisions/strategy subsystems already embody; written to STRATEGY.md as part of task fn-57.8, per the user's explicit instruction.

## Early proof point

Task fn-57.1 validates the core approach (run-scoped, read-only gap detection over `.flow/sync-runs/` with the zero-overhead inactive path). If reliable run-scoping can't be achieved with on-disk anchors (`claimed_at` / `created_at` / PR `createdAt`), re-evaluate the check model (per-run nonce receipts) before wiring any skill.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | `sync receipt --event` tagging | fn-57.1, fn-57.2 | — |
| R2 | `sync check` + end-of-skill check/retro-fire in work/capture/make-pr | fn-57.1, fn-57.3, fn-57.4 | — |
| R3 | No tracker-mutation code in flowctl | fn-57.1 | Negative constraint — verified by acceptance on .1 |
| R4 | make-pr ref verify/repair (§4.6b) | fn-57.4 | — |
| R5 | Receipt gate on agent-only transports | fn-57.3, fn-57.4 | — |
| R6 | 3-way body merge stays a skill | — | Boundary invariant; no work, verified at review |
| R7 | Tracker-agnostic shared layer | fn-57.1, fn-57.2 | — |
| R8 | Zero overhead when bridge inactive | fn-57.1 | — |
| R9 | Tracker docs + linear-mcp correction + version | fn-57.2, fn-57.5 | — |
| R10 | prime glossary bootstrap | fn-57.6 | — |
| R11 | capture glossary writes | fn-57.7 | — |
| R12 | Glossary read path (scouts / worker / reviews) | fn-57.7 | — |
| R13 | Self-improving docs page (site + repo) | fn-57.8 | — |
| R14 | STRATEGY.md self-improving track | fn-57.8 | — |
| R15 | Hero "Self-improving" pillar + grid redesign (frontend design plugin) | fn-57.8 | — |
