## Conversation Evidence

> user: "a the linear/jira/github sync stuff right? i already do linear manually in the workunits/sapient project ... some open questions here are would we also sync the tasks after the plan step, do we sync on spec complettion, make-pr, resolve-pr etc, ie. updating the mirror with comments etc"
> user: "how does openai symphony do it, i think they just use linear to start agents? check"
> user: "yes we should capture both but we should do linear first, then github"
> user: "with your spec stuff, although we shouldnt blindly copy what i did in the workunits project, for example we dont have explicit 'merge/sync' there i think"
> user: "the body text sync will be agentic via the agent harness so it can be two-way surely, also play the flows in your head, ie. either someone specs something in flow-next and syncs to linear or a PM/PO puts a vague spec/issue in linear that another PO/Dev syncs into flow-next and does a bunch of steps up to plan and it always gets synced back etc"
> [context: workunits-mvp/CLAUDE.md manual protocol — Linear canonical; Flow local; copy spec body 1:1 both ways; Linear owns backlog metadata/status/comments, Flow owns local task decomposition; attach evidence to Linear on completion. No conflict detection, no lastSyncedAt, no merge.]
> [context: Ray Fernando running-bug-review-board issue-trackers.md (Apache-2.0) — discovery ceremony (detect/surface/ask/never-assume), per-item Tracker/<type> + lastSyncedAt, push/pull/reconcile with field-level who-wins rules, enumerate-only helper scripts, createLocalForUntracked: ask.]
> [context: OpenAI Symphony — Linear board as finite-state-machine / control plane; daemon polls, claims issues, spawns Codex agents, opens PRs linked back. Mirror-image of flow-next (Symphony = Linear canonical + thin WORKFLOW.md; flow-next = spec canonical). Sources: openai/symphony.]

## Goal & Context
<!-- scope: business -->
<!-- Source-tag breakdown: 50% [user] / 35% [paraphrase] / 15% [inferred] -->

flow-next specs (`.flow/specs/<id>.md`) are markdown-of-record but isolated from where teams live (Linear / Jira / GitHub). Gordon already runs this sync by hand in the workunits/Sapient project (Linear canonical; Flow local; copy the spec body 1:1 both ways; attach evidence on completion) — but that manual protocol has **no real reconciliation**: no conflict detection, no `lastSyncedAt`, no merge. This spec automates a bridge as **projection, not coordination**: the spec stays the single source of truth and the quality layer; the tracker is a **co-editable mirror** for teams that must live in it. "Not coordination" means the tracker never drives flow state or spawns agents (Symphony's control-plane model) — it does NOT mean one-way. Body, status, and comments all sync **two-way**, and body reconciliation is **agentic** (the host agent does a semantic merge, which is exactly what flow-next's "host agent IS the intelligence" architecture is for). This unlocks the key flow: a vague PM/PO issue in Linear is pulled into flow, enriched through capture/interview/plan, and the enrichment **syncs back** to the tracker automatically. The design takes the *decisions* from the workunits practice and the *sync engine* (discovery ceremony, per-item `lastSyncedAt`, field-level reconciliation, surface-diffs-never-overwrite) from Ray Fernando's running-bug-review-board `issue-trackers.md` (Apache-2.0 — credited). **Linear-first** — where the lived demand is (the workunits team + the Symphony/Linear ecosystem) — **GitHub next**.

## Architecture & Data Models
<!-- scope: technical -->

A SKILL drives the sync workflow; thin flowctl plumbing provides atomic helpers — the canonical flow-next split (flowctl owns "enumerate / set-field / validate-config / atomic-write"; the skill, running on the host agent, owns "call the tracker API / reconcile / merge bodies / ask the user on genuine conflict"). Per-item sync state lives in spec metadata, written atomically by flowctl: the tracker id (dedupe key), `lastSyncedAt`, and a **merge-base snapshot** of the body at last sync (the 3-way merge ancestor). Three sync operations (push / pull / reconcile) run across three layers: body (two-way, agentic 3-way merge + format translation between flow's structured spec and the tracker's free-form issue), status/metadata (two-way reconciled), comments/evidence (two-way append). Per-tracker adapters are extensible (Linear first, GitHub next; Jira/Notion later). Canonical skill files use Claude-native tool names; `sync-codex.sh` rewrites for the Codex mirror.

