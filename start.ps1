#!/usr/bin/env pwsh
# RocketGo 自动回复机器人 - Windows PowerShell启动脚本

Write-Host "========================================"
Write-Host "RocketGo 自动回复机器人"
Write-Host "========================================"
Write-Host ""

# 检查Python是否安装
try {
    $pythonVersion = python --version 2>&1
    Write-Host "检测到 $pythonVersion"
} catch {
    Write-Host "错误: 未检测到Python，请先安装Python 3.8+" -ForegroundColor Red
    Write-Host "下载地址: https://www.python.org/downloads/"
    Read-Host "按Enter键退出"
    exit 1
}

# 显示菜单
Write-Host ""
Write-Host "请选择启动模式:"
Write-Host "[1] GUI模式 (图形界面)"
Write-Host "[2] CLI模式 (命令行)"
Write-Host "[3] 退出"
Write-Host ""

$choice = Read-Host "请输入选项 (1/2/3)"

switch ($choice) {
    "1" {
        Write-Host ""
        Write-Host "启动GUI模式..." -ForegroundColor Green
        python launcher.py --gui
    }
    "2" {
        Write-Host ""
        Write-Host "启动CLI模式..." -ForegroundColor Green
        python launcher.py --cli
    }
    "3" {
        Write-Host "退出"
        exit 0
    }
    default {
        Write-Host "无效选项，默认启动GUI模式..." -ForegroundColor Yellow
        python launcher.py --gui
    }
}

Read-Host "按Enter键退出"
