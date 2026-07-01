---
satisfies: [R3]
---

## Description
Add the Windows-native `flowctl.cmd` batch shim (npm-style dual launcher) so PowerShell / cmd.exe contexts — Claude Desktop, native Codex, native Cursor — run `flowctl.py` through a working interpreter without hitting the stub. A bash launcher is invisible to those shells (no shebang honoring), so this closes the non-Git-Bash Windows gap.

**Size:** M
**Files:** `plugins/flow-next/scripts/flowctl.cmd` (new), `.flow/bin/flowctl.cmd` (new, tracked), `plugins/flow-next/scripts/ralph/flowctl.cmd` (new), `.gitattributes` (new or edit), `plugins/flow-next/skills/flow-next-setup/workflow.md`, `plugins/flow-next/skills/flow-next-ralph-init/SKILL.md`

## Approach
- **`.cmd` shape (mirror `npm/cmd-shim`):** `find_dp0` subroutine (`SET dp0=%~dp0`), quote every expansion (`"%dp0%flowctl.py" %*`), forward `%*`, propagate exit with `EXIT /b %errorlevel%`. Resolve interpreter `py -3` → `python` (probe order matching task .1). Note `%~` modifiers can't combine with `%*` (MS `call` docs). Guard the Ctrl-C "Terminate Batch Job?" orphan (npm's `endLocal & goto` trick) if trivial.
- **`.gitattributes` (load-bearing):** pin `*.cmd text eol=crlf` and the extensionless launchers `eol=lf` — a `.cmd` checked out LF misbehaves; a bash launcher checked out CRLF breaks the shebang.
- **PATHEXT:** typing `flowctl` in cmd/PowerShell resolves `flowctl.cmd` (`.CMD` in default PATHEXT) — no user action needed.
- **Copy-site wiring:** setup `cp`s the `.cmd` into `.flow/bin/` and ralph-init `cp`s it into `scripts/ralph/` — mirror the existing `flowctl`/`flowctl.py` copy lines (repo-scout: setup workflow.md ~150-155 + the :650-651 install summary; ralph-init SKILL.md BOTH :90 and :103 branches + chmod :93/:105).

## Investigation targets
**Required:**
- `plugins/flow-next/skills/flow-next-setup/workflow.md:150-155` + `:650-651` — the `.flow/bin` copy block + install summary
- `plugins/flow-next/skills/flow-next-ralph-init/SKILL.md:88-106` — BOTH cp branches (fresh + re-init) — easy to miss the second
- `plugins/flow-next/scripts/flowctl` — the sibling bash launcher (task .1) whose probe order the `.cmd` mirrors

**Optional:**
- `npm/cmd-shim`, `gradle/gradlew.bat` (external) — canonical `.cmd` template + `.gitattributes` eol pinning

## Acceptance
- [ ] `plugins/flow-next/scripts/flowctl.cmd` + tracked `.flow/bin/flowctl.cmd` + `scripts/ralph/flowctl.cmd` exist; from cmd/PowerShell, `flowctl <cmd>` runs `flowctl.py` via `py -3` (preferred) without hitting the stub
- [ ] `.cmd` forwards args (incl. spaced/paren'd paths) and propagates the exit code (`EXIT /b %errorlevel%`)
- [ ] `.gitattributes` pins `*.cmd eol=crlf` and the bash launchers `eol=lf`
- [ ] setup `cp`s `flowctl.cmd` into `.flow/bin/` (+ install summary lists it); ralph-init `cp`s it into `scripts/ralph/` in BOTH branches

## Done summary
TBD

## Evidence
- Commits:
- Tests:
- PRs:
