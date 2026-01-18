# 项目架构审查报告

## 发现的问题

### 1. 路径引用错误（严重问题）

多个文件引用了不存在的 `订单流交易策略` 目录，但实际目录是 `booking`。这些文件无法正常工作：

**受影响的文件：**
- `run_backtest_simple.py` - 引用了 `订单流交易策略.config` 等模块
- `run_backtest_wrapper.py` - 引用了 `订单流交易策略/run_backtest.py`
- `simple_test.py` - 引用了 `订单流交易策略` 模块
- `test_orderflow.py` - 引用了 `订单流交易策略` 模块
- `booking/test_strategy.py` - 引用了 `订单流交易策略` 模块
- `booking/run_orderflow.py` - 引用了 `订单流交易策略` 模块

**建议：**
- 删除这些无法工作的文件，或
- 修复所有路径引用，将 `订单流交易策略` 改为 `booking`

### 2. 重复的回测脚本

**根目录：**
- `run_backtest_simple.py` - 简化的回测脚本（路径错误）
- `run_backtest_wrapper.py` - 包装脚本（路径错误）

**booking目录：**
- `run_backtest.py` - 实际使用的回测脚本 ✅

**建议：**
- 删除根目录的两个回测脚本（`run_backtest_simple.py` 和 `run_backtest_wrapper.py`）
- 统一使用 `booking/run_backtest.py`

### 3. 重复的测试文件

**根目录：**
- `simple_test.py` - 简单测试（路径错误）
- `test_orderflow.py` - 订单流测试（路径错误）
- `test_edgex_simple.py` - EdgeX简单测试
- `test_exchange_api.py` - 交易所API测试

**booking目录：**
- `test_strategy.py` - 策略测试（路径错误）

**建议：**
- 删除路径错误的测试文件
- 保留 `test_edgex_simple.py` 和 `test_exchange_api.py`（如果它们能正常工作）
- 修复 `booking/test_strategy.py` 的路径引用

### 4. 重复的订单流入口

**booking目录：**
- `run_orderflow.py` - 命令行入口（路径错误，引用了不存在的模块）
- `run_orderflow_bot.py` - 实时交易机器人 ✅（实际使用）

**建议：**
- 删除或修复 `run_orderflow.py`（如果不再需要）
- 保留 `run_orderflow_bot.py`（这是实际使用的入口）

### 5. 文档重复

**booking目录中的文档：**
- `QUICK_TEST.md` - 快速测试指南
- `RUN_TEST.md` - 运行测试指南（内容与QUICK_TEST.md重叠）
- `USAGE.md` - 使用指南（与README.md有重叠）
- `README.md` - 主文档
- `BACKTEST_GUIDE.md` - 回测指南
- `ORDERFLOW_BOT_README.md` - 订单流机器人文档
- `MONITOR_GUI_README.md` - 监控GUI文档
- `MULTI_TICKER_GUIDE.md` - 多交易对指南
- `SIGNALS_RECORDING.md` - 信号记录文档
- `DATA_SOURCES.md` - 数据源文档
- `STRATEGY_DETAILS.md` - 策略详情文档

**建议：**
- 合并 `QUICK_TEST.md` 和 `RUN_TEST.md`（内容高度重叠）
- 考虑将 `USAGE.md` 的内容整合到 `README.md` 中
- 保留其他专业文档（BACKTEST_GUIDE.md, ORDERFLOW_BOT_README.md等）

### 6. 历史数据文件

**booking目录中的JSON文件：**
- `example_data.json` - 示例数据 ✅（保留）
- `historical_data_1500.json` - 历史数据（可能不再需要）
- `real_data_edgex_ETH_20260111_215135.json` - 真实数据（测试数据）
- `real_data_edgex_ETH_20260111_224028.json` - 真实数据（测试数据）
- `real_data_edgex_ETH_20260111_225601.json` - 真实数据（测试数据）

**建议：**
- 保留 `example_data.json` 作为示例
- 考虑将其他数据文件移动到 `data/` 或 `backtest_data/` 目录
- 或者删除不再使用的测试数据文件

### 7. 其他可能多余的文件

