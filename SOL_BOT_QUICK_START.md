# SOL订单流机器人 - 快速开始指南

## 📋 概述

SOL订单流机器人是专门针对SOL交易对优化的订单流策略机器人，通过降低触发阈值来**提升订单流策略的触发可能性**。

## 🚀 快速启动

### 方式1: 使用启动脚本（最简单）

**Windows批处理:**
```bash
# 平衡设置（推荐首次使用）
start_sol_orderflow_bot.bat balanced

# 激进设置（更容易触发）
start_sol_orderflow_bot.bot aggressive
```

**PowerShell:**
```powershell
# 平衡设置
.\start_sol_orderflow_bot.ps1 balanced

# 激进设置
.\start_sol_orderflow_bot.ps1 aggressive
```

### 方式2: 直接运行Python脚本

```bash
# 平衡设置（推荐）
python booking/run_sol_orderflow_bot.py --mode balanced --simulate

# 激进设置（更容易触发）
python booking/run_sol_orderflow_bot.py --mode aggressive --simulate

# 非常激进设置（最大化触发频率）
python booking/run_sol_orderflow_bot.py --mode very-aggressive --simulate
```

## 📊 运行模式对比

| 模式 | 失衡阈值 | 信号强度阈值 | 确认tick数 | 触发频率 | 适用场景 |
|------|---------|------------|-----------|---------|---------|
| **balanced** | 0.4 | 0.5 | 2 | 中等 | 推荐首次使用 |
| **aggressive** | 0.3 | 0.4 | 1 | 高 | 希望更多交易机会 |
| **very-aggressive** | 0.2 | 0.3 | 1 | 非常高 | 最大化触发频率 |

## ⚙️ 关键优化参数

相比默认配置，SOL机器人做了以下优化：

1. ✅ **失衡阈值**: 0.6 → **0.2-0.4** (降低50-67%)
2. ✅ **信号强度阈值**: 0.7 → **0.3-0.5** (降低29-57%)
3. ✅ **确认tick数**: 3 → **1-2** (减少33-67%)
4. ✅ **更新间隔**: 0.5秒 → **0.3-0.4秒** (缩短20-40%)
5. ✅ **最小订单规模**: 10000 → **5000美元** (降低50%)
6. ✅ **大单阈值**: 50000 → **30000美元** (降低40%)

## 📝 使用步骤

### 步骤1: 首次测试（推荐）

```bash
# 使用平衡模式 + 模拟模式
python booking/run_sol_orderflow_bot.py --mode balanced --simulate --enable-logging
```

运行1-2小时，观察：
- 信号生成频率
- 信号质量
- 是否满足需求

### 步骤2: 根据结果调整

**如果信号太少:**
```bash
# 切换到激进模式
python booking/run_sol_orderflow_bot.py --mode aggressive --simulate
```

**如果假信号太多:**
```bash
# 使用自定义参数，提高阈值
python booking/run_sol_orderflow_bot.py --mode custom \
    --imbalance-threshold 0.5 \
    --signal-strength-threshold 0.6 \
    --confirmation-ticks 2 \
    --simulate
```

### 步骤3: 真实交易

确认参数合适后，移除 `--simulate` 进行真实交易：

```bash
# ⚠️ 警告：这将使用真实资金！
python booking/run_sol_orderflow_bot.py --mode balanced
```

## 📈 预期效果

使用SOL优化配置后，预期可以：

- ✅ **触发频率提升**: 相比默认配置，信号生成频率提升 **2-5倍**
- ✅ **更快响应**: 更短的更新间隔和确认时间，更快捕捉市场机会
- ✅ **更多机会**: 降低阈值让更多市场失衡被识别

## ⚠️ 注意事项

1. **首次使用建议模拟模式**: 使用 `--simulate` 参数先测试
2. **风险控制**: 更容易触发意味着交易频率增加，需要更严格的风险控制
3. **假信号风险**: 降低阈值会增加假信号的风险，需要观察和调整
4. **市场适应性**: 不同市场时段可能需要不同参数

## 📚 相关文档

- **详细优化指南**: `booking/SOL_OPTIMIZATION_GUIDE.md` ⭐
- **参数说明**: `booking/ORDERFLOW_PARAMETERS.md`
- **策略详情**: `booking/README.md`
- **信号记录**: `booking/SIGNALS_RECORDING.md`

## 🆘 常见问题

### Q: 如何查看生成的信号？

A: 信号会记录在 `logs/orderflow_signals_edgex_SOL_simulate_YYYYMMDD.csv` 文件中。

### Q: 如何监控机器人运行状态？

A: 可以使用 `monitor_sol_bot.ps1` 脚本监控：
```powershell
.\monitor_sol_bot.ps1
```

### Q: 如何停止机器人？

A: 按 `Ctrl+C` 停止机器人。

### Q: 信号太少怎么办？

A: 尝试使用 `aggressive` 或 `very-aggressive` 模式，或进一步降低阈值参数。

### Q: 假信号太多怎么办？

A: 提高 `--imbalance-threshold` 和 `--signal-strength-threshold` 参数，或增加 `--confirmation-ticks`。

## 🎯 快速命令参考

```bash
# 最简单的启动方式（平衡模式 + 模拟）
python booking/run_sol_orderflow_bot.py --mode balanced --simulate

# 最容易触发的配置
python booking/run_sol_orderflow_bot.py --mode very-aggressive --simulate

# 自定义参数
python booking/run_sol_orderflow_bot.py --mode custom \
    --imbalance-threshold 0.3 \
    --signal-strength-threshold 0.4 \
    --confirmation-ticks 1 \
    --simulate
```

---

**提示**: 建议先阅读 `booking/SOL_OPTIMIZATION_GUIDE.md` 了解详细的参数调整策略。
