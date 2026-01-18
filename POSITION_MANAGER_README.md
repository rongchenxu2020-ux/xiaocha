# 持仓管理模块使用说明

## 概述

`position_manager.py` 是一个用于控制策略持仓的模块，可以帮助您：

- 获取所有当前持仓
- 检查持仓是否在策略中
- 自动平仓不在策略中的持仓
- 监控持仓状态和盈亏

## 功能特性

1. **持仓查询**: 获取所有持仓信息，包括持仓量、均价、未实现盈亏等
2. **策略匹配**: 检查持仓是否在策略配置的交易对中
3. **自动平仓**: 可以自动平仓不在策略中的持仓
4. **持仓摘要**: 提供持仓统计和盈亏汇总

## 安装要求

确保已安装必要的依赖：

```bash
pip install edgex-sdk python-dotenv
```

## 环境变量配置

在 `.env` 文件中配置：

```
EDGEX_ACCOUNT_ID=your_account_id
EDGEX_STARK_PRIVATE_KEY=your_private_key
EDGEX_BASE_URL=https://pro.edgex.exchange
STRATEGY_TICKERS=ETH,SOL  # 可选：策略交易对
```

## 使用方法

### 方法1: 使用命令行脚本

```bash
# 查看持仓摘要
python position_manager.py ETH SOL

# 试运行模式（查看将要平仓的持仓，不实际平仓）
python position_manager.py ETH SOL --dry-run

# 执行平仓（平仓不在策略中的持仓）
python position_manager.py ETH SOL --close
```

### 方法2: 在代码中使用

```python
import asyncio
from position_manager import PositionManager

async def main():
    # 创建持仓管理器
    manager = PositionManager()
    
    try:
        # 初始化
        await manager.initialize()
        
        # 设置策略交易对
        manager.set_strategy_tickers(['ETH', 'SOL'])
        
        # 获取所有持仓
        all_positions = await manager.get_all_positions()
        
        # 分类持仓
        in_strategy = manager.get_positions_in_strategy(all_positions)
        not_in_strategy = manager.get_positions_not_in_strategy(all_positions)
        
        # 获取持仓摘要
        summary = await manager.get_position_summary()
        print(f"总持仓数: {summary['total_positions']}")
        print(f"在策略中: {summary['in_strategy']}")
        print(f"不在策略中: {summary['not_in_strategy']}")
        
        # 平仓不在策略中的持仓（试运行）
        await manager.close_positions_not_in_strategy(dry_run=True)
        
        # 实际执行平仓
        # results = await manager.close_positions_not_in_strategy(dry_run=False)
        
    finally:
        await manager.close()

asyncio.run(main())
```

## API 参考

### PositionManager 类

#### 初始化

```python
manager = PositionManager(exchange="edgex", base_url=None)
```

- `exchange`: 交易所名称，目前支持 "edgex"
- `base_url`: API基础URL，如果为None则从环境变量读取

#### 主要方法

##### `async initialize()`
初始化客户端和合约映射。必须先调用此方法。

##### `set_strategy_tickers(tickers: List[str])`
设置策略中配置的交易对。

```python
manager.set_strategy_tickers(['ETH', 'SOL'])
```

##### `async get_all_positions() -> List[PositionInfo]`
获取所有持仓。

##### `get_positions_in_strategy(positions: List[PositionInfo]) -> List[PositionInfo]`
获取在策略中的持仓。

##### `get_positions_not_in_strategy(positions: List[PositionInfo]) -> List[PositionInfo]`
获取不在策略中的持仓。

##### `async close_position(position: PositionInfo, use_market_order: bool = False) -> bool`
平仓指定的持仓。

- `position`: 持仓信息
- `use_market_order`: 是否使用市价单（快速平仓）

##### `async close_positions_not_in_strategy(dry_run: bool = True) -> Dict[str, bool]`
平仓所有不在策略中的持仓。

- `dry_run`: 是否为试运行模式（只显示，不实际平仓）

##### `async get_position_summary() -> Dict`
获取持仓摘要，包含统计信息和盈亏汇总。

##### `async close()`
关闭客户端连接。

### PositionInfo 数据类

持仓信息包含以下字段：

- `contract_id`: 合约ID
- `ticker`: 交易对符号（如 'ETH'）
- `open_size`: 持仓量（正数为多头，负数为空头）
- `avg_price`: 平均开仓价格
- `unrealized_pnl`: 未实现盈亏
- `contract_name`: 合约名称
- `leverage`: 杠杆倍数

属性：

- `is_long`: 是否为多头持仓
- `is_short`: 是否为空头持仓
- `abs_size`: 持仓绝对值

## 使用示例

### 示例1: 检查持仓是否在策略中

```python
manager = PositionManager()
await manager.initialize()
manager.set_strategy_tickers(['ETH', 'SOL'])

all_positions = await manager.get_all_positions()
in_strategy = manager.get_positions_in_strategy(all_positions)
not_in_strategy = manager.get_positions_not_in_strategy(all_positions)

print(f"在策略中: {len(in_strategy)} 个")
print(f"不在策略中: {len(not_in_strategy)} 个")
```

### 示例2: 获取持仓摘要

```python
manager = PositionManager()
await manager.initialize()
manager.set_strategy_tickers(['ETH', 'SOL'])

summary = await manager.get_position_summary()
print(f"总持仓数: {summary['total_positions']}")
print(f"总盈亏: {summary['total_pnl']}")
```

### 示例3: 平仓不在策略中的持仓

```python
manager = PositionManager()
await manager.initialize()
manager.set_strategy_tickers(['ETH', 'SOL'])

# 试运行模式
await manager.close_positions_not_in_strategy(dry_run=True)

# 实际执行
results = await manager.close_positions_not_in_strategy(dry_run=False)
```

### 示例4: 平仓单个持仓

```python
manager = PositionManager()
await manager.initialize()

positions = await manager.get_all_positions()
if positions:
    position = positions[0]
    success = await manager.close_position(position, use_market_order=True)
```

## 注意事项

1. **风险提示**: 平仓操作会实际执行交易，请谨慎使用
2. **试运行模式**: 建议先使用 `dry_run=True` 查看将要平仓的持仓
3. **网络延迟**: 平仓操作可能需要一些时间，请耐心等待
4. **错误处理**: 如果平仓失败，会记录错误信息，但不会中断其他持仓的平仓操作

## 与 check_positions_in_strategy.py 的区别

- `check_positions_in_strategy.py`: 简单的检查脚本，只查看持仓状态
- `position_manager.py`: 完整的持仓管理模块，可以集成到其他代码中使用，支持自动平仓等功能

## 故障排除

### 问题: 无法连接到交易所

**解决方案**: 检查环境变量是否正确设置，特别是 `EDGEX_ACCOUNT_ID` 和 `EDGEX_STARK_PRIVATE_KEY`

### 问题: 平仓失败

**解决方案**: 
- 检查持仓是否已经平仓（open_size == 0）
- 检查网络连接
- 查看错误信息，可能是价格或数量问题

### 问题: 合约映射失败

**解决方案**: 确保已调用 `initialize()` 方法，并且网络连接正常

## 更新日志

- v1.0.0: 初始版本，支持基本的持仓查询和平仓功能