## Edge Cases & Constraints
<!-- scope: technical -->

- **Body merge is agentic, not deterministic** — relies on the host agent for semantic 3-way merge against the `lastSyncedAt` base. The merge-base snapshot is what keeps it reliable (real 3-way, not a 2-way guess); without a stored base the agent would over-surface false conflicts.
- **Format asymmetry:** the flow spec is structured (sections, R-IDs, source tags); the tracker issue body is free-form. Syncing flow→tracker renders/cleans the structure into a readable issue; syncing tracker→flow folds free-text edits into the right flow sections without inventing R-IDs/tags. The agent translates; it does not byte-copy.
- **Ralph / autonomous mode:** confident merges + conflict-free status/comment ops proceed unattended; genuine body contradictions and unresolvable status conflicts NEVER block — they queue for the human.
- **Headless / Codex / cron MCP gap:** interactively-authed MCP (Linear MCP) may be absent in headless/cron runs — degrade to no-op + receipt note, never crash. GitHub-via-`gh` is the headless-robust path.
- **Volume + rate limits:** pull queries batch and stay within tracker rate limits. Real Linear MCP tool names differ from BRB's illustrative ones — verify at build.

## Acceptance Criteria
<!-- scope: both -->

- **R1:** Sync config in `.flow/` records: tracker type (`linear` first, `github` next), per-event sync policy, a per-tracker block (team / project id, label / priority map), and a conflict-tiebreak default (`flow-wins` | `tracker-wins` | `always-ask`) for the rare unresolvable case. Forward-compatible (version field; unknown keys ignored). [paraphrase]
- **R2:** Discovery ceremony — detect tracker signals (Linear MCP registered, `LINEAR_API_KEY`, `gh auth`, `*.atlassian.net`), surface present AND absent, ASK the user, never assume; write config only on confirmation, with provenance. The ceremony configures *which* tracker/team, NOT *where the user must start* — the entry point is flexible: author in flow and push, or link an existing tracker issue ad-hoc (e.g. "grab issue X and spec it") via an already-installed MCP. The bridge attaches sync state on link rather than imposing a fixed starting point. [user]/[paraphrase]
- **R3:** Grain — one flow spec maps to one tracker issue; tasks stay flow-local by default (optionally rendered as a checklist inside the issue body, NOT as sub-issues). [user]/[paraphrase]
- **R4:** Per-item sync state — spec metadata carries the tracker id (dedupe key), `lastSyncedAt`, and a body merge-base snapshot at last sync; flowctl owns the atomic write. [paraphrase]
- **R5:** Enumerate-only flowctl helpers list specs needing push (no tracker id) and stale specs (`lastSyncedAt` old / missing); the SKILL performs the actual tracker API calls, body merge, and reconciliation (flowctl enumerates / validates / atomic-writes; agent acts / merges / judges / asks). [paraphrase]
- **R6:** Body sync is **two-way**, reconciled **agentically** — not a text copy. The host agent reads both bodies + the `lastSyncedAt` merge-base (3-way: base vs flow-side vs tracker-side), folds non-conflicting changes from each side together (e.g. PM clarifies the goal in Linear while a dev adds acceptance criteria in flow → both preserved), and **translates between formats** (flow's structured spec / R-IDs ↔ the tracker's free-form issue body). Enrichment done in flow (capture/interview/plan) flows back to the tracker; tracker edits fold into the right flow sections. [user]/[paraphrase]
- **R7:** Status / priority / metadata sync is two-way + reconciled with explicit who-wins rules (tracker wins `done`/`verified`; flow wins `in-progress`; priority + `deferred`/`wontfix` surface to the user, never auto-changed). [paraphrase]
- **R8:** Comments / evidence sync is two-way append — flow lifecycle events post structured comments to the issue; tracker comments pull into the spec's sync log; appends only (no conflict). [paraphrase]
- **R9:** Only a genuine semantic contradiction the agent can't confidently resolve (both sides rewrote the same content to mean different things) is surfaced as a **focused, scoped** conflict for the human — never the whole body, never a silent overwrite. Interactive: show the merged body for confirmation before write-back. Ralph/autonomous: confident merges proceed; genuine conflicts queue for the human (R11). [user]/[paraphrase]
- **R10:** Lifecycle sync points — capture/interview: spec push/pull + merge; plan: no sub-issues by default; per task done: post a status comment + evidence (tests / PR) and move the issue In-Progress on first claim; spec-completion-review: flip the issue Done/verified + post verdict / R-ID coverage; make-pr: attach the PR link to the issue; resolve-pr: optional resolution comment. [user]/[paraphrase]
- **R11:** Ralph-safe — genuine body contradictions and unresolvable status conflicts NEVER block in an autonomous loop; they queue for the human (deferred-decisions list). Autonomous runs apply confident body merges + conflict-free status/comment ops. [paraphrase]
- **R12:** Each sync run emits a proof-of-work receipt (pushed / pulled / merged / updated / diverged / queued), recording every body merge for auditability + rollback, consistent with the existing receipt model. [paraphrase]
- **R13:** Linear adapter first (official Linear MCP); document the headless / Codex / cron caveat (interactively-authed MCP may be absent — degrade to no-op + receipt note); verify real Linear MCP tool names at build. GitHub adapter next (via `gh`, headless-safe). [user]/[paraphrase]
- **R14:** Positioned and documented as projection / co-editable mirror (spec = source of truth; tracker mirrors but never drives the agent loop / spawns agents), NOT coordination; the projection-not-coordination + Linear-first call is recorded as a decision. [paraphrase]
- **R15:** Version bump + docs across THREE surfaces — and because this **changes the documented lifecycle flows** (a tracker dimension now rides on capture / interview / plan / work / make-pr), the flow-next.dev **guide / workflow pages need real edits, not just a changelog line**: (a) **repo** — a new sync reference, `flowctl.md` (sync helpers), `teams.md` (tracker bridge + Symphony contrast), CHANGELOG, root README, CLAUDE.md "where to look", `.flow/usage.md`; (b) **flow-next.dev** (`~/work/flow-next.dev`) — a new tracker-sync docs page **plus updates to the affected guide / lifecycle walkthrough pages** (each flow step gains an **optional, clearly-marked opt-in** tracker-sync touchpoint — not everyone runs project-management software, so the no-tracker path stays the documented default and is shown unchanged) + changelog entry, run the `pnpm build` gate; (c) **mickel.tech** (`~/work/mickel.tech`) — the flow-next app page, **maintainer-only (Gordon updates post-merge; contributor PRs skip it)**. [inferred]
- **R16:** Identity / naming alignment — for **tracker-first / synced specs, the flow spec id adopts the tracker key as its handle** (e.g. `wor-17-<slug>`, tasks `wor-17.M`) instead of a fresh `fn-NN`, matching the manual workunits convention (`wor-2-…`) so the two schemes don't diverge. For flow-first specs (no tracker, or pushed out), the flow id stays the handle and the tracker issue carries it back (a `flow:<id>` label or `[<id>]` title prefix). Either way each side references the other (flow stores the tracker id per R4) and titles stay 1:1 via body sync. This interlocks with the separate id-scheme change (deprecating the sequential `fn-NN` number) — once that lands, the tracker key simply *is* the handle for synced specs; until then, synced specs carry the tracker key as an alias. [user]/[paraphrase]

