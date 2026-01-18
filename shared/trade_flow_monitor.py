"""
交易流监控模块

监控大额交易、交易方向、异常交易模式等
"""

from decimal import Decimal
from typing import List, Dict, Optional, Deque
from collections import deque
from dataclasses import dataclass
import time


@dataclass
class Trade:
    """交易记录"""
    price: Decimal
    size: Decimal
    side: str  # 'buy' or 'sell'
    timestamp: float
    trade_id: Optional[str] = None
    
    @property
    def value(self) -> Decimal:
        """交易价值（美元）"""
        return self.price * self.size


class TradeFlowMonitor:
    """交易流监控器"""
    
    def __init__(self, window_seconds: int = 60, large_order_threshold: Decimal = Decimal(50000)):
        """
        初始化交易流监控器
        
        Args:
            window_seconds: 时间窗口（秒）
            large_order_threshold: 大单阈值（美元）
        """
        self.window_seconds = window_seconds
        self.large_order_threshold = large_order_threshold
        self.trades: Deque[Trade] = deque()
        self.large_trades: Deque[Trade] = deque()
    
    def add_trade(self, price: Decimal, size: Decimal, side: str, trade_id: Optional[str] = None) -> Trade:
        """
        添加交易记录
        
        Args:
            price: 成交价格
            size: 成交数量
            side: 交易方向 ('buy' or 'sell')
            trade_id: 交易ID
        
        Returns:
            Trade: 交易记录对象
        """
        trade = Trade(
            price=price,
            size=size,
            side=side,
            timestamp=time.time(),
            trade_id=trade_id
        )
        
        self.trades.append(trade)
        
        # 如果是大单，记录到大单列表
        if trade.value >= self.large_order_threshold:
            self.large_trades.append(trade)
        
        # 清理过期交易
        self._cleanup_old_trades()
        
        return trade
    
    def _cleanup_old_trades(self):
        """清理超出时间窗口的交易"""
        current_time = time.time()
        cutoff_time = current_time - self.window_seconds
        
        # 清理普通交易
        while self.trades and self.trades[0].timestamp < cutoff_time:
            self.trades.popleft()
        
        # 清理大单交易
        while self.large_trades and self.large_trades[0].timestamp < cutoff_time:
            self.large_trades.popleft()
    
    def get_buy_sell_ratio(self) -> float:
        """
        计算买卖比例
        
        Returns:
            float: 买卖比例，> 1 表示买入占优，< 1 表示卖出占优
        """
        if not self.trades:
            return 1.0
        
        buy_volume = sum(trade.size for trade in self.trades if trade.side == 'buy')
        sell_volume = sum(trade.size for trade in self.trades if trade.side == 'sell')
        
        if sell_volume == 0:
            return float('inf') if buy_volume > 0 else 1.0
        
        return float(buy_volume / sell_volume)
    
    def get_buy_sell_imbalance(self) -> float:
        """
        计算买卖失衡比率
        
        Returns:
            float: 失衡比率，范围[-1, 1]
                  > 0 表示买入占优
                  < 0 表示卖出占优
        """
        if not self.trades:
            return 0.0
        
        buy_volume = sum(trade.size for trade in self.trades if trade.side == 'buy')
        sell_volume = sum(trade.size for trade in self.trades if trade.side == 'sell')
        total_volume = buy_volume + sell_volume
        
        if total_volume == 0:
            return 0.0
        
        imbalance = float((buy_volume - sell_volume) / total_volume)
        return imbalance
    
    def get_volume_profile(self) -> Dict[str, Decimal]:
        """
        获取成交量分布
        
        Returns:
            Dict包含买卖双方的成交量
        """
        buy_volume = sum(trade.size for trade in self.trades if trade.side == 'buy')
        sell_volume = sum(trade.size for trade in self.trades if trade.side == 'sell')
        total_volume = buy_volume + sell_volume
        
        return {
            'buy_volume': buy_volume,
            'sell_volume': sell_volume,
            'total_volume': total_volume,
            'buy_value': sum(trade.value for trade in self.trades if trade.side == 'buy'),
            'sell_value': sum(trade.value for trade in self.trades if trade.side == 'sell'),
            'total_value': sum(trade.value for trade in self.trades)
        }
    
    def get_large_trades_count(self) -> int:
        """获取大单数量"""
        return len(self.large_trades)
    
    def get_large_trades_value(self) -> Decimal:
        """获取大单总价值"""
        return sum(trade.value for trade in self.large_trades)
    
    def detect_momentum(self, lookback_seconds: int = 10) -> float:
        """
        检测价格动量
        
        Args:
            lookback_seconds: 回看时间（秒）
        
        Returns:
            float: 动量值，> 0 表示上涨动量，< 0 表示下跌动量
        """
        if not self.trades:
            return 0.0
        
        current_time = time.time()
        cutoff_time = current_time - lookback_seconds
        
        recent_trades = [t for t in self.trades if t.timestamp >= cutoff_time]
        
        if len(recent_trades) < 2:
            return 0.0
        
        # 计算价格变化
        first_price = recent_trades[0].price
        last_price = recent_trades[-1].price
        
        if first_price == 0:
            return 0.0
        
        momentum = float((last_price - first_price) / first_price)
        return momentum
    
    def detect_aggressive_buying(self, threshold: float = 0.7) -> bool:
        """
        检测激进买入
        
        Args:
            threshold: 买入比例阈值
        
        Returns:
            bool: 是否检测到激进买入
        """
        if not self.trades:
            return False
        
        recent_trades = list(self.trades)[-10:]  # 最近10笔交易
        if len(recent_trades) < 5:
            return False
        
        buy_count = sum(1 for t in recent_trades if t.side == 'buy')
        buy_ratio = buy_count / len(recent_trades)
        
        return buy_ratio >= threshold
    
    def detect_aggressive_selling(self, threshold: float = 0.7) -> bool:
        """
        检测激进卖出
        
        Args:
            threshold: 卖出比例阈值
        
        Returns:
            bool: 是否检测到激进卖出
        """
        if not self.trades:
            return False
        
        recent_trades = list(self.trades)[-10:]  # 最近10笔交易
        if len(recent_trades) < 5:
            return False
        
        sell_count = sum(1 for t in recent_trades if t.side == 'sell')
        sell_ratio = sell_count / len(recent_trades)
        
        return sell_ratio >= threshold
    
    def get_trade_flow_metrics(self) -> Dict:
        """
        获取交易流综合指标
        
        Returns:
            Dict包含各种交易流指标
        """
        volume_profile = self.get_volume_profile()
        buy_sell_ratio = self.get_buy_sell_ratio()
        imbalance = self.get_buy_sell_imbalance()
        momentum = self.detect_momentum()
        
        return {
            'total_trades': len(self.trades),
            'large_trades_count': self.get_large_trades_count(),
            'large_trades_value': float(self.get_large_trades_value()),
            'buy_volume': float(volume_profile['buy_volume']),
            'sell_volume': float(volume_profile['sell_volume']),
            'total_volume': float(volume_profile['total_volume']),
            'buy_value': float(volume_profile['buy_value']),
            'sell_value': float(volume_profile['sell_value']),
            'total_value': float(volume_profile['total_value']),
            'buy_sell_ratio': buy_sell_ratio,
            'imbalance': imbalance,
            'momentum': momentum,
            'aggressive_buying': self.detect_aggressive_buying(),
            'aggressive_selling': self.detect_aggressive_selling()
        }
