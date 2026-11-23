# stop_demo.ps1 — гасит экспортёр и Prometheus, запущенные start_demo.ps1.
#
# Запуск:
#   powershell -ExecutionPolicy Bypass -File "C:\...\ДЗ 4\tools\stop_demo.ps1"

$ErrorActionPreference = 'Continue'

Write-Host "=== ДЗ 4: остановка демонстрации ===" -ForegroundColor Cyan
$stopped = $false
foreach ($port in 8000, 9090) {
    $pids = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $pids) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Write-Host "  остановлен процесс $procId на порту $port"
        $stopped = $true
    }
}
if (-not $stopped) { Write-Host "  ничего не запущено — порты 8000 и 9090 свободны" }
Write-Host "Готово."
