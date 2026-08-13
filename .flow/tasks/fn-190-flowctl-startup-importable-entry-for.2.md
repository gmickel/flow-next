---
satisfies: [R1, R2, R3, R4]
---
# fn-190-flowctl-startup-importable-entry-for.2 Importable entry for the main CLI path + the whole launcher artifact graph

## Description
Make the main CLI path import flowctl as a module so CPython's bytecode cache applies, keeping the CLI surface byte-identical and the authenticated static-help path untouched. The launcher is a drift-guarded artifact GRAPH plus embedded constants that `init` restamps - update every site in this one change or a consumer's next `init` silently reverts it.

**Size:** M
**Files:** NEW thin entry beside the module (implementer names it, e.g. `plugins/flow-next/scripts/flowctl_entry.py`); `plugins/flow-next/scripts/flowctl` and `flowctl.cmd`; `plugins/flow-next/bin/flowctl`; embedded `LAUNCHER_SH`/`LAUNCHER_CMD` constants in `plugins/flow-next/scripts/flowctl.py` (~:19847-19960, behind a DRIFT GUARD comment); `.flow/bin/flowctl`; `scripts/install-codex.sh` (copy block ~:250-260); `plugins/flow-next/skills/flow-next-setup/workflow.md` copy steps; ralph-init launcher copies; staged-layout smoke fixtures; `.gitignore`; `plugins/flow-next/docs/flowctl.md`
**Touches:** [plugins/flow-next/scripts/**, plugins/flow-next/bin/flowctl, plugins/flow-next/skills/flow-next-setup/workflow.md, plugins/flow-next/skills/flow-next-ralph-init/**, plugins/flow-next/docs/flowctl.md, plugins/flow-next/tests/**, scripts/install-codex.sh, .flow/bin/**, .gitignore]

### Approach
**A validated spike exists: worktree `/tmp/fn190-spike`, branch `spike/fn-190-importable-entry` (built on main @ 9e111db4, 2026-08-13).** It contains a working entry, the four bash launcher copies routed through it, a green full suite, and a 63-case parity sweep harness. Read it first: it is the reference implementation for the mechanism, and it is deliberately INCOMPLETE — missing the `.cmd` twin, install-codex/setup/ralph-init channels, smoke fixtures, `.gitignore`, and the docs rewrite. Do not merge it; reproduce it properly.

Findings from that spike that are now requirements:
- **The wrapper must FALL BACK, not fail:** prefer the entry when the file exists beside the source, else use the source script. A stale install then behaves exactly as today (no speedup, no error), and the orphan case is covered by the entry's own message. This is simpler and safer than making the wrapper detect a broken install.
- **Editing the embedded launcher constants breaks the distribution manifest** (it hashes the module), so `test_startup_bootstrap`'s manifest-source-sha assertion fails until `python3 scripts/gen_tracker_manifest.py` runs. Propagation for THIS task is: copy the module AND the new entry into `.flow/bin/`, regenerate the manifest, then `./scripts/sync-codex.sh` twice.
- **Parity is mechanically checkable across the whole surface** — enumerate subcommands from root `--help`, run each `--help` plus a set of error/runtime paths through both entries, diff stdout/stderr/exit code. The spike's sweep found zero diffs over 63 cases; reproduce it as a test rather than a one-off script.

- Entry does exactly four things (spec's Architecture section is the contract): contain `sys.path` to its own directory ONLY, import the flowctl module, set `sys.argv[0]` to the sibling module path BEFORE dispatch, call `main()` and let `SystemExit` propagate. `main()` is at ~:48695 and the `__main__` guard at ~:51691 - re-grep.
- **argv[0] is a frozen-surface trap:** argparse derives `prog` from `sys.argv[0]`, so a naive entry yields `usage: flowctl_entry.py ...` and an inline `python3 -c` yields `usage: -c ...`. The authenticated bootstrap already performs exactly this normalization (`flowctl_bootstrap.py` ~:174) - copy that behavior. Add tests asserting stdout/stderr/exit-code parity against direct module invocation for (a) a NON-root subcommand's `--help` and (b) a deliberate argparse error.
- **Enumerate the artifact graph mechanically before editing:** `grep -rln 'FLOWCTL_ENTRY\|flowctl_bootstrap' .` plus the assertions inside `test_bin_launcher_parity.py` and `test_init_stamp_launchers.py` - those tests DEFINE the graph. The on-disk launchers must stay byte-identical to `LAUNCHER_SH`/`LAUNCHER_CMD`; LAUNCHER_CMD is stored LF and written CRLF.
- **The new entry must ride every channel that carries flowctl.py today** (setup workflow, install-codex.sh, ralph-init, `.flow/bin/`). With the fallback above, a channel that forgets it degrades to today's speed rather than breaking - which is safe but SILENT, so the installed-layout smoke has to assert the entry actually shipped (measure or assert the resolved entry, not just a zero exit). The entry's own missing-source message covers only the orphan case (entry present, module absent).
- Do NOT touch `flowctl_bootstrap.py`'s in-memory exec (~:110) or the launcher's static-help dispatch: bare `usage`/`--help` keep the authenticated path. That is also why the smoke must invoke a NON-static subcommand - `usage` would pass even if the entry never shipped.
- fn-77 contract: launchers stay bash/.cmd and may gain lines; NEVER overwrite `.flow/bin/flowctl` with Python source. The interpreter probe (PYTHON_BIN → py -3 → python3 → python, 3.11+ functional check, Store-stub rejection) stays exactly as-is.
- `.gitignore`: cover the new `__pycache__` locations, including one beside the COMMITTED `.flow/bin/` copy; verify `git status` is clean after a warm run (a dirty tree there would defeat the green-receipt cleanliness probe).
- Rewrite (do not append to) the bytecode-rejection paragraph in `docs/flowctl.md` (~:125). Today it reads as if no CLI path may ever use a pyc; it must scope that to the manifest-AUTHENTICATED static-help path and state the main path's standard source-mtime/size invalidation trust model.
- Measure R1 at BOTH boundaries on the pre-change tree and after, warm loop, median of >=6: direct module invocation and through the wrapper. Spike reference numbers (same machine class): direct 0.510s -> 0.247s (`memory add`), 0.217s -> 0.067s (`--help`); wrapper 0.434s -> 0.266s (`show --json`), 0.545s -> 0.385s (`status`).
- **EARLY PROOF POINT (restated after the spike):** the gate is the ABSOLUTE saving, >=0.12s per call. Do NOT gate on a ratio - through the wrapper the ratio lands 1.4x-1.6x because the wrapper's own floor (shell spawn ~60ms + interpreter probe ~33ms) and the command's real work dilute a fixed saving. If the absolute saving comes in under 0.12s, STOP and report.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/bin/flowctl` (49 lines) - the wrapper, its FLOWCTL_ENTRY selection, and the static-help dispatch
- `plugins/flow-next/scripts/flowctl.py` at the LAUNCHER_SH/LAUNCHER_CMD drift-guard block - restamp source of truth
- `plugins/flow-next/tests/test_bin_launcher_parity.py`, `test_init_stamp_launchers.py` - they define the graph the change must keep coherent
- `plugins/flow-next/scripts/flowctl_bootstrap.py` - the deliberate no-cache exec and the argv[0] normalization to copy (do NOT change its design)
- `plugins/flow-next/docs/flowctl.md` bytecode-rejection paragraph - the rewrite target

**Optional** (reference as needed):
- `scripts/install-codex.sh` copy block - one channel that must learn the entry
- `plugins/flow-next/skills/flow-next-setup/workflow.md` copy steps - another channel

### Key context
- `test_tracker_distribution`'s runtime smoke drives the real launcher including `.cmd` on Windows CI - the OS matrix is the honest gate for this task.
- Read-only install dirs get no pyc and must keep working unaccelerated: that is correct behavior, not a warning surface.

### Acceptance
- [ ] Warm per-invocation saving >=0.12s, measured at BOTH boundaries (direct + through the wrapper), method and numbers in the task summary and PR; ratios reported, not gated
- [ ] Parity tests assert identical stdout/stderr/exit code vs direct module invocation for a non-root subcommand `--help` and an argparse error, program name included
- [ ] Entry contains sys.path to its own directory only; `SystemExit` propagation unchanged
- [ ] Full artifact graph updated in this change and enumerated in the summary: both scripts/ launchers, embedded LAUNCHER_SH/LAUNCHER_CMD, bin/flowctl, .flow/bin/flowctl, install-codex.sh, setup workflow, ralph-init copies, smoke fixtures
- [ ] `init` restamping reproduces the shipped launchers (test_init_stamp_launchers green); `.flow/bin/flowctl` is still bash (fn-77)
- [ ] Installed-layout smoke invokes a NON-static subcommand through the wrapper and succeeds; a stale install missing the entry falls back to the source script silently; an orphaned entry with no source beside it exits non-zero naming the expected path, never a traceback
- [ ] Manifest regenerated after touching the embedded launcher constants (`gen_tracker_manifest.py`), entry copied into `.flow/bin/`, sync-codex run twice; `test_startup_bootstrap` green
- [ ] Differential parity test covers the whole subcommand surface (every subcommand's `--help` plus error/runtime paths), asserting identical stdout/stderr/exit code between entry and direct invocation
- [ ] `flowctl_bootstrap.py` and the static-help dispatch untouched; docs bytecode paragraph REWRITTEN to scope the rejection to the authenticated path
- [ ] `.gitignore` covers the new `__pycache__` locations; `git status` clean after a warm run
- [ ] Focused suites green: `cd plugins/flow-next/tests && python3 -m unittest test_bin_launcher_parity test_init_stamp_launchers test_startup_bootstrap test_tracker_distribution test_flowctl_surface -q`

## Acceptance
- [ ] TBD

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
