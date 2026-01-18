import json
import sys
from pathlib import Path

# 强制刷新输出
sys.stdout.reconfigure(encoding='utf-8') if hasattr(sys.stdout, 'reconfigure') else None

data_dir = Path('edgex_data')
files = sorted([f for f in data_dir.glob('edgex_continuous_*.json') if 'final' not in f.name])

if not files:
    print("No data files found")
    exit()

first_file = files[0]
last_file = files[-1]

with open(first_file, encoding='utf-8') as f:
    first_data = json.load(f)
with open(last_file, encoding='utf-8') as f:
    last_data = json.load(f)

eth_first = [r for r in first_data if r.get('contract_name') == 'ETHUSD'][0]
eth_last = [r for r in last_data if r.get('contract_name') == 'ETHUSD'][-1]

first_price = eth_first['mid_price']
last_price = eth_last['mid_price']
change = last_price - first_price
change_pct = (change / first_price) * 100

print("=" * 70)
print("价格变化分析")
print("=" * 70)
print(f"初始价格: ${first_price:.2f}")
print(f"最终价格: ${last_price:.2f}")
print(f"价格变化: ${change:.2f} ({change_pct:.2f}%)")
print()

# 基于之前的12个信号计算收益
initial_capital = 10000
position_size = 0.1
fee_rate = 0.0005

print("=" * 70)
print("策略收益估算（基于12个交易信号）")
print("=" * 70)
print(f"初始资金: ${initial_capital:,.2f}")
print(f"订单大小: {position_size}")
print(f"手续费率: {fee_rate * 100}%")
print(f"信号数量: 12 (1买入, 11卖出)")
print()

# 假设买入持有策略
buy_cost = first_price * position_size * (1 + fee_rate)
sell_revenue = last_price * position_size * (1 - fee_rate)
profit = sell_revenue - buy_cost
return_pct = (profit / buy_cost * 100) if buy_cost > 0 else 0

print("场景1: 买入持有策略")
print("-" * 70)
print(f"买入成本: ${buy_cost:.2f}")
print(f"卖出收入: ${sell_revenue:.2f}")
print(f"盈亏: ${profit:.2f}")
print(f"收益率: {return_pct:.2f}%")
print()

# 基于信号交易
signals = 12
avg_price = (first_price + last_price) / 2
price_volatility = abs(change) / len(files) if len(files) > 0 else 0

# 假设每次交易平均盈利为价格波动的30%
avg_profit_per_trade = price_volatility * position_size * 0.3
total_profit = avg_profit_per_trade * signals
total_fees = avg_price * position_size * fee_rate * signals * 2
net_profit = total_profit - total_fees
final_equity = initial_capital + net_profit
return_pct2 = (net_profit / initial_capital * 100) if initial_capital > 0 else 0

print("场景2: 基于12个信号交易")
print("-" * 70)
print(f"总交易次数: {signals}")
print(f"平均价格: ${avg_price:.2f}")
print(f"价格波动: ${price_volatility:.2f}")
print(f"平均每笔盈利: ${avg_profit_per_trade:.2f}")
print(f"总盈利: ${total_profit:.2f}")
print(f"总手续费: ${total_fees:.2f}")
print(f"净盈亏: ${net_profit:.2f}")
print(f"最终权益: ${final_equity:,.2f}")
print(f"总收益率: {return_pct2:.2f}%")
print()

# 时间跨度
time_span = eth_last['unix_time'] - eth_first['unix_time']
days = time_span / 86400
if days > 0:
    annual_return = return_pct2 * (365 / days)
    print(f"时间跨度: {days:.1f} 天")
    print(f"年化收益率: {annual_return:.2f}%")

print("=" * 70)
