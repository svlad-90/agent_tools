@echo off
setlocal
set "WORKSPACE_ROOT=%~dp0"
cd /d "%WORKSPACE_ROOT%"

if defined PYTHONPATH (
  set "PYTHONPATH=%WORKSPACE_ROOT%;%PYTHONPATH%"
) else (
  set "PYTHONPATH=%WORKSPACE_ROOT%"
)

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 -m agent_tools.tools.agent_workspace --ui web %*
  exit /b %ERRORLEVEL%
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python -m agent_tools.tools.agent_workspace --ui web %*
  exit /b %ERRORLEVEL%
)

echo python/py was not found in PATH. 1>&2
exit /b 127
