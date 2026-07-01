---
satisfies: [R3]
---

## Description
Add the Windows-native `flowctl.cmd` batch shim (npm-style dual launcher) so PowerShell / cmd.exe contexts — Claude Desktop, native Codex, native Cursor — run `flowctl.py` through a working interpreter without hitting the stub. A bash launcher is invisible to those shells. Also copy the shared resolver into `scripts/ralph/` so installed-repo consumers (task .4 hooks) can reach it.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.cmd` (new), `.flow/bin/flowctl.cmd` (new, tracked), `plugins/flow-next/scripts/ralph/flowctl.cmd` (new), `.gitattributes` (new/edit), `plugins/flow-next/skills/flow-next-setup/workflow.md`, `plugins/flow-next/skills/flow-next-ralph-init/SKILL.md`

## Approach
- **`.cmd` shape (mirror `npm/cmd-shim`):** `find_dp0` (`SET dp0=%~dp0`), quote every expansion (`"%dp0%flowctl.py" %*`), forward `%*`, propagate exit with `EXIT /b %errorlevel%`. Guard the Ctrl-C "Terminate Batch Job?" orphan if trivial. `%~` modifiers can't combine with `%*` (MS `call` docs).
- **Probe order matches R1:** `%PYTHON_BIN%` → `py -3` → `python3` → `python`, each probed. **`%PYTHON_BIN%` is a command name ONLY (plan-review Minor)** — no quoted paths-with-spaces, no embedded args — so batch quoting stays trivial. Document this; a value like `C:\Program Files\...\python.exe` is out of scope for the override (mirrors the bash side, where `PYTHON_BIN` is also command-name-only).
- **`.gitattributes` (load-bearing):** pin `*.cmd text eol=crlf` and the extensionless launchers `eol=lf`.
- **PATHEXT:** typing `flowctl` in cmd/PowerShell resolves `flowctl.cmd` (default PATHEXT) — no user action.
- **Copy-site wiring:** setup `cp`s `flowctl.cmd` into `.flow/bin/` (+ install summary); ralph-init `cp`s `flowctl.cmd` AND `lib/pick-python.sh` into `scripts/ralph/` — mirror the existing copy lines. Copying the resolver here is what makes task .4's ralph hook wrapper work in installed repos (plan-review Major).

## Investigation targets
**Required:**
- `plugins/flow-next/skills/flow-next-setup/workflow.md:150-155` + `:650-651`
- `plugins/flow-next/skills/flow-next-ralph-init/SKILL.md:88-106` — BOTH cp branches + chmod :93/:105
- `plugins/flow-next/scripts/flowctl` — the sibling bash launcher (task .1) whose order the `.cmd` mirrors

**Optional:**
- `npm/cmd-shim`, `gradle/gradlew.bat` (external)

## Acceptance
- [ ] `flowctl.cmd` (+ tracked `.flow/bin/flowctl.cmd` + `scripts/ralph/flowctl.cmd`) exist; from cmd/PowerShell, `flowctl <cmd>` runs `flowctl.py` via the probe without hitting the stub
- [ ] `.cmd` probe order matches R1; `%PYTHON_BIN%` honored as a command-name-only override (documented)
- [ ] `.cmd` forwards args (incl. spaced/paren'd SCRIPT paths — dp0) and propagates exit code (`EXIT /b %errorlevel%`)
- [ ] `.gitattributes` pins `*.cmd eol=crlf` and the bash launchers `eol=lf`
- [ ] setup `cp`s `flowctl.cmd` into `.flow/bin/` (+ summary); ralph-init `cp`s `flowctl.cmd` AND `lib/pick-python.sh` into `scripts/ralph/` in BOTH branches

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
