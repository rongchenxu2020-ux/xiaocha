# 回测数据来源指南

## 当前数据获取方式

### ✅ 已支持的方式

1. **本地JSON文件** - 推荐用于完整回测
2. **本地CSV文件** - 简单格式，易于准备
3. **模拟数据生成** - 快速测试策略逻辑

### ⚠️ 从交易所API获取（限制）

**重要说明**: 大多数交易所**不提供历史订单簿数据API**，因此：

- ❌ 无法直接从交易所API获取历史订单簿快照
- ❌ 无法获取历史订单簿深度数据
- ✅ 可以获取当前订单簿（但这不是历史数据）

## 数据获取方案

### 方案1: 实时收集并存储（推荐）

在策略运行时实时收集数据：

```python
# 在策略中添加数据收集功能
class DataCollector:
    def __init__(self):
        self.orderbooks = []
        self.trades = []
    
    async def collect_orderbook(self, snapshot):
        self.orderbooks.append({
            'timestamp': time.time(),
            'bids': [(float(level.price), float(level.size)) for level in snapshot.bids],
            'asks': [(float(level.price), float(level.size)) for level in snapshot.asks]
        })
    
    def save_to_json(self, filename):
        data = {
            'orderbooks': self.orderbooks,
            'trades': self.trades
        }
        with open(filename, 'w') as f:
            json.dump(data, f)
```

### 方案2: 使用第三方数据服务

#### 选项A: CoinGecko / CoinMarketCap
- 提供K线数据（OHLCV）
- 不提供订单簿数据
- 可用于简化回测

#### 选项B: CryptoCompare
- 提供交易数据
- 部分提供订单簿数据
- 需要API密钥

#### 选项C: Kaiko / CryptoDataDownload
- 专业级市场数据
- 提供订单簿和交易数据
- 通常需要付费

### 方案3: 使用K线数据简化回测

如果无法获取订单簿数据，可以使用K线数据进行简化回测：

```python
# 使用K线数据模拟订单簿
def kline_to_orderbook(kline):
    open_price = kline['open']
    close_price = kline['close']
    high_price = kline['high']
    low_price = kline['low']
    
    # 模拟订单簿
    mid_price = (high_price + low_price) / 2
    spread = (high_price - low_price) * 0.001  # 0.1% spread
    
    return {
        'bids': [(mid_price - spread/2, volume)],
        'asks': [(mid_price + spread/2, volume)],
        'best_bid': mid_price - spread/2,
        'best_ask': mid_price + spread/2
    }
```

### 方案4: 使用模拟数据

对于策略逻辑测试，可以使用模拟数据：

```bash
python booking/run_backtest.py \
    --generate-mock \
    --start-price 2000 \
    --num-samples 10000 \
    --volatility 0.002
```

## 数据格式要求

### JSON格式（推荐）

```json
{
    "orderbooks": [
        {
            "timestamp": 1609459200.0,
            "bids": [[2000.0, 10.5], [1999.5, 15.2]],
            "asks": [[2000.5, 12.3], [2001.0, 8.7]]
        }
    ],
    "trades": [
        {
            "timestamp": 1609459200.5,
            "price": 2000.0,
            "size": 0.1,
            "side": "buy"
        }
    ]
}
```

### CSV格式

**订单簿CSV**:
```csv
timestamp,bid_price,bid_size,ask_price,ask_size
1609459200.0,2000.0,10.5,2000.5,12.3
```

**交易CSV**:
```csv
timestamp,price,size,side
1609459200.5,2000.0,0.1,buy
```

## 数据收集脚本示例

创建一个数据收集脚本，在策略运行时保存数据：

```python
# collect_data.py
import asyncio
import json
import time
from decimal import Decimal
from booking.orderflow_strategy import OrderFlowStrategy
from booking.config import OrderFlowConfig

class DataCollector:
    def __init__(self):
        self.orderbooks = []
        self.trades = []
    
    def save_orderbook(self, snapshot):
        self.orderbooks.append({
            'timestamp': time.time(),
            'bids': [[float(level.price), float(level.size)] 
                     for level in snapshot.bids],
            'asks': [[float(level.price), float(level.size)] 
                     for level in snapshot.asks]
        })
    
    def save_to_file(self, filename='collected_data.json'):
        data = {
            'orderbooks': self.orderbooks,
            'trades': self.trades
        }
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"数据已保存到: {filename}")

# 在策略中集成数据收集
collector = DataCollector()
# ... 在订单簿更新时调用 collector.save_orderbook(snapshot)
```

## 推荐工作流程

1. **开发阶段**: 使用模拟数据快速测试策略逻辑
2. **验证阶段**: 使用少量真实数据验证策略
3. **优化阶段**: 使用完整历史数据进行参数优化
4. **生产阶段**: 实时收集数据，用于后续回测

## 总结

- ✅ **必须**: 准备本地数据文件（JSON或CSV）
- ✅ **推荐**: 实时收集数据并存储
- ⚠️ **限制**: 交易所API通常不提供历史订单簿数据
- 💡 **替代**: 使用K线数据或第三方数据服务

对于完整的订单流策略回测，**建议实时收集并存储数据**，这是最可靠的方式。
