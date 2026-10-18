@ECHO OFF
REM flowctl.cmd -- Windows batch launcher for cmd.exe / PowerShell (Claude
REM Desktop, native Codex, native Cursor). Invokes the source-first bootstrap
REM beside flowctl.py via a probed Python 3.11+ interpreter. Companion to the extensionless
REM bash `flowctl` launcher (Git Bash / WSL / macOS / Linux); PATHEXT resolves
REM `flowctl` to this file in cmd/PowerShell.
REM
REM Probe = functionality + minimum version: each candidate must actually run
REM and report Python 3.11+, so the Microsoft Store `python3` App Execution
REM Alias stub and working-but-too-old interpreters are skipped. Candidate order:
REM   %PYTHON_BIN% (command name only) -> py -3 -> python3 -> python
REM Keep this probe in sync with plugins/flow-next/scripts/lib/pick-python.sh.
GOTO :start

:find_dp0
SET "dp0=%~dp0"
SET "self=%~f0"
EXIT /b

:start
SETLOCAL
CALL :find_dp0

REM FLOW_NEXT_FLOWCTL names the flowctl a host orchestrator wants every call to use
REM (never FLOWCTL_BIN: an unrelated flowctl CLI tells its users to set that).
REM Delegate before the Python probe so that flowctl needs no Python. cmd.exe
REM decides what runs (PATHEXT finds flowctl.exe from a bare flowctl path); a
REM value it cannot run fails loudly, because falling back would let two
REM flowctls write one repo. A value naming this launcher (or its bash twin)
REM runs it normally; %%~fI normalizes slashes so a forward-slash path to this
REM file cannot recurse. 9009 is cmd.exe's "not recognized" exit code.
IF NOT DEFINED FLOW_NEXT_FLOWCTL GOTO :probe
FOR %%I IN ("%FLOW_NEXT_FLOWCTL%") DO SET "_bin=%%~fI"
IF /I "%_bin%"=="%self%" GOTO :probe
IF /I "%_bin%"=="%dp0%flowctl" GOTO :probe
CALL "%_bin%" %*
IF ERRORLEVEL 9009 IF NOT ERRORLEVEL 9010 GOTO :bad_bin
EXIT /b %errorlevel%

:bad_bin
ECHO flowctl: FLOW_NEXT_FLOWCTL is set but could not be run: "%FLOW_NEXT_FLOWCTL%" 1>&2
ECHO   Fix the path, or unset FLOW_NEXT_FLOWCTL to use the plugin's bundled flowctl. 1>&2
EXIT /b 1

:probe

SET "_prog="
SET "_old="

REM %PYTHON_BIN% is honored as a COMMAND NAME ONLY (e.g. python3.12, py) -- no
REM quoted paths-with-spaces / embedded args, which keeps batch quoting trivial.
REM CALL is required because a candidate may itself be a .cmd shim; without it,
REM control transfers out of this launcher instead of resuming the probe ladder.
IF DEFINED PYTHON_BIN (
  CALL "%PYTHON_BIN%" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 3)" >NUL 2>&1
  IF NOT ERRORLEVEL 1 SET "_prog=%PYTHON_BIN%"
  IF NOT DEFINED _prog IF ERRORLEVEL 3 IF NOT ERRORLEVEL 4 SET "_old=%PYTHON_BIN%"
)
IF NOT DEFINED _prog (
  CALL py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 3)" >NUL 2>&1
  IF NOT ERRORLEVEL 1 SET "_prog=py -3"
  IF NOT DEFINED _prog IF ERRORLEVEL 3 IF NOT ERRORLEVEL 4 SET "_old=py -3"
)
IF NOT DEFINED _prog (
  CALL python3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 3)" >NUL 2>&1
  IF NOT ERRORLEVEL 1 SET "_prog=python3"
  IF NOT DEFINED _prog IF ERRORLEVEL 3 IF NOT ERRORLEVEL 4 SET "_old=python3"
)
IF NOT DEFINED _prog (
  CALL python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 3)" >NUL 2>&1
  IF NOT ERRORLEVEL 1 SET "_prog=python"
  IF NOT DEFINED _prog IF ERRORLEVEL 3 IF NOT ERRORLEVEL 4 SET "_old=python"
)

IF NOT DEFINED _prog (
  IF DEFINED _old (
    ECHO flowctl: Python 3.11 or newer is required; working but too-old candidate: %_old%. 1>&2
    ECHO   Install a supported Python, or set PYTHON_BIN to its command name. 1>&2
  ) ELSE (
    ECHO flowctl: no working Python interpreter found ^(tried PYTHON_BIN, py -3, python3, python^). 1>&2
    ECHO   On Windows, 'python3' may be the disabled Microsoft Store alias stub; 1>&2
    ECHO   install python.org Python ^(or the py launcher^), or set PYTHON_BIN to a working interpreter. 1>&2
  )
  EXIT /b 1
)

REM %_prog% is intentionally UNQUOTED so a two-word `py -3` expands to two argv
REM words; this is why %PYTHON_BIN% must be a command name only. Args (%*) and
REM the dp0 path are quoted so spaced/paren'd install paths survive.
SET "_entry=%dp0%flowctl.py"
IF EXIST "%dp0%flowctl_bootstrap.py" IF "%~2"=="" IF "%~1"=="usage" SET "_entry=%dp0%flowctl_bootstrap.py"
IF EXIST "%dp0%flowctl_bootstrap.py" IF "%~2"=="" IF "%~1"=="--help" SET "_entry=%dp0%flowctl_bootstrap.py"
%_prog% "%_entry%" %*
EXIT /b %errorlevel%
