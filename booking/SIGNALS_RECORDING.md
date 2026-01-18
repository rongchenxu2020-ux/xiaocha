# 交易信号记录说明

## 信号记录位置

订单流策略机器人会将所有交易信号记录到以下位置：

### 1. CSV文件（推荐查看）

**文件路径**: `logs/orderflow_signals_{exchange}_{ticker}_{mode}_{date}.csv`

**示例文件名**:
- 模拟模式: `logs/orderflow_signals_edgex_ETH_simulate_20260111.csv`
- 真实交易: `logs/orderflow_signals_edgex_ETH_live_20260111.csv`

**CSV文件格式**:

| 列名 | 说明 | 示例 |
|------|------|------|
| Timestamp | 信号生成时间 | 2026-01-11 14:30:25 |
| Direction | 交易方向 | BUY 或 SELL |
| Price | 信号价格 | 2000.50 |
| Strength | 信号强度 (0-1) | 0.7500 |
| Position Size | 建议头寸大小 | 0.1 |
| Reason | 信号原因 | 订单簿买单占优 (失衡: 65.00%) |
| Status | 信号状态 | GENERATED / CONFIRMED_SIMULATE / EXECUTED_SUCCESS / EXECUTED_FAILED |
| Confirmed | 是否已确认 | YES 或 NO |

**状态说明**:
- `GENERATED`: 信号已生成，等待确认
- `CONFIRMED_SIMULATE`: 信号已确认（模拟模式，未实际下单）
- `EXECUTED_SUCCESS`: 信号已确认并成功执行（真实交易模式）
- `EXECUTED_FAILED`: 信号已确认但执行失败（真实交易模式）

### 2. 活动日志文件

**文件路径**: `logs/{exchange}_{ticker}_activity.log`

**示例文件名**: `logs/edgex_ETH_activity.log`

**日志内容**:
- 所有信号生成和确认的详细信息
- 订单簿指标变化
- 交易流指标
- 错误和警告信息

**日志格式**:
```
2026-01-11 14:30:25.123 - INFO - [EDGEX_ETH] 生成信号: BUY @ 2000.50, 强度: 75.00%, 原因: 订单簿买单占优 (失衡: 65.00%)
2026-01-11 14:30:25.456 - INFO - [EDGEX_ETH] 信号已确认 [模拟模式 - 不会实际下单]
2026-01-11 14:30:25.789 - INFO - [EDGEX_ETH]   模拟交易: BUY 0.1 @ 2000.50
```

### 3. 内存中的信号历史

机器人运行时，所有信号也会保存在内存中的 `signals_history` 列表中，可以通过 `get_status()` 方法获取。

## 如何查看信号记录

### 方法1: 直接查看CSV文件

使用Excel、Google Sheets或任何文本编辑器打开CSV文件：

```bash
# Windows
notepad logs\orderflow_signals_edgex_ETH_simulate_20260111.csv

# 或使用Excel
start excel logs\orderflow_signals_edgex_ETH_simulate_20260111.csv
```

### 方法2: 使用Python分析

```python
import pandas as pd
import os

# 读取信号CSV文件
csv_file = "logs/orderflow_signals_edgex_ETH_simulate_20260111.csv"
if os.path.exists(csv_file):
    df = pd.read_csv(csv_file)
    
    # 查看所有信号
    print(df)
    
    # 统计信息
    print(f"总信号数: {len(df)}")
    print(f"买入信号: {len(df[df['Direction'] == 'BUY'])}")
    print(f"卖出信号: {len(df[df['Direction'] == 'SELL'])}")
    print(f"已确认信号: {len(df[df['Confirmed'] == 'YES'])}")
    
    # 平均信号强度
    print(f"平均信号强度: {df['Strength'].mean():.2%}")
```

### 方法3: 查看日志文件

