@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

set "PYTHON_EXE=%CD%\.venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    echo [ERROR] 未找到项目虚拟环境：.venv\Scripts\python.exe
    echo 请先运行：py -m venv .venv
    pause
    exit /b 1
)

for /f "tokens=3" %%V in ('findstr /B APP_VERSION app_info.py') do set "APP_VERSION=%%~V"
if not defined APP_VERSION (
    echo [ERROR] 无法读取 APP_VERSION。
    pause
    exit /b 1
)

echo ==========================================
echo   GNBP Image Generator V%APP_VERSION%
echo   Portable local build
echo ==========================================

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo 构建便携程序目录...
"%PYTHON_EXE%" -m PyInstaller build.spec --clean --noconfirm
if errorlevel 1 goto :failed

echo [SUCCESS] dist\GNBP-Image-Generator_V%APP_VERSION%-Portable\GNBP-Image-Generator_V%APP_VERSION%.exe
if /i not "%~1"=="--no-pause" pause
exit /b 0

:failed
echo [ERROR] 构建失败，请查看上方日志。
if /i not "%~1"=="--no-pause" pause
exit /b 1
