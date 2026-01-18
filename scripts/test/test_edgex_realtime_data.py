"""
测试脚本：检查是否能够通过环境变量获取ETH和SOL在EdgeX的实时数据
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from decimal import Decimal
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

async def test_edgex_realtime_data():
    """测试EdgeX实时数据获取"""
    
    # 从环境变量读取配置
    account_id = os.getenv('EDGEX_ACCOUNT_ID')
    stark_private_key = os.getenv('EDGEX_STARK_PRIVATE_KEY')
    base_url = os.getenv('EDGEX_BASE_URL', 'https://pro.edgex.exchange')
    ws_url = os.getenv('EDGEX_WS_URL', 'wss://quote.edgex.exchange')
    
    print("=" * 60)
    print("EdgeX 实时数据测试")
    print("=" * 60)
    
    # 检查环境变量
    if not account_id or not stark_private_key:
        print("[ERROR] 错误: 环境变量未设置")
        print(f"   EDGEX_ACCOUNT_ID: {'已设置' if account_id else '未设置'}")
        print(f"   EDGEX_STARK_PRIVATE_KEY: {'已设置' if stark_private_key else '未设置'}")
        return False
    
    print(f"[OK] 环境变量已设置")
    print(f"   EDGEX_ACCOUNT_ID: {account_id}")
    print(f"   EDGEX_STARK_PRIVATE_KEY: {'*' * 20}...{stark_private_key[-4:] if len(stark_private_key) > 4 else '****'}")
    print(f"   Base URL: {base_url}")
    print(f"   WebSocket URL: {ws_url}")
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
        
        print("\n" + "=" * 60)
        print("合约信息")
        print("=" * 60)
        
        if eth_contract:
            eth_contract_id = eth_contract.get('contractId')
            print(f"[OK] ETH合约找到:")
            print(f"   合约ID: {eth_contract_id}")
            print(f"   合约名称: {eth_contract.get('contractName')}")
            print(f"   最小订单量: {eth_contract.get('minOrderSize')}")
            print(f"   价格精度: {eth_contract.get('tickSize')}")
        else:
            print("[ERROR] ETH合约未找到")
            return False
        
        if sol_contract:
            sol_contract_id = sol_contract.get('contractId')
            print(f"\n[OK] SOL合约找到:")
            print(f"   合约ID: {sol_contract_id}")
            print(f"   合约名称: {sol_contract.get('contractName')}")
            print(f"   最小订单量: {sol_contract.get('minOrderSize')}")
            print(f"   价格精度: {sol_contract.get('tickSize')}")
        else:
            print("\n[ERROR] SOL合约未找到")
            return False
        
        # 测试REST API获取实时价格
        print("\n" + "=" * 60)
        print("REST API 实时价格测试")
        print("=" * 60)
        
        from edgex_sdk import GetOrderBookDepthParams
        
        # 获取ETH价格
        print("\n[PRICE] ETH 实时价格:")
        try:
            eth_depth_params = GetOrderBookDepthParams(contract_id=eth_contract_id, limit=15)
            eth_order_book = await client.quote.get_order_book_depth(eth_depth_params)
            eth_data = eth_order_book['data'][0]
            eth_bids = eth_data.get('bids', [])
            eth_asks = eth_data.get('asks', [])
            
            if eth_bids and eth_asks:
                best_bid = Decimal(eth_bids[0]['price'])
                best_ask = Decimal(eth_asks[0]['price'])
                spread = best_ask - best_bid
                mid_price = (best_bid + best_ask) / 2
                print(f"   最佳买价: {best_bid}")
                print(f"   最佳卖价: {best_ask}")
                print(f"   中间价: {mid_price}")
                print(f"   价差: {spread} ({spread/mid_price*100:.4f}%)")
            else:
                print("   [WARNING] 无法获取ETH订单簿数据")
        except Exception as e:
            print(f"   [ERROR] 获取ETH价格失败: {e}")
        
        # 获取SOL价格
        print("\n[PRICE] SOL 实时价格:")
        try:
            sol_depth_params = GetOrderBookDepthParams(contract_id=sol_contract_id, limit=15)
            sol_order_book = await client.quote.get_order_book_depth(sol_depth_params)
            sol_data = sol_order_book['data'][0]
            sol_bids = sol_data.get('bids', [])
            sol_asks = sol_data.get('asks', [])
            
            if sol_bids and sol_asks:
                best_bid = Decimal(sol_bids[0]['price'])
                best_ask = Decimal(sol_asks[0]['price'])
                spread = best_ask - best_bid
                mid_price = (best_bid + best_ask) / 2
                print(f"   最佳买价: {best_bid}")
                print(f"   最佳卖价: {best_ask}")
                print(f"   中间价: {mid_price}")
                print(f"   价差: {spread} ({spread/mid_price*100:.4f}%)")
            else:
                print("   [WARNING] 无法获取SOL订单簿数据")
        except Exception as e:
            print(f"   [ERROR] 获取SOL价格失败: {e}")
        
        # 测试WebSocket实时数据
        print("\n" + "=" * 60)
        print("WebSocket 实时数据测试")
        print("=" * 60)
        
        # 初始化WebSocket管理器
        ws_manager = WebSocketManager(
            base_url=ws_url,
            account_id=int(account_id),
            stark_pri_key=stark_private_key
        )
        
        # 存储接收到的数据
        import time
        eth_data_received = False
        sol_data_received = False
        message_count = 0
        start_time = None
        first_eth_time = None
        first_sol_time = None
        last_eth_time = None
        last_sol_time = None
        eth_update_count = 0
        sol_update_count = 0
        
        def handle_depth_message(message):
            """处理深度数据消息（带时间记录）"""
            nonlocal eth_data_received, sol_data_received, message_count
            nonlocal first_eth_time, first_sol_time, last_eth_time, last_sol_time
            nonlocal eth_update_count, sol_update_count
            try:
                if isinstance(message, str):
                    message = json.loads(message)
                
                message_count += 1
                current_time = time.time()
                
                # 打印所有消息以便调试
                if message_count <= 3:
                    print(f"   [DEBUG] 收到消息 #{message_count}: {str(message)[:200]}")
                
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
                        
                        if contract_id == str(eth_contract_id):
                            if not eth_data_received:
                                first_eth_time = current_time
                            eth_data_received = True
                            last_eth_time = current_time
                            eth_update_count += 1
                            bids = order_book_data.get('bids', [])
                            asks = order_book_data.get('asks', [])
                            
                            if bids and asks:
                                best_bid = Decimal(bids[0]['price'])
                                best_ask = Decimal(asks[0]['price'])
                                elapsed = current_time - start_time if start_time else 0
                                print(f"\n[WS] ETH WebSocket数据 ({depth_type}) [第{eth_update_count}次更新, 运行{elapsed:.1f}秒]:")
                                print(f"   最佳买价: {best_bid}")
                                print(f"   最佳卖价: {best_ask}")
                                print(f"   价差: {best_ask - best_bid}")
                        
                        elif contract_id == str(sol_contract_id):
                            if not sol_data_received:
                                first_sol_time = current_time
                            sol_data_received = True
                            last_sol_time = current_time
                            sol_update_count += 1
                            bids = order_book_data.get('bids', [])
                            asks = order_book_data.get('asks', [])
                            
                            if bids and asks:
                                best_bid = Decimal(bids[0]['price'])
                                best_ask = Decimal(asks[0]['price'])
                                elapsed = current_time - start_time if start_time else 0
                                print(f"\n[WS] SOL WebSocket数据 ({depth_type}) [第{sol_update_count}次更新, 运行{elapsed:.1f}秒]:")
                                print(f"   最佳买价: {best_bid}")
                                print(f"   最佳卖价: {best_ask}")
                                print(f"   价差: {best_ask - best_bid}")
                elif msg_type or (isinstance(message, dict) and message):
                    if message_count <= 5:
                        print(f"   [DEBUG] 其他消息: type={msg_type}, channel={channel}")
                
            except Exception as e:
                print(f"   [WARNING] 处理WebSocket消息错误: {e}")
                import traceback
                traceback.print_exc()
        
        # 连接WebSocket并订阅
        print("\n[CONNECT] 正在连接WebSocket...")
        try:
            ws_manager.connect_public()
            print("[OK] WebSocket公共连接已建立")
            
            # 获取公共客户端并设置消息处理器
            public_client = ws_manager.get_public_client()
            public_client.on_message("depth", handle_depth_message)
            
            # 订阅ETH和SOL的深度数据
            print(f"\n[SUBSCRIBE] 正在订阅ETH深度数据 (depth.{eth_contract_id}.15)...")
            public_client.subscribe(f"depth.{eth_contract_id}.15")
            
            print(f"[SUBSCRIBE] 正在订阅SOL深度数据 (depth.{sol_contract_id}.15)...")
            public_client.subscribe(f"depth.{sol_contract_id}.15")
            
            print("\n[WAIT] 等待WebSocket数据 (15秒)...")
            print("   提示: WebSocket可以持续接收数据，只要连接保持，理论上可以无限期接收实时更新")
            
            # 开始计时
            start_time = time.time()
            
            # 等待数据 - 给WebSocket更多时间建立连接和接收数据
            await asyncio.sleep(2)  # 先等待2秒让连接稳定
            
            for i in range(26):  # 再等待最多13秒
                await asyncio.sleep(0.5)
                if eth_data_received and sol_data_received:
                    break
                # 每5秒打印一次状态
                if i > 0 and i % 10 == 0:
                    elapsed = time.time() - start_time
                    print(f"   [WAIT] 已等待 {elapsed:.1f} 秒...")
            
            total_time = time.time() - start_time
            
            print("\n" + "=" * 60)
            print("测试结果")
            print("=" * 60)
            
            if eth_data_received:
                print("[OK] ETH WebSocket数据接收成功")
                if first_eth_time and last_eth_time:
                    duration = last_eth_time - first_eth_time
                    print(f"   ETH数据接收时间范围: {duration:.1f}秒")
                    print(f"   ETH更新次数: {eth_update_count}")
            else:
                print("[ERROR] ETH WebSocket数据未接收")
            
            if sol_data_received:
                print("[OK] SOL WebSocket数据接收成功")
                if first_sol_time and last_sol_time:
                    duration = last_sol_time - first_sol_time
                    print(f"   SOL数据接收时间范围: {duration:.1f}秒")
                    print(f"   SOL更新次数: {sol_update_count}")
            else:
                print("[ERROR] SOL WebSocket数据未接收")
            
            print(f"\n[INFO] 总共接收到 {message_count} 条WebSocket消息")
            print(f"[INFO] 总运行时间: {total_time:.1f}秒")
            
            print("\n" + "=" * 60)
            print("数据获取能力说明")
            print("=" * 60)
            print("1. REST API:")
            print("   - 类型: 实时订单簿快照（当前时刻）")
            print("   - 持续时间: 一次性获取，无历史数据")
            print("   - 限制: EdgeX不提供历史K线数据API")
            print()
            print("2. WebSocket:")
            print("   - 类型: 实时订单簿更新流")
            print("   - 持续时间: 理论上无限期（只要连接保持）")
            print(f"   - 本次测试: 运行了 {total_time:.1f}秒，接收了 {message_count} 条消息")
            print("   - 数据更新频率: 取决于市场活动，通常每秒多次更新")
            print()
            print("注意: EdgeX目前不提供公开的历史K线数据API。")
            print("      如需历史数据，可以考虑:")
            print("      - 持续运行WebSocket并本地存储数据")
            print("      - 使用其他提供历史数据API的交易所")
            
            # 断开连接
            ws_manager.disconnect_public()
            print("\n[DISCONNECT] WebSocket已断开")
            
        except Exception as e:
            print(f"[ERROR] WebSocket连接失败: {e}")
            import traceback
            traceback.print_exc()
        
        # 关闭客户端
        await client.close()
        
        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)
        
        return eth_data_received and sol_data_received
        
    except Exception as e:
        print(f"\n[ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_edgex_realtime_data())
    if result:
        print("\n[SUCCESS] 测试通过: 可以通过环境变量获取ETH和SOL在EdgeX的实时数据")
    else:
        print("\n[FAILED] 测试失败: 无法通过环境变量获取ETH和SOL在EdgeX的实时数据")
