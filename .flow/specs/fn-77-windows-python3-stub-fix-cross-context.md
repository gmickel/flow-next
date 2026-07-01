## Conversation Evidence

> user (turn 1): "what is up with this -- we have this on ALL windows computers, how can we help? research deeply" — attached screenshot of a flow-next session narrating: "python3 resolves to broken Windows stub. Call flowctl.py with real python directly." and "Showed spec with real python".
> user (turn 2): "capture it, we will want lots of tests for this somehow, no regressions on the mac/linux side of things. obviously our windows users are in powershell or claude desktop app etc, consider all, but i want a lean fix that just works"

## Goal & Context
<!-- scope: business -->

On Windows, `python3` resolves to the Microsoft Store **App Execution Alias** stub — a 0-byte reparse point at `%LOCALAPPDATA%\Microsoft\WindowsApps\python3.exe` that ships enabled by default. When real Python was installed from python.org / the `py` launcher (not the Store), the stub shadows it: running `python3` prints *"Python was not found…"* and exits **9009**. It is present on `PATH` (so `command -v python3` succeeds) but non-functional. [user] [paraphrase]

flowctl invokes `python3` in several places, so this breaks flow-next on **every** Windows machine in the affected configuration — the reporting user hit it on all of theirs. The agent in the screenshot had to hand-improvise ("call flowctl.py with real python directly"); the fix must make flowctl **just work** across every Windows invocation context without user intervention. [user]

## Architecture & Data Models
<!-- scope: technical -->

Two root defects: (1) the `flowctl` launchers hardcode `exec python3` with **no fallback**; (2) the existing GH-35 `pick_python` helper tests `command -v` = **presence, not functionality**, so it hands back the broken stub. [paraphrase]

Blast radius (canonical, non-codex), all confirmed in-repo:
- **3 byte-identical launcher copies** from one source `plugins/flow-next/scripts/flowctl` → `.flow/bin/flowctl` (setup Step 4 `cp`) and `scripts/ralph/flowctl` (ralph-init `cp`). [paraphrase]
- **Live Ralph hook** `scripts/ralph/hooks/ralph-guard.py` executed **by PATH** via `#!/usr/bin/env python3` (registered in `hooks.json`) — no bash wrapper can save it. [paraphrase]
- **`ralph.sh` pipes to `watch-filter.py` by shebang** (`ralph.sh:1096–1109`) — unhardened despite ralph hardening flowctl's own `PYTHON_BIN`. [paraphrase]
- **Agent-run heredocs** (host Bash tool runs these directly): `flow-next-qa/workflow.md:521`, `flow-next-prospect/workflow.md:63,490,740` — bare `python3 -`. [paraphrase]
- **User-facing CI template** `docs/ci-workflow-example.yml:31` — bare `python3 flowctl.py`. [paraphrase]
- **12 byte-identical `pick_python` copies**, no shared helper (1 partly-hardened exception: the runtime-generated `flowctl-wrapper.sh` in `ralph.sh:66–73` uses `${PYTHON_BIN:-python3}`+`python` fallback but still `command -v`). [paraphrase]

Target design — one interpreter target (`flowctl.py`), thin cross-context shims + a shared probe:
- **Shared resolver** (`scripts/lib/pick-python.sh`, sourced everywhere) — a **functionality probe** (`<cand> -c "import sys"`, reject nonzero exit), candidate order `$PYTHON_BIN` → `py -3` → `python3` → `python`. [user] [paraphrase]
- **Dual launcher** — bash `flowctl` (Git Bash / WSL / mac / linux) **+** `flowctl.cmd` batch shim (PowerShell / cmd.exe — Claude Desktop, native Codex/Cursor), `py -3` preferred (npm-style dual shim). [user]
- **`flowctl init` re-stamps** `.flow/bin/flowctl` + `.flow/bin/flowctl.cmd` so existing installs self-heal without a full `/flow-next:setup` re-run. [user] [paraphrase]

## API Contracts
<!-- scope: technical -->

`pick-python.sh` exposes one function that echoes a runnable interpreter token (may be multi-word, e.g. `py -3`) and returns non-zero when none work:

```
pick_python() -> stdout: "<interpreter token>"   # e.g. "python3", "python", "py -3"
                 exit 0 on success, non-zero when no working interpreter found
```

Contract: the returned token, when invoked as `$TOKEN -c "import sys"`, exits 0 on the resolving machine. The 9009 stub MUST NOT be returned even though it is on `PATH`. Callers `exec $TOKEN "$SCRIPT_DIR/flowctl.py" "$@"` (unquoted expansion to allow the two-word `py -3`). [paraphrase]