## Boundaries
<!-- scope: business -->

- **Fully opt-in** — with no tracker configured, the lifecycle skills (capture / interview / plan / work / make-pr) behave exactly as today: zero new steps, zero new prerequisites, project-management software not assumed. The bridge activates ONLY after the discovery ceremony writes a tracker config; it adds nothing to the base / zero-dep flow (preserves the STRATEGY zero-dep base contract). Tracker touchpoints appear in the guides as optional steps, never mandatory.
- NOT a daemon / control-plane like OpenAI Symphony (Linear-as-state-machine that *spawns* agents / drives flow state) — this is a projection bridge; flow-next stays spec-canonical and owns the agent loop. A Symphony-like trigger layer (a poller / webhook listener that watches tracker state and fires flow-next actions) is a **separable future addition on top of this bridge** — explicitly out of scope here, and a separate strategy decision because it would make the tracker a trigger, revisiting the projection-not-coordination line. The sync bridge (linkage + state + headless flowctl actions) is the substrate that makes it cheap to add later.
- NOT auto-creating tracker sub-issues per flow task (tasks stay flow-local).
- NOT auto-importing tracker-only issues into flow without asking (default "ask").
- NOT a deterministic text-merge engine — body reconciliation is agentic; only genuine contradictions surface for a human, never a silent overwrite.
- Jira / Notion adapters are out of scope here (Linear + GitHub only); the adapter shape stays extensible.
- Does NOT copy the workunits manual full-body-overwrite convention — replaced by the agentic 3-way reconciliation + merge base.

