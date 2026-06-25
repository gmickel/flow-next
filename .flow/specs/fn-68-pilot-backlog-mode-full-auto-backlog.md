# fn-68 pilot backlog mode — full-auto backlog triage + dep-scheduling + async gap-surfacing

## Goal & Context
<!-- scope: business -->

The autonomy track already ships **pilot** (ready spec → plan → reviews → work → draft PR) and **land** (draft PR → CI-fix → gated merge → release), both driven by host `/loop` / `/goal`. But pilot's consent boundary is explicit — *"human judgment lives before pilot"*: it only selects from the **already-ready** queue and assumes specs are triaged, dep-clear, and unambiguous. Everything **in front of the ready gate** — enumerating the whole open backlog, triaging raw items, checking deps, deciding what's next, and unblocking the things that need a human — is still manual prompting today. flow-next is already usable that way (semi-auto by prompting); the gap is a **standing organ that manages the entire open backlog unattended and only pulls a human in when it genuinely cannot proceed**.

Trigger: the Warp *"factory engineers, not product engineers"* memo (2026-06). Its transferable frame: the job is building the factory, measured by **% of changes shipped automatically / (inference cost + human time)**, with agents doing triage → spec → implement → review → verify → monitor and humans stepping in only where needed. flow-next has the conveyor (pilot/land/Ralph) and a two-way tracker channel (tracker-sync); it lacks the **floor scheduler**, the **async human-in-the-loop valve** (so "stuck" becomes a question, not a stall), and the **efficiency readout**.

This spec adds an **optional backlog mode** to pilot. Per tick: enumerate everything open (flow + tracker), select the top dep-ordered actionable item, **triage** it, and — if it is a workable, written spec — advance it one stage along pilot's existing pipeline `plan → plan-review → work → make-pr (draft)` — **full-auto by default**, surfacing a precise question to the human via the spec + tracker when it cannot safely proceed, and **never merging** (land stays human-gated).

**Backlog mode does not author specs.** Spec authoring (`capture`, conversation→spec; `interview`, interactive Q&A) is **human-gated and upstream** — an agent inventing scope from a one-line ticket is precisely the slop the question-valve exists to prevent. So a ticket without a workable spec is **surfaced as a gap** ("run `/flow-next:capture` or `/flow-next:interview`"), never auto-written. The autonomous span runs only from a *workable spec* onward — exactly pilot's current pipeline. The lifecycle, with consent gates marked:

```
idea → [capture / interview] → plan → plan-review → work → make-pr(draft) → [human review] → resolve-pr → [land / merge]
        ^ human, upstream        └──────────── backlog mode runs this span ────────────┘                ^ human, downstream
```

Triage sits at the front and only **routes**: workable → run the span; not-workable → surface "needs a spec," park; blocked → sequence behind the blocker. It never authors and never merges. (`plan` — spec→tasks — is autonomous and already a pilot stage; spec *authoring* is not.)

Decided **not** to build a separate skill (an earlier "foreman above pilot" proposal was considered and rejected): Gordon's full-auto reframe removed the pre-pilot consent boundary that would have justified splitting. pilot already selects across the backlog and walks a pipeline, so backlog mode is a **leftward extension of the same single-tick conductor**, not a new altitude — one `/loop` target, one verdict grammar, one mental model.

## Architecture & Data Models
<!-- scope: technical -->

