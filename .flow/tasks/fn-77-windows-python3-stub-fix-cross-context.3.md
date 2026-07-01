---
satisfies: [R4]
---

## Description
Teach `flowctl init` to (re-)stamp `.flow/bin/flowctl` and `.flow/bin/flowctl.cmd` so existing installs self-heal. Today only setup writes `.flow/bin/`; `init` never touches it. `.flow/bin/` is tracked (repo-scout) → init must be idempotent (rewrite only on content diff) to avoid churn.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (`cmd_init`)

## Approach
- **Emit inline, don't copy:** at runtime `flowctl.py` executes from `.flow/bin/flowctl.py` and has no bundled launcher template / plugin-root on disk. So `cmd_init` writes the launcher(+`.cmd`) text from an in-module constant, NOT `cp`. Keep the constant as the single source of truth shared with task .1's `scripts/flowctl` body (identical) — cross-reference so they don't drift.
- **Bootstrap chicken-and-egg (plan-review Major — the key one):** a *broken* `.flow/bin/flowctl` (old `exec python3`) can't run to self-heal. `init` itself runs INSIDE `flowctl.py`, so it never needs the broken bash launcher. Self-heal reaches a broken install only via a working entrypoint: (a) plugin auto-update → fixed `scripts/flowctl`/`.cmd` runs setup/init → re-stamps; (b) the newly-delivered `.flow/bin/flowctl.cmd` (Windows) works even when the bash launcher is broken; (c) the manual escape hatch `py -3 .flow/bin/flowctl.py init` (or `python .flow/bin/flowctl.py init`). Task .6 documents (b)/(c); this task must NOT claim `.flow/bin/flowctl init` self-heals a already-broken bash launcher.
- **Insertion point:** after the subdir loop in `cmd_init` (~`flowctl.py:5320`): `mkdir` `.flow/bin`, write `flowctl` + `flowctl.cmd` only when absent OR content differs from the constant (idempotent; action string only on real rewrite). Preserve `chmod +x` best-effort.
- **Coordination:** edits the SAME `flowctl.py` fn-74's paused worktree rewrites — expect a rebase (spec-scout).

## Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl.py:5306-5356` — `cmd_init` body; insertion point ~5320
- `plugins/flow-next/scripts/flowctl.py:4082` — the `.flow/bin/*` "bundled flowctl" doc line
- `plugins/flow-next/scripts/flowctl` — the launcher body to embed as the constant (task .1)

## Acceptance
- [ ] `flowctl init` (invoked via ANY working entrypoint) on a repo whose `.flow/bin/flowctl` is the OLD `exec python3` form rewrites it to the probe form (+ adds `.flow/bin/flowctl.cmd` if missing)
- [ ] `flowctl init` is idempotent — a second run reports no `.flow/bin` action and makes no file change (no tracked-file churn)
- [ ] Fresh `flowctl init` creates `.flow/bin/flowctl` + `.flow/bin/flowctl.cmd` with the probe launcher
- [ ] The embedded launcher constant is byte-identical to `scripts/flowctl` (drift guard — a test or explicit cross-reference)
- [ ] Task acceptance does NOT claim a broken `.flow/bin/flowctl` bash launcher self-heals by running itself — the bootstrap entrypoints (plugin update / `.cmd` / `py -3 …flowctl.py init`) are the documented paths

## Done summary
Taught `flowctl init` (`cmd_init`) to re-stamp `.flow/bin/flowctl` + `.flow/bin/flowctl.cmd` from byte-identical in-module constants so existing installs with the old `exec python3` launcher self-heal without a full `/flow-next:setup` re-run. Idempotent (writes only on content diff — no tracked-file churn), best-effort `chmod +x`, with a byte-for-byte drift guard test plus smoke-test coverage of fresh-stamp, old→probe self-heal, and no-churn re-run.
## Evidence
- Commits: 598a87da98ce7c09762715fddf553681b45962ba
- Tests: bash plugins/flow-next/scripts/smoke_test.sh (138 passed, 0 failed), python3 -m unittest tests.test_init_stamp_launchers (7 passed)
- PRs: