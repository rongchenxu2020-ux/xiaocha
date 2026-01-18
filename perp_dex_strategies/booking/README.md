# 订单流交易策略

## 概述

订单流交易策略（Order Flow Trading Strategy）是一种基于市场微观结构信息的交易方法。该策略通过分析订单簿、交易流和挂单行为来识别市场趋势和潜在的价格变动。

## 核心概念

### 什么是订单流？

订单流是指市场中买方和卖方订单的动态变化，包括：
- **订单簿深度**：买卖盘口的挂单数量和价格分布
- **大单追踪**：识别大额订单和机构交易行为
- **订单失衡**：买卖订单的不平衡状态
- **流动性分析**：评估市场的流动性水平

### 策略原理

订单流交易策略主要基于以下假设：
1. **订单失衡预示价格方向**：大量买单聚集通常预示价格上涨，反之亦然
2. **大单影响**：机构或大户的大额订单会影响短期价格走势
3. **流动性真空**：订单簿中的流动性缺口可能导致价格快速移动
4. **订单取消模式**：频繁取消订单可能表示做市商或大户的意图

## 功能模块

### 1. 订单簿分析
- 实时监控订单簿深度
- 计算买卖盘口失衡比率
- 识别支撑位和阻力位

### 2. 交易流监控
- 追踪大额交易
- 分析交易方向（买入/卖出）
- 识别异常交易模式

### 3. 信号生成
- 基于订单流指标生成交易信号
- 结合价格和成交量确认信号
- 设置风险管理参数

### 4. 执行引擎
- 自动下单系统
- 滑点控制
- 订单执行优化

## 使用方法

### 快速开始

#### 1. 基本使用

```bash
python booking/run_orderflow.py --exchange edgex --ticker ETH
```

#### 2. 完整参数示例

```bash
python booking/run_orderflow.py \
    --exchange edgex \
    --ticker ETH \
    --orderbook-depth 20 \
    --imbalance-threshold 0.6 \
    --min-order-size 10000 \
    --large-order-threshold 50000 \
    --position-size 0.1 \
    --max-position 1.0 \
    --signal-strength-threshold 0.7 \
    --update-interval 0.5
```

#### 3. 使用Python API

```python
from booking.config import OrderFlowConfig
from booking.orderflow_strategy import OrderFlowStrategy

# 创建策略配置
config = OrderFlowConfig(
    exchange='edgex',
    ticker='ETH',
    contract_id='ETH',
    imbalance_threshold=0.6,
    signal_strength_threshold=0.7,
    position_size=Decimal(0.1)
)

# 创建策略实例
strategy = OrderFlowStrategy(config)

# 运行策略
await strategy.initialize()
await strategy.run()
```

## 参数说明

### 基础参数
- `--exchange`: 交易所名称（edgex, backpack, paradex, apex等）
- `--ticker`: 交易对符号（ETH, BTC等）
- `--env-file`: 环境变量文件路径（默认: .env）

### 订单簿分析参数
- `--orderbook-depth`: 订单簿深度（默认: 20）
- `--imbalance-threshold`: 失衡阈值 0-1（默认: 0.6）
- `--min-order-size`: 最小监控订单规模，美元（默认: 10000）

### 交易流监控参数
- `--large-order-threshold`: 大单阈值，美元（默认: 50000）
- `--trade-flow-window`: 交易流时间窗口，秒（默认: 60）

### 信号生成参数
- `--signal-strength-threshold`: 信号强度阈值 0-1（默认: 0.7）
- `--confirmation-ticks`: 确认所需的tick数（默认: 3）

### 执行参数
- `--position-size`: 每笔交易的头寸大小（默认: 0.1）
- `--max-position`: 最大持仓（默认: 1.0）
- `--stop-loss-pct`: 止损百分比（默认: 0.02）
- `--take-profit-pct`: 止盈百分比（默认: 0.01）

### 风险控制参数
- `--max-orders-per-minute`: 每分钟最大订单数（默认: 5）
- `--max-daily-loss`: 每日最大亏损（默认: 无限制）

### 其他参数
- `--update-interval`: 更新间隔，秒（默认: 0.5）
- `--disable-logging`: 禁用日志输出

## 策略工作原理

1. **订单簿分析**: 实时分析订单簿深度，计算失衡比率、支撑阻力位等
2. **交易流监控**: 监控大额交易、交易方向、价格动量等
3. **信号生成**: 综合订单簿和交易流指标生成交易信号
4. **信号确认**: 需要连续多个一致信号才执行交易
5. **风险控制**: 检查持仓限制、订单频率、每日亏损等

## 风险提示

⚠️ **重要提醒**：
- 订单流策略依赖于高频数据和实时处理能力
- 市场流动性不足时可能产生假信号
- 建议在充分理解策略逻辑后再进行实盘交易
- 请合理设置止损和仓位管理参数
- 不同交易所的订单簿API可能不同，部分功能可能需要适配

## 支持的交易所

- EdgeX ✅
- Backpack ✅
- Paradex ✅
- Apex ✅
- 其他交易所（使用基础BBO数据，功能受限）

## 故障排除

### 问题：无法获取订单簿深度数据

**解决方案**:
1. 检查交易所是否支持深度API
2. 查看日志中的错误信息
3. 策略会自动降级使用BBO数据

### 问题：信号生成过于频繁或过少

**解决方案**:
1. 调整 `--signal-strength-threshold` 参数
2. 调整 `--imbalance-threshold` 参数
3. 调整 `--confirmation-ticks` 参数

## 技术栈

- Python 3.10+
- WebSocket 实时数据流
- 异步IO处理
- 数值计算和统计分析

## 回测系统

✅ **回测功能已实现**

订单流策略现在支持完整的历史数据回测功能：

- **数据加载**: 支持JSON和CSV格式的历史数据
- **模拟数据**: 可生成模拟数据进行快速测试
- **性能指标**: 计算胜率、夏普比率、最大回撤等指标
- **详细报告**: 生成完整的回测报告
- **数据导出**: 支持导出交易记录和权益曲线

### 快速开始回测

```bash
# 使用模拟数据快速测试
python booking/run_backtest.py \
    --generate-mock \
    --start-price 2000 \
    --num-samples 1000 \
    --exchange edgex \
    --ticker ETH

# 使用历史数据文件
python booking/run_backtest.py \
    --data data.json \
    --exchange edgex \
    --ticker ETH
```

详细使用说明请参考 [回测系统使用指南](BACKTEST_GUIDE.md) 和 [测试指南](TEST_GUIDE.md)

## 开发状态

✅ **核心功能已完成**

- ✅ 订单簿分析模块
- ✅ 交易流监控模块
- ✅ 信号生成逻辑
- ✅ 风险控制机制
- ✅ 回测系统
- ⚠️ 订单簿深度数据获取（部分交易所需要适配）
- ⚠️ 止损止盈自动管理（待完善）

该策略模块持续优化中，欢迎贡献代码和建议。

## 🚀 SOL订单流机器人（优化版）

专门针对SOL交易对优化的订单流策略机器人，通过降低触发阈值来提升订单流策略的触发可能性。

### 快速开始

#### 方式1: 使用启动脚本（推荐）

**Windows (批处理):**
```bash
# 平衡设置（推荐开始使用）
start_sol_orderflow_bot.bat balanced

# 激进设置（更容易触发）
start_sol_orderflow_bot.bat aggressive

# 非常激进设置（最大化触发频率）
start_sol_orderflow_bot.bat very-aggressive
```

**Windows (PowerShell):**
```powershell
# 平衡设置
.\start_sol_orderflow_bot.ps1 balanced

# 激进设置
.\start_sol_orderflow_bot.ps1 aggressive

# 非常激进设置
.\start_sol_orderflow_bot.ps1 very-aggressive
```

#### 方式2: 直接使用Python脚本

```bash
# 平衡设置（推荐）
python booking/run_sol_orderflow_bot.py --mode balanced --simulate

# 激进设置（更容易触发）
python booking/run_sol_orderflow_bot.py --mode aggressive --simulate

# 非常激进设置（最大化触发频率）
python booking/run_sol_orderflow_bot.py --mode very-aggressive --simulate

# 自定义参数
python booking/run_sol_orderflow_bot.py --mode custom \
    --imbalance-threshold 0.3 \
    --signal-strength-threshold 0.4 \
    --confirmation-ticks 1 \
    --simulate
```

### 运行模式说明

| 模式 | 失衡阈值 | 信号强度阈值 | 确认tick数 | 更新间隔 | 触发频率 |
|------|---------|------------|-----------|---------|---------|
| **balanced** | 0.4 | 0.5 | 2 | 0.4秒 | 中等 |
| **aggressive** | 0.3 | 0.4 | 1 | 0.3秒 | 高 |
| **very-aggressive** | 0.2 | 0.3 | 1 | 0.3秒 | 非常高 |

### 优化参数说明

SOL机器人相比默认配置做了以下优化，以提升触发可能性：

1. **降低失衡阈值**: 从0.6降至0.2-0.4，让更小的订单簿失衡也能触发信号
2. **降低信号强度阈值**: 从0.7降至0.3-0.5，让更弱的信号也能通过筛选
3. **减少确认tick数**: 从3降至1-2，更快响应市场变化
4. **缩短更新间隔**: 从0.5秒降至0.3-0.4秒，更频繁检查市场
5. **降低最小订单规模**: 从10000美元降至5000美元，让更多订单参与分析
6. **降低大单阈值**: 从50000美元降至30000美元，更容易识别大单

### 参数对比

| 参数 | 默认值 | SOL平衡设置 | SOL激进设置 | SOL非常激进 |
|------|--------|------------|------------|------------|
| `imbalance_threshold` | 0.6 | **0.4** | **0.3** | **0.2** |
| `signal_strength_threshold` | 0.7 | **0.5** | **0.4** | **0.3** |
| `confirmation_ticks` | 3 | **2** | **1** | **1** |
| `update_interval` | 0.5秒 | **0.4秒** | **0.3秒** | **0.3秒** |
| `position_size` | 0.1 | **1.0** | **1.0** | **1.0** |
| `min_order_size` | 10000 | **5000** | **5000** | **5000** |

### 使用建议

1. **首次使用**: 建议从 `balanced` 模式开始，使用 `--simulate` 模拟模式测试
2. **观察信号**: 运行1-2小时，观察信号生成频率和质量
3. **调整参数**: 如果信号太少，可以尝试 `aggressive` 模式；如果假信号太多，可以调整参数
4. **真实交易**: 确认参数合适后，可以移除 `--simulate` 进行真实交易

### 详细文档

- **SOL优化指南**: `booking/SOL_OPTIMIZATION_GUIDE.md` ⭐ 推荐阅读
- **参数说明**: `booking/ORDERFLOW_PARAMETERS.md`
- **信号记录**: `booking/SIGNALS_RECORDING.md`

## 贡献指南

1. Fork 本仓库
2. 创建功能分支
3. 提交更改
4. 发起 Pull Request

## 许可证

请参考项目根目录的 LICENSE 文件。
