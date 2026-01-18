"""
做市商交易策略模块

该模块提供做市商交易策略实现，同时在买卖两侧挂单，赚取买卖价差。
"""

__version__ = "1.0.0"

from .config import MarketMakerConfig, OrderFlowConfig  # OrderFlowConfig保持向后兼容
from .orderbook_analyzer import OrderBookAnalyzer, OrderBookSnapshot, OrderBookLevel
from .trade_flow_monitor import TradeFlowMonitor, Trade
from .market_maker_strategy import MarketMakerStrategy, MakerOrder

# 向后兼容：保留旧的导入
try:
    from .orderflow_strategy import OrderFlowStrategy, TradingSignal
except ImportError:
    OrderFlowStrategy = None
    TradingSignal = None

# 回测相关
from .backtest_data import BacktestData, BacktestDataLoader, HistoricalOrderBook, HistoricalTrade
from .backtest_engine import BacktestEngine, BacktestResult
from .performance_metrics import PerformanceMetrics, PerformanceCalculator, TradeRecord
from .backtest_report import BacktestReportGenerator

__all__ = [
    # 策略相关
    'MarketMakerConfig',
    'OrderFlowConfig',  # 向后兼容
    'OrderBookAnalyzer',
    'OrderBookSnapshot',
    'OrderBookLevel',
    'TradeFlowMonitor',
    'Trade',
    'MarketMakerStrategy',
    'MakerOrder',
    # 向后兼容
    'OrderFlowStrategy',
    'TradingSignal',
    # 回测相关
    'BacktestData',
    'BacktestDataLoader',
    'HistoricalOrderBook',
    'HistoricalTrade',
    'BacktestEngine',
    'BacktestResult',
    'PerformanceMetrics',
    'PerformanceCalculator',
    'TradeRecord',
    'BacktestReportGenerator',
]
