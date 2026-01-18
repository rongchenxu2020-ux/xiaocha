@echo off
REM 启动做市商机器人测试（带GUI显示）
REM 使用方法: start_test_market_maker.bat

echo ========================================
echo 做市商机器人测试 - GUI监控模式
echo ========================================
echo.

python booking\test_market_maker_gui.py

pause
