#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速测试订单流策略的脚本
"""

import sys
import os
from pathlib import Path
from decimal import Decimal

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 设置工作目录
os.chdir(project_root)

try:
    from booking.config import OrderFlowConfig
    from booking.backtest_data import BacktestDataLoader
    from booking.backtest_engine import BacktestEngine
    from booking.backtest_report import BacktestReportGenerator
except ImportError as e:
    print(f"导入错误: {e}")
    print(f"当前工作目录: {os.getcwd()}")
    print(f"Python路径: {sys.path}")
    sys.exit(1)


def main():
    """运行快速测试"""
    print("=" * 80)
    print("订单流策略 - 模拟数据测试")
    print("=" * 80)
    print()
    
    # 生成模拟数据
    print("1. 生成模拟数据...")
    print("   - 起始价格: $2000")
    print("   - 样本数量: 500")
    print("   - 时间间隔: 1秒")
    print("   - 波动率: 0.001")
    print()
    
    data = BacktestDataLoader.generate_mock_data(
        start_price=Decimal(2000),
        num_samples=500,
        interval_seconds=1.0,
        volatility=0.001
    )
    
    print(f"✅ 数据生成完成: {len(data.orderbooks)} 个订单簿快照, {len(data.trades)} 笔交易")
    print(f"   时间范围: {data.start_time:.0f} - {data.end_time:.0f}")
    print()
    
    # 创建策略配置
    print("2. 配置策略参数...")
    config = OrderFlowConfig(
        exchange='edgex',
        ticker='ETH',
        contract_id='ETH',
        orderbook_depth=20,
        imbalance_threshold=0.6,
        min_order_size=Decimal(10000),
        large_order_threshold=Decimal(50000),
        trade_flow_window=60,
        signal_strength_threshold=0.7,
        confirmation_ticks=3,
        position_size=Decimal(0.1),
        max_position=Decimal(1.0),
        stop_loss_pct=Decimal(0.02),
        take_profit_pct=Decimal(0.01),
        max_orders_per_minute=5,
        max_daily_loss=None,
        update_interval=0.5,
        enable_logging=False
    )
    print("✅ 策略配置完成")
    print()
    
    # 创建回测引擎
    print("3. 开始回测...")
    engine = BacktestEngine(config, initial_balance=Decimal(10000))
    result = engine.run(data)
    print()
    
    # 生成报告
    print("4. 生成回测报告...")
    report_text = BacktestReportGenerator.generate_text_report(result)
    print(report_text)
    
    # 保存报告
    output_dir = Path("backtest_results")
    output_dir.mkdir(exist_ok=True)
    report_file = output_dir / "test_report.txt"
    BacktestReportGenerator.generate_text_report(result, str(report_file))
    
    # 导出数据
    trades_file = output_dir / "test_trades.csv"
    equity_file = output_dir / "test_equity.csv"
    BacktestReportGenerator.export_trades_to_csv(result, str(trades_file))
    BacktestReportGenerator.export_equity_curve_to_csv(result, str(equity_file))
    
    print()
    print("=" * 80)
    print("测试完成！")
    print(f"报告已保存到: {report_file}")
    print(f"交易记录已保存到: {trades_file}")
    print(f"权益曲线已保存到: {equity_file}")
    print("=" * 80)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
