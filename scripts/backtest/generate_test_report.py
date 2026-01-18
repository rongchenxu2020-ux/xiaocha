#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
订单流策略测试报告生成器
使用真实API数据收集并生成测试报告
"""

import sys
import asyncio
import time
from pathlib import Path
from decimal import Decimal
from datetime import datetime
import dotenv

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from exchanges import ExchangeFactory
from booking.config import OrderFlowConfig
from booking.backtest_data import BacktestData, HistoricalOrderBook, HistoricalTrade, BacktestDataLoader
from booking.backtest_engine import BacktestEngine
from booking.backtest_report import BacktestReportGenerator


async def collect_api_data(exchange: str, ticker: str, duration_seconds: int = 60, interval: float = 1.0):
    """从API收集实时数据"""
    print(f"开始从 {exchange} 收集 {ticker} 的数据...")
    print(f"收集时长: {duration_seconds} 秒, 采样间隔: {interval} 秒")
    print()
    
    # 加载环境变量
    env_file = project_root / ".env"
    if env_file.exists():
        dotenv.load_dotenv(env_file)
    else:
        print("警告: 未找到 .env 文件，将使用环境变量")
        print()
    
    # 创建交易所配置
    exchange_config = {
        'contract_id': ticker,
        'ticker': ticker,
        'tick_size': Decimal('0.01'),
        'quantity': Decimal('0.1'),
    }
    
    # 创建配置对象类
    class SimpleConfig:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    # 临时修改BaseExchangeClient来接受对象
    from exchanges.base import BaseExchangeClient
    original_init = BaseExchangeClient.__init__
    def patched_init(self, config):
        if isinstance(config, dict):
            self.config = SimpleConfig(**config)
        else:
            self.config = config
        self._validate_config()
    
    # 应用补丁
    BaseExchangeClient.__init__ = patched_init
    
    # 尝试创建交易所客户端，如果失败则尝试其他交易所
    client = None
    used_exchange = exchange
    
    # 支持的交易所列表（按优先级）- 只尝试edgex和lighter
    allowed_exchanges = ['edgex', 'lighter']
    exchanges_to_try = [exchange] if exchange in allowed_exchanges else []
    # 如果指定的交易所不在允许列表中，添加允许的交易所
    if not exchanges_to_try:
        exchanges_to_try = [e for e in allowed_exchanges]
    else:
        # 添加其他允许的交易所作为备选
        exchanges_to_try.extend([e for e in allowed_exchanges if e != exchange])
    
    try:
        for ex in exchanges_to_try:
            try:
                print(f"尝试连接 {ex} 交易所...")
                client = ExchangeFactory.create_exchange(ex, exchange_config)
                await client.connect()
                used_exchange = ex
                print(f"成功连接到 {ex} 交易所")
                print()
                break
            except ImportError as e:
                print(f"  {ex} 不可用: {e}")
                continue
            except Exception as e:
                print(f"  {ex} 连接失败: {e}")
                continue
    finally:
        # 恢复原始方法
        BaseExchangeClient.__init__ = original_init
    
    if client is None:
        print("\n错误: 无法连接到任何交易所")
        print("\n请检查:")
        print("1. 是否已安装所需的依赖包")
        print("2. .env 文件是否配置正确")
        print("3. API密钥是否有效")
        raise ValueError("无法连接到任何交易所")
    
    # 开始收集数据
    orderbooks = []
    start_time = time.time()
    end_time = start_time + duration_seconds
    sample_count = 0
    
    print("正在收集数据...")
    
    try:
        # 对于EdgeX，需要先获取contract_id
        contract_id = ticker
        if used_exchange == 'edgex':
            try:
                contract_id, tick_size = await client.get_contract_attributes()
                print(f"   获取到合约ID: {contract_id}")
                client.config.contract_id = contract_id
                client.config.tick_size = tick_size
            except Exception as e:
                print(f"   获取合约ID失败，使用ticker: {e}")
        
        while time.time() < end_time:
            try:
                # 获取订单簿（尝试获取深度数据）
                best_bid, best_ask = await client.fetch_bbo_prices(contract_id)
                
                if best_bid > 0 and best_ask > 0:
                    # 尝试获取完整的订单簿深度
                    bids = []
                    asks = []
                    
                    if used_exchange == 'edgex':
                        try:
                            from edgex_sdk import GetOrderBookDepthParams
                            depth_params = GetOrderBookDepthParams(
                                contract_id=contract_id, 
                                limit=20  # 获取20层深度
                            )
                            order_book = await client.client.quote.get_order_book_depth(depth_params)
                            order_book_data = order_book.get('data', [])
                            if order_book_data:
                                entry = order_book_data[0]
                                bids = [(Decimal(level['price']), Decimal(level['size'])) 
                                        for level in entry.get('bids', [])]
                                asks = [(Decimal(level['price']), Decimal(level['size'])) 
                                        for level in entry.get('asks', [])]
                        except Exception as e:
                            # 如果获取深度失败，使用最佳买卖价
                            bids = [(best_bid, Decimal(100))]
                            asks = [(best_ask, Decimal(100))]
                    else:
                        # 其他交易所：使用最佳买卖价
                        bids = [(best_bid, Decimal(100))]
                        asks = [(best_ask, Decimal(100))]
                    
                    # 创建订单簿快照
                    orderbook = HistoricalOrderBook(
                        timestamp=time.time(),
                        bids=bids,
                        asks=asks,
                        best_bid=best_bid,
                        best_ask=best_ask
                    )
                    orderbooks.append(orderbook)
                    sample_count += 1
                    
                    if sample_count % 10 == 0:
                        elapsed = time.time() - start_time
                        remaining = duration_seconds - elapsed
                        progress = (elapsed / duration_seconds) * 100
                        remaining_min = int(remaining / 60)
                        remaining_sec = int(remaining % 60)
                        print(f"  进度: {progress:.1f}% | 已收集 {sample_count} 个样本 | 剩余时间: {remaining_min}分{remaining_sec}秒")
                
                await asyncio.sleep(interval)
                
            except Exception as e:
                print(f"  获取数据时出错: {e}")
                await asyncio.sleep(1)
        
        await client.disconnect()
        
        if not orderbooks:
            raise ValueError("未能收集到任何数据")
        
        # 创建回测数据
        data = BacktestData(
            orderbooks=orderbooks,
            trades=[],  # 暂时没有交易数据
            start_time=orderbooks[0].timestamp,
            end_time=orderbooks[-1].timestamp
        )
        
        print(f"\n数据收集完成: {len(orderbooks)} 个订单簿快照")
        print(f"使用的交易所: {used_exchange}")
        print(f"时间范围: {datetime.fromtimestamp(data.start_time).strftime('%Y-%m-%d %H:%M:%S')} - "
              f"{datetime.fromtimestamp(data.end_time).strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        return data, used_exchange
        
    except Exception as e:
        print(f"数据收集失败: {e}")
        import traceback
        traceback.print_exc()
        raise


def main():
    """主函数"""
    import sys
    # 设置输出编码
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    
    print("=" * 80)
    print("订单流策略 - API数据测试报告生成器")
    print("=" * 80)
    print()
    
    # 配置参数（可以根据需要修改）
    # 注意：请根据你已配置的API选择交易所
    # 当前仅支持: edgex, lighter
    exchange = 'edgex'  # 使用 EdgeX（优先尝试，如果失败会尝试lighter）
    ticker = 'ETH'
    
    # 数据源选择：使用历史数据文件或从API实时收集
    # 如果指定了历史数据文件，将从文件加载；否则从API收集
    historical_data_file = "booking/historical_data_1500.json"  # 设置为None从API收集真实数据，或指定JSON文件路径使用历史数据
    
    # 如果使用API收集数据，以下参数生效
    duration_seconds = 3600  # 收集1小时数据（3600秒）
    interval = 1.0  # 每秒采样一次
    save_collected_data = True  # 是否保存收集的数据到文件
    
    print(f"配置:")
    print(f"  - 交易所: {exchange}")
    print(f"  - 交易对: {ticker}")
    if historical_data_file:
        print(f"  - 数据源: 历史数据文件 ({historical_data_file})")
    else:
        print(f"  - 数据源: API实时收集")
        print(f"  - 收集时长: {duration_seconds} 秒 ({duration_seconds/60:.1f} 分钟)")
        print(f"  - 保存数据: {'是' if save_collected_data else '否'}")
    print()
    
    # 策略参数（快速测试模式 - 大幅降低阈值以便生成信号）
    # 注意：这些是测试参数，实际交易时应使用更严格的阈值
    imbalance_threshold = 0.1  # 从0.6降低到0.1 (10%) - 更容易触发
    signal_strength_threshold = 0.3  # 从0.7降低到0.3 (30%) - 更容易生成信号
    confirmation_ticks = 1  # 从3降低到1 - 不需要连续确认，立即执行
    position_size = Decimal(0.1)
    
    try:
        # 1. 加载数据（从文件或API）
        if historical_data_file:
            print("步骤1: 从历史数据文件加载数据")
            print("-" * 80)
            data_file_path = project_root / historical_data_file
            if not data_file_path.exists():
                raise FileNotFoundError(f"历史数据文件不存在: {data_file_path}")
            
            print(f"正在加载历史数据: {data_file_path}")
            data = BacktestDataLoader.load_from_json(str(data_file_path))
            actual_exchange = exchange  # 使用配置的交易所名称
            print(f"✅ 成功加载历史数据: {len(data.orderbooks)} 个订单簿快照")
            if data.trades:
                print(f"✅ 包含 {len(data.trades)} 笔交易记录")
            print(f"时间范围: {datetime.fromtimestamp(data.start_time).strftime('%Y-%m-%d %H:%M:%S')} - "
                  f"{datetime.fromtimestamp(data.end_time).strftime('%Y-%m-%d %H:%M:%S')}")
            print()
        else:
            print("步骤1: 从API收集真实数据")
            print("-" * 80)
            data, actual_exchange = asyncio.run(collect_api_data(exchange, ticker, duration_seconds, interval))
            
            # 如果启用保存，保存收集的数据
            if save_collected_data:
                output_dir = project_root / "booking"
                output_dir.mkdir(exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                data_file = output_dir / f"real_data_{actual_exchange}_{ticker}_{timestamp}.json"
                BacktestDataLoader.save_to_json(data, str(data_file))
                print(f"✅ 真实数据已保存到: {data_file}")
                print(f"   下次可以使用此文件进行回测: historical_data_file = \"{data_file.relative_to(project_root)}\"")
                print()
        
        # 2. 配置策略
        print("步骤2: 配置策略参数")
        print("-" * 80)
        config = OrderFlowConfig(
            exchange=actual_exchange,
            ticker=ticker,
            contract_id=ticker,
            orderbook_depth=20,
            imbalance_threshold=imbalance_threshold,
            min_order_size=Decimal(10000),
            large_order_threshold=Decimal(50000),
            trade_flow_window=60,
            signal_strength_threshold=signal_strength_threshold,
            confirmation_ticks=confirmation_ticks,
            position_size=position_size,
            max_position=Decimal(1.0),
            stop_loss_pct=Decimal(0.02),
            take_profit_pct=Decimal(0.01),
            max_orders_per_minute=5,
            max_daily_loss=None,
            update_interval=0.5,
            enable_logging=False
        )
        print("策略配置:")
        print(f"  - 交易所: {actual_exchange}")
        print(f"  - 交易对: {ticker}")
        print(f"  - 失衡阈值: {imbalance_threshold} (快速测试模式)")
        print(f"  - 信号强度阈值: {signal_strength_threshold} (快速测试模式)")
        print(f"  - 确认tick数: {confirmation_ticks} (快速测试模式)")
        print(f"  - 持仓大小: {position_size}")
        print("  ⚠️  注意: 当前使用快速测试参数，实际交易时应使用更严格的阈值")
        print()
        
        # 3. 运行回测
        print("步骤3: 运行回测")
        print("-" * 80)
        engine = BacktestEngine(config, initial_balance=Decimal(10000))
        result = engine.run(data)
        print()
        
        # 4. 生成报告
        print("步骤4: 生成测试报告")
        print("-" * 80)
        
        # 保存报告
        output_dir = project_root / "backtest_results"
        output_dir.mkdir(exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = output_dir / f"test_report_{actual_exchange}_{ticker}_{timestamp}.txt"
        
        report_text = BacktestReportGenerator.generate_text_report(result, str(report_file))
        print(report_text)
        
        # 导出数据
        trades_file = output_dir / f"trades_{actual_exchange}_{ticker}_{timestamp}.csv"
        equity_file = output_dir / f"equity_{actual_exchange}_{ticker}_{timestamp}.csv"
        
        BacktestReportGenerator.export_trades_to_csv(result, str(trades_file))
        BacktestReportGenerator.export_equity_curve_to_csv(result, str(equity_file))
        
        print()
        print("=" * 80)
        print("测试报告生成完成！")
        print(f"报告文件: {report_file}")
        print(f"交易记录: {trades_file}")
        print(f"权益曲线: {equity_file}")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
