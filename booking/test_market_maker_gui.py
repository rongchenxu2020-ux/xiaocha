#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
做市商机器人测试脚本 - 带GUI显示
启动做市商机器人在模拟模式下运行，并在GUI中显示状态
"""

import sys
import subprocess
import time
import threading
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def start_market_maker_bot():
    """启动做市商机器人（模拟模式）"""
    bot_script = project_root / "booking" / "run_market_maker_bot.py"
    
    cmd = [
        sys.executable,
        str(bot_script),
        "--exchange", "edgex",
        "--ticker", "ETH",
        "--order-size", "0.1",
        "--spread-ratio", "0.5",
        "--max-position", "1.0",
        "--simulate",
        "--enable-logging"
    ]
    
    print("=" * 80)
    print("启动做市商机器人（模拟模式）...")
    print("=" * 80)
    print(f"命令: {' '.join(cmd)}")
    print()
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            universal_newlines=True
        )
        
        # 实时输出日志
        def print_output():
            for line in process.stdout:
                print(line, end='')
        
        output_thread = threading.Thread(target=print_output, daemon=True)
        output_thread.start()
        
        return process
    except Exception as e:
        print(f"启动机器人失败: {e}")
        return None


def start_gui_monitor():
    """启动GUI监控工具"""
    gui_script = project_root / "booking" / "monitor_bots_gui.py"
    
    cmd = [sys.executable, str(gui_script)]
    
    print("=" * 80)
    print("启动GUI监控工具...")
    print("=" * 80)
    print()
    
    try:
        subprocess.Popen(cmd)
        print("GUI监控工具已启动")
    except Exception as e:
        print(f"启动GUI失败: {e}")


def main():
    """主函数"""
    print("=" * 80)
    print("做市商机器人测试 - GUI监控模式")
    print("=" * 80)
    print()
    print("此脚本将:")
    print("  1. 启动做市商机器人在模拟模式下运行")
    print("  2. 启动GUI监控工具显示机器人状态")
    print()
    print("提示:")
    print("  - 机器人将在模拟模式下运行，不会实际下单")
    print("  - GUI将每3秒自动刷新一次")
    print("  - 按 Ctrl+C 停止机器人")
    print("=" * 80)
    print()
    
    # 等待用户确认
    try:
        input("按 Enter 键开始...")
    except KeyboardInterrupt:
        print("\n已取消")
        return
    
    # 启动GUI监控工具
    print("\n正在启动GUI监控工具...")
    start_gui_monitor()
    time.sleep(2)  # 等待GUI启动
    
    # 启动做市商机器人
    print("\n正在启动做市商机器人...")
    bot_process = start_market_maker_bot()
    
    if not bot_process:
        print("无法启动机器人，退出")
        return
    
    print()
    print("=" * 80)
    print("机器人已启动！")
    print("=" * 80)
    print()
    print("现在可以:")
    print("  - 在GUI中查看机器人状态和交易信号")
    print("  - 查看实时日志输出")
    print("  - 按 Ctrl+C 停止机器人")
    print()
    
    try:
        # 等待进程结束
        bot_process.wait()
    except KeyboardInterrupt:
        print("\n\n收到停止信号，正在关闭机器人...")
        bot_process.terminate()
        try:
            bot_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            bot_process.kill()
        print("机器人已停止")
    
    print("\n测试完成")


if __name__ == "__main__":
    main()
