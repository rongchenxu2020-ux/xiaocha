#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断为什么没有生成交易信号
"""

import sys
import json
from pathlib import Path
from decimal import Decimal

sys.path.insert(0, str(Path(__file__).parent))

from booking.backtest_data import BacktestDataLoader
from booking.config import OrderFlowConfig
from booking.backtest_engine import BacktestEngine
from booking.orderbook_analyzer import OrderBookSnapshot

# 查找最新的测试数据
backtest_dir = Path(__file__).parent / "backtest_results"
data_files = list(backtest_dir.glob("*_edgex_ETH_*.json"))

if not data_files:
    print("未找到测试数据文件")
    sys.exit(1)

# 使用最新的数据文件
latest_data_file = max(data_files, key=lambda p: p.stat().st_mtime)
print(f"分析数据文件: {latest_data_file.name}")
print("=" * 80)

# 加载数据
loader = BacktestDataLoader()
data = loader.load_from_json(str(latest_data_file))

print(f"\n数据统计:")
print(f"  - 订单簿快照数: {len(data.orderbooks)}")
print(f"  - 交易记录数: {len(data.trades)}")
print(f"  - 时间范围: {data.orderbooks[0].timestamp if data.orderbooks else 'N/A'} - {data.orderbooks[-1].timestamp if data.orderbooks else 'N/A'}")

# 检查订单簿数据质量
print(f"\n订单簿数据质量检查:")
if data.orderbooks:
    sample = data.orderbooks[0]
    print(f"  - 买单层级数: {len(sample.bids)}")
    print(f"  - 卖单层级数: {len(sample.asks)}")
    print(f"  - 最佳买价: ${sample.best_bid}")
    print(f"  - 最佳卖价: ${sample.best_ask}")
    print(f"  - 中间价: ${sample.mid_price}")
    
    # 检查是否有深度数据
    total_bid_volume = sum(vol for _, vol in sample.bids)
    total_ask_volume = sum(vol for _, vol in sample.asks)
    print(f"  - 买单总深度: {total_bid_volume}")
    print(f"  - 卖单总深度: {total_ask_volume}")
    
    if len(sample.bids) <= 1 and len(sample.asks) <= 1:
        print(f"\n  ⚠️  警告: 订单簿数据只有最佳买卖价，缺少深度数据！")
        print(f"     这会导致无法准确计算订单簿失衡指标。")

# 检查交易流数据
print(f"\n交易流数据检查:")
if len(data.trades) == 0:
    print(f"  ⚠️  警告: 没有交易流数据！")
    print(f"     这会导致无法计算交易流失衡和动量指标。")
    print(f"     策略需要交易流数据来生成完整的信号。")
else:
    print(f"  - 交易记录数: {len(data.trades)}")
    sample_trade = data.trades[0]
    print(f"  - 示例交易: 价格=${sample_trade.price}, 数量={sample_trade.size}, 方向={sample_trade.side}")

# 模拟信号生成过程
print(f"\n" + "=" * 80)
print("模拟信号生成过程（使用默认配置）:")
print("=" * 80)

config = OrderFlowConfig(
    exchange='edgex',
    ticker='ETH',
    contract_id='10000002',
    imbalance_threshold=0.6,  # 60%失衡
    signal_strength_threshold=0.7,  # 70%信号强度
    confirmation_ticks=3,  # 需要3个连续tick确认
)

print(f"\n配置参数:")
print(f"  - 失衡阈值: {config.imbalance_threshold} (60%)")
print(f"  - 信号强度阈值: {config.signal_strength_threshold} (70%)")
print(f"  - 确认tick数: {config.confirmation_ticks}")

# 分析前几个订单簿快照
print(f"\n分析前5个订单簿快照:")
from booking.orderbook_analyzer import OrderBookAnalyzer

analyzer = OrderBookAnalyzer(depth=config.orderbook_depth)

for i, orderbook in enumerate(data.orderbooks[:5]):
    print(f"\n  快照 {i+1}:")
    metrics = analyzer.get_orderbook_metrics(orderbook)
    
    imbalance = metrics['imbalance']
    weighted_imbalance = metrics['weighted_imbalance']
    
    print(f"    - 失衡: {imbalance:.2%} (阈值: {config.imbalance_threshold*100:.0f}%)")
    print(f"    - 加权失衡: {weighted_imbalance:.2%}")
    print(f"    - 最佳买价: ${orderbook.best_bid}")
    print(f"    - 最佳卖价: ${orderbook.best_ask}")
    
    # 检查是否满足信号条件
    if abs(imbalance) > config.imbalance_threshold:
        print(f"    ✅ 失衡超过阈值！")
    else:
        print(f"    ❌ 失衡未超过阈值")
    
    # 计算信号强度（简化版）
    signal_strength = 0.0
    if abs(imbalance) > config.imbalance_threshold:
        signal_strength += abs(imbalance) * 0.4
    if abs(weighted_imbalance) > config.imbalance_threshold:
        signal_strength += abs(weighted_imbalance) * 0.3
    
    print(f"    - 信号强度: {signal_strength:.2%} (阈值: {config.signal_strength_threshold*100:.0f}%)")
    
    if signal_strength >= config.signal_strength_threshold:
        print(f"    ✅ 信号强度足够！")
    else:
        print(f"    ❌ 信号强度不足")

# 总结问题
print(f"\n" + "=" * 80)
print("问题诊断总结:")
print("=" * 80)

issues = []

if len(data.orderbooks) < config.confirmation_ticks:
    issues.append(f"数据量不足: 只有{len(data.orderbooks)}个快照，但需要至少{config.confirmation_ticks}个tick来确认信号")

if len(data.orderbooks) > 0 and len(data.orderbooks[0].bids) <= 1:
    issues.append("订单簿数据缺少深度: 只有最佳买卖价，无法准确计算失衡指标")

if len(data.trades) == 0:
    issues.append("缺少交易流数据: 无法计算交易流失衡和动量，这些是信号生成的重要组成部分")

if issues:
    print("\n发现的问题:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
    
    print("\n建议解决方案:")
    print("  1. 增加数据收集时长（至少60秒以上）")
    print("  2. 收集完整的订单簿深度数据（不只是最佳买卖价）")
    print("  3. 收集交易流数据（实际成交记录）")
    print("  4. 降低策略参数阈值进行测试:")
    print("     - imbalance_threshold: 0.6 -> 0.3")
    print("     - signal_strength_threshold: 0.7 -> 0.5")
    print("     - confirmation_ticks: 3 -> 2")
else:
    print("\n未发现明显问题，可能需要调整策略参数或收集更多数据。")

print("\n" + "=" * 80)
