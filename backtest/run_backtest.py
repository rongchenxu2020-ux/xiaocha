#!/usr/bin/env python3
"""
订单流策略回测命令行入口

使用方法:
    python booking/run_backtest.py --data data.json --exchange edgex --ticker ETH
"""

import argparse
import sys
from pathlib import Path
from decimal import Decimal

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.config import OrderFlowConfig
from backtest.backtest_data import BacktestDataLoader
from backtest.backtest_engine import BacktestEngine
from backtest.backtest_report import BacktestReportGenerator


def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description='订单流交易策略回测',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
    # 使用JSON数据文件回测
    python booking/run_backtest.py --data data.json --exchange edgex --ticker ETH
    
    # 使用CSV数据文件回测
    python booking/run_backtest.py --orderbook-csv orderbook.csv --trades-csv trades.csv --exchange edgex --ticker ETH
    
    # 生成模拟数据并回测
    python booking/run_backtest.py --generate-mock --start-price 2000 --num-samples 1000 --exchange edgex --ticker ETH
    
    # 自定义策略参数
    python booking/run_backtest.py --data data.json --exchange edgex --ticker ETH \\
        --imbalance-threshold 0.6 --signal-strength-threshold 0.7 --position-size 0.1
        """
    )
    
    # 数据源参数
    data_group = parser.add_mutually_exclusive_group(required=True)
    data_group.add_argument('--data', type=str,
                           help='JSON格式的回测数据文件')
    data_group.add_argument('--orderbook-csv', type=str,
                           help='订单簿CSV文件')
    data_group.add_argument('--generate-mock', action='store_true',
                           help='生成模拟数据进行回测')
    data_group.add_argument('--from-api', action='store_true',
                           help='从交易所API获取数据（注意：大多数交易所不提供历史订单簿数据）')
    
    parser.add_argument('--trades-csv', type=str,
                       help='交易CSV文件（与--orderbook-csv一起使用）')
    
    # API数据参数
    parser.add_argument('--start-time', type=float,
                       help='开始时间戳（与--from-api一起使用，如果为历史时间将被忽略）')
    parser.add_argument('--end-time', type=float,
                       help='结束时间戳（与--from-api一起使用）')
    parser.add_argument('--duration-seconds', type=float,
                       help='收集时长，秒（与--from-api一起使用，如果未指定end-time）')
    parser.add_argument('--interval-seconds', type=float, default=1.0,
                       help='API数据采样间隔，秒（默认: 1.0）')
    parser.add_argument('--save-collected-data', type=str,
                       help='保存收集的数据到文件（与--from-api一起使用）')
    
    # 模拟数据参数
    parser.add_argument('--start-price', type=Decimal, default=Decimal(2000),
                       help='模拟数据起始价格（默认: 2000）')
    parser.add_argument('--num-samples', type=int, default=1000,
                       help='模拟数据样本数量（默认: 1000）')
    parser.add_argument('--interval-seconds', type=float, default=1.0,
                       help='模拟数据时间间隔，秒（默认: 1.0）')
    parser.add_argument('--volatility', type=float, default=0.001,
                       help='模拟数据波动率（默认: 0.001）')
    
    # 基础参数
    parser.add_argument('--exchange', type=str, required=True,
                       help='交易所名称（用于配置）')
    parser.add_argument('--ticker', type=str, required=True,
                       help='交易对符号')
    
    # 策略参数
    parser.add_argument('--orderbook-depth', type=int, default=20,
                       help='订单簿深度（默认: 20）')
    parser.add_argument('--imbalance-threshold', type=float, default=0.6,
                       help='失衡阈值 0-1（默认: 0.6）')
    parser.add_argument('--min-order-size', type=Decimal, default=Decimal(10000),
                       help='最小监控订单规模，美元（默认: 10000）')
    parser.add_argument('--large-order-threshold', type=Decimal, default=Decimal(50000),
                       help='大单阈值，美元（默认: 50000）')
    parser.add_argument('--trade-flow-window', type=int, default=60,
                       help='交易流时间窗口，秒（默认: 60）')
    parser.add_argument('--signal-strength-threshold', type=float, default=0.7,
                       help='信号强度阈值 0-1（默认: 0.7）')
    parser.add_argument('--confirmation-ticks', type=int, default=3,
                       help='确认所需的tick数（默认: 3）')
    parser.add_argument('--position-size', type=Decimal, default=Decimal(0.1),
                       help='每笔交易的头寸大小（默认: 0.1）')
    parser.add_argument('--max-position', type=Decimal, default=Decimal(1.0),
                       help='最大持仓（默认: 1.0）')
    parser.add_argument('--stop-loss-pct', type=Decimal, default=Decimal(0.02),
                       help='止损百分比（默认: 0.02）')
    parser.add_argument('--take-profit-pct', type=Decimal, default=Decimal(0.01),
                       help='止盈百分比（默认: 0.01）')
    
    # 回测参数
    parser.add_argument('--initial-balance', type=Decimal, default=Decimal(10000),
                       help='初始资金（默认: 10000）')
    
    # 输出参数
    parser.add_argument('--output-dir', type=str, default='backtest_results',
                       help='输出目录（默认: backtest_results）')
    parser.add_argument('--export-trades', action='store_true',
                       help='导出交易记录到CSV')
    parser.add_argument('--export-equity', action='store_true',
                       help='导出权益曲线到CSV')
    
    return parser.parse_args()


def main():
    """主函数"""
    args = parse_arguments()
    
    # 创建输出目录
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True)
    
    # 加载回测数据
    print("加载回测数据...")
    if args.generate_mock:
        print(f"生成模拟数据: {args.num_samples} 个样本, 起始价格 ${args.start_price}")
        data = BacktestDataLoader.generate_mock_data(
            start_price=args.start_price,
            num_samples=args.num_samples,
            interval_seconds=args.interval_seconds,
            volatility=args.volatility
        )
    elif args.from_api:
        if not args.end_time and not args.duration_seconds:
            print("错误: 使用 --from-api 时必须指定 --end-time 或 --duration-seconds")
            sys.exit(1)
        print(f"从交易所API实时收集数据: {args.exchange} {args.ticker}")
        print("⚠️  注意: 大多数交易所不提供历史订单簿数据API")
        print("⚠️  此功能将实时收集当前数据，可用于后续回测")
        import asyncio
        data = asyncio.run(BacktestDataLoader.load_from_exchange_api(
            exchange=args.exchange,
            ticker=args.ticker,
            start_time=args.start_time,
            end_time=args.end_time,
            duration_seconds=args.duration_seconds,
            interval_seconds=args.interval_seconds,
            save_to_file=args.save_collected_data
        ))
    elif args.data:
        print(f"从JSON文件加载: {args.data}")
        data = BacktestDataLoader.load_from_json(args.data)
    elif args.orderbook_csv:
        print(f"从CSV文件加载: {args.orderbook_csv}")
        data = BacktestDataLoader.load_from_csv(
            args.orderbook_csv,
            args.trades_csv
        )
    else:
        print("错误: 必须指定数据源")
        sys.exit(1)
    
    print(f"数据加载完成: {len(data.orderbooks)} 个订单簿快照, {len(data.trades)} 笔交易")
    print(f"时间范围: {data.start_time} - {data.end_time}")
    
    # 创建策略配置
    config = OrderFlowConfig(
        exchange=args.exchange.lower(),
        ticker=args.ticker.upper(),
        contract_id=args.ticker.upper(),  # 回测时使用ticker作为contract_id
        orderbook_depth=args.orderbook_depth,
        imbalance_threshold=args.imbalance_threshold,
        min_order_size=args.min_order_size,
        large_order_threshold=args.large_order_threshold,
        trade_flow_window=args.trade_flow_window,
        signal_strength_threshold=args.signal_strength_threshold,
        confirmation_ticks=args.confirmation_ticks,
        position_size=args.position_size,
        max_position=args.max_position,
        stop_loss_pct=args.stop_loss_pct,
        take_profit_pct=args.take_profit_pct,
        max_orders_per_minute=5,
        max_daily_loss=None,
        update_interval=0.5,
        enable_logging=False
    )
    
    # 创建回测引擎
    print("\n开始回测...")
    engine = BacktestEngine(config, initial_balance=args.initial_balance)
    result = engine.run(data)
    
    # 生成报告
    print("\n生成回测报告...")
    report_file = output_dir / f"backtest_report_{args.ticker}_{int(data.start_time)}.txt"
    report_text = BacktestReportGenerator.generate_text_report(result, str(report_file))
    
    # 打印报告
    print("\n" + report_text)
    
    # 导出交易记录
    if args.export_trades:
        trades_file = output_dir / f"trades_{args.ticker}_{int(data.start_time)}.csv"
        BacktestReportGenerator.export_trades_to_csv(result, str(trades_file))
    
    # 导出权益曲线
    if args.export_equity:
        equity_file = output_dir / f"equity_curve_{args.ticker}_{int(data.start_time)}.csv"
        BacktestReportGenerator.export_equity_curve_to_csv(result, str(equity_file))
    
    # 打印摘要
    summary = BacktestReportGenerator.generate_summary(result)
    print(f"\n{summary}")
    print(f"\n详细报告已保存到: {report_file}")


if __name__ == "__main__":
    main()
