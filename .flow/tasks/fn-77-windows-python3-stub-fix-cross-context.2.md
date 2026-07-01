---
satisfies: [R3]
---

## Description
Add the Windows-native `flowctl.cmd` batch shim (npm-style dual launcher) so PowerShell / cmd.exe contexts — Claude Desktop, native Codex, native Cursor — run `flowctl.py` through a working interpreter without hitting the stub. A bash launcher is invisible to those shells. Also wire ralph-init to copy the resolver + `.cmd` into the installed `scripts/ralph/`.

**Committed vs install-produced (cursor-review Major):** commit `flowctl.cmd` at `plugins/flow-next/scripts/flowctl.cmd` (source) and `.flow/bin/flowctl.cmd` (this repo's dogfood). The `scripts/ralph/flowctl.cmd` + `scripts/ralph/pick-python.sh` are NOT committed — ralph-init copies them into the user's project.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.cmd` (new), `.flow/bin/flowctl.cmd` (new, tracked), `.gitattributes` (new/edit), `plugins/flow-next/skills/flow-next-setup/workflow.md`, `plugins/flow-next/skills/flow-next-ralph-init/SKILL.md`

## Approach
- **`.cmd` shape (mirror `npm/cmd-shim`):** `find_dp0` (`SET dp0=%~dp0`), quote every expansion (`"%dp0%flowctl.py" %*`), forward `%*`, `EXIT /b %errorlevel%`. Guard the Ctrl-C "Terminate Batch Job?" orphan if trivial.
- **Probe order matches R1:** `%PYTHON_BIN%` → `py -3` → `python3` → `python`. **`%PYTHON_BIN%` is a command name ONLY (plan-review Minor)** — no quoted paths-with-spaces / embedded args.
- **`.gitattributes` (load-bearing):** pin `*.cmd text eol=crlf` and the extensionless launchers `eol=lf`.
- **PATHEXT:** typing `flowctl` in cmd/PowerShell resolves `flowctl.cmd`.
- **setup copy wiring:** setup `cp`s `flowctl.cmd` into `.flow/bin/` (+ install summary at :650-651).
- **ralph-init copy wiring:** ralph-init `cp`s `flowctl` + `flowctl.cmd` + `flowctl.py` + `pick-python.sh` into the user's `scripts/ralph/` (both cp branches, SKILL.md :90 and :103). Copying `pick-python.sh` into `scripts/ralph/` (flat) is what makes task .4's `ralph.sh` + hook wrapper resolve the helper in the installed layout.

## Investigation targets
**Required:**
- `plugins/flow-next/skills/flow-next-setup/workflow.md:150-155` + `:650-651`
- `plugins/flow-next/skills/flow-next-ralph-init/SKILL.md:88-106` — BOTH cp branches + chmod :93/:105
- `plugins/flow-next/scripts/flowctl` — the sibling bash launcher (task .1)

**Optional:**
- `npm/cmd-shim`, `gradle/gradlew.bat` (external)

## Acceptance
- [ ] `plugins/flow-next/scripts/flowctl.cmd` (source) + tracked `.flow/bin/flowctl.cmd` exist; from cmd/PowerShell, `flowctl <cmd>` runs `flowctl.py` via the probe without hitting the stub
- [ ] `.cmd` probe order matches R1; `%PYTHON_BIN%` honored as command-name-only (documented)
- [ ] `.cmd` forwards args (incl. spaced/paren'd dp0 paths) and propagates exit code (`EXIT /b %errorlevel%`)
- [ ] `.gitattributes` pins `*.cmd eol=crlf` and the bash launchers `eol=lf`
- [ ] setup `cp`s `flowctl.cmd` into `.flow/bin/` (+ summary); ralph-init `cp`s `flowctl` + `flowctl.cmd` + `flowctl.py` + `pick-python.sh` into the user's `scripts/ralph/` in BOTH branches (verified via the installed layout, not a committed `scripts/ralph/`)

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
