"""
持仓管理模块 - 帮助控制策略的持仓
"""

import os
import sys
import asyncio
from pathlib import Path
from decimal import Decimal
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from edgex_sdk import Client
import dotenv

# 设置输出编码为UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')


@dataclass
class PositionInfo:
    """持仓信息"""
    contract_id: str
    ticker: str
    open_size: Decimal
    avg_price: Decimal
    unrealized_pnl: Decimal
    contract_name: str = ""
    leverage: Decimal = Decimal('1')
    
    @property
    def is_long(self) -> bool:
        """是否为多头持仓"""
        return self.open_size > 0
    
    @property
    def is_short(self) -> bool:
        """是否为空头持仓"""
        return self.open_size < 0
    
    @property
    def abs_size(self) -> Decimal:
        """持仓绝对值"""
        return abs(self.open_size)


class PositionManager:
    """持仓管理器 - 用于控制策略的持仓"""
    
    def __init__(self, exchange: str = "edgex", base_url: Optional[str] = None):
        """
        初始化持仓管理器
        
        Args:
            exchange: 交易所名称，目前支持 "edgex"
            base_url: API基础URL，如果为None则从环境变量读取
        """
        self.exchange = exchange.lower()
        self.base_url = base_url or os.getenv('EDGEX_BASE_URL', 'https://pro.edgex.exchange')
        
        # 从环境变量读取配置
        self.account_id = os.getenv('EDGEX_ACCOUNT_ID')
        self.stark_private_key = os.getenv('EDGEX_STARK_PRIVATE_KEY')
        
        if not self.account_id or not self.stark_private_key:
            raise ValueError("EDGEX_ACCOUNT_ID 和 EDGEX_STARK_PRIVATE_KEY 环境变量必须设置")
        
        # 初始化客户端
        self.client: Optional[Client] = None
        
        # 合约映射缓存
        self.contract_id_to_ticker: Dict[str, str] = {}
        self.ticker_to_contract_id: Dict[str, str] = {}
        self.contract_id_to_name: Dict[str, str] = {}
        
        # 策略配置的交易对
        self.strategy_tickers: Set[str] = set()
        
    async def initialize(self):
        """初始化客户端和合约映射"""
        if self.exchange == "edgex":
            self.client = Client(
                base_url=self.base_url,
                account_id=int(self.account_id),
                stark_private_key=self.stark_private_key
            )
            await self._load_contract_mapping()
        else:
            raise ValueError(f"不支持的交易所: {self.exchange}")
    
    async def _load_contract_mapping(self):
        """加载合约ID到ticker的映射"""
        if not self.client:
            raise RuntimeError("客户端未初始化，请先调用 initialize()")
        
        metadata_response = await self.client.get_metadata()
        metadata_data = metadata_response.get('data', {})
        contract_list = metadata_data.get('contractList', [])
        
        self.contract_id_to_ticker.clear()
        self.ticker_to_contract_id.clear()
        self.contract_id_to_name.clear()
        
        for contract in contract_list:
            contract_id = str(contract.get('contractId', ''))
            contract_name = contract.get('contractName', '')
            ticker = self._contract_name_to_ticker(contract_name)
            
            if contract_id and ticker:
                self.contract_id_to_ticker[contract_id] = ticker
                self.ticker_to_contract_id[ticker] = contract_id
                self.contract_id_to_name[contract_id] = contract_name
    
    def _contract_name_to_ticker(self, contract_name: str) -> str:
        """将合约名称转换为ticker（例如 ETHUSD -> ETH）"""
        if contract_name.endswith('USD'):
            return contract_name[:-3]
        return contract_name
    
    def set_strategy_tickers(self, tickers: List[str]):
        """
        设置策略中配置的交易对
        
        Args:
            tickers: 交易对列表，例如 ['ETH', 'SOL']
        """
        self.strategy_tickers = {t.upper() for t in tickers}
    
    async def get_all_positions(self) -> List[PositionInfo]:
        """
        获取所有持仓
        
        Returns:
            持仓信息列表
        """
        if not self.client:
            raise RuntimeError("客户端未初始化，请先调用 initialize()")
        
        positions_response = await self.client.get_account_positions()
        
        if not positions_response or 'data' not in positions_response:
            return []
        
        positions_list = positions_response.get('data', {}).get('positionList', [])
        position_infos = []
        
        for position in positions_list:
            contract_id = str(position.get('contractId', ''))
            open_size = Decimal(str(position.get('openSize', 0)))
            
            # 只返回有持仓的
            if open_size == 0:
                continue
            
            ticker = self.contract_id_to_ticker.get(contract_id, f'未知({contract_id})')
            contract_name = self.contract_id_to_name.get(contract_id, '')
            
            position_info = PositionInfo(
                contract_id=contract_id,
                ticker=ticker,
                open_size=open_size,
                avg_price=Decimal(str(position.get('avgPrice', 0))),
                unrealized_pnl=Decimal(str(position.get('unrealizedPnl', 0))),
                contract_name=contract_name,
                leverage=Decimal(str(position.get('leverage', 1)))
            )
            position_infos.append(position_info)
        
        return position_infos
    
    def get_positions_in_strategy(self, positions: List[PositionInfo]) -> List[PositionInfo]:
        """
        获取在策略中的持仓
        
        Args:
            positions: 所有持仓列表
            
        Returns:
            在策略中的持仓列表
        """
        if not self.strategy_tickers:
            return positions  # 如果没有设置策略，返回所有持仓
        
        return [pos for pos in positions if pos.ticker in self.strategy_tickers]
    
    def get_positions_not_in_strategy(self, positions: List[PositionInfo]) -> List[PositionInfo]:
        """
        获取不在策略中的持仓
        
        Args:
            positions: 所有持仓列表
            
        Returns:
            不在策略中的持仓列表
        """
        if not self.strategy_tickers:
            return []  # 如果没有设置策略，返回空列表
        
        return [pos for pos in positions if pos.ticker not in self.strategy_tickers]
    
    async def close_position(self, position: PositionInfo, use_market_order: bool = False) -> bool:
        """
        平仓指定的持仓
        
        Args:
            position: 持仓信息
            use_market_order: 是否使用市价单（快速平仓），默认False使用限价单
            
        Returns:
            是否成功
        """
        if not self.client:
            raise RuntimeError("客户端未初始化，请先调用 initialize()")
        
        if position.open_size == 0:
            return True  # 已经平仓
        
        # 确定平仓方向
        if position.is_long:
            close_side = 'sell'
        else:
            close_side = 'buy'
        
        quantity = abs(position.open_size)
        
        try:
            if use_market_order:
                # 使用市价单快速平仓
                # 注意：EdgeX可能不支持市价单，这里需要根据实际情况调整
                # 暂时使用限价单，价格设置为当前市场价格附近
                from edgex_sdk import GetOrderBookDepthParams
                depth_params = GetOrderBookDepthParams(contract_id=int(position.contract_id), limit=1)
                order_book = await self.client.quote.get_order_book_depth(depth_params)
                
                if order_book and 'data' in order_book and len(order_book['data']) > 0:
                    data = order_book['data'][0]
                    bids = data.get('bids', [])
                    asks = data.get('asks', [])
                    
                    if close_side == 'sell' and bids:
                        price = Decimal(bids[0]['price'])
                    elif close_side == 'buy' and asks:
                        price = Decimal(asks[0]['price'])
                    else:
                        # 使用均价作为后备
                        price = position.avg_price
                else:
                    price = position.avg_price
            else:
                # 使用限价单，价格设置为当前市场价格附近（确保能成交）
                from edgex_sdk import GetOrderBookDepthParams
                depth_params = GetOrderBookDepthParams(contract_id=int(position.contract_id), limit=1)
                order_book = await self.client.quote.get_order_book_depth(depth_params)
                
                if order_book and 'data' in order_book and len(order_book['data']) > 0:
                    data = order_book['data'][0]
                    bids = data.get('bids', [])
                    asks = data.get('asks', [])
                    
                    if close_side == 'sell' and bids:
                        # 卖单：价格略低于最佳买价，确保快速成交
                        price = Decimal(bids[0]['price']) * Decimal('0.999')
                    elif close_side == 'buy' and asks:
                        # 买单：价格略高于最佳卖价，确保快速成交
                        price = Decimal(asks[0]['price']) * Decimal('1.001')
                    else:
                        price = position.avg_price
                else:
                    price = position.avg_price
            
            # 下平仓单
            from edgex_sdk import PlaceOrderParams, OrderSide, OrderType
            order_side = OrderSide.SELL if close_side == 'sell' else OrderSide.BUY
            
            place_order_params = PlaceOrderParams(
                contract_id=int(position.contract_id),
                side=order_side,
                order_type=OrderType.LIMIT,
                size=str(quantity),
                price=str(price),
                post_only=False  # 允许作为taker快速成交
            )
            
            result = await self.client.place_order(place_order_params)
            
            if result and 'data' in result:
                return True
            else:
                print(f"[ERROR] 平仓失败: {result}")
                return False
                
        except Exception as e:
            print(f"[ERROR] 平仓时发生错误: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    async def close_positions_not_in_strategy(self, dry_run: bool = True) -> Dict[str, bool]:
        """
        平仓所有不在策略中的持仓
        
        Args:
            dry_run: 是否为试运行模式（只显示，不实际平仓）
            
        Returns:
            平仓结果字典 {ticker: success}
        """
        all_positions = await self.get_all_positions()
        positions_to_close = self.get_positions_not_in_strategy(all_positions)
        
        results = {}
        
        if not positions_to_close:
            print("[INFO] 没有需要平仓的持仓")
            return results
        
        print(f"\n{'[试运行] ' if dry_run else ''}准备平仓 {len(positions_to_close)} 个不在策略中的持仓:")
        for pos in positions_to_close:
            print(f"  • {pos.ticker}: {pos.open_size} @ {pos.avg_price} (盈亏: {pos.unrealized_pnl})")
        
        if dry_run:
            print("\n[INFO] 这是试运行模式，不会实际平仓。设置 dry_run=False 来执行平仓。")
            return results
        
        print("\n开始平仓...")
        for pos in positions_to_close:
            print(f"\n正在平仓 {pos.ticker}...")
            success = await self.close_position(pos, use_market_order=True)
            results[pos.ticker] = success
            if success:
                print(f"  ✅ {pos.ticker} 平仓成功")
            else:
                print(f"  ❌ {pos.ticker} 平仓失败")
            await asyncio.sleep(0.5)  # 避免请求过快
        
        return results
    
    async def get_position_summary(self) -> Dict:
        """
        获取持仓摘要
        
        Returns:
            包含持仓统计信息的字典
        """
        all_positions = await self.get_all_positions()
        in_strategy = self.get_positions_in_strategy(all_positions)
        not_in_strategy = self.get_positions_not_in_strategy(all_positions)
        
        total_pnl = sum(pos.unrealized_pnl for pos in all_positions)
        in_strategy_pnl = sum(pos.unrealized_pnl for pos in in_strategy)
        not_in_strategy_pnl = sum(pos.unrealized_pnl for pos in not_in_strategy)
        
        return {
            'total_positions': len(all_positions),
            'in_strategy': len(in_strategy),
            'not_in_strategy': len(not_in_strategy),
            'total_pnl': total_pnl,
            'in_strategy_pnl': in_strategy_pnl,
            'not_in_strategy_pnl': not_in_strategy_pnl,
            'positions': all_positions,
            'in_strategy_positions': in_strategy,
            'not_in_strategy_positions': not_in_strategy
        }
    
    async def close(self):
        """关闭客户端连接"""
        if self.client:
            await self.client.close()
            self.client = None


async def main():
    """示例用法"""
    # 加载.env文件
    project_root = Path(__file__).parent
    env_file = project_root / ".env"
    if env_file.exists():
        dotenv.load_dotenv(env_file)
    
    # 创建持仓管理器
    manager = PositionManager()
    
    try:
        # 初始化
        await manager.initialize()
        
        # 设置策略交易对（可以从命令行参数或环境变量读取）
        import sys
        if len(sys.argv) > 1:
            strategy_tickers = [t.upper() for t in sys.argv[1:]]
        else:
            strategy_ticker_env = os.getenv('STRATEGY_TICKERS', '')
            if strategy_ticker_env:
                strategy_tickers = [t.strip().upper() for t in strategy_ticker_env.split(',') if t.strip()]
            else:
                strategy_tickers = []
        
        if strategy_tickers:
            manager.set_strategy_tickers(strategy_tickers)
            print(f"[INFO] 策略交易对: {', '.join(strategy_tickers)}\n")
        
        # 获取持仓摘要
        summary = await manager.get_position_summary()
        
        print("=" * 60)
        print("持仓摘要")
        print("=" * 60)
        print(f"总持仓数: {summary['total_positions']}")
        print(f"在策略中: {summary['in_strategy']}")
        print(f"不在策略中: {summary['not_in_strategy']}")
        print(f"总未实现盈亏: {summary['total_pnl']}")
        print(f"策略内盈亏: {summary['in_strategy_pnl']}")
        print(f"策略外盈亏: {summary['not_in_strategy_pnl']}")
        print()
        
        # 显示在策略中的持仓
        if summary['in_strategy_positions']:
            print("✅ 在策略中的持仓:")
            for pos in summary['in_strategy_positions']:
                print(f"  • {pos.ticker}: {pos.open_size} @ {pos.avg_price} (盈亏: {pos.unrealized_pnl})")
            print()
        
        # 显示不在策略中的持仓
        if summary['not_in_strategy_positions']:
            print("⚠️  不在策略中的持仓:")
            for pos in summary['not_in_strategy_positions']:
                print(f"  • {pos.ticker}: {pos.open_size} @ {pos.avg_price} (盈亏: {pos.unrealized_pnl})")
            print()
        
        # 询问是否平仓不在策略中的持仓
        if summary['not_in_strategy_positions']:
            print("=" * 60)
            print("是否平仓不在策略中的持仓？")
            print("=" * 60)
            print("提示: 运行脚本时添加 --close 参数来执行平仓")
            print("      或者使用 --dry-run 来查看将要平仓的持仓")
            
            # 检查命令行参数
            if '--close' in sys.argv:
                print("\n执行平仓...")
                results = await manager.close_positions_not_in_strategy(dry_run=False)
                print("\n平仓结果:")
                for ticker, success in results.items():
                    status = "✅ 成功" if success else "❌ 失败"
                    print(f"  {ticker}: {status}")
            elif '--dry-run' in sys.argv:
                print("\n试运行模式（不会实际平仓）:")
                await manager.close_positions_not_in_strategy(dry_run=True)
        
    finally:
        await manager.close()


if __name__ == "__main__":
    asyncio.run(main())
