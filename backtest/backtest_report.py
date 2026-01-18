"""
回测报告生成器

生成详细的回测报告，包括文本报告和CSV导出
"""

from decimal import Decimal
from typing import List, Optional
from pathlib import Path
import csv
from datetime import datetime

from ..shared.performance_metrics import PerformanceMetrics, TradeRecord
from .backtest_engine import BacktestResult


class BacktestReportGenerator:
    """回测报告生成器"""
    
    @staticmethod
    def generate_text_report(result: BacktestResult, output_file: Optional[str] = None) -> str:
        """
        生成文本格式的回测报告
        
        Args:
            result: 回测结果
            output_file: 输出文件路径（可选）
        
        Returns:
            str: 报告文本
        """
        metrics = result.metrics
        
        report = []
        report.append("=" * 80)
        report.append("订单流交易策略 - 回测报告")
        report.append("=" * 80)
        report.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # 基础信息
        report.append("【基础信息】")
        report.append(f"初始资金: ${result.initial_balance:,.2f}")
        report.append(f"最终资金: ${result.final_balance:,.2f}")
        report.append(f"总盈亏: ${result.final_balance - result.initial_balance:,.2f}")
        report.append(f"总收益率: {metrics.total_return * 100:.2f}%")
        report.append("")
        
        # 交易统计
        report.append("【交易统计】")
        report.append(f"总交易次数: {metrics.total_trades}")
        report.append(f"盈利交易: {metrics.winning_trades}")
        report.append(f"亏损交易: {metrics.losing_trades}")
        report.append(f"胜率: {metrics.win_rate * 100:.2f}%")
        report.append(f"平均盈利: ${metrics.average_win:,.2f}")
        report.append(f"平均亏损: ${metrics.average_loss:,.2f}")
        report.append(f"盈利因子: {metrics.profit_factor:.2f}")
        report.append("")
        
        # 风险指标
        report.append("【风险指标】")
        report.append(f"最大回撤: {metrics.max_drawdown * 100:.2f}%")
        report.append(f"最大回撤持续时间: {metrics.max_drawdown_duration / 3600:.2f} 小时")
        if metrics.sharpe_ratio is not None:
            report.append(f"夏普比率: {metrics.sharpe_ratio:.2f}")
        if metrics.sortino_ratio is not None:
            report.append(f"索提诺比率: {metrics.sortino_ratio:.2f}")
        report.append("")
        
        # 其他指标
        report.append("【其他指标】")
        report.append(f"平均持仓时间: {metrics.average_holding_time / 60:.2f} 分钟")
        report.append(f"最大连续盈利: {metrics.max_consecutive_wins}")
        report.append(f"最大连续亏损: {metrics.max_consecutive_losses}")
        report.append("")
        
        # 信号统计
        report.append("【信号统计】")
        report.append(f"生成信号数: {result.signals_generated}")
        report.append(f"执行信号数: {result.signals_executed}")
        if result.signals_generated > 0:
            execution_rate = result.signals_executed / result.signals_generated * 100
            report.append(f"信号执行率: {execution_rate:.2f}%")
        report.append("")
        
        # 交易明细（前10笔）
        if result.trades:
            report.append("【交易明细（前10笔）】")
            report.append(f"{'时间':<20} {'方向':<8} {'价格':<12} {'数量':<12} {'盈亏':<12}")
            report.append("-" * 80)
            
            for trade in result.trades[:10]:
                timestamp_str = datetime.fromtimestamp(trade.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                direction_str = trade.direction.upper()
                price_str = f"${trade.price:,.2f}"
                size_str = f"{trade.size:.4f}"
                pnl_str = f"${trade.pnl:,.2f}"
                report.append(f"{timestamp_str:<20} {direction_str:<8} {price_str:<12} {size_str:<12} {pnl_str:<12}")
            
            if len(result.trades) > 10:
                report.append(f"... 还有 {len(result.trades) - 10} 笔交易")
            report.append("")
        
        report.append("=" * 80)
        
        report_text = "\n".join(report)
        
        # 保存到文件
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"报告已保存到: {output_file}")
        
        return report_text
    
    @staticmethod
    def export_trades_to_csv(result: BacktestResult, output_file: str):
        """
        导出交易记录到CSV
        
        Args:
            result: 回测结果
            output_file: 输出文件路径
        """
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp', 'datetime', 'direction', 'price', 'size', 'value', 'pnl'])
            
            for trade in result.trades:
                dt = datetime.fromtimestamp(trade.timestamp).strftime('%Y-%m-%d %H:%M:%S')
                value = trade.price * trade.size
                writer.writerow([
                    trade.timestamp,
                    dt,
                    trade.direction,
                    float(trade.price),
                    float(trade.size),
                    float(value),
                    float(trade.pnl)
                ])
        
        print(f"交易记录已导出到: {output_file}")
    
    @staticmethod
    def export_equity_curve_to_csv(result: BacktestResult, output_file: str):
        """
        导出权益曲线到CSV
        
        Args:
            result: 回测结果
            output_file: 输出文件路径
        """
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['index', 'equity'])
            
            for i, equity in enumerate(result.equity_curve):
                writer.writerow([i, equity])
        
        print(f"权益曲线已导出到: {output_file}")
    
    @staticmethod
    def generate_summary(result: BacktestResult) -> str:
        """
        生成简要摘要
        
        Args:
            result: 回测结果
        
        Returns:
            str: 摘要文本
        """
        metrics = result.metrics
        return (
            f"回测摘要: "
            f"收益率={metrics.total_return*100:.2f}%, "
            f"胜率={metrics.win_rate*100:.2f}%, "
            f"最大回撤={metrics.max_drawdown*100:.2f}%, "
            f"交易次数={metrics.total_trades}, "
            f"盈利因子={metrics.profit_factor:.2f}"
        )
