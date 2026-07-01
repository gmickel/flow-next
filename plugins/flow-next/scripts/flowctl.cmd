@ECHO OFF
REM flowctl.cmd -- Windows batch launcher for cmd.exe / PowerShell (Claude
REM Desktop, native Codex, native Cursor). Invokes flowctl.py from this
REM directory via a probed Python interpreter. Companion to the extensionless
REM bash `flowctl` launcher (Git Bash / WSL / macOS / Linux); PATHEXT resolves
REM `flowctl` to this file in cmd/PowerShell.
REM
REM Probe = functionality, not presence: each candidate must actually run
REM `<cand> -c "import sys"` and exit 0, so the Microsoft Store `python3` App
REM Execution Alias stub (prints "Python was not found", exits 9009) is skipped
REM even though it is on PATH. Candidate order mirrors the bash launcher:
REM   %PYTHON_BIN% (command name only) -> py -3 -> python3 -> python
REM Keep this probe in sync with plugins/flow-next/scripts/lib/pick-python.sh.
GOTO :start

:find_dp0
SET "dp0=%~dp0"
EXIT /b

:start
SETLOCAL
CALL :find_dp0

SET "_prog="

REM %PYTHON_BIN% is honored as a COMMAND NAME ONLY (e.g. python3.12, py) -- no
REM quoted paths-with-spaces / embedded args, which keeps batch quoting trivial.
IF DEFINED PYTHON_BIN (
  "%PYTHON_BIN%" -c "import sys" >NUL 2>&1 && SET "_prog=%PYTHON_BIN%"
)
IF NOT DEFINED _prog (
  py -3 -c "import sys" >NUL 2>&1 && SET "_prog=py -3"
)
IF NOT DEFINED _prog (
  python3 -c "import sys" >NUL 2>&1 && SET "_prog=python3"
)
IF NOT DEFINED _prog (
  python -c "import sys" >NUL 2>&1 && SET "_prog=python"
)

IF NOT DEFINED _prog (
  ECHO flowctl: no working Python interpreter found ^(tried PYTHON_BIN, py -3, python3, python^). 1>&2
  ECHO   On Windows, 'python3' may be the disabled Microsoft Store alias stub; 1>&2
  ECHO   install python.org Python ^(or the py launcher^), or set PYTHON_BIN to a working interpreter. 1>&2
  EXIT /b 1
)

REM %_prog% is intentionally UNQUOTED so a two-word `py -3` expands to two argv
REM words; this is why %PYTHON_BIN% must be a command name only. Args (%*) and
REM the dp0 path are quoted so spaced/paren'd install paths survive.
%_prog% "%dp0%flowctl.py" %*
EXIT /b %errorlevel%
