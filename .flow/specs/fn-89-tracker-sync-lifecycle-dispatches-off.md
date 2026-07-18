# fn-89-tracker-sync-lifecycle-dispatches-off Tracker-sync lifecycle dispatches off the critical path (background runner)

> REWRITTEN IN FULL 2026-07-18 (maintainer-directed) after the same-day soundness review: from per-touchpoint choreography to doctrine + two invariants. R-IDs are preserved where the reviewed number's theme survives, marked superseded where v1 descopes them (numbering gaps are deliberate - never compact), and extended with R9+.

## Goal & Context

Tracker touchpoints run inline in host skills: the host context absorbs transport echoes (MCP `save_issue` echoes ~10k-token issue bodies back, twice per body write) and, for genuinely-changed reconciles, ~13-17k tokens of merge doctrine; wall-clock stalls seconds per touchpoint between tasks.

Two mitigations landed since this spec was first authored and re-scope the win: the R22 unchanged-both-sides short-circuit already elides the doctrine load for steady-state reconciles inline (tracker-sync steps.md:365-377), and the GraphQL rung's curl-capture pattern never echoes bodies into host context. What remains worth taking off the critical path in v1 is the cheap, high-frequency case: comment-shaped lifecycle ops - and the wall-clock overlap while a worker or the user is the long pole.

