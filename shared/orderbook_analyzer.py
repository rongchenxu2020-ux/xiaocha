"""
订单簿分析模块

分析订单簿深度、失衡、支撑阻力位等
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Tuple, Dict, Optional
from collections import deque
import time


@dataclass
class OrderBookLevel:
    """订单簿层级"""
    price: Decimal
    size: Decimal
    side: str  # 'bid' or 'ask'


@dataclass
class OrderBookSnapshot:
    """订单簿快照"""
    bids: List[OrderBookLevel]
    asks: List[OrderBookLevel]
    timestamp: float
    best_bid: Decimal
    best_ask: Decimal
    
    @property
    def mid_price(self) -> Decimal:
        """中间价"""
        return (self.best_bid + self.best_ask) / 2
    
    @property
    def spread(self) -> Decimal:
        """买卖价差"""
        return self.best_ask - self.best_bid
    
    @property
    def spread_pct(self) -> Decimal:
        """买卖价差百分比"""
        if self.mid_price > 0:
            return (self.spread / self.mid_price) * 100
        return Decimal(0)


class OrderBookAnalyzer:
    """订单簿分析器"""
    
    def __init__(self, depth: int = 20):
        """
        初始化订单簿分析器
        
        Args:
            depth: 分析的订单簿深度
        """
        self.depth = depth
        self.snapshots = deque(maxlen=100)  # 保存最近100个快照
        self.current_snapshot: Optional[OrderBookSnapshot] = None
    
    def update_snapshot(self, bids: List[Tuple[Decimal, Decimal]], 
                       asks: List[Tuple[Decimal, Decimal]]) -> OrderBookSnapshot:
        """
        更新订单簿快照
        
        Args:
            bids: [(price, size), ...] 买单列表，按价格从高到低
            asks: [(price, size), ...] 卖单列表，按价格从低到高
        
        Returns:
            OrderBookSnapshot: 订单簿快照
        """
        # 转换为OrderBookLevel对象
        bid_levels = [
            OrderBookLevel(price=Decimal(price), size=Decimal(size), side='bid')
            for price, size in bids[:self.depth]
        ]
        ask_levels = [
            OrderBookLevel(price=Decimal(price), size=Decimal(size), side='ask')
            for price, size in asks[:self.depth]
        ]
        
        best_bid = bid_levels[0].price if bid_levels else Decimal(0)
        best_ask = ask_levels[0].price if ask_levels else Decimal(0)
        
        snapshot = OrderBookSnapshot(
            bids=bid_levels,
            asks=ask_levels,
            timestamp=time.time(),
            best_bid=best_bid,
            best_ask=best_ask
        )
        
        self.current_snapshot = snapshot
        self.snapshots.append(snapshot)
        
        return snapshot
    
    def calculate_imbalance(self, snapshot: Optional[OrderBookSnapshot] = None) -> float:
        """
        计算订单簿失衡比率
        
        Args:
            snapshot: 订单簿快照，如果为None则使用当前快照
        
        Returns:
            float: 失衡比率，范围[-1, 1]
                  > 0 表示买单占优
                  < 0 表示卖单占优
        """
        if snapshot is None:
            snapshot = self.current_snapshot
        
        if not snapshot or not snapshot.bids or not snapshot.asks:
            return 0.0
        
        # 计算买卖双方的总量
        bid_volume = sum(level.size for level in snapshot.bids)
        ask_volume = sum(level.size for level in snapshot.asks)
        
        total_volume = bid_volume + ask_volume
        if total_volume == 0:
            return 0.0
        
        # 失衡比率 = (买单量 - 卖单量) / 总成交量
        imbalance = float((bid_volume - ask_volume) / total_volume)
        return imbalance
    
    def calculate_weighted_imbalance(self, snapshot: Optional[OrderBookSnapshot] = None,
                                    depth_levels: int = 5) -> float:
        """
        计算加权失衡比率（距离价格越近权重越大）
        
        Args:
            snapshot: 订单簿快照
            depth_levels: 考虑的深度层级数
        
        Returns:
            float: 加权失衡比率
        """
        if snapshot is None:
            snapshot = self.current_snapshot
        
        if not snapshot or not snapshot.bids or not snapshot.asks:
            return 0.0
        
        mid_price = snapshot.mid_price
        if mid_price == 0:
            return 0.0
        
        bid_weighted = Decimal(0)
        ask_weighted = Decimal(0)
        
        # 计算买单加权总量
        for i, level in enumerate(snapshot.bids[:depth_levels]):
            # 距离越近权重越大（使用倒数）
            weight = Decimal(1) / (i + 1)
            bid_weighted += level.size * weight
        
        # 计算卖单加权总量
        for i, level in enumerate(snapshot.asks[:depth_levels]):
            weight = Decimal(1) / (i + 1)
            ask_weighted += level.size * weight
        
        total_weighted = bid_weighted + ask_weighted
        if total_weighted == 0:
            return 0.0
        
        imbalance = float((bid_weighted - ask_weighted) / total_weighted)
        return imbalance
    
    def find_support_resistance(self, snapshot: Optional[OrderBookSnapshot] = None) -> Tuple[Decimal, Decimal]:
        """
        识别支撑位和阻力位
        
        Args:
            snapshot: 订单簿快照
        
        Returns:
            Tuple[支撑位, 阻力位]
        """
        if snapshot is None:
            snapshot = self.current_snapshot
        
        if not snapshot:
            return Decimal(0), Decimal(0)
        
        # 支撑位：买单量最大的价格
        support = Decimal(0)
        max_bid_size = Decimal(0)
        for level in snapshot.bids:
            if level.size > max_bid_size:
                max_bid_size = level.size
                support = level.price
        
        # 阻力位：卖单量最大的价格
        resistance = Decimal(0)
        max_ask_size = Decimal(0)
        for level in snapshot.asks:
            if level.size > max_ask_size:
                max_ask_size = level.size
                resistance = level.price
        
        return support, resistance
    
    def calculate_liquidity(self, snapshot: Optional[OrderBookSnapshot] = None,
                           price_range_pct: float = 0.5) -> Dict[str, Decimal]:
        """
        计算流动性指标
        
        Args:
            snapshot: 订单簿快照
            price_range_pct: 价格范围百分比
        
        Returns:
            Dict包含买卖双方的流动性指标
        """
        if snapshot is None:
            snapshot = self.current_snapshot
        
        if not snapshot:
            return {'bid_liquidity': Decimal(0), 'ask_liquidity': Decimal(0)}
        
        mid_price = snapshot.mid_price
        if mid_price == 0:
            return {'bid_liquidity': Decimal(0), 'ask_liquidity': Decimal(0)}
        
        price_range = mid_price * Decimal(price_range_pct / 100)
        bid_liquidity = Decimal(0)
        ask_liquidity = Decimal(0)
        
        # 计算买单流动性（在价格范围内的总量）
        for level in snapshot.bids:
            if level.price >= mid_price - price_range:
                bid_liquidity += level.size
        
        # 计算卖单流动性
        for level in snapshot.asks:
            if level.price <= mid_price + price_range:
                ask_liquidity += level.size
        
        return {
            'bid_liquidity': bid_liquidity,
            'ask_liquidity': ask_liquidity,
            'total_liquidity': bid_liquidity + ask_liquidity
        }
    
    def detect_large_orders(self, snapshot: Optional[OrderBookSnapshot] = None,
                           threshold: Decimal = Decimal(50000)) -> Dict[str, List[OrderBookLevel]]:
        """
        检测大单
        
        Args:
            snapshot: 订单簿快照
            threshold: 大单阈值（美元）
        
        Returns:
            Dict包含买卖双方的大单列表
        """
        if snapshot is None:
            snapshot = self.current_snapshot
        
        if not snapshot:
            return {'large_bids': [], 'large_asks': []}
        
        large_bids = []
        large_asks = []
        
        # 检测买单大单
        for level in snapshot.bids:
            order_value = level.price * level.size
            if order_value >= threshold:
                large_bids.append(level)
        
        # 检测卖单大单
        for level in snapshot.asks:
            order_value = level.price * level.size
            if order_value >= threshold:
                large_asks.append(level)
        
        return {
            'large_bids': large_bids,
            'large_asks': large_asks
        }
    
    def get_orderbook_metrics(self, snapshot: Optional[OrderBookSnapshot] = None) -> Dict:
        """
        获取订单簿综合指标
        
        Args:
            snapshot: 订单簿快照
        
        Returns:
            Dict包含各种订单簿指标
        """
        if snapshot is None:
            snapshot = self.current_snapshot
        
        if not snapshot:
            return {}
        
        imbalance = self.calculate_imbalance(snapshot)
        weighted_imbalance = self.calculate_weighted_imbalance(snapshot)
        support, resistance = self.find_support_resistance(snapshot)
        liquidity = self.calculate_liquidity(snapshot)
        
        return {
            'best_bid': float(snapshot.best_bid),
            'best_ask': float(snapshot.best_ask),
            'mid_price': float(snapshot.mid_price),
            'spread': float(snapshot.spread),
            'spread_pct': float(snapshot.spread_pct),
            'imbalance': imbalance,
            'weighted_imbalance': weighted_imbalance,
            'support': float(support),
            'resistance': float(resistance),
            'bid_liquidity': float(liquidity['bid_liquidity']),
            'ask_liquidity': float(liquidity['ask_liquidity']),
            'total_liquidity': float(liquidity['total_liquidity']),
            'timestamp': snapshot.timestamp
        }
