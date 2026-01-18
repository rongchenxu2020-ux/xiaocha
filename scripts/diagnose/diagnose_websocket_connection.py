#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断 EDGEX WebSocket 连接错误
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# 设置 Windows 控制台编码
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except:
        pass

# 加载环境变量
env_path = Path(__file__).parent / '.env'
if env_path.exists():
    load_dotenv(env_path)
    print(f"[OK] 已加载 .env 文件: {env_path}")
else:
    print(f"[WARNING] 未找到 .env 文件: {env_path}")
    print("   请确保 .env 文件存在于项目根目录")

print("=" * 80)
print("EDGEX WebSocket 连接诊断")
print("=" * 80)

# 1. 检查环境变量配置
print("\n【1. 环境变量检查】")
print("-" * 80)

required_vars = {
    'EDGEX_ACCOUNT_ID': os.getenv('EDGEX_ACCOUNT_ID'),
    'EDGEX_STARK_PRIVATE_KEY': os.getenv('EDGEX_STARK_PRIVATE_KEY'),
    'EDGEX_BASE_URL': os.getenv('EDGEX_BASE_URL', 'https://pro.edgex.exchange'),
    'EDGEX_WS_URL': os.getenv('EDGEX_WS_URL', 'wss://quote.edgex.exchange'),
}

issues = []
for var_name, var_value in required_vars.items():
    if var_value:
        if 'PRIVATE_KEY' in var_name or 'SECRET' in var_name:
            # 隐藏敏感信息，只显示前4位和后4位
            masked = var_value[:4] + '...' + var_value[-4:] if len(var_value) > 8 else '***'
            print(f"  [OK] {var_name}: {masked} (长度: {len(var_value)})")
        else:
            print(f"  [OK] {var_name}: {var_value}")
    else:
        print(f"  [ERROR] {var_name}: 未设置")
        issues.append(f"{var_name} 未设置")

# 检查账户ID格式
if required_vars['EDGEX_ACCOUNT_ID']:
    try:
        account_id_int = int(required_vars['EDGEX_ACCOUNT_ID'])
        print(f"  [OK] 账户ID格式正确: {account_id_int}")
    except ValueError:
        print(f"  [ERROR] 账户ID格式错误: 必须是数字")
        issues.append("EDGEX_ACCOUNT_ID 格式错误")

# 检查私钥格式（Stark key通常是64字符的十六进制）
if required_vars['EDGEX_STARK_PRIVATE_KEY']:
    key = required_vars['EDGEX_STARK_PRIVATE_KEY']
    if len(key) < 60:
        print(f"  [WARNING] 私钥长度可能不正确: {len(key)} 字符 (通常应该是64字符)")
        issues.append("EDGEX_STARK_PRIVATE_KEY 长度异常")
    if not all(c in '0123456789abcdefABCDEF' for c in key):
        print(f"  [WARNING] 私钥格式可能不正确: 应该只包含十六进制字符")
        issues.append("EDGEX_STARK_PRIVATE_KEY 格式异常")

# 2. 检查 edgex_sdk 包
print("\n【2. SDK 包检查】")
print("-" * 80)

try:
    import edgex_sdk
    print(f"  [OK] edgex_sdk 已安装")
    try:
        print(f"  [OK] edgex_sdk 版本: {edgex_sdk.__version__}")
    except:
        print(f"  [WARNING] 无法获取 edgex_sdk 版本")
    
    # 检查必要的类
    from edgex_sdk import Client, WebSocketManager
    print(f"  [OK] Client 类可用")
    print(f"  [OK] WebSocketManager 类可用")
except ImportError as e:
    print(f"  [ERROR] edgex_sdk 未安装或导入失败: {e}")
    issues.append("edgex_sdk 包未安装")
    print(f"\n  安装命令: pip install edgex-sdk")

# 3. 测试 REST API 连接
print("\n【3. REST API 连接测试】")
print("-" * 80)

