"""
做市商交易策略核心实现

同时在买卖两侧挂单，赚取买卖价差
"""

import asyncio
import time
from decimal import Decimal
from typing import Optional, Dict, List, Tuple
from dataclasses import dataclass

from exchanges import ExchangeFactory
from helpers import TradingLogger
from ..shared.config import MarketMakerConfig
from ..shared.orderbook_analyzer import OrderBookAnalyzer, OrderBookSnapshot


@dataclass
class MakerOrder:
    """做市商订单"""
    order_id: str
    side: str  # 'buy' or 'sell'
    price: Decimal
    quantity: Decimal
    timestamp: float


class MarketMakerStrategy:
    """做市商交易策略"""
    
    def __init__(self, config: MarketMakerConfig):
        """
        初始化做市商策略
        
        Args:
            config: 策略配置
        """
        self.config = config
        
        # 初始化交易所客户端
        class ExchangeConfig:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)
        
        exchange_config = ExchangeConfig(
            contract_id=config.contract_id,
            ticker=config.ticker,
            tick_size=Decimal('0.01'),
            quantity=config.order_size,
        )
        self.exchange_client = ExchangeFactory.create_exchange(
            config.exchange,
            exchange_config
        )
        
        # 初始化分析器
        self.orderbook_analyzer = OrderBookAnalyzer(depth=config.orderbook_depth)
        
        # 初始化日志
        self.logger = TradingLogger(
            exchange=config.exchange,
            ticker=config.ticker,
            log_to_console=config.enable_logging
        )
        
        # 状态管理
        self.running = False
        self.current_position = Decimal(0)
        self.active_buy_order: Optional[MakerOrder] = None
        self.active_sell_order: Optional[MakerOrder] = None
        self.order_count_today = 0
        self.daily_pnl = Decimal(0)
        self.last_mid_price = None
        self.simulate_mode = False  # 模拟模式标志
        
    async def initialize(self):
        """初始化策略"""
        try:
            # 获取合约信息
            if hasattr(self.exchange_client, 'get_contract_attributes'):
                contract_id, tick_size = await self.exchange_client.get_contract_attributes()
                self.config.contract_id = contract_id
                self.exchange_client.config.contract_id = contract_id
                self.exchange_client.config.tick_size = tick_size
            else:
                self.config.contract_id = self.config.ticker
            
            await self.exchange_client.connect()
            self.logger.log("做市商策略初始化成功", "INFO")
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
            
            # EdgeX: 优先尝试使用深度API，失败则使用BBO数据
            if exchange_name == 'edgex':
                try:
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
                        
                        bids = [(Decimal(b['price']), Decimal(b['size'])) for b in bids_raw]
                        asks = [(Decimal(a['price']), Decimal(a['size'])) for a in asks_raw]
                        
                        return bids, asks
                except Exception as depth_error:
                    # 如果深度API失败，回退到使用BBO数据
                    self.logger.log(f"EdgeX深度API失败，使用BBO数据: {depth_error}", "WARN")
                
                # 使用BBO数据（与Lighter相同）
                best_bid, best_ask = await self.exchange_client.fetch_bbo_prices(self.config.contract_id)
                
                if best_bid > 0 and best_ask > 0:
                    # 使用BBO创建简化的订单簿（只需要best_bid和best_ask即可）
                    # 做市商策略只需要这两个价格
                    bids = [(best_bid, Decimal(100))]
                    asks = [(best_ask, Decimal(100))]
                    return bids, asks
                else:
                    return [], []
            
            # Backpack: 使用深度API
            elif exchange_name == 'backpack':
                order_book = self.exchange_client.public_client.get_depth(self.config.contract_id)
                bids_raw = order_book.get('bids', [])
                asks_raw = order_book.get('asks', [])
                
                bids = [(Decimal(b[0]), Decimal(b[1])) for b in bids_raw[:self.config.orderbook_depth]]
                asks = [(Decimal(a[0]), Decimal(a[1])) for a in asks_raw[:self.config.orderbook_depth]]
                
                bids = sorted(bids, key=lambda x: x[0], reverse=True)
                asks = sorted(asks, key=lambda x: x[0])
                
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
                    
                    bids = [(Decimal(b[0]), Decimal(b[1])) for b in bids_raw]
                    asks = [(Decimal(a[0]), Decimal(a[1])) for a in asks_raw]
                    
                    return bids, asks
            
            # Apex: 使用深度API
            elif exchange_name == 'apex':
                order_book = self.exchange_client.rest_client.depth_v3(symbol=self.config.contract_id)
                order_book_data = order_book.get('data', {})
                
                bids_raw = order_book_data.get('b', [])
                asks_raw = order_book_data.get('a', [])
                
                bids = [(Decimal(b[0]), Decimal(b[1])) for b in bids_raw[:self.config.orderbook_depth]]
                asks = [(Decimal(a[0]), Decimal(a[1])) for a in asks_raw[:self.config.orderbook_depth]]
                
                return bids, asks
            
            # Lighter: 使用BBO数据（WebSocket已提供best_bid和best_ask）
            elif exchange_name == 'lighter':
                best_bid, best_ask = await self.exchange_client.fetch_bbo_prices(self.config.contract_id)
                
                if best_bid > 0 and best_ask > 0:
                    spread = best_ask - best_bid
                    bids = []
                    asks = []
                    
                    # 使用BBO创建简化的订单簿（只需要best_bid和best_ask即可）
                    # 做市商策略只需要这两个价格
                    bids.append((best_bid, Decimal(100)))
                    asks.append((best_ask, Decimal(100)))
                    
                    return bids, asks
                else:
                    return [], []
            
            # 其他交易所：使用BBO
            else:
                best_bid, best_ask = await self.exchange_client.fetch_bbo_prices(self.config.contract_id)
                
                if best_bid > 0 and best_ask > 0:
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
            else:
                # 如果获取订单簿深度失败，尝试使用BBO数据
                try:
                    best_bid, best_ask = await self.exchange_client.fetch_bbo_prices(self.config.contract_id)
                    if best_bid > 0 and best_ask > 0:
                        # 使用BBO创建最小订单簿快照
                        bids = [(best_bid, Decimal(100))]
                        asks = [(best_ask, Decimal(100))]
                        snapshot = self.orderbook_analyzer.update_snapshot(bids, asks)
                        return snapshot
                except Exception as e2:
                    self.logger.log(f"使用BBO数据也失败: {e2}", "WARN")
        except Exception as e:
            self.logger.log(f"更新订单簿失败: {e}", "WARN")
        return None
    
    def calculate_maker_prices(self, snapshot: OrderBookSnapshot) -> Tuple[Decimal, Decimal]:
        """
        计算做市商报价
        
        Args:
            snapshot: 订单簿快照
            
        Returns:
            Tuple[bid_price, ask_price]: 买卖报价
        """
        if not snapshot:
            return None, None
        
        mid_price = (snapshot.best_bid + snapshot.best_ask) / 2
        spread = snapshot.best_ask - snapshot.best_bid
        
        # 根据配置的价差比例计算报价
        # 如果使用固定价差，则使用固定值；否则使用市场价差的百分比
        if self.config.spread_type == 'fixed':
            target_spread = self.config.target_spread
        else:
            # 使用市场价差的百分比
            target_spread = spread * self.config.spread_ratio
        
        # 确保价差不小于最小价差
        min_spread = self.config.min_spread
        if target_spread < min_spread:
            target_spread = min_spread
        
        # 计算买卖价格（在中间价两侧）
        bid_price = mid_price - target_spread / 2
        ask_price = mid_price + target_spread / 2
        
        # 根据持仓调整价格（库存倾斜）
        if self.config.inventory_skew_enabled:
            # 如果持仓为正（多头），降低卖价，提高买价，鼓励卖出
            # 如果持仓为负（空头），提高买价，降低卖价，鼓励买入
            skew_factor = self.current_position / self.config.max_position if self.config.max_position > 0 else 0
            skew_adjustment = target_spread * skew_factor * self.config.inventory_skew_factor
            
            if skew_factor > 0:  # 多头，鼓励卖出
                ask_price -= skew_adjustment
                bid_price -= skew_adjustment * 0.5  # 买价调整较小
            elif skew_factor < 0:  # 空头，鼓励买入
                bid_price += skew_adjustment
                ask_price += skew_adjustment * 0.5  # 卖价调整较小
        
        # 确保价格符合tick_size
        tick_size = self.exchange_client.config.tick_size
        bid_price = (bid_price / tick_size).quantize(Decimal('1')) * tick_size
        ask_price = (ask_price / tick_size).quantize(Decimal('1')) * tick_size
        
        # 确保买价不超过卖价
        if bid_price >= ask_price:
            bid_price = ask_price - tick_size
        
        return bid_price, ask_price
    
    async def cancel_order(self, order: MakerOrder) -> bool:
        """取消订单"""
        if not order:
            return True
        
        try:
            # 模拟模式：不实际取消，只记录日志
            if self.simulate_mode:
                self.logger.log(f"[模拟模式] 模拟取消订单: {order.order_id}", "INFO")
                return True
            
            # 真实模式：实际取消订单
            # 这里应该调用交易所的取消订单API
            # 简化实现，实际需要根据交易所实现
            if hasattr(self.exchange_client, 'cancel_order'):
                result = await self.exchange_client.cancel_order(order.order_id)
                return result
            else:
                self.logger.log(f"交易所不支持取消订单: {order.order_id}", "WARN")
                return False
        except Exception as e:
            self.logger.log(f"取消订单失败: {e}", "ERROR")
            return False
    
    async def place_maker_order(self, side: str, price: Decimal, quantity: Decimal) -> Optional[MakerOrder]:
        """下做市商订单"""
        try:
            # 模拟模式：不实际下单，只记录日志
            if self.simulate_mode:
                # 生成模拟订单ID
                simulated_order_id = f"SIM_{side}_{int(time.time() * 1000)}"
                self.logger.log(
                    f"[模拟模式] 模拟下单: {side.upper()} {quantity} @ {price} (订单ID: {simulated_order_id})",
                    "INFO"
                )
                return MakerOrder(
                    order_id=simulated_order_id,
                    side=side,
                    price=price,
                    quantity=quantity,
                    timestamp=time.time()
                )
            
            # 真实模式：实际下单
            # 使用 place_close_order 因为它接受价格参数，并且确保是maker订单（post-only）
            order_result = await self.exchange_client.place_close_order(
                contract_id=self.config.contract_id,
                quantity=quantity,
                price=price,
                side=side
            )
            
            if order_result.success and order_result.order_id:
                return MakerOrder(
                    order_id=order_result.order_id,
                    side=side,
                    price=price,
                    quantity=quantity,
                    timestamp=time.time()
                )
            else:
                self.logger.log(f"下单失败: {order_result.error_message if order_result else 'Unknown error'}", "WARN")
                return None
        except Exception as e:
            self.logger.log(f"下单异常: {e}", "ERROR")
            return None
    
    async def update_maker_orders(self, snapshot: OrderBookSnapshot):
        """更新做市商订单"""
        if not snapshot:
            return
        
        # 计算新的报价
        new_bid_price, new_ask_price = self.calculate_maker_prices(snapshot)
        
        if not new_bid_price or not new_ask_price:
            return
        
        # 检查是否需要更新买单
        if self.active_buy_order:
            price_diff = abs(self.active_buy_order.price - new_bid_price)
            price_change_pct = price_diff / new_bid_price if new_bid_price > 0 else 0
            
            # 如果价格变化超过阈值，取消旧订单并下新订单
            if price_change_pct > self.config.price_update_threshold:
                self.logger.log(f"买单价格变化 {price_change_pct:.2%}，更新订单", "INFO")
                await self.cancel_order(self.active_buy_order)
                self.active_buy_order = None
        
        # 检查是否需要更新卖单
        if self.active_sell_order:
            price_diff = abs(self.active_sell_order.price - new_ask_price)
            price_change_pct = price_diff / new_ask_price if new_ask_price > 0 else 0
            
            if price_change_pct > self.config.price_update_threshold:
                self.logger.log(f"卖单价格变化 {price_change_pct:.2%}，更新订单", "INFO")
                await self.cancel_order(self.active_sell_order)
                self.active_sell_order = None
        
        # 如果没有买单，下一个
        if not self.active_buy_order:
            # 检查持仓限制
            if self.current_position < self.config.max_position:
                self.active_buy_order = await self.place_maker_order('buy', new_bid_price, self.config.order_size)
                if self.active_buy_order:
                    self.logger.log(f"下买单: {new_bid_price} x {self.config.order_size}", "INFO")
                    self.order_count_today += 1
        
        # 如果没有卖单，下一个
        if not self.active_sell_order:
            # 检查持仓限制
            if self.current_position > -self.config.max_position:
                self.active_sell_order = await self.place_maker_order('sell', new_ask_price, self.config.order_size)
                if self.active_sell_order:
                    self.logger.log(f"下卖单: {new_ask_price} x {self.config.order_size}", "INFO")
                    self.order_count_today += 1
    
    def _check_risk_limits(self) -> bool:
        """检查风险限制"""
        # 检查每日最大亏损
        if self.config.max_daily_loss and self.daily_pnl <= -self.config.max_daily_loss:
            self.logger.log(f"达到每日最大亏损限制: {self.config.max_daily_loss}", "WARN")
            return False
        
        return True
    
    async def monitor_positions(self):
        """监控持仓并管理风险"""
        # 检查持仓是否超出限制
        if abs(self.current_position) > self.config.max_position:
            self.logger.log(f"持仓超出限制: {self.current_position}", "WARN")
            # 可以在这里实现平仓逻辑
        
        # 检查风险限制
        if not self._check_risk_limits():
            # 停止下单
            if self.active_buy_order:
                await self.cancel_order(self.active_buy_order)
                self.active_buy_order = None
            if self.active_sell_order:
                await self.cancel_order(self.active_sell_order)
                self.active_sell_order = None
    
    async def run(self):
        """运行策略主循环"""
        self.running = True
        self.logger.log("做市商策略开始运行", "INFO")
        
        try:
            while self.running:
                # 更新订单簿
                snapshot = await self.update_orderbook()
                
                if snapshot:
                    # 更新做市商订单
                    await self.update_maker_orders(snapshot)
                    
                    # 记录状态
                    if self.config.enable_logging:
                        mid_price = (snapshot.best_bid + snapshot.best_ask) / 2
                        spread = snapshot.best_ask - snapshot.best_bid
                        
                        self.logger.log(
                            f"中间价: {mid_price}, 价差: {spread:.4f}, "
                            f"持仓: {self.current_position}, "
                            f"买单: {self.active_buy_order.price if self.active_buy_order else 'None'}, "
                            f"卖单: {self.active_sell_order.price if self.active_sell_order else 'None'}",
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
            # 取消所有活跃订单
            if self.active_buy_order:
                await self.cancel_order(self.active_buy_order)
            if self.active_sell_order:
                await self.cancel_order(self.active_sell_order)
            
            await self.exchange_client.disconnect()
            self.logger.log("做市商策略已关闭", "INFO")
        except Exception as e:
            self.logger.log(f"关闭时出错: {e}", "ERROR")
    
    def get_strategy_status(self) -> Dict:
        """获取策略状态"""
        snapshot = self.orderbook_analyzer.current_snapshot
        mid_price = None
        spread = None
        if snapshot:
            mid_price = float((snapshot.best_bid + snapshot.best_ask) / 2)
            spread = float(snapshot.best_ask - snapshot.best_bid)
        
        return {
            'running': self.running,
            'current_position': float(self.current_position),
            'active_buy_order': {
                'price': float(self.active_buy_order.price),
                'quantity': float(self.active_buy_order.quantity)
            } if self.active_buy_order else None,
            'active_sell_order': {
                'price': float(self.active_sell_order.price),
                'quantity': float(self.active_sell_order.quantity)
            } if self.active_sell_order else None,
            'order_count_today': self.order_count_today,
            'daily_pnl': float(self.daily_pnl),
            'mid_price': mid_price,
            'spread': spread,
        }
