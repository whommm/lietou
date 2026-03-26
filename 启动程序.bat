@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ====================================
echo 智能岗位分析与寻访助手
====================================
echo.

REM 检查虚拟环境是否存在
if not exist "venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境 venv
    echo 请先创建虚拟环境: python -m venv venv
    pause
    exit /b 1
)

echo [检查] 检查依赖包...
venv\Scripts\python.exe -c "import customtkinter" 2>nul
if errorlevel 1 (
    echo [安装] 正在安装依赖包...
    venv\Scripts\pip.exe install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo [启动] 启动程序...
venv\Scripts\python.exe main.py

if errorlevel 1 (
    echo.
    echo [错误] 程序运行出错
    pause
)