```bash
# Windows PowerShell
Get-Content logs\edgex_ETH_activity.log -Tail 50

# 或搜索特定内容
Select-String -Path logs\edgex_ETH_activity.log -Pattern "信号"
```

## 信号记录示例

### CSV文件示例

```csv
Timestamp,Direction,Price,Strength,Position Size,Reason,Status,Confirmed
2026-01-11 14:30:25,BUY,2000.50,0.7500,0.1,订单簿买单占优 (失衡: 65.00%),GENERATED,NO
2026-01-11 14:30:26,BUY,2000.52,0.7800,0.1,订单簿买单占优 (失衡: 68.00%),GENERATED,NO
2026-01-11 14:30:27,BUY,2000.55,0.8000,0.1,订单簿买单占优 (失衡: 70.00%),CONFIRMED_SIMULATE,YES
2026-01-11 14:35:10,SELL,2010.20,0.7200,0.1,订单簿卖单占优 (失衡: -62.00%),GENERATED,NO
2026-01-11 14:35:11,SELL,2010.25,0.7500,0.1,订单簿卖单占优 (失衡: -65.00%),CONFIRMED_SIMULATE,YES
```

### 日志文件示例

```
2026-01-11 14:30:25.123 - INFO - [EDGEX_ETH] 生成信号: BUY @ 2000.50, 强度: 75.00%, 原因: 订单簿买单占优 (失衡: 65.00%)
2026-01-11 14:30:25.456 - INFO - [EDGEX_ETH] 等待信号确认 (1/1)
2026-01-11 14:30:26.123 - INFO - [EDGEX_ETH] 生成信号: BUY @ 2000.52, 强度: 78.00%, 原因: 订单簿买单占优 (失衡: 68.00%)
2026-01-11 14:30:26.456 - INFO - [EDGEX_ETH] 等待信号确认 (2/1)
2026-01-11 14:30:27.123 - INFO - [EDGEX_ETH] 生成信号: BUY @ 2000.55, 强度: 80.00%, 原因: 订单簿买单占优 (失衡: 70.00%)
2026-01-11 14:30:27.456 - INFO - [EDGEX_ETH] 信号已确认 [模拟模式 - 不会实际下单]
2026-01-11 14:30:27.789 - INFO - [EDGEX_ETH]   模拟交易: BUY 0.1 @ 2000.55
```

## 注意事项

1. **文件位置**: 所有日志文件都保存在项目根目录的 `logs/` 文件夹中
2. **文件命名**: CSV文件按日期命名，每天会创建新文件
3. **编码格式**: 所有文件使用UTF-8编码，确保中文正确显示
4. **实时更新**: 信号生成后会立即写入CSV和日志文件
5. **文件大小**: 长时间运行可能会产生较大的日志文件，建议定期清理

## 分析信号数据

### 使用Python进行数据分析

```python
import pandas as pd
import matplotlib.pyplot as plt

# 读取数据
df = pd.read_csv('logs/orderflow_signals_edgex_ETH_simulate_20260111.csv')
df['Timestamp'] = pd.to_datetime(df['Timestamp'])

# 按方向统计
buy_signals = df[df['Direction'] == 'BUY']
sell_signals = df[df['Direction'] == 'SELL']

print(f"买入信号: {len(buy_signals)}")
print(f"卖出信号: {len(sell_signals)}")
print(f"平均信号强度: {df['Strength'].mean():.2%}")

# 绘制信号强度分布
plt.figure(figsize=(10, 6))
plt.plot(df['Timestamp'], df['Strength'], label='信号强度')
plt.xlabel('时间')
plt.ylabel('信号强度')
plt.title('信号强度随时间变化')
plt.legend()
plt.show()
```

## 故障排除

如果看不到信号记录：

1. **检查logs目录**: 确保 `logs/` 目录存在且可写
2. **检查文件权限**: 确保程序有写入权限
3. **查看控制台输出**: 检查是否有错误信息
4. **检查策略参数**: 确保阈值设置合理，能够生成信号
