# Muse + Wonder skips the configured implementation review on risky defect fixes

Stub, for discussion before a fix. Found by the Muse arms pilot (agent-evals
`study/muse-arms-2026-10`, `studies/muse-arms-2026-10/REPORT.md`, 2026-10-13).

## Problem

On flow-next 8.6.0 with `review.backend=codex:gpt-6-astra:high` pinned, Claude Code + Opus 5.5 ran
the configured cross-model review on the hard-bug case (flow-swarm-211) in 2/2 draws: defect →
direct fix with the failing test committed first → codex review (3 reviewers) → fix → re-review.
Muse Code 1.4.6 + Wonder / Wonder Full ran it in 0/4 draws on the same case and prepared repo:

| draw | what Muse did at the review step |
|---|---|
| A b1 (Wonder Full) | `stage: impl-review - skipped(error: configured codex backend not invoked this session)` |
| A rerun (Wonder Full) | read the impl-review skill, then `skipped(reach: needs a committed branch; change is uncommitted)` |
| B b1 (Wonder) | spawned a Muse subagent as "reviewer" (same family, not the configured backend), reported `review — ran` |
| B rerun (Wonder) | no stage lines at all |

No Muse draw committed its work (changes left uncommitted on `main`), which is what made the
"needs a committed branch" reason true. On the simple-bug case every arm on both hosts skipped
review by risk, as intended. The codex CLI was present and authenticated in every sandbox (Claude
Code's draws used it from the same setup).

Effect: on Muse the cross-model review gate silently does not run for changes that need it, and
the Muse-vs-Claude comparison partly measures "with review" vs "without".

## Hypotheses (unverified)

- **H1 commit step:** Wonder does not follow work's commit discipline on the direct/defect route,
  so review's reach check fails and is reported as a skip instead of committing first.
- **H2 host note:** setup's Muse host note ("Review: host fails closed …", "review CLIs need
  `--disable-sandbox`") reads to Wonder as "review is not available here".
- **H3 risk wording:** the defect route's review trigger is judged on a model's own risk call;
  Wonder rates the change below the bar or treats review as optional when attended and no PR is
  requested.
- **H4 substitution:** nothing tells a non-Claude host that a native subagent is not a stand-in
  for the configured backend.

## Repro (small, cheap: regular Wonder, no Full quota)

1. Throwaway repo with flow-next 8.6.0 set up for Muse (`install-muse.sh`), `review.backend`
   pinned to `codex:gpt-6-astra:high`, codex logged in, a small but stateful bug (persisted state +
   in-memory semantics, like flow-swarm-211's session-write fix) with a failing test available.
2. `muse exec --disable-sandbox --trust-workspace --model muse-wonder-1.0 --json
   "/flow-next:flow <bug report>"` × 3; record per run: commit made? impl-review skill read?
   `codex` invoked? stage line printed.
3. Same with Claude Code + Opus as control (expect commit + codex review).
4. Ablate one at a time to separate H1-H4: commit pre-made by the harness (H1); Muse host note
   removed from AGENTS.md (H2); request states the change touches persisted state (H3).
5. The agent-evals harness can also do it directly: `muse_round.py --cases flow-swarm-211
   --arms B --batches 3` (about 10 min per draw).

## Acceptance (for the eventual fix)

- **R1:** On Muse + Wonder, a change that flow-next's own route rules send to review runs the
  configured backend, or stops with an explicit `NEEDS_HUMAN`/skip reason that names the real
  blocker; never a same-family substitute reported as the review.
- **R2:** Work commits before review on every host, so review's reach check is not the reason
  for a skip.
- **R3:** No change in Claude Code / Codex behaviour (Claude Code control still reviews 2/2).