Design philosophy (2026-07-18 discussion, binding): the host agent is intelligent - give it a five-sentence discipline and two MUST invariants in one shared reference, hard-contract only what live testing proved soft prose cannot hold (the runner's output line), and descope everything whose measured cost exceeds its benefit (state-shaped forks measured ~150k subagent tokens in rehearsal vs an R22-mitigated inline path).

## Overview & Approach

1. **Shared discipline reference `plugins/flow-next/references/tracker-dispatch.md` (NEW, <=50 lines)** - the single place the rules live; every touchpoint's dispatch line just points here (fn-82 progressive-disclosure shape, like `references/html-artifacts.md`). Content, in full:
   - **The discipline (five sentences):** When a tracker gate resolves to a COMMENT op on a LINKED spec and the host is Claude Code, dispatch it to a background `tracker-runner` subagent and keep working. Fire-and-forget only when a later `sync check` this session will audit the receipt; otherwise await the runner before your skill's summary. Before ANY `sync check`, and before any state-shaped tracker work on a spec, await your outstanding dispatches for that spec. An UNLINKED spec's first touch is state-shaped (create-if-unlinked writes link state) - run it inline. When unsure, await: it costs seconds.
   - **MUST invariant 1 (single state-writer):** never let two operations touch one spec's sync state concurrently - a comment fork writes only its own receipt file and the tracker comment, so linked-spec comment forks may overlap freely, but anything that writes link/merge-base/lastSyncedAt state runs alone.
   - **MUST invariant 2 (join-before-audit):** no `sync check` runs with a dispatch outstanding for the audited spec - the demonstrated false-MISSING duplicate-retro-fire race.
   - **Join mechanics:** joins are notification-driven (a completed background subagent re-invokes the host); a bounded non-blocking status poll is the fallback; `TaskOutput(block=true)` on agent tasks is FORBIDDEN (live-tested: it dumps the subagent transcript into host context, defeating the isolation).
   - **Host capability ladder + degradation (revised 2026-07-18, maintainer discussion):** three tiers, resolved by a cheap probe. Tier A - background dispatch + notification join: Claude Code (verified live). Tier B - isolated-but-awaited: the host spawns the runner and AWAITS its terminal line (ordinary fork-join subagents; no async machinery) - context isolation preserved, overlap forgone; Cursor qualifies (fork-join fan-out verified on-platform), Codex qualifies PENDING one interactive-surface probe (open issue openai/codex#33267 reports parent-turn-unusable child results under `codex exec` - verify the interactive CLI surface before enabling; model inheritance is fine, the runner simply runs the session model). Tier C - inline exactly as today: probe failed, runner missing, or dispatch errored - loudly, never silently. On Tier B every dispatch is awaited, so the join invariant is trivially satisfied and fire-and-forget does not exist there.
   - **Recovery:** the host tracks its own outstanding dispatches in-context; after compaction, receipts on disk are the truth (`sync check --since`).
2. **Runner agent `agents/tracker-runner.md` (NEW)** - `model: sonnet` (scout-tier convention; live-verified sufficient for the hardest op class in rehearsal), `disallowedTools: Task` (keeps Write/Edit/Bash - the `pr-comment-resolver`/`worker` precedent, which use `model: inherit`; the sonnet pin here follows the scout tiering instead, deliberately). Inputs: `OPERATION` / `SPEC_ID` / `EVENT` / `FLOWCTL` / `DISPATCH: forked` + autonomy markers. It executes the EXISTING `flow-next-tracker-sync` skill body for that ONE op (no second implementation) with `forked => queue-not-ask` folded into tracker-sync's single RALPH gate (one-line change, steps.md:21-26). Output: a parseable TERMINAL line the host reads as the LAST line (live-tested: sole-line discipline fails, agents narrate):
   `TRACKER_RUNNER=<status> spec=<id> note="<one line>"` - `<status>` = the full receipt enum `pushed|pulled|merged|updated|diverged|queued|errored|noop`.
3. **v1 scope = comment-shaped ops on linked specs, Claude Code only.** Gates whose RESOLVED op is `comment` (work.done, resolvePr, qa, and completionReview/makePr on repos whose leaf is `comment`) gain one conditional sentence pointing at the reference. Everything else - reconcile/push leaves, state-shaped ops, unlinked first touches, ceremonies, manual runs, interactive conflict resolution - runs inline byte-identically to today. No config leaf (inline is the natural degrade; add a kill-switch only if dogfood demands one).
4. **Pre-audit join sentences** (one line each, pointing at the reference) before the `sync check` call sites: work Phase 5 (phases.md:528 region), make-pr section 5.7 (create-and-finalize.md:596 region), capture Phase 6 (workflow.md:862-889 region) - the last two matter for the cross-skill straddle (a work.done fork still in flight when a later skill audits the same spec in-session).
5. **sync-codex plumbing:** the agents glob auto-generates `codex/agents/tracker-runner.toml` (loop at sync-codex.sh:1402-1437, confirmed glob); `sandbox_for()` (sync-codex.sh:101-107) gains `tracker-runner` -> `workspace-write`; a global `Task flow-next:tracker-runner` -> `tracker_runner` role rewrite + hard-fail guard (the fn-100 transform+guard pattern). The mirror renders the prose with the capability ladder: Codex resolves Tier B (isolated-but-awaited via `spawn_agent`, session-model inheritance - no model steering needed) once the .1 probe passes the interactive surface (openai/codex#33267 caveat is `codex exec`-scoped; verify before enabling), else Tier C inline. True background (Tier A) on Codex stays future work alongside fn-98.
6. **Event-tag hygiene rides along:** the resolve-pr and qa dispatch lines currently lack their `event:` tags (resolve-pr workflow.md:449, qa workflow.md:602 placeholder) - add them so `sync check` can audit those events.

## API Contracts

- **No flowctl changes.** No new config leaves, no locking, receipts/event tags/`sync check` semantics untouched.
- NEW `plugins/flow-next/references/tracker-dispatch.md` (the discipline; <=50 lines).
- NEW `agents/tracker-runner.md` (contract above) + generated `codex/agents/tracker-runner.toml` (workspace-write).
- Touchpoint gates: one added conditional sentence each; join sentences at three audit sites; event tags on resolve-pr/qa.

## Boundaries / non-goals

- State-shaped ops (reconcile, push, create-if-unlinked) stay INLINE in v1 - measured ~150k-token sonnet fork per state-shaped op vs an R22-mitigated inline path; revisit with dogfood data, decision recorded here deliberately.
- `land.merged` stays inline (land is its own loop). Pilot backlog-mode tracker ops (`list-open`/`list-relations`/`question`) are OUT of scope (pilot orchestrates its own ticks).
- Ceremonies, `--dry-run`, manual `/flow-next:tracker-sync` runs, and interactive genuine-conflict resolution stay inline (`AskUserQuestion` is unreachable in forks; forked conflicts queue via `sync defer`, surfaced host-side after the join - interactive only).
- Tier A (background) beyond Claude Code is out of scope for v1 (Codex true-async unverified - fn-98 adjacent; Cursor notification semantics unprobed). Tier B on Codex is gated on the .1 probe. Cross-PROCESS serialization: out of scope (documented limitation).
- No formal ledger data structure - the host's own context is the ledger; receipts are the recovery truth.

## Acceptance Criteria

- **R1:** Comment-shaped touchpoints on LINKED specs, on Claude Code, dispatch to a background `tracker-runner`; the host continues working. Fire-and-forget only where a later in-session `sync check` audits the receipt (work.done, comment-leaf completionReview); awaited before the skill summary where none does (resolvePr, qa). Outcome lines surface in the host's end-of-run summary.
- **R2 (revised - descope):** State-shaped touchpoints (capture/interview/plan reconcile, work.firstClaim push, makePr reconcile) and unlinked-spec first touches run INLINE, byte-identical to today. No fork path exists for them in v1.
- **R3 (revised):** MUST invariant 1 holds: no two concurrent operations on one spec's sync state - linked-spec comment forks may overlap freely (receipts are per-file); an unlinked spec's comment op runs inline; any state-shaped inline op on a spec first awaits that spec's outstanding forks. No formal ledger: host context tracks dispatches; receipts-on-disk recover after compaction.
- **R4 (revised):** MUST invariant 2 holds: pre-audit join sentences at work Phase 5, make-pr section 5.7, capture Phase 6 - each awaits outstanding dispatches for the audited spec before `sync check`. Joins are notification-driven; `TaskOutput(block=true)` on agent tasks is forbidden in the prose.
- **R5:** SUPERSEDED (v1 drops the `tracker.dispatch` config leaf - YAGNI; inline is the degrade path). Number retained as a deliberate gap.
- **R6:** Ceremonies, manual runs, `--dry-run`, and interactive conflict resolution stay inline; a forked dispatch that hits a genuine conflict queues (`sync defer`) and the host - interactive only - may surface it after the join.
- **R7:** The runner executes the existing tracker-sync skill body (no second implementation); `forked => queue-not-ask` is folded into tracker-sync's single RALPH gate as a one-line change; receipts and event-tag semantics unchanged.
- **R8 (revised):** Host capability ladder: Claude Code = Tier A (background + notification join); Cursor = Tier B (isolated-but-awaited, fork-join verified); Codex = Tier B iff the .1 interactive-surface probe passes (parent reads the runner's terminal line cleanly; #33267 caveat), else Tier C inline; Copilot/Droid = Tier C until probed. sync-codex role rewrite + guard + `sandbox_for` workspace-write; full pytest + smoke green; CHANGELOG under `## Unreleased`, no version bump (batched releases).
- **R9:** The runner's output contract is the parseable TERMINAL line `TRACKER_RUNNER=<status> spec=<id> note="..."` with the full receipt enum; every host parse reads the LAST line only (never sole-line discipline - live-test-proven to fail).
- **R10:** resolve-pr and qa dispatch lines carry their `event:` tags (auditable by `sync check`), replacing the bare/placeholder forms.
- **R11:** `plugins/flow-next/references/tracker-dispatch.md` exists, <=50 lines, carrying the five-sentence discipline, both MUST invariants, join mechanics, host gate, degradation, and recovery - and is the ONLY place the rules are stated (gates point at it; no duplicated rule prose at the touchpoints).
- **R12:** A live interleave proof is recorded in the .4 task evidence: one background comment dispatch overlapping host work, notification-driven join, `sync check` clean (no false MISSING, no duplicate retro-fire), terminal line parsed from the last line.

## Early proof point

Task .1 validates the core mechanics (runner contract + terminal-line parse + toml generation) before any touchpoint is converted. If the terminal-line contract cannot be parsed reliably from a sonnet runner, revisit the contract format before .2.

## Requirement coverage

| Req | Description | Task(s) | Gap justification |
|-----|-------------|---------|-------------------|
| R1 | Comment-op background dispatch + await split | .2 | - |
| R2 | State-shaped + unlinked stay inline | .2 | - |
| R3 | MUST 1: single state-writer per spec | .2 | - |
| R4 | MUST 2: pre-audit joins at three sites | .2 | - |
| R5 | (superseded - config leaf dropped) | - | v1 descope, deliberate gap |
| R6 | Inline ceremonies + queue-then-surface conflicts | .2 | - |
| R7 | Runner runs existing skill body; RALPH gate one-liner | .1 | - |
| R8 | Host gate + mirror + gates green + CHANGELOG | .3 | - |
| R9 | Terminal-line output contract | .1 | - |
| R10 | resolve-pr/qa event tags | .2 | - |
| R11 | The shared discipline reference | .1 | - |
| R12 | Live interleave proof | .4 | - |

## Decision Context

- Full rewrite 2026-07-18 after the soundness review (same day, live-tested): sonnet runner executed a real state-shaped reconcile with full doctrine fidelity (including the readiness projection the maintainer's inline shortcuts had skipped) at ~153k subagent tokens - proving the runner concept AND pricing state-shaped forks out of v1. `TaskOutput(block=true)` live-tested as context-hostile on agent tasks -> notification-driven joins. Sole-line output discipline live-tested as unreliable -> terminal-line parse. The old spec's "Codex forbids background jobs" rationale was found to be an RP-specific warning, not a convention. set-merge-base was confirmed single-atomic-write (both halves, one file) - the residual serialization rationale is the lost-update race between overlapping reconciles, not a torn file. Receipts confirmed one-file-per-receipt. The sync-check retro-fire race (false MISSING while a dispatch is in flight) was confirmed real and unprotected today.
- Philosophy shift (maintainer discussion): doctrine + two invariants beats choreography. Every dropped mechanism (dispatch-class taxonomy, formal ledger, config leaf) is recorded above so it is not re-invented without new evidence.
- The old spec's anchor set drifted (2.15.0/2.16.0); current anchors are in the Approach section and were verified 2026-07-18. Re-verify at work time as usual.
