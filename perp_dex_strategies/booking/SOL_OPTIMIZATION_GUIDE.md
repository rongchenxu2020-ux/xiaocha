# SOL订单流策略优化指南

本文档专门说明如何调整参数，让订单流机器人在SOL上更容易触发交易信号。

## 🎯 优化目标

让SOL策略**更容易触发**，捕捉更多交易机会，适合：
- SOL市场波动性较大
- 希望提高交易频率
- 愿意接受更多信号（包括一些假信号）

## 📊 关键参数调整

### 1. 失衡阈值 (`imbalance_threshold`) ⭐⭐⭐ 最重要

**默认值**: `0.6`  
**SOL推荐值**: `0.3` - `0.4`

**说明**:
- 这个参数控制订单簿失衡达到多少才会触发信号
- 降低此值会让策略更敏感，更容易捕捉到市场失衡
- SOL市场通常波动较大，较小的失衡也可能有意义

**调整建议**:
```bash
# 保守设置（仍然较容易触发）
--imbalance-threshold 0.4

# 激进设置（非常容易触发）
--imbalance-threshold 0.3

# 非常激进（几乎任何失衡都触发）
--imbalance-threshold 0.2
```

### 2. 信号强度阈值 (`signal_strength_threshold`) ⭐⭐⭐ 最重要

**默认值**: `0.7`  
**SOL推荐值**: `0.4` - `0.5`

**说明**:
- 控制信号强度必须达到多少才会被考虑
- 降低此值会让更多信号通过筛选
- 信号强度由多个因素组成（订单簿失衡40% + 加权失衡30% + 交易流20% + 动量10%）

**调整建议**:
```bash
# 保守设置
--signal-strength-threshold 0.5

# 激进设置（更容易触发）
--signal-strength-threshold 0.4

# 非常激进
--signal-strength-threshold 0.3
```

### 3. 确认Tick数 (`confirmation_ticks`) ⭐⭐ 重要

**默认值**: `3`  
**SOL推荐值**: `1` - `2`

**说明**:
- 控制需要连续多少个相同方向的信号才执行交易
- 减少此值会让策略响应更快，更容易触发
- 但也会增加假信号的风险

**调整建议**:
```bash
# 快速响应（推荐）
--confirmation-ticks 1

# 平衡设置
--confirmation-ticks 2

# 保守设置（默认）
--confirmation-ticks 3
```

### 4. 最小订单规模 (`min_order_size`) ⭐⭐ 重要

**默认值**: `10000` (美元)  
**SOL推荐值**: `5000` - `7000`

**说明**:
- 控制参与分析的订单最小规模
- 降低此值会让更多订单参与分析，可能发现更多失衡
- SOL市场订单规模可能相对较小

**注意**: 此参数目前不在命令行中，需要在代码中修改 `config.py` 或通过编程方式设置。

### 5. 更新间隔 (`update_interval`) ⭐ 次要

**默认值**: `0.5` 秒  
**SOL推荐值**: `0.3` - `0.4` 秒

**说明**:
- 控制策略分析订单簿的频率
- 更短的间隔可以更快捕捉到市场变化
- 但会增加系统资源消耗

**调整建议**:
```bash
# 更频繁更新（推荐）
--update-interval 0.3

# 平衡设置
--update-interval 0.4

# 默认设置
--update-interval 0.5
```

### 6. 头寸大小 (`position_size`) 

**默认值**: `0.1`  
**SOL推荐值**: `1.0` - `5.0`

**说明**:
- SOL价格较低，可以使用更大的头寸
- 不影响触发频率，但影响每次交易的规模

## 🚀 推荐的SOL配置

### 配置1: 平衡设置（推荐开始使用）

```bash
python booking/run_orderflow_bot.py \
    --exchange edgex \
    --ticker SOL \
    --position-size 1.0 \
    --imbalance-threshold 0.4 \
    --signal-strength-threshold 0.5 \
    --confirmation-ticks 2 \
    --update-interval 0.4 \
    --max-position 5.0 \
    --stop-loss-pct 0.02 \
    --take-profit-pct 0.01 \
    --simulate \
    --enable-logging
```

**特点**:
- 比默认设置更容易触发
- 仍然保持一定的信号质量
- 适合大多数SOL交易场景

### 配置2: 激进设置（更容易触发）

```bash
python booking/run_orderflow_bot.py \
    --exchange edgex \
    --ticker SOL \
    --position-size 1.0 \
    --imbalance-threshold 0.3 \
    --signal-strength-threshold 0.4 \
    --confirmation-ticks 1 \
    --update-interval 0.3 \
    --max-position 5.0 \
    --stop-loss-pct 0.02 \
    --take-profit-pct 0.01 \
    --simulate \
    --enable-logging
```

**特点**:
- 非常容易触发
- 会捕捉到更多交易机会
- 可能包含更多假信号，需要更严格的风险控制

### 配置3: 非常激进设置（最大化触发频率）

