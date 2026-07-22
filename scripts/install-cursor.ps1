#Requires -Version 5.1
<#
.SYNOPSIS
  Install Flow-Next into Cursor (~/.cursor/plugins/local) as a local plugin on Windows.

.DESCRIPTION
  Windows-native sibling of scripts/install-cursor.sh. Uses robocopy (built into
  Windows) to mirror the plugin into %USERPROFILE%\.cursor\plugins\local\flow-next
  as a REAL directory -- Cursor's plugin loader rejects a symlink whose realpath
  escapes ~/.cursor. It's a snapshot; re-run after `git pull` to update.

  One-liner install (no manual clone needed) -- paste into PowerShell:

    git clone --depth 1 https://github.com/gmickel/flow-next.git $env:TEMP\flow-next-install; `
      powershell -ExecutionPolicy Bypass -File $env:TEMP\flow-next-install\scripts\install-cursor.ps1; `
      Remove-Item -Recurse -Force $env:TEMP\flow-next-install

  From a checkout, if you hit an execution-policy error, run via:

    powershell -ExecutionPolicy Bypass -File .\scripts\install-cursor.ps1

  What gets installed (mirrors install-cursor.sh exactly):
    - Manifest:  .cursor-plugin\plugin.json   (explicit skills/agents/commands/rules paths)
    - Skills:    skills\<name>\SKILL.md       (via the manifest override)
    - Commands:  commands\flow-next\*.md      (via the manifest override)
    - Agents:    agents\*.md                  (via the manifest override)
    - Rules:     rules\*.mdc                  (flow-next.mdc guidance rail)
    - Hooks:     none shipped at plugin level (Ralph is opt-in via ralph-init project settings)
    - flowctl:   scripts\flowctl[.py]          (resolved at runtime via .flow\bin after setup)

  Excludes the Codex mirror (codex\), tests\, and Python/OS cruft.

  Caveats (cosmetic / known) -- same as the bash installer:
    - Cursor registers the skills/commands/agents but does NOT show flow-next as a
      grouped "plugin" card in the marketplace UI -- the components still work.
    - Ralph autonomous mode is NOT supported on Cursor: flow-next's hooks use Claude
      Code's schema (PreToolUse/Stop + Bash|Execute matchers); Cursor's hook events
      are afterFileEdit / beforeShellExecution, so the Ralph guard never fires.

.PARAMETER Plugin
  Plugin to install. Only 'flow-next' is supported (the default).
#>
param([string]$Plugin = "flow-next")

$ErrorActionPreference = "Stop"

$ScriptDir = $PSScriptRoot
$RepoRoot  = (Resolve-Path (Join-Path $ScriptDir "..")).Path

if ($Plugin -ne "flow-next") {
    Write-Error "Only 'flow-next' is supported (got '$Plugin')."
    exit 1
}

$PluginDir = Join-Path $RepoRoot "plugins\$Plugin"
$Manifest  = Join-Path $PluginDir ".cursor-plugin\plugin.json"
if (-not (Test-Path $Manifest)) {
    Write-Error "$Manifest not found. Run this from a flow-next checkout (the Cursor manifest must be present)."
    exit 1
}

$Dest = Join-Path $env:USERPROFILE ".cursor\plugins\local\$Plugin"

Write-Host "Installing $Plugin into Cursor ($Dest)..."
New-Item -ItemType Directory -Force -Path (Split-Path $Dest) | Out-Null

# Real-dir mirror via robocopy (Windows-native; the rsync analogue). /MIR keeps the
# snapshot in lockstep on re-run (purges removed files). Exclude the Codex mirror,
# tests, and Python/OS cruft. robocopy exit codes 0-7 are success; >=8 is failure.
$roboArgs = @(
    $PluginDir, $Dest, "/MIR",
    "/XD", "codex", "tests", "__pycache__",
    "/XF", "*.pyc", ".DS_Store",
    "/NJH", "/NJS", "/NFL", "/NDL", "/NP", "/R:1", "/W:1"
)
& robocopy @roboArgs | Out-Null
$rc = $LASTEXITCODE
if ($rc -ge 8) {
    Write-Error "robocopy failed (exit code $rc)."
    exit 1
}

# robocopy /MIR purges dest files absent from source, but /XD excludes a directory
# from processing ENTIRELY — so it neither copies nor PURGES an excluded dir. A
# stale codex/ (or tests/) left in the dest from an earlier full copy would survive
# as unused weight. Setup's Cursor-vs-Codex detection is a POSITIVE path check
# (PLUGIN_ROOT under ~/.cursor/) — not codex/ absence — but still strip excluded
# dirs so the snapshot stays a true mirror (rsync side: --delete-excluded).
foreach ($x in @("codex", "tests", "__pycache__")) {
    $stale = Join-Path $Dest $x
    if (Test-Path $stale) { Remove-Item -Recurse -Force $stale }
}

function Get-DirCount($path) {
    if (-not (Test-Path $path)) { return 0 }
    return (Get-ChildItem -Path $path -Directory -ErrorAction SilentlyContinue | Measure-Object).Count
}
function Get-FileCount($path, $filter) {
    if (-not (Test-Path $path)) { return 0 }
    return (Get-ChildItem -Path $path -Filter $filter -File -ErrorAction SilentlyContinue | Measure-Object).Count
}

$skills   = Get-DirCount  (Join-Path $Dest "skills")
$commands = Get-FileCount (Join-Path $Dest "commands\flow-next") "*.md"
$agents   = Get-FileCount (Join-Path $Dest "agents") "*.md"
$rules    = Get-FileCount (Join-Path $Dest "rules") "*.mdc"

Write-Host ""
Write-Host "Installed. Cursor registers the components on next launch:"
Write-Host "  skills:   $skills"
Write-Host "  commands: $commands"
Write-Host "  agents:   $agents"
Write-Host "  rules:    $rules"
Write-Host ""
Write-Host "Next steps:"
Write-Host "  1. Fully restart Cursor (Quit, reopen) - a new local plugin needs a full restart."
Write-Host "  2. In your project, run /flow-next:setup (writes .flow\bin\flowctl + AGENTS.md;"
Write-Host "     skills resolve flowctl via .flow\bin since Cursor exposes no plugin-root env var)."
Write-Host "  3. Drive the workflow by TYPING the commands - /flow-next:plan, /flow-next:work, ..."
Write-Host "     (they run when typed even though the slash autocomplete under-lists them)."
Write-Host ""
Write-Host "Re-run this script after 'git pull' to update the snapshot."
Write-Host "Uninstall: Remove-Item -Recurse -Force `"$Dest`""
