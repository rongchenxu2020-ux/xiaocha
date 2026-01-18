"""
订单流交易策略核心实现

整合订单簿分析和交易流监控，生成交易信号并执行
"""

import asyncio
import time
from decimal import Decimal
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

from exchanges import ExchangeFactory
from helpers import TradingLogger
from ..shared.config import OrderFlowConfig
from ..shared.orderbook_analyzer import OrderBookAnalyzer, OrderBookSnapshot
from ..shared.trade_flow_monitor import TradeFlowMonitor, Trade


@dataclass
class TradingSignal:
    """交易信号"""
    direction: str  # 'buy' or 'sell'
    strength: float  # 信号强度 0-1
    price: Decimal
    reason: str
    timestamp: float
    
    def is_valid(self, min_strength: float = 0.7) -> bool:
        """检查信号是否有效"""
        return self.strength >= min_strength


class OrderFlowStrategy:
    """订单流交易策略"""
    
    def __init__(self, config: OrderFlowConfig):
        """
        初始化订单流策略
        
        Args:
            config: 策略配置
        """
        self.config = config
        
        # 初始化交易所客户端
        # 创建一个简单的配置对象，兼容字典和对象访问
        class ExchangeConfig:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        exchange_config = ExchangeConfig(
            contract_id=config.contract_id,
            ticker=config.ticker,
            tick_size=Decimal('0.01'),  # 默认值，实际应从交易所获取
            quantity=config.position_size,  # 添加quantity字段，某些交易所可能需要
        )
        self.exchange_client = ExchangeFactory.create_exchange(
            config.exchange,
            exchange_config
        )
        
        # 初始化分析器
        self.orderbook_analyzer = OrderBookAnalyzer(depth=config.orderbook_depth)
        self.trade_flow_monitor = TradeFlowMonitor(
            window_seconds=config.trade_flow_window,
            large_order_threshold=config.large_order_threshold
        )
        
        # 初始化日志
        self.logger = TradingLogger(
            exchange=config.exchange,
            ticker=config.ticker,
            log_to_console=config.enable_logging
        )
        
        # 状态管理
        self.running = False
        self.current_position = Decimal(0)
        self.active_orders: List[str] = []
        self.signals_history: List[TradingSignal] = []
        self.last_order_time = 0
        self.order_count_today = 0
        self.daily_pnl = Decimal(0)
        
        # 信号确认
        self.signal_buffer: List[TradingSignal] = []
    
    async def initialize(self):
        """初始化策略"""
        try:
            # 获取合约信息（contract_id和tick_size）
            if hasattr(self.exchange_client, 'get_contract_attributes'):
                contract_id, tick_size = await self.exchange_client.get_contract_attributes()
                self.config.contract_id = contract_id
                # 更新exchange_client的配置
                self.exchange_client.config.contract_id = contract_id
                self.exchange_client.config.tick_size = tick_size
            else:
                # 如果交易所不支持，尝试从ticker推断
                self.config.contract_id = self.config.ticker
            
            await self.exchange_client.connect()
            self.logger.log("订单流策略初始化成功", "INFO")
            self.logger.log(f"合约ID: {self.config.contract_id}", "INFO")
        except Exception as e:
            self.logger.log(f"初始化失败: {e}", "ERROR")
            raise
    
    async def fetch_orderbook_depth(self) -> Tuple[List[Tuple[Decimal, Decimal]], List[Tuple[Decimal, Decimal]]]:
        """
        获取订单簿深度数据
        
        Returns:
            Tuple[(bids: [(price, size), ...]), (asks: [(price, size), ...])]
        """
        try:
            exchange_name = self.exchange_client.get_exchange_name()
            
            # EdgeX: 使用深度API
            if exchange_name == 'edgex':
                from edgex_sdk import GetOrderBookDepthParams
                depth_params = GetOrderBookDepthParams(
                    contract_id=self.config.contract_id,
                    limit=self.config.orderbook_depth
                )
                order_book = await self.exchange_client.client.quote.get_order_book_depth(depth_params)
                order_book_data = order_book['data']
                
                if order_book_data:
                    order_book_entry = order_book_data[0]
                    bids_raw = order_book_entry.get('bids', [])
                    asks_raw = order_book_entry.get('asks', [])
                    
                    # 转换为 (price, size) 元组列表
                    bids = [(Decimal(b['price']), Decimal(b['size'])) for b in bids_raw]
                    asks = [(Decimal(a['price']), Decimal(a['size'])) for a in asks_raw]
                    
                    return bids, asks
            
            # Backpack: 使用深度API
            elif exchange_name == 'backpack':
                order_book = self.exchange_client.public_client.get_depth(self.config.contract_id)
                bids_raw = order_book.get('bids', [])
                asks_raw = order_book.get('asks', [])
                
                # Backpack返回格式: [[price, size], ...]
                bids = [(Decimal(b[0]), Decimal(b[1])) for b in bids_raw[:self.config.orderbook_depth]]
                asks = [(Decimal(a[0]), Decimal(a[1])) for a in asks_raw[:self.config.orderbook_depth]]
                
                # 确保排序正确
                bids = sorted(bids, key=lambda x: x[0], reverse=True)  # 价格从高到低
                asks = sorted(asks, key=lambda x: x[0])  # 价格从低到高
                
                return bids, asks
            
            # Paradex: 使用深度API
            elif exchange_name == 'paradex':
                orderbook_data = self.exchange_client.paradex.api_client.fetch_orderbook(
                    self.config.contract_id,
                    {"depth": self.config.orderbook_depth}
                )
                
                if orderbook_data:
                    bids_raw = orderbook_data.get('bids', [])
                    asks_raw = orderbook_data.get('asks', [])
                    
                    # Paradex返回格式: [[price, size], ...]
                    bids = [(Decimal(b[0]), Decimal(b[1])) for b in bids_raw]
                    asks = [(Decimal(a[0]), Decimal(a[1])) for a in asks_raw]
                    
                    return bids, asks
            
            # Apex: 使用深度API
            elif exchange_name == 'apex':
                order_book = self.exchange_client.rest_client.depth_v3(symbol=self.config.contract_id)
                order_book_data = order_book.get('data', {})
                
                bids_raw = order_book_data.get('b', [])
                asks_raw = order_book_data.get('a', [])
                
                # Apex返回格式: [[price, size], ...]
                bids = [(Decimal(b[0]), Decimal(b[1])) for b in bids_raw[:self.config.orderbook_depth]]
                asks = [(Decimal(a[0]), Decimal(a[1])) for a in asks_raw[:self.config.orderbook_depth]]
                
                return bids, asks
            
            # 其他交易所：尝试使用fetch_bbo_prices并生成模拟深度数据
            else:
                best_bid, best_ask = await self.exchange_client.fetch_bbo_prices(self.config.contract_id)
                
                if best_bid > 0 and best_ask > 0:
                    # 生成模拟深度数据（仅用于演示，实际应使用交易所的深度API）
                    spread = best_ask - best_bid
                    bids = []
                    asks = []
                    
                    for i in range(self.config.orderbook_depth):
                        bid_price = best_bid - spread * i * Decimal(0.1)
                        ask_price = best_ask + spread * i * Decimal(0.1)
                        bids.append((bid_price, Decimal(100)))
                        asks.append((ask_price, Decimal(100)))
                    
                    return bids, asks
                else:
                    return [], []
                    
        except Exception as e:
            self.logger.log(f"获取订单簿深度失败: {e}", "WARN")
            # 如果获取深度失败，尝试获取BBO并生成基础数据
            try:
                best_bid, best_ask = await self.exchange_client.fetch_bbo_prices(self.config.contract_id)
                if best_bid > 0 and best_ask > 0:
                    return [(best_bid, Decimal(100))], [(best_ask, Decimal(100))]
            except:
                pass
            return [], []
    
    async def update_orderbook(self):
        """更新订单簿数据"""
        try:
            bids, asks = await self.fetch_orderbook_depth()
            if bids and asks:
                snapshot = self.orderbook_analyzer.update_snapshot(bids, asks)
                return snapshot
        except Exception as e:
            self.logger.log(f"更新订单簿失败: {e}", "WARN")
        return None
    
    def generate_signal(self) -> Optional[TradingSignal]:
        """
        生成交易信号
        
        Returns:
            TradingSignal: 交易信号，如果无信号则返回None
        """
        if not self.orderbook_analyzer.current_snapshot:
            return None
        
        snapshot = self.orderbook_analyzer.current_snapshot
        
        # 获取订单簿指标
        orderbook_metrics = self.orderbook_analyzer.get_orderbook_metrics(snapshot)
        imbalance = orderbook_metrics['imbalance']
        weighted_imbalance = orderbook_metrics['weighted_imbalance']
        
        # 获取交易流指标
        trade_flow_metrics = self.trade_flow_monitor.get_trade_flow_metrics()
        trade_imbalance = trade_flow_metrics['imbalance']
        momentum = trade_flow_metrics['momentum']
        
        # 信号强度计算
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
        if abs(momentum) > 0.001:  # 0.1%的价格变化
            if momentum > 0 and direction != 'sell':
                direction = 'buy'
                signal_strength += min(abs(momentum) * 100, 0.1)  # 限制贡献
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
            price = snapshot.best_ask  # 买入时使用卖一价
        else:
            price = snapshot.best_bid  # 卖出时使用买一价
        
        signal = TradingSignal(
            direction=direction,
            strength=min(signal_strength, 1.0),
            price=price,
            reason='; '.join(reasons),
            timestamp=time.time()
        )
        
        return signal
    
    def confirm_signal(self, signal: TradingSignal) -> bool:
        """
        确认信号（需要连续多个信号确认）
        
        Args:
            signal: 交易信号
        
        Returns:
            bool: 信号是否被确认
        """
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
    
    async def execute_signal(self, signal: TradingSignal) -> bool:
        """
        执行交易信号
        
        Args:
            signal: 交易信号
        
        Returns:
            bool: 是否执行成功
        """
        # 风险控制检查
        if not self._check_risk_limits():
            return False
        
        # 检查持仓限制
        if signal.direction == 'buy' and self.current_position >= self.config.max_position:
            self.logger.log(f"已达到最大持仓限制: {self.config.max_position}", "WARN")
            return False
        
        if signal.direction == 'sell' and self.current_position <= -self.config.max_position:
            self.logger.log(f"已达到最大持仓限制: {self.config.max_position}", "WARN")
            return False
        
        try:
            # 下单
            order_result = await self.exchange_client.place_open_order(
                contract_id=self.config.contract_id,
                quantity=self.config.position_size,
                direction=signal.direction
            )
            
            if order_result.success:
                self.active_orders.append(order_result.order_id)
                self.last_order_time = time.time()
                self.order_count_today += 1
                
                self.logger.log(
                    f"执行信号: {signal.direction.upper()} @ {signal.price}, "
                    f"原因: {signal.reason}, 强度: {signal.strength:.2%}",
                    "INFO"
                )
                
                # 更新持仓（简化处理，实际应从交易所获取）
                if signal.direction == 'buy':
                    self.current_position += self.config.position_size
                else:
                    self.current_position -= self.config.position_size
                
                return True
            else:
                self.logger.log(f"下单失败: {order_result.error_message}", "ERROR")
                return False
                
        except Exception as e:
            self.logger.log(f"执行信号失败: {e}", "ERROR")
            return False
    
    def _check_risk_limits(self) -> bool:
        """检查风险限制"""
        # 检查每日最大亏损
        if self.config.max_daily_loss and self.daily_pnl <= -self.config.max_daily_loss:
            self.logger.log(f"达到每日最大亏损限制: {self.config.max_daily_loss}", "WARN")
            return False
        
        # 检查订单频率
        current_time = time.time()
        if current_time - self.last_order_time < 60 / self.config.max_orders_per_minute:
            return False
        
        return True
    
    async def monitor_positions(self):
        """监控持仓并管理止损止盈"""
        # 这里应该实现止损止盈逻辑
        # 简化实现，实际需要根据持仓情况设置止损止盈订单
        pass
    
    async def run(self):
        """运行策略主循环"""
        self.running = True
        self.logger.log("订单流策略开始运行", "INFO")
        
        try:
            while self.running:
                # 更新订单簿
                snapshot = await self.update_orderbook()
                
                if snapshot:
                    # 生成信号
                    signal = self.generate_signal()
                    
                    if signal:
                        # 确认信号
                        if self.confirm_signal(signal):
                            # 执行信号
                            await self.execute_signal(signal)
                            self.signals_history.append(signal)
                    
                    # 记录指标
                    if self.config.enable_logging:
                        orderbook_metrics = self.orderbook_analyzer.get_orderbook_metrics()
                        trade_flow_metrics = self.trade_flow_monitor.get_trade_flow_metrics()
                        
                        self.logger.log(
                            f"订单簿失衡: {orderbook_metrics.get('imbalance', 0):.2%}, "
                            f"交易流失衡: {trade_flow_metrics.get('imbalance', 0):.2%}, "
                            f"持仓: {self.current_position}",
                            "DEBUG"
                        )
                
                # 监控持仓
                await self.monitor_positions()
                
                # 等待下一次更新
                await asyncio.sleep(self.config.update_interval)
                
        except KeyboardInterrupt:
            self.logger.log("收到停止信号", "INFO")
        except Exception as e:
            self.logger.log(f"策略运行错误: {e}", "ERROR")
        finally:
            await self.shutdown()
    
    async def shutdown(self):
        """关闭策略"""
        self.running = False
        try:
            await self.exchange_client.disconnect()
            self.logger.log("订单流策略已关闭", "INFO")
        except Exception as e:
            self.logger.log(f"关闭时出错: {e}", "ERROR")
    
    def get_strategy_status(self) -> Dict:
        """获取策略状态"""
        return {
            'running': self.running,
            'current_position': float(self.current_position),
            'active_orders_count': len(self.active_orders),
            'signals_generated': len(self.signals_history),
            'order_count_today': self.order_count_today,
            'daily_pnl': float(self.daily_pnl),
            'orderbook_metrics': self.orderbook_analyzer.get_orderbook_metrics() if self.orderbook_analyzer.current_snapshot else {},
            'trade_flow_metrics': self.trade_flow_monitor.get_trade_flow_metrics()
        }
