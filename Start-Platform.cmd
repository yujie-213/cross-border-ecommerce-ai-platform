@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"
set "PLATFORM_PY=.venv\Scripts\python.exe"
if not exist "%PLATFORM_PY%" set "PLATFORM_PY=.tmp\stage-a-clean\Scripts\python.exe"
if not exist "%PLATFORM_PY%" (
  echo Python environment missing. Follow README first-time setup.
  pause
  exit /b 1
)
"%PLATFORM_PY%" tools\local_platform.py start
if errorlevel 1 pause
