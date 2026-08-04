---
satisfies: [R1]
---
# fn-166-flowctl-module-split-importable.2 Importable launcher: pyc-cached main CLI path + flowctl.md:125 scoped rewrite

## Description
Make the main CLI path import flowctl as a module so `__pycache__` bytecode caching applies; measure and record the >=2x warm-startup win; rewrite `docs/flowctl.md:125` to scope the recorded bytecode-cache rejection to the untouched authenticated bootstrap path. The launcher is a drift-guarded artifact GRAPH, not two files — update every site together.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl` (bash launcher), `plugins/flow-next/scripts/flowctl.cmd`, embedded `LAUNCHER_SH`/`LAUNCHER_CMD` constants in `plugins/flow-next/scripts/flowctl.py:19101-19158`, `plugins/flow-next/bin/flowctl`, `.flow/bin/flowctl` + `.flow/bin/` copies, NEW thin entry file (e.g. `plugins/flow-next/scripts/flowctl_entry.py` — implementer names it), `scripts/install-codex.sh` (:245-251 copy lines), `plugins/flow-next/skills/flow-next-setup/workflow.md` (copy steps), ralph-init launcher copies (grep for them), staged-layout smoke fixtures, `.gitignore`, `plugins/flow-next/docs/flowctl.md`

### Approach
- Launcher execs a thin entry that does sys.path containment (the script's own directory ONLY) + imports flowctl + calls `main()` (exists at `flowctl.py:46820`; re-grep). Python does not bytecode-cache `python3 file.py`; only imported modules get `__pycache__` — that asymmetry is the entire win.
- **Launcher artifact graph — update as ONE unit:** the on-disk launchers are drift-guarded byte-identical to the `LAUNCHER_SH`/`LAUNCHER_CMD` constants embedded in flowctl.py (:19101-19158; `flowctl init` RESTAMPS launchers from these constants — a stale constant silently reverts the launcher on next init). Enumerate the full graph mechanically first: `grep -rln "flowctl_bootstrap\|FLOWCTL_ENTRY" --include="*" .` plus the assertions in `test_bin_launcher_parity` / `test_init_stamp_launchers`. Known sites: both scripts/ launchers, the embedded constants, `plugins/flow-next/bin/flowctl`, `.flow/bin/flowctl`, `scripts/install-codex.sh` copy lines, setup workflow copy steps, ralph-init copies, smoke fixtures.
- Entry-file distribution: the new entry file must ride EVERY channel that today carries `flowctl.py` (setup workflow, install-codex.sh, ralph-init, `.flow/bin/`) — a missing copy means Codex/Ralph installs exec a nonexistent entry. Regenerate the manifest after (it hashes flowctl.py).
- Entry-shape choice (record it): separate thin entry file (recommended — one quoting-safe implementation) vs inline `python3 -c` in both launchers (no new file to distribute; logic duplicated; argv[0] becomes `-c`). Whichever is chosen, the full graph above still applies.
- Replicate the module-entry guard semantics (`flowctl.py:49735`) exactly — exit codes are frozen CLI surface (SystemExit propagation included).
- **`argv[0]` parity (review round 2):** argparse derives `prog` from `sys.argv[0]`; a file entry yields `usage: flowctl_entry.py ...`, inline yields `usage: -c ...` — both are frozen-surface diffs. The entry MUST set `sys.argv[0]` to the sibling `flowctl.py` path before calling `main()` (the bootstrap already does exactly this normalization at `flowctl_bootstrap.py:174`). Add launcher tests asserting stdout/stderr + exit-code parity with direct `python3 flowctl.py` for (a) a non-root subcommand's `--help` and (b) an argparse error.
- fn-77 contract: launchers stay bash/.cmd (may gain lines); NEVER overwrite `.flow/bin/flowctl` with Python source. The static-help fast path (`flowctl_bootstrap.py` for bare `usage`/`--help`, dispatched at launcher `:44-49`) is UNTOUCHED.
- `.gitignore`: cover `.flow/bin/__pycache__/` (`.flow/bin` is committed) and verify `plugins/flow-next/scripts/__pycache__/` coverage; confirm `git status` clean after a warm run.
- Rewrite `docs/flowctl.md:125` (rewrite, don't append): the bytecode-cache rejection protects the manifest-AUTHENTICATED static-help path, which keeps in-memory exec; the main path makes no hash-authentication claim and relies on Python's standard pyc invalidation.
- Add an installed-layout smoke: from a staged/installed layout, invoke a NON-static command (not bare usage/--help) through the launcher and assert success — proves the entry file actually shipped.
- Measure and record method + before/after numbers (task summary + PR): warm timing loop, e.g. 5x `flowctl show fn-166-flowctl-module-split-importable --json`, baseline ~290ms, target >=2x.

### Investigation targets
**Required** (read before coding):
- `plugins/flow-next/scripts/flowctl:1-49` — bash launcher, FLOWCTL_ENTRY mechanism at :44-49
- `plugins/flow-next/scripts/flowctl.py:19095-19210` — embedded LAUNCHER_SH/LAUNCHER_CMD constants + drift-guard comment
- `plugins/flow-next/tests/test_bin_launcher_parity.py` + `test_init_stamp_launchers.py` — they DEFINE the artifact graph the change must keep coherent
- `plugins/flow-next/scripts/flowctl_bootstrap.py:98-176` — deliberate no-cache exec design (do NOT change)
- `plugins/flow-next/docs/flowctl.md:118-130` — the rejection paragraph to rewrite

**Optional** (reference as needed):
- `scripts/install-codex.sh:240-260` — launcher/flowctl.py copy lines
- `plugins/flow-next/skills/flow-next-setup/workflow.md:140-151` — copy-mode propagation steps

### Key context
- `test_tracker_distribution` RuntimeSmoke runs the real launcher incl. `.cmd` on Windows CI.
- EARLY PROOF POINT: if measurement lands under 2x, STOP — re-evaluate the entry shape or document a floor with evidence; do not push on and hope.
## Acceptance
- [ ] Warm `show --json` >=2x faster than the ~290ms baseline; method + before/after numbers recorded in task summary/PR
- [ ] FULL launcher artifact graph updated together: both scripts/ launchers, embedded LAUNCHER_SH/LAUNCHER_CMD constants, `plugins/flow-next/bin/flowctl`, `.flow/bin/flowctl`, install-codex.sh, setup workflow, ralph-init copies, smoke fixtures — enumerated mechanically and listed in the task summary
- [ ] Entry file (if chosen) rides every distribution channel that carries flowctl.py; installed-layout smoke invokes a non-static command through the launcher
- [ ] `.flow/bin/flowctl` remains a bash launcher (fn-77); `flowctl_bootstrap.py` untouched; `docs/flowctl.md:125` rewritten to scope the rejection
- [ ] `.gitignore` covers new `__pycache__` dirs; `git status` clean after a warm run
- [ ] Focused suites green: `python3 -m unittest test_bin_launcher_parity test_init_stamp_launchers test_startup_bootstrap test_tracker_distribution test_flowctl_surface -q`
- [ ] Entry normalizes `sys.argv[0]` to the sibling flowctl.py path; parity tests assert identical usage/help/error output + exit codes vs direct `python3 flowctl.py`
## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
