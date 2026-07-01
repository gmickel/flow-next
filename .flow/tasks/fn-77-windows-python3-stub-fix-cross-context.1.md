---
satisfies: [R1, R2]
---

## Description
Create the shared interpreter resolver and make the bash `flowctl` launcher robust against the Windows Store `python3` stub. **Early proof point** — proves the probe skips the 9009 stub while keeping mac/linux on `python3`.

Two artifacts:
1. **New `plugins/flow-next/scripts/lib/pick-python.sh`** — sourceable helper whose `pick_python` fills a bash **array `FLOW_PY=( … )`**, reading the scalar override `$PYTHON_BIN` first. Returns non-zero when none work. The 11 plugin-tree consumers (task .4) source it via `scripts/lib/pick-python.sh`.
2. **Rewrite `plugins/flow-next/scripts/flowctl`** with a **self-contained inline array probe** (do NOT source the helper — a launcher copy can't assume `scripts/lib/` is reachable; see Decision context). Update this repo's tracked dogfood `.flow/bin/flowctl` to match.

**NOTE (cursor-review Major):** there is NO committed `plugins/flow-next/scripts/ralph/flowctl` — that copy is produced PER-PROJECT by ralph-init (wired in task .2), not edited here. The only committed launcher artifacts are `plugins/flow-next/scripts/flowctl` (source) and `.flow/bin/flowctl` (this repo's dogfood install).

**Size:** M
**Files:** `plugins/flow-next/scripts/lib/pick-python.sh` (new), `plugins/flow-next/scripts/flowctl`, `.flow/bin/flowctl`

## Approach
- **Two distinct names (plan-review Major):** `PYTHON_BIN` = user-provided **scalar** override (command name only; exportable). `FLOW_PY` = the **resolved bash array**. Callers `exec "${FLOW_PY[@]}" "$SCRIPT_DIR/flowctl.py" "$@"`. Never reuse `PYTHON_BIN` as the array (arrays aren't exportable; `"$PYTHON_BIN"` scalar-expands only element 0).
- **Array carries `py -3`:** a single string token can't be both multi-word `py -3` and space-safe — the array can. Emit PATH-resolvable command names (`python3`/`python`/`py -3`), NOT rewritten absolute paths; the stub is excluded by the probe.
- **Probe = functionality:** `"${cand[@]}" -c "import sys"`, reject non-zero. Store stub exits 9009 on args, never 0 with `-c` (bpo-41327) — rejects both the stub AND a genuinely-absent interpreter (Win11 24H2+ ships the alias disabled).
- **Order:** `$PYTHON_BIN` → `py -3` → `python3` → `python`. `py.exe` (C:\Windows\py.exe) is registry-resolved, never a Store stub.
- **`set -u`-safe:** guard with `${FLOW_PY[@]:-}` / `${PYTHON_BIN:-}`.
- Model on `gradle/gradlew`; reuse `ensure_flowctl_wrapper()` resilience (chmod `|| true`) from `ralph.sh:57-72`.

## Investigation targets
**Required:**
- `plugins/flow-next/scripts/flowctl:4` — the `exec python3` line
- `.flow/bin/flowctl` — the tracked dogfood copy to update in lockstep
- `plugins/flow-next/skills/flow-next-ralph-init/templates/ralph.sh:57-72` — `ensure_flowctl_wrapper()` model (its scalar `PY="${PYTHON_BIN:-python3}"` is what task .4 replaces)
- `plugins/flow-next/scripts/smoke_test.sh:10-16` — `to_winpath()`
- `plugins/flow-next/scripts/ralph_smoke_test.sh:14` — a representative existing `pick_python()`

## Acceptance
- [ ] `scripts/lib/pick-python.sh` exists, `set -u`-safe, fills `FLOW_PY` array, reads scalar `$PYTHON_BIN` first, returns non-zero when none work
- [ ] The probe rejects a fake `python3` that exits 9009 (on PATH) and falls through to a working `python`/`py -3`
- [ ] `exec "${FLOW_PY[@]}" …` runs BOTH the two-word `py -3` case AND a bare `python3` case
- [ ] `scripts/flowctl` + `.flow/bin/flowctl` resolve via the inline array probe before exec (no phantom `scripts/ralph/flowctl` edit — that copy is task .2's install wiring)
- [ ] On mac/linux (working `python3`, no `py`) the resolver still selects `python3` first — no behavior change
- [ ] `.flow/bin/flowctl --help` and a real `flowctl list` succeed unchanged on this repo (dogfood)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
