@echo off
chcp 65001 >nul
title 投资·AI产业链每日情报看板

echo ====================================================
echo   投资·AI产业链每日情报看板 - 一键启动
echo ====================================================
echo.

:: 检查Python
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 未检测到 Python，正在打开下载页面...
    echo 请安装 Python 3.10+ ，安装时勾选 "Add Python to PATH"
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 首次运行时安装依赖
if not exist ".deps_installed" (
    echo [首次启动] 正在安装依赖包...
    pip install -r scraper/requirements.txt -q
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] 依赖安装失败，请检查网络连接
        pause
        exit /b 1
    )
    echo. > .deps_installed
    echo [OK] 依赖安装完成
    echo.
)

:: 启动服务器并在2秒后自动打开浏览器
echo [启动] 正在启动本地服务器...
echo.
echo   访问地址: http://localhost:8199
echo   关闭此窗口即可停止服务器
echo.

:: 后台启动浏览器延迟打开
start "" cmd /c "timeout /t 3 /nobreak >nul && start http://localhost:8199"

python server.py
pause
