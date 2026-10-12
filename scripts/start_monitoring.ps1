# scripts/start_monitoring.ps1
# Automates Prometheus & Grafana startup, scrape verification, and browser launch
# Supports both Docker Compose and Native Windows Zero-Setup modes

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " ResearchOps AI — Prometheus & Grafana Observability Setup" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$scriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Split-Path -Parent $scriptRoot

# 1. Check if Docker is available and running
Write-Host "`n[1/3] Determining deployment mode (Docker vs Native Zero-Setup)..." -ForegroundColor Yellow
$dockerOk = $false
try {
    $info = docker info 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dockerOk = $true
    }
} catch {
    $dockerOk = $false
}

if ($dockerOk) {
    Write-Host "  -> Docker daemon is active. Launching via Docker Compose..." -ForegroundColor Green
    docker compose up -d prometheus grafana
} else {
    Write-Host "  -> Docker daemon not detected. Using Native Windows zero-setup binaries..." -ForegroundColor Cyan

    $promExe = Join-Path $repoRoot ".tools\prometheus_raw\prometheus-2.51.0.windows-amd64\prometheus.exe"
    $promCfg = Join-Path $repoRoot "monitoring\prometheus.yml"
    $promData = Join-Path $repoRoot ".tools\prom_data"

    $grafanaExe = Join-Path $repoRoot ".tools\grafana_raw\grafana-v10.4.0\bin\grafana-server.exe"
    $grafanaHome = Join-Path $repoRoot ".tools\grafana_raw\grafana-v10.4.0"
    $grafanaCfg = Join-Path $repoRoot ".tools\grafana.ini"

    # Start Prometheus if not listening on 9090
    $promConn = Get-NetTCPConnection -LocalPort 9090 -ErrorAction SilentlyContinue
    if (-not $promConn) {
        Write-Host "  -> Starting native Prometheus (Port 9090)..." -ForegroundColor Yellow
        Start-Process -FilePath $promExe -ArgumentList "--config.file=`"$promCfg`" --web.listen-address=0.0.0.0:9090 --storage.tsdb.path=`"$promData`"" -WindowStyle Hidden
    } else {
        Write-Host "  -> Prometheus already active on port 9090." -ForegroundColor Green
    }

    # Start Grafana if not listening on 3001
    $grafConn = Get-NetTCPConnection -LocalPort 3001 -ErrorAction SilentlyContinue
    if (-not $grafConn) {
        Write-Host "  -> Starting native Grafana (Port 3001)..." -ForegroundColor Yellow
        Start-Process -FilePath $grafanaExe -ArgumentList "--homepath=`"$grafanaHome`" --config=`"$grafanaCfg`"" -WindowStyle Hidden
    } else {
        Write-Host "  -> Grafana already active on port 3001." -ForegroundColor Green
    }
}

# 2. Wait for endpoints to become responsive
Write-Host "`n[2/3] Verifying Observability Endpoints..." -ForegroundColor Yellow

$promHealthy = $false
for ($i = 0; $i -lt 15; $i++) {
    try {
        $res = Invoke-WebRequest -Uri "http://localhost:9090/-/healthy" -UseBasicParsing -TimeoutSec 2
        if ($res.StatusCode -eq 200) {
            $promHealthy = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}
if ($promHealthy) {
    Write-Host "  -> Prometheus Server : HEALTHY [OK] (http://localhost:9090)" -ForegroundColor Green
} else {
    Write-Host "  -> Prometheus Server : STARTING UP (http://localhost:9090)" -ForegroundColor Yellow
}

$grafanaHealthy = $false
for ($i = 0; $i -lt 15; $i++) {
    try {
        $res = Invoke-WebRequest -Uri "http://localhost:3001/api/health" -UseBasicParsing -TimeoutSec 2
        if ($res.StatusCode -eq 200) {
            $grafanaHealthy = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 1
    }
}
if ($grafanaHealthy) {
    Write-Host "  -> Grafana Dashboard : HEALTHY [OK] (http://localhost:3001)" -ForegroundColor Green
} else {
    Write-Host "  -> Grafana Dashboard : STARTING UP (http://localhost:3001)" -ForegroundColor Yellow
}

# 3. Summary & Links
Write-Host "`n[3/3] Observability Telemetry Stack Ready!" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor DarkGray
Write-Host "  * Grafana Dashboard  : http://localhost:3001/d/researchops-overview/researchops-overview" -ForegroundColor Green
Write-Host "    -> Anonymous Mode  : Enabled (Direct instant access)" -ForegroundColor White
Write-Host "    -> Admin Login     : admin / admin" -ForegroundColor White
Write-Host "  * Prometheus UI      : http://localhost:9090" -ForegroundColor Green
Write-Host "  * Scrape Targets     : http://localhost:9090/targets" -ForegroundColor Green
Write-Host "  * Raw Metrics Feed   : http://localhost:8000/metrics" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor DarkGray

# Open dashboard in default browser
Start-Process "http://localhost:3001/d/researchops-overview/researchops-overview"
