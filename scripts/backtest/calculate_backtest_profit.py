"""
基于历史数据计算策略收益（简化版）
"""

import json
from pathlib import Path
from decimal import Decimal
from datetime import datetime

project_root = Path(__file__).parent
data_dir = project_root / "edgex_data"

# 加载历史数据
print("=" * 70)
print("EdgeX 策略收益计算")
print("=" * 70)

all_records = []
for file_path in sorted(data_dir.glob("edgex_continuous_*.json")):
    if "final" in file_path.name:
        continue
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            records = json.load(f)
            if isinstance(records, list):
                all_records.extend(records)
    except:
        pass

all_records.sort(key=lambda x: x.get('unix_time', 0))
eth_records = [r for r in all_records if r.get('contract_name') == 'ETHUSD']

print(f"[OK] 已加载 {len(eth_records)} 条ETH历史记录")
print(f"   时间范围: {datetime.fromtimestamp(eth_records[0]['unix_time'])} 至 {datetime.fromtimestamp(eth_records[-1]['unix_time'])}")
print()

# 计算价格变化
initial_price = eth_records[0].get('mid_price', 0)
final_price = eth_records[-1].get('mid_price', 0)
price_change = final_price - initial_price
price_change_pct = (price_change / initial_price * 100) if initial_price > 0 else 0

print("=" * 70)
print("价格分析")
print("=" * 70)
print(f"初始价格: ${initial_price:.2f}")
print(f"最终价格: ${final_price:.2f}")
print(f"价格变化: ${price_change:.2f} ({price_change_pct:.2f}%)")
print()

# 模拟策略收益（基于之前的12个信号）
# 假设每个信号都执行了交易
initial_capital = 10000
position_size = 0.1
fee_rate = 0.0005  # 0.05%

print("=" * 70)
print("策略收益估算")
print("=" * 70)
print(f"初始资金: ${initial_capital:,.2f}")
print(f"订单大小: {position_size}")
print(f"手续费率: {fee_rate * 100}%")
print()

# 基于之前的测试，生成了12个信号（1个买入，11个卖出）
# 假设我们按照信号执行交易
signals = 12
buy_signals = 1
sell_signals = 11

# 简化计算：假设买入后持有，然后在最终价格卖出
# 或者假设做多/做空策略

print("场景1: 买入持有策略")
print("-" * 70)
if initial_price > 0:
    # 买入
    buy_cost = initial_price * position_size * (1 + fee_rate)
    # 最终卖出
    sell_revenue = final_price * position_size * (1 - fee_rate)
    profit = sell_revenue - buy_cost
    return_pct = (profit / buy_cost * 100) if buy_cost > 0 else 0
    print(f"买入成本: ${buy_cost:.2f}")
    print(f"卖出收入: ${sell_revenue:.2f}")
    print(f"盈亏: ${profit:.2f}")
    print(f"收益率: {return_pct:.2f}%")
print()

print("场景2: 基于信号交易（假设12个信号全部执行）")
print("-" * 70)
# 假设每个信号都产生一次交易
# 简化：假设平均每次交易盈利/亏损基于价格波动
avg_price = sum(r.get('mid_price', 0) for r in eth_records) / len(eth_records) if eth_records else 0
price_volatility = sum(abs(eth_records[i+1].get('mid_price', 0) - eth_records[i].get('mid_price', 0)) 
                      for i in range(min(100, len(eth_records)-1))) / min(100, len(eth_records)-1) if len(eth_records) > 1 else 0

# 假设每次交易平均盈利为价格波动的50%
avg_profit_per_trade = price_volatility * position_size * 0.5
total_trades = signals
total_profit = avg_profit_per_trade * total_trades
total_fees = avg_price * position_size * fee_rate * total_trades * 2  # 买卖各一次
net_profit = total_profit - total_fees
final_equity = initial_capital + net_profit
return_pct = (net_profit / initial_capital * 100) if initial_capital > 0 else 0

print(f"总交易次数: {total_trades}")
print(f"平均价格波动: ${price_volatility:.2f}")
print(f"平均每笔盈利: ${avg_profit_per_trade:.2f}")
print(f"总盈利: ${total_profit:.2f}")
print(f"总手续费: ${total_fees:.2f}")
print(f"净盈亏: ${net_profit:.2f}")
print(f"最终权益: ${final_equity:,.2f}")
print(f"总收益率: {return_pct:.2f}%")

# 计算年化收益率
time_span = eth_records[-1]['unix_time'] - eth_records[0]['unix_time']
days = time_span / 86400
if days > 0:
    annual_return = return_pct * (365 / days)
    print(f"时间跨度: {days:.1f} 天")
    print(f"年化收益率: {annual_return:.2f}%")

print("=" * 70)
