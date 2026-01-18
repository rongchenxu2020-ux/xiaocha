#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试交易所API数据获取
检查lighter和edgex是否能成功获取订单簿数据
"""

import sys
import asyncio
from pathlib import Path
from decimal import Decimal
import dotenv

# 添加项目路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 加载环境变量
env_file = project_root / ".env"
if env_file.exists():
    dotenv.load_dotenv(env_file)
    print("已加载 .env 文件")
else:
    print("警告: 未找到 .env 文件")
print()

from exchanges import ExchangeFactory


class SimpleConfig:
    """简单的配置对象，用于测试"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def get(self, key, default=None):
        """字典风格的get方法"""
        return getattr(self, key, default)


async def test_exchange(exchange_name: str, ticker: str = 'ETH'):
    """测试交易所API连接和数据获取"""
    print("=" * 80)
    print(f"测试 {exchange_name.upper()} 交易所")
    print("=" * 80)
    print()
    
    # 创建交易所配置对象
    exchange_config = SimpleConfig(
        contract_id=ticker,
        ticker=ticker,
        tick_size=Decimal('0.01'),
        quantity=Decimal('0.1'),  # 某些交易所需要这个
    )
    
    try:
        # 1. 尝试创建客户端
        print(f"1. 创建 {exchange_name} 客户端...")
        try:
            # 创建配置对象（交易所客户端期望对象而不是字典）
            config_obj = SimpleConfig(
                contract_id=ticker,
                ticker=ticker,
                tick_size=Decimal('0.01'),
                quantity=Decimal('0.1'),
            )
            
            # 直接传递对象给ExchangeFactory（如果它接受对象）
            # 如果不行，我们需要在初始化后替换
            try:
                client = ExchangeFactory.create_exchange(exchange_name, config_obj)
            except TypeError:
                # 如果ExchangeFactory不接受对象，先传字典，然后替换
                config_dict = {
                    'contract_id': ticker,
                    'ticker': ticker,
                    'tick_size': Decimal('0.01'),
                    'quantity': Decimal('0.1'),
                }
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
                try:
                    client = ExchangeFactory.create_exchange(exchange_name, config_dict)
                finally:
                    # 恢复原始方法
                    BaseExchangeClient.__init__ = original_init
            print(f"   [OK] 客户端创建成功")
        except ImportError as e:
            print(f"   [FAIL] 导入失败: {e}")
            print(f"   原因: 缺少必要的依赖包")
            print(f"   解决方案:")
            if 'edgex' in str(e).lower():
                print(f"     - 安装edgex SDK: 请参考requirements.txt中的edgex SDK安装说明")
            elif 'lighter' in str(e).lower():
                print(f"     - 安装lighter SDK: pip install lighter-sdk==0.1.4")
            else:
                print(f"     - 运行: pip install -r requirements.txt")
            return False
        except Exception as e:
            print(f"   [FAIL] 创建失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        print()
        
        # 2. 尝试连接
        print(f"2. 连接 {exchange_name} 交易所...")
        try:
            await client.connect()
            print(f"   [OK] 连接成功")
        except Exception as e:
            print(f"   [FAIL] 连接失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        print()
        
        # 3. 尝试获取订单簿数据
        print(f"3. 获取 {ticker} 订单簿数据...")
        try:
            # 对于EdgeX，需要先获取contract_id
            if exchange_name == 'edgex':
                try:
                    contract_id, tick_size = await client.get_contract_attributes()
                    print(f"   合约ID: {contract_id}, Tick Size: {tick_size}")
                    # 更新config
                    client.config.contract_id = contract_id
                    client.config.tick_size = tick_size
                except Exception as e:
                    print(f"   获取合约属性失败: {e}")
                    # 继续尝试使用ticker
            
            best_bid, best_ask = await client.fetch_bbo_prices(client.config.contract_id or ticker)
            
            if best_bid > 0 and best_ask > 0:
                print(f"   [OK] 数据获取成功")
                print(f"   最佳买价: ${best_bid:,.2f}")
                print(f"   最佳卖价: ${best_ask:,.2f}")
                print(f"   中间价: ${(best_bid + best_ask) / 2:,.2f}")
                print(f"   价差: ${best_ask - best_bid:,.2f} ({(best_ask - best_bid) / best_bid * 100:.4f}%)")
                
                # 尝试获取更多数据（如果支持）
                try:
                    # 检查是否有获取深度数据的方法
                    if hasattr(client, 'fetch_orderbook_depth'):
                        depth_data = await client.fetch_orderbook_depth(ticker, depth=5)
                        print(f"   [OK] 深度数据获取成功: {len(depth_data.get('bids', []))} 个买单层级")
                except:
                    pass  # 深度数据获取失败不影响基本功能
                
                success = True
            else:
                print(f"   [FAIL] 获取的数据无效: bid={best_bid}, ask={best_ask}")
                success = False
                
        except Exception as e:
            print(f"   [FAIL] 获取数据失败: {e}")
            import traceback
            traceback.print_exc()
            success = False
        print()
        
        # 4. 断开连接
        print(f"4. 断开连接...")
        try:
            await client.disconnect()
            print(f"   [OK] 断开成功")
        except Exception as e:
            print(f"   [WARN] 断开时出错: {e}")
        print()
        
        return success
        
    except Exception as e:
        print(f"[FAIL] 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """主函数"""
    import sys
    if hasattr(sys.stdout, 'reconfigure'):
        try:
            sys.stdout.reconfigure(encoding='utf-8')
        except:
            pass
    
    print("=" * 80)
    print("交易所API数据获取测试")
    print("=" * 80)
    print()
    
    # 测试的交易所
    exchanges_to_test = ['lighter', 'edgex']
    ticker = 'ETH'
    
    results = {}
    
    for exchange in exchanges_to_test:
        print()
        try:
            success = await test_exchange(exchange, ticker)
            results[exchange] = success
        except Exception as e:
            print(f"测试 {exchange} 时出错: {e}")
            import traceback
            traceback.print_exc()
            results[exchange] = False
        print()
    
    # 总结
    print("=" * 80)
    print("测试总结")
    print("=" * 80)
    print()
    
    for exchange, success in results.items():
        status = "[OK] 成功" if success else "[FAIL] 失败"
        print(f"{exchange.upper():<15} {status}")
    
    print()
    
    # 检查是否有可用的交易所
    available = [ex for ex, success in results.items() if success]
    if available:
        print(f"可用的交易所: {', '.join(available)}")
        print(f"\n建议使用以下交易所进行测试:")
        print(f"  py generate_test_report.py")
        print(f"  (在脚本中修改 exchange = '{available[0]}')")
    else:
        print("警告: 没有可用的交易所")
        print("\n请检查:")
        print("1. .env 文件是否配置了API密钥")
        print("2. 是否安装了必要的依赖包")
        print("3. 网络连接是否正常")
    
    print("=" * 80)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
