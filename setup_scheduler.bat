@echo off
chcp 65001 >nul
echo ====================================================
echo 投资·AI产业链每日情报看板 - 定时任务设置
echo ====================================================
echo.

:: 获取当前脚本所在目录
set "PROJECT_DIR=%~dp0"
:: 去掉末尾反斜杠
set "PROJECT_DIR=%PROJECT_DIR:~0,-1%"

:: 查找Python路径
where python >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 未找到 Python，请先安装 Python 并加入 PATH
    pause
    exit /b 1
)

for /f "delims=" %%i in ('where python') do set "PYTHON_PATH=%%i"
echo [OK] Python 路径: %PYTHON_PATH%

:: 任务名称
set "TASK_NAME=AI_DailyBrief_Scraper"

:: 检查任务是否已存在
schtasks /query /tn "%TASK_NAME%" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    echo [INFO] 定时任务已存在，正在更新...
    schtasks /delete /tn "%TASK_NAME%" /f >nul 2>&1
)

:: 创建每天早上8:30运行的定时任务
schtasks /create /tn "%TASK_NAME%" /tr "\"%PYTHON_PATH%\" \"%PROJECT_DIR%\scraper\main.py\"" /sc daily /st 08:30 /f
if %ERRORLEVEL% neq 0 (
    echo [ERROR] 创建定时任务失败
    pause
    exit /b 1
)

echo.
echo ====================================================
echo [OK] 定时任务创建成功！
echo.
echo 任务名称: %TASK_NAME%
echo 执行时间: 每天 08:30
echo 执行内容: python %PROJECT_DIR%\scraper\main.py
echo.
echo 数据将自动更新到:
echo   - site/data/latest.json
echo   - site/data/history/YYYY-MM-DD.json
echo   - AI Investment Daily Brief.html (自包含版本)
echo.
echo 管理命令:
echo   查看任务:   schtasks /query /tn "%TASK_NAME%"
echo   删除任务:   schtasks /delete /tn "%TASK_NAME%" /f
echo   立即运行:   schtasks /run /tn "%TASK_NAME%"
echo   修改时间:   schtasks /change /tn "%TASK_NAME%" /st HH:MM
echo ====================================================
echo.

pause
