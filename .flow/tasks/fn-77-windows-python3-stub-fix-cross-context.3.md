---
satisfies: [R4]
---

## Description
Teach `flowctl init` to (re-)stamp `.flow/bin/flowctl` and `.flow/bin/flowctl.cmd` so **existing installs self-heal on next run** without a full `/flow-next:setup`. Today only setup writes `.flow/bin/`; `init` never touches it — so a user with a pre-fix launcher stays broken until they re-run setup. Since `.flow/bin/` is tracked (repo-scout), init must be idempotent (rewrite only when content differs) to avoid diff churn.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.py` (`cmd_init`)

## Approach
- **Emit inline, don't copy:** at runtime `flowctl.py` executes from `.flow/bin/flowctl.py` and has NO bundled launcher template / plugin-root on disk (repo-scout). So `cmd_init` must write the launcher(+`.cmd`) text from an in-module constant (heredoc-style string), NOT `cp` from an unknown path. Keep that constant as the single source of truth shared with task .1's `scripts/flowctl` (identical body) — note the coupling so they don't drift.
- **Insertion point:** after the subdir-creation loop in `cmd_init` (repo-scout ~`flowctl.py:5320`), `mkdir` `.flow/bin` if missing, then write `flowctl` + `flowctl.cmd` only when absent OR content differs from the current constant (idempotent; report an action string only when it actually rewrites).
- Preserve `chmod +x` on the bash launcher (best-effort, `|| true` for NTFS).
- Add a `## coordination` note in the task: this edits the SAME `flowctl.py` that fn-74's paused worktree rewrites — expect a rebase (spec-scout).

## Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl.py:5306-5356` — `cmd_init` body (subdir loop, gitignore, meta, config); insertion point ~5320
- `plugins/flow-next/scripts/flowctl.py:4082` — the `.flow/bin/*` "bundled flowctl" doc line
- `plugins/flow-next/scripts/flowctl` — the launcher body to embed as the constant (task .1)

## Acceptance
- [ ] `flowctl init` on a repo whose `.flow/bin/flowctl` is the OLD `exec python3` form rewrites it to the probe form (and adds `.flow/bin/flowctl.cmd` if missing)
- [ ] `flowctl init` is idempotent — a second run reports no `.flow/bin` action and makes no file change (no tracked-file churn)
- [ ] Fresh `flowctl init` creates `.flow/bin/flowctl` + `.flow/bin/flowctl.cmd` with the probe launcher
- [ ] The embedded launcher constant is byte-identical to `scripts/flowctl` (guard against drift — a test or comment cross-reference)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
