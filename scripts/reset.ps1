<#
.SYNOPSIS
  Wipe all data (docker compose down -v) and bring the stack back up. The seed re-runs automatically.
#>
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Docker is not running; dev.ps1 will start it.'
} else {
    Write-Host 'Stopping stack and removing volumes (pgdata, redisdata, miniodata)...'
    docker compose down -v --remove-orphans
    if ($LASTEXITCODE -ne 0) { throw 'docker compose down failed' }
}
& (Join-Path $PSScriptRoot 'dev.ps1')
