"""
持续运行EdgeX WebSocket并本地存储数据测试脚本
测试能够持续运行多长时间并存储数据
"""

import os
import sys
import asyncio
import json
import time
import signal
from pathlib import Path
from decimal import Decimal
from datetime import datetime
from edgex_sdk import Client, WebSocketManager
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

# 全局变量用于优雅退出
running = True
data_storage = []
last_save_time = time.time()
save_interval = 60  # 每60秒自动保存一次

def signal_handler(signum, frame):
    """处理中断信号"""
    global running
    print("\n\n[INFO] 收到中断信号，正在优雅退出...")
    running = False

# 注册信号处理器
signal.signal(signal.SIGINT, signal_handler)
if sys.platform != 'win32':
    signal.signal(signal.SIGTERM, signal_handler)

def save_data_to_file(data_list, filename_prefix="edgex_data"):
    """保存数据到JSON文件"""
    if not data_list:
        return
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    data_dir = project_root / "edgex_data"
    data_dir.mkdir(exist_ok=True)
    
    filename = data_dir / f"{filename_prefix}_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data_list, f, indent=2, ensure_ascii=False, default=str)
        print(f"\n[SAVE] 数据已保存到: {filename}")
        print(f"       共保存 {len(data_list)} 条记录")
    except Exception as e:
        print(f"[ERROR] 保存数据失败: {e}")

