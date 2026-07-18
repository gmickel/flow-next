# Tracker background-dispatch discipline

Loaded by tracker touchpoint gates when a tracker lifecycle operation may be
dispatched off the critical path. This file is the sole statement of the rules.

## The discipline

1. When a tracker gate resolves to a COMMENT op on a LINKED spec and the host qualifies on the capability ladder below (Tier A or Tier B), dispatch it to a `tracker-runner` subagent - Tier A in the background (keep working), Tier B awaited. Tier C runs it inline.
2. Fire-and-forget only when a later `sync check` this session will audit the receipt; otherwise await the runner before your skill's summary.
3. Before ANY `sync check`, and before any state-shaped tracker work on a spec, await your outstanding dispatches for that spec.
4. An UNLINKED spec's first touch is state-shaped (create-if-unlinked writes link state) - run it inline.
5. When unsure, await: it costs seconds.

## MUST invariant 1 - single state-writer

Never let two operations touch one spec's sync state concurrently - a comment fork writes only its own receipt file and the tracker comment (a one-way lifecycle append NEVER advances `lastSyncedAt` - comments-sync.md scopes that advance to two-way reconciles), so linked-spec comment forks may overlap freely, but anything that writes link/merge-base/lastSyncedAt state runs alone.

## MUST invariant 2 - join-before-audit

No `sync check` runs with a dispatch outstanding for the audited spec - this is the demonstrated false-MISSING duplicate-retro-fire race.

## Dispatch contract

Pass the runner `OPERATION` (for example, `comment`), `SPEC_ID`, `EVENT` (the perEvent key, for example `work.done`), `FLOWCTL` (path), `DISPATCH: forked`, plus the host run's autonomy markers. Parse its terminal line `TRACKER_RUNNER=<status> spec=<id> note="..."` from the LAST line of output, never as the sole line; status is `pushed|pulled|merged|updated|diverged|queued|errored|noop`.

## Join mechanics - Tier A, Claude Code

Joins are notification-driven: a completed background subagent re-invokes the host; a bounded non-blocking status poll is the fallback. `TaskOutput(block=true)` on agent tasks is FORBIDDEN on Claude Code (live-tested: it dumps the subagent transcript into host context, defeating isolation).

## Host capability ladder + degradation

Tier A - background dispatch + notification join: Claude Code (verified live). Tier B - isolated-but-awaited: the host spawns the runner and AWAITS its terminal line (ordinary fork-join subagents, no async machinery) - context isolation preserved, overlap forgone; Cursor and Codex qualify (Codex probed live 2026-07-18, codex-cli 0.144.1, exec surface; the runner inherits the session model). On Tier B every dispatch is awaited, so the join invariant is trivially satisfied and fire-and-forget does not exist there. Tier C - inline exactly as today: probe failed, runner missing, or dispatch errored - degrade loudly, never silently.

## Recovery

The host tracks its own outstanding dispatches in-context; after compaction, receipts on disk are the truth (`flowctl sync check --since`).
