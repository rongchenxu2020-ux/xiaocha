#!/bin/bash
# 启动做市商机器人测试（带GUI显示）
# 使用方法: bash booking/start_test_market_maker.sh

echo "========================================"
echo "做市商机器人测试 - GUI监控模式"
echo "========================================"
echo ""

python3 booking/test_market_maker_gui.py
