---
satisfies: [R8, R9, R10]
---

## Description
Prove the fix and lock it against regression — with heavy emphasis on **no mac/linux regression** (hard constraint). Two layers:
1. **POSIX regression harness** (existing CI, mac/linux): a fake-9009-`python3`-stub-on-PATH scenario.
2. **A real `windows-latest` CI job** exercising `flowctl.cmd` (cmd/PowerShell) and bash `flowctl` (Git Bash) against a **deterministic** stub.

**Size:** M
**Files:** new regression test (e.g. `plugins/flow-next/scripts/pick_python_test.sh`), `plugins/flow-next/scripts/alias_smoke.sh`, `.github/workflows/*.yml`

## Approach
- **Fake-stub harness (proven in planning):** a stub `python3` first on PATH that prints "Python was not found…" to stderr and `exit 9009`, plus a working `python`/`py -3`. Assert: (a) OLD `command -v python3` selects the stub, (b) NEW probe rejects it and falls through, (c) `$PYTHON_BIN` override is itself probed (broken override rejected), (d) `py -3` preferred when present-and-working, (e) array form runs `py -3` AND bare `python3` correctly.
- **mac/linux guard (R8):** assert that with a normal working `python3` and no `py`, the resolver returns `python3` first; run the full existing smoke suite unchanged.
- **Windows CI job — deterministic stub required (plan-review Minor):** do NOT rely on the hosted runner's Store alias (runners may not expose it). Instead, place a fake `python3` stub (a `.cmd`/`.exe`/shim that exits 9009) FIRST on PATH for BOTH the PowerShell/cmd job AND the Git Bash job, install a real python.org Python (with `py`), then assert `flowctl.cmd` (pwsh) and `flowctl` (Git Bash) both bypass the stub and succeed. Reuse the CRLF-normalization discipline for Windows CI (git `8fd228db`).
- Extend `alias_smoke.sh` (already has `pick_python`) with the stub scenario for the standard smoke path.

## Investigation targets
**Required:**
- `plugins/flow-next/scripts/alias_smoke.sh:47-56` — existing `pick_python` to extend
- `.github/workflows/` — existing CI + any current Windows job (git `8fd228db` CRLF pattern)
- `plugins/flow-next/scripts/smoke_test.sh` — smoke-suite entry to keep green (R8)

**Optional:**
- `plugins/flow-next/scripts/lib/pick-python.sh` (task .1) — unit under test

## Acceptance
- [ ] Regression test creates a 9009 `python3` stub on PATH and asserts: OLD `command -v` selects it, NEW probe falls through, `$PYTHON_BIN`-override-probed, `py -3`-preferred, array-runs-`py -3`-and-`python3`
- [ ] `alias_smoke.sh` extended with the stub scenario; passes on mac/linux
- [ ] Full existing smoke suite passes unchanged on mac/linux (explicit R8 guard)
- [ ] `windows-latest` job puts a DETERMINISTIC fake `python3` stub (exit 9009) first on PATH for BOTH pwsh and Git Bash, then asserts `flowctl.cmd` and `flowctl` bypass it and succeed — not reliant on the runner's Store alias
- [ ] CI green on macOS, Linux, and Windows

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
