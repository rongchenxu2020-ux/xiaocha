# 订单流策略测试指南

## 快速测试步骤

### 1. 确保环境正确

```bash
# 进入项目目录
cd c:\Users\user\Desktop\perp-dex-tools-main

# 检查Python版本（需要3.8+）
python --version

# 如果python命令不可用，尝试：
python3 --version
py --version
```

### 2. 运行测试脚本（推荐方法）

```bash
# 方法1: 使用python命令
python booking/test_strategy.py

# 方法2: 如果python不可用，尝试python3
python3 booking/test_strategy.py

# 方法3: Windows上可以尝试py命令
py booking/test_strategy.py
```

### 3. 使用回测命令行

```bash
# 生成模拟数据并回测
python booking/run_backtest.py --generate-mock --start-price 2000 --num-samples 500 --exchange edgex --ticker ETH --imbalance-threshold 0.6 --signal-strength-threshold 0.7 --position-size 0.1 --export-trades --export-equity
```

### 4. 在Python中直接运行

```python
import sys
from pathlib import Path
from decimal import Decimal

# 添加项目路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from booking.config import OrderFlowConfig
from booking.backtest_data import BacktestDataLoader
from booking.backtest_engine import BacktestEngine
from booking.backtest_report import BacktestReportGenerator

# 生成模拟数据
data = BacktestDataLoader.generate_mock_data(
    start_price=Decimal(2000),
    num_samples=500,
    interval_seconds=1.0,
    volatility=0.001
)

# 配置策略
config = OrderFlowConfig(
    exchange='edgex',
    ticker='ETH',
    contract_id='ETH',
    imbalance_threshold=0.6,
    signal_strength_threshold=0.7,
    position_size=Decimal(0.1)
)

# 运行回测
engine = BacktestEngine(config, initial_balance=Decimal(10000))
result = engine.run(data)

# 生成报告
report = BacktestReportGenerator.generate_text_report(result)
print(report)
```

## 预期输出

测试应该会显示：
- 数据生成进度
- 回测执行进度
- 完整的回测报告，包括：
  - 基础信息（初始/最终资金、收益率）
  - 交易统计（交易次数、胜率、盈利因子）
  - 风险指标（最大回撤、夏普比率）
  - 信号统计

## 输出文件

测试完成后会在 `backtest_results/` 目录生成：
- `test_report.txt` - 详细回测报告
- `test_trades.csv` - 交易记录
- `test_equity.csv` - 权益曲线

## 故障排除

### 问题1: 'python' 不是内部或外部命令

**解决方案**:
1. 检查Python是否已安装
2. 尝试使用 `python3` 或 `py` 命令
3. 将Python添加到系统PATH

### 问题2: 导入错误 (ImportError)

**解决方案**:
1. 确保在项目根目录运行
2. 检查是否有虚拟环境需要激活
3. 确保所有依赖已安装

### 问题3: 模块找不到 (ModuleNotFoundError)

**解决方案**:
```bash
# 确保在项目根目录
cd c:\Users\user\Desktop\perp-dex-tools-main

# 检查Python路径
python -c "import sys; print(sys.path)"
```

### 问题4: 编码错误

**解决方案**:
- 脚本已添加 `# -*- coding: utf-8 -*-` 声明
- 如果仍有问题，确保终端支持UTF-8编码

### 问题5: 数据格式错误

**解决方案**:
- 检查数据格式是否正确
- 验证策略参数是否合理
- 确保有足够的模拟数据

## 验证清单

- [ ] Python已安装且版本 >= 3.8
- [ ] 在项目根目录运行
- [ ] 所有依赖已安装
- [ ] 文件路径正确
- [ ] 终端支持UTF-8编码

## 联系支持

如果以上方法都无法解决问题，请提供：
1. Python版本信息
2. 完整的错误信息
3. 操作系统信息
4. 运行命令和输出
