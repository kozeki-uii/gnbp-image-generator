@echo off
setlocal
cd /d "%~dp0"

set "VENV_PYTHON=%CD%\.venv\Scripts\python.exe"
set "VENV_PYTHONW=%CD%\.venv\Scripts\pythonw.exe"

if exist "%VENV_PYTHON%" goto :start_app

echo First run: creating the local Python environment...
where py >nul 2>&1
if not errorlevel 1 goto :create_with_launcher
where python >nul 2>&1
if errorlevel 1 goto :missing_python
python -m venv .venv
goto :environment_created

:create_with_launcher
py -m venv .venv

:environment_created
if errorlevel 1 goto :setup_failed

echo Installing dependencies. This may take a few minutes on the first run...
"%VENV_PYTHON%" -m pip install -r requirements.txt
if errorlevel 1 goto :setup_failed

:start_app
start "" "%VENV_PYTHONW%" "%CD%\main.py"
exit /b 0

:missing_python
echo [ERROR] Python was not found. Install Python 3.11 or newer, then try again.
pause
exit /b 1

:setup_failed
echo [ERROR] Setup failed. Review the message above, then try again.
pause
exit /b 1
