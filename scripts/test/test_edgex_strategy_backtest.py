"""
回测脚本：使用历史数据计算策略收益
"""

import os
import sys
import json
import time
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from collections import deque
import dotenv

# 设置输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 加载.env文件
project_root = Path(__file__).parent
env_file = project_root / ".env"
if env_file.exists():
    dotenv.load_dotenv(env_file)


class SimpleOrderFlowStrategy:
    """简化的订单流策略，用于回测"""
    
    def __init__(self, tick_size, position_size=Decimal('0.1'), imbalance_threshold=0.3):
        self.tick_size = tick_size
        self.position_size = position_size
        self.imbalance_threshold = imbalance_threshold
        
        # 订单簿数据（模拟）
        self.bid_volume = Decimal(0)
        self.ask_volume = Decimal(0)
        self.best_bid = Decimal(0)
        self.best_ask = Decimal(0)
        
        # 价格历史（用于计算失衡）
        self.price_history = deque(maxlen=10)
        
    def update_market_data(self, best_bid, best_ask, mid_price):
        """更新市场数据"""
        self.best_bid = Decimal(str(best_bid))
        self.best_ask = Decimal(str(best_ask))
        self.price_history.append(Decimal(str(mid_price)))
        
        # 模拟订单簿失衡（基于价格变化趋势和价差）
        spread = self.best_ask - self.best_bid
        spread_pct = float(spread / self.best_bid) if self.best_bid > 0 else 0
        
        if len(self.price_history) >= 3:
            recent_prices = list(self.price_history)[-3:]
            price_trend = float((recent_prices[-1] - recent_prices[0]) / recent_prices[0])
            
            # 基于价格趋势和价差计算失衡
            # 如果价格上涨且价差较小，买盘更强
            if price_trend > 0.00005:  # 0.005%以上
                imbalance_factor = abs(price_trend) * 20 + (0.01 - min(spread_pct, 0.01)) * 5
                self.bid_volume = Decimal('1000') * Decimal(str(1 + imbalance_factor))
                self.ask_volume = Decimal('1000')
            elif price_trend < -0.00005:  # 下跌
                imbalance_factor = abs(price_trend) * 20 + (0.01 - min(spread_pct, 0.01)) * 5
                self.ask_volume = Decimal('1000') * Decimal(str(1 + imbalance_factor))
                self.bid_volume = Decimal('1000')
            else:
                # 基于价差判断
                if spread_pct < 0.005:  # 价差很小，可能失衡
                    self.bid_volume = Decimal('1200')
                    self.ask_volume = Decimal('800')
                else:
                    self.bid_volume = Decimal('1000')
                    self.ask_volume = Decimal('1000')
        else:
            # 基于价差判断
            if spread_pct < 0.005:
                self.bid_volume = Decimal('1200')
                self.ask_volume = Decimal('800')
            else:
                self.bid_volume = Decimal('1000')
                self.ask_volume = Decimal('1000')
    
    def calculate_imbalance(self):
        """计算订单簿失衡"""
        total_volume = self.bid_volume + self.ask_volume
        if total_volume == 0:
            return 0.0
        
        imbalance = float((self.bid_volume - self.ask_volume) / total_volume)
        return imbalance
    
    def generate_signal(self):
        """生成交易信号"""
        if self.best_bid <= 0 or self.best_ask <= 0:
            return None
        
        imbalance = self.calculate_imbalance()
        
        # 如果失衡超过阈值，生成信号
        if abs(imbalance) > self.imbalance_threshold:
            direction = 'buy' if imbalance > 0 else 'sell'
            strength = min(abs(imbalance) / self.imbalance_threshold, 1.0)
            
            return {
                'direction': direction,
                'strength': strength,
                'imbalance': imbalance,
                'price': float(self.best_ask if direction == 'buy' else self.best_bid)
            }
        
        return None


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, strategy, initial_capital=Decimal('10000'), fee_rate=Decimal('0.0005')):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate  # 0.05% 手续费
        
        # 账户状态
        self.cash = initial_capital
        self.position = Decimal(0)  # 持仓数量
        self.avg_entry_price = Decimal(0)  # 平均入场价格
        
        # 交易记录
        self.trades = []
        self.equity_curve = []
        
        # 统计
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_profit = Decimal(0)
        self.max_drawdown = Decimal(0)
        self.peak_equity = initial_capital
        
    def execute_trade(self, signal, current_price, timestamp):
        """执行交易"""
        direction = signal['direction']
        price = Decimal(str(signal['price']))
        size = self.strategy.position_size
        
        # 计算手续费
        fee = price * size * self.fee_rate
        
        if direction == 'buy':
            # 买入
            cost = price * size + fee
            
            if cost <= self.cash:
                self.cash -= cost
                
                # 更新平均入场价格
                if self.position == 0:
                    self.avg_entry_price = price
                else:
                    total_cost = self.avg_entry_price * self.position + cost
                    self.avg_entry_price = total_cost / (self.position + size)
                
                self.position += size
                
                trade = {
                    'timestamp': timestamp,
                    'type': 'BUY',
                    'price': float(price),
                    'size': float(size),
                    'fee': float(fee),
                    'position_after': float(self.position),
                    'cash_after': float(self.cash)
                }
                self.trades.append(trade)
                self.total_trades += 1
                return True
        
        else:  # sell
            # 卖出
            if self.position >= size:
                revenue = price * size - fee
                self.cash += revenue
                
                # 计算盈亏
                pnl = (price - self.avg_entry_price) * size - fee
                self.total_profit += pnl
                
                if pnl > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1
                
                self.position -= size
                
                if self.position == 0:
                    self.avg_entry_price = Decimal(0)
                
                trade = {
                    'timestamp': timestamp,
                    'type': 'SELL',
                    'price': float(price),
                    'size': float(size),
                    'fee': float(fee),
                    'pnl': float(pnl),
                    'position_after': float(self.position),
                    'cash_after': float(self.cash)
                }
                self.trades.append(trade)
                self.total_trades += 1
                return True
        
        return False
    
    def calculate_equity(self, current_price):
        """计算当前权益"""
        position_value = Decimal(str(current_price)) * self.position
        return self.cash + position_value
    
    def update_equity_curve(self, current_price, timestamp):
        """更新权益曲线"""
        equity = self.calculate_equity(current_price)
        self.equity_curve.append({
            'timestamp': timestamp,
            'equity': float(equity),
            'cash': float(self.cash),
            'position': float(self.position),
            'position_value': float(Decimal(str(current_price)) * self.position)
        })
        
        # 更新最大回撤
        if equity > self.peak_equity:
            self.peak_equity = equity
        
        drawdown = (self.peak_equity - equity) / self.peak_equity
        if drawdown > self.max_drawdown:
            self.max_drawdown = drawdown
    
    def get_statistics(self, final_price):
        """获取回测统计"""
        final_equity = self.calculate_equity(final_price)
        total_return = (final_equity - self.initial_capital) / self.initial_capital * 100
        
        win_rate = (self.winning_trades / self.total_trades * 100) if self.total_trades > 0 else 0
        
        return {
            'initial_capital': float(self.initial_capital),
            'final_equity': float(final_equity),
            'total_return_pct': float(total_return),
            'total_profit': float(self.total_profit),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate_pct': float(win_rate),
            'max_drawdown_pct': float(self.max_drawdown * 100),
            'final_position': float(self.position),
            'final_cash': float(self.cash)
        }


