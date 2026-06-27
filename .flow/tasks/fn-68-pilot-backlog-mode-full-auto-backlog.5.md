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
TBD

## Evidence
- Commits:
- Tests:
- PRs:
