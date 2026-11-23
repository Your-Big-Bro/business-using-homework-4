# start_demo.ps1 — поднимает всё для показа ДЗ 4 одной командой.
#
# Что делает:
#   1. останавливает прежние процессы на портах 8000 (экспортёр) и 9090 (Prometheus);
#   2. очищает базу Prometheus, чтобы график начинался с чистого листа;
#   3. запускает экспортёр в режиме replay (60 с плато → линейная деградация);
#   4. запускает Prometheus с конфигом и правилами алертов;
#   5. ждёт готовности и печатает шпаргалку со ссылками и таймингом.
#
# Запуск (из любой папки):
#   powershell -ExecutionPolicy Bypass -File "C:\...\ДЗ 4\tools\start_demo.ps1"
#
# Ключи:
#   -NoReset  — не удалять prometheus/data (сохранить старые графики)

param([switch]$NoReset)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "=== ДЗ 4: подготовка демонстрации ===" -ForegroundColor Cyan
$statusFile = Join-Path $root "artifacts\demo_status.txt"
"$(Get-Date -Format o)  starting" | Set-Content -LiteralPath $statusFile -Encoding UTF8

# 1. останавливаем всё, что уже слушает нужные порты
foreach ($port in 8000, 9090) {
    $pids = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    foreach ($procId in $pids) {
        Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
        Write-Host "  остановлен процесс $procId на порту $port"
    }
}
Start-Sleep -Seconds 2

# 2. чистая база Prometheus (иначе на графике останется прошлая деградация)
if (-not $NoReset) {
    Remove-Item -Recurse -Force (Join-Path $root 'prometheus\data') -ErrorAction SilentlyContinue
    Write-Host "  база Prometheus очищена — график будет с нуля"
}

# 3. находим Python (сначала окружение DSH, потом системный)
$py = $env:DSH_PYTHON
if (-not $py) {
    $candidate = 'C:\Users\Dimanowski\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe'
    $py = if (Test-Path $candidate) { $candidate } else { 'python' }
}
$env:PYTHONPATH = Join-Path $root '.pylibs'
$env:PYTHONIOENCODING = 'utf-8'

# 4. экспортёр метрик
Start-Process -FilePath $py `
    -ArgumentList 'src\metrics_exporter.py', '--mode', 'replay', '--port', '8000' `
    -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $root 'artifacts\exporter.log') `
    -RedirectStandardError (Join-Path $root 'artifacts\exporter.err.log')
Write-Host "  экспортёр запущен (replay, :8000)"
Start-Sleep -Seconds 2

# 5. Prometheus
$prom = Get-ChildItem (Join-Path $root 'prometheus\prometheus-*\prometheus.exe') -ErrorAction SilentlyContinue |
        Select-Object -First 1
if (-not $prom) {
    Write-Host "  ОШИБКА: prometheus.exe не найден — запустите tools\fetch_prometheus.py" -ForegroundColor Red
    exit 1
}
Start-Process -FilePath $prom.FullName `
    -ArgumentList '--config.file=prometheus\prometheus.yml', '--storage.tsdb.path=prometheus\data',
                  '--web.listen-address=127.0.0.1:9090' `
    -WorkingDirectory $root -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $root 'artifacts\prometheus.log') `
    -RedirectStandardError (Join-Path $root 'artifacts\prometheus.err.log')
Write-Host "  Prometheus запущен (:9090)"

# 6. ждём готовности
$ok = $false
for ($i = 0; $i -lt 30; $i++) {
    Start-Sleep -Seconds 1
    try {
        $null = Invoke-WebRequest 'http://127.0.0.1:9090/-/healthy' -UseBasicParsing -TimeoutSec 2
        $ok = $true
        break
    } catch { }
}
if (-not $ok) {
    Write-Host "  ОШИБКА: Prometheus не ответил за 30 секунд, смотрите artifacts\prometheus.err.log" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== ВСЁ ГОТОВО, МОЖНО ЗАПИСЫВАТЬ ===" -ForegroundColor Green
Write-Host ""
Write-Host "Тайминг сценария (отсчёт пошёл сейчас):" -ForegroundColor Yellow
Write-Host "  0:00 - 1:00   F1 стабилен на 0.588, алертов нет"
Write-Host "  1:00 - 3:00   F1 линейно падает до 0.490, растёт model_drift_share"
Write-Host "  1:30 - 1:50   загорается DataDriftDetected"
Write-Host "  2:30 - 3:10   загораются ModelF1Drop и ModelF1Critical"
Write-Host ""
Write-Host "Что открыть:" -ForegroundColor Yellow
Write-Host "  http://127.0.0.1:9090/alerts        — список горящих алертов"
Write-Host "  http://127.0.0.1:9090/graph         — запрос model_f1_score + кнопка Execute"
Write-Host "  http://127.0.0.1:9090/targets       — оба таргета UP"
Write-Host ""
Write-Host "Остановить: powershell -ExecutionPolicy Bypass -File tools\stop_demo.ps1"
"$(Get-Date -Format o)  ready  exporter=:8000  prometheus=:9090" | Set-Content -LiteralPath $statusFile -Encoding UTF8
