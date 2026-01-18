"""
回测性能指标计算模块
"""

from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import math


@dataclass
class TradeRecord:
    """交易记录"""
    timestamp: float
    direction: str  # 'buy' or 'sell'
    price: Decimal
    size: Decimal
    pnl: Decimal = Decimal(0)  # 该笔交易的盈亏
    
    @property
    def value(self) -> Decimal:
        """交易价值"""
        return self.price * self.size


@dataclass
class PerformanceMetrics:
    """性能指标"""
    # 基础指标
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    # 盈亏指标
    total_pnl: Decimal
    total_return: float  # 总收益率
    average_win: Decimal
    average_loss: Decimal
    profit_factor: float  # 盈利因子 = 总盈利 / 总亏损
    
    # 风险指标
    max_drawdown: float  # 最大回撤
    max_drawdown_duration: float  # 最大回撤持续时间（秒）
    sharpe_ratio: Optional[float]  # 夏普比率
    sortino_ratio: Optional[float]  # 索提诺比率
    
    # 其他指标
    average_holding_time: float  # 平均持仓时间（秒）
    max_consecutive_wins: int
    max_consecutive_losses: int


class PerformanceCalculator:
    """性能指标计算器"""
    
    @staticmethod
    def calculate_metrics(
        trades: List[TradeRecord],
        initial_balance: Decimal = Decimal(10000),
        risk_free_rate: float = 0.0
    ) -> PerformanceMetrics:
        """
        计算性能指标
        
        Args:
            trades: 交易记录列表
            initial_balance: 初始资金
            risk_free_rate: 无风险利率（年化）
        
        Returns:
            PerformanceMetrics: 性能指标
        """
        if not trades:
            return PerformanceMetrics(
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate=0.0,
                total_pnl=Decimal(0),
                total_return=0.0,
                average_win=Decimal(0),
                average_loss=Decimal(0),
                profit_factor=0.0,
                max_drawdown=0.0,
                max_drawdown_duration=0.0,
                sharpe_ratio=None,
                sortino_ratio=None,
                average_holding_time=0.0,
                max_consecutive_wins=0,
                max_consecutive_losses=0
            )
        
        # 基础统计
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if t.pnl > 0)
        losing_trades = sum(1 for t in trades if t.pnl < 0)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0.0
        
        # 盈亏统计
        total_pnl = sum(t.pnl for t in trades)
        total_return = float(total_pnl / initial_balance) if initial_balance > 0 else 0.0
        
        wins = [t.pnl for t in trades if t.pnl > 0]
        losses = [abs(t.pnl) for t in trades if t.pnl < 0]
        
        average_win = Decimal(sum(wins) / len(wins)) if wins else Decimal(0)
        average_loss = Decimal(sum(losses) / len(losses)) if losses else Decimal(0)
        
        total_profit = sum(wins) if wins else 0
        total_loss = sum(losses) if losses else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf') if total_profit > 0 else 0.0
        
        # 计算回撤
        equity_curve = []
        running_balance = initial_balance
        for trade in trades:
            running_balance += trade.pnl
            equity_curve.append(float(running_balance))
        
        max_drawdown, max_drawdown_duration = PerformanceCalculator._calculate_drawdown(
            equity_curve, trades
        )
        
        # 计算夏普比率和索提诺比率
        returns = PerformanceCalculator._calculate_returns(trades, initial_balance)
        sharpe_ratio = PerformanceCalculator._calculate_sharpe_ratio(returns, risk_free_rate)
        sortino_ratio = PerformanceCalculator._calculate_sortino_ratio(returns, risk_free_rate)
        
        # 计算平均持仓时间
        if len(trades) >= 2:
            holding_times = [
                trades[i+1].timestamp - trades[i].timestamp
                for i in range(len(trades) - 1)
            ]
            average_holding_time = sum(holding_times) / len(holding_times) if holding_times else 0.0
        else:
            average_holding_time = 0.0
        
        # 计算最大连续盈亏
        max_consecutive_wins, max_consecutive_losses = PerformanceCalculator._calculate_consecutive(
            trades
        )
        
        return PerformanceMetrics(
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            total_pnl=total_pnl,
            total_return=total_return,
            average_win=average_win,
            average_loss=average_loss,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            average_holding_time=average_holding_time,
            max_consecutive_wins=max_consecutive_wins,
            max_consecutive_losses=max_consecutive_losses
        )
    
    @staticmethod
    def _calculate_drawdown(equity_curve: List[float], trades: List[TradeRecord]) -> Tuple[float, float]:
        """计算最大回撤"""
        if not equity_curve:
            return 0.0, 0.0
        
        peak = equity_curve[0]
        max_dd = 0.0
        dd_start_time = None
        max_dd_duration = 0.0
        
        for i, equity in enumerate(equity_curve):
            if equity > peak:
                peak = equity
                dd_start_time = None
            else:
                dd = (peak - equity) / peak if peak > 0 else 0.0
                if dd > max_dd:
                    max_dd = dd
                    if dd_start_time is None:
                        dd_start_time = trades[i].timestamp if i < len(trades) else 0
                
                if dd_start_time and i < len(trades):
                    duration = trades[i].timestamp - dd_start_time
                    if duration > max_dd_duration:
                        max_dd_duration = duration
        
        return max_dd, max_dd_duration
    
    @staticmethod
    def _calculate_returns(trades: List[TradeRecord], initial_balance: Decimal) -> List[float]:
        """计算收益率序列"""
        if not trades:
            return []
        
        returns = []
        running_balance = float(initial_balance)
        
        for trade in trades:
            if running_balance > 0:
                return_pct = float(trade.pnl / Decimal(running_balance))
                returns.append(return_pct)
                running_balance += float(trade.pnl)
            else:
                returns.append(0.0)
        
        return returns
    
    @staticmethod
    def _calculate_sharpe_ratio(returns: List[float], risk_free_rate: float) -> Optional[float]:
        """计算夏普比率"""
        if not returns or len(returns) < 2:
            return None
        
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)
        
        if std_dev == 0:
            return None
        
        # 假设是日收益率，年化
        annualized_return = mean_return * 252
        annualized_std = std_dev * math.sqrt(252)
        
        sharpe = (annualized_return - risk_free_rate) / annualized_std if annualized_std > 0 else None
        return sharpe
    
    @staticmethod
    def _calculate_sortino_ratio(returns: List[float], risk_free_rate: float) -> Optional[float]:
        """计算索提诺比率（只考虑下行风险）"""
        if not returns or len(returns) < 2:
            return None
        
        mean_return = sum(returns) / len(returns)
        downside_returns = [r for r in returns if r < 0]
        
        if not downside_returns:
            return None
        
        downside_variance = sum(r ** 2 for r in downside_returns) / len(downside_returns)
        downside_std = math.sqrt(downside_variance)
        
        if downside_std == 0:
            return None
        
        # 年化
        annualized_return = mean_return * 252
        annualized_downside_std = downside_std * math.sqrt(252)
        
        sortino = (annualized_return - risk_free_rate) / annualized_downside_std if annualized_downside_std > 0 else None
        return sortino
    
    @staticmethod
    def _calculate_consecutive(trades: List[TradeRecord]) -> Tuple[int, int]:
        """计算最大连续盈亏"""
        if not trades:
            return 0, 0
        
        max_wins = 0
        max_losses = 0
        current_wins = 0
        current_losses = 0
        
        for trade in trades:
            if trade.pnl > 0:
                current_wins += 1
                current_losses = 0
                max_wins = max(max_wins, current_wins)
            elif trade.pnl < 0:
                current_losses += 1
                current_wins = 0
                max_losses = max(max_losses, current_losses)
            else:
                current_wins = 0
                current_losses = 0
        
        return max_wins, max_losses
