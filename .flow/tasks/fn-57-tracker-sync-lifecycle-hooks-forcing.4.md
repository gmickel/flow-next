---
satisfies: [R2, R4, R5]
---

## Description

Wire the sync check + retro-fire + summary slot into capture and make-pr, and add make-pr §4.6b: the deterministic post-create PR↔issue ref verify/repair that closes the execution-fidelity gap (R4).

**Size:** M
**Files:** `plugins/flow-next/skills/flow-next-capture/workflow.md`, `plugins/flow-next/skills/flow-next-make-pr/workflow.md`

## Approach

**capture** — 5.7 (:700-717) passes `event: capture` to the tracker-sync invocation. Phase 6 footer (:728-789) gains the check block: `--events capture`, `--since` = the spec's `created_at` (on-disk anchor — the spec was created this run in Phase 5; a Phase-6-captured "now" would postdate the 5.7 receipt and false-MISSING). Same one-cycle retro-fire + four-state summary slot as work (spec §Check semantics). Capture is Ralph-blocked, so no stdout-routing concern.

**make-pr** — two additions:
1. **§4.6b ref verify/repair (NEW — nothing exists post-create today):** immediately after the `gh pr create` retry loop (:1346-1380, after :1379, before §4.7 at :1386). When the bridge is active + spec linked: fetch the LIVE body (`gh pr view --json body --jq .body` — never the local `$BODY_FILE`; the repair exists precisely for hand-rolled creates where the local file is stale/absent); test with the SAME whole-line matcher as §4.6a (`grep -qixF "$REF"` — substring matching false-positives on spec paths, see :1335-1338; factor the `REF` derivation + match so the two sites cannot drift); if absent, append-only (`printf '\n\n---\n%s\n'`) and write back via `gh pr edit --body-file -` (gh has NO append flag — read-modify-write, narrow window, accept the documented small race); re-check the 65,536-char cap before writing (a near-cap body + ref can 422); everything `2>/dev/null || true` non-fatal.
2. **Check wiring:** §5.6 (:1561-1586) passes `event: makePr`; Phase 5 final output gains the check block — `--events makePr`, `--since` = the PR's `createdAt` (`gh pr view --json createdAt`). One-cycle retro-fire + four-state summary slot. **Ralph stdout invariant (:1559): stdout is reserved for `PR_URL=<url>` — all check/summary lines to stderr.**

## Investigation targets

**Required:**
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md:1314-1344` — §4.6a (REF derivation :1330-1334, idempotent append :1341-1342, the why-whole-line comment :1335-1338)
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md:1346-1386` — pr-create retry loop + where §4.6b lands
- `plugins/flow-next/skills/flow-next-make-pr/workflow.md:1408-1601` — Phase 5 (footers :1412-1417, :1538-1557; Ralph stdout rule :1559; §5.6 :1561-1586)
- `plugins/flow-next/skills/flow-next-capture/workflow.md:700-789` — 5.7 block + Phase 6 footer
- `.flow/specs/fn-57-tracker-sync-lifecycle-hooks-forcing.md` §Check semantics

**Optional:**
- `plugins/flow-next/skills/flow-next-make-pr/SKILL.md:62-69` — draft/Ralph flag table (update if it gains a verify mention)

## Acceptance

- [ ] §4.6b exists post-create: live-body fetch, shared whole-line `grep -qixF` match with §4.6a, append-only repair via `gh pr edit --body-file -`, 65,536 cap re-check, fully non-fatal
- [ ] A PR created with the ref already present is untouched (idempotent); a hand-rolled create missing the ref gets it appended exactly once
- [ ] capture Phase 6 + make-pr Phase 5 each carry the check block (correct `--since` anchors: spec `created_at` / PR `createdAt`) + one-cycle retro-fire + mandatory four-state summary slot
- [ ] make-pr under Ralph: stdout still emits only `PR_URL=<url>`; all new output on stderr
- [ ] Both touchpoint invocations pass their `event:` key

## Done summary
Wired the fn-57 end-of-run sync check + one-cycle retro-fire + mandatory four-state Tracker sync summary slot into capture (Phase 6, --since = spec created_at) and make-pr (new §5.7, --since = PR createdAt, Ralph stdout invariant preserved), tagged both touchpoint dispatches with their event: keys (capture / makePr), and added make-pr §4.6b — the deterministic post-create PR↔issue ref verify/repair against the LIVE PR body using the shared §4.6a whole-line grep -qixF matcher, append-only gh pr edit repair, 65,536-char cap re-check, fully non-fatal.
## Evidence
- Commits: 548875ef9f94ef238e1bd1440a1484821c217975
- Tests: cd plugins/flow-next && python3 -m unittest discover -s tests -p test_sync_check.py -v (19/19 OK), bash -n over every bash fence in both workflow.md files (only pre-existing placeholder block fails, identical at base), bash smoke of §4.6b matcher/append/cap/idempotency logic (5 cases OK), .flow/bin/flowctl sync check fn-57-tracker-sync-lifecycle-hooks-forcing --events capture,makePr --since <now> --json (read-only, exit 0, reports MISSING correctly)
- PRs: