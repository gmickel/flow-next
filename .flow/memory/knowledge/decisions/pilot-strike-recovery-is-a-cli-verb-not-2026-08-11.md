---
title: "Pilot strike recovery is a CLI verb, not board-native transition detection"
date: "2026-08-11"
track: knowledge
category: decisions
module: plugins/flow-next/skills/flow-next-pilot
tags: [pilot, strikes, tracker-sync, readyState, fn-184]
applies_when: "Someone proposes clearing pilot strikes from board state / tracker transitions, or an armed-readyState operator asks for board-only strike recovery."
related_to: [knowledge/decisions/tracker-sync-is-projection-not-2026-06-01]
---

## Decision

Pilot strike recovery under an armed `tracker.readyState` is a deterministic CLI verb (`flowctl pilot strikes clear <spec-id>`), NOT board-native transition detection. Decided in fn-184 (#325), 2026-08-11.

## The deferred alternative

An observed-transition bit in the strikes ledger: each pilot tick already sees current board state, so a tick observing the struck issue OUT of the ready lane could record `leftReadySinceStrike=true`, and a later projection-set ready would then count as a human re-bless. Board-native (preserves "board is the single control plane" ergonomics for armed repos), no new verb.

## Why deferred

- **Tick-granularity hole:** a fast out-and-back between ticks is silently missed - the human performed the documented recovery and nothing happened, with no error anywhere. The verb has no such window.
- **Ambiguity is structural, not incidental:** the reporter's phase-C measurement showed a deliberate out-and-back is byte-identical to a projection echo in every durable artifact; the transition bit only narrows this to "observed by a tick", it does not remove it.
- **Semantics creep:** the ledger is a plain counter today; observation state would couple it to tick scheduling.
- Strikes are pilot state, not readiness state, so a CLI clear does not dent the board-as-readiness-control-plane doctrine.

## Reopen when

A real consumer reports the CLI verb as an operational burden (e.g. board-only operators with no repo shell access). The transition bit is then the design to evaluate first, with the tick-granularity caveat stated up front.