async def test_continuous_edgex_data(duration_minutes=None):
    """持续运行EdgeX WebSocket并存储数据"""
    
    # 从环境变量读取配置
    account_id = os.getenv('EDGEX_ACCOUNT_ID')
    stark_private_key = os.getenv('EDGEX_STARK_PRIVATE_KEY')
    base_url = os.getenv('EDGEX_BASE_URL', 'https://pro.edgex.exchange')
    ws_url = os.getenv('EDGEX_WS_URL', 'wss://quote.edgex.exchange')
    
    print("=" * 70)
    print("EdgeX 持续数据收集测试")
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
    print(f"   WebSocket URL: {ws_url}")
    
    if duration_minutes:
        print(f"\n[INFO] 将运行 {duration_minutes} 分钟")
    else:
        print(f"\n[INFO] 将持续运行直到手动停止 (Ctrl+C)")
    print(f"[INFO] 数据将每 {save_interval} 秒自动保存一次")
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
        
        # 查找ETH和SOL的合约ID
        eth_contract = None
        sol_contract = None
        
        for contract in contract_list:
            contract_name = contract.get('contractName', '')
            if contract_name == 'ETHUSD':
                eth_contract = contract
            elif contract_name == 'SOLUSD':
                sol_contract = contract
        
        if not eth_contract or not sol_contract:
            print("[ERROR] 无法找到ETH或SOL合约")
            return False
        
        eth_contract_id = eth_contract.get('contractId')
        sol_contract_id = sol_contract.get('contractId')
        
        print(f"[OK] ETH合约ID: {eth_contract_id}")
        print(f"[OK] SOL合约ID: {sol_contract_id}")
        
        # 初始化WebSocket管理器
        print("\n[INIT] 正在初始化WebSocket管理器...")
        ws_manager = WebSocketManager(
            base_url=ws_url,
            account_id=int(account_id),
            stark_pri_key=stark_private_key
        )
        
        # 统计数据
        stats = {
            'start_time': time.time(),
            'eth_count': 0,
            'sol_count': 0,
            'total_messages': 0,
            'last_eth_time': None,
            'last_sol_time': None,
            'eth_prices': [],
            'sol_prices': []
        }
        
        def handle_depth_message(message):
            """处理深度数据消息并存储"""
            global data_storage, last_save_time
            
            try:
                if isinstance(message, str):
                    message = json.loads(message)
                
                msg_type = message.get("type", "") if isinstance(message, dict) else ""
                channel = message.get("channel", "") if isinstance(message, dict) else ""
                
                # 处理depth消息
                if msg_type == "quote-event" and channel.startswith("depth."):
                    content = message.get("content", {})
                    data = content.get('data', [])
                    
                    if data and len(data) > 0:
                        order_book_data = data[0]
                        contract_id = str(order_book_data.get('contractId', ''))
                        depth_type = order_book_data.get('depthType', '')
                        bids = order_book_data.get('bids', [])
                        asks = order_book_data.get('asks', [])
                        
                        if bids and asks:
                            best_bid = float(bids[0]['price'])
                            best_ask = float(asks[0]['price'])
                            mid_price = (best_bid + best_ask) / 2
                            spread = best_ask - best_bid
                            
                            current_time = time.time()
                            timestamp = datetime.fromtimestamp(current_time).isoformat()
                            
                            record = {
                                'timestamp': timestamp,
                                'unix_time': current_time,
                                'contract_id': contract_id,
                                'contract_name': 'ETHUSD' if contract_id == str(eth_contract_id) else 'SOLUSD',
                                'depth_type': depth_type,
                                'best_bid': best_bid,
                                'best_ask': best_ask,
                                'mid_price': mid_price,
                                'spread': spread,
                                'spread_pct': (spread / mid_price * 100) if mid_price > 0 else 0
                            }
                            
                            # 存储数据
                            data_storage.append(record)
                            stats['total_messages'] += 1
                            
                            # 更新统计
                            if contract_id == str(eth_contract_id):
                                stats['eth_count'] += 1
                                stats['last_eth_time'] = current_time
                                stats['eth_prices'].append(mid_price)
                                # 只保留最近100个价格用于统计
                                if len(stats['eth_prices']) > 100:
                                    stats['eth_prices'].pop(0)
                            elif contract_id == str(sol_contract_id):
                                stats['sol_count'] += 1
                                stats['last_sol_time'] = current_time
                                stats['sol_prices'].append(mid_price)
                                # 只保留最近100个价格用于统计
                                if len(stats['sol_prices']) > 100:
                                    stats['sol_prices'].pop(0)
                            
                            # 定期自动保存
                            if current_time - last_save_time >= save_interval:
                                save_data_to_file(data_storage, "edgex_continuous")
                                last_save_time = current_time
                                data_storage = []  # 清空已保存的数据
                
            except Exception as e:
                print(f"[WARNING] 处理消息错误: {e}")
        
        # 连接WebSocket并订阅
        print("\n[CONNECT] 正在连接WebSocket...")
        try:
            ws_manager.connect_public()
            print("[OK] WebSocket公共连接已建立")
            
            # 获取公共客户端并设置消息处理器
            public_client = ws_manager.get_public_client()
            public_client.on_message("depth", handle_depth_message)
            
            # 订阅ETH和SOL的深度数据
            print(f"[SUBSCRIBE] 正在订阅ETH深度数据 (depth.{eth_contract_id}.15)...")
            public_client.subscribe(f"depth.{eth_contract_id}.15")
            
            print(f"[SUBSCRIBE] 正在订阅SOL深度数据 (depth.{sol_contract_id}.15)...")
            public_client.subscribe(f"depth.{sol_contract_id}.15")
            
            print("\n" + "=" * 70)
            print("开始收集数据...")
            print("=" * 70)
            print("提示: 按 Ctrl+C 可以优雅退出并保存数据")
            print()
            
            # 等待连接稳定
            await asyncio.sleep(2)
            
            # 主循环 - 持续运行直到停止
            end_time = None
            if duration_minutes:
                end_time = stats['start_time'] + (duration_minutes * 60)
            
            last_stats_time = time.time()
            
            while running:
                current_time = time.time()
                
                # 检查是否达到指定运行时间
                if end_time and current_time >= end_time:
                    print(f"\n[INFO] 已达到指定运行时间 ({duration_minutes} 分钟)，正在退出...")
                    break
                
                # 每10秒打印一次统计信息
                if current_time - last_stats_time >= 10:
                    elapsed = current_time - stats['start_time']
                    hours = int(elapsed // 3600)
                    minutes = int((elapsed % 3600) // 60)
                    seconds = int(elapsed % 60)
                    
                    eth_rate = stats['eth_count'] / elapsed if elapsed > 0 else 0
                    sol_rate = stats['sol_count'] / elapsed if elapsed > 0 else 0
                    
                    print(f"\r[STATS] 运行时间: {hours:02d}:{minutes:02d}:{seconds:02d} | "
                          f"ETH: {stats['eth_count']} ({eth_rate:.1f}/s) | "
                          f"SOL: {stats['sol_count']} ({sol_rate:.1f}/s) | "
                          f"总计: {stats['total_messages']} 条消息 | "
                          f"待保存: {len(data_storage)} 条", end='', flush=True)
                    
                    last_stats_time = current_time
                
                await asyncio.sleep(0.5)
            
            # 最终保存数据
            print("\n\n[SAVE] 正在保存最终数据...")
            if data_storage:
                save_data_to_file(data_storage, "edgex_continuous_final")
            
            # 打印最终统计
            total_time = time.time() - stats['start_time']
            hours = int(total_time // 3600)
            minutes = int((total_time % 3600) // 60)
            seconds = int(total_time % 60)
            
            print("\n" + "=" * 70)
            print("最终统计")
            print("=" * 70)
            print(f"总运行时间: {hours:02d}:{minutes:02d}:{seconds:02d} ({total_time:.1f}秒)")
            print(f"ETH数据记录: {stats['eth_count']} 条")
            print(f"SOL数据记录: {stats['sol_count']} 条")
            print(f"总消息数: {stats['total_messages']} 条")
            print(f"平均消息速率: {stats['total_messages'] / total_time:.2f} 条/秒")
            print(f"ETH平均速率: {stats['eth_count'] / total_time:.2f} 条/秒")
            print(f"SOL平均速率: {stats['sol_count'] / total_time:.2f} 条/秒")
            
            if stats['eth_prices']:
                eth_min = min(stats['eth_prices'])
                eth_max = max(stats['eth_prices'])
                eth_avg = sum(stats['eth_prices']) / len(stats['eth_prices'])
                print(f"\nETH价格统计 (最近100条):")
                print(f"  最低: {eth_min:.2f}")
                print(f"  最高: {eth_max:.2f}")
                print(f"  平均: {eth_avg:.2f}")
            
            if stats['sol_prices']:
                sol_min = min(stats['sol_prices'])
                sol_max = max(stats['sol_prices'])
                sol_avg = sum(stats['sol_prices']) / len(stats['sol_prices'])
                print(f"\nSOL价格统计 (最近100条):")
                print(f"  最低: {sol_min:.2f}")
                print(f"  最高: {sol_max:.2f}")
                print(f"  平均: {sol_avg:.2f}")
            
            # 断开连接
            ws_manager.disconnect_public()
            print("\n[DISCONNECT] WebSocket已断开")
            
        except Exception as e:
            print(f"\n[ERROR] WebSocket连接失败: {e}")
            import traceback
            traceback.print_exc()
            # 保存已收集的数据
            if data_storage:
                save_data_to_file(data_storage, "edgex_continuous_error")
        
        # 关闭客户端
        await client.close()
        
        print("\n" + "=" * 70)
        print("测试完成")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        # 保存已收集的数据
        if data_storage:
            save_data_to_file(data_storage, "edgex_continuous_error")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='持续运行EdgeX WebSocket并存储数据')
    parser.add_argument('--duration', type=int, default=None,
                        help='运行时长（分钟），不指定则持续运行直到手动停止')
    
    args = parser.parse_args()
    
    print("\n" + "=" * 70)
    print("EdgeX 持续数据收集工具")
    print("=" * 70)
    print("此工具将持续运行WebSocket连接并存储ETH和SOL的实时数据")
    print("数据将自动保存到 edgex_data/ 目录")
    print("=" * 70)
    print()
    
    try:
        result = asyncio.run(test_continuous_edgex_data(args.duration))
        if result:
            print("\n[SUCCESS] 数据收集完成")
        else:
            print("\n[FAILED] 数据收集失败")
    except KeyboardInterrupt:
        print("\n\n[INFO] 用户中断，正在退出...")
        running = False
    except Exception as e:
        print(f"\n[ERROR] 程序异常: {e}")
        import traceback
        traceback.print_exc()
