---
satisfies: [R12]
---

## Description
Cross-platform parity + autonomous-safety verification — its OWN task because Codex-mirror regen exposes latent canonical issues (memory `mirror-regen-exposes-latent-canonical`: land/fn-60 took **4** NEEDS_WORK rounds from mirror regen — never an afterthought).
- Run `scripts/sync-codex.sh`; **impl-review the regenerated mirror**: the R14 fix + the new `triage`/`ask` stages + the AskUserQuestion→numbered-prompt rewrite must survive; no Claude-native tool-name leakage.
- `/goal` (Codex) parity for the new `TRIAGED`/`ASKED` verdict line (and confirm `NO_WORK`/`DEFERRED_TO_LAND` still grep-able for stop-clauses).
- Autonomous-safety tests: under `FLOW_AUTONOMOUS=1` / `mode:autonomous`, backlog mode never reaches `AskUserQuestion`, never invokes merge/land, never authors a spec; the gate-off path is byte-identical.

**Size:** M · deps .4
**Files:** `plugins/flow-next/codex/**` (regenerated), `plugins/flow-next/tests/test_*.py`, `scripts/sync-codex.sh` (only if a per-skill block needs adding)

## Investigation targets
**Required:**
- `scripts/sync-codex.sh` — the canonical→mirror rewrite rules (AskUserQuestion, Task→spawn_agent, tool names)
- `plugins/flow-next/codex/skills/flow-next-pilot/` — the regenerated mirror to impl-review
- `plugins/flow-next/tests/` — existing smoke/shape tests to extend

## Acceptance
- [ ] `sync-codex.sh` regenerates cleanly; the Codex mirror carries the R14 fix + `triage`/`ask` stages; `AskUserQuestion` rewritten to the numbered-prompt form; zero Claude-native tool leakage in the mirror.
- [ ] `/goal` driver parity: TRIAGED/ASKED documented for stop-clauses; NO_WORK + DEFERRED_TO_LAND still present + grep-able.
- [ ] autonomous-safety tests pass: under the autonomy marker, backlog mode never reaches AskUserQuestion, never invokes merge/land, never authors a spec; gate-off path byte-identical.

## Done summary
Regenerated the Codex mirror (sync-codex.sh) for pilot backlog mode + tracker-sync and fixed three latent mirror defects the regen exposed: the R2 numbered-prompt instruction block was mis-injected into negation-only autonomy prose (pilot's Forbidden/Phase-3.5 sections AND before tracker-sync's Phase-0 R14 invariant — both contradict the never-prompt contract), a bold-led maintainer breadcrumb wasn't stripped, and a wrong-article artifact. Hardened sync-codex.sh's is_negative_context() (case-insensitive, full reach-family + modal) and breadcrumb stripper, and added a 20-case autonomous-safety prose-contract test (test_pilot_backlog_mirror_safety.py) locking cross-platform parity (R14 fix + triage/ask + ASKED survive; zero Claude-native leakage; /goal NO_WORK/DEFERRED_TO_LAND grep-able; TRIAGED diagnostic-only) and the no-prompt / never-merge / never-author / byte-identical-gate-off invariants (R12; verifies R6/R7). Registered the fn-68 test trio in CI. RP impl-review: SHIP (1 NEEDS_WORK round — it caught the tracker-sync instance).
## Evidence
- Commits: 26aeadd9, f78f060783f2c74f7aada673137e84426ab43e28
- Tests: python3 -m unittest discover -s plugins/flow-next/tests -p test_pilot_backlog_mirror_safety.py (20 cases), python3 -m unittest discover -s plugins/flow-next/tests -p test_pilot_backlog_substrate.py (32), python3 -m unittest discover -s plugins/flow-next/tests -p test_tracker_sync_backlog_mode.py (23), bash scripts/sync-codex.sh (21 validators green, idempotent)
- PRs: