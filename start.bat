@echo off
REM RocketGo 自动回复机器人 - Windows启动脚本

echo ========================================
echo RocketGo 自动回复机器人
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未检测到Python，请先安装Python 3.8+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

REM 显示菜单
echo 请选择启动模式:
echo [1] GUI模式 (图形界面)
echo [2] CLI模式 (命令行)
echo [3] 退出
echo.

set /p choice="请输入选项 (1/2/3): "

if "%choice%"=="1" (
    echo.
    echo 启动GUI模式...
    python launcher.py --gui
) else if "%choice%"=="2" (
    echo.
    echo 启动CLI模式...
    python launcher.py --cli
) else if "%choice%"=="3" (
    echo 退出
    exit /b 0
) else (
    echo 无效选项，默认启动GUI模式...
    python launcher.py --gui
)

pause
