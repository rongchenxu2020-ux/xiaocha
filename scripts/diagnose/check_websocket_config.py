#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速检查 EDGEX WebSocket 配置
"""

import os
import sys
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
    print("[OK] .env 文件已加载\n")
else:
    print("[ERROR] .env 文件不存在\n")
    sys.exit(1)

print("=" * 60)
print("EDGEX WebSocket 配置检查")
print("=" * 60)

# 检查必要的环境变量
account_id = os.getenv('EDGEX_ACCOUNT_ID')
stark_key = os.getenv('EDGEX_STARK_PRIVATE_KEY')
base_url = os.getenv('EDGEX_BASE_URL', 'https://pro.edgex.exchange')
ws_url = os.getenv('EDGEX_WS_URL', 'wss://quote.edgex.exchange')

print(f"\n[配置检查]")
print(f"EDGEX_ACCOUNT_ID: {'[OK] 已设置' if account_id else '[ERROR] 未设置'}")
if account_id:
    try:
        int(account_id)
        print(f"  格式: [OK] 有效数字")
    except:
        print(f"  格式: [ERROR] 必须是数字")

print(f"EDGEX_STARK_PRIVATE_KEY: {'[OK] 已设置' if stark_key else '[ERROR] 未设置'}")
if stark_key:
    print(f"  长度: {len(stark_key)} 字符")
    if len(stark_key) < 60:
        print(f"  [WARNING] 警告: 长度可能不正确（通常应该是64字符）")
    if not all(c in '0123456789abcdefABCDEF' for c in stark_key):
        print(f"  [WARNING] 警告: 包含非十六进制字符")

print(f"EDGEX_BASE_URL: {base_url}")
print(f"EDGEX_WS_URL: {ws_url}")

# 检查SDK
print(f"\n[SDK 检查]")
try:
    import edgex_sdk
    print(f"[OK] edgex_sdk 已安装")
    try:
        from edgex_sdk import Client, WebSocketManager
        print(f"[OK] 必要的类可导入")
    except ImportError as e:
        print(f"[ERROR] 导入失败: {e}")
except ImportError:
    print(f"[ERROR] edgex_sdk 未安装")
    print(f"  安装命令: pip install edgex-sdk")

# 测试初始化
print(f"\n[初始化测试]")
if account_id and stark_key:
    try:
        from edgex_sdk import WebSocketManager
        
        ws_manager = WebSocketManager(
            base_url=ws_url,
            account_id=int(account_id),
            stark_pri_key=stark_key
        )
        print(f"[OK] WebSocketManager 初始化成功")
        print(f"\n[WARNING] 注意: 实际连接测试需要运行机器人")
        print(f"   如果连接失败，常见原因:")
        print(f"   1. API密钥错误或已过期")
        print(f"   2. 账户权限不足")
        print(f"   3. 网络连接问题")
        print(f"   4. edgex_sdk 版本不兼容")
        
    except Exception as e:
        print(f"[ERROR] 初始化失败: {e}")
        import traceback
        traceback.print_exc()
else:
    print(f"[SKIP] 跳过（缺少凭证）")

print(f"\n" + "=" * 60)