- `diagnose_no_trades.py` - 诊断脚本（如果不再使用）
- `generate_test_report.py` - 测试报告生成器（如果功能已整合到其他模块）
- `monitor_sol_bot.ps1` - PowerShell脚本（如果不再使用）

## 建议的清理操作

### 优先级1：修复或删除无法工作的文件

1. **删除路径错误的文件：**
   ```
   - run_backtest_simple.py
   - run_backtest_wrapper.py
   - simple_test.py
   - test_orderflow.py
   - booking/test_strategy.py（或修复路径）
   - booking/run_orderflow.py（或修复路径）
   ```

2. **修复文档中的错误路径引用：**
   - 更新所有文档中的 `订单流交易策略` 为 `booking`

### 优先级2：整理文档

1. **合并重复文档：**
   - 合并 `QUICK_TEST.md` 和 `RUN_TEST.md`
   - 将 `USAGE.md` 内容整合到 `README.md`

2. **更新文档中的路径引用**

### 优先级3：整理数据文件

1. **创建数据目录：**
   ```
   booking/data/
   ```

2. **移动历史数据文件到数据目录**

## 项目结构建议

```
perp-dex-tools-main/
├── booking/                    # 订单流策略模块
│   ├── __init__.py
│   ├── config.py
│   ├── orderflow_strategy.py
│   ├── backtest_*.py          # 回测相关
│   ├── run_orderflow_bot.py   # 主入口
│   ├── monitor_bots_gui.py
│   ├── data/                  # 数据文件目录
│   │   ├── example_data.json
│   │   └── historical_*.json
│   └── docs/                  # 文档目录（可选）
│       ├── README.md
│       ├── BACKTEST_GUIDE.md
│       └── ...
├── exchanges/                  # 交易所模块
├── hedge/                      # 对冲模式
├── helpers/                    # 辅助模块
├── tests/                      # 测试文件
│   ├── test_edgex_simple.py
│   └── test_exchange_api.py
├── runbot.py                   # 主交易机器人
├── hedge_mode.py              # 对冲模式入口
└── README.md                   # 主文档
```

## 总结

**主要问题：**
1. 多个文件引用了不存在的 `订单流交易策略` 目录
2. 存在重复的测试和回测脚本
3. 文档内容有重叠

**已完成的清理操作：**
1. ✅ 删除了无法工作的文件：
   - `run_backtest_simple.py`
   - `run_backtest_wrapper.py`
   - `simple_test.py`
   - `test_orderflow.py`

2. ✅ 修复了路径引用：
   - `booking/run_orderflow.py` - 已修复
   - `booking/test_strategy.py` - 已修复
   - `booking/run_backtest.py` - 已修复
   - 所有文档中的路径引用已更新

3. ✅ 整理了文档结构：
   - 合并 `QUICK_TEST.md` 和 `RUN_TEST.md` 为 `TEST_GUIDE.md`
   - 整合 `USAGE.md` 内容到 `README.md`
   - 删除了重复的文档文件
   - 修复了所有文档中的路径引用

4. ✅ 整理了数据文件：
   - 创建了 `booking/data/` 目录
   - 移动了历史数据文件到 `data/` 目录
   - 保留了 `example_data.json` 作为示例

**当前项目结构：**
```
perp-dex-tools-main/
├── booking/                    # 订单流策略模块
│   ├── __init__.py
│   ├── config.py
│   ├── orderflow_strategy.py
│   ├── backtest_*.py          # 回测相关
│   ├── run_orderflow_bot.py   # 主入口（实时交易）
│   ├── run_orderflow.py       # 命令行入口（已修复）
│   ├── test_strategy.py       # 测试脚本（已修复）
│   ├── monitor_bots_gui.py
│   ├── data/                  # 数据文件目录
│   │   ├── example_data.json
│   │   └── historical_*.json
│   └── docs/                  # 文档
│       ├── README.md          # 主文档（已更新）
│       ├── BACKTEST_GUIDE.md  # 回测指南（已修复路径）
│       ├── TEST_GUIDE.md      # 测试指南（合并后）
│       └── ...
├── exchanges/                  # 交易所模块
├── hedge/                      # 对冲模式
├── helpers/                    # 辅助模块
├── tests/                      # 测试文件
├── runbot.py                   # 主交易机器人
└── hedge_mode.py              # 对冲模式入口
```
