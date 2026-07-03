---
satisfies: [R14]
---

## Description

The ship gate (user decision 2026-07-03: no config — prove it or don't ship it). Extend the fn-83.2 methodology to three real external flow-managed repos and render the verdict: zero false skips everywhere AND ≥50% aggregate skip-rate on true negatives from disjoint repos ⇒ the gate ships unconditionally; otherwise the gate does not ship.

**Size:** M
**Files:** `optimization/plan-sync-gate/cross-repo/` (methodology, scenario POINTERS + aggregate results only — NO external content), maintainer-local working dir for raw keys

## Approach

- **Repos + sampling:** `~/work/DocIQ-Sphere` (disjoint multi-stack — the representative target), `~/work/gno`, `~/work/transcribe`. Per repo ≥8 scenarios: real completed tasks that had downstream todo tasks at completion time. Reconstruct at pinned full SHAs via `git worktree add --detach` in the EXTERNAL repo (read-only; clean up after). Older evidence lacks `base_commit` — derive base = first-evidence-commit^ (document per scenario); tasks with unrecoverable evidence: log + skip (not silently).
- **Answer keys:** same procedure as fn-83.2 (real `agents/plan-sync.md` via `claude -p --model opus`, DRY_RUN, full input contract with at-SHA husks from the external repo, N=3 majority, wobble⇒drift-positive; resolved model recorded). Keys for external repos stay maintainer-local (privacy) — committed artifacts: methodology README, scenario pointer table (repo, SHA, task id, derivation notes), aggregate per-repo results (counts, rates), and the verdict.
- **Probe runs:** deterministic, against the same reconstructed states. Record per-repo: false-skip count (must be 0), skip-rate on true negatives, spawn reasons histogram (which lattice arm fired — tells us WHERE yield is lost if low).
- **Verdict:** PASS (0 false skips everywhere AND aggregate true-negative skip-rate ≥50% on DocIQ-Sphere+gno+transcribe) ⇒ record in results + unblock fn-83.4's gate wiring. FAIL ⇒ record evidence + explicitly mark fn-83.4 to ship without gate wiring (unconditional spawn); probe/ledger/harness remain dev assets. Either way: results.tsv rows + optimization-log.md row.
- **Privacy check (hard):** grep the committed diff for external-repo content before commit — paths under `optimization/plan-sync-gate/cross-repo/` must contain no DocIQ/gno/transcribe prose beyond file paths + ids + SHAs.

## Investigation targets

**Required:**
- `optimization/plan-sync-gate/README.md` + `builders.py` + `answer-key.json` — the fn-83.2 machinery to extend
- External repos' `.flow/runtime` evidence shapes (older flowctl versions — verify `load_task_with_state` compatibility per repo before sampling)

## Key context

Cost note: ~72-90 real-agent runs ≈ same order as fn-83.2 (~$100). The spawn-reason histogram is as valuable as the rate — if DocIQ also shows 0% skip, the "monolith vs sliced" hypothesis is dead and the gate should not ship; if it shows healthy skips, the flow-next 0% is confirmed as worst-case shape.

## Acceptance

- [ ] ≥8 replayed scenarios per external repo (or documented shortfall with reasons), pinned SHAs, derivation notes
- [ ] Frozen external answer keys generated per the fn-83.2 procedure (N=3, wobble⇒positive, model recorded); kept maintainer-local; regeneration procedure documented
- [ ] Zero false skips across ALL repos (hard); aggregate true-negative skip-rate + per-repo rates + spawn-reason histogram reported
- [ ] Explicit PASS/FAIL verdict recorded with its consequence for fn-83.4 wiring
- [ ] No external-repo content committed (privacy grep clean); results.tsv + optimization-log rows

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
