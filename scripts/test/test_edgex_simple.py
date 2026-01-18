#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""简单测试EdgeX数据获取"""

import sys
import asyncio
from pathlib import Path
from decimal import Decimal
import dotenv

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

dotenv.load_dotenv(project_root / ".env")

from exchanges import ExchangeFactory


class SimpleConfig:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


async def test_edgex():
    print("测试 EdgeX 数据获取")
    print("=" * 60)
    
    config_dict = {
        'contract_id': 'ETH',
        'ticker': 'ETH',
        'tick_size': Decimal('0.01'),
        'quantity': Decimal('0.1'),
    }
    
    try:
        # 创建客户端（需要先创建对象，然后替换）
        print("1. 创建客户端...")
        # 临时修改BaseExchangeClient来接受对象
        from exchanges.base import BaseExchangeClient
        original_init = BaseExchangeClient.__init__
        
        def patched_init(self, config):
            if isinstance(config, dict):
                self.config = SimpleConfig(**config)
            else:
                self.config = config
            self._validate_config()
        
        BaseExchangeClient.__init__ = patched_init
        try:
            client = ExchangeFactory.create_exchange('edgex', config_dict)
        finally:
            BaseExchangeClient.__init__ = original_init
        print("   [OK]")
        
        # 连接
        print("2. 连接交易所...")
        await client.connect()
        print("   [OK]")
        
        # 获取合约属性
        print("3. 获取合约属性...")
        contract_id, tick_size = await client.get_contract_attributes()
        print(f"   [OK] 合约ID: {contract_id}, Tick Size: {tick_size}")
        client.config.contract_id = contract_id
        client.config.tick_size = tick_size
        
        # 获取订单簿
        print("4. 获取订单簿数据...")
        best_bid, best_ask = await client.fetch_bbo_prices(contract_id)
        print(f"   [OK] 最佳买价: ${best_bid:,.2f}")
        print(f"   [OK] 最佳卖价: ${best_ask:,.2f}")
        print(f"   [OK] 中间价: ${(best_bid + best_ask) / 2:,.2f}")
        
        # 断开
        print("5. 断开连接...")
        await client.disconnect()
        print("   [OK]")
        
        print("\n" + "=" * 60)
        print("[SUCCESS] EdgeX 数据获取测试成功！")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n[FAIL] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_edgex())
    sys.exit(0 if success else 1)