`flowctl.cmd` mirrors the contract for cmd/PowerShell: resolve `py -3` → `python` → `python3` (probed), then `%RESOLVED% "%~dp0flowctl.py" %*`, forwarding the exit code. [paraphrase]

## Edge Cases & Constraints
<!-- scope: technical -->

- **mac/linux no-regression (hard constraint):** no `py` launcher exists there, so resolution falls through cleanly to `python3`; a system with working `python3` MUST still select `python3` first, unchanged. [user]
- `$PYTHON_BIN` override is honored **but still probed** — a broken explicit override is rejected, not trusted. [user] [paraphrase]
- `py -3` preferred on Windows because the py launcher is installed by python.org and is **never** a Store alias stub. [paraphrase]
- The probe runs one extra `-c "import sys"` per resolution — negligible, and cached within a single launcher invocation. [inferred]
- CRLF / exec-bit hazards already present on Windows (Git Bash) must not regress — `.cmd` is CRLF-tolerant; the bash path keeps its existing `cygpath`/exec-bit handling. [inferred]

## Acceptance Criteria
<!-- scope: both -->

- **R1:** A single shared resolver (`scripts/lib/pick-python.sh`) probes functionality (`<cand> -c "import sys"`, rejects non-zero exit) with candidate order `$PYTHON_BIN` → `py -3` → `python3` → `python`; the 12 copy-pasted `pick_python` bodies source it instead of redefining. [user] [paraphrase]
- **R2:** The bash `flowctl` launcher (source `scripts/flowctl`, re-stamped into `.flow/bin/flowctl` and `scripts/ralph/flowctl`) resolves via the probe before `exec`; on a machine where `python3` is the 9009 stub but `python`/`py -3` works, `flowctl <cmd>` succeeds. [user]
- **R3:** A `flowctl.cmd` batch shim ships alongside the bash launcher; invoking `flowctl` from PowerShell / cmd.exe runs `flowctl.py` through a working interpreter (`py -3` preferred) without hitting the stub. [user]
- **R4:** `flowctl init` re-stamps `.flow/bin/flowctl` + `.flow/bin/flowctl.cmd`; a pre-fix `.flow/bin/flowctl` is refreshed on next `init` without a full `/flow-next:setup` re-run. [user] [paraphrase]
- **R5:** Direct-shebang Python is invoked through a resolved interpreter, not bare `#!/usr/bin/env python3` path execution: `hooks.json` invokes `ralph-guard.py` via a resolved interpreter; `ralph.sh` pipes to `watch-filter.py` as `"$PYTHON_BIN" watch-filter.py`. [user] [paraphrase]
- **R6:** Agent-run heredocs resolve an interpreter once and invoke `$PY - <<'PY'`: `flow-next-qa/workflow.md` and `flow-next-prospect/workflow.md` no longer emit bare `python3 -`. [user]
- **R7:** The CI template `docs/ci-workflow-example.yml` no longer hardcodes bare `python3 flowctl.py`; it uses a probe / `py -3` form that works on a Windows runner. [user]
- **R8:** No mac/linux regression: on a system with a working `python3` and no `py` launcher, the resolver selects `python3` first and all existing smoke tests pass unchanged. [user]
- **R9:** Regression coverage via a fake-9009-stub-on-PATH harness: asserts the OLD `command -v` path selects the stub, the NEW probe falls through to a working interpreter, `$PYTHON_BIN`-override-is-probed, and `py -3`-preferred-when-present; `alias_smoke.sh` is extended with the stub scenario. [user]
- **R10:** A real Windows CI runner job exercises `flowctl.cmd` (PowerShell/cmd) and the bash launcher (Git Bash) end-to-end against the stub configuration. [user] [paraphrase]
- **R11:** Docs updated — `troubleshooting.md` + `platforms.md` (and flow-next.dev) document the fix and the immediate user workaround: disable App Execution Aliases (Settings → Apps → Advanced app settings → App execution aliases → off for `python.exe`/`python3.exe`). [user]

## Boundaries
<!-- scope: business -->

- **No `flowctl.py` behavior change** — this spec changes only the launch path + interpreter resolution, not CLI semantics. [paraphrase]
- **No user Python install/change required** — the fix works with existing python.org / `py`-launcher installs. [user] [paraphrase]
- **We do not disable App Execution Aliases programmatically** — that stays a documented user workaround; flow-next never edits OS settings. [paraphrase]
- **Lean fix** — no new runtime dependencies, no config surface, no feature flags. [user]
- **No version bump in this spec** — staged batched-unreleased per repo convention; the release/version decision is made separately later. [user] [paraphrase]
- **No Python version-floor change** — flowctl stays py3; this is not a 2-vs-3 debate. [inferred]

