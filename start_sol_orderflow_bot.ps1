# SOL订单流机器人启动脚本（PowerShell）
# 使用方法: .\start_sol_orderflow_bot.ps1 [模式] [其他参数]
# 
# 模式选项:
#   balanced        - 平衡设置（推荐开始使用）
#   aggressive      - 激进设置（更容易触发）
#   very-aggressive - 非常激进（最大化触发频率）
#   custom          - 自定义参数
#
# 示例:
#   .\start_sol_orderflow_bot.ps1 balanced
#   .\start_sol_orderflow_bot.ps1 aggressive --simulate
#   .\start_sol_orderflow_bot.ps1 very-aggressive --simulate --enable-logging

param(
    [string]$Mode = "balanced",
    [string[]]$ExtraArgs = @()
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SOL订单流机器人启动脚本" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "模式: $Mode" -ForegroundColor Yellow
if ($ExtraArgs.Count -gt 0) {
    Write-Host "额外参数: $($ExtraArgs -join ' ')" -ForegroundColor Yellow
}
Write-Host ""

# 检查Python是否安装
try {
    $pythonVersion = python --version 2>&1
    Write-Host "Python版本: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "错误: 未找到Python，请先安装Python" -ForegroundColor Red
    exit 1
}

# 检查.env文件
if (-not (Test-Path ".env")) {
    Write-Host "警告: 未找到 .env 文件" -ForegroundColor Yellow
    Write-Host "请确保已配置环境变量" -ForegroundColor Yellow
    Write-Host ""
}

# 默认添加模拟模式（如果用户没有指定）
$hasSimulate = $ExtraArgs | Where-Object { $_ -match "simulate" }
if (-not $hasSimulate) {
    Write-Host "提示: 默认使用模拟模式（不会实际下单）" -ForegroundColor Cyan
    Write-Host "如需真实交易，请添加参数: --no-simulate 或移除 --simulate" -ForegroundColor Cyan
    Write-Host ""
    $ExtraArgs += "--simulate"
}

# 构建命令
$command = "python booking/run_sol_orderflow_bot.py --mode $Mode"
if ($ExtraArgs.Count -gt 0) {
    $command += " " + ($ExtraArgs -join " ")
}

Write-Host "正在启动SOL订单流机器人..." -ForegroundColor Green
Write-Host "执行命令: $command" -ForegroundColor Gray
Write-Host ""

# 运行机器人
try {
    Invoke-Expression $command
} catch {
    Write-Host ""
    Write-Host "机器人运行出错: $_" -ForegroundColor Red
    exit 1
}
