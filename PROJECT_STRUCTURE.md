# 项目结构说明

## 项目概述

这是一个支持多交易所的模块化交易机器人项目，包含策略交易、对冲交易、持仓管理、回测等功能。

## 目录结构

```
perp-dex-tools-main/
├── 📁 核心模块
│   ├── trading_bot.py           # 主交易机器人
│   ├── runbot.py                # 交易机器人启动脚本
│   ├── position_manager.py      # 持仓管理模块
│   └── hedge_mode.py            # 对冲模式主入口
│
├── 📁 策略模块 (strategies/)
│   ├── orderflow_strategy.py    # 订单流策略
│   ├── market_maker_strategy.py # 做市商策略
│   ├── run_orderflow_bot.py     # 订单流机器人启动脚本
│   ├── run_market_maker_bot.py  # 做市商机器人启动脚本
│   └── ...
│
├── 📁 回测模块 (backtest/)
│   ├── backtest_engine.py       # 回测引擎（可被不同策略使用）
│   ├── backtest_data.py         # 回测数据加载
│   ├── backtest_report.py       # 回测报告生成
│   └── run_backtest.py          # 回测启动脚本
│
├── 📁 共享组件 (shared/)
│   ├── config.py                # 配置（策略和回测共用）
│   ├── orderbook_analyzer.py    # 订单簿分析器
│   ├── trade_flow_monitor.py    # 交易流监控
│   └── performance_metrics.py   # 性能指标计算
│
├── 📁 交易所客户端 (exchanges/)
│   ├── base.py                  # 交易所客户端基类
│   ├── factory.py               # 交易所工厂
│   ├── edgex.py                 # EdgeX 交易所客户端
│   ├── backpack.py              # Backpack 交易所客户端
│   ├── paradex.py               # Paradex 交易所客户端
│   ├── aster.py                 # Aster 交易所客户端
│   ├── lighter.py               # Lighter 交易所客户端
│   ├── grvt.py                  # GRVT 交易所客户端
│   ├── extended.py              # Extended 交易所客户端
│   ├── apex.py                  # Apex 交易所客户端
│   └── nado.py                  # Nado 交易所客户端
│
├── 📁 对冲模式 (hedge/)
│   ├── hedge_mode_edgex.py      # EdgeX 对冲机器人
│   ├── hedge_mode_bp.py         # Backpack 对冲机器人
│   ├── hedge_mode_grvt.py       # GRVT 对冲机器人
│   ├── hedge_mode_grvt_v2.py    # GRVT 对冲机器人 v2
│   ├── hedge_mode_ext.py        # Extended 对冲机器人
│   ├── hedge_mode_apex.py       # Apex 对冲机器人
│   └── hedge_mode_nado.py       # Nado 对冲机器人
│
├── 📁 辅助模块 (helpers/)
│   ├── logger.py                # 日志记录器
│   ├── telegram_bot.py          # Telegram 通知机器人
│   └── lark_bot.py              # Lark 通知机器人
│
├── 📁 策略模块 (strategies/)
│   ├── orderflow_strategy.py      # 订单流策略
│   ├── market_maker_strategy.py   # 做市商策略
│   ├── run_orderflow_bot.py       # 订单流机器人启动脚本
│   ├── run_market_maker_bot.py    # 做市商机器人启动脚本
│   ├── run_orderflow.py           # 订单流运行脚本
│   ├── run_sol_orderflow_bot.py   # SOL订单流机器人
│   └── run_lighter_market_maker.py # Lighter做市商机器人
│
├── 📁 回测模块 (backtest/)
│   ├── backtest_engine.py         # 回测引擎（可被不同策略使用）
│   ├── backtest_data.py           # 回测数据加载
│   ├── backtest_report.py         # 回测报告生成
│   └── run_backtest.py            # 回测启动脚本
│
├── 📁 共享组件 (shared/)
│   ├── config.py                  # 配置（策略和回测共用）
│   ├── orderbook_analyzer.py      # 订单簿分析器
│   ├── trade_flow_monitor.py      # 交易流监控
│   └── performance_metrics.py     # 性能指标计算
│
├── 📁 脚本目录 (scripts/)
│   ├── backtest/                  # 回测分析脚本
│   │   ├── final_backtest_summary.py
│   │   ├── quick_backtest_summary.py
│   │   ├── backtest_comparison.py
│   │   ├── backtest_with_stop_loss_summary.py
│   │   ├── calculate_backtest_profit.py
│   │   └── generate_test_report.py
│   │
│   ├── test/                    # 测试脚本
│   │   ├── test_edgex_realtime_data.py
│   │   ├── test_edgex_simple.py
│   │   ├── test_edgex_strategy_backtest.py
│   │   ├── test_edgex_strategy_order.py
│   │   ├── test_edgex_continuous_data.py
│   │   ├── test_edgex_precise_backtest.py
│   │   ├── test_exchange_api.py
│   │   └── test_gui.py
│   │
│   ├── diagnose/                # 诊断脚本
│   │   ├── diagnose_no_trades.py
│   │   ├── diagnose_websocket_connection.py
│   │   ├── check_websocket_config.py
│   │   └── explain_trade_difference.py
│   │
│   └── utils/                   # 工具脚本
│       ├── quick_profit_calc.py
│       ├── position_manager_example.py
│       └── monitor_sol_bot.ps1
│
├── 📁 文档 (docs/)
│   ├── ADDING_EXCHANGES.md      # 添加交易所指南
│   ├── telegram-bot-setup.md    # Telegram 机器人设置
│   └── telegram-bot-setup-en.md # Telegram 机器人设置（英文）
│
├── 📁 测试 (tests/)
│   └── test_query_retry.py      # 查询重试测试
│
├── 📁 数据目录
│   ├── backtest_results/        # 回测结果
│   ├── edgex_data/              # EdgeX 历史数据
│   └── booking/data/            # 回测数据
│
├── 📄 配置文件
│   ├── .env                     # 环境变量（需自行创建）
│   ├── env_example.txt          # 环境变量示例
│   ├── requirements.txt         # Python 依赖
│   ├── apex_requirements.txt    # Apex 特定依赖
│   └── .gitignore               # Git 忽略文件
│
└── 📄 文档文件
    ├── README.md                # 主文档（中文）
    ├── README_EN.md             # 主文档（英文）
    ├── POSITION_MANAGER_README.md # 持仓管理模块文档
    ├── PROJECT_STRUCTURE.md     # 本文件
    ├── SOL_BOT_QUICK_START.md   # SOL 机器人快速开始
    ├── WEBSOCKET_DIAGNOSIS.md   # WebSocket 诊断
    ├── ARCHITECTURE_REVIEW.md   # 架构审查
    └── booking/                 # booking 模块文档
        ├── README.md
        ├── BACKTEST_GUIDE.md
        ├── ORDERFLOW_BOT_README.md
        └── ...
```

