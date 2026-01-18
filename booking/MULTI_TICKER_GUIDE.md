# 多交易品种订单流策略指南

## 概述

订单流策略**完全支持**多种交易品种，不限于ETH。只要EdgeX交易所支持的交易对，都可以使用订单流策略进行交易。

## 支持的交易品种

### EdgeX交易所支持的常见交易对

根据EdgeX的合约命名规则（`{TICKER}USD`），理论上支持所有EdgeX上可用的永续合约，包括但不限于：

- **ETH** (ETHUSD)
- **BTC** (BTCUSD)  
- **SOL** (SOLUSD)
- **其他EdgeX支持的交易对**

### 如何查看EdgeX支持的所有交易对

EdgeX通过`get_metadata()` API返回所有可用合约列表。代码会自动查找匹配的交易对。

## 使用方法

### 基本命令格式

```bash
python booking/run_orderflow_bot.py \
    --exchange edgex \
    --ticker <交易对> \
    --simulate \
    --enable-logging
```

### 不同交易品种的示例

#### 1. ETH (以太坊)

```bash
python booking/run_orderflow_bot.py \
    --exchange edgex \
    --ticker ETH \
    --simulate \
    --position-size 0.1 \
    --imbalance-threshold 0.1 \
    --signal-strength-threshold 0.3 \
    --confirmation-ticks 1
```

#### 2. BTC (比特币)

```bash
python booking/run_orderflow_bot.py \
    --exchange edgex \
    --ticker BTC \
    --simulate \
    --position-size 0.05 \
    --imbalance-threshold 0.1 \
    --signal-strength-threshold 0.3 \
    --confirmation-ticks 1
```

**注意**: BTC通常需要更小的头寸大小（如0.05），因为BTC价格更高。

#### 3. SOL (Solana)

```bash
python booking/run_orderflow_bot.py \
    --exchange edgex \
    --ticker SOL \
    --simulate \
    --position-size 1.0 \
    --imbalance-threshold 0.1 \
    --signal-strength-threshold 0.3 \
    --confirmation-ticks 1
```

**注意**: SOL价格较低，可以使用更大的头寸大小。

#### 4. 其他交易对

只需将`--ticker`参数改为对应的交易对代码即可：

```bash
python booking/run_orderflow_bot.py \
    --exchange edgex \
    --ticker <TICKER> \
    --simulate \
    --position-size <适当大小> \
    --imbalance-threshold 0.1 \
    --signal-strength-threshold 0.3 \
    --confirmation-ticks 1
```

## 参数调整建议

不同交易品种可能需要不同的参数设置：

### 1. 头寸大小 (position-size)

根据交易对的价格和波动性调整：

| 交易对 | 建议头寸大小 | 说明 |
|--------|-------------|------|
| BTC | 0.01 - 0.05 | 价格高，使用较小头寸 |
| ETH | 0.1 - 0.5 | 中等价格 |
| SOL | 1.0 - 5.0 | 价格较低，可使用较大头寸 |
| 其他 | 根据价格调整 | 参考ETH/BTC比例 |

### 2. 失衡阈值 (imbalance-threshold)

不同交易对的订单簿特征可能不同：

- **高流动性交易对** (BTC, ETH): 可以使用较高的阈值 (0.5-0.7)
- **中等流动性**: 使用中等阈值 (0.3-0.5)
- **低流动性**: 使用较低阈值 (0.1-0.3) 以捕获更多信号

### 3. 信号强度阈值 (signal-strength-threshold)

- **波动性大的交易对**: 可以使用较低阈值 (0.3-0.5)
- **稳定交易对**: 使用较高阈值 (0.6-0.8)

### 4. 更新间隔 (update-interval)

- **高波动性**: 更短的间隔 (0.3-0.5秒)
- **低波动性**: 可以稍长 (0.5-1.0秒)

## 代码实现说明

### 交易对查找逻辑

代码通过以下方式查找交易对：