- **Backlog mode is a behavior of the existing `flow-next-pilot` skill**, gated by config `pilot.autonomy` (default `ready` = current behavior; `backlog` enables the wide mode), overridable per run by `--backlog` / `--auto`. With the flag off, pilot behavior is unchanged.
- **Single-tick contract preserved.** One invocation = select one item + advance one stage + emit one terminal verdict. `/loop` (Claude Code) and `/goal` (Codex) still own repetition. No within-tick loop over multiple items.
- **Selection widens** from "one ready spec" to "one actionable open item across flow specs + tracker issues, **dep-ordered**" — using `depends_on_epics` + tracker `depRelations` + the `flow-next-deps` graph.
- **Pipeline extends leftward** with `triage` and `ask` stages **in front of** pilot's existing `plan → plan-review → work → make-pr` — it does **not** add a spec-authoring stage:
  - **triage** — classify the selected item: workable-now / needs-spec / blocked-by-dep / ambiguous / needs-human. Routing only.
  - **ask** — when not-workable or ambiguous, write **Open Questions** into the spec, project them as a tracker comment via tracker-sync, mark park-pending-answer. For a *missing or too-thin* spec the surfaced gap is an explicit "run `/flow-next:capture` or `/flow-next:interview`" — backlog mode never authors the spec itself. (It MAY fill an obvious blank in an *existing* spec; it never authors from nothing.)
  - workable, written, dep-clear specs flow into pilot's existing `plan → plan-review → work → make-pr` unchanged.
- **Backlog-mode workflow lives in its own reference file** under the pilot skill (e.g. `references/backlog-mode.md`) so `SKILL.md`'s core single-tick contract stays thin — separation of concerns at the file level, not the command level.
- **Net-new flowctl plumbing (thin):** a backlog-wide ready scan (`flowctl ready --all`; today `ready` is `--spec`-only) returning open items with triage/dep/ready state; and a per-tick **decision log** (receipt-shaped) recording each action + token cost, which powers metrics and the self-improvement substrate.
- **Merge stays out.** land remains a separate human-gated step; backlog mode never invokes merge/land.

## API Contracts
<!-- scope: technical -->

- **Config:** `pilot.autonomy ∈ {ready (default), backlog}`. Per-run override `--backlog` / `--auto`. Optional `pilot.autonomy.gate: [<class>…]` forces surfacing before action for named classes (e.g. `risky`, `prod-config`).
- **Invocation:** unchanged — `/flow-next:pilot` via `/loop` or `/goal`; flags pass through.
- **Verdict grammar (extends `PILOT_VERDICT`):** `TRIAGED <id> <class>` / `PROMOTED <id>` / `ADVANCED <id> <stage>` / `ASKED <id> (<n> questions)` / `IDLE` (nothing actionable) / `NEEDS_HUMAN <id> <reason>`. One terminal line for the driver, as today.
- **Question channel:** spec-first (an `## Open Questions` section, always written) projected to the active tracker adapter via tracker-sync (Linear now, GitHub next; **Jira = spec-only** until an adapter exists). Human answers in spec or tracker comment → tracker-sync reconciles → next tick re-triages.
- **`flowctl ready --all --json`:** returns open items `{id, source: flow|tracker, triageClass, blockedBy, ready}`.
- **Decision log:** append + summarize subcommand yielding `{tick, id, action, costTokens}` rows.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Never merges** — hard boundary; land stays human-gated.
- **Never answers its own questions**; never promotes an item with an unanswered open question.
- **Park is never silent** — always a logged dep-wait or a surfaced question.
- **Dep deadlock / cycle:** detect, surface as a question, do not spin.
- **Idempotent surfacing:** re-triaging an already-asked/parked item must not duplicate questions/comments (dedup via tracker-sync comment dedup + stable Open-Questions anchors).
- **No autonomous spec authoring:** backlog mode never runs `capture`/`interview` and never writes a spec from a bare ticket; a missing/too-thin spec is surfaced as a "needs capture/interview" gap and parked. Augmenting an obvious blank in an *existing* spec is the only writing it may do.
- **Tracker unavailable** (no adapter / offline): degrade to spec-only questions + log note; never crash (mirrors tracker-sync noop).
- **Default off:** existing pilot/land/Ralph users unaffected until they opt in.
- **Single-tick discipline preserved:** the host primitive loops, not the skill.
- **Cross-platform:** canonical Claude names; `sync-codex.sh` regenerates the Codex mirror; `/goal` (Codex) driver parity.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** pilot gains a backlog mode gated by config `pilot.autonomy` (default = current ready-only behavior), overridable per run by `--backlog` / `--auto`; with the flag off, pilot behavior is unchanged.
- **R2:** In backlog mode, one tick enumerates the full open set (flow specs + tracker issues), selects the top dep-ordered actionable item, triages it, and — for a workable written spec — advances it exactly one stage of pilot's existing pipeline (`plan → plan-review → work → make-pr`), emitting one terminal verdict line. The autonomous span runs only from a workable spec onward; `make-pr` (draft) is its terminus.
- **R3:** Triage classifies the selected item into workable-now / needs-spec / blocked-by-dep / ambiguous / needs-human and **routes** accordingly — promote, sequence behind blocker, or ask. It never authors a spec: a missing/too-thin spec is routed to the `ask` gap ("run capture/interview"), not auto-written.
- **R4:** When it cannot safely proceed, it writes Open Questions into the spec and projects them as a tracker comment via tracker-sync (spec-first; Linear/GitHub where an adapter exists; spec-only for Jira), then parks-pending-answer and moves on — never blocks, never asks interactively.
- **R5:** Full-auto by default — workable, dep-clear, unambiguous items are promoted/advanced with no pre-gate; a force-gate config can require surfacing before action for named classes.
- **R6:** Never merges; land remains a separate human-gated step; backlog mode never invokes merge/land.
- **R7:** Idempotent surfacing — re-triaging a parked item does not duplicate questions/comments; an answered question causes the next tick to re-triage and proceed.
- **R8:** A backlog-wide ready scan exists (`flowctl ready --all` or equivalent) returning open items with triage/dep/ready state; pilot consumes it for selection.
- **R9:** A per-tick decision log records each action (promote/spec/ask/dep/advance/escalate) + token cost, yielding factory metrics: % moved with no question / one async answer / parked, and cost per change.
- **R10:** Verdict grammar extended (`TRIAGED`/`PROMOTED`/`ADVANCED`/`ASKED`/`IDLE`/`NEEDS_HUMAN`) and documented for `/loop` + `/goal` drivers.
- **R11:** Backlog-mode workflow lives in its own reference file; `SKILL.md`'s core single-tick contract stays thin; docs updated (pilot `SKILL.md`, `docs/ralph.md`, flow-next.dev page + BOTH navbars + changelog); plugin version bumped.
- **R12:** Cross-platform parity — canonical Claude names; `sync-codex.sh` regenerates cleanly; `/goal` driver parity verified.