```bash
python booking/run_orderflow_bot.py \
    --exchange edgex \
    --ticker SOL \
    --position-size 1.0 \
    --imbalance-threshold 0.2 \
    --signal-strength-threshold 0.3 \
    --confirmation-ticks 1 \
    --update-interval 0.3 \
    --max-position 5.0 \
    --stop-loss-pct 0.02 \
    --take-profit-pct 0.01 \
    --simulate \
    --enable-logging
```

**特点**:
- 几乎任何失衡都会触发
- 交易频率最高
- 需要非常严格的风险控制
- 建议只在模拟模式下测试

## 📈 参数对比表

| 参数 | 默认值 | 平衡设置 | 激进设置 | 非常激进 |
|------|--------|---------|---------|---------|
| `imbalance_threshold` | 0.6 | 0.4 | 0.3 | 0.2 |
| `signal_strength_threshold` | 0.7 | 0.5 | 0.4 | 0.3 |
| `confirmation_ticks` | 3 | 2 | 1 | 1 |
| `update_interval` | 0.5 | 0.4 | 0.3 | 0.3 |
| `position_size` | 0.1 | 1.0 | 1.0 | 1.0 |
| **预期触发频率** | 低 | 中 | 高 | 非常高 |

## 🔍 信号生成逻辑说明

理解信号生成逻辑有助于更好地调整参数：

### 信号强度计算

信号强度由以下部分组成：
1. **订单簿失衡** (40%权重): `abs(imbalance) * 0.4`
2. **加权失衡** (30%权重): `abs(weighted_imbalance) * 0.3`
3. **交易流失衡** (20%权重): `abs(trade_imbalance) * 0.2` (需要 > 0.3)
4. **价格动量** (10%权重): `min(abs(momentum) * 100, 0.1)` (需要 > 0.1%)

### 触发条件

信号必须满足：
1. ✅ 至少一个指标超过阈值（失衡阈值或交易流失衡0.3或动量0.1%）
2. ✅ 总信号强度 >= `signal_strength_threshold`
3. ✅ 连续 `confirmation_ticks` 个相同方向的信号

### 如何让SOL更容易触发

1. **降低失衡阈值**: 让更小的失衡也能触发（最重要）
2. **降低信号强度阈值**: 让更弱的信号也能通过（最重要）
3. **减少确认tick数**: 更快响应，不需要等待多个确认
4. **缩短更新间隔**: 更频繁检查，不错过机会

## ⚠️ 注意事项

### 1. 假信号风险

降低阈值会增加假信号的风险：
- 建议先用 `--simulate` 模式测试
- 观察信号质量，调整参数
- 逐步降低阈值，不要一次性降太多

### 2. 风险控制

更容易触发意味着：
- 交易频率增加
- 需要更严格的风险控制
- 建议设置合理的止损和最大持仓

### 3. 市场适应性

不同市场时段可能需要不同参数：
- **高波动时段**: 可以使用更激进的设置
- **低波动时段**: 建议使用平衡设置
- **重要事件**: 建议使用保守设置

### 4. 回测验证

调整参数后建议：
1. 先用模拟模式运行一段时间
2. 分析信号质量和交易结果
3. 根据结果微调参数
4. 再进行真实交易

## 📝 测试步骤

### 步骤1: 使用平衡设置测试

```bash
python booking/run_orderflow_bot.py \
    --exchange edgex \
    --ticker SOL \
    --imbalance-threshold 0.4 \
    --signal-strength-threshold 0.5 \
    --confirmation-ticks 2 \
    --simulate \
    --enable-logging
```

运行1-2小时，观察：
- 信号生成频率
- 信号质量
- 是否满足你的需求

### 步骤2: 根据结果调整

如果信号太少：
- 降低 `imbalance_threshold` 到 0.3
- 降低 `signal_strength_threshold` 到 0.4
- 减少 `confirmation_ticks` 到 1

如果假信号太多：
- 提高 `imbalance_threshold` 到 0.5
- 提高 `signal_strength_threshold` 到 0.6
- 增加 `confirmation_ticks` 到 2-3

### 步骤3: 优化后运行

找到合适的参数后，可以：
- 继续模拟模式运行
- 或切换到真实交易模式（移除 `--simulate`）

## 🎯 快速开始

**最简单的让SOL更容易触发的方法**:

```bash
python booking/run_orderflow_bot.py \
    --exchange edgex \
    --ticker SOL \
    --imbalance-threshold 0.3 \
    --signal-strength-threshold 0.4 \
    --confirmation-ticks 1 \
    --simulate
```

这三个参数的调整就能显著提高触发频率！

## 📚 相关文档

- 完整参数说明: `booking/ORDERFLOW_PARAMETERS.md`
- 多交易对指南: `booking/MULTI_TICKER_GUIDE.md`
- 机器人使用: `booking/ORDERFLOW_BOT_README.md`
- 信号记录: `booking/SIGNALS_RECORDING.md`
