# 选品 Agent 一键启动脚本
# 自动：UTF-8 编码 → 检查代理 → 跑 Agent → 打开报告
# 用法：在 D:\new 项目\ 下执行  .\poc\01-选品\run.ps1

# 1. 强制 UTF-8（解决乱码根因）
chcp 65001 | Out-Null
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  选品 Agent — 一键启动" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan

# 2. 检查美国代理
Write-Host "`n[1/3] 检查美国代理..." -ForegroundColor Yellow
$proxyAlive = Test-NetConnection -ComputerName 127.0.0.1 -Port 10808 -WarningAction SilentlyContinue -InformationLevel Quiet
if ($proxyAlive) {
    Write-Host "  ✓ xray 代理已就绪 (127.0.0.1:10808)" -ForegroundColor Green
} else {
    Write-Host "  ⚠ xray 代理未启动，尝试启动..." -ForegroundColor Yellow
    Start-Process -FilePath ".\.venv\Scripts\python.exe" -ArgumentList "poc\01-选品\proxy\setup_us_proxy.py" -WindowStyle Hidden
    Start-Sleep -Seconds 5
    Write-Host "  ✓ 已启动 xray" -ForegroundColor Green
}

# 3. 跑 Agent
$query = if ($args[0]) { $args[0] } else { "我想做蓝牙耳机这个品类，帮我做完整的选品调研。" }
Write-Host "`n[2/3] 启动 Agent..." -ForegroundColor Yellow
Write-Host "  需求: $query" -ForegroundColor Gray

& .\.venv\Scripts\python.exe "poc\01-选品\agent.py" $query

# 4. 找到最新报告
Write-Host "`n[3/3] 查找最新报告..." -ForegroundColor Yellow
$latest = Get-ChildItem "poc\01-选品\reports\agent_final_*.md" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if ($latest) {
    Write-Host "  ✓ 最终报告: $($latest.FullName)" -ForegroundColor Green
    Write-Host "`n--- 报告预览（前 60 行）---" -ForegroundColor Cyan
    Get-Content $latest.FullName -Encoding utf8 -TotalCount 60
} else {
    Write-Host "  ⚠ 未找到最终报告" -ForegroundColor Red
}

Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  完成" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
