"""
回测引擎

模拟策略在历史数据上的执行
"""

import time
from decimal import Decimal
from typing import List, Optional, Dict
from dataclasses import dataclass

from ..shared.config import OrderFlowConfig
from ..shared.orderbook_analyzer import OrderBookAnalyzer
from ..shared.trade_flow_monitor import TradeFlowMonitor
from ..strategies.orderflow_strategy import OrderFlowStrategy, TradingSignal
from .backtest_data import BacktestData, HistoricalOrderBook, HistoricalTrade
from ..shared.performance_metrics import TradeRecord, PerformanceMetrics, PerformanceCalculator


@dataclass
class BacktestResult:
    """回测结果"""
    trades: List[TradeRecord]
    metrics: PerformanceMetrics
    equity_curve: List[float]
    signals_generated: int
    signals_executed: int
    initial_balance: Decimal
    final_balance: Decimal


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, config: OrderFlowConfig, initial_balance: Decimal = Decimal(10000)):
        """
        初始化回测引擎
        
        Args:
            config: 策略配置
            initial_balance: 初始资金
        """
        self.config = config
        self.initial_balance = initial_balance
        self.balance = initial_balance
        
        # 初始化分析器（不使用真实的交易所客户端）
        self.orderbook_analyzer = OrderBookAnalyzer(depth=config.orderbook_depth)
        self.trade_flow_monitor = TradeFlowMonitor(
            window_seconds=config.trade_flow_window,
            large_order_threshold=config.large_order_threshold
        )
        
        # 回测状态
        self.current_position = Decimal(0)
        self.position_entry_price = Decimal(0)
        self.position_entry_time = 0.0
        self.trades: List[TradeRecord] = []
        self.signals_generated = 0
        self.signals_executed = 0
        self.signal_buffer: List[TradingSignal] = []
        self.equity_curve: List[float] = [float(initial_balance)]
    
    def run(self, data: BacktestData) -> BacktestResult:
        """
        运行回测
        
        Args:
            data: 回测数据
        
        Returns:
            BacktestResult: 回测结果
        """
        print(f"开始回测: {len(data.orderbooks)} 个订单簿快照, {len(data.trades)} 笔交易")
        
        # 按时间顺序处理订单簿
        for i, orderbook in enumerate(data.orderbooks):
            # 更新订单簿
            bids = orderbook.bids
            asks = orderbook.asks
            snapshot = self.orderbook_analyzer.update_snapshot(bids, asks)
            
            # 更新交易流（添加该时间点附近的交易）
            nearby_trades = data.get_trades_in_range(
                orderbook.timestamp - self.config.trade_flow_window,
                orderbook.timestamp
            )
            for trade in nearby_trades:
                self.trade_flow_monitor.add_trade(
                    price=trade.price,
                    size=trade.size,
                    side=trade.side,
                    trade_id=trade.trade_id
                )
            
            # 生成信号
            signal = self._generate_signal(snapshot)
            
            if signal:
                self.signals_generated += 1
                
                # 确认信号
                if self._confirm_signal(signal):
                    # 执行信号
                    self._execute_signal(signal, orderbook.timestamp)
            
            # 更新持仓盈亏（标记到市场）
            self._update_position_mark_to_market(snapshot.mid_price, orderbook.timestamp)
            
            # 更新权益曲线
            current_equity = float(self.balance + self._calculate_position_value(snapshot.mid_price))
            self.equity_curve.append(current_equity)
            
            # 进度显示
            if (i + 1) % 100 == 0:
                progress = (i + 1) / len(data.orderbooks) * 100
                print(f"回测进度: {progress:.1f}% ({i+1}/{len(data.orderbooks)})")
        
        # 平仓所有持仓
        if self.current_position != 0:
            last_orderbook = data.orderbooks[-1]
            self._close_position(last_orderbook.mid_price, last_orderbook.timestamp)
        
        # 计算性能指标
        metrics = PerformanceCalculator.calculate_metrics(
            self.trades,
            self.initial_balance
        )
        
        return BacktestResult(
            trades=self.trades,
            metrics=metrics,
            equity_curve=self.equity_curve,
            signals_generated=self.signals_generated,
            signals_executed=self.signals_executed,
            initial_balance=self.initial_balance,
            final_balance=self.balance
        )
    
    def _generate_signal(self, snapshot) -> Optional[TradingSignal]:
        """生成交易信号（复用策略逻辑）"""
        if not snapshot:
            return None
        
        # 获取订单簿指标
        orderbook_metrics = self.orderbook_analyzer.get_orderbook_metrics(snapshot)
        imbalance = orderbook_metrics['imbalance']
        weighted_imbalance = orderbook_metrics['weighted_imbalance']
        
        # 获取交易流指标
        trade_flow_metrics = self.trade_flow_monitor.get_trade_flow_metrics()
        trade_imbalance = trade_flow_metrics['imbalance']
        momentum = trade_flow_metrics['momentum']
        
        # 信号强度计算（与策略逻辑相同）
        signal_strength = 0.0
        direction = None
        reasons = []
        
        # 订单簿失衡信号
        if abs(imbalance) > self.config.imbalance_threshold:
            if imbalance > 0:
                direction = 'buy'
                signal_strength += abs(imbalance) * 0.4
                reasons.append(f"订单簿买单占优 (失衡: {imbalance:.2%})")
            else:
                direction = 'sell'
                signal_strength += abs(imbalance) * 0.4
                reasons.append(f"订单簿卖单占优 (失衡: {imbalance:.2%})")
        
        # 加权失衡信号
        if abs(weighted_imbalance) > self.config.imbalance_threshold:
            if weighted_imbalance > 0 and direction != 'sell':
                direction = 'buy'
                signal_strength += abs(weighted_imbalance) * 0.3
                reasons.append(f"加权失衡偏向买入 ({weighted_imbalance:.2%})")
            elif weighted_imbalance < 0 and direction != 'buy':
                direction = 'sell'
                signal_strength += abs(weighted_imbalance) * 0.3
                reasons.append(f"加权失衡偏向卖出 ({weighted_imbalance:.2%})")
        
        # 交易流信号
        if abs(trade_imbalance) > 0.3:
            if trade_imbalance > 0 and direction != 'sell':
                direction = 'buy'
                signal_strength += abs(trade_imbalance) * 0.2
                reasons.append(f"交易流买入占优 ({trade_imbalance:.2%})")
            elif trade_imbalance < 0 and direction != 'buy':
                direction = 'sell'
                signal_strength += abs(trade_imbalance) * 0.2
                reasons.append(f"交易流卖出占优 ({trade_imbalance:.2%})")
        
        # 动量信号
        if abs(momentum) > 0.001:
            if momentum > 0 and direction != 'sell':
                direction = 'buy'
                signal_strength += min(abs(momentum) * 100, 0.1)
                reasons.append(f"价格上涨动量 ({momentum:.2%})")
            elif momentum < 0 and direction != 'buy':
                direction = 'sell'
                signal_strength += min(abs(momentum) * 100, 0.1)
                reasons.append(f"价格下跌动量 ({momentum:.2%})")
        
        # 检查信号强度
        if signal_strength < self.config.signal_strength_threshold or direction is None:
            return None
        
        # 确定入场价格
        if direction == 'buy':
            price = snapshot.best_ask
        else:
            price = snapshot.best_bid
        
        signal = TradingSignal(
            direction=direction,
            strength=min(signal_strength, 1.0),
            price=price,
            reason='; '.join(reasons),
            timestamp=time.time()
        )
        
        return signal
    
    def _confirm_signal(self, signal: TradingSignal) -> bool:
        """确认信号"""
        self.signal_buffer.append(signal)
        
        # 只保留最近的信号
        if len(self.signal_buffer) > self.config.confirmation_ticks * 2:
            self.signal_buffer = self.signal_buffer[-self.config.confirmation_ticks * 2:]
        
        # 检查是否有足够的一致信号
        if len(self.signal_buffer) < self.config.confirmation_ticks:
            return False
        
        recent_signals = self.signal_buffer[-self.config.confirmation_ticks:]
        
        # 检查方向是否一致
        directions = [s.direction for s in recent_signals]
        if len(set(directions)) != 1:
            return False
        
        # 检查信号强度是否足够
        avg_strength = sum(s.strength for s in recent_signals) / len(recent_signals)
        if avg_strength < self.config.signal_strength_threshold:
            return False
        
        return True
    
    def _execute_signal(self, signal: TradingSignal, timestamp: float):
        """执行交易信号"""
        # 检查持仓限制
        if signal.direction == 'buy' and self.current_position >= self.config.max_position:
            return
        
        if signal.direction == 'sell' and self.current_position <= -self.config.max_position:
            return
        
        # 如果有反向持仓，先平仓
        if (signal.direction == 'buy' and self.current_position < 0) or \
           (signal.direction == 'sell' and self.current_position > 0):
            self._close_position(signal.price, timestamp)
        
        # 开新仓
        trade_size = self.config.position_size
        trade_value = signal.price * trade_size
        
        # 检查资金是否足够
        if signal.direction == 'buy' and trade_value > self.balance:
            return  # 资金不足
        
        # 执行交易
        if signal.direction == 'buy':
            self.current_position += trade_size
            self.balance -= trade_value
        else:  # sell
            self.current_position -= trade_size
            self.balance += trade_value
        
        self.position_entry_price = signal.price
        self.position_entry_time = timestamp
        
        # 记录交易
        trade_record = TradeRecord(
            timestamp=timestamp,
            direction=signal.direction,
            price=signal.price,
            size=trade_size,
            pnl=Decimal(0)  # 开仓时盈亏为0
        )
        self.trades.append(trade_record)
        self.signals_executed += 1
    
    def _close_position(self, price: Decimal, timestamp: float):
        """平仓"""
        if self.current_position == 0:
            return
        
        trade_size = abs(self.current_position)
        trade_value = price * trade_size
        
        # 计算盈亏
        if self.current_position > 0:  # 平多
            pnl = (price - self.position_entry_price) * trade_size
            self.balance += trade_value
        else:  # 平空
            pnl = (self.position_entry_price - price) * trade_size
            self.balance += trade_value
        
        # 更新资金
        self.balance += pnl
        
        # 记录交易
        direction = 'sell' if self.current_position > 0 else 'buy'
        trade_record = TradeRecord(
            timestamp=timestamp,
            direction=direction,
            price=price,
            size=trade_size,
            pnl=pnl
        )
        self.trades.append(trade_record)
        
        # 重置持仓
        self.current_position = Decimal(0)
        self.position_entry_price = Decimal(0)
        self.position_entry_time = 0.0
    
    def _update_position_mark_to_market(self, current_price: Decimal, timestamp: float):
        """更新持仓的标记到市场价值（用于计算权益曲线）"""
        # 这个方法主要用于计算权益曲线，不实际执行交易
        pass
    
    def _calculate_position_value(self, current_price: Decimal) -> Decimal:
        """计算持仓的当前价值"""
        if self.current_position == 0:
            return Decimal(0)
        
        if self.current_position > 0:  # 多头
            return (current_price - self.position_entry_price) * self.current_position
        else:  # 空头
            return (self.position_entry_price - current_price) * abs(self.current_position)