## 核心模块说明

### 1. 交易机器人 (trading_bot.py)

主要交易逻辑实现，支持：
- 自动下单和平仓
- 多交易所支持
- 风险管理
- 网格步长控制

**使用方式：**
```bash
python runbot.py --exchange edgex --ticker ETH --direction buy --quantity 1.0
```

### 2. 持仓管理 (position_manager.py)

持仓管理和控制模块，提供：
- 获取所有持仓
- 检查持仓是否在策略中
- 自动平仓不在策略中的持仓
- 持仓摘要和统计

**使用方式：**
```bash
python position_manager.py ETH SOL --dry-run  # 试运行
python position_manager.py ETH SOL --close    # 执行平仓
```

**文档：** 详见 `POSITION_MANAGER_README.md`

### 3. 对冲模式 (hedge_mode.py)

对冲交易模式，在不同交易所之间进行对冲交易。

**使用方式：**
```bash
python hedge_mode.py --exchange edgex --ticker ETH --quantity 1.0
```

### 4. 交易策略 (strategies/)

包含各种交易策略的实现，包括：
- 订单流策略（OrderFlow Strategy）
- 做市商策略（Market Maker Strategy）

**主要文件：**
- `orderflow_strategy.py`: 订单流策略实现
- `market_maker_strategy.py`: 做市商策略实现
- `run_orderflow_bot.py`: 订单流机器人启动脚本
- `run_market_maker_bot.py`: 做市商机器人启动脚本

### 5. 回测模块 (backtest/)

独立的回测引擎，可以被不同策略使用。回测功能与策略分离，实现了模块化设计。

**主要文件：**
- `backtest_engine.py`: 回测引擎核心实现
- `backtest_data.py`: 回测数据加载和管理
- `backtest_report.py`: 回测报告生成
- `run_backtest.py`: 回测启动脚本

**使用方式：**
```python
from backtest.backtest_engine import BacktestEngine
from strategies.orderflow_strategy import OrderFlowStrategy
# 任何策略都可以使用相同的回测引擎
```

### 6. 共享组件 (shared/)

策略和回测共同使用的组件，包括配置、分析工具等。

