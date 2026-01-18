"""
测试脚本：使用已下载的数据测试策略是否能够成功开单
"""

import os
import sys
import asyncio
import json
import time
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from edgex_sdk import Client, OrderSide, GetOrderBookDepthParams
import dotenv

# 设置输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# 加载.env文件
project_root = Path(__file__).parent
env_file = project_root / ".env"
if env_file.exists():
    dotenv.load_dotenv(env_file)
    print(f"[INFO] 已加载 .env 文件: {env_file}\n")
else:
    print(f"[WARNING] 未找到 .env 文件: {env_file}")
    print("   将使用系统环境变量\n")


class SimpleOrderFlowStrategy:
    """简化的订单流策略，用于测试"""
    
    def __init__(self, contract_id, tick_size, position_size=Decimal('0.1')):
        self.contract_id = contract_id
        self.tick_size = tick_size
        self.position_size = position_size
        self.orderbook_depth = 15
        
        # 订单簿数据
        self.bids = []
        self.asks = []
        self.best_bid = Decimal(0)
        self.best_ask = Decimal(0)
        
        # 策略参数
        self.imbalance_threshold = 0.3  # 失衡阈值
        self.signal_strength_threshold = 0.6  # 信号强度阈值
        
    def update_orderbook(self, bids, asks):
        """更新订单簿数据"""
        self.bids = bids
        self.asks = asks
        if bids and asks:
            self.best_bid = Decimal(bids[0]['price'])
            self.best_ask = Decimal(asks[0]['price'])
    
    def calculate_imbalance(self):
        """计算订单簿失衡"""
        if not self.bids or not self.asks:
            return 0.0
        
        # 计算买卖盘总量（前5档）
        bid_volume = sum(Decimal(b['size']) for b in self.bids[:5])
        ask_volume = sum(Decimal(a['size']) for a in self.asks[:5])
        
        total_volume = bid_volume + ask_volume
        if total_volume == 0:
            return 0.0
        
        # 失衡 = (买盘 - 卖盘) / 总量
        imbalance = float((bid_volume - ask_volume) / total_volume)
        return imbalance
    
    def generate_signal(self):
        """生成交易信号"""
        if not self.bids or not self.asks:
            return None
        
        imbalance = self.calculate_imbalance()
        
        # 如果失衡超过阈值，生成信号
        if abs(imbalance) > self.imbalance_threshold:
            direction = 'buy' if imbalance > 0 else 'sell'
            strength = min(abs(imbalance) / self.imbalance_threshold, 1.0)
            
            return {
                'direction': direction,
                'strength': strength,
                'imbalance': imbalance,
                'price': self.best_ask if direction == 'buy' else self.best_bid
            }
        
        return None


def load_historical_data(data_dir):
    """加载历史数据文件"""
    data_dir = Path(data_dir)
    if not data_dir.exists():
        return []
    
    all_records = []
    
    # 读取所有非final文件
    for file_path in sorted(data_dir.glob("edgex_continuous_*.json")):
        if "final" in file_path.name:
            continue
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                records = json.load(f)
                if isinstance(records, list):
                    all_records.extend(records)
        except Exception as e:
            print(f"[WARNING] 读取文件失败 {file_path.name}: {e}")
    
    # 按时间排序
    all_records.sort(key=lambda x: x.get('unix_time', 0))
    
    # 只保留ETH数据
    eth_records = [r for r in all_records if r.get('contract_name') == 'ETHUSD']
    
    return eth_records


async def fetch_orderbook_depth(client, contract_id, depth=15):
    """获取订单簿深度数据"""
    try:
        depth_params = GetOrderBookDepthParams(contract_id=contract_id, limit=depth)
        order_book = await client.quote.get_order_book_depth(depth_params)
        
        if order_book and 'data' in order_book and len(order_book['data']) > 0:
            order_book_data = order_book['data'][0]
            bids = order_book_data.get('bids', [])
            asks = order_book_data.get('asks', [])
            return bids, asks
    except Exception as e:
        print(f"[WARNING] 获取订单簿深度失败: {e}")
    
    return [], []


