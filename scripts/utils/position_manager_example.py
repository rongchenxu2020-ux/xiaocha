"""
持仓管理模块使用示例
"""

import asyncio
from position_manager import PositionManager
import dotenv
from pathlib import Path

# 加载.env文件
project_root = Path(__file__).parent
env_file = project_root / ".env"
if env_file.exists():
    dotenv.load_dotenv(env_file)


async def example_check_positions():
    """示例1: 检查持仓是否在策略中"""
    manager = PositionManager()
    
    try:
        await manager.initialize()
        
        # 设置策略交易对
        manager.set_strategy_tickers(['ETH', 'SOL'])
        
        # 获取所有持仓
        all_positions = await manager.get_all_positions()
        print(f"当前共有 {len(all_positions)} 个持仓\n")
        
        # 分类持仓
        in_strategy = manager.get_positions_in_strategy(all_positions)
        not_in_strategy = manager.get_positions_not_in_strategy(all_positions)
        
        print("在策略中的持仓:")
        for pos in in_strategy:
            print(f"  {pos.ticker}: {pos.open_size} (盈亏: {pos.unrealized_pnl})")
        
        print("\n不在策略中的持仓:")
        for pos in not_in_strategy:
            print(f"  {pos.ticker}: {pos.open_size} (盈亏: {pos.unrealized_pnl})")
            
    finally:
        await manager.close()


async def example_get_summary():
    """示例2: 获取持仓摘要"""
    manager = PositionManager()
    
    try:
        await manager.initialize()
        manager.set_strategy_tickers(['ETH', 'SOL'])
        
        summary = await manager.get_position_summary()
        
        print("持仓摘要:")
        print(f"  总持仓数: {summary['total_positions']}")
        print(f"  在策略中: {summary['in_strategy']}")
        print(f"  不在策略中: {summary['not_in_strategy']}")
        print(f"  总盈亏: {summary['total_pnl']}")
        
    finally:
        await manager.close()


async def example_close_positions():
    """示例3: 平仓不在策略中的持仓（试运行）"""
    manager = PositionManager()
    
    try:
        await manager.initialize()
        manager.set_strategy_tickers(['ETH', 'SOL'])
        
        # 试运行模式（不会实际平仓）
        print("试运行模式 - 查看将要平仓的持仓:")
        await manager.close_positions_not_in_strategy(dry_run=True)
        
        # 实际执行平仓（取消注释来执行）
        # print("\n执行平仓:")
        # results = await manager.close_positions_not_in_strategy(dry_run=False)
        # print("平仓结果:", results)
        
    finally:
        await manager.close()


async def example_close_single_position():
    """示例4: 平仓单个持仓"""
    manager = PositionManager()
    
    try:
        await manager.initialize()
        
        # 获取所有持仓
        positions = await manager.get_all_positions()
        
        if positions:
            # 平仓第一个持仓
            position = positions[0]
            print(f"准备平仓: {position.ticker} ({position.open_size})")
            
            success = await manager.close_position(position, use_market_order=True)
            if success:
                print("平仓成功")
            else:
                print("平仓失败")
        else:
            print("当前没有持仓")
            
    finally:
        await manager.close()


if __name__ == "__main__":
    print("=" * 60)
    print("持仓管理模块使用示例")
    print("=" * 60)
    print()
    
    print("示例1: 检查持仓是否在策略中")
    print("-" * 60)
    asyncio.run(example_check_positions())
    
    print("\n\n示例2: 获取持仓摘要")
    print("-" * 60)
    asyncio.run(example_get_summary())
    
    print("\n\n示例3: 平仓不在策略中的持仓（试运行）")
    print("-" * 60)
    asyncio.run(example_close_positions())