## Boundaries
<!-- scope: business -->

- **Not a new skill / command** — a config-gated mode on pilot. The separate-skill ("foreman") proposal is explicitly rejected.
- **Not a loop runner** — `/loop` and `/goal` own repetition; backlog mode is a smarter tick, not a new primitive.
- **Never merges** — land stays human-gated; the merge consent boundary is untouched.
- **Not prospect** — prospect invents *new* work; backlog mode manages the *existing* open backlog.
- **Not interactive interview** — surfacing is async (spec + tracker), never a blocking prompt.
- **Does not author specs** — `capture`/`interview` are human-gated prerequisites that must run before a ticket is workable; triage surfaces "needs a spec" as a gap and parks, it never auto-writes one (may augment an obvious blank in an existing spec only). The autonomous span is *workable spec → draft PR*, not *ticket → draft PR*.
- **Jira comment projection out of scope** until a Jira adapter exists (spec-only questions meanwhile).
- **Self-improvement *synthesis* is a follow-on** — this spec ships the decision-log substrate + metrics readout; the agent that mines the log into spec-template / plan patches is a separate, later spec.

## Decision Context
<!-- scope: both -->

### Motivation
<!-- scope: business -->

The Warp *"factory engineers, not product engineers"* memo (2026-06): build the factory, measure **% shipped automatically / (inference + human cost)**, agents do triage → spec → implement → review → verify → monitor with humans stepping in only where needed. flow-next already has the conveyor (pilot/land/Ralph) and the two-way tracker channel (tracker-sync); the gaps are (a) a standing backlog scheduler in front of the ready gate, (b) an async human-in-the-loop valve so "stuck" becomes a question not a stall, (c) a factory-efficiency readout. The seductive-but-rejected part of the memo ("1300 ready issues — just let an agent rip") is precisely what flow-next's gated discipline guards against; this spec keeps the merge gate human and makes the *only* erosion of the consent boundary an **async, auditable question**, not an open-loop fire-hose.