def load_historical_data(data_dir):
    """加载历史数据文件"""
    data_dir = Path(data_dir)
    if not data_dir.exists():
        return []
    
    all_records = []
    
    # 读取所有非final文件
    for file_path in sorted(data_dir.glob("edgex_continuous_*.json")):
        if "final" in file_path.name:
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
                if isinstance(records, list):
                    all_records.extend(records)
        except Exception as e:
            print(f"[WARNING] 读取文件失败 {file_path.name}: {e}")
    
    # 按时间排序
    all_records.sort(key=lambda x: x.get('unix_time', 0))
    
    # 只保留ETH数据
    eth_records = [r for r in all_records if r.get('contract_name') == 'ETHUSD']
    
    return eth_records


def run_backtest():
    """运行回测"""
    
    print("=" * 70)
    print("EdgeX 策略回测")
    print("=" * 70)
    
    # 加载历史数据
    data_dir = project_root / "edgex_data"
    print(f"[LOAD] 正在加载历史数据...")
    historical_records = load_historical_data(data_dir)
    
    if not historical_records:
        print("[ERROR] 未找到历史数据文件")
        return
    
    print(f"[OK] 已加载 {len(historical_records)} 条历史记录")
    print(f"   时间范围: {datetime.fromtimestamp(historical_records[0]['unix_time'])} 至 {datetime.fromtimestamp(historical_records[-1]['unix_time'])}")
    print()
    
    # 初始化策略（降低阈值以产生更多信号）
    strategy = SimpleOrderFlowStrategy(
        tick_size=Decimal('0.01'),
        position_size=Decimal('0.1'),
        imbalance_threshold=0.15  # 降低阈值以产生更多交易
    )
    
    # 初始化回测引擎
    initial_capital = Decimal('10000')  # 初始资金 $10,000
    backtest = BacktestEngine(
        strategy=strategy,
        initial_capital=initial_capital,
        fee_rate=Decimal('0.0005')  # 0.05% 手续费
    )
    
    print(f"[INIT] 回测参数:")
    print(f"   初始资金: ${initial_capital}")
    print(f"   订单大小: {strategy.position_size}")
    print(f"   失衡阈值: {strategy.imbalance_threshold}")
    print(f"   手续费率: {backtest.fee_rate * 100}%")
    print()
    
    print("=" * 70)
    print("开始回测...")
    print("=" * 70)
    
    # 回测参数
    signal_check_interval = 5  # 每5秒检查一次信号
    min_trade_interval = 10  # 最小交易间隔10秒
    
    last_signal_time = 0
    last_trade_time = 0
    
    # 处理历史数据（采样处理以提高速度）
    sample_interval = max(1, len(historical_records) // 10000)  # 最多处理10000个点
    print(f"[INFO] 采样处理: 每 {sample_interval} 个点处理一次\n")
    
    processed_count = 0
    for i in range(0, len(historical_records), sample_interval):
        record = historical_records[i]
        timestamp = record.get('unix_time', 0)
        best_bid = record.get('best_bid', 0)
        best_ask = record.get('best_ask', 0)
        mid_price = record.get('mid_price', 0)
        
        if best_bid <= 0 or best_ask <= 0 or mid_price <= 0:
            continue
        
        processed_count += 1
        
        # 更新策略市场数据
        strategy.update_market_data(best_bid, best_ask, mid_price)
        
        # 更新权益曲线
        backtest.update_equity_curve(mid_price, timestamp)
        
        # 检查交易信号
        time_since_last_signal = timestamp - last_signal_time if last_signal_time > 0 else float('inf')
        
        if time_since_last_signal >= signal_check_interval:
            signal = strategy.generate_signal()
            
            if signal and signal['strength'] >= 0.5:  # 降低信号强度要求
                time_since_last_trade = timestamp - last_trade_time if last_trade_time > 0 else float('inf')
                
                if time_since_last_trade >= min_trade_interval:
                    # 执行交易
                    if backtest.execute_trade(signal, mid_price, timestamp):
                        last_trade_time = timestamp
                        last_signal_time = timestamp
                        
                        equity = backtest.calculate_equity(mid_price)
                        return_pct = (equity - initial_capital) / initial_capital * 100
                        print(f"[TRADE #{backtest.total_trades}] {signal['direction'].upper()} @ ${signal['price']:.2f} | "
                              f"权益: ${equity:.2f} | 收益率: {return_pct:.2f}%")
        
        # 每处理1000个点显示一次进度
        if processed_count % 1000 == 0:
            equity = backtest.calculate_equity(mid_price)
            return_pct = (equity - initial_capital) / initial_capital * 100
            print(f"[PROGRESS] 已处理 {processed_count}/{len(historical_records)//sample_interval} 个数据点 | "
                  f"交易数: {backtest.total_trades} | 当前权益: ${equity:.2f} | 收益率: {return_pct:.2f}%")
    
    # 计算最终统计
    final_price = historical_records[-1].get('mid_price', 0)
    stats = backtest.get_statistics(final_price)
    
    print("\n" + "=" * 70)
    print("回测结果")
    print("=" * 70)
    print(f"初始资金: ${stats['initial_capital']:,.2f}")
    print(f"最终权益: ${stats['final_equity']:,.2f}")
    print(f"总收益率: {stats['total_return_pct']:.2f}%")
    print(f"总盈亏: ${stats['total_profit']:,.2f}")
    print()
    print(f"交易统计:")
    print(f"   总交易次数: {stats['total_trades']}")
    print(f"   盈利交易: {stats['winning_trades']}")
    print(f"   亏损交易: {stats['losing_trades']}")
    print(f"   胜率: {stats['win_rate_pct']:.2f}%")
    print()
    print(f"风险指标:")
    print(f"   最大回撤: {stats['max_drawdown_pct']:.2f}%")
    print()
    print(f"最终状态:")
    print(f"   持仓数量: {stats['final_position']:.4f}")
    print(f"   现金余额: ${stats['final_cash']:,.2f}")
    print()
    
    # 计算年化收益率
    time_span = historical_records[-1]['unix_time'] - historical_records[0]['unix_time']
    days = time_span / 86400
    if days > 0:
        annual_return = stats['total_return_pct'] * (365 / days)
        print(f"时间跨度: {days:.1f} 天")
        print(f"年化收益率: {annual_return:.2f}%")
    
    print("=" * 70)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("EdgeX 策略回测工具")
    print("=" * 70)
    print("此工具将使用历史数据回测策略收益")
    print("=" * 70)
    print()
    
    try:
        run_backtest()
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断，正在退出...")
    except Exception as e:
        print(f"\n[ERROR] 程序异常: {e}")
        import traceback
        traceback.print_exc()
