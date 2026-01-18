#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
订单流策略实时交易机器人
实时跟踪EdgeX交易所，执行订单流策略
"""

import sys
import asyncio
import signal
import json
import time
import csv
import os
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import dotenv

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from exchanges import ExchangeFactory
from shared.config import MarketMakerConfig
from strategies.market_maker_strategy import MarketMakerStrategy
# 向后兼容
from shared.config import OrderFlowConfig
try:
    from strategies.orderflow_strategy import OrderFlowStrategy
except ImportError:
    OrderFlowStrategy = None
from shared.orderbook_analyzer import OrderBookSnapshot, OrderBookLevel
from edgex_sdk import WebSocketManager


class RealTimeOrderFlowBot:
    """实时做市商交易机器人（原订单流机器人，已改为做市商策略）"""
    
    def __init__(self, config):
        """
        初始化机器人
        
        Args:
            config: 做市商策略配置（MarketMakerConfig 或 OrderFlowConfig）
        """
        self.config = config
        # 如果是 OrderFlowConfig，转换为 MarketMakerConfig
        if isinstance(config, OrderFlowConfig) and not isinstance(config, MarketMakerConfig):
            # 创建新的 MarketMakerConfig
            config = MarketMakerConfig(
                exchange=config.exchange,
                ticker=config.ticker,
                contract_id=config.contract_id,
                orderbook_depth=config.orderbook_depth,
                order_size=config.position_size,
                max_position=config.max_position,
                update_interval=config.update_interval,
                enable_logging=config.enable_logging
            )
        self.config = config
        self.strategy = MarketMakerStrategy(config)
        
        # WebSocket相关
        self.ws_manager = None
        self.order_book = {'bids': {}, 'asks': {}}
        self.best_bid = None
        self.best_ask = None
        self.order_book_ready = False
        
        # 运行状态
        self.running = False
        self.stop_flag = False
        self.simulate_mode = False  # 模拟模式标志
        
        # 线程安全
        self.order_book_lock = asyncio.Lock()
        self.last_orderbook_update = 0
        self._loop = None  # 事件循环引用
        
        # 日志
        self.logger = self.strategy.logger
        
        # 信号记录文件（稍后在initialize中设置）
        self.signals_csv_file = None
    
    def _setup_signals_csv(self) -> str:
        """设置信号记录CSV文件"""
        project_root = Path(__file__).parent.parent
        logs_dir = project_root / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        mode_text = "simulate" if self.simulate_mode else "live"
        timestamp = datetime.now().strftime('%Y%m%d')
        csv_file = logs_dir / f"orderflow_signals_{self.config.exchange}_{self.config.ticker}_{mode_text}_{timestamp}.csv"
        
        # 如果文件不存在，创建并写入表头
        if not csv_file.exists():
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp', 'Direction', 'Price', 'Strength', 'Position Size',
                    'Reason', 'Status', 'Confirmed'
                ])
        
        return str(csv_file)
    
    def log_signal_to_csv(self, signal, confirmed: bool = False, status: str = "GENERATED"):
        """将信号记录到CSV文件"""
        if not self.signals_csv_file:
            return
        try:
            timestamp = datetime.fromtimestamp(signal.timestamp).strftime('%Y-%m-%d %H:%M:%S')
            with open(self.signals_csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp,
                    signal.direction.upper(),
                    float(signal.price),
                    f"{signal.strength:.4f}",
                    float(self.config.position_size),
                    signal.reason,
                    status,
                    "YES" if confirmed else "NO"
                ])
        except Exception as e:
            self.logger.log(f"记录信号到CSV失败: {e}", "WARN")
    
    async def initialize(self):
        """初始化机器人"""
        try:
            # 设置信号记录CSV文件（需要在simulate_mode设置后）
            self.signals_csv_file = self._setup_signals_csv()
            
            # 初始化策略
            await self.strategy.initialize()
            
            # 获取合约信息
            if hasattr(self.strategy.exchange_client, 'get_contract_attributes'):
                contract_id, tick_size = await self.strategy.exchange_client.get_contract_attributes()
                self.config.contract_id = contract_id
                self.strategy.exchange_client.config.contract_id = contract_id
                self.strategy.exchange_client.config.tick_size = tick_size
            
            # 初始化WebSocket管理器（如果使用EdgeX）
            if self.config.exchange == 'edgex':
                import os
                account_id = os.getenv('EDGEX_ACCOUNT_ID')
                stark_private_key = os.getenv('EDGEX_STARK_PRIVATE_KEY')
                ws_url = os.getenv('EDGEX_WS_URL', 'wss://quote.edgex.exchange')
                
                if account_id and stark_private_key:
                    self.ws_manager = WebSocketManager(
                        base_url=ws_url,
                        account_id=int(account_id),
                        stark_pri_key=stark_private_key
                    )
                    await self.setup_websocket()
                else:
                    self.logger.log("警告: EdgeX WebSocket凭证未设置，将使用REST API轮询", "WARN")
            
            self.logger.log("机器人初始化成功", "INFO")
            self.logger.log(f"合约ID: {self.config.contract_id}", "INFO")
            
        except Exception as e:
            self.logger.log(f"初始化失败: {e}", "ERROR")
            raise
    
    async def setup_websocket(self):
        """设置WebSocket连接"""
        if not self.ws_manager:
            return
        
        try:
            # 保存事件循环引用
            self._loop = asyncio.get_running_loop()
            
            # 注册订单簿更新处理器
            public_client = self.ws_manager.get_public_client()
            public_client.on_message("depth", self.handle_order_book_update)
            
            # 连接公共WebSocket（用于市场数据）
            self.ws_manager.connect_public()
            self.logger.log("WebSocket连接已建立", "INFO")
            
            # 订阅订单簿深度频道
            public_client.subscribe(f"depth.{self.config.contract_id}.{self.config.orderbook_depth}")
            self.logger.log(f"已订阅订单簿深度频道: depth.{self.config.contract_id}.{self.config.orderbook_depth}", "INFO")
            
            # 等待初始订单簿数据
            await asyncio.sleep(2)  # 给WebSocket一些时间接收数据
            
        except Exception as e:
            self.logger.log(f"WebSocket设置失败: {e}", "ERROR")
            raise
    
    def handle_order_book_update(self, message):
        """处理订单簿更新消息（在WebSocket线程中调用）"""
        try:
            if isinstance(message, str):
                message = json.loads(message)
            
            # 检查是否是订单簿更新消息
            if message.get("type") == "quote-event":
                content = message.get("content", {})
                channel = message.get("channel", "")
                
                if channel.startswith("depth."):
                    data = content.get('data', [])
                    if data and len(data) > 0:
                        order_book_data = data[0]
                        depth_type = order_book_data.get('depthType', '')
                        
                        # 处理SNAPSHOT（完整数据）或CHANGED（增量更新）
                        if depth_type in ['SNAPSHOT', 'CHANGED']:
                            # 安全地将更新任务调度到事件循环（线程安全）
                            if self._loop and self._loop.is_running():
                                # 使用call_soon_threadsafe确保线程安全
                                def schedule_update():
                                    asyncio.create_task(self._async_update_orderbook(order_book_data))
                                self._loop.call_soon_threadsafe(schedule_update)
                            else:
                                # 如果事件循环未运行，直接同步更新（不推荐，但作为后备）
                                self._update_orderbook_data(order_book_data)
                            
        except Exception as e:
            self.logger.log(f"处理订单簿更新失败: {e}", "WARN")
    
    async def _async_update_orderbook(self, order_book_data):
        """异步更新订单簿（线程安全）"""
        async with self.order_book_lock:
            self._update_orderbook_data(order_book_data)
    
    def _update_orderbook_data(self, order_book_data):
        """更新订单簿数据（同步方法）"""
        try:
            # 更新买单
            bids = order_book_data.get('bids', [])
            for bid in bids:
                price = Decimal(bid['price'])
                size = Decimal(bid['size'])
                if size > 0:
                    self.order_book['bids'][price] = size
                else:
                    self.order_book['bids'].pop(price, None)
            
            # 更新卖单
            asks = order_book_data.get('asks', [])
            for ask in asks:
                price = Decimal(ask['price'])
                size = Decimal(ask['size'])
                if size > 0:
                    self.order_book['asks'][price] = size
                else:
                    self.order_book['asks'].pop(price, None)
            
            # 更新最佳买卖价
            if self.order_book['bids']:
                self.best_bid = max(self.order_book['bids'].keys())
            if self.order_book['asks']:
                self.best_ask = min(self.order_book['asks'].keys())
            
            # 标记订单簿已就绪
            if not self.order_book_ready and self.best_bid and self.best_ask:
                self.order_book_ready = True
                self.logger.log("订单簿数据已就绪", "INFO")
            
            # 更新最后更新时间
            self.last_orderbook_update = time.time()
            
            # 更新策略的订单簿
            self.update_strategy_orderbook()
            
        except Exception as e:
            self.logger.log(f"更新订单簿数据失败: {e}", "WARN")
    
    def update_strategy_orderbook(self):
        """更新策略的订单簿数据"""
        try:
            # 转换为OrderBookSnapshot格式
            bids = [OrderBookLevel(price=p, size=s, side='bid') 
                   for p, s in sorted(self.order_book['bids'].items(), reverse=True)[:self.config.orderbook_depth]]
            asks = [OrderBookLevel(price=p, size=s, side='ask') 
                   for p, s in sorted(self.order_book['asks'].items())[:self.config.orderbook_depth]]
            
            if bids and asks and self.best_bid and self.best_ask:
                snapshot = OrderBookSnapshot(
                    bids=bids,
                    asks=asks,
                    timestamp=time.time(),
                    best_bid=self.best_bid,
                    best_ask=self.best_ask
                )
                
                # 更新策略的订单簿分析器
                self.strategy.orderbook_analyzer.current_snapshot = snapshot
                
        except Exception as e:
            self.logger.log(f"更新策略订单簿失败: {e}", "WARN")
    
    async def fetch_orderbook_rest(self):
        """使用REST API获取订单簿（备用方案）"""
        try:
            bids, asks = await self.strategy.fetch_orderbook_depth()
            if bids and asks:
                snapshot = await self.strategy.update_orderbook()
                return snapshot
        except Exception as e:
            self.logger.log(f"REST API获取订单簿失败: {e}", "WARN")
        return None
    
    async def run(self):
        """运行机器人主循环"""
        self.running = True
        mode_text = "[模拟模式]" if self.simulate_mode else "[真实交易模式]"
        self.logger.log(f"做市商交易机器人开始运行 {mode_text}", "INFO")
        self.logger.log(f"交易所: {self.config.exchange}", "INFO")
        self.logger.log(f"交易对: {self.config.ticker}", "INFO")
        self.logger.log(f"更新间隔: {self.config.update_interval}秒", "INFO")
        self.logger.log(f"信号记录文件: {self.signals_csv_file}", "INFO")
        self.logger.log("=" * 80, "INFO")
        
        last_update_time = 0
        
        try:
            while self.running and not self.stop_flag:
                current_time = time.time()
                
                # 如果使用WebSocket且订单簿已就绪，直接使用WebSocket数据
                if self.ws_manager and self.order_book_ready:
                    # WebSocket数据会自动更新，只需检查是否有新数据
                    if current_time - last_update_time >= self.config.update_interval:
                        # 检查订单簿是否有更新（避免处理过期数据）
                        if current_time - self.last_orderbook_update < 5.0:  # 5秒内的数据认为是有效的
                            # 更新做市商订单
                            await self.process_signals()
                        else:
                            self.logger.log("⚠️ 订单簿数据可能已过期，跳过本次处理", "WARN")
                        last_update_time = current_time
                else:
                    # 使用REST API轮询
                    snapshot = await self.fetch_orderbook_rest()
                    if snapshot:
                        await self.process_signals()
                
                # 监控持仓
                await self.strategy.monitor_positions()
                
                # 等待下一次更新
                await asyncio.sleep(self.config.update_interval)
                
        except KeyboardInterrupt:
            self.logger.log("收到停止信号", "INFO")
        except Exception as e:
            self.logger.log(f"机器人运行错误: {e}", "ERROR")
            import traceback
            self.logger.log(traceback.format_exc(), "ERROR")
        finally:
            await self.shutdown()
    
    async def process_signals(self):
        """更新做市商订单（原订单流信号处理已改为做市商订单更新）"""
        try:
            snapshot = self.strategy.orderbook_analyzer.current_snapshot
            if snapshot:
                # 更新做市商订单
                await self.strategy.update_maker_orders(snapshot)
                
                # 记录状态
                if self.config.enable_logging:
                    mid_price = (snapshot.best_bid + snapshot.best_ask) / 2
                    spread = snapshot.best_ask - snapshot.best_bid
                    
                    self.logger.log(
                        f"中间价: {mid_price}, 价差: {spread:.4f}, "
                        f"持仓: {self.strategy.current_position}, "
                        f"买单: {self.strategy.active_buy_order.price if self.strategy.active_buy_order else 'None'}, "
                        f"卖单: {self.strategy.active_sell_order.price if self.strategy.active_sell_order else 'None'}",
                        "DEBUG"
                    )
                
        except Exception as e:
            self.logger.log(f"更新做市商订单失败: {e}", "ERROR")
    
    async def shutdown(self):
        """关闭机器人"""
        self.running = False
        self.stop_flag = True
        
        try:
            # 断开WebSocket
            if self.ws_manager:
                self.ws_manager.disconnect_all()
            
            # 关闭策略
            await self.strategy.shutdown()
            
            self.logger.log("机器人已安全关闭", "INFO")
        except Exception as e:
            self.logger.log(f"关闭时出错: {e}", "ERROR")
    
    def get_status(self):
        """获取机器人状态"""
        status = self.strategy.get_strategy_status()
        status['order_book_ready'] = self.order_book_ready
        status['best_bid'] = float(self.best_bid) if self.best_bid else None
        status['best_ask'] = float(self.best_ask) if self.best_ask else None
        return status


def main():
    """主函数"""
    import sys
    import argparse
    
    # 设置输出编码
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='做市商策略实时交易机器人（原订单流策略已改为做市商策略）')
    parser.add_argument('--exchange', type=str, default='edgex', help='交易所名称')
    parser.add_argument('--ticker', type=str, default='ETH', help='交易对')
    parser.add_argument('--position-size', type=float, default=0.1, help='每笔交易的头寸大小')
    parser.add_argument('--imbalance-threshold', type=float, default=0.6, help='失衡阈值')
    parser.add_argument('--signal-strength-threshold', type=float, default=0.7, help='信号强度阈值')
    parser.add_argument('--confirmation-ticks', type=int, default=3, help='确认所需的tick数')
    parser.add_argument('--update-interval', type=float, default=0.5, help='更新间隔（秒）')
    parser.add_argument('--max-position', type=float, default=1.0, help='最大持仓')
    parser.add_argument('--stop-loss-pct', type=float, default=0.02, help='止损百分比')
    parser.add_argument('--take-profit-pct', type=float, default=0.01, help='止盈百分比')
    parser.add_argument('--enable-logging', action='store_true', help='启用详细日志')
    parser.add_argument('--simulate', action='store_true', help='模拟模式：只跟踪信号，不实际下单')
    
    args = parser.parse_args()
    
    # 加载环境变量
    env_file = project_root / ".env"
    if env_file.exists():
        dotenv.load_dotenv(env_file)
    else:
        print("警告: 未找到 .env 文件，将使用环境变量")
    
    print("=" * 80)
    print("做市商策略 - 实时交易机器人")
    print("=" * 80)
    print()
    print("配置:")
    print(f"  - 交易所: {args.exchange}")
    print(f"  - 交易对: {args.ticker}")
    print(f"  - 头寸大小: {args.position_size}")
    print(f"  - 失衡阈值: {args.imbalance_threshold}")
    print(f"  - 信号强度阈值: {args.signal_strength_threshold}")
    print(f"  - 确认tick数: {args.confirmation_ticks}")
    print(f"  - 更新间隔: {args.update_interval}秒")
    print(f"  - 运行模式: {'[模拟模式 - 不会实际下单]' if args.simulate else '[真实交易模式 - 将使用真实资金]'}")
    print()
    if not args.simulate:
        print("警告: 这是实时交易机器人，将使用真实资金进行交易！")
    else:
        print("模拟模式: 将跟踪和分析信号，但不会实际下单")
    print("按 Ctrl+C 停止机器人")
    print("=" * 80)
    print()
    
    # 创建配置（使用做市商配置）
    config = MarketMakerConfig(
        exchange=args.exchange,
        ticker=args.ticker,
        contract_id=args.ticker,  # 将在初始化时更新
        orderbook_depth=20,
        order_size=Decimal(str(args.position_size)),
        spread_type='percentage',
        target_spread=Decimal('0.0001'),
        spread_ratio=Decimal('0.5'),
        min_spread=Decimal('0.0001'),
        max_position=Decimal(str(args.max_position)),
        inventory_skew_enabled=True,
        inventory_skew_factor=Decimal('0.3'),
        price_update_threshold=0.001,
        update_interval=args.update_interval,
        enable_logging=args.enable_logging
    )
    
    # 创建机器人
    bot = RealTimeOrderFlowBot(config)
    bot.simulate_mode = args.simulate  # 设置模拟模式
    # 同步设置策略的模拟模式
    if hasattr(bot.strategy, 'simulate_mode'):
        bot.strategy.simulate_mode = args.simulate
    
    # 设置信号处理
    def signal_handler(sig, frame):
        print("\n收到停止信号，正在关闭机器人...")
        bot.stop_flag = True
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 初始化并运行
        asyncio.run(bot.initialize())
        asyncio.run(bot.run())
    except KeyboardInterrupt:
        print("\n机器人已停止")
    except Exception as e:
        print(f"\n机器人运行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
