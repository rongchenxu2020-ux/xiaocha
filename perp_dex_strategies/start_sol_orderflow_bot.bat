@echo off
REM SOL订单流机器人启动脚本（Windows）
REM 使用方法: start_sol_orderflow_bot.bat [模式] [其他参数]
REM 
REM 模式选项:
REM   balanced        - 平衡设置（推荐开始使用）
REM   aggressive      - 激进设置（更容易触发）
REM   very-aggressive - 非常激进（最大化触发频率）
REM   custom          - 自定义参数
REM
REM 示例:
REM   start_sol_orderflow_bot.bat balanced
REM   start_sol_orderflow_bot.bat aggressive --simulate
REM   start_sol_orderflow_bot.bat very-aggressive --simulate --enable-logging

chcp 65001 >nul
setlocal

set MODE=balanced
set EXTRA_ARGS=

REM 解析参数
if "%1"=="" goto :run
set MODE=%1
shift

:parse_args
if "%1"=="" goto :run
set EXTRA_ARGS=%EXTRA_ARGS% %1
shift
goto :parse_args

:run
echo ========================================
echo SOL订单流机器人启动脚本
echo ========================================
echo.
echo 模式: %MODE%
echo 额外参数: %EXTRA_ARGS%
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python
    pause
    exit /b 1
)

REM 检查.env文件
if not exist ".env" (
    echo 警告: 未找到 .env 文件
    echo 请确保已配置环境变量
    echo.
)

REM 默认添加模拟模式（如果用户没有指定）
echo %EXTRA_ARGS% | findstr /i "simulate" >nul
if errorlevel 1 (
    echo 提示: 默认使用模拟模式（不会实际下单）
    echo 如需真实交易，请添加参数: --no-simulate 或移除 --simulate
    echo.
    set EXTRA_ARGS=%EXTRA_ARGS% --simulate
)

REM 运行机器人
echo 正在启动SOL订单流机器人...
echo.
python booking/run_sol_orderflow_bot.py --mode %MODE% %EXTRA_ARGS%

if errorlevel 1 (
    echo.
    echo 机器人运行出错，请检查错误信息
    pause
    exit /b 1
)

pause
