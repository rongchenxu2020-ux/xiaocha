"""
做市商策略配置类
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class MarketMakerConfig:
    """做市商策略配置参数"""
    # 基础参数
    exchange: str
    ticker: str
    contract_id: str
    
    # 订单簿分析参数
    orderbook_depth: int = 20  # 订单簿深度
    
    # 做市商参数
    order_size: Decimal = Decimal(0.1)  # 每笔订单的大小
    spread_type: str = 'percentage'  # 价差类型: 'fixed' 或 'percentage'
    target_spread: Decimal = Decimal(0.0001)  # 目标价差（固定价差时使用）
    spread_ratio: Decimal = Decimal(0.5)  # 价差比例（市场价差的百分比，如0.5表示市场价差的50%）
    min_spread: Decimal = Decimal(0.0001)  # 最小价差
    
    # 库存管理
    inventory_skew_enabled: bool = True  # 是否启用库存倾斜
    inventory_skew_factor: Decimal = Decimal(0.3)  # 库存倾斜因子（0-1）
    max_position: Decimal = Decimal(1.0)  # 最大持仓
    
    # 订单更新参数
    price_update_threshold: float = 0.001  # 价格更新阈值（1%）
    
    # 风险控制
    max_daily_loss: Optional[Decimal] = None  # 每日最大亏损
    
    # 其他参数
    update_interval: float = 0.5  # 更新间隔（秒）
    enable_logging: bool = True  # 是否启用日志


# 保持向后兼容（可选）
OrderFlowConfig = MarketMakerConfig
