# 订单流策略参数说明

本文档详细说明订单流策略的所有配置参数。

## 📋 参数总览

### 基础参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `exchange` | str | `edgex` | 交易所名称（如：edgex, backpack等） |
| `ticker` | str | `ETH` | 交易对符号（如：ETH, BTC, SOL） |
| `contract_id` | str | - | 合约ID（自动解析，通常与ticker相同） |

### 订单簿分析参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `orderbook_depth` | int | `20` | 订单簿深度（监控的买卖盘层数） |
| `imbalance_threshold` | float | `0.6` | 失衡阈值（0-1之间），超过此值认为订单簿失衡 |
| `min_order_size` | Decimal | `10000` | 最小监控订单规模（美元），小于此规模的订单不参与分析 |

### 交易流监控参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `large_order_threshold` | Decimal | `50000` | 大单阈值（美元），超过此规模的订单被视为大单 |
| `trade_flow_window` | int | `60` | 交易流时间窗口（秒），分析最近N秒内的交易流 |

### 信号生成参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `signal_strength_threshold` | float | `0.7` | 信号强度阈值（0-1），只有强度超过此值的信号才会被考虑 |
| `confirmation_ticks` | int | `3` | 确认所需的连续tick数，信号需要连续N个tick确认才执行 |

### 执行参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `position_size` | Decimal | `0.1` | 每笔交易的头寸大小 |
| `max_position` | Decimal | `1.0` | 最大持仓限制，超过此值不再开新仓 |
| `stop_loss_pct` | Decimal | `0.02` | 止损百分比（如0.02表示2%） |
| `take_profit_pct` | Decimal | `0.01` | 止盈百分比（如0.01表示1%） |

### 风险控制参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `max_orders_per_minute` | int | `5` | 每分钟最大订单数，防止过度交易 |
| `max_daily_loss` | Optional[Decimal] | `None` | 每日最大亏损限制（可选），达到此值停止交易 |

### 其他参数

| 参数名 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `update_interval` | float | `0.5` | 策略更新间隔（秒），策略分析订单簿的频率 |
| `enable_logging` | bool | `True` | 是否启用详细日志记录 |

## 🚀 命令行参数

运行 `run_orderflow_bot.py` 时可通过命令行参数设置：

### 必需参数

```bash
--exchange <交易所名称>     # 例如: edgex, backpack
--ticker <交易对>          # 例如: ETH, BTC, SOL
```

### 可选参数

```bash
--position-size <数值>              # 每笔交易的头寸大小（默认: 0.1）
--imbalance-threshold <数值>       # 失衡阈值（默认: 0.6）
--signal-strength-threshold <数值>  # 信号强度阈值（默认: 0.7）
--confirmation-ticks <整数>         # 确认所需的tick数（默认: 3）
--update-interval <数值>            # 更新间隔秒数（默认: 0.5）
--max-position <数值>               # 最大持仓（默认: 1.0）
--stop-loss-pct <数值>              # 止损百分比（默认: 0.02）
--take-profit-pct <数值>            # 止盈百分比（默认: 0.01）
--enable-logging                    # 启用详细日志（默认: False）
--simulate                          # 模拟模式：只跟踪信号，不实际下单
```

## 📝 使用示例

### 基本使用

```bash
python booking/run_orderflow_bot.py --exchange edgex --ticker ETH
```

### 完整参数示例

```bash
python booking/run_orderflow_bot.py \
    --exchange edgex \
    --ticker ETH \
    --position-size 0.1 \
    --imbalance-threshold 0.6 \
    --signal-strength-threshold 0.7 \
    --confirmation-ticks 3 \
    --update-interval 0.5 \
    --max-position 1.0 \
    --stop-loss-pct 0.02 \
    --take-profit-pct 0.01 \
    --enable-logging \
    --simulate
```

### 模拟模式（推荐先测试）

```bash
python booking/run_orderflow_bot.py \
    --exchange edgex \
    --ticker ETH \
    --simulate
```

## ⚙️ 参数调优建议

### 失衡阈值 (`imbalance_threshold`)

- **较低值 (0.5-0.6)**: 更敏感，会捕捉更多信号，但可能产生更多假信号
- **较高值 (0.7-0.8)**: 更保守，只捕捉强烈的失衡信号，信号质量更高但数量较少
- **建议**: 根据市场波动性调整，波动大的市场可以用较高阈值

### 信号强度阈值 (`signal_strength_threshold`)