```python
# 在 exchanges/edgex.py 中
async def get_contract_attributes(self) -> Tuple[str, Decimal]:
    ticker = self.config.ticker  # 例如: "ETH", "BTC", "SOL"
    
    response = await self.client.get_metadata()
    contract_list = response.get('data', {}).get('contractList', [])
    
    # 查找匹配的合约 (格式: TICKER + "USD")
    for c in contract_list:
        if c.get('contractName') == ticker + 'USD':
            # 找到匹配的合约
            return contract_id, tick_size
```

### 自动适配

- **合约ID**: 自动从EdgeX元数据中获取
- **Tick Size**: 自动获取每个交易对的最小价格单位
- **最小订单量**: 自动验证是否符合交易所要求

## 验证交易对是否可用

如果指定的交易对不存在，机器人会在初始化时报告错误：

```
Failed to get contract ID for ticker: <TICKER>
```

### 手动检查可用交易对

你可以创建一个简单的脚本来列出所有可用交易对：

```python
import asyncio
import os
from edgex_sdk import Client
import dotenv

dotenv.load_dotenv()

async def list_contracts():
    client = Client(
        base_url=os.getenv('EDGEX_BASE_URL', 'https://pro.edgex.exchange'),
        account_id=int(os.getenv('EDGEX_ACCOUNT_ID')),
        stark_private_key=os.getenv('EDGEX_STARK_PRIVATE_KEY')
    )
    
    response = await client.get_metadata()
    contracts = response.get('data', {}).get('contractList', [])
    
    print("EdgeX支持的交易对:")
    for c in contracts:
        contract_name = c.get('contractName', '')
        if contract_name.endswith('USD'):
            ticker = contract_name[:-3]  # 移除'USD'后缀
            print(f"  - {ticker} ({contract_name})")
    
    await client.close()

asyncio.run(list_contracts())
```

## 多交易对同时运行

你可以同时运行多个机器人实例，每个监控不同的交易对：

### 终端1 - ETH
```bash
python booking/run_orderflow_bot.py --exchange edgex --ticker ETH --simulate
```

### 终端2 - BTC
```bash
python booking/run_orderflow_bot.py --exchange edgex --ticker BTC --simulate
```

### 终端3 - SOL
```bash
python booking/run_orderflow_bot.py --exchange edgex --ticker SOL --simulate
```

每个实例会：
- 创建独立的日志文件
- 生成独立的信号CSV文件
- 独立运行，互不干扰

## 日志文件命名

不同交易对的日志文件会自动区分：

- **信号CSV**: `logs/orderflow_signals_edgex_{TICKER}_simulate_{DATE}.csv`
- **活动日志**: `logs/edgex_{TICKER}_activity.log`

例如：
- ETH: `logs/orderflow_signals_edgex_ETH_simulate_20260111.csv`
- BTC: `logs/orderflow_signals_edgex_BTC_simulate_20260111.csv`
- SOL: `logs/orderflow_signals_edgex_SOL_simulate_20260111.csv`

## 常见问题

### Q: 如何知道某个交易对是否支持？

A: 运行机器人时，如果交易对不存在，会在初始化阶段报错。或者使用上面的脚本列出所有可用交易对。

### Q: 不同交易对的参数需要调整吗？

A: 是的，建议根据交易对的特点调整：
- 价格高的交易对（如BTC）使用较小的头寸
- 波动性大的交易对可能需要更频繁的更新
- 流动性低的交易对可能需要更低的阈值

### Q: 可以同时运行多个交易对吗？

A: 可以，每个交易对运行独立的机器人实例即可。

### Q: 策略逻辑对不同交易对都一样吗？

A: 是的，订单流策略的核心逻辑是通用的，适用于所有交易对。只需要根据交易对特性调整参数即可。

## 总结

✅ **订单流策略完全支持多交易品种**

- 只需修改`--ticker`参数
- 代码会自动查找和适配交易对
- 每个交易对独立运行和记录
- 根据交易对特性调整参数以获得最佳效果

开始使用其他交易对，只需运行：

```bash
python booking/run_orderflow_bot.py --exchange edgex --ticker <你的交易对> --simulate
```
