@echo off
setlocal
chcp 65001 >nul

py -3.11 -c "import sys" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] 未找到 Python 3.11，请先安装或修复 Python Launcher。
    pause
    exit /b 1
)

for /f "delims=" %%V in ('py -3.11 -c "from app_info import APP_VERSION; print(APP_VERSION)"') do set "APP_VERSION=%%V"
if not defined APP_VERSION (
    echo [ERROR] 无法从 app_info.py 读取版本号。
    pause
    exit /b 1
)

for /f "delims=" %%N in ('py -3.11 -c "from app_info import APP_EXECUTABLE_NAME; print(APP_EXECUTABLE_NAME)"') do set "APP_EXE_NAME=%%N"
if not defined APP_EXE_NAME (
    echo [ERROR] 无法从 app_info.py 读取应用名称。
    pause
    exit /b 1
)

echo ==========================================
echo      GNBP Image Generator V%APP_VERSION%
echo      构建工具 (Python 3.11)
echo ==========================================

REM 1. 强制清理旧文件 (防止缓存导致玄学报错)
echo [1/3] 清理旧的构建文件...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

REM 2. (可选) 自动重新生成图标，防止图标文件丢失
echo [2/3] 检查/生成图标...
if exist make_icon.py (
    py -3.11 make_icon.py
    if errorlevel 1 (
        echo [ERROR] 图标生成失败。
        pause
        exit /b 1
    )
)

REM 3. 调用 Python 3.11 运行 PyInstaller
echo [3/3] 开始打包...
echo 正在使用: Python 3.11
echo ------------------------------------------

REM 核心命令：指定用 3.11 的环境来跑 PyInstaller
py -3.11 -m PyInstaller build.spec --clean --noconfirm

echo ==========================================
if %ERRORLEVEL% == 0 (
    echo [SUCCESS] 打包成功：dist\%APP_EXE_NAME%.exe
) else (
    echo [ERROR] 打包失败，请检查上面的报错信息。
)
echo ==========================================
pause
endlocal