- **较低值 (0.6-0.7)**: 捕捉更多交易机会，但信号质量可能较低
- **较高值 (0.8-0.9)**: 只捕捉高质量信号，交易频率降低但成功率可能提高
- **建议**: 从0.7开始，根据回测结果调整

### 确认tick数 (`confirmation_ticks`)

- **较少 (1-2)**: 响应更快，但可能被噪音干扰
- **较多 (3-5)**: 更稳健，减少假信号，但可能错过快速机会
- **建议**: 默认3个tick，适合大多数市场

### 更新间隔 (`update_interval`)

- **较短 (0.1-0.3秒)**: 更实时，但消耗更多资源
- **较长 (0.5-1.0秒)**: 资源消耗少，但可能错过快速变化
- **建议**: 0.5秒是平衡点，适合大多数情况

### 头寸大小 (`position_size`)

- **较小 (0.05-0.1)**: 风险较低，适合测试或保守策略
- **较大 (0.2-0.5)**: 收益潜力更大，但风险也更高
- **建议**: 从0.1开始，根据账户规模和风险承受能力调整

### 止损/止盈 (`stop_loss_pct` / `take_profit_pct`)

- **止损**: 建议设置在1-3%之间，根据市场波动性调整
- **止盈**: 建议设置为止损的一半到相等，保持风险收益比
- **建议**: 默认2%止损、1%止盈是保守设置

## 🔍 参数在代码中的位置

### 配置文件

所有参数定义在 `booking/config.py` 的 `OrderFlowConfig` 类中：

```python
@dataclass
class OrderFlowConfig:
    # 基础参数
    exchange: str
    ticker: str
    contract_id: str
    
    # 订单簿分析参数
    orderbook_depth: int = 20
    imbalance_threshold: float = 0.6
    min_order_size: Decimal = Decimal(10000)
    
    # ... 其他参数
```

### 命令行解析

命令行参数在 `booking/run_orderflow_bot.py` 的 `main()` 函数中解析：

```python
parser.add_argument('--exchange', type=str, default='edgex')
parser.add_argument('--ticker', type=str, default='ETH')
# ... 其他参数
```

## 📊 参数关系图

```
订单流策略参数
│
├── 基础参数 (exchange, ticker, contract_id)
│
├── 分析参数
│   ├── 订单簿分析 (orderbook_depth, imbalance_threshold, min_order_size)
│   └── 交易流监控 (large_order_threshold, trade_flow_window)
│
├── 信号参数
│   ├── 信号生成 (signal_strength_threshold)
│   └── 信号确认 (confirmation_ticks)
│
├── 执行参数
│   ├── 头寸管理 (position_size, max_position)
│   └── 止盈止损 (stop_loss_pct, take_profit_pct)
│
└── 控制参数
    ├── 风险控制 (max_orders_per_minute, max_daily_loss)
    └── 系统参数 (update_interval, enable_logging)
```

## ⚠️ 注意事项

1. **参数相互影响**: 某些参数会相互影响，调整时需要综合考虑
2. **市场适应性**: 不同市场（如ETH vs BTC）可能需要不同的参数设置
3. **回测验证**: 调整参数后建议先进行回测验证
4. **模拟测试**: 在真实交易前，建议先用 `--simulate` 模式测试
5. **风险控制**: 始终设置合理的止损和最大持仓限制

## 🎯 SOL交易对快速优化

如果想让SOL更容易触发，可以使用以下参数：

### 快速配置（更容易触发）

```bash
python booking/run_orderflow_bot.py \
    --exchange edgex \
    --ticker SOL \
    --imbalance-threshold 0.3 \
    --signal-strength-threshold 0.4 \
    --confirmation-ticks 1 \
    --simulate
```

### 关键参数调整

| 参数 | 默认值 | SOL推荐值 | 说明 |
|------|--------|-----------|------|
| `imbalance_threshold` | 0.6 | **0.3-0.4** | 降低此值让策略更敏感 |
| `signal_strength_threshold` | 0.7 | **0.4-0.5** | 降低此值让更多信号通过 |
| `confirmation_ticks` | 3 | **1-2** | 减少确认次数，更快响应 |

**详细说明**: 查看 `booking/SOL_OPTIMIZATION_GUIDE.md`

## 📚 相关文档

- **SOL优化指南**: `booking/SOL_OPTIMIZATION_GUIDE.md` ⭐ 推荐
- 策略详情: `booking/STRATEGY_DETAILS.md`
- 回测指南: `booking/BACKTEST_GUIDE.md`
- 机器人使用: `booking/ORDERFLOW_BOT_README.md`
- 信号记录: `booking/SIGNALS_RECORDING.md`