### Implementation Tradeoffs
<!-- scope: technical -->

- **Mode-on-pilot over separate skill:** the full-auto reframe removed the consent boundary that justified a split; pilot already selects across the backlog and walks a pipeline, so this is a leftward pipeline extension, not a new altitude. One `/loop` target, one verdict grammar, one mental model. Cost: pilot's `SKILL.md` grows — mitigated by a dedicated reference file. (Earlier "foreman above pilot" considered and rejected.)
- **Full-auto default + async-surface valve over propose-and-confirm gate:** a pre-gate would duplicate what prompting already gives; surfacing-on-block is the memo's semi-automation realized as a conversation, and yields the human-touch-point log for free.
- **Surface "needs a spec" over autonomous authoring:** an earlier draft had triage auto-draft a spec for thin tickets. Rejected — `capture`/`interview` are human-gated by nature (capture needs a conversation; interview is interactive), and autonomous scope-invention is exactly the slop the valve guards against. The narrower span (workable spec → draft PR) is both safer and thinner to build; spec authoring stays upstream and human.
- **Config flag (default) overridable per-run (`--backlog`/`--auto`):** config so `/loop /flow-next:pilot` picks it up without arg-threading; flag for ad-hoc override.
- **Default off:** preserves existing pilot/land/Ralph users; opt into the bigger autonomy.
- **Reuse over rebuild:** pilot (the whole `plan → make-pr` executor), land (merge), tracker-sync (channel), flow-next-deps (graph), receipts (log shape). Net-new code is just the wide ready scan + the decision log + the `triage`/`ask` (route + surface) handlers — no spec-authoring engine.

## Strategy Alignment
<!-- STRATEGY.md cross-check at author time -->

- **Ralph autonomous mode track** ("Pilot + land are the default path") — extends pilot to manage the whole open backlog, pushing the consent boundary from before-the-loop to inside-the-loop-on-block. Quality discipline (multi-model review, don't-thrash reflexes, evidence over narration) carries forward unchanged; merge stays gated.
- **Self-improving through normal work track** — the per-tick decision log is the substrate that lets the system measure (and later compound from) its own human-intervention points as a side-effect of running the backlog, no manual ceremony.
- **Cross-platform parity track** — canonical names + sync-codex + `/goal` parity.
- **Key metric "idea-to-merge wall-clock"** — backlog mode directly compresses it by running the upstream stages unattended.

## Conversation Evidence

> user: "push flow-next but also mergefoundry more towards autonomy, perhaps a spec … for a full loop skill that triages then goes all the way to PR and resolver PR without the merge at the end and has more self improvement"
> user: "get all open stuff in flow or the tracker, triage it, check deps, what's next, start working through them"
> user: "the triage step … it triages and on specs/linear/jira tickets it can't work yet, it surfaces the gap to the human via comment or open questions in the spec"
> user: "i didn't mean that we should make our own loop command, that's a primitive in claude code, and we have goal in codex … a skill that ties them together, or we revamp pilot to do more"
> user (consent dial): "flow-next is already usable in a semi automated way … we should make these optional things full auto if possible with an option to surface things to a human via the tracker sync … i'm not sure if this is an extra skill or an additional optional workflow inside pilot?"
> user (trigger surface): "i would do a config flag that can be overwritten ofc by adding --backlog or --auto"

Source: Warp *"factory engineers — not product engineers"* memo (2026-06), shared by Gordon. Reference autonomy primitives already shipped: `/flow-next:pilot` (fn-59), `/flow-next:land` (fn-60).
