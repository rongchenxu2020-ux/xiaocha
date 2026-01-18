"""
精确回测脚本：基于历史数据逐笔计算策略收益
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


class PreciseOrderFlowStrategy:
    """精确的订单流策略，用于回测"""
    
    def __init__(self, tick_size, position_size=Decimal('0.1'), imbalance_threshold=0.3):
        self.tick_size = tick_size
        self.position_size = position_size
        self.imbalance_threshold = imbalance_threshold
        
        # 价格历史（用于计算趋势和失衡）
        self.price_history = deque(maxlen=20)
        self.bid_history = deque(maxlen=20)
        self.ask_history = deque(maxlen=20)
        self.spread_history = deque(maxlen=20)
        
        # 当前市场数据
        self.best_bid = Decimal(0)
        self.best_ask = Decimal(0)
        self.mid_price = Decimal(0)
        self.spread = Decimal(0)
        
    def update_market_data(self, best_bid, best_ask, mid_price):
        """更新市场数据"""
        self.best_bid = Decimal(str(best_bid))
        self.best_ask = Decimal(str(best_ask))
        self.mid_price = Decimal(str(mid_price))
        self.spread = self.best_ask - self.best_bid
        
        self.price_history.append(self.mid_price)
        self.bid_history.append(self.best_bid)
        self.ask_history.append(self.best_ask)
        self.spread_history.append(self.spread)
    
    def calculate_imbalance(self):
        """计算订单簿失衡（基于价格趋势、价差和波动）"""
        if len(self.price_history) < 5:
            return 0.0
        
        # 1. 价格趋势（短期动量）
        recent_prices = list(self.price_history)[-5:]
        price_trend = float((recent_prices[-1] - recent_prices[0]) / Decimal(str(recent_prices[0]))) if recent_prices[0] > 0 else 0
        
        # 2. 价差变化（价差缩小可能表示失衡）
        if len(self.spread_history) >= 3:
            recent_spreads = list(self.spread_history)[-3:]
            spread_change = float((recent_spreads[0] - recent_spreads[-1]) / Decimal(str(recent_spreads[0]))) if recent_spreads[0] > 0 else 0
        else:
            spread_change = 0
        
        # 3. 价格波动率（波动大时可能失衡）
        price_volatility = 0.0
        if len(self.price_history) >= 3:
            price_changes = [abs(float((self.price_history[i] - self.price_history[i-1]) / self.price_history[i-1])) 
                           for i in range(1, len(self.price_history))]
            price_volatility = sum(price_changes[-5:]) / min(5, len(price_changes)) if price_changes else 0
        
        # 4. 买卖价差比例（价差小可能表示失衡）
        spread_pct = float(self.spread / self.mid_price) if self.mid_price > 0 else 0
        
        # 综合计算失衡
        # 价格上涨 + 价差缩小 + 波动增加 = 买盘失衡
        # 价格下跌 + 价差缩小 + 波动增加 = 卖盘失衡
        
        imbalance = 0.0
        
        # 趋势贡献（40%）
        if abs(price_trend) > 0.0001:  # 0.01%以上
            imbalance += price_trend * 0.4
        
        # 价差变化贡献（30%）
        if abs(spread_change) > 0.1:  # 价差变化超过10%
            imbalance += spread_change * 0.3
        
        # 波动率贡献（20%）
        if price_volatility > 0.0001:  # 有波动
            imbalance += (price_volatility * 10) * (1 if price_trend > 0 else -1) * 0.2
        
        # 价差比例贡献（10%）
        if spread_pct < 0.001:  # 价差很小（0.1%以下）
            # 价差很小时，根据趋势判断
            imbalance += (0.001 - spread_pct) * 100 * (1 if price_trend > 0 else -1) * 0.1
        
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
            
            # 确定执行价格（买入用ask，卖出用bid）
            if direction == 'buy':
                exec_price = self.best_ask
            else:
                exec_price = self.best_bid
            
            return {
                'direction': direction,
                'strength': strength,
                'imbalance': imbalance,
                'price': float(exec_price),
                'best_bid': float(self.best_bid),
                'best_ask': float(self.best_ask),
                'spread': float(self.spread)
            }
        
        return None


class PreciseBacktestEngine:
    """精确回测引擎"""
    
    def __init__(self, strategy, initial_capital=Decimal('10000'), fee_rate=Decimal('0.0005'),
                 stop_loss_pct=Decimal('0.02'), take_profit_pct=Decimal('0.01')):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.fee_rate = fee_rate  # 0.05% 手续费
        self.stop_loss_pct = stop_loss_pct  # 止损百分比（如2%）
        self.take_profit_pct = take_profit_pct  # 止盈百分比（如1%）
        
        # 账户状态
        self.cash = initial_capital
        self.position = Decimal(0)  # 持仓数量（正数=多头，负数=空头）
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
        self.total_fees = Decimal(0)
        
        # 止损止盈统计
        self.stop_loss_triggered = 0
        self.take_profit_triggered = 0
        
    def execute_trade(self, signal, current_price, timestamp):
        """执行交易（支持双向交易）"""
        direction = signal['direction']
        exec_price = Decimal(str(signal['price']))
        size = self.strategy.position_size
        
        # 计算手续费
        fee = exec_price * size * self.fee_rate
        
        if direction == 'buy':
            # 买入（开多或平空）
            cost = exec_price * size + fee
            
            if cost <= self.cash:
                self.cash -= cost
                self.total_fees += fee
                
                if self.position < 0:
                    # 平空头
                    closed_size = min(size, abs(self.position))
                    pnl = (self.avg_entry_price - exec_price) * closed_size - fee
                    self.total_profit += pnl
                    
                    if pnl > 0:
                        self.winning_trades += 1
                    else:
                        self.losing_trades += 1
                    
                    self.position += closed_size
                    
                    # 如果还有剩余，开多头
                    remaining = size - closed_size
                    if remaining > 0:
                        if self.position == 0:
                            self.avg_entry_price = exec_price
                        else:
                            total_cost = self.avg_entry_price * self.position + exec_price * remaining
                            self.avg_entry_price = total_cost / (self.position + remaining)
                        self.position += remaining
                else:
                    # 开多头
                    if self.position == 0:
                        self.avg_entry_price = exec_price
                    else:
                        total_cost = self.avg_entry_price * self.position + exec_price * size
                        self.avg_entry_price = total_cost / (self.position + size)
                    self.position += size
                
                trade = {
                    'timestamp': timestamp,
                    'type': 'BUY',
                    'price': float(exec_price),
                    'size': float(size),
                    'fee': float(fee),
                    'position_after': float(self.position),
                    'cash_after': float(self.cash),
                    'pnl': float(pnl) if self.position < 0 else None
                }
                self.trades.append(trade)
                self.total_trades += 1
                return True
        
        else:  # sell
            # 卖出（开空或平多）
            if self.position > 0:
                # 平多头
                closed_size = min(size, self.position)
                revenue = exec_price * closed_size - fee
                self.cash += revenue
                self.total_fees += fee
                
                pnl = (exec_price - self.avg_entry_price) * closed_size - fee
                self.total_profit += pnl
                
                if pnl > 0:
                    self.winning_trades += 1
                else:
                    self.losing_trades += 1
                
                self.position -= closed_size
                
                if self.position == 0:
                    self.avg_entry_price = Decimal(0)
                
                # 如果还有剩余，开空头
                remaining = size - closed_size
                if remaining > 0:
                    self.avg_entry_price = exec_price
                    self.position -= remaining
            else:
                # 开空头
                revenue = exec_price * size - fee
                self.cash += revenue
                self.total_fees += fee
                
                if self.position == 0:
                    self.avg_entry_price = exec_price
                else:
                    total_revenue = abs(self.avg_entry_price * self.position) + exec_price * size
                    self.avg_entry_price = total_revenue / (abs(self.position) + size)
                self.position -= size
            
            trade = {
                'timestamp': timestamp,
                'type': 'SELL',
                'price': float(exec_price),
                'size': float(size),
                'fee': float(fee),
                'position_after': float(self.position),
                'cash_after': float(self.cash),
                'pnl': float(pnl) if self.position > 0 else None
            }
            self.trades.append(trade)
            self.total_trades += 1
            return True
        
        return False
    
    def calculate_equity(self, current_price):
        """计算当前权益"""
        position_value = Decimal(str(current_price)) * self.position
        return self.cash + position_value
    
    def check_stop_loss_take_profit(self, current_price, timestamp):
        """检查是否需要止损或止盈，如果需要则自动平仓"""
        if self.position == 0 or self.avg_entry_price == 0:
            return False, None
        
        current_price_decimal = Decimal(str(current_price))
        price_change_pct = (current_price_decimal - self.avg_entry_price) / self.avg_entry_price
        
        should_close = False
        close_reason = ""
        
        if self.position > 0:  # 多头持仓
            # 止盈：价格上涨超过止盈百分比
            if price_change_pct >= self.take_profit_pct:
                should_close = True
                close_reason = "TAKE_PROFIT"
                self.take_profit_triggered += 1
            # 止损：价格下跌超过止损百分比
            elif price_change_pct <= -self.stop_loss_pct:
                should_close = True
                close_reason = "STOP_LOSS"
                self.stop_loss_triggered += 1
        
        elif self.position < 0:  # 空头持仓
            # 止盈：价格下跌超过止盈百分比（空头盈利）
            if price_change_pct <= -self.take_profit_pct:
                should_close = True
                close_reason = "TAKE_PROFIT"
                self.take_profit_triggered += 1
            # 止损：价格上涨超过止损百分比（空头亏损）
            elif price_change_pct >= self.stop_loss_pct:
                should_close = True
                close_reason = "STOP_LOSS"
                self.stop_loss_triggered += 1
        
        if should_close:
            # 强制平仓
            size = abs(self.position)
            fee = current_price_decimal * size * self.fee_rate
            
            if self.position > 0:  # 平多头
                revenue = current_price_decimal * size - fee
                self.cash += revenue
                pnl = (current_price_decimal - self.avg_entry_price) * size - fee
            else:  # 平空头
                cost = current_price_decimal * size + fee
                self.cash -= cost
                pnl = (self.avg_entry_price - current_price_decimal) * size - fee
            
            self.total_fees += fee
            self.total_profit += pnl
            
            if pnl > 0:
                self.winning_trades += 1
            else:
                self.losing_trades += 1
            
            # 记录交易
            trade = {
                'timestamp': timestamp,
                'type': 'SELL' if self.position > 0 else 'BUY',
                'price': float(current_price_decimal),
                'size': float(size),
                'fee': float(fee),
                'position_after': 0.0,
                'cash_after': float(self.cash),
                'pnl': float(pnl),
                'close_reason': close_reason,
                'entry_price': float(self.avg_entry_price)
            }
            self.trades.append(trade)
            self.total_trades += 1
            
            # 清空持仓
            self.position = Decimal(0)
            self.avg_entry_price = Decimal(0)
            
            return True, close_reason
        
        return False, None
    
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
        
        # 计算平均盈亏
        avg_win = 0
        avg_loss = 0
        if self.trades:
            pnls = [t.get('pnl', 0) for t in self.trades if t.get('pnl') is not None]
            if pnls:
                wins = [p for p in pnls if p > 0]
                losses = [p for p in pnls if p < 0]
                avg_win = sum(wins) / len(wins) if wins else 0
                avg_loss = sum(losses) / len(losses) if losses else 0
        
        # 计算夏普比率（简化版）
        if len(self.equity_curve) > 1:
            returns = [(self.equity_curve[i]['equity'] - self.equity_curve[i-1]['equity']) / self.equity_curve[i-1]['equity']
                      for i in range(1, len(self.equity_curve))]
            if returns:
                avg_return = sum(returns) / len(returns)
                variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
                std_dev = variance ** 0.5
                sharpe_ratio = (avg_return / std_dev * (252 ** 0.5)) if std_dev > 0 else 0  # 年化夏普
            else:
                sharpe_ratio = 0
        else:
            sharpe_ratio = 0
        
        return {
            'initial_capital': float(self.initial_capital),
            'final_equity': float(final_equity),
            'total_return_pct': float(total_return),
            'total_profit': float(self.total_profit),
            'total_fees': float(self.total_fees),
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate_pct': float(win_rate),
            'avg_win': float(avg_win),
            'avg_loss': float(avg_loss),
            'profit_factor': float(abs(avg_win / avg_loss)) if avg_loss != 0 else 0,
            'max_drawdown_pct': float(self.max_drawdown * 100),
            'sharpe_ratio': float(sharpe_ratio),
            'final_position': float(self.position),
            'final_cash': float(self.cash),
            'stop_loss_triggered': self.stop_loss_triggered,
            'take_profit_triggered': self.take_profit_triggered
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


def run_precise_backtest():
    """运行精确回测"""
    
    print("=" * 70)
    print("EdgeX 策略精确回测")
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
    
    # 初始化策略（优化参数以减少交易频率）
    strategy = PreciseOrderFlowStrategy(
        tick_size=Decimal('0.01'),
        position_size=Decimal('0.1'),
        imbalance_threshold=0.35  # 提高阈值以减少交易频率（从0.2提高到0.35）
    )
    
    # 初始化回测引擎（添加止损止盈）
    initial_capital = Decimal('10000')  # 初始资金 $10,000
    backtest = PreciseBacktestEngine(
        strategy=strategy,
        initial_capital=initial_capital,
        fee_rate=Decimal('0.0005'),  # 0.05% 手续费
        stop_loss_pct=Decimal('0.01'),  # 1% 止损（更严格）
        take_profit_pct=Decimal('0.02')  # 2% 止盈（更高目标）
    )
    
    print(f"[INIT] 回测参数（优化版 + 止损止盈）:")
    print(f"   初始资金: ${initial_capital}")
    print(f"   订单大小: {strategy.position_size}")
    print(f"   失衡阈值: {strategy.imbalance_threshold} (已提高，减少交易频率)")
    print(f"   手续费率: {backtest.fee_rate * 100}%")
    print(f"   止损: {backtest.stop_loss_pct * 100}%")
    print(f"   止盈: {backtest.take_profit_pct * 100}%")
    print()
    
    print("=" * 70)
    print("开始精确回测（优化参数）...")
    print("=" * 70)
    print("正在处理数据，请稍候...")
    print()
    
    # 回测参数（优化：增加检查间隔和最小交易间隔）
    signal_check_interval = 10  # 每10秒检查一次信号（从3秒增加到10秒）
    min_trade_interval = 30  # 最小交易间隔30秒（从5秒增加到30秒）
    
    last_signal_time = 0
    last_trade_time = 0
    
    # 处理历史数据
    processed = 0
    for i, record in enumerate(historical_records):
        timestamp = record.get('unix_time', 0)
        best_bid = record.get('best_bid', 0)
        best_ask = record.get('best_ask', 0)
        mid_price = record.get('mid_price', 0)
        
        if best_bid <= 0 or best_ask <= 0 or mid_price <= 0:
            continue
        
        processed += 1
        
        # 更新策略市场数据
        strategy.update_market_data(best_bid, best_ask, mid_price)
        
        # 检查止损止盈（在更新权益曲线之前）
        stop_triggered, stop_reason = backtest.check_stop_loss_take_profit(mid_price, timestamp)
        if stop_triggered:
            equity = backtest.calculate_equity(mid_price)
            return_pct = (equity - initial_capital) / initial_capital * 100
            trade = backtest.trades[-1]
            print(f"[{stop_reason}] 自动平仓 @ ${mid_price:.2f} | "
                  f"入场价: ${trade.get('entry_price', 0):.2f} | "
                  f"PnL: ${trade.get('pnl', 0):+.2f} | "
                  f"权益: ${equity:.2f} ({return_pct:+.2f}%)")
        
        # 更新权益曲线
        backtest.update_equity_curve(mid_price, timestamp)
        
        # 检查交易信号
        time_since_last_signal = timestamp - last_signal_time if last_signal_time > 0 else float('inf')
        
        if time_since_last_signal >= signal_check_interval:
            signal = strategy.generate_signal()
            
            if signal and signal['strength'] >= 0.7:  # 提高信号强度要求（从0.5提高到0.7）
                time_since_last_trade = timestamp - last_trade_time if last_trade_time > 0 else float('inf')
                
                if time_since_last_trade >= min_trade_interval:
                    # 执行交易
                    if backtest.execute_trade(signal, mid_price, timestamp):
                        last_trade_time = timestamp
                        last_signal_time = timestamp
                        
                        # 显示交易信息
                        equity = backtest.calculate_equity(mid_price)
                        return_pct = (equity - initial_capital) / initial_capital * 100
                        trade = backtest.trades[-1]
                        pnl_str = f" | PnL: ${trade.get('pnl', 0):.2f}" if trade.get('pnl') is not None else ""
                        print(f"[TRADE #{backtest.total_trades}] {signal['direction'].upper()} @ ${signal['price']:.2f} "
                              f"| 权益: ${equity:.2f} ({return_pct:+.2f}%){pnl_str}")
        
        # 每处理5000个点显示一次进度
        if processed % 5000 == 0:
            equity = backtest.calculate_equity(mid_price)
            return_pct = (equity - initial_capital) / initial_capital * 100
            print(f"[PROGRESS] 已处理 {processed}/{len(historical_records)} 个数据点 | "
                  f"交易数: {backtest.total_trades} | 当前权益: ${equity:.2f} | 收益率: {return_pct:+.2f}%")
    
    # 计算最终统计
    final_price = historical_records[-1].get('mid_price', 0)
    stats = backtest.get_statistics(final_price)
    
    print("\n" + "=" * 70)
    print("精确回测结果")
    print("=" * 70)
    print(f"初始资金: ${stats['initial_capital']:,.2f}")
    print(f"最终权益: ${stats['final_equity']:,.2f}")
    print(f"总收益率: {stats['total_return_pct']:+.2f}%")
    print(f"总盈亏: ${stats['total_profit']:+,.2f}")
    print(f"总手续费: ${stats['total_fees']:,.2f}")
    print()
    print(f"交易统计:")
    print(f"   总交易次数: {stats['total_trades']}")
    print(f"   盈利交易: {stats['winning_trades']}")
    print(f"   亏损交易: {stats['losing_trades']}")
    print(f"   胜率: {stats['win_rate_pct']:.2f}%")
    if stats['avg_win'] > 0:
        print(f"   平均盈利: ${stats['avg_win']:.2f}")
    if stats['avg_loss'] < 0:
        print(f"   平均亏损: ${stats['avg_loss']:.2f}")
    if stats['profit_factor'] > 0:
        print(f"   盈亏比: {stats['profit_factor']:.2f}")
    print()
    print(f"风险指标:")
    print(f"   最大回撤: {stats['max_drawdown_pct']:.2f}%")
    if stats['sharpe_ratio'] != 0:
        print(f"   夏普比率: {stats['sharpe_ratio']:.2f}")
    print()
    print(f"止损止盈统计:")
    print(f"   止损触发: {stats['stop_loss_triggered']} 次")
    print(f"   止盈触发: {stats['take_profit_triggered']} 次")
    print()
    print(f"最终状态:")
    print(f"   持仓数量: {stats['final_position']:+.4f}")
    print(f"   现金余额: ${stats['final_cash']:,.2f}")
    print()
    
    # 计算年化收益率
    time_span = historical_records[-1]['unix_time'] - historical_records[0]['unix_time']
    days = time_span / 86400
    if days > 0:
        annual_return = stats['total_return_pct'] * (365 / days)
        print(f"时间跨度: {days:.1f} 天")
        print(f"年化收益率: {annual_return:+.2f}%")
    
    # 显示最近10笔交易
    if backtest.trades:
        print("\n" + "=" * 70)
        print("最近10笔交易")
        print("=" * 70)
        for trade in backtest.trades[-10:]:
            pnl_str = f" | PnL: ${trade.get('pnl', 0):+.2f}" if trade.get('pnl') is not None else ""
            print(f"{trade['type']} @ ${trade['price']:.2f} | 持仓: {trade['position_after']:+.4f} | "
                  f"现金: ${trade['cash_after']:.2f}{pnl_str}")
    
    # 按日期统计盈亏
    if backtest.trades:
        print("\n" + "=" * 70)
        print("单日盈亏统计")
        print("=" * 70)
        
        from collections import defaultdict
        daily_stats = defaultdict(lambda: {'trades': 0, 'pnl': 0, 'fees': 0, 'winning': 0, 'losing': 0})
        
        for trade in backtest.trades:
            trade_date = datetime.fromtimestamp(trade['timestamp']).strftime('%Y-%m-%d')
            daily_stats[trade_date]['trades'] += 1
            daily_stats[trade_date]['fees'] += trade.get('fee', 0)
            
            if trade.get('pnl') is not None:
                daily_stats[trade_date]['pnl'] += trade['pnl']
                if trade['pnl'] > 0:
                    daily_stats[trade_date]['winning'] += 1
                else:
                    daily_stats[trade_date]['losing'] += 1
        
        # 按日期排序
        sorted_dates = sorted(daily_stats.keys())
        
        print(f"{'日期':<12} {'交易数':<8} {'盈利':<8} {'亏损':<8} {'盈亏':<12} {'手续费':<10} {'胜率':<8}")
        print("-" * 70)
        
        total_daily_pnl = 0
        for date in sorted_dates:
            stats = daily_stats[date]
            total_trades = stats['trades']
            winning = stats['winning']
            losing = stats['losing']
            pnl = stats['pnl']
            fees = stats['fees']
            win_rate = (winning / (winning + losing) * 100) if (winning + losing) > 0 else 0
            
            total_daily_pnl += pnl
            
            pnl_str = f"${pnl:+,.2f}" if pnl != 0 else "$0.00"
            print(f"{date:<12} {total_trades:<8} {winning:<8} {losing:<8} {pnl_str:<12} ${fees:.2f:<9} {win_rate:.1f}%")
        
        print("-" * 70)
        print(f"{'总计':<12} {sum(s['trades'] for s in daily_stats.values()):<8} "
              f"{sum(s['winning'] for s in daily_stats.values()):<8} "
              f"{sum(s['losing'] for s in daily_stats.values()):<8} "
              f"${total_daily_pnl:+,.2f:<11} "
              f"${sum(s['fees'] for s in daily_stats.values()):.2f:<9}")
        
        print("\n" + "=" * 70)
    
    print("=" * 70)


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("EdgeX 策略精确回测工具")
    print("=" * 70)
    print("此工具将使用历史数据精确回测策略收益")
    print("支持双向交易（做多做空）")
    print("=" * 70)
    print()
    
    try:
        run_precise_backtest()
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断，正在退出...")
    except Exception as e:
        print(f"\n[ERROR] 程序异常: {e}")
        import traceback
        traceback.print_exc()
