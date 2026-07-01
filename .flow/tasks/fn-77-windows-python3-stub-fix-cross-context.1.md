---
satisfies: [R1, R2]
---

## Description
Create the shared interpreter resolver and make the bash `flowctl` launcher robust against the Windows Store `python3` stub. This is the **early proof point** — it proves the probe skips the 9009 stub while keeping mac/linux on `python3`.

Two artifacts:
1. **New `plugins/flow-next/scripts/lib/pick-python.sh`** — a sourceable helper exposing `pick_python()` that echoes a runnable interpreter token and returns non-zero when none work. The 12 in-tree consumers (task .4) will source it.
2. **Rewrite `plugins/flow-next/scripts/flowctl`** with a **self-contained inline probe** (do NOT source the helper — the `.flow/bin/` copy can't reach `scripts/lib/`; see Decision context). Also update this repo's tracked `.flow/bin/flowctl` and `scripts/ralph/flowctl` copies to match (they are byte-identical copies today).

**Size:** M
**Files:** `plugins/flow-next/scripts/lib/pick-python.sh` (new), `plugins/flow-next/scripts/flowctl`, `.flow/bin/flowctl`, `plugins/flow-next/scripts/ralph/flowctl`

## Approach
- **Probe = functionality, not presence:** run `"$cand" -c "import sys"` and reject any non-zero exit. The Store stub is a GUI-subsystem app that exits 9009 on args and can never exit 0 with `-c` (bpo-41327) — so the probe rejects both the stub AND a genuinely-absent interpreter (Win11 24H2+ ships the alias disabled, so `python3` is simply missing — handle both identically).
- **Candidate order:** `$PYTHON_BIN` → `py -3` → `python3` → `python`. `py.exe` (C:\Windows\py.exe, PEP 397/514) is registry-resolved and never a Store stub.
- **Multi-word token:** `py -3` is two words — callers `exec $PYTHON_BIN "$SCRIPT_DIR/flowctl.py" "$@"` UNQUOTED (or a bash array). Never `exec "$PYTHON_BIN"` (execs a file literally named `py -3`).
- **`set -u`-safe:** consumers `set -euo pipefail` before sourcing (repo-scout) — use `${PYTHON_BIN:-}` and keep the probe out of a bare pipeline; guard with `if …; then`.
- **PATH-hijack safety:** resolve to the absolute interpreter path (don't run a CWD `python.cmd`); belt-and-suspenders, reject a resolved path under `\Microsoft\WindowsApps\`.
- Model the launcher shape on `gradle/gradlew` (committed extensionless-bash + interpreter probe) and reuse `ensure_flowctl_wrapper()` resilience (chmod `|| true` for NTFS exec-bit) from `ralph.sh:57-72`.

## Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl:4` — the `exec python3` line to replace
- `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh:57-72` — `ensure_flowctl_wrapper()` resilience model (PYTHON_BIN fallback + chmod||true)
- `plugins/flow-next/scripts/smoke_test.sh:10-16` — `to_winpath()` cygpath -m helper (reuse for any path interp)
- `plugins/flow-next/scripts/ralph_smoke_test.sh:14` — a representative existing `pick_python()` body to preserve semantics

**Optional:**
- gradle `gradlew` / npm `cmd-shim` (external) — dual-launcher probe reference

## Acceptance
- [ ] `plugins/flow-next/scripts/lib/pick-python.sh` exists, is `set -u`-safe, echoes a working interpreter token, returns non-zero when none work
- [ ] The probe rejects a fake `python3` that exits 9009 (on PATH) and falls through to a working `python`/`py -3`
- [ ] `scripts/flowctl` + `.flow/bin/flowctl` + `scripts/ralph/flowctl` resolve via the inline probe before exec; multi-word `py -3` works (unquoted expansion)
- [ ] On mac/linux (working `python3`, no `py`) the resolver still selects `python3` first — no behavior change
- [ ] `.flow/bin/flowctl --help` and a real `flowctl list` succeed unchanged on this repo (dogfood)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
