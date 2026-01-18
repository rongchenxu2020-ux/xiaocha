# 订单流策略回测系统使用指南

## 概述

回测系统允许您使用历史数据测试订单流交易策略，评估策略性能，优化参数设置。

## 快速开始

### 1. 使用模拟数据快速测试

```bash
python booking/run_backtest.py \
    --generate-mock \
    --start-price 2000 \
    --num-samples 1000 \
    --exchange edgex \
    --ticker ETH
```

### 2. 使用JSON数据文件

```bash
python booking/run_backtest.py \
    --data data.json \
    --exchange edgex \
    --ticker ETH
```

### 3. 使用CSV数据文件

```bash
python booking/run_backtest.py \
    --orderbook-csv orderbook.csv \
    --trades-csv trades.csv \
    --exchange edgex \
    --ticker ETH
```

## 数据格式

### JSON格式

```json
{
    "orderbooks": [
        {
            "timestamp": 1234567890.0,
            "bids": [[2000.0, 10.5], [1999.5, 15.2]],
            "asks": [[2000.5, 12.3], [2001.0, 8.7]]
        }
    ],
    "trades": [
        {
            "timestamp": 1234567890.0,
            "price": 2000.0,
            "size": 0.1,
            "side": "buy",
            "trade_id": "trade_001"
        }
    ]
}
```

### CSV格式

**订单簿CSV (orderbook.csv)**:
```csv
timestamp,bid_price,bid_size,ask_price,ask_size
1234567890.0,2000.0,10.5,2000.5,12.3
1234567891.0,2000.1,11.2,2000.6,13.1
```

**交易CSV (trades.csv)**:
```csv
timestamp,price,size,side
1234567890.0,2000.0,0.1,buy
1234567891.0,2000.2,0.15,sell
```

## 参数说明

### 数据源参数

- `--data`: JSON格式的回测数据文件
- `--orderbook-csv`: 订单簿CSV文件
- `--trades-csv`: 交易CSV文件（可选）
- `--generate-mock`: 生成模拟数据进行回测

### 模拟数据参数

- `--start-price`: 起始价格（默认: 2000）
- `--num-samples`: 样本数量（默认: 1000）
- `--interval-seconds`: 时间间隔，秒（默认: 1.0）
- `--volatility`: 价格波动率（默认: 0.001）

### 策略参数

与实时策略相同的参数，包括：
- `--imbalance-threshold`: 失衡阈值（默认: 0.6）
- `--signal-strength-threshold`: 信号强度阈值（默认: 0.7）
- `--position-size`: 每笔交易的头寸大小（默认: 0.1）
- `--max-position`: 最大持仓（默认: 1.0）
- 等等...

### 回测参数

- `--initial-balance`: 初始资金（默认: 10000）

### 输出参数

- `--output-dir`: 输出目录（默认: backtest_results）
- `--export-trades`: 导出交易记录到CSV
- `--export-equity`: 导出权益曲线到CSV

## 回测报告

回测系统会生成详细的文本报告，包括：

### 基础信息
- 初始资金、最终资金
- 总盈亏、总收益率

### 交易统计
- 总交易次数
- 盈利/亏损交易数
- 胜率
- 平均盈利/亏损
- 盈利因子

### 风险指标
- 最大回撤
- 最大回撤持续时间
- 夏普比率
- 索提诺比率

### 其他指标
- 平均持仓时间
- 最大连续盈利/亏损
- 信号生成和执行统计

## 完整示例

```bash
# 使用模拟数据，自定义策略参数
python booking/run_backtest.py \
    --generate-mock \
    --start-price 2000 \
    --num-samples 5000 \
    --interval-seconds 0.5 \
    --volatility 0.002 \
    --exchange edgex \
    --ticker ETH \
    --imbalance-threshold 0.6 \
    --signal-strength-threshold 0.7 \
    --position-size 0.1 \
    --max-position 1.0 \
    --initial-balance 10000 \
    --export-trades \
    --export-equity \
    --output-dir my_backtest_results
```

## 性能指标说明

### 胜率 (Win Rate)
盈利交易数 / 总交易数

### 盈利因子 (Profit Factor)
总盈利 / 总亏损

### 最大回撤 (Max Drawdown)
从峰值到谷值的最大跌幅

### 夏普比率 (Sharpe Ratio)
衡量风险调整后的收益
- > 1: 良好
- > 2: 优秀
- > 3: 卓越

### 索提诺比率 (Sortino Ratio)
类似夏普比率，但只考虑下行风险

## 优化建议

1. **参数优化**: 使用不同的参数组合进行多次回测，找到最优参数
2. **数据质量**: 确保历史数据的质量和完整性
3. **样本外测试**: 保留部分数据用于样本外测试
4. **过拟合风险**: 避免过度优化参数导致过拟合

## 注意事项

⚠️ **重要提醒**:
- 回测结果不代表未来表现
- 历史数据可能不包含所有市场情况
- 实际交易中可能存在滑点、手续费等成本
- 建议结合实盘测试验证策略有效性

## 导出数据

### 导出交易记录
```bash
python booking/run_backtest.py \
    --data data.json \
    --exchange edgex \
    --ticker ETH \
    --export-trades
```

### 导出权益曲线
```bash
python booking/run_backtest.py \
    --data data.json \
    --exchange edgex \
    --ticker ETH \
    --export-equity
```

导出的CSV文件可用于：
- Excel分析
- Python可视化
- 进一步的数据分析

## 故障排除

### 问题：数据加载失败

**解决方案**:
1. 检查数据文件格式是否正确
2. 确保时间戳格式正确
3. 检查价格和数量是否为有效数字

### 问题：回测结果异常

**解决方案**:
1. 检查策略参数是否合理
2. 验证数据质量
3. 查看日志中的错误信息

## 下一步

- 使用回测结果优化策略参数
- 进行样本外测试
- 在模拟环境中测试策略
- 逐步过渡到实盘交易
