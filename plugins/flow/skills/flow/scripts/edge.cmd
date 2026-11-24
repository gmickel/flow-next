@ECHO OFF
REM edge.cmd -- Windows batch launcher for cmd.exe / PowerShell.
REM Invokes edge.py beside this script via a probed Python 3.11+ interpreter.
REM Candidate order: %PYTHON_BIN% -> py -3 -> python3 -> python.
GOTO :start

:find_dp0
SET "dp0=%~dp0"
EXIT /b

:start
SETLOCAL
CALL :find_dp0

SET "_prog="
SET "_old="

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
    ECHO edge: Python 3.11 or newer is required; working but too-old candidate: %_old%. 1>&2
    ECHO   Install a supported Python, or set PYTHON_BIN to its command name. 1>&2
  ) ELSE (
    ECHO edge: no working Python interpreter found ^(tried PYTHON_BIN, py -3, python3, python^). 1>&2
    ECHO   On Windows, 'python3' may be the disabled Microsoft Store alias stub; 1>&2
    ECHO   install python.org Python ^(or the py launcher^), or set PYTHON_BIN to a working interpreter. 1>&2
  )
  EXIT /b 1
)

%_prog% "%dp0%edge.py" %*
EXIT /b %errorlevel%