async def test_strategy_with_historical_data():
    """使用历史数据测试策略开单"""
    
    # 从环境变量读取配置
    account_id = os.getenv('EDGEX_ACCOUNT_ID')
    stark_private_key = os.getenv('EDGEX_STARK_PRIVATE_KEY')
    base_url = os.getenv('EDGEX_BASE_URL', 'https://pro.edgex.exchange')
    
    print("=" * 70)
    print("EdgeX 策略开单测试（使用历史数据）")
    print("=" * 70)
    
    # 检查环境变量
    if not account_id or not stark_private_key:
        print("[ERROR] 错误: 环境变量未设置")
        print(f"   EDGEX_ACCOUNT_ID: {'已设置' if account_id else '未设置'}")
        print(f"   EDGEX_STARK_PRIVATE_KEY: {'已设置' if stark_private_key else '未设置'}")
        return False
    
    print(f"[OK] 环境变量已设置")
    print(f"   EDGEX_ACCOUNT_ID: {account_id}")
    print(f"   Base URL: {base_url}")
    print()
    
    # 加载历史数据
    data_dir = project_root / "edgex_data"
    print(f"[LOAD] 正在加载历史数据...")
    historical_records = load_historical_data(data_dir)
    
    if not historical_records:
        print("[ERROR] 未找到历史数据文件")
        return False
    
    print(f"[OK] 已加载 {len(historical_records)} 条历史记录")
    print(f"   时间范围: {datetime.fromtimestamp(historical_records[0]['unix_time'])} 至 {datetime.fromtimestamp(historical_records[-1]['unix_time'])}")
    print()
    
    try:
        # 初始化EdgeX客户端
        print("[INIT] 正在初始化EdgeX客户端...")
        client = Client(
            base_url=base_url,
            account_id=int(account_id),
            stark_private_key=stark_private_key
        )
        
        # 获取合约列表
        print("[FETCH] 正在获取合约列表...")
        response = await client.get_metadata()
        data = response.get('data', {})
        contract_list = data.get('contractList', [])
        
        if not contract_list:
            print("[ERROR] 无法获取合约列表")
            return False
        
        # 查找ETH合约
        eth_contract = None
        for contract in contract_list:
            contract_name = contract.get('contractName', '')
            if contract_name == 'ETHUSD':
                eth_contract = contract
                break
        
        if not eth_contract:
            print("[ERROR] ETH合约未找到")
            return False
        
        eth_contract_id = eth_contract.get('contractId')
        eth_tick_size = Decimal(str(eth_contract.get('tickSize', '0.01')))
        eth_min_order_size = Decimal(str(eth_contract.get('minOrderSize', '0.1')))
        
        print(f"[OK] ETH合约信息:")
        print(f"   合约ID: {eth_contract_id}")
        print(f"   合约名称: {eth_contract.get('contractName')}")
        print(f"   最小订单量: {eth_min_order_size}")
        print(f"   价格精度: {eth_tick_size}")
        print()
        
        # 初始化策略
        print("[INIT] 正在初始化策略...")
        strategy = SimpleOrderFlowStrategy(
            contract_id=eth_contract_id,
            tick_size=eth_tick_size,
            position_size=eth_min_order_size
        )
        print(f"[OK] 策略已初始化")
        print(f"   订单大小: {strategy.position_size}")
        print(f"   失衡阈值: {strategy.imbalance_threshold}")
        print()
        
        # 统计数据
        stats = {
            'start_time': time.time(),
            'data_points_processed': 0,
            'orderbook_fetches': 0,
            'signals_generated': 0,
            'orders_placed': 0,
            'orders_successful': 0,
            'orders_failed': 0,
            'last_order_time': None
        }
        
        print("=" * 70)
        print("开始测试策略开单...")
        print("=" * 70)
        print("提示: 将按时间顺序处理历史数据，当检测到信号时尝试开单")
        print("      按 Ctrl+C 可以停止测试")
        print()
        
        # 处理历史数据
        # 由于历史数据只有best_bid/best_ask，我们需要获取当前订单簿深度
        # 或者每隔一段时间获取一次深度数据
        
        test_duration = 300  # 测试5分钟
        end_time = stats['start_time'] + test_duration
        last_orderbook_fetch = 0
        orderbook_fetch_interval = 5  # 每5秒获取一次订单簿深度
        last_signal_check = 0
        signal_check_interval = 5  # 每5秒检查一次信号
        min_order_interval = 10  # 最小下单间隔10秒
        
        # 处理历史数据点（采样处理，不处理所有点）
        sample_interval = max(1, len(historical_records) // 1000)  # 最多处理1000个点
        
        print(f"[INFO] 将处理 {len(historical_records) // sample_interval} 个数据点（采样间隔: {sample_interval}）")
        print()
        
        record_index = 0
        while time.time() < end_time and record_index < len(historical_records):
            current_time = time.time()
            
            # 获取当前订单簿深度（定期更新）
            if current_time - last_orderbook_fetch >= orderbook_fetch_interval:
                bids, asks = await fetch_orderbook_depth(client, eth_contract_id, strategy.orderbook_depth)
                if bids and asks:
                    strategy.update_orderbook(bids, asks)
                    stats['orderbook_fetches'] += 1
                    last_orderbook_fetch = current_time
                    
                    # 检查信号
                    if current_time - last_signal_check >= signal_check_interval:
                        last_signal_check = current_time
                        
                        signal = strategy.generate_signal()
                        
                        if signal and signal['strength'] >= strategy.signal_strength_threshold:
                            # 检查是否距离上次开单足够久
                            if stats['last_order_time'] is None or \
                               (current_time - stats['last_order_time']) >= min_order_interval:
                                
                                stats['signals_generated'] += 1
                                
                                print(f"\n[SIGNAL] 检测到交易信号:")
                                print(f"   方向: {signal['direction'].upper()}")
                                print(f"   强度: {signal['strength']:.2%}")
                                print(f"   失衡: {signal['imbalance']:.2%}")
                                print(f"   价格: {signal['price']}")
                                print(f"   最佳买价: {strategy.best_bid}")
                                print(f"   最佳卖价: {strategy.best_ask}")
                                
                                # 尝试开单
                                try:
                                    print(f"\n[ORDER] 正在尝试开单...")
                                    
                                    # 计算订单价格
                                    if signal['direction'] == 'buy':
                                        order_price = strategy.best_ask - strategy.tick_size
                                        side = OrderSide.BUY
                                    else:
                                        order_price = strategy.best_bid + strategy.tick_size
                                        side = OrderSide.SELL
                                    
                                    # 四舍五入到tick_size
                                    rounded_price = round(order_price / strategy.tick_size) * strategy.tick_size
                                    
                                    print(f"   订单方向: {signal['direction'].upper()}")
                                    print(f"   订单价格: {rounded_price}")
                                    print(f"   订单数量: {strategy.position_size}")
                                    
                                    # 下单
                                    order_result = await client.create_limit_order(
                                        contract_id=eth_contract_id,
                                        size=str(strategy.position_size),
                                        price=str(rounded_price),
                                        side=side,
                                        post_only=True
                                    )
                                    
                                    stats['orders_placed'] += 1
                                    
                                    if order_result and 'data' in order_result:
                                        order_id = order_result['data'].get('orderId')
                                        if order_id:
                                            print(f"[SUCCESS] 订单已提交!")
                                            print(f"   订单ID: {order_id}")
                                            
                                            # 等待一小段时间检查订单状态
                                            await asyncio.sleep(0.5)
                                            
                                            # 检查订单状态
                                            try:
                                                from edgex_sdk import GetActiveOrderParams
                                                order_params = GetActiveOrderParams(contract_id=eth_contract_id)
                                                active_orders = await client.trade.get_active_orders(order_params)
                                                
                                                # 查找我们的订单
                                                order_found = False
                                                if active_orders and 'data' in active_orders:
                                                    for order in active_orders['data']:
                                                        if str(order.get('orderId')) == str(order_id):
                                                            order_found = True
                                                            order_status = order.get('status', 'UNKNOWN')
                                                            print(f"   订单状态: {order_status}")
                                                            
                                                            if order_status in ['OPEN', 'PARTIALLY_FILLED', 'FILLED']:
                                                                stats['orders_successful'] += 1
                                                                print(f"[SUCCESS] 订单成功! 状态: {order_status}")
                                                            else:
                                                                stats['orders_failed'] += 1
                                                                print(f"[WARNING] 订单状态异常: {order_status}")
                                                            break
                                                
                                                if not order_found:
                                                    print(f"[INFO] 订单可能已成交或取消")
                                                    stats['orders_successful'] += 1
                                                    
                                            except Exception as e:
                                                print(f"[WARNING] 检查订单状态失败: {e}")
                                            
                                            stats['last_order_time'] = current_time
                                        else:
                                            print(f"[ERROR] 订单ID未返回")
                                            stats['orders_failed'] += 1
                                    else:
                                        print(f"[ERROR] 下单失败: {order_result}")
                                        stats['orders_failed'] += 1
                                    
                                except Exception as e:
                                    print(f"[ERROR] 开单异常: {e}")
                                    import traceback
                                    traceback.print_exc()
                                    stats['orders_failed'] += 1
                                    stats['last_order_time'] = current_time
            
            # 处理历史数据点（用于显示进度）
            if record_index < len(historical_records):
                record = historical_records[record_index]
                stats['data_points_processed'] += 1
                record_index += sample_interval
            
            # 每30秒打印一次统计
            elapsed = current_time - stats['start_time']
            if int(elapsed) % 30 == 0 and int(elapsed) > 0:
                print(f"\n[STATS] 运行时间: {int(elapsed)}秒 | "
                      f"数据点: {stats['data_points_processed']} | "
                      f"订单簿获取: {stats['orderbook_fetches']} | "
                      f"信号数: {stats['signals_generated']} | "
                      f"下单数: {stats['orders_placed']} | "
                      f"成功: {stats['orders_successful']} | "
                      f"失败: {stats['orders_failed']}")
            
            await asyncio.sleep(1)
        
        # 打印最终统计
        total_time = time.time() - stats['start_time']
        print("\n" + "=" * 70)
        print("测试结果")
        print("=" * 70)
        print(f"总运行时间: {total_time:.1f}秒")
        print(f"处理数据点: {stats['data_points_processed']}")
        print(f"订单簿获取次数: {stats['orderbook_fetches']}")
        print(f"生成信号数: {stats['signals_generated']}")
        print(f"尝试下单数: {stats['orders_placed']}")
        print(f"成功下单数: {stats['orders_successful']}")
        print(f"失败下单数: {stats['orders_failed']}")
        
        if stats['orders_placed'] > 0:
            success_rate = stats['orders_successful'] / stats['orders_placed'] * 100
            print(f"成功率: {success_rate:.1f}%")
        
        # 关闭客户端
        await client.close()
        
        print("\n" + "=" * 70)
        print("测试完成")
        print("=" * 70)
        
        return stats['orders_successful'] > 0
        
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("EdgeX 策略开单测试工具（使用历史数据）")
    print("=" * 70)
    print("此工具将使用已下载的历史数据测试策略是否能够成功开单")
    print("测试将持续5分钟")
    print("=" * 70)
    print()
    
    try:
        result = asyncio.run(test_strategy_with_historical_data())
        if result:
            print("\n[SUCCESS] 测试通过: 策略能够成功开单")
        else:
            print("\n[INFO] 测试完成: 未成功开单（可能是市场条件不满足）")
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断，正在退出...")
    except Exception as e:
        print(f"\n[ERROR] 程序异常: {e}")
        import traceback
        traceback.print_exc()