## Decision Context
<!-- scope: both — conditionally substructured -->

### Motivation
Teams that already live in Linear (the workunits team; the Symphony/Linear ecosystem) need flow-next to project status outward AND pull vague issues in to enrich them — without giving up the spec as the quality layer — "Symphony, but with real specs + re-anchoring + receipts." Linear-first because that is where the real, lived demand is. Framed as projection (co-editable mirror, not control plane) so it complements, rather than contradicts, the strategy thesis that the spec carries the weight upstream.

### Implementation Tradeoffs
Body reconciliation is **agentic, not a deterministic merge engine** — a direct application of the CLAUDE.md "Architecture: agentic vs deterministic" rule ("the host agent IS the intelligence; default to skill-based, reach for deterministic flowctl only when there's a real reason"; its anti-pattern list literally names "building a deterministic fallback engine for when the LLM is unavailable"). A dumb 2-way text copy would lose data (forcing the one-way compromise); the agent instead does a semantic 3-way merge against the `lastSyncedAt` base and translates between flow's structured spec and the tracker's free-form issue. The split stays clean: flowctl owns the deterministic parts (enumerate, write `lastSyncedAt`, store the merge-base snapshot, validate config), the agent owns the judgment (the merge). This is what makes the tracker-first enrichment flow work end-to-end: vague Linear issue → pulled into flow → fleshed out via capture/interview/plan → synced back. The entry point is intentionally loose — most users already have a tracker MCP installed and can just say "grab issue X and spec it," so the bridge attaches sync state on link rather than gating on a formal start. Only genuine contradictions surface (scoped, not whole-body); the receipt records every merge for audit/rollback; Ralph queues conflicts rather than blocking. GitHub-via-`gh` is the headless-robust path, but Linear-via-MCP ships first to match demand, accepting the headless-MCP caveat as a documented constraint.

## Requirement coverage

| R-ID | Task |
|------|------|
| R1 | fn-52.M (TBD — populate via /flow-next:plan; stage Linear-first then GitHub) |
| R2 | fn-52.M (TBD) |
| R3 | fn-52.M (TBD) |
| R4 | fn-52.M (TBD) |
| R5 | fn-52.M (TBD) |
| R6 | fn-52.M (TBD) |
| R7 | fn-52.M (TBD) |
| R8 | fn-52.M (TBD) |
| R9 | fn-52.M (TBD) |
| R10 | fn-52.M (TBD) |
| R11 | fn-52.M (TBD) |
| R12 | fn-52.M (TBD) |
| R13 | fn-52.M (TBD) |
| R14 | fn-52.M (TBD) |
| R15 | fn-52.M (TBD) |
| R16 | fn-52.M (TBD) |
