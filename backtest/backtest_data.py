"""
回测数据模型

定义历史数据的结构和加载方法
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import List, Optional, Dict, Tuple
from datetime import datetime
import json
import csv
import time
from pathlib import Path


@dataclass
class HistoricalOrderBook:
    """历史订单簿快照"""
    timestamp: float
    bids: List[Tuple[Decimal, Decimal]]  # [(price, size), ...]
    asks: List[Tuple[Decimal, Decimal]]  # [(price, size), ...]
    best_bid: Decimal
    best_ask: Decimal
    
    @property
    def mid_price(self) -> Decimal:
        """中间价"""
        return (self.best_bid + self.best_ask) / 2


@dataclass
class HistoricalTrade:
    """历史交易记录"""
    timestamp: float
    price: Decimal
    size: Decimal
    side: str  # 'buy' or 'sell'
    trade_id: Optional[str] = None
    
    @property
    def value(self) -> Decimal:
        """交易价值"""
        return self.price * self.size


@dataclass
class BacktestData:
    """回测数据集"""
    orderbooks: List[HistoricalOrderBook]
    trades: List[HistoricalTrade]
    start_time: float
    end_time: float
    
    def __len__(self) -> int:
        return len(self.orderbooks)
    
    def get_orderbook_at(self, timestamp: float) -> Optional[HistoricalOrderBook]:
        """获取指定时间点的订单簿"""
        # 找到最接近的订单簿
        closest = None
        min_diff = float('inf')
        
        for ob in self.orderbooks:
            diff = abs(ob.timestamp - timestamp)
            if diff < min_diff:
                min_diff = diff
                closest = ob
        
        return closest
    
    def get_trades_in_range(self, start: float, end: float) -> List[HistoricalTrade]:
        """获取时间范围内的交易"""
        return [t for t in self.trades if start <= t.timestamp <= end]


class BacktestDataLoader:
    """回测数据加载器"""
    
    @staticmethod
    async def load_from_exchange_api(
        exchange: str,
        ticker: str,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        duration_seconds: Optional[float] = None,
        interval_seconds: float = 1.0,
        save_to_file: Optional[str] = None
    ) -> BacktestData:
        """
        从交易所API实时收集数据
        
        ⚠️ 重要说明：
        大多数交易所不提供历史订单簿数据API，此方法实际上是实时收集当前数据。
        如果指定了历史时间范围，将使用当前时间替代。
        
        Args:
            exchange: 交易所名称
            ticker: 交易对符号
            start_time: 开始时间戳（如果为None，使用当前时间）
            end_time: 结束时间戳（如果为None，使用当前时间+duration_seconds）
            duration_seconds: 收集时长（秒），如果end_time为None时使用
            interval_seconds: 数据采样间隔（秒）
            save_to_file: 保存数据到文件（可选）
        
        Returns:
            BacktestData: 回测数据
        """
        import asyncio
        from exchanges import ExchangeFactory
        
        # 创建交易所客户端
        exchange_config = {
            'contract_id': ticker,
            'ticker': ticker,
            'tick_size': Decimal('0.01'),
        }
        
        try:
            client = ExchangeFactory.create_exchange(exchange, exchange_config)
            await client.connect()
            
            # 确定时间范围
            current_real_time = time.time()
            if start_time is None:
                start_time = current_real_time
            if end_time is None:
                if duration_seconds:
                    end_time = start_time + duration_seconds
                else:
                    end_time = start_time + 60  # 默认收集60秒
            
            # 如果指定的时间范围是历史时间，使用当前时间
            if start_time < current_real_time:
                print(f"⚠️  警告: 指定的开始时间 {start_time} 是历史时间")
                print(f"⚠️  交易所不提供历史订单簿数据，将使用当前时间开始收集")
                start_time = current_real_time
                if end_time < current_real_time:
                    end_time = start_time + (end_time - start_time) if duration_seconds else start_time + 60
            
            orderbooks = []
            trades = []
            current_time = start_time
            sample_count = 0
            total_samples = int((end_time - start_time) / interval_seconds)
            
            print(f"从 {exchange} 实时收集数据: {ticker}")
            print(f"时间范围: {datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')} - "
                  f"{datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"预计收集 {total_samples} 个样本，间隔 {interval_seconds} 秒")
            print(f"开始收集...")
            
            while current_time < end_time and time.time() < end_time:
                try:
                    # 获取当前订单簿
                    best_bid, best_ask = await client.fetch_bbo_prices(ticker)
                    
                    if best_bid > 0 and best_ask > 0:
                        # 尝试获取订单簿深度（如果支持）
                        try:
                            # 这里可以尝试获取深度数据
                            # 目前使用简化的订单簿（只有最佳买卖价）
                            bids = [(best_bid, Decimal(100))]  # 模拟数量
                            asks = [(best_ask, Decimal(100))]
                        except:
                            bids = [(best_bid, Decimal(100))]
                            asks = [(best_ask, Decimal(100))]
                        
                        orderbooks.append(HistoricalOrderBook(
                            timestamp=time.time(),  # 使用实际时间戳
                            bids=bids,
                            asks=asks,
                            best_bid=best_bid,
                            best_ask=best_ask
                        ))
                        
                        sample_count += 1
                        if sample_count % 10 == 0:
                            progress = (time.time() - start_time) / (end_time - start_time) * 100
                            print(f"进度: {progress:.1f}% ({sample_count}/{total_samples} 样本)")
                    
                    await asyncio.sleep(interval_seconds)
                    current_time = time.time()
                    
                except Exception as e:
                    print(f"获取数据时出错: {e}")
                    await asyncio.sleep(1)
            
            await client.disconnect()
            
            if not orderbooks:
                raise ValueError("未能获取到订单簿数据")
            
            # 更新实际时间范围
            actual_start = min(ob.timestamp for ob in orderbooks)
            actual_end = max(ob.timestamp for ob in orderbooks)
            
            print(f"\n✅ 数据收集完成: {len(orderbooks)} 个订单簿快照")
            print(f"实际时间范围: {datetime.fromtimestamp(actual_start).strftime('%Y-%m-%d %H:%M:%S')} - "
                  f"{datetime.fromtimestamp(actual_end).strftime('%Y-%m-%d %H:%M:%S')}")
            
            data = BacktestData(
                orderbooks=orderbooks,
                trades=trades,
                start_time=actual_start,
                end_time=actual_end
            )
            
            # 保存到文件
            if save_to_file:
                BacktestDataLoader.save_to_json(data, save_to_file)
                print(f"✅ 数据已保存到: {save_to_file}")
            
            return data
            
        except Exception as e:
            raise ValueError(f"从交易所API获取数据失败: {e}. "
                           f"建议使用本地数据文件或第三方数据服务。")
    
    @staticmethod
    def save_to_json(data: 'BacktestData', file_path: str):
        """保存回测数据到JSON文件"""
        output = {
            'orderbooks': [],
            'trades': []
        }
        
        for ob in data.orderbooks:
            output['orderbooks'].append({
                'timestamp': ob.timestamp,
                'bids': [[float(price), float(size)] for price, size in ob.bids],
                'asks': [[float(price), float(size)] for price, size in ob.asks]
            })
        
        for trade in data.trades:
            output['trades'].append({
                'timestamp': trade.timestamp,
                'price': float(trade.price),
                'size': float(trade.size),
                'side': trade.side,
                'trade_id': trade.trade_id
            })
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2)
    
    @staticmethod
    def load_from_json(file_path: str) -> BacktestData:
        """
        从JSON文件加载回测数据
        
        JSON格式:
        {
            "orderbooks": [
                {
                    "timestamp": 1234567890.0,
                    "bids": [[price, size], ...],
                    "asks": [[price, size], ...]
                },
                ...
            ],
            "trades": [
                {
                    "timestamp": 1234567890.0,
                    "price": 2000.0,
                    "size": 0.1,
                    "side": "buy"
                },
                ...
            ]
        }
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        orderbooks = []
        for ob_data in data.get('orderbooks', []):
            bids = [(Decimal(str(b[0])), Decimal(str(b[1]))) for b in ob_data['bids']]
            asks = [(Decimal(str(a[0])), Decimal(str(a[1]))) for a in ob_data['asks']]
            
            best_bid = max(bids, key=lambda x: x[0])[0] if bids else Decimal(0)
            best_ask = min(asks, key=lambda x: x[0])[0] if asks else Decimal(0)
            
            orderbooks.append(HistoricalOrderBook(
                timestamp=ob_data['timestamp'],
                bids=bids,
                asks=asks,
                best_bid=best_bid,
                best_ask=best_ask
            ))
        
        trades = []
        for trade_data in data.get('trades', []):
            trades.append(HistoricalTrade(
                timestamp=trade_data['timestamp'],
                price=Decimal(str(trade_data['price'])),
                size=Decimal(str(trade_data['size'])),
                side=trade_data['side'],
                trade_id=trade_data.get('trade_id')
            ))
        
        if not orderbooks:
            raise ValueError("订单簿数据为空")
        
        start_time = min(ob.timestamp for ob in orderbooks)
        end_time = max(ob.timestamp for ob in orderbooks)
        
        return BacktestData(
            orderbooks=orderbooks,
            trades=trades,
            start_time=start_time,
            end_time=end_time
        )
    
    @staticmethod
    def load_from_csv(orderbook_file: str, trades_file: Optional[str] = None) -> BacktestData:
        """
        从CSV文件加载回测数据
        
        Orderbook CSV格式:
        timestamp,bid_price,bid_size,ask_price,ask_size
        
        Trades CSV格式:
        timestamp,price,size,side
        """
        orderbooks = []
        
        # 加载订单簿数据
        with open(orderbook_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                timestamp = float(row['timestamp'])
                bid_price = Decimal(row['bid_price'])
                bid_size = Decimal(row['bid_size'])
                ask_price = Decimal(row['ask_price'])
                ask_size = Decimal(row['ask_size'])
                
                orderbooks.append(HistoricalOrderBook(
                    timestamp=timestamp,
                    bids=[(bid_price, bid_size)],
                    asks=[(ask_price, ask_size)],
                    best_bid=bid_price,
                    best_ask=ask_price
                ))
        
        # 加载交易数据（如果提供）
        trades = []
        if trades_file and Path(trades_file).exists():
            with open(trades_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    trades.append(HistoricalTrade(
                        timestamp=float(row['timestamp']),
                        price=Decimal(row['price']),
                        size=Decimal(row['size']),
                        side=row['side']
                    ))
        
        if not orderbooks:
            raise ValueError("订单簿数据为空")
        
        start_time = min(ob.timestamp for ob in orderbooks)
        end_time = max(ob.timestamp for ob in orderbooks)
        
        return BacktestData(
            orderbooks=orderbooks,
            trades=trades,
            start_time=start_time,
            end_time=end_time
        )
    
    @staticmethod
    def generate_mock_data(
        start_price: Decimal,
        num_samples: int = 1000,
        interval_seconds: float = 1.0,
        volatility: float = 0.001
    ) -> BacktestData:
        """
        生成模拟回测数据（用于测试）
        
        Args:
            start_price: 起始价格
            num_samples: 样本数量
            interval_seconds: 时间间隔（秒）
            volatility: 价格波动率
        """
        import random
        import time
        
        current_price = start_price
        base_time = time.time() - (num_samples * interval_seconds)
        
        orderbooks = []
        trades = []
        
        for i in range(num_samples):
            timestamp = base_time + i * interval_seconds
            
            # 随机价格波动
            change = Decimal(random.uniform(-volatility, volatility))
            current_price = current_price * (1 + change)
            
            # 生成订单簿
            spread = current_price * Decimal(0.0001)  # 0.01% spread
            best_bid = current_price - spread / 2
            best_ask = current_price + spread / 2
            
            bids = [(best_bid, Decimal(random.uniform(10, 100)))]
            asks = [(best_ask, Decimal(random.uniform(10, 100)))]
            
            orderbooks.append(HistoricalOrderBook(
                timestamp=timestamp,
                bids=bids,
                asks=asks,
                best_bid=best_bid,
                best_ask=best_ask
            ))
            
            # 随机生成一些交易
            if random.random() < 0.3:  # 30%概率有交易
                side = 'buy' if random.random() > 0.5 else 'sell'
                size = Decimal(random.uniform(0.01, 1.0))
                price = best_ask if side == 'buy' else best_bid
                
                trades.append(HistoricalTrade(
                    timestamp=timestamp,
                    price=price,
                    size=size,
                    side=side
                ))
        
        return BacktestData(
            orderbooks=orderbooks,
            trades=trades,
            start_time=orderbooks[0].timestamp,
            end_time=orderbooks[-1].timestamp
        )
