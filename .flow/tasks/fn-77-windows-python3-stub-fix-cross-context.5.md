---
satisfies: [R8, R9, R10]
---

## Description
Prove the fix and lock it against regression — with heavy emphasis on **no mac/linux regression** (Gordon's hard constraint). Two layers:
1. **POSIX regression harness** (runs in existing CI on mac/linux): a fake-9009-`python3`-stub-on-PATH scenario asserting the resolver behavior.
2. **A real Windows CI runner job** (`windows-latest`) exercising `flowctl.cmd` (cmd/PowerShell) and the bash `flowctl` (Git Bash) end-to-end.

**Size:** M
**Files:** new regression test (e.g. `plugins/flow-next/scripts/pick_python_test.sh` or a pytest), `plugins/flow-next/scripts/alias_smoke.sh`, `.github/workflows/*.yml`

## Approach
- **Fake-stub harness (proven in planning):** put a stub `python3` first on PATH that prints the "Python was not found…" line to stderr and `exit 9009`, plus a working `python` (or `py -3`). Assert: (a) the OLD `command -v python3` path selects the stub, (b) the NEW probe rejects it and falls through to the working interpreter, (c) `$PYTHON_BIN` override is itself probed (a broken override is rejected), (d) `py -3` is preferred when present-and-working.
- **mac/linux guard:** assert that with a normal working `python3` and no `py`, the resolver returns `python3` first; run the full existing smoke suite unchanged (R8).
- **Windows CI job:** matrix add `windows-latest`; install python.org Python (with `py`); optionally toggle/simulate the App Execution Alias; run `flowctl.cmd list`/`validate` from `pwsh` AND `flowctl` from Git Bash; assert both succeed. Reuse the CRLF-normalization discipline already used for Windows CI (git log `8fd228db`).
- Extend `alias_smoke.sh` (already has `pick_python`) with the stub scenario so it's exercised by the standard smoke path too.

## Investigation targets
**Required:**
- `plugins/flow-next/scripts/alias_smoke.sh:47-56` — existing `pick_python` in a smoke script to extend
- `.github/workflows/` — existing CI workflow(s) + any current Windows job (git `8fd228db` CRLF-normalization pattern)
- `plugins/flow-next/scripts/smoke_test.sh` — smoke-suite entry to keep green (R8)

**Optional:**
- `plugins/flow-next/scripts/lib/pick-python.sh` (task .1) — unit under test

## Acceptance
- [ ] A regression test creates a 9009 `python3` stub on PATH and asserts: OLD `command -v` selects it, NEW probe falls through to a working interpreter, `$PYTHON_BIN`-override-is-probed, `py -3`-preferred-when-present
- [ ] `alias_smoke.sh` extended with the stub scenario; passes on mac/linux
- [ ] The full existing smoke suite passes unchanged on mac/linux (explicit R8 regression guard)
- [ ] A `windows-latest` CI job runs `flowctl.cmd` (pwsh) and `flowctl` (Git Bash) end-to-end and passes
- [ ] CI is green on macOS, Linux, and Windows

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
