<#
.SYNOPSIS
  Start the full CampusHire stack (Docker Desktop -> compose up --build -> wait for health).
.PARAMETER Local
  Print the env overrides for running the backend outside Docker (infra still in Docker), then exit.
.PARAMETER NoBuild
  Skip --build (reuse existing images).
#>
param(
    [switch]$Local,
    [switch]$NoBuild
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if ($Local) {
    Write-Host @'
Local (non-Docker) backend run. Start only infra:  docker compose up -d postgres redis minio mailpit
Then, in PowerShell from .\backend:

  py -3.13 -m venv .venv; .\.venv\Scripts\Activate.ps1      # may need: Set-ExecutionPolicy -Scope Process Bypass
  pip install -r requirements.txt -r requirements-dev.txt
  $env:DATABASE_URL         = "postgresql+asyncpg://campushire:campushire@localhost:5433/campushire"
  $env:TEST_DATABASE_URL    = "postgresql+asyncpg://campushire:campushire@localhost:5433/campushire_test"
  $env:REDIS_URL            = "redis://localhost:6379/0"
  $env:CELERY_BROKER_URL    = "redis://localhost:6379/1"
  $env:CELERY_RESULT_BACKEND= "redis://localhost:6379/2"
  $env:MINIO_ENDPOINT       = "http://localhost:9000"
  $env:MINIO_PUBLIC_URL     = "http://localhost:9000"
  $env:MINIO_ACCESS_KEY     = "campushire"
  $env:MINIO_SECRET_KEY     = "campushire-secret"
  $env:SMTP_HOST            = "localhost"
  $env:JWT_SECRET           = "change-me-dev-only-0123456789abcdef0123456789abcdef"
  alembic upgrade head; python -m app.seed
  uvicorn app.main:app --reload --port 8000
  python -m pytest
'@
    return
}

function Test-DockerUp {
    docker info *> $null
    return ($LASTEXITCODE -eq 0)
}

function Wait-Url([string]$Url, [int]$TimeoutSec = 300) {
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 400) { return $true }
        } catch { }
        Start-Sleep -Seconds 3
    }
    return $false
}

# 1. Docker daemon
if (-not (Test-DockerUp)) {
    Write-Host 'Docker daemon not reachable, starting Docker Desktop...'
    $exe = Join-Path $Env:ProgramFiles 'Docker\Docker\Docker Desktop.exe'
    if (-not (Test-Path $exe)) { throw "Docker Desktop not found at $exe" }
    Start-Process $exe
    $deadline = (Get-Date).AddSeconds(120)
    while (-not (Test-DockerUp)) {
        if ((Get-Date) -gt $deadline) { throw 'Docker did not become ready within 120 s.' }
        Start-Sleep -Seconds 3
    }
    Write-Host 'Docker is ready.'
}

# 2. .env
if (-not (Test-Path (Join-Path $root '.env'))) {
    Copy-Item (Join-Path $root '.env.example') (Join-Path $root '.env')
    Write-Host 'Created .env from .env.example'
}

# 3. Port check (informational)
foreach ($p in 3000, 8000, 5433, 6379, 9000, 9001, 1025, 8025) {
    $c = Get-NetTCPConnection -LocalPort $p -State Listen -ErrorAction SilentlyContinue
    if ($c) {
        $owner = (Get-Process -Id $c[0].OwningProcess -ErrorAction SilentlyContinue).ProcessName
        Write-Host "note: port $p already listening (process: $owner). Fine if it is this stack, otherwise change the host port in docker-compose.yml."
    }
}

# 4. Up
$argsList = @('compose', 'up', '-d')
if (-not $NoBuild) { $argsList += '--build' }
& docker @argsList
if ($LASTEXITCODE -ne 0) { throw 'docker compose up failed' }

# 5. Wait for readiness
Write-Host 'Waiting for API (http://localhost:8000/readyz). First run builds, migrates and seeds; this can take a few minutes.'
if (-not (Wait-Url 'http://localhost:8000/readyz' 420)) {
    docker compose logs --tail 60 api
    throw 'API did not become ready.'
}
Write-Host 'Waiting for frontend (http://localhost:3000) ...'
if (-not (Wait-Url 'http://localhost:3000' 240)) {
    docker compose logs --tail 60 frontend
    throw 'Frontend did not become ready.'
}

Write-Host ''
Write-Host 'CampusHire is up:'
Write-Host '  App          http://localhost:3000'
Write-Host '  API docs     http://localhost:8000/docs'
Write-Host '  MinIO        http://localhost:9001  (campushire / campushire-secret)'
Write-Host '  Mailpit      http://localhost:8025'
Write-Host '  Postgres     localhost:5433  (campushire / campushire)'
Write-Host 'Run .\scripts\smoke.ps1 to verify.'