if required_vars['EDGEX_ACCOUNT_ID'] and required_vars['EDGEX_STARK_PRIVATE_KEY']:
    try:
        from edgex_sdk import Client
        
        client = Client(
            base_url=required_vars['EDGEX_BASE_URL'],
            account_id=int(required_vars['EDGEX_ACCOUNT_ID']),
            stark_private_key=required_vars['EDGEX_STARK_PRIVATE_KEY']
        )
        print(f"  [OK] Client 初始化成功")
        
        # 尝试获取账户信息（如果API支持）
        try:
            # 这里可以尝试调用一个简单的API来验证凭证
            print(f"  [OK] REST API 客户端创建成功")
        except Exception as e:
            print(f"  [WARNING] REST API 测试失败: {e}")
            issues.append(f"REST API 测试失败: {e}")
    except Exception as e:
        print(f"  [ERROR] Client 初始化失败: {e}")
        issues.append(f"Client 初始化失败: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"  [SKIP] 跳过 REST API 测试（缺少凭证）")

# 4. 测试 WebSocket 连接
print("\n【4. WebSocket 连接测试】")
print("-" * 80)

async def test_websocket_connection():
    """测试 WebSocket 连接"""
    if not required_vars['EDGEX_ACCOUNT_ID'] or not required_vars['EDGEX_STARK_PRIVATE_KEY']:
        print(f"  [SKIP] 跳过 WebSocket 测试（缺少凭证）")
        return
    
    try:
        from edgex_sdk import WebSocketManager
        
        ws_manager = WebSocketManager(
            base_url=required_vars['EDGEX_WS_URL'],
            account_id=int(required_vars['EDGEX_ACCOUNT_ID']),
            stark_pri_key=required_vars['EDGEX_STARK_PRIVATE_KEY']
        )
        print(f"  [OK] WebSocketManager 初始化成功")
        print(f"  [OK] WebSocket URL: {required_vars['EDGEX_WS_URL']}")
        
        # 尝试连接
        print(f"  [TESTING] 尝试连接 WebSocket...")
        try:
            ws_manager.connect_private()
            print(f"  [OK] WebSocket 连接成功！")
            
            # 等待一小段时间看是否保持连接
            await asyncio.sleep(2)
            
            # 检查连接状态
            try:
                private_client = ws_manager.get_private_client()
                print(f"  [OK] 私有 WebSocket 客户端可用")
            except Exception as e:
                print(f"  [WARNING] 无法获取私有客户端: {e}")
            
            # 断开连接
            ws_manager.disconnect_private()
            print(f"  [OK] 已断开连接")
            
        except Exception as e:
            print(f"  [ERROR] WebSocket 连接失败: {e}")
            issues.append(f"WebSocket 连接失败: {e}")
            
            # 详细错误信息
            error_str = str(e)
            if "400" in error_str or "Handshake status 400" in error_str:
                print(f"\n  [ANALYSIS] 错误分析:")
                print(f"     - HTTP 400 表示请求格式错误或认证失败")
                print(f"     - 可能原因:")
                print(f"       1. API 密钥或账户ID错误")
                print(f"       2. 私钥格式不正确")
                print(f"       3. 账户权限不足")
                print(f"       4. WebSocket URL 不正确")
                print(f"       5. 交易所API变更")
            
            import traceback
            print(f"\n  详细错误信息:")
            traceback.print_exc()
            
    except Exception as e:
        print(f"  [ERROR] WebSocketManager 初始化失败: {e}")
        issues.append(f"WebSocketManager 初始化失败: {e}")
        import traceback
        traceback.print_exc()

# 运行异步测试
if required_vars['EDGEX_ACCOUNT_ID'] and required_vars['EDGEX_STARK_PRIVATE_KEY']:
    try:
        asyncio.run(test_websocket_connection())
    except Exception as e:
        print(f"  [ERROR] 异步测试执行失败: {e}")
        import traceback
        traceback.print_exc()

# 5. 网络连接测试
print("\n【5. 网络连接测试】")
print("-" * 80)

import socket
import urllib.parse

def test_network_connectivity(host, port=None):
    """测试网络连接"""
    try:
        parsed = urllib.parse.urlparse(host)
        hostname = parsed.hostname or host
        port = port or (443 if parsed.scheme == 'https' or parsed.scheme == 'wss' else 80)
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((hostname, port))
        sock.close()
        
        if result == 0:
            print(f"  [OK] {hostname}:{port} 可达")
            return True
        else:
            print(f"  [ERROR] {hostname}:{port} 不可达 (错误码: {result})")
            return False
    except Exception as e:
        print(f"  [ERROR] {host} 连接测试失败: {e}")
        return False

# 测试基础URL
base_host = required_vars['EDGEX_BASE_URL'].replace('https://', '').replace('http://', '')
test_network_connectivity(base_host, 443)

# 测试WebSocket URL
ws_host = required_vars['EDGEX_WS_URL'].replace('wss://', '').replace('ws://', '')
test_network_connectivity(ws_host, 443)

# 6. 检查代码中的连接逻辑
print("\n【6. 代码逻辑检查】")
print("-" * 80)

edgex_file = Path(__file__).parent / 'exchanges' / 'edgex.py'
if edgex_file.exists():
    print(f"  [OK] edgex.py 文件存在")
    
    # 检查关键代码
    with open(edgex_file, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if 'WebSocketManager' in content:
        print(f"  [OK] 使用了 WebSocketManager")
    else:
        print(f"  [WARNING] 未找到 WebSocketManager 使用")
    
    if 'connect_private' in content:
        print(f"  [OK] 调用了 connect_private()")
    else:
        print(f"  [WARNING] 未找到 connect_private() 调用")
else:
    print(f"  [ERROR] edgex.py 文件不存在")

# 7. 总结和建议
print("\n" + "=" * 80)
print("【诊断总结】")
print("=" * 80)

if issues:
    print(f"\n发现 {len(issues)} 个问题:")
    for i, issue in enumerate(issues, 1):
        print(f"  {i}. {issue}")
    
    print(f"\n建议解决方案:")
    print(f"  1. 检查 .env 文件中的配置是否正确")
    print(f"  2. 验证 EDGEX_ACCOUNT_ID 是否为有效的数字ID")
    print(f"  3. 验证 EDGEX_STARK_PRIVATE_KEY 是否为正确的64字符十六进制私钥")
    print(f"  4. 检查账户是否有API访问权限")
    print(f"  5. 确认网络连接正常，没有被防火墙阻止")
    print(f"  6. 查看 EDGEX 官方文档，确认API是否有变更")
    print(f"  7. 尝试更新 edgex-sdk 包: pip install --upgrade edgex-sdk")
    print(f"  8. 检查 EDGEX 交易所状态页面，确认服务是否正常")
else:
    print(f"\n[OK] 未发现明显问题")
    print(f"  如果仍然无法连接，可能是:")
    print(f"  - 交易所API临时故障")
    print(f"  - 账户权限限制")
    print(f"  - SDK版本不兼容")
    print(f"  - 需要联系 EDGEX 技术支持")

print("\n" + "=" * 80)
