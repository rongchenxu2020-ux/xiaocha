@echo off
chcp 65001 >nul
echo 启动订单流机器人监控界面...
python booking\monitor_bots_gui.py
pause