**主要文件：**
- `config.py`: 配置类（OrderFlowConfig, MarketMakerConfig等）
- `orderbook_analyzer.py`: 订单簿分析器
- `trade_flow_monitor.py`: 交易流监控
- `performance_metrics.py`: 性能指标计算

## 交易所支持

目前支持的交易所：
- ✅ EdgeX
- ✅ Backpack
- ✅ Paradex
- ✅ Aster
- ✅ Lighter
- ✅ GRVT
- ✅ Extended
- ✅ Apex
- ✅ Nado

每个交易所都有对应的客户端实现（位于 `exchanges/` 目录）和对冲模式实现（位于 `hedge/` 目录）。

## 脚本分类

### 回测脚本 (scripts/backtest/)

用于回测策略和分析回测结果：

- `final_backtest_summary.py`: 最终回测结果总结
- `quick_backtest_summary.py`: 快速回测总结
- `backtest_comparison.py`: 回测参数对比
- `calculate_backtest_profit.py`: 计算回测利润
- `generate_test_report.py`: 生成测试报告

### 测试脚本 (scripts/test/)

用于测试交易所API和功能：

- `test_edgex_*.py`: EdgeX 相关测试
- `test_exchange_api.py`: 交易所API测试
- `test_gui.py`: GUI测试

### 诊断脚本 (scripts/diagnose/)

用于诊断问题和检查配置：

- `diagnose_no_trades.py`: 诊断无交易问题
- `diagnose_websocket_connection.py`: 诊断WebSocket连接
- `check_websocket_config.py`: 检查WebSocket配置
- `explain_trade_difference.py`: 解释交易差异

### 工具脚本 (scripts/utils/)

辅助工具脚本：

- `quick_profit_calc.py`: 快速利润计算
- `position_manager_example.py`: 持仓管理模块使用示例
- `monitor_sol_bot.ps1`: SOL机器人监控脚本

## 数据目录

- `backtest_results/`: 回测结果输出
- `edgex_data/`: EdgeX历史数据（用于回测）
- `booking/data/`: 回测所需的数据文件

## 配置文件

### .env 文件

创建 `.env` 文件并配置必要的环境变量，参考 `env_example.txt`：

```bash
# EdgeX
EDGEX_ACCOUNT_ID=your_account_id
EDGEX_STARK_PRIVATE_KEY=your_private_key
EDGEX_BASE_URL=https://pro.edgex.exchange

# 策略配置
STRATEGY_TICKERS=ETH,SOL

# Telegram 通知（可选）
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 快速开始

1. **安装依赖：**
   ```bash
   pip install -r requirements.txt
   ```

2. **配置环境变量：**
   - 复制 `env_example.txt` 为 `.env`
   - 填入您的API密钥和配置

3. **运行交易机器人：**
   ```bash
   python runbot.py --exchange edgex --ticker ETH --direction buy --quantity 1.0
   ```

4. **查看持仓：**
   ```bash
   python position_manager.py ETH SOL
   ```

## 项目变更日志

### 最新更新（2026-01-17）

**第一次重构：**
- ✅ 删除重复的 `check_positions_in_strategy.py`（功能已合并到 `position_manager.py`）
- ✅ 整理项目结构，创建 `scripts/` 目录
- ✅ 将回测脚本移动到 `scripts/backtest/`
- ✅ 将测试脚本移动到 `scripts/test/`
- ✅ 将诊断脚本移动到 `scripts/diagnose/`
- ✅ 将工具脚本移动到 `scripts/utils/`
- ✅ 创建项目结构文档

**第二次重构（策略与回测分离）：**
- ✅ 创建 `strategies/` 目录，统一管理交易策略
- ✅ 创建 `backtest/` 目录，独立回测引擎
- ✅ 创建 `shared/` 目录，存放策略和回测共享的组件
- ✅ 将订单流策略和做市商策略移动到 `strategies/`
- ✅ 将回测引擎和相关文件移动到 `backtest/`
- ✅ 将共享组件（配置、分析器等）移动到 `shared/`
- ✅ 更新所有导入路径，确保模块正常工作
- ✅ 实现策略与回测的解耦，不同策略可以使用相同的回测功能

## 注意事项

1. **环境变量**：必须正确配置 `.env` 文件才能使用
2. **API密钥**：请妥善保管您的API密钥，不要提交到版本控制系统
3. **测试环境**：建议先在测试环境中运行，确认无误后再用于实盘
4. **风险管理**：请根据自身风险承受能力设置合理的参数

## 贡献指南

如需添加新的交易所支持，请参考 `docs/ADDING_EXCHANGES.md`。

## 许可证

详见 `LICENSE` 文件。
