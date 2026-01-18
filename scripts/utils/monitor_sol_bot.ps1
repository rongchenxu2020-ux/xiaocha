# SOL订单流机器人监控脚本
# 使用方法: .\monitor_sol_bot.ps1

$logFile = "logs\edgex_SOL_activity.log"
$signalFile = "logs\orderflow_signals_edgex_SOL_simulate_20260111.csv"
$processId = 63228

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SOL订单流机器人监控" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

while ($true) {
    Clear-Host
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "SOL订单流机器人监控 - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor Cyan
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host ""
    
    # 检查进程
    $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($proc) {
        $runtime = (Get-Date) - $proc.StartTime
        Write-Host "[状态] 运行中" -ForegroundColor Green
        Write-Host "  进程ID: $($proc.Id)"
        Write-Host "  运行时长: $([math]::Round($runtime.TotalMinutes, 1)) 分钟"
        Write-Host "  内存使用: $([math]::Round($proc.WorkingSet64 / 1MB, 1)) MB"
    } else {
        Write-Host "[状态] 已停止" -ForegroundColor Red
        Write-Host "  进程不存在"
        break
    }
    
    Write-Host ""
    Write-Host "=== 信号统计 ===" -ForegroundColor Yellow
    if (Test-Path $signalFile) {
        $csv = Import-Csv $signalFile -ErrorAction SilentlyContinue
        if ($csv) {
            $total = $csv.Count
            $confirmed = ($csv | Where-Object { $_.Confirmed -eq "YES" }).Count
            $buy = ($csv | Where-Object { $_.Direction -eq "BUY" }).Count
            $sell = ($csv | Where-Object { $_.Direction -eq "SELL" }).Count
            
            Write-Host "  总信号数: $total"
            Write-Host "  已确认信号: $confirmed" -ForegroundColor $(if ($confirmed -gt 0) { "Green" } else { "Gray" })
            Write-Host "  买入信号: $buy"
            Write-Host "  卖出信号: $sell"
            
            if ($total -gt 0) {
                $avgStrength = ($csv | ForEach-Object { [double]$_.Strength } | Measure-Object -Average).Average
                Write-Host "  平均信号强度: $([math]::Round($avgStrength * 100, 2))%"
                
                # 显示最新5个信号
                Write-Host ""
                Write-Host "  最新信号:" -ForegroundColor Yellow
                $csv | Select-Object -Last 5 | ForEach-Object {
                    $statusColor = switch ($_.Status) {
                        "CONFIRMED_SIMULATE" { "Green" }
                        "GENERATED" { "Yellow" }
                        default { "White" }
                    }
                    Write-Host "    $($_.Timestamp) | $($_.Direction) @ $($_.Price) | 强度: $([math]::Round([double]$_.Strength * 100, 1))% | $($_.Status)" -ForegroundColor $statusColor
                }
            } else {
                Write-Host "  暂无信号生成" -ForegroundColor Gray
            }
        } else {
            Write-Host "  信号文件为空" -ForegroundColor Gray
        }
    } else {
        Write-Host "  信号文件不存在" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "=== 最新日志（最后10行）===" -ForegroundColor Yellow
    if (Test-Path $logFile) {
        Get-Content $logFile -Tail 10 | ForEach-Object {
            if ($_ -match "ERROR") {
                Write-Host "  $_" -ForegroundColor Red
            } elseif ($_ -match "生成信号|信号已确认") {
                Write-Host "  $_" -ForegroundColor Green
            } else {
                Write-Host "  $_"
            }
        }
    } else {
        Write-Host "  日志文件不存在" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "按 Ctrl+C 停止监控" -ForegroundColor Gray
    Write-Host "下次更新: 10秒后..." -ForegroundColor Gray
    
    Start-Sleep -Seconds 10
}
