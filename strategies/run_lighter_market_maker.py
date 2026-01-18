#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lighter 做市商策略实时交易机器人
使用BBO数据运行做市商策略（不需要订单簿深度数据）
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
from shared.orderbook_analyzer import OrderBookSnapshot, OrderBookLevel


class LighterMarketMakerBot:
    """Lighter 做市商交易机器人（使用BBO数据）"""
    
    def __init__(self, config: MarketMakerConfig):
        """
        初始化机器人
        
        Args:
            config: 做市商策略配置
        """
        self.config = config
        self.strategy = MarketMakerStrategy(config)
        self.strategy.simulate_mode = self.simulate_mode
        
        # 运行状态
        self.running = False
        self.stop_flag = False
        self.simulate_mode = False  # 模拟模式标志
        
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
        csv_file = logs_dir / f"market_maker_signals_{self.config.exchange}_{self.config.ticker}_{mode_text}_{timestamp}.csv"
        
        # 如果文件不存在，创建并写入表头
        if not csv_file.exists():
            with open(csv_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Timestamp', 'Bid Price', 'Ask Price', 'Mid Price', 'Spread',
                    'Position', 'Buy Order ID', 'Sell Order ID', 'Status'
                ])
        
        return str(csv_file)
    
    def log_status_to_csv(self, status: dict):
        """将状态记录到CSV文件"""
        if not self.signals_csv_file:
            return
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.signals_csv_file, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    timestamp,
                    float(status.get('bid_price', 0)),
                    float(status.get('ask_price', 0)),
                    float(status.get('mid_price', 0)),
                    float(status.get('spread', 0)),
                    float(status.get('position', 0)),
                    status.get('buy_order_id', ''),
                    status.get('sell_order_id', ''),
                    status.get('status', '')
                ])
        except Exception as e:
            self.logger.log(f"记录状态到CSV失败: {e}", "WARN")
    
    async def initialize(self):
        """初始化机器人"""
        try:
            # 设置信号记录CSV文件
            self.signals_csv_file = self._setup_signals_csv()
            
            # 初始化策略
            await self.strategy.initialize()
            
            # 获取合约信息
            if hasattr(self.strategy.exchange_client, 'get_contract_attributes'):
                contract_id, tick_size = await self.strategy.exchange_client.get_contract_attributes()
                self.config.contract_id = contract_id
                self.strategy.exchange_client.config.contract_id = contract_id
                self.strategy.exchange_client.config.tick_size = tick_size
            
            self.logger.log("机器人初始化成功", "INFO")
            self.logger.log(f"合约ID: {self.config.contract_id}", "INFO")
            self.logger.log("使用BBO数据运行（不需要订单簿深度）", "INFO")
            
        except Exception as e:
            self.logger.log(f"初始化失败: {e}", "ERROR")
            raise
    
    async def fetch_bbo_and_update_orderbook(self):
        """使用BBO数据更新订单簿"""
        try:
            best_bid, best_ask = await self.strategy.exchange_client.fetch_bbo_prices(self.config.contract_id)
            
            if best_bid > 0 and best_ask > 0:
                # 创建最小订单簿快照（只需要best_bid和best_ask）
                bids = [OrderBookLevel(price=best_bid, size=Decimal(100), side='bid')]
                asks = [OrderBookLevel(price=best_ask, size=Decimal(100), side='ask')]
                
                snapshot = OrderBookSnapshot(
                    bids=bids,
                    asks=asks,
                    timestamp=time.time(),
                    best_bid=best_bid,
                    best_ask=best_ask
                )
                
                # 更新策略的订单簿分析器
                self.strategy.orderbook_analyzer.current_snapshot = snapshot
                
                return snapshot
        except Exception as e:
            self.logger.log(f"获取BBO数据失败: {e}", "WARN")
        return None
    
    async def run(self):
        """运行机器人主循环"""
        self.running = True
        mode_text = "[模拟模式]" if self.simulate_mode else "[真实交易模式]"
        self.logger.log(f"Lighter 做市商交易机器人开始运行 {mode_text}", "INFO")
        self.logger.log(f"交易所: {self.config.exchange}", "INFO")
        self.logger.log(f"交易对: {self.config.ticker}", "INFO")
        self.logger.log(f"订单大小: {self.config.order_size}", "INFO")
        self.logger.log(f"价差类型: {self.config.spread_type}", "INFO")
        self.logger.log(f"更新间隔: {self.config.update_interval}秒", "INFO")
        self.logger.log(f"状态记录文件: {self.signals_csv_file}", "INFO")
        self.logger.log("=" * 80, "INFO")
        
        last_update_time = 0
        
        try:
            while self.running and not self.stop_flag:
                current_time = time.time()
                
                # 使用BBO数据更新订单簿
                if current_time - last_update_time >= self.config.update_interval:
                    snapshot = await self.fetch_bbo_and_update_orderbook()
                    if snapshot:
                        # 更新做市商订单
                        await self.strategy.update_maker_orders(snapshot)
                        # 记录状态
                        await self.log_status()
                    last_update_time = current_time
                
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
    
    async def log_status(self):
        """记录状态"""
        try:
            snapshot = self.strategy.orderbook_analyzer.current_snapshot
            if snapshot:
                mid_price = (snapshot.best_bid + snapshot.best_ask) / 2
                spread = snapshot.best_ask - snapshot.best_bid
                
                status = {
                    'bid_price': float(self.strategy.active_buy_order.price) if self.strategy.active_buy_order else 0,
                    'ask_price': float(self.strategy.active_sell_order.price) if self.strategy.active_sell_order else 0,
                    'mid_price': float(mid_price),
                    'spread': float(spread),
                    'position': float(self.strategy.current_position),
                    'buy_order_id': self.strategy.active_buy_order.order_id if self.strategy.active_buy_order else '',
                    'sell_order_id': self.strategy.active_sell_order.order_id if self.strategy.active_sell_order else '',
                    'status': 'ACTIVE'
                }
                
                self.log_status_to_csv(status)
                
                if self.config.enable_logging:
                    self.logger.log(
                        f"中间价: {mid_price}, 价差: {spread:.4f}, "
                        f"持仓: {self.strategy.current_position}, "
                        f"买单: {status['bid_price']}, 卖单: {status['ask_price']}",
                        "DEBUG"
                    )
        except Exception as e:
            self.logger.log(f"记录状态失败: {e}", "WARN")
    
    async def shutdown(self):
        """关闭机器人"""
        self.running = False
        self.stop_flag = True
        
        try:
            # 关闭策略
            await self.strategy.shutdown()
            
            self.logger.log("机器人已安全关闭", "INFO")
        except Exception as e:
            self.logger.log(f"关闭时出错: {e}", "ERROR")
    
    def get_status(self):
        """获取机器人状态"""
        status = self.strategy.get_strategy_status()
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
    parser = argparse.ArgumentParser(description='Lighter 做市商策略实时交易机器人（使用BBO数据）')
    parser.add_argument('--ticker', type=str, default='ETH', help='交易对')
    parser.add_argument('--order-size', type=float, default=0.1, help='每笔订单的大小')
    parser.add_argument('--spread-type', type=str, default='percentage', choices=['fixed', 'percentage'], help='价差类型')
    parser.add_argument('--target-spread', type=float, default=0.0001, help='目标价差（固定价差时使用）')
    parser.add_argument('--spread-ratio', type=float, default=0.5, help='价差比例（市场价差的百分比）')
    parser.add_argument('--min-spread', type=float, default=0.0001, help='最小价差')
    parser.add_argument('--max-position', type=float, default=1.0, help='最大持仓')
    parser.add_argument('--inventory-skew-enabled', action='store_true', default=True, help='启用库存倾斜')
    parser.add_argument('--inventory-skew-factor', type=float, default=0.3, help='库存倾斜因子')
    parser.add_argument('--price-update-threshold', type=float, default=0.001, help='价格更新阈值')
    parser.add_argument('--update-interval', type=float, default=0.5, help='更新间隔（秒）')
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
    print("Lighter 做市商策略 - 实时交易机器人（使用BBO数据）")
    print("=" * 80)
    print()
    print("配置:")
    print(f"  - 交易所: lighter")
    print(f"  - 交易对: {args.ticker}")
    print(f"  - 订单大小: {args.order_size}")
    print(f"  - 价差类型: {args.spread_type}")
    print(f"  - 目标价差: {args.target_spread}")
    print(f"  - 价差比例: {args.spread_ratio}")
    print(f"  - 最大持仓: {args.max_position}")
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
    
    # 创建配置
    config = MarketMakerConfig(
        exchange='lighter',
        ticker=args.ticker,
        contract_id=args.ticker,  # 将在初始化时更新
        orderbook_depth=1,  # 只需要1层（BBO数据）
        order_size=Decimal(str(args.order_size)),
        spread_type=args.spread_type,
        target_spread=Decimal(str(args.target_spread)),
        spread_ratio=Decimal(str(args.spread_ratio)),
        min_spread=Decimal(str(args.min_spread)),
        max_position=Decimal(str(args.max_position)),
        inventory_skew_enabled=args.inventory_skew_enabled,
        inventory_skew_factor=Decimal(str(args.inventory_skew_factor)),
        price_update_threshold=args.price_update_threshold,
        update_interval=args.update_interval,
        enable_logging=args.enable_logging
    )
    
    # 创建机器人
    bot = LighterMarketMakerBot(config)
    bot.simulate_mode = args.simulate  # 设置模拟模式
    bot.strategy.simulate_mode = args.simulate  # 同步设置策略的模拟模式
    
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
