<#
.SYNOPSIS
  Backend pytest (inside the api container), then frontend lint, typecheck and build (on the host).
.PARAMETER SkipBackend
  Skip the backend half.
.PARAMETER SkipFrontend
  Skip the frontend half.
.PARAMETER PytestArgs
  Extra args for pytest, e.g. -PytestArgs "-k","applications"
#>
param(
    [switch]$SkipBackend,
    [switch]$SkipFrontend,
    [string[]]$PytestArgs = @()
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Run([string]$what, [scriptblock]$cmd) {
    Write-Host "==> $what" -ForegroundColor Cyan
    & $cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED: $what (exit $LASTEXITCODE)" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

if (-not $SkipBackend) {
    docker info *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Docker is not running. Run .\scripts\dev.ps1 first.' -ForegroundColor Red
        exit 1
    }
    Run 'docker compose up -d --wait api' { docker compose up -d --wait api }
    Run 'pytest (api container)' { docker compose exec -T api pytest -q --cov=app --cov-report=term-missing:skip-covered @PytestArgs }
}

if (-not $SkipFrontend) {
    Push-Location (Join-Path $root 'frontend')
    try {
        if (-not (Test-Path 'node_modules')) { Run 'npm ci' { npm ci } }
        Run 'npm run lint'  { npm run lint }
        Run 'tsc --noEmit'  { npx tsc --noEmit }
        Run 'npm run build' { npm run build }
    } finally { Pop-Location }
}

Write-Host 'All checks passed.' -ForegroundColor Green
