@echo off
setlocal
set "WORKSPACE_ROOT=%~dp0"
cd /d "%WORKSPACE_ROOT%"
if defined PYTHONPATH (set "PYTHONPATH=%WORKSPACE_ROOT%;%PYTHONPATH%") else (set "PYTHONPATH=%WORKSPACE_ROOT%")
"%WORKSPACE_ROOT%agent_tools\.venv\Scripts\python.exe" -m agent_tools.agent_workspace --ui web %*
exit /b %ERRORLEVEL%
