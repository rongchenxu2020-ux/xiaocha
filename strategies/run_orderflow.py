#!/usr/bin/env python3
"""
做市商交易策略命令行入口（原订单流策略已改为做市商策略）

使用方法:
    python booking/run_orderflow.py --exchange edgex --ticker ETH --position-size 0.1
"""

import argparse
import asyncio
import sys
from pathlib import Path
from decimal import Decimal
import dotenv

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.config import MarketMakerConfig
from strategies.market_maker_strategy import MarketMakerStrategy
# 向后兼容
from shared.config import OrderFlowConfig
try:
    from booking.orderflow_strategy import OrderFlowStrategy
except ImportError:
    OrderFlowStrategy = None
from exchanges import ExchangeFactory


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='做市商交易策略（原订单流策略已改为做市商策略）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    python booking/run_orderflow.py --exchange edgex --ticker ETH --min-order-size 10000
    python booking/run_orderflow.py --exchange backpack --ticker BTC --imbalance-threshold 0.7
    python booking/run_orderflow.py --exchange edgex --ticker ETH --position-size 0.1 --max-position 1.0
        """
    )
    
    # 基础参数
    parser.add_argument('--exchange', type=str, required=True,
                        choices=ExchangeFactory.get_supported_exchanges(),
                        help='交易所名称')
    parser.add_argument('--ticker', type=str, required=True,
                        help='交易对符号 (如: ETH, BTC)')
    parser.add_argument('--env-file', type=str, default='.env',
                        help='环境变量文件路径 (默认: .env)')
    
    # 订单簿分析参数
    parser.add_argument('--orderbook-depth', type=int, default=20,
                        help='订单簿深度 (默认: 20)')
    parser.add_argument('--imbalance-threshold', type=float, default=0.6,
                        help='失衡阈值 0-1 (默认: 0.6)')
    parser.add_argument('--min-order-size', type=Decimal, default=Decimal(10000),
                        help='最小监控订单规模，美元 (默认: 10000)')
    
    # 交易流监控参数
    parser.add_argument('--large-order-threshold', type=Decimal, default=Decimal(50000),
                        help='大单阈值，美元 (默认: 50000)')
    parser.add_argument('--trade-flow-window', type=int, default=60,
                        help='交易流时间窗口，秒 (默认: 60)')
    
    # 信号生成参数
    parser.add_argument('--signal-strength-threshold', type=float, default=0.7,
                        help='信号强度阈值 0-1 (默认: 0.7)')
    parser.add_argument('--confirmation-ticks', type=int, default=3,
                        help='确认所需的tick数 (默认: 3)')
    
    # 执行参数
    parser.add_argument('--position-size', type=Decimal, default=Decimal(0.1),
                        help='每笔交易的头寸大小 (默认: 0.1)')
    parser.add_argument('--max-position', type=Decimal, default=Decimal(1.0),
                        help='最大持仓 (默认: 1.0)')
    parser.add_argument('--stop-loss-pct', type=Decimal, default=Decimal(0.02),
                        help='止损百分比 (默认: 0.02)')
    parser.add_argument('--take-profit-pct', type=Decimal, default=Decimal(0.01),
                        help='止盈百分比 (默认: 0.01)')
    
    # 风险控制参数
    parser.add_argument('--max-orders-per-minute', type=int, default=5,
                        help='每分钟最大订单数 (默认: 5)')
    parser.add_argument('--max-daily-loss', type=Decimal, default=None,
                        help='每日最大亏损 (默认: 无限制)')
    
    # 其他参数
    parser.add_argument('--update-interval', type=float, default=0.5,
                        help='更新间隔，秒 (默认: 0.5)')
    parser.add_argument('--disable-logging', action='store_true',
                        help='禁用日志输出')
    
    return parser.parse_args()


async def main():
    """主函数"""
    args = parse_arguments()
    
    # 加载环境变量
    env_path = Path(args.env_file)
    if not env_path.exists():
        print(f"错误: 环境变量文件不存在: {env_path.resolve()}")
        sys.exit(1)
    dotenv.load_dotenv(args.env_file)
    
    # 创建交易所配置（需要从交易所获取contract_id和tick_size）
    # 这里简化处理，实际应该从交易所API获取
    exchange_config = {
        'contract_id': '',  # 将在策略初始化时设置
        'ticker': args.ticker.upper(),
        'tick_size': Decimal('0.01'),  # 默认值，应从交易所获取
    }
    
    # 创建策略配置（使用做市商配置）
    strategy_config = MarketMakerConfig(
        exchange=args.exchange.lower(),
        ticker=args.ticker.upper(),
        contract_id='',  # 将在初始化时设置
        orderbook_depth=args.orderbook_depth,
        order_size=args.position_size,
        spread_type='percentage',
        target_spread=Decimal('0.0001'),
        spread_ratio=Decimal('0.5'),
        min_spread=Decimal('0.0001'),
        max_position=args.max_position,
        inventory_skew_enabled=True,
        inventory_skew_factor=Decimal('0.3'),
        price_update_threshold=0.001,
        update_interval=args.update_interval,
        enable_logging=not args.disable_logging
    )
    
    # 创建策略实例（使用做市商策略）
    strategy = MarketMakerStrategy(strategy_config)
    
    try:
        # 初始化策略
        await strategy.initialize()
        
        # 运行策略
        await strategy.run()
        
    except KeyboardInterrupt:
        print("\n收到停止信号，正在关闭...")
    except Exception as e:
        print(f"策略执行失败: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await strategy.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
