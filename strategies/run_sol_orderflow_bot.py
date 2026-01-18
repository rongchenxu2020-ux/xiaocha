#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SOL订单流机器人 - 优化版
专门针对SOL交易对优化的订单流策略机器人，提升触发订单流策略的可能性
"""

import sys
import asyncio
import signal
import json
import time
import csv
import os
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import dotenv

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.config import MarketMakerConfig
from strategies.run_orderflow_bot import RealTimeOrderFlowBot


def main():
    """主函数 - SOL优化配置"""
    import argparse
    
    # 设置输出编码
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description='SOL做市商策略机器人 - 优化版（原订单流策略已改为做市商策略）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
SOL优化参数说明:
  --mode: 运行模式
    - balanced: 平衡设置（推荐开始使用）
    - aggressive: 激进设置（更容易触发）
    - very-aggressive: 非常激进（最大化触发频率）
    - custom: 自定义参数

示例:
  # 使用平衡设置（推荐）
  python booking/run_sol_orderflow_bot.py --mode balanced --simulate
  
  # 使用激进设置
  python booking/run_sol_orderflow_bot.py --mode aggressive --simulate
  
  # 使用非常激进设置
  python booking/run_sol_orderflow_bot.py --mode very-aggressive --simulate
  
  # 自定义参数
  python booking/run_sol_orderflow_bot.py --mode custom \\
      --imbalance-threshold 0.3 \\
      --signal-strength-threshold 0.4 \\
      --confirmation-ticks 1 \\
      --simulate
        """
    )
    
    parser.add_argument('--exchange', type=str, default='edgex', help='交易所名称（默认: edgex）')
    parser.add_argument('--mode', type=str, default='balanced',
                       choices=['balanced', 'aggressive', 'very-aggressive', 'custom'],
                       help='运行模式（默认: balanced）')
    parser.add_argument('--position-size', type=float, default=None, help='每笔交易的头寸大小（覆盖模式默认值）')
    parser.add_argument('--imbalance-threshold', type=float, default=None, help='失衡阈值（覆盖模式默认值）')
    parser.add_argument('--signal-strength-threshold', type=float, default=None, help='信号强度阈值（覆盖模式默认值）')
    parser.add_argument('--confirmation-ticks', type=int, default=None, help='确认所需的tick数（覆盖模式默认值）')
    parser.add_argument('--update-interval', type=float, default=None, help='更新间隔（秒）（覆盖模式默认值）')
    parser.add_argument('--max-position', type=float, default=None, help='最大持仓（覆盖模式默认值）')
    parser.add_argument('--stop-loss-pct', type=float, default=0.02, help='止损百分比（默认: 0.02）')
    parser.add_argument('--take-profit-pct', type=float, default=0.01, help='止盈百分比（默认: 0.01）')
    parser.add_argument('--enable-logging', action='store_true', help='启用详细日志')
    parser.add_argument('--simulate', action='store_true', help='模拟模式：只跟踪信号，不实际下单')
    
    args = parser.parse_args()
    
    # 加载环境变量
    env_file = project_root / ".env"
    if env_file.exists():
        dotenv.load_dotenv(env_file)
    else:
        print("警告: 未找到 .env 文件，将使用环境变量")
    
    # 根据模式设置默认参数（SOL优化值）
    mode_configs = {
        'balanced': {
            'imbalance_threshold': 0.4,
            'signal_strength_threshold': 0.5,
            'confirmation_ticks': 2,
            'update_interval': 0.4,
            'position_size': 1.0,
            'max_position': 5.0,
        },
        'aggressive': {
            'imbalance_threshold': 0.3,
            'signal_strength_threshold': 0.4,
            'confirmation_ticks': 1,
            'update_interval': 0.3,
            'position_size': 1.0,
            'max_position': 5.0,
        },
        'very-aggressive': {
            'imbalance_threshold': 0.2,
            'signal_strength_threshold': 0.3,
            'confirmation_ticks': 1,
            'update_interval': 0.3,
            'position_size': 1.0,
            'max_position': 5.0,
        },
        'custom': {
            'imbalance_threshold': 0.3,
            'signal_strength_threshold': 0.4,
            'confirmation_ticks': 1,
            'update_interval': 0.3,
            'position_size': 1.0,
            'max_position': 5.0,
        }
    }
    
    # 获取模式配置
    mode_config = mode_configs[args.mode]
    
    # 使用命令行参数覆盖模式默认值
    imbalance_threshold = args.imbalance_threshold if args.imbalance_threshold is not None else mode_config['imbalance_threshold']
    signal_strength_threshold = args.signal_strength_threshold if args.signal_strength_threshold is not None else mode_config['signal_strength_threshold']
    confirmation_ticks = args.confirmation_ticks if args.confirmation_ticks is not None else mode_config['confirmation_ticks']
    update_interval = args.update_interval if args.update_interval is not None else mode_config['update_interval']
    position_size = args.position_size if args.position_size is not None else mode_config['position_size']
    max_position = args.max_position if args.max_position is not None else mode_config['max_position']
    
    # 显示配置信息
    print("=" * 80)
    print("SOL做市商策略机器人 - 优化版")
    print("=" * 80)
    print()
    print("配置:")
    print(f"  - 交易所: {args.exchange}")
    print(f"  - 交易对: SOL")
    print(f"  - 运行模式: {args.mode.upper()}")
    print(f"  - 头寸大小: {position_size}")
    print(f"  - 价差类型: percentage (使用市场价差的百分比)")
    print(f"  - 价差比例: 0.5 (市场价差的50%)")
    print(f"  - 订单大小: {position_size}")
    print(f"  - 更新间隔: {update_interval}秒 (默认: 0.5, 缩短以提升响应)")
    print(f"  - 最大持仓: {max_position}")
    print(f"  - 运行模式: {'[模拟模式 - 不会实际下单]' if args.simulate else '[真实交易模式 - 将使用真实资金]'}")
    print()
    
    if not args.simulate:
        print("⚠️  警告: 这是实时交易机器人，将使用真实资金进行交易！")
        print("⚠️  建议先使用 --simulate 模式测试")
        print()
        response = input("确认继续？(yes/no): ")
        if response.lower() != 'yes':
            print("已取消")
            return
    else:
        print("✅ 模拟模式: 将跟踪和分析信号，但不会实际下单")
    
    print("按 Ctrl+C 停止机器人")
    print("=" * 80)
    print()
    
    # 创建配置（使用做市商配置）
    config = MarketMakerConfig(
        exchange=args.exchange,
        ticker='SOL',
        contract_id='SOL',  # 将在初始化时更新
        orderbook_depth=20,
        order_size=Decimal(str(position_size)),
        spread_type='percentage',
        target_spread=Decimal('0.0001'),
        spread_ratio=Decimal('0.5'),  # 使用市场价差的50%
        min_spread=Decimal('0.0001'),
        max_position=Decimal(str(max_position)),
        inventory_skew_enabled=True,
        inventory_skew_factor=Decimal('0.3'),
        price_update_threshold=0.001,
        update_interval=update_interval,
        enable_logging=args.enable_logging
    )
    
    # 创建机器人
    bot = RealTimeOrderFlowBot(config)
    bot.simulate_mode = args.simulate  # 设置模拟模式
    # 同步设置策略的模拟模式
    if hasattr(bot.strategy, 'simulate_mode'):
        bot.strategy.simulate_mode = args.simulate
    
    # 设置信号处理
    def signal_handler(sig, frame):
        print("\n收到停止信号，正在关闭机器人...")
        bot.stop_flag = True
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 初始化并运行
        asyncio.run(bot.initialize())
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n机器人已停止")
    except Exception as e:
        print(f"\n机器人运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