## Decision Context
<!-- scope: both -->

**Probe over presence.** The Store stub satisfies `command -v` but fails on exec (9009). Only *running* the interpreter distinguishes a real Python from the alias stub — so the resolver runs `-c "import sys"` and rejects non-zero. This is the single insight GH-35 missed; presence-checking is why the "Windows-supported" smoke tests still break here. [user] [paraphrase]

**`py -3` first on Windows.** The py launcher is installed by python.org and is never a Store alias stub, making it the most reliable Windows candidate. [paraphrase]

**Dual bash + `.cmd` shim.** A bash launcher is invisible to PowerShell/cmd (no shebang honoring) — exactly the shells where Claude Desktop, native Codex, and Cursor run. The npm-style dual shim (`flowctl` + `flowctl.cmd`) is the proven "works everywhere" pattern and keeps one Python target. [user] [paraphrase]

**`init` self-heal.** `.flow/bin/flowctl` is a *copy*, not a live reference, and only `/flow-next:setup` writes it today; without `init` re-stamping, existing Windows installs would stay broken until a manual re-setup. [user] [paraphrase]

**Rejected alternatives:**
- *Tell users to disable App Execution Aliases as the fix* — unreliable, per-machine, not durable; kept only as an interim workaround. [user]
- *Prose "agent should use `py -3`" instruction* — fragile; depends on the model remembering. A deterministic launcher is the point. [paraphrase]
- *Rewrite flowctl.py as a packaged `.exe` / console entry-point* — heavyweight, breaks the zero-dependency ethos. [inferred]

## Strategy Alignment

Active tracks served by this plan:
- **Cross-platform parity** — flow-next is a first-class citizen on Claude Code / Codex / Droid / OpenCode across macOS, Linux, and Windows. This fix removes a break that made the base `flowctl` CLI unusable on Windows in the common python.org-install configuration — directly advancing the parity track.

Consistent with the **zero-dependency** approach: the fix adds no runtime dependency (probes interpreters already present) and nothing to the uninstall path (the `.cmd` shim lives under `.flow/bin/`, deleted with the directory).

## Early proof point

Task **fn-77-...​.1** (shared probe helper + self-contained bash launcher) validates the core hypothesis: the `-c "import sys"` functionality probe rejects a 9009 stub on PATH and falls through to a working interpreter, while mac/linux still selects `python3` first. Proven in planning with a fake-stub harness. **If it fails** (e.g. a stub that exits 0, or a mac/linux regression), re-evaluate the probe strategy before building the `.cmd` shim (.2), init self-heal (.3), and the sweep (.4).

## Coordination note (not a dependency)

fn-77 has **no logical dependency** on any other spec, but it shares files with **fn-74** (Cursor review backend — paused, live worktree): `plugins/flow-next/scripts/flowctl.py` (init self-heal ↔ fn-74's backend dispatch rewrites), `flow-next-setup/workflow.md`, and `ralph.sh`. Whichever lands second needs a rebase pass. No `spec add-dep` edge is warranted (spec-scout). fn-75 (the branch currently in flight) explicitly does **not** touch flowctl (its R14) — no collision there.

## Requirement coverage

| R-ID | Description | Task(s) | Gap justification |
|------|-------------|---------|-------------------|
| R1 | Shared `pick-python.sh` probe helper (functionality, not presence); 12 copies source it | fn-77-...​.1 (helper), fn-77-...​.4 (consumers) | — |
| R2 | Bash `flowctl` launcher resolves via probe before exec (3 copies) | fn-77-...​.1 | — |
| R3 | `flowctl.cmd` dual shim for PowerShell/cmd (`py -3` first) + copy wiring | fn-77-...​.2 | — |
| R4 | `flowctl init` re-stamps `.flow/bin/flowctl`(+`.cmd`) — self-heal | fn-77-...​.3 | — |
| R5 | Un-shebang direct-exec `.py` (hooks.json→ralph-guard.py, ralph.sh→watch-filter.py) | fn-77-...​.4 | — |
| R6 | qa/prospect heredocs resolve `$PY` once | fn-77-...​.4 | — |
| R7 | CI example no longer bare `python3 flowctl.py` | fn-77-...​.6 | — |
| R8 | No mac/linux regression — `python3` still picked first | fn-77-...​.1 (design), fn-77-...​.5 (verified) | — |
| R9 | Fake-9009-stub regression harness + `alias_smoke` extension | fn-77-...​.5 | — |
| R10 | Real Windows CI runner job (`flowctl.cmd` + bash launcher) | fn-77-...​.5 | — |
| R11 | Docs (troubleshooting/platforms/flowctl.md/README) + alias workaround | fn-77-...​.6 | — |
